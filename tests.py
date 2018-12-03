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

def test_valid_string_literals():
	for invalid in invalid_attribute_cases:
		valid = f'"{invalid}"'
		print(valid)
		ie.compile(valid)

def test_invalid_attribute_syntax():
	for invalid in invalid_attribute_cases:
		print(invalid)  # in case it does not raise and we want to see what failed
		with py.test.raises(SyntaxError):
			ie.compile(invalid)

def test_del_store_import():
	for test in (
		'a!.b',
		'a.b.c!.d',
	):
		del_ = f'del {test}'
		store = f'{test} = 1'

		for test in del_, store:
			print(test)
			ie.compile(test, mode='exec')

def test_invalid_del_store_import():
	for test in (
		'a!',
		'a.b!',
	):
		del_ = f'del {test}'
		store = f'{test} = 1'
		for test in del_, store:
			print(test)
			# we use Exception instead of SyntaxError because this error may be caught
			# by builtins.compile (raises ValueError) or ie.parse (raises SyntaxError)
			with py.test.raises(Exception):
				ie.compile(test, mode='exec')

def test_invalid_argument_syntax():
	for invalid in (
		'def foo(x!): pass',
		'def foo(*x!): pass',
		'def foo(**y!): pass',
		'def foo(*, z!): pass',
		# note space around equals sign:
		# class Y(Z!=1) is valid if Z.__ne__ returns a class
		'class Y(Z! = 1): pass',
	):
		with py.test.raises(SyntaxError):
			print(invalid)
			ie.compile(invalid, mode='exec')

def test_invalid_def_syntax():
	for invalid in (
		'def !foo(y): pass',
		'def fo!o(y): pass',
		'def foo!(y): pass',
		'class X!: pass',
		'class Fo!o: pass'
		'class !Foo: pass',
	):
		# note space around equals sign:
		# class Y(Z!=1) is valid if Z.__ne__ returns a class
		'class Y(Z! = 1): pass',

def test_del_store_attribute():
	class AttributeBox:
		pass

	x = AttributeBox()
	g = dict(x=x)

	ie.exec('x.y = 1', g)
	assert x.y == 1

	ie.exec('del x.y', g)
	assert not hasattr(x, 'y')

def test_eval_exec():
	import collections
	import ipaddress
	import textwrap
	import urllib.parse

	assert ie.eval('collections!.Counter(urllib.parse!.quote("foo"))') == dict(f=1, o=2)
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
			return urllib.parse!.unquote('can%20we%20make%20it%20into%20jishaku%3F')

		# the hanging indent on the following line is intentional
		

		return bar()"""
	), g)

	assert g['foo'](1) == 'can we make it into jishaku?'
