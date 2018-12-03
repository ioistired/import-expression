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

import ast as _ast
import builtins as _builtins
import contextlib as _contextlib
import importlib as _importlib
import inspect as _inspect
import typing as _typing

from . import constants
from ._syntax import fix_syntax as _fix_syntax
from ._parser import parse_ast as parse_ast
from .version import __version__

with _contextlib.suppress(NameError):
	del version

__all__ = ('compile', 'parse', 'eval', 'exec', 'constants')

def parse(source: str, *, mode='eval', filename=constants.DEFAULT_FILENAME):
	"""
	convert Import Expression Python™ to an AST

	Keyword arguments:
	mode: determines the type of the returned root node.
	As in the mode argument of :func:`ast.parse`,
	it must be one of "eval" or "exec".
	Eval mode returns an :class:`ast.Expression` object. Source must represent a single expression.
	Exec mode returns a :class:` Module` object. Source represents zero or more statements.

	Filename is used in tracebacks, in case of invalid syntax or runtime exceptions.
	"""
	fixed = _fix_syntax(source)
	tree = _ast.parse(fixed, filename, mode)
	return parse_ast(tree, filename=filename)

def compile(source: _typing.Union[_ast.AST, str], filename=constants.DEFAULT_FILENAME, mode='eval'):
	"""compile a string or AST containing import expressions to a code object"""
	if isinstance(source, str):
		source = parse(source, filename=filename, mode=mode)

	return _builtins.compile(source, filename, mode)

def eval(source: str, globals=None, locals=None):
	"""evaluate Import Expression Python™ in the given globals and locals"""
	globals, locals = _parse_eval_exec_args(globals, locals)
	return _builtins.eval(compile(source, constants.DEFAULT_FILENAME, 'eval'), globals, locals)

def exec(source, globals=None, locals=None):
	"""execute Import Expression Python™ in the given globals and locals

	Note: unlike :func:`exec`, the default globals are *not* the caller's globals!
	This is due to a python limitation.
	Therefore, if no globals are provided, the results will be discarded!
	"""
	globals, locals = _parse_eval_exec_args(globals, locals)
	_builtins.eval(compile(source, constants.DEFAULT_FILENAME, 'exec'), globals, locals)

def _parse_eval_exec_args(globals, locals):
	if globals is None:  # can't use truthiness because {} is falsy
		globals = {}

	globals.update({
		constants.IMPORTER: _importlib.import_module})

	if locals is None:
		locals = globals

	return globals, locals
