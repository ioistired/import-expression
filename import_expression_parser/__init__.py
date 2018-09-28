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
