import ast

from .constants import *

parse_ast = lambda root_node, **kwargs: ast.fix_missing_locations(Transformer(**kwargs).visit(root_node))

def remove_string_right(haystack, needle):
	left, needle, right = haystack.rpartition(needle)
	if not right:
		return left
	return haystack

remove_import_op = lambda name: remove_string_right(name, MARKER)
has_invalid_import_op = lambda name: MARKER in remove_import_op(name)
has_import_op = lambda name: name.endswith(MARKER) and remove_import_op(name)

def _tokenize(s):
	return tokenize.tokenize(io.BytesIO(s.encode('utf-8')).readline)

_load = ast.Load()  # optimization

class Transformer(ast.NodeTransformer):
	def __init__(self, *, source=None):
		self.source = source

	def visit_Attribute(self, node):
		attr = has_import_op(node.attr)
		if attr:
			node.attr = attr
			as_source = self.attribute_source(node)
			if type(node.ctx) is not ast.Load:
				return node

			return ast.copy_location(
				self.import_call(as_source),
				node)
		else:
			transformed_lhs = self.visit(node.value)
			return ast.copy_location(
				ast.Attribute(
					value=transformed_lhs,
					ctx=_load,
					attr=node.attr),
				node)

	@classmethod
	def attribute_source(cls, node: ast.Attribute, _seen_import_op=False):
		is_import = cls.has_import_op(node)
		cls._check_node_syntax(node, is_import, _seen_import_op)

		stripped = cls.remove_import_op(node)
		if type(node) is ast.Name:
			return stripped

		lhs = cls.attribute_source(node.value, is_import or _seen_import_op)
		rhs = stripped

		return lhs + '.' + rhs

	@classmethod
	def _check_node_syntax(cls, node, is_import, seen_import_op):
		if is_import and seen_import_op:
			raise SyntaxError('multiple import expressions not allowed')

		if cls.has_invalid_import_op(node):
			raise SyntaxError(f'"{IMPORT_OP} only allowed at end of attribute name')

	@staticmethod
	def strip_import_op(s):
		seen_import_op = False
		attrs = []
		for attr in s.split('.'):
			stripped = has_import_op(attr)

			if has_invalid_import_op(attr):
				raise SyntaxError(f'"{IMPORT_OP} only allowed at end of attribute name')

			if stripped and seen_import_op:
				raise SyntaxError('multiple import expressions not allowed')
			elif stripped:
				seen_import_op = True
				attr = stripped

			attrs.append(attr)
		return attrs

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

	has_import_op = _call_on_name_or_attribute(has_import_op)
	remove_import_op = _call_on_name_or_attribute(remove_import_op)
	has_invalid_import_op = _call_on_name_or_attribute(has_invalid_import_op)
	name_or_attribute = _call_on_name_or_attribute(lambda x: x)

	del _call_on_name_or_attribute

	@staticmethod
	def import_call(attribute_source):
		return ast.Call(
			func=ast.Name(id=IMPORTER, ctx=_load),
			args=[ast.Str(attribute_source)],
			keywords=[])
