import py.test

import import_expression_parser as iep

def test_invalid_syntax():
	for invalid in (
		'!foo',
		'foo!.bar!',
		'foo.bar!.baz!',
		'foo.bar!.baz',
	):
		with py.test.raises(SyntaxError):
			iep.parse(invalid)

def test_eval():
	import builtins
	import importlib
	import textwrap

	_G = dict(__import_module=importlib.import_module)
	globals = _G.copy

	def eval(str):
		return builtins.eval(iep.parse(str, include_import_statement=False), globals())

	import ipaddress
	assert eval('ipaddress!.IPV6LENGTH') == ipaddress.IPV6LENGTH
	assert eval('urllib.parse!.quote("!")') == '%3F'

	g = {}
	exec(iep.parse(textwrap.dedent("""
		def foo():
			return urllib.parse!.unquote('%3F')
		def bar():
			return operator!.concat(foo(), "these_tests_are_overkill_for_a_debug_cog%3D1")"""
	)), g)

	assert g['bar']() == '?these_tests_are_overkill_for_a_debug_cog=1'
