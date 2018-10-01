#!/usr/bin/env python3
# encoding: utf-8

import builtins
import contextlib
import inspect
import os
import sys

from . import _public as import_expression

def patch(globals=sys.modules['__main__'].__dict__):
	"""monkey patch sys.excepthook so that import expressions work at the repl

	If a line has a syntax error, import_expression.eval is attempted on it.
	If this also results in a syntax error, import_eval.exec will be run instead.
	Both cases will run in the context of the given globals dict, or if None, globals produced by statements will be saved to the __main__ module
	"""
	if not _is_tty():
		raise RuntimeError(f'patch() only works at the REPL, where stdin is a TTY.')

	sys.excepthook = _make_excepthook(globals)

def _make_excepthook(globals):
	def excepthook(_, error, __):
		if (
			type(error) is not SyntaxError
			or error.lineno != 1  # we don't have all the code
		):
			return sys.__excepthook__(type(error), error, error.__traceback__)

		try:
			result = import_expression.eval(error.text, globals)
		except SyntaxError:
			try:
				import_expression.exec(error.text, globals)
			except SyntaxError:
				# it must be invalid Python syntax, not invalid import expr syntax
				return sys.__excepthook__(type(error), error, error.__traceback__)
		except SyntaxError:
			return sys.__excepthook__(type(error), error, error.__traceback__)
		except BaseException as error:
			return sys.__excepthook__(type(error), error, error.__traceback__)
		else:
			if result is None:
				return

			builtins._ = result
			print(repr(result))

	return excepthook

def _is_tty():
	return os.isatty(sys.stdin.fileno())
