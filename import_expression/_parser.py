# encoding: utf-8

# Copyright © 2018 Benjamin Mintz <bmintz@protonmail.com>

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

from .constants import *

parse_ast = lambda root_node, **kwargs: ast.fix_missing_locations(Transformer(**kwargs).visit(root_node))

def remove_string_right(haystack, needle):
	left, needle, right = haystack.rpartition(needle)
	if not right:
		return left
	# needle not found
	return haystack

remove_import_op = lambda name: remove_string_right(name, MARKER)
has_any_import_op = lambda name: MARKER in name
has_invalid_import_op = lambda name: MARKER in remove_import_op(name)
has_valid_import_op = lambda name: name.endswith(MARKER) and remove_import_op(name)

class Transformer(ast.NodeTransformer):
	def __init__(self, *, filename=None):
		self.filename = filename

	def visit_Attribute(self, node):
		"""
		convert Attribute nodes containing import expressions into Attribute nodes containing import calls
		"""
		not_to_be_transformed = self._check_node_syntax(node)
		if not_to_be_transformed:
			return not_to_be_transformed

		maybe_transformed = self._transform_attribute_attr(node)
		if maybe_transformed:
			return maybe_transformed
		else:
			transformed_lhs = self.visit(node.value)
			return ast.copy_location(
				ast.Attribute(
					value=transformed_lhs,
					ctx=node.ctx,
					attr=node.attr),
				node)

	def visit_Name(self, node):
		"""convert solitary Names that have import expressions, such as "a!", into import calls"""
		not_to_be_transformed = self._check_node_syntax(node)
		if not_to_be_transformed:
			return not_to_be_transformed

		is_import = id = has_valid_import_op(node.id)
		if is_import:
			return ast.copy_location(self._import_call(id, node.ctx), node)
		return node

	@staticmethod
	def _import_call(attribute_source, ctx):
		return ast.Call(
			func=ast.Name(id=IMPORTER, ctx=ctx),
			args=[ast.Str(attribute_source)],
			keywords=[])

	def _transform_attribute_attr(self, node):
		"""convert an Attribute node's left hand side into an import call"""

		attr = is_import = has_valid_import_op(node.attr)

		if not is_import:
			return None

		node.attr = attr
		as_source = self.attribute_source(node)

		return ast.copy_location(
			self._import_call(as_source, node.ctx),
			node)

	def attribute_source(self, node: ast.Attribute, _seen_import_op=False):
		"""return a source-code representation of an Attribute node"""

		is_import = self._has_valid_import_op(node)
		if is_import and _seen_import_op:
			raise self._syntax_error('multiple import expressions not allowed', node) from None

		stripped = self._remove_import_op(node)
		if type(node) is ast.Name:
			return stripped

		lhs = self.attribute_source(node.value, is_import or _seen_import_op)
		rhs = stripped

		return lhs + '.' + rhs

	def visit_def_(self, node):
		if not has_any_import_op(node.name):
			# it's valid so far, just ensure that arguments are also visited
			return self.generic_visit(node)

		if isinstance(node, ast.ClassDef):
			type_name = 'class'
		else:
			type_name = 'function'

		raise self._syntax_error(
			f'"{IMPORT_OP}" not allowed in the name of a {type_name}',
			node
		) from None

	visit_FunctionDef = visit_def_
	visit_ClassDef = visit_def_

	def visit_arg(self, node):
		"""ensure foo(x!=1) or def foo(x!) does not occur"""
		if has_any_import_op(node.arg):
			raise self._syntax_error(
				f'"{IMPORT_OP}" not allowed in function arguments',
				node
			) from None

		return node

	visit_keyword = visit_arg

	def _check_node_syntax(self, node):
		if self._import_expression_candidate(node):
			self._ensure_only_valid_import_ops(node)
			return None  # to indicate that the node needs further processing
		else:
			self._ensure_no_import_ops(node)
			return node  # node is fine as-is

	def _import_expression_candidate(self, node):
		return isinstance(node, (ast.Attribute, ast.Name))

	def _ensure_only_valid_import_ops(self, node):
		if self._for_any_child_node_string(has_invalid_import_op, node):
			raise self._syntax_error(
				f'"{IMPORT_OP}" only allowed at end of attribute name',
				node
			) from None

	def _ensure_no_import_ops(self, node):
		if self._for_any_node_string(has_any_import_op, node):
			raise self._syntax_error(
				'import expressions are only allowed in variables and attributes',
				node
			) from None

	@classmethod
	def _for_any_child_node_string(cls, predicate, node):
		for child_node in ast.walk(node):
			if cls._for_any_node_string(predicate, node):
				return True

		return False

	@staticmethod
	def _for_any_node_string(predicate, node):
		for field, value in ast.iter_fields(node):
			if isinstance(value, str) and predicate(value):
				return True

		return False

	def _call_on_name_or_attribute(func):
		def checker(node):
			if type(node) is ast.Attribute:
				to_check = node.attr
			elif type(node) is ast.Name:
				to_check = node.id
			else:
				raise TypeError(f'node must be an Attribute or Name node, not {type(node)}')
			return func(to_check)

		return staticmethod(checker)

	_has_valid_import_op = _call_on_name_or_attribute(has_valid_import_op)
	_remove_import_op = _call_on_name_or_attribute(remove_import_op)
	_has_invalid_import_op = _call_on_name_or_attribute(has_invalid_import_op)

	del _call_on_name_or_attribute

	def _syntax_error(self, message, node):
		# last two items in the tuple are column offset and source code text
		return SyntaxError(message, (self.filename, getattr(node, 'lineno', None), None, None))
