import collections
import io
from token import *
import tokenize as tokenize_

from ._constants import *

tokenize_.TokenInfo.value = property(lambda self: self.string)

is_import = lambda token: token.type == tokenize_.ERRORTOKEN and token.string == IMPORT_OP

def fix_syntax(source):
	syntax_fixer = SyntaxFixer(source)
	return syntax_fixer.fix_syntax()

class SyntaxFixer:
	def __init__(self, source: str):
		self.source = source

	def fix_syntax(self):
		patched_tokens = self.patch_tokens()
		try:
			return tokenize_.untokenize(patched_tokens)
		except ValueError:
			raise SyntaxError('illegal import op') from None

	def patch_tokens(self):
		tokens = tokenize(self.source)
		patched_tokens = []
		self.prev_token = None

		self.col_offset = 0  # tracks how many chars we've added to the current row
		self.prev_row = 0

		for token in tokens:
			patched_tokens.append(self.patch_token(token))

			if self.end_row > self.prev_row:
				self.col_offset = 0

			self.prev_token = token
			self.prev_row, self.prev_col = self.prev_token.end

		return patched_tokens

	def patch_token(self, token):
		self.start_row, self.start_col = token.start
		self.end_row, self.end_col = token.end

		if is_import(token):
			new_token = self.patch_import_token(token)
		else:
			new_token = self.patch_non_import_token(token)

		return new_token

	def patch_import_token(self, token):
		new_end_row, new_end_col = token.end

		new_value = MARKER
		self.col_offset += len(MARKER) - len(IMPORT_OP)  # since we're not including the import op itself
		new_end_col += self.col_offset

		return token._replace(string=new_value, end=(self.end_row, new_end_col))

	def patch_non_import_token(self, token):
		if self.prev_token is None or self.prev_row != self.end_row:
			# column offsets have not changed
			return token

		new_start_row, new_start_col = token.start
		new_end_row, new_end_col = token.end

		new_start_col += self.col_offset
		new_end_col += self.col_offset
		return token._replace(start=(new_start_row, new_start_col), end=(new_end_row, new_end_col))

def tokenize(string):
	return tokenize_.tokenize(io.BytesIO(string.encode('utf-8')).readline)
