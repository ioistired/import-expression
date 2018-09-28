import collections
import io
from token import *
import tokenize as tokenize_
from .constants import *

tokenize_.TokenInfo.value = property(lambda self: self.string)

IMPORT_OP = '!'
is_import = lambda token: token.type == tokenize_.ERRORTOKEN and token.string == IMPORT_OP

NEWLINES = {NEWLINE, tokenize_.NL}

def fix_syntax(s):
	tokens = tokenize(s)  # TODO is there a better way than tokenizing and then untokenizing? don't think so?
	untokenizer = Untokenizer()
	out = untokenizer.untokenize(tokens)

	if untokenizer.encoding is not None:
		out = out.encode(untokenizer.encoding)

	return out

# taken from Lib/tokenize_.py at 3.6
# TODO find out if license is compat with Charity Public License
class Untokenizer:
	def __init__(self):
		self.tokens = collections.deque()
		self.indents = collections.deque()
		self.prev_row = 1
		self.prev_col = 0
		self.startline = False
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

	def untokenize(self, iterable):
		for token in iterable:
			if token.type == tokenize_.ENCODING:
				self.encoding = token.value
				continue

			if token.type == ENDMARKER:
				break

			if self._untokenize_whitespace(token):
				continue

			self.add_whitespace(token.start)

			if is_import(token):
				self.tokens.append(MARKER)
			else:
				self.tokens.append(token.value)

			self.prev_row, self.prev_col = token.end
			if type in NEWLINES:
				self.prev_row += 1
				self.prev_col = 0

		return "".join(self.tokens)

	def _untokenize_whitespace(self, token):
		if token.type == INDENT:
			self.indents.append(token.value)
			return True

		elif token.type == DEDENT:
			self.indents.pop()
			self.prev_row, self.prev_col = token.end
			return True

		elif token.type in NEWLINES:
			self.startline = True

		elif self.startline and self.indents:
			indent = self.indents[-1]
			start_row, start_col = token.start
			if start_row >= len(indent):
				self.tokens.append(indent)
				self.prev_col = len(indent)
			self.startline = False

		return False

def tokenize(string):
	return tokenize_.tokenize(io.BytesIO(string.encode('utf-8')).readline)
