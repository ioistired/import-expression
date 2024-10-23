# Copyright © io mintz <io@mintz.cc>
# Copyright © Thanos <111999343+Sachaa-Thanasius@users.noreply.github.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”),
# to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# This file primarily consists of code vendored from the CPython standard library.
# It is used under the Python Software Foundation License Version 2.
# See LICENSE for details.

import io
import re
import sys
import string
import typing
import collections
from token import *
from .constants import *
import tokenize as tokenize_

T = typing.TypeVar("T")

def fix_syntax(s: typing.AnyStr, filename=DEFAULT_FILENAME) -> bytes:
	try:
		tokens, encoding = tokenize(s)
		tokens = list(tokens)
	except tokenize_.TokenError as ex:
		message, (lineno, offset) = ex.args

		try:
			source_line = s.splitlines()[lineno-2]
		except IndexError:
			source_line = None

		raise SyntaxError(message, (filename, lineno-1, offset, source_line)) from None

	transformed = transform_tokens(tokens)
	return tokenize_.untokenize(transformed).decode(encoding)

def offset_token_horizontal(tok: tokenize_.TokenInfo, offset: int) -> tokenize_.TokenInfo:
	"""Takes a token and returns a new token with the columns for start and end offset by a given amount."""

	start_row, start_col = tok.start
	end_row, end_col = tok.end
	return tok._replace(start=(start_row, start_col + offset), end=(end_row, end_col + offset))

def offset_line_horizontal(
	tokens: typing.List[tokenize_.TokenInfo],
	start_index: int = 0,
	*,
	line: int,
	offset: int,
) -> None:
	"""Takes a list of tokens and changes the offset of some of the tokens in place."""

	for i, tok in enumerate(tokens[start_index:], start=start_index):
		if tok.start[0] != line:
			break
		tokens[i] = offset_token_horizontal(tok, offset)

def transform_tokens(tokens: typing.Iterable[tokenize_.TokenInfo]) -> typing.List[tokenize_.TokenInfo]:
	"""Find the inline import expressions in a list of tokens and replace the relevant tokens to wrap the imported
	modules with a call to MARKER.

	Later, the AST transformer step will replace those with valid import expressions.
	"""

	orig_tokens = list(tokens)
	new_tokens: typing.List[tokenize_.TokenInfo] = []

	for orig_i, tok in enumerate(orig_tokens):
		# "!" is only an OP in >=3.12.
		if tok.type in {tokenize_.OP, tokenize_.ERRORTOKEN} and tok.string == IMPORT_OP:
			has_invalid_syntax = False

			# Collect all name and attribute access-related tokens directly connected to the "!".
			last_place = len(new_tokens)
			looking_for_name = True

			for old_tok in reversed(new_tokens):
				if old_tok.exact_type != (tokenize_.NAME if looking_for_name else tokenize_.DOT):
					# The "!" was placed somewhere in a class definition, e.g. "class Fo!o: pass".
					has_invalid_syntax = (old_tok.exact_type == tokenize_.NAME and old_tok.string == "class")

					# There's a name immediately following "!". Might be a f-string conversion flag
					# like "f'{thing!r}'" or just something invalid like "def fo!o(): pass".
					try:
						peek = orig_tokens[orig_i + 1]
					except IndexError:
						pass
					else:
						has_invalid_syntax = (has_invalid_syntax or peek.type == tokenize_.NAME)

					break

				last_place -= 1
				looking_for_name = not looking_for_name

			# The "!" is just by itself or in a bad spot. Let it error later if it's wrong.
			# Also allows other token transformers to work with it without erroring early.
			if has_invalid_syntax or last_place == len(new_tokens):
				new_tokens.append(tok)
				continue

			# Insert a call to the MARKER just before the inline import expression.
			old_first = new_tokens[last_place]
			old_f_row, old_f_col = old_first.start

			new_tokens[last_place:last_place] = [
				old_first._replace(type=tokenize_.NAME, string=MARKER, end=(old_f_row, old_f_col + len(MARKER))),
				tokenize_.TokenInfo(
					tokenize_.OP,
					"(",
					(old_f_row, old_f_col + len(MARKER)),
					(old_f_row, old_f_col + len(MARKER)+1),
					old_first.line,
				),
			]

			# Adjust the positions of the following tokens within the inline import expression.
			new_tokens[last_place + 2:] = (offset_token_horizontal(tok, len(MARKER)+1) for tok in new_tokens[last_place + 2:])

			# Add a closing parenthesis.
			(end_row, end_col) = new_tokens[-1].end
			line = new_tokens[-1].line
			end_paren_token = tokenize_.TokenInfo(tokenize_.OP, ")", (end_row, end_col), (end_row, end_col + 1), line)
			new_tokens.append(end_paren_token)

			# Fix the positions of the rest of the tokens on the same line.
			fixed_line_tokens: typing.List[tokenize_.TokenInfo] = []
			offset_line_horizontal(orig_tokens, orig_i, line=new_tokens[-1].start[0], offset=len(MARKER)+1)

			# Check the rest of the line for inline import expressions.
			new_tokens.extend(transform_tokens(fixed_line_tokens))

		else:
			new_tokens.append(tok)

	# Hack to get around a bug where code that ends in a comment, but no newline, has an extra
	# NEWLINE token added in randomly. This patch wasn't backported to 3.8.
	# https://github.com/python/cpython/issues/79288
	# https://github.com/python/cpython/issues/88833
	if sys.version_info < (3, 9):
		if len(new_tokens) >= 4 and (
			new_tokens[-4].type == tokenize_.COMMENT
			and new_tokens[-3].type == tokenize_.NL
			and new_tokens[-2].type == tokenize_.NEWLINE
			and new_tokens[-1].type == tokenize_.ENDMARKER
		):
			del new_tokens[-2]

	return new_tokens

def tokenize(source) -> (str, str):
	if isinstance(source, str):
		source = source.encode('utf-8')
	stream = io.BytesIO(source)
	encoding, _ = tokenize_.detect_encoding(stream.readline)
	stream.seek(0)
	return tokenize_.tokenize(stream.readline), encoding
