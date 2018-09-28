import builtins

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
	import textwrap

	import ipaddress
	assert iep.eval('ipaddress!.IPV6LENGTH') == ipaddress.IPV6LENGTH
	assert iep.eval('urllib.parse!.quote("?")') == '%3F'

	g = {}
	iep.exec(textwrap.dedent("""
		def a():
			return urllib.parse!.unquote('%3F')
		def c():
			return operator!.concat(a(), "these_tests_are_overkill_for_a_debug_cog%3D1")"""
	), g)

	assert g['c']() == '?these_tests_are_overkill_for_a_debug_cog=1'
