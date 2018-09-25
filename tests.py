import py.test

import import_expression_parser
from import_expression_parser import parse_import_expressions

def test_invalid_syntax():
	for invalid in (
		'?foo',
		'foo?.bar?',
		'foo.bar?.baz?',
		'foo.bar?.baz',
	):
		with py.test.raises(SyntaxError):
			parse_import_expressions(invalid)

def _replace_header(string):
	left, header, right = string.partition(import_expression_parser.HEADER)
	return right

def _parse(input):
	return _replace_header(parse_import_expressions(input))

imp = '__import_module'

def test_basic():
	assert _parse('x.y?.z') == f'{imp}("x.y").z'
	assert _parse('print(tokenize?.OP)') == f'print({imp}("tokenize").OP)'

def test_eval():
	import builtins
	import importlib
	import textwrap

	_G = dict(__import_module=importlib.import_module)
	globals = _G.copy

	def eval(str):
		return builtins.eval(parse_import_expressions(str, include_import_statement=False), globals())

	import ipaddress
	assert eval('ipaddress?.IPV6LENGTH') == ipaddress.IPV6LENGTH
	assert eval('urllib.parse?.quote("?")') == '%3F'

	g = {}
	exec(parse_import_expressions(textwrap.dedent("""
		def foo():
			return urllib.parse?.unquote('%3F')
		def bar():
			return operator?.concat(foo(), "these_tests_are_overkill_for_a_debug_cog%3D1")"""
	)), g)

	assert g['bar']() == '?these_tests_are_overkill_for_a_debug_cog=1'
