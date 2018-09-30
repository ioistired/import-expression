import ast

from ._constants import *

parse_ast = lambda root_node, **kwargs: ast.fix_missing_locations(Transformer(**kwargs).visit(root_node))

def remove_string_right(haystack, needle):
	left, needle, right = haystack.rpartition(needle)
	if not right:
		return left
	# needle not found
	return haystack

remove_import_op = lambda name: remove_string_right(name, MARKER)
has_invalid_import_op = lambda name: MARKER in remove_import_op(name)
has_import_op = lambda name: name.endswith(MARKER) and remove_import_op(name)

class Transformer(ast.NodeTransformer):
	def __init__(self, *, source=None):
		self.source = source

	def visit_Attribute(self, node):
		maybe_transformed = self._transform_attribute_attr(node)
		if maybe_transformed:
			return maybe_transformed
		else:
			transformed_lhs = self.visit(node.value)
			return ast.copy_location(
				ast.Attribute(
					value=transformed_lhs,
					ctx=_load,
					attr=node.attr),
				node)

	def visit_Name(self, node):
		is_import = id = has_import_op(node.id)
		if is_import:
			return ast.copy_location(self._import_call(id), node)
		return node

	@staticmethod
	def _import_call(attribute_source):
		return ast.Call(
			func=ast.Name(id=IMPORTER, ctx=_load),
			args=[ast.Str(attribute_source)],
			keywords=[])

	@classmethod
	def _transform_attribute_attr(cls, node):
		attr = is_import = has_import_op(node.attr)

		if not is_import:
			return None

		node.attr = attr
		as_source = cls.attribute_source(node)
		if type(node.ctx) is not ast.Load:
			return node

		return ast.copy_location(
			cls._import_call(as_source),
			node)

	@classmethod
	def attribute_source(cls, node: ast.Attribute, _seen_import_op=False):
		is_import = cls._has_import_op(node)
		cls._check_node_syntax(node, is_import, _seen_import_op)

		stripped = cls._remove_import_op(node)
		if type(node) is ast.Name:
			return stripped

		lhs = cls.attribute_source(node.value, is_import or _seen_import_op)
		rhs = stripped

		return lhs + '.' + rhs

	@classmethod
	def _check_node_syntax(cls, node, is_import, seen_import_op):
		if is_import and seen_import_op:
			raise SyntaxError('multiple import expressions not allowed')

		if cls._has_invalid_import_op(node):
			raise SyntaxError(f'"{IMPORT_OP} only allowed at end of attribute name')

	def _call_on_name_or_attribute(func):
		def checker(node):
			if type(node) is ast.Attribute:
				to_check = node.attr
			elif type(node) is ast.Name:
				to_check = node.id
			else:
				raise TypeError(f'node must be an Attribute or Name node, not {type(node)}') from None
			return func(to_check)

		return staticmethod(checker)

	_has_import_op = _call_on_name_or_attribute(has_import_op)
	_remove_import_op = _call_on_name_or_attribute(remove_import_op)
	_has_invalid_import_op = _call_on_name_or_attribute(has_invalid_import_op)

	del _call_on_name_or_attribute

_load = ast.Load()  # optimization
