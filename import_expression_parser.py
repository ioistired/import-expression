#!/usr/bin/env python3
# encoding: utf-8

import io
import collections
import tokenize

_is_op = lambda type, op: lambda token: token.type == type and token.string == op

START_IMPORT = '<<'
_is_start = _is_op(tokenize.OP, START_IMPORT)

END_IMPORT = '>>'
_is_end = _is_op(tokenize.OP, END_IMPORT)

DOT = '.'
_is_dot = _is_op(tokenize.OP, DOT)

IMPORTER = '__import_module'
HEADER = f'from importlib import import_module as {IMPORTER}\n'

def _token_gen(str):
	return tokenize.tokenize(io.BytesIO(str.encode('utf-8')).readline)

class _ImportParserState:
	__slots__ = ('in_import', 'started_name', 'previous_tokens', 'filename')

	def __init__(self, filename='<repl session>'):
		self.in_import = False
		self.started_name = False
		# enough to store ">>" + "." in order
		# to determine if the user is dumb enough to do
		# <<x>>.<<y>>
		self.previous_tokens = collections.deque(maxlen=2)
		self.filename = filename

	@property
	def last_token(self):
		return self.previous_tokens[-1]

	def reset(self):
		self.__init__(filename=self.filename)

	def __iter__(self):
		yield from map(self.__getattr__, self.__slots__)

	def __repr__(self):
		return (
			f'{self.__module__}.{self.__class__.__qualname__}<'
			f'in_import={self.in_import}, '
			f'started_name={self.started_name}, '
			f'previous_tokens={list(self.previous_tokens)}, '
			f'filename={self.filename!r}>')

def _error(state, message, token=None):
	token = token or state.last_token
	text, (lineno, offset) = token.line, token.end
	return SyntaxError(message, (state.filename, lineno, offset, text))

def parse_import_expressions(str, *, filename='<repl session>'):
	output = io.StringIO()
	output.write(HEADER)

	state = _ImportParserState(filename=filename)

	for token in _token_gen(str):
		_parse(token, state, output)
		state.previous_tokens.append(token)

	if state.in_import:
		# e.g. "<<"
		raise _error(state, 'unclosed start of import expression')

	return output.getvalue()

def _parse(token, state, output):
	if token.type == tokenize.ENCODING:
		# tokenize puts this at the start of every token stream ¯⧹_(ツ)_⧸¯
		return

	elif token.type == tokenize.OP:
		_handle_op(token, state, output)

	elif state.in_import:
		_handle_import_name(token, state, output)

	else:
		output.write(token.string)

def _handle_op(token, state, output):
	if token.string == START_IMPORT:
		_handle_import_expr_start(state, output)

	elif token.string == END_IMPORT:
		_handle_import_expr_end(state, output)

	elif token.string == DOT:
		_handle_dot(token, state, output)

	else:
		output.write(token.string)

def _handle_import_expr_start(state, output):
	if state.in_import:
		# e.g. "<< <<x>>.y >>"
		raise _error(state, 'nested import expressions are not allowed')

	if _is_end(state.previous_tokens[0]) and _is_dot(state.last_token):
		raise _error(state, 'attribute access: expected name, got import expression')

	state.in_import = True
	output.write(f'{IMPORTER}("')

def _handle_import_expr_end(state, output):
	if not state.in_import:
		# e.g. ">>"
		raise _error(state, 'unexpected end of import expression')

	if _is_dot(state.last_token):
		# e.g. "<<x.>>.y"
		raise _error(state, f'unexpected end of import expression; expected name, got "{DOT}"')

	state.reset()
	output.write('")')

def _handle_dot(token, state, output):
	if state.in_import and not state.started_name:
		# e.g. "<<.x>>"
		raise _error(state, 'import expression may not begin with a dot')

	output.write(token.string)

def _handle_import_name(token, state, output):
	if token.type == tokenize.NAME:
		state.started_name = True
		output.write(token.string)
	else:
		# e.g. "<<'foo'>>" (a lot of cases will reach this branch though)
		raise _error(state, token=token, message='expected only (possibly dotted) names inside of an import expression')
