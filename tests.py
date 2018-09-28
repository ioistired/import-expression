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
	assert eval('ipaddress!.IPV6LENGTH') == ipaddress.IPV6LENGTH
	assert eval('urllib.parse!.quote("!")') == '%3F'

	g = {}
	exec(textwrap.dedent("""
		def foo():
			return urllib.parse!.unquote('%3F')
		def bar():
			return operator!.concat(foo(), "these_tests_are_overkill_for_a_debug_cog%3D1")"""
	), g)

	assert g['bar']() == '?these_tests_are_overkill_for_a_debug_cog=1'

def eval(str, globals=None, locals=None):
	from importlib import import_module

	globals, locals = _parse_eval_exec_args(globals, locals)

	globals = {
		iep.IMPORTER: import_module}
	return builtins.eval(compile(iep.parse(str, include_import_header=False), '<eval test case>', 'eval'), globals)

def exec(str, globals, locals):
	builtins.exec(compile(iep.parse(str), '<exec test case>', 'exec'), globals, locals)
