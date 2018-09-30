#!/usr/bin/env python3
# encoding: utf-8

import builtins
import os
import sys
import warnings

from . import eval as ie_eval
from ._syntax import TokenError

def patch():
	"""monkey patch sys.excepthook so that import expressions work at the repl"""
	if not _isatty():
		warnings.warn('Patching outside of the REPL is not recommended')

	original_excepthook = sys.excepthook

	def excepthook(type, error, traceback):
		if (
			type is not SyntaxError
			or error.lineno != 1  # we don't have all the code
		):
			return original_excepthook(type, error, traceback)

		try:
			result = ie_eval(error.text)
		except TokenError as ex:
			# this is our error, so don't display it to the user
			return original_excepthook(type, error, traceback)
		except BaseException as ex:
			return original_excepthook(type(ex), ex, ex.__traceback__)
		else:
			builtins._ = result
			print(repr(result))

	sys.excepthook = excepthook

def _isatty():
	return os.isatty(sys.stdin.fileno())
