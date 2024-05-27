# Copyright © io mintz <io@mintz.cc>

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

import contextlib
import os
import textwrap

import pytest

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

@pytest.mark.parametrize('valid', [f'"{invalid}"' for invalid in invalid_attribute_cases])
def test_valid_string_literals(valid):
	ie.compile(valid)

@pytest.mark.parametrize('invalid', invalid_attribute_cases)
def test_invalid_attribute_syntax(invalid):
	with pytest.raises(SyntaxError):
		ie.compile(invalid)

def test_import_op_as_attr_name():
	with pytest.raises(SyntaxError):
		ie.compile('a.!.b')

del_store_import_tests = []
for test in (
	'a!.b',
	'a.b.c!.d',
):
	del_store_import_tests.append(f'del {test}')
	del_store_import_tests.append(f'{test} = 1')

@pytest.mark.parametrize('test', del_store_import_tests)
def test_del_store_import(test):
	ie.compile(test)

invalid_del_store_import_tests = []
for test in (
	'a!',
	'a.b!',
):
	invalid_del_store_import_tests.append(f'del {test}')
	invalid_del_store_import_tests.append(f'{test} = 1')

@pytest.mark.parametrize('test', invalid_del_store_import_tests)
def test_invalid_del_store_import(test):
	with pytest.raises((
		ValueError,  # raised by builtins.compile
		SyntaxError,  # ie.parse
	)):
		ie.compile(test)

def test_lone_import_op():
	with pytest.raises(SyntaxError):
		ie.compile('!')

@pytest.mark.parametrize('invalid', (
	'def foo(x!): pass',
	'def foo(*x!): pass',
	'def foo(**y!): pass',
	'def foo(*, z!): pass',
	# note space around equals sign:
	# class Y(Z!=1) is valid if Z.__ne__ returns a class
	'class Y(Z! = 1): pass',
))
def test_invalid_argument_syntax(invalid):
	with pytest.raises(SyntaxError):
		ie.compile(invalid)

@pytest.mark.parametrize('invalid', (
	'def !foo(y): pass',
	'def fo!o(y): pass',
	'def foo!(y): pass',
	'class X!: pass',
	'class Fo!o: pass'
	'class !Foo: pass',
	# note space around equals sign:
	# class Y(Z!=1) is valid if Z.__ne__ returns a class
	'class Y(Z! = 1): pass',
))
def test_invalid_def_syntax(invalid):
	with pytest.raises(SyntaxError):
		ie.compile(invalid)

def test_del_store_attribute():
	class AttributeBox:
		pass

	x = AttributeBox()
	g = dict(x=x)

	ie.exec('x.y = 1', g)
	assert x.y == 1

	ie.exec('del x.y', g)
	assert not hasattr(x, 'y')

def test_kwargs():
	# see issue #1
	ie.compile('f(**a)', mode='eval')

	import collections
	assert ie.eval('dict(x=collections!)')['x'] is collections

@pytest.mark.parametrize(('stmt', 'annotation_var'), (
	('def foo() -> typing!.Any: pass', 'return'),
	('def foo(x: typing!.Any): pass', 'x'),
	('def foo(x: typing!.Any = 1): pass', 'x'),
))
def test_typehint_conversion(stmt, annotation_var):
	from typing import Any
	g = {}
	ie.exec(stmt, g)
	assert g['foo'].__annotations__[annotation_var] is Any

def test_comments():
	ie.exec('# a')

@pytest.mark.parametrize('invalid', (
	'import x!',
	'import x.y!',
	'import x!.y!',
	'from x!.y import z',
	'from x.y import z!',
	'from w.x import y as z!',
	'from w.x import y as z, a as b!',
))
def test_import_statement(invalid):
	with pytest.raises(SyntaxError):
		ie.compile(invalid, mode='exec')

def test_eval_exec():
	import ipaddress
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

			bar.x = 1  # ensure normal attribute syntax is untouched

			# the hanging indent on the following line is intentional
			

			return bar()
	"""), g)

	assert g['foo'](1) == 'can we make it into jishaku?'

def test_flags():
	import ast
	assert isinstance(ie.compile('foo', flags=ast.PyCF_ONLY_AST), ast.AST)

def test_eval_code_object():
	import collections
	code = ie.compile('collections!.Counter', '', 'eval')
	assert ie.eval(code) is collections.Counter

def test_exec_code_object():
	import collections
	code = ie.compile('def foo(): return collections!.Counter', '', 'exec')
	g = {}
	ie.exec(code, globals=g)
	assert g['foo']() is collections.Counter

@pytest.mark.parametrize('invalid', (')', '"'))
def test_normal_invalid_syntax(invalid):
	"""ensure regular syntax errors are still caught"""
	with pytest.raises(SyntaxError):
		ie.compile(invalid)

def test_dont_imply_dedent():
	from codeop import PyCF_DONT_IMPLY_DEDENT
	with pytest.raises(SyntaxError):
		ie.compile('def foo():\n\tpass', mode='single', flags=PyCF_DONT_IMPLY_DEDENT)

def test_transform_ast():
	from typing import Any
	node = ie.parse(ie.parse('typing!.Any', mode='eval'))
	assert ie.eval(node) is Any

def test_locals_arg():
	ie.exec('assert locals() is globals()', {})
	ie.exec('assert locals() is not globals()', {}, {})

def test_bytes():
	import typing
	assert ie.eval(b'typing!.TYPE_CHECKING') == typing.TYPE_CHECKING

def test_beat_is_gay():
	with pytest.raises(SyntaxError):
		ie.compile('"beat".succ!')
