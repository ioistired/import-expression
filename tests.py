import builtins

import py.test

import import_expression as ie

invalid_attribute_cases = (
	# arrange this as if ! is binary 1, empty str is 0
	'!a',

	'a.!b',
	'!a.b',
	'a!.b!',

	'a.b!.c!',
	'a!.b!.c',

	'a.b.!c',
	'a.!b.c',
	'a.!b.!c'
	'!a.b.c',
	'!a.b.!c',
	'!a.!b.c',
	'!a.!b.!c'

	'a!b',
	'ab.bc.d!e',
	'ab.b!c',
)

def test_valid_strings():
	for invalid in invalid_attribute_cases:
		valid = f'"{invalid}"'
		ie.parse(valid)

def test_invalid_attribute_syntax():
	for invalid in invalid_attribute_cases:
		print(invalid)
		with py.test.raises(SyntaxError):
			ie.parse(invalid)

def test_invalid_non_attribute_syntax():
	for invalid in (
		'def foo(x!): pass',
		'class X!: pass',
		'def fo!o(y): pass',
		'class X(Y!): pass',
	):
		with py.test.raises(SyntaxError):
			ie.parse(invalid)

def test_eval_exec():
	import collections
	import ipaddress
	import textwrap
	import urllib.parse

	assert ie.eval('ipaddress!.IPV6LENGTH') == ipaddress.IPV6LENGTH
	assert ie.eval('urllib.parse!.quote("?")') == urllib.parse.quote('?')

	g = {}
	ie.exec(textwrap.dedent("""
		a = urllib.parse!.unquote
		def b():
			return operator!.concat(a('%3F'), a('these_tests_are_overkill_for_a_debug_cog%3D1'))"""
	), g)

	assert g['b']() == '?these_tests_are_overkill_for_a_debug_cog=1'


	g = {}
	ie.exec(textwrap.dedent("""
	def foo(x):
		x = x + 1
		x = x + 1
		x = x + 1
		x = x + 1

		def bar():
			return urllib.parse!.unquote('this%20will%20never%20be%20merged%20into%20jishaku%2C%20will%20it%20%3A%28')

		# the hanging indent on the following line is intentional
		

		return bar()"""
	), g)

	assert g['foo'](1) == 'this will never be merged into jishaku, will it :('
	assert ie.eval('collections!.Counter(urllib.parse!.quote("foo"))') == dict(f=1, o=2)

	class AttributeBox:
		pass

	g = {'x': AttributeBox()}

	ie.exec('x.y = 1', g)
	assert g['x'].y == 1

	ie.exec('del x.y')
	assert not hasattr(g['x'], 'y')
