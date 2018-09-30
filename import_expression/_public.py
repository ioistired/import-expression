import ast as _ast
import builtins as _builtins
import importlib as _importlib
import inspect as _inspect

from . import _constants
from ._syntax import fix_syntax as _fix_syntax  # this is for internal use
from ._parser import parse_ast as _parse_ast

def parse(source: str, *, mode='eval', filename=_constants.DEFAULT_FILENAME):
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
	return _parse_ast(tree, source=fixed)

def compile(source: str, filename=_constants.DEFAULT_FILENAME, mode='eval'):
	"""compile a string containing import expressions to a code object"""
	return compile(parse(source, filename=filename, mode=mode), filename, mode)

def eval(source: str, globals=None, locals=None):
	"""evaluate Import Expression Python™ in the given globals and locals"""
	globals, locals = _parse_eval_exec_args(globals, locals)
	return _builtins.eval(compile(source), globals, locals)

def exec(source, globals=None, locals=None):
	"""execute Import Expression Python™ in the given globals and locals

	Note: unlike :func:`exec`, the default globals are *not* the caller's globals!
	This is due to a python limitation.
	Therefore, if no globals are provided, the results will be discarded!
	"""
	globals, locals = _parse_eval_exec_args(globals, locals)
	_builtins.eval(compile(parse(source, mode='exec'), _constants.DEFAULT_FILENAME,'exec'), globals, locals)

def _parse_eval_exec_args(globals, locals):
	if globals is None:  # can't use truthiness because {} is falsy
		globals = {}

	globals.update({
		_constants.IMPORTER: _importlib.import_module})

	if locals is None:
		locals = globals

	return globals, locals
