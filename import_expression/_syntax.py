# Copyright © 2018–2019 Io Mintz <io@mintz.cc>

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

import collections
import io
import re
import string
import tokenize as tokenize_
from codeop import PyCF_DONT_IMPLY_DEDENT
from token import *
# TODO only import what we need
vars().update({k: v for k, v in vars(tokenize_).items() if not k.startswith('_')})

from .constants import *

tokenize_.TokenInfo.value = property(lambda self: self.string)

is_import = lambda token: token.type == tokenize_.ERRORTOKEN and token.string == IMPORT_OP

NEWLINES = {NEWLINE, tokenize_.NL}

def fix_syntax(s: str, flags=0, filename=DEFAULT_FILENAME) -> bytes:
	imply_dedent = not (flags & PyCF_DONT_IMPLY_DEDENT)
	tokens = tokenize(s, imply_dedent=imply_dedent)
	untokenizer = Untokenizer()
	try:
		out = untokenizer.untokenize(tokens)
	except tokenize_.TokenError as ex:
		message, (lineno, offset) = ex.args

		try:
			source_line = s.splitlines()[lineno-2]
		except IndexError:
			source_line = None

		raise SyntaxError(message, (filename, lineno-1, offset, source_line)) from None

	return out

# taken from Lib/tokenize.py at 3.6
# modified to support PyCF_DONT_IMPLY_DEDENT
# modified to always use unicode strings instead of bytes
def _tokenize(readline, *, imply_dedent=True):
	lnum = parenlev = continued = 0
	contstr, needcont = '', 0
	contline = None
	indents = [0]

	yield TokenInfo(ENCODING, 'utf-8', (0, 0), (0, 0), '')
	last_line = ''
	line = ''
	while True:	 # loop over lines in stream
		try:
			# We capture the value of the line variable here because
			# readline uses the empty string '' to signal end of input,
			# hence `line` itself will always be overwritten at the end
			# of this loop.
			last_line = line
			line = readline()
		except StopIteration:
			line = ''

		lnum += 1
		pos, max = 0, len(line)

		if contstr:	 # continued string
			if not line:
				raise TokenError("EOF in multi-line string", strstart)
			endmatch = endprog.match(line)
			if endmatch:
				pos = end = endmatch.end(0)
				yield TokenInfo(STRING, contstr + line[:end], strstart, (lnum, end), contline + line)
				contstr, needcont = '', 0
				contline = None
			elif needcont and line[-2:] != '\\\n' and line[-3:] != '\\\r\n':
				yield TokenInfo(ERRORTOKEN, contstr + line,
						   strstart, (lnum, len(line)), contline)
				contstr = ''
				contline = None
				continue
			else:
				contstr = contstr + line
				contline = contline + line
				continue

		elif parenlev == 0 and not continued:  # new statement
			if not line: break
			column = 0
			while pos < max:  # measure leading whitespace
				if line[pos] == ' ':
					column += 1
				elif line[pos] == '\t':
					column = (column//tabsize + 1)*tabsize
				elif line[pos] == '\f':
					column = 0
				else:
					break
				pos += 1
			if pos == max:
				break

			if line[pos] in '#\r\n':  # skip comments or blank lines
				if line[pos] == '#':
					comment_token = line[pos:].rstrip('\r\n')
					yield TokenInfo(COMMENT, comment_token, (lnum, pos), (lnum, pos + len(comment_token)), line)
					pos += len(comment_token)

				yield TokenInfo(NL, line[pos:], (lnum, pos), (lnum, len(line)), line)
				continue

			if column > indents[-1]:  # count indents or dedents
				indents.append(column)
				yield TokenInfo(INDENT, line[:pos], (lnum, 0), (lnum, pos), line)
			while column < indents[-1]:
				if column not in indents:
					raise IndentationError(
						"unindent does not match any outer indentation level",
						("<tokenize>", lnum, pos, line))
				indents = indents[:-1]

				yield TokenInfo(DEDENT, '', (lnum, pos), (lnum, pos), line)

		else:  # continued statement
			if not line:
				raise TokenError("EOF in multi-line statement", (lnum, 0))
			continued = 0

		while pos < max:
			pseudomatch = re.compile(PseudoToken).match(line, pos)
			if pseudomatch:	 # scan for tokens
				start, end = pseudomatch.span(1)
				spos, epos, pos = (lnum, start), (lnum, end), end
				if start == end:
					continue
				token, initial = line[start:end], line[start]

				if (
					initial in string.digits  # ordinary number
					or (initial == '.' and token != '.' and token != '...')
				):
					yield TokenInfo(NUMBER, token, spos, epos, line)
				elif initial in '\r\n':
					if parenlev > 0:
						yield TokenInfo(NL, token, spos, epos, line)
					else:
						yield TokenInfo(NEWLINE, token, spos, epos, line)

				elif initial == '#':
					assert not token.endswith("\n")
					yield TokenInfo(COMMENT, token, spos, epos, line)

				elif token in triple_quoted:
					endprog = re.compile(endpats[token])
					endmatch = endprog.match(line, pos)
					if endmatch:  # all on one line
						pos = endmatch.end(0)
						token = line[start:pos]
						yield TokenInfo(STRING, token, spos, (lnum, pos), line)
					else:
						strstart = (lnum, start)  # multiple lines
						contstr = line[start:]
						contline = line
						break

				# Check up to the first 3 chars of the token to see if
				#  they're in the single_quoted set. If so, they start
				#  a string.
				# We're using the first 3, because we're looking for
				#  "rb'" (for example) at the start of the token. If
				#  we switch to longer prefixes, this needs to be
				#  adjusted.
				# Note that initial == token[:1].
				# Also note that single quote checking must come after
				#  triple quote checking (above).
				elif (initial in single_quoted or
					  token[:2] in single_quoted or
					  token[:3] in single_quoted):
					if token[-1] == '\n':  # continued string
						strstart = (lnum, start)
						# Again, using the first 3 chars of the
						#  token. This is looking for the matching end
						#  regex for the correct type of quote
						#  character. So it's really looking for
						#  endpats["'"] or endpats['"'], by trying to
						#  skip string prefix characters, if any.
						endprog = re.compile(
							endpats.get(initial) or
							endpats.get(token[1]) or
							endpats.get(token[2]))
						contstr, needcont = line[start:], 1
						contline = line
						break
					else:  # ordinary string
						yield TokenInfo(STRING, token, spos, epos, line)

				elif initial.isidentifier():  # ordinary name
					yield TokenInfo(NAME, token, spos, epos, line)
				elif initial == '\\':  # continued stmt
					continued = 1
				else:
					if initial in '([{':
						parenlev += 1
					elif initial in ')]}':
						parenlev -= 1
					yield TokenInfo(OP, token, spos, epos, line)
			else:
				yield TokenInfo(ERRORTOKEN, line[pos], (lnum, pos), (lnum, pos+1), line)
				pos += 1

	# Add an implicit NEWLINE if the input doesn't end in one
	if last_line and last_line[-1] not in '\r\n':
		yield TokenInfo(NEWLINE, '', (lnum - 1, len(last_line)), (lnum - 1, len(last_line) + 1), '')
	if imply_dedent:  # the REPL uses this
		for indent in indents[1:]:	# pop remaining indent levels
			yield TokenInfo(DEDENT, '', (lnum, 0), (lnum, 0), '')
	yield TokenInfo(ENDMARKER, '', (lnum, 0), (lnum, 0), '')

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
			raise ValueError(
				"start ({},{}) precedes previous end ({},{})".format(row, col, self.prev_row, self.prev_col))

		col_offset = col - self.prev_col
		self.tokens.append(" " * col_offset)

	def untokenize(self, iterable):
		indents = []
		startline = False
		for token in iterable:
			if token.type == tokenize_.ENCODING:
				self.encoding = token.value
				continue

			if token.type == tokenize_.ENDMARKER:
				break

			# XXX this abomination comes from tokenize.py
			# i tried to move it to a separate method but failed

			if token.type == tokenize_.INDENT:
				indents.append(token.value)
				continue
			elif token.type == tokenize_.DEDENT:
				indents.pop()
				self.prev_row, self.prev_col = token.end
				continue
			elif token.type in NEWLINES:
				startline = True
			elif startline and indents:
				indent = indents[-1]
				start_row, start_col = token.start
				if start_col >= len(indent):
					self.tokens.append(indent)
					self.prev_col = len(indent)
				startline = False

			# end abomination

			self.add_whitespace(token.start)

			if is_import(token):
				self.tokens.append(MARKER)
			else:
				self.tokens.append(token.value)

			self.prev_row, self.prev_col = token.end

			# don't ask me why this shouldn't be "in NEWLINES",
			# but ignoring tokenize_.NL here fixes #3
			if token.type == NEWLINE:
				self.prev_row += 1
				self.prev_col = 0

		return "".join(self.tokens)

def tokenize(string, *, imply_dedent=True):
	return _tokenize(io.StringIO(string).readline, imply_dedent=imply_dedent)
