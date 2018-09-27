#!/usr/bin/env python3
# encoding: utf-8

import ast as _ast
from importlib import import_module as _import_module

from . import constants as _constants
from .syntax import fix_syntax as _fix_syntax  # this is for internal use
from .parser import parse_ast  # we can export this tho

_VALID_MODES = frozenset({'eval', 'exec'})
_HUMAN_READABLE_MODES = ' or '.join(_VALID_MODES)

eval_globals = {
	_constants.IMPORTER: _import_module}.copy

def parse(source, *, mode='eval', filename=_constants.DEFAULT_FILENAME):
	if mode not in _VALID_MODES:
		raise ValueError(f'mode must be one of {_HUMAN_READABLE_MODES}')

	fixed = _fix_syntax(source, include_import_statement=mode == 'exec')
	tree = _ast.parse(fixed, filename,  mode)
	return parse_ast(tree, source=fixed)
