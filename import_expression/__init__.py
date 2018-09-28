#!/usr/bin/env python3
# encoding: utf-8

import ast as _ast
import builtins as _builtins
from importlib import import_module as _import_module

from . import constants as _constants
from .syntax import fix_syntax as _fix_syntax  # this is for internal use
from .parser import parse_ast  # we can export this tho

def parse(source, *, mode='eval', filename=_constants.DEFAULT_FILENAME):
	fixed = _fix_syntax(source)
	tree = _ast.parse(fixed, filename,  mode)
	return parse_ast(tree, source=fixed)

def eval(str, globals=None, locals=None):
	globals, locals = _parse_eval_exec_args(globals, locals)
	return _builtins.eval(compile(parse(str, mode='eval'), _constants.DEFAULT_FILENAME, 'eval'), globals, locals)

def exec(str, globals=None, locals=None):
	globals, locals = _parse_eval_exec_args(globals, locals)
	_builtins.eval(compile(parse(str, mode='exec'), _constants.DEFAULT_FILENAME, 'exec'), globals, locals)

def _parse_eval_exec_args(globals, locals):
	if globals is None:  # can't use truthiness because {} is falsy
		globals = _builtins.globals()

	globals.update({
		_constants.IMPORTER: _import_module})

	if locals is None:
		locals = globals

	return globals, locals
