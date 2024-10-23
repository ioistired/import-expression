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

import ast
import sys
import typing
import functools
import contextlib
from collections import namedtuple
from .constants import *

T = typing.TypeVar("T")

# https://github.com/python/cpython/blob/5d04cc50e51cb262ee189a6ef0e79f4b372d1583/Objects/exceptions.c#L2438-L2441
_sec_fields = 'filename lineno offset text'.split()
if sys.version_info >= (3, 10):
	_sec_fields.extend('end_lineno end_offset'.split())

SyntaxErrorContext = namedtuple('SyntaxErrorContext', _sec_fields)

del _sec_fields

def transform_ast(root_node, **kwargs): return ast.fix_missing_locations(Transformer(**kwargs).visit(root_node))

def find_imports(root_node, **kwargs):
	t = ListingTransformer(**kwargs)
	t.visit(root_node)
	return t.imports

class Transformer(ast.NodeTransformer):
	"""An AST transformer that replaces calls to MARKER with '__import__("importlib").import_module(...)'."""

	def __init__(self, *, filename=None, source=None):
		self.filename = filename
		self.source_lines = source.splitlines() if source is not None else None

	def _collapse_attributes(self, node: typing.Union[ast.Attribute, ast.Name]) -> str:
		if isinstance(node, ast.Name):
			return node.id

		if not (
			isinstance(node, ast.Attribute)	 # pyright: ignore[reportUnnecessaryIsInstance]
			and isinstance(node.value, (ast.Attribute, ast.Name))
		):
			raise self._syntax_error(
				"Only names and attribute access (dot operator) "
				"can be within the inline import expression.",
				node,
			)	# noqa: TRY004

		return self._collapse_attributes(node.value) + f".{node.attr}"

	def visit_Call(self, node: ast.Call) -> ast.AST:
		"""Replace the import calls with a valid inline import expression."""

		if (
			isinstance(node.func, ast.Name)
			and node.func.id == MARKER
			and len(node.args) == 1
			and isinstance(node.args[0], (ast.Attribute, ast.Name))
		):
			identifier = self._collapse_attributes(node.args[0])
			self.transform_import_expr(node, identifier, node.args[0].ctx)
		return self.generic_visit(node)

	def transform_import_expr(self, node, identifier, ctx):
		node.func = ast.Attribute(
			value=ast.Call(
				func=ast.Name(id="__import__", ctx=ast.Load()),
				args=[ast.Constant(value="importlib")],
				keywords=[],
			),
			attr="import_module",
			ctx=ctx,
		)
		identifier = self._collapse_attributes(node.args[0])
		self.import_hook(identifier)
		node.args[0] = ast.Constant(value=identifier)

	def import_hook(self, identifier):
		"""defined by subclasses"""
		...

	def _syntax_error(self, message, node):
		lineno = getattr(node, 'lineno', None)
		offset = getattr(node, 'col_offset', None)
		end_lineno = getattr(node, 'end_lineno', None)
		end_offset = getattr(node, 'end_offset', None)

		text = None
		if self.source_lines is not None and lineno:
			if end_offset is None:
				sl = lineno-1
			else:
				sl = slice(lineno-1, end_lineno-1)

			with contextlib.suppress(IndexError):
				text = self.source_lines[sl]

		kwargs = dict(
			filename=self.filename,
			lineno=lineno,
			offset=offset,
			text=text,
		)
		if sys.version_info >= (3, 10):
			kwargs.update(dict(
				end_lineno=end_lineno,
				end_offset=end_offset,
			))

		return SyntaxError(message, SyntaxErrorContext(**kwargs))

class ListingTransformer(Transformer):
	"""like the parent class but lists all imported modules as self.imports"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.imports = []

	def import_hook(self, attribute_source):
		self.imports.append(attribute_source)
