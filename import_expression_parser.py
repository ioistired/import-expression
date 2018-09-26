#!/usr/bin/env python3
# encoding: utf-8

import ast
import io
import collections
import token
import tokenize
import uuid

_is = lambda type, op: lambda token: token.type == type and token.string == op

IMPORT_OP = '!'
_is_import = _is(token.ERRORTOKEN, IMPORT_OP)

IMPORTER = '__import_module'
HEADER = f'from importlib import import_module as {IMPORTER}\n'

# replace IMPORT_OP with this to make it valid syntax
MARKER = '__IMPORT_EXPR_END'

NEWLINES = {token.NEWLINE, tokenize.NL}

# taken from Lib/tokenize.py at 3.6
# TODO find out if license is compat with Charity Public License
class _Untokenizer:
	def __init__(self):
		self.tokens = []
		self.prev_row = 1
		self.prev_col = 0
		self.encoding = None

	def add_whitespace(self, start):
		row, col = start
		if row < self.prev_row or row == self.prev_row and col < self.prev_col:
			raise ValueError("start ({},{}) precedes previous end ({},{})"
							 .format(row, col, self.prev_row, self.prev_col))
		row_offset = row - self.prev_row
		if row_offset:
			self.tokens.append("\\\n" * row_offset)
			self.prev_col = 0
		col_offset = col - self.prev_col
		if col_offset:
			self.tokens.append(" " * col_offset)

	def untokenize(self, iterable, *, include_import_statement):
		it = iter(iterable)
		indents = []
		startline = False

		if include_import_statement:
			self.tokens.append(HEADER)

		for t in it:
			if len(t) == 2:
				self.compat(t, it)
				break
			tok_type, value, start, end, line = t
			if tok_type == tokenize.ENCODING:
				self.encoding = value
				continue
			if tok_type == token.ENDMARKER:
				break
			if tok_type == token.INDENT:
				indents.append(value)
				continue
			elif tok_type == token.DEDENT:
				indents.pop()
				self.prev_row, self.prev_col = end
				continue
			elif tok_type in NEWLINES:
				startline = True
			elif startline and indents:
				indent = indents[-1]
				if start[1] >= len(indent):
					self.tokens.append(indent)
					self.prev_col = len(indent)
				startline = False

			self.add_whitespace(start)

			if _is_import(t):
				self.tokens.append(MARKER)
			else:
				self.tokens.append(value)

			self.prev_row, self.prev_col = end
			if tok_type in NEWLINES:
				self.prev_row += 1
				self.prev_col = 0

		return "".join(self.tokens)

	def compat(self, token, iterable):
		indents = []
		toks_append = self.tokens.append
		startline = token[0] in (NEWLINE, NL)
		prevstring = False

		for tok in chain([token], iterable):
			toknum, tokval = tok[:2]
			if toknum == tokenize.ENCODING:
				self.encoding = tokval
				continue

			if toknum in {token.NAME, token.NUMBER, token.ASYNC, token.AWAIT}:
				tokval += ' '

			# Insert a space between two consecutive strings
			if toknum == STRING:
				if prevstring:
					tokval = ' ' + tokval
				prevstring = True
			else:
				prevstring = False

			if toknum == token.INDENT:
				indents.append(tokval)
				continue
			elif toknum == token.DEDENT:
				indents.pop()
				continue
			elif toknum in NEWLINES:
				startline = True
			elif startline and indents:
				toks_append(indents[-1])
				startline = False
			toks_append(tokval)

def _tokenize(string):
	return tokenize.tokenize(io.BytesIO(string.encode('utf-8')).readline)

def parse(s, *, include_import_statement=True, filename='<repl session>'):
	tokens = _tokenize(s)  # TODO is there a better way than tokenizing and then untokenizing? don't think so?
	ut = _Untokenizer()
	out = ut.untokenize(tokens, include_import_statement=include_import_statement)
	if ut.encoding is not None:
		out = out.encode(ut.encoding)
	return ImportTransformer().visit(ast.parse(out, filename))

class ImportTransformer(ast.NodeTransformer):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def visit_Attribute(self, node):
		if not isinstance(node.ctx, ast.Load):
			print('not load')
			return node

		if node.attr.endswith(MARKER):
			print('endswith marker')

			without_marker = node.attr.rpartition(MARKER)[0]

			return node  # "comment out" the rest

			return ast.copy_location(ast.Call(
				func=ast.Name(id=IMPORTER, ctx=ast.Load()), args=[
					ast.Str(s=NotImplemented)),  # XXX
				]
			), node)
		else:
			print('not endswith marker', node.attr)
			return node
