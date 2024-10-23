# Copyright © io mintz <io@mintz.cc>
# Copyright © Thanos <111999343+Sachaa-Thanasius@users.noreply.github.com>

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

# This file primarily consists of code vendored from the CPython standard library.
# It is used under the Python Software Foundation License Version 2.
# See LICENSE for details.

import __future__
import ast
import asyncio
import atexit
import code
import codeop
import concurrent.futures
import contextlib
import contextvars
import importlib
import inspect
import os.path
import rlcompleter
import sys
import traceback
import threading
import tokenize
import types
import warnings
from asyncio import futures
from codeop import PyCF_DONT_IMPLY_DEDENT, PyCF_ALLOW_INCOMPLETE_INPUT

import import_expression
from import_expression import constants

features = [getattr(__future__, fname) for fname in __future__.all_feature_names]

from ast import PyCF_ALLOW_TOP_LEVEL_AWAIT

class ImportExpressionCommandCompiler(codeop.CommandCompiler):
	def __init__(self):
		super().__init__()
		self.compiler = ImportExpressionCompile()

# this must be vendored as codeop.Compile is hardcoded to use builtins.compile
class ImportExpressionCompile:
	"""Instances of this class behave much like the built-in compile
	function, but if one is used to compile text containing a future
	statement, it "remembers" and compiles all subsequent program texts
	with the statement in force."""
	def __init__(self):
		self.flags = PyCF_DONT_IMPLY_DEDENT | PyCF_ALLOW_INCOMPLETE_INPUT

	def __call__(self, source, filename, symbol, **kwargs):
		flags = self.flags
		if kwargs.get('incomplete_input', True) is False:
			flags &= ~PyCF_DONT_IMPLY_DEDENT
			flags &= ~PyCF_ALLOW_INCOMPLETE_INPUT
		codeob = import_expression.compile(source, filename, symbol, flags, True)
		for feature in features:
			if codeob.co_flags & feature.compiler_flag:
				self.flags |= feature.compiler_flag
		return codeob

class ImportExpressionInteractiveConsole(code.InteractiveConsole):
	def __init__(self, locals=None, filename='<console>'):
		super().__init__(locals, filename)
		self.compile = ImportExpressionCommandCompiler()

# we must vendor this class because it creates global variables that the main code depends on
class ImportExpressionAsyncIOInteractiveConsole(ImportExpressionInteractiveConsole):
	def __init__(self, locals, loop):
		super().__init__(locals)
		self.loop = loop
		self.locals.update(dict(asyncio=asyncio, loop=loop))
		self.compile.compiler.flags |= PyCF_ALLOW_TOP_LEVEL_AWAIT

		self.loop = loop
		self.context = contextvars.copy_context()

	def runcode(self, code):
		global return_code
		future = concurrent.futures.Future()

		def callback():
			global return_code
			global repl_future
			global repl_future_interrupted

			repl_future = None
			repl_future_interrupted = False

			func = types.FunctionType(code, self.locals)
			try:
				coro = func()
			except SystemExit as se:
				return_code = se.code
				self.loop.stop()
				return
			except KeyboardInterrupt as ex:
				repl_future_interrupted = True
				future.set_exception(ex)
				return
			except BaseException as ex:
				future.set_exception(ex)
				return

			if not inspect.iscoroutine(coro):
				future.set_result(coro)
				return

			try:
				repl_future = self.loop.create_task(coro, context=self.context)
				futures._chain_future(repl_future, future)
			except BaseException as exc:
				future.set_exception(exc)

		self.loop.call_soon_threadsafe(callback, context=self.context)

		try:
			return future.result()
		except SystemExit as se:
			return_code = se.code
			self.loop.stop()
			return
		except BaseException:
			if repl_future_interrupted:
				self.write("\nKeyboardInterrupt\n")
			else:
				self.showtraceback()

class REPLThread(threading.Thread):
	def __init__(self, interact_kwargs):
		self.interact_kwargs = interact_kwargs
		super().__init__()

	def run(self):
		try:
			if startup_path := os.getenv("PYTHONSTARTUP"):
				with tokenize.open(startup_path) as f:
					startup_code = compile(f.read(), startup_path, "exec")
					exec(startup_code, console.locals)

			console.interact(**self.interact_kwargs)
		finally:
			warnings.filterwarnings(
				'ignore',
				message=r'^coroutine .* was never awaited$',
				category=RuntimeWarning,
			)

			loop.call_soon_threadsafe(loop.stop)

class ImportExpressionCompleter(rlcompleter.Completer):
	def attr_matches(self, text):
		# hack to help ensure valid syntax
		mod_names = import_expression.find_imports(text.rstrip().rstrip('.'))
		if not mod_names:
			return super().attr_matches(text)
		mod_name = mod_names[0]
		mod_name_with_import_op = mod_name + constants.IMPORT_OP
		# don't import the module in our current namespace, otherwise tab completion would also have side effects
		old_namespace = self.namespace
		# __import__ is used instead of importlib.import_module
		# because __import__ is designed for updating module-level globals, which we are doing.
		# Specifically, __import__('x.y') returns x, which is necessary for tab completion.
		mod = __import__(mod_name)
		self.namespace = {mod.__name__: mod}
		res = [
			# this is a hack because it also replaces non-identifiers
			# however, readline / rlcompleter only operates on identifiers so it's OK i guess
			# we need to replace so that the tab completions all have the correct prefix
			match.replace(mod_name, mod_name_with_import_op, 1)
			for match
			in super().attr_matches(text.replace(mod_name_with_import_op, mod_name))
		]
		self.namespace = old_namespace
		return res

def asyncio_main(repl_locals, interact_kwargs):
	global console
	global loop
	global repl_future
	global repl_future_interrupted

	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)

	console = ImportExpressionAsyncIOInteractiveConsole(repl_locals, loop)

	repl_future = None
	repl_future_interrupted = False

	repl_thread = REPLThread(interact_kwargs)
	repl_thread.daemon = True
	repl_thread.start()

	while True:
		try:
			loop.run_forever()
		except KeyboardInterrupt:
			repl_future_interrupted = True
			if repl_future and not repl_future.done():
				repl_future.cancel()
			continue
		else:
			break

	return return_code

def parse_args():
	import argparse

	version_info = (
		f'Import Expression Parser {import_expression.__version__}\n'
		f'Python {sys.version}'
	)

	parser = argparse.ArgumentParser(prog='import-expression', description='a python REPL with inline import support')
	parser.add_argument('-q', '--quiet', action='store_true', help='hide the intro banner and exit message')
	parser.add_argument('-a', '--asyncio', action='store_true', help='use the asyncio REPL (python 3.8+)')
	parser.add_argument('-i', dest='interactive', action='store_true', help='inspect interactively after running script')
	parser.add_argument('-V', '--version', action='version', version=version_info)
	parser.add_argument('filename', help='run this file', nargs='?')

	return parser.parse_args()

def setup_history_and_tab_completion(locals):
	try:
		import readline
		import site
		import rlcompleter
	except ImportError:
		# readline is not available on all platforms
		return

	try:
		# set up history
		sys.__interactivehook__()
	except AttributeError:
		# site has not set __interactivehook__ because python was run without site packages
		return

	# allow completion of text containing an import op (otherwise it is treated as a word boundary)
	readline.set_completer_delims(readline.get_completer_delims().replace(constants.IMPORT_OP, ''))
	# inform tab completion of what variables were set at the REPL
	readline.set_completer(ImportExpressionCompleter(locals).complete)

def main():
	cwd = os.getcwd()
	if cwd not in sys.path:
		# if invoked as a script, the user would otherwise not be able to import modules from the cwd,
		# which would be inconsistent with `python -m import_expression`.
		sys.path.insert(0, cwd)

	repl_locals = {
		key: globals()[key] for key in [
			'__name__', '__package__',
			'__loader__', '__spec__',
			'__builtins__', '__file__'
		]
		if key in globals()
	}

	args = parse_args()

	prelude = None
	if args.filename:
		with open(args.filename) as f:
			flags = 0
			if args.asyncio:
				flags |= PyCF_ALLOW_TOP_LEVEL_AWAIT
			prelude = import_expression.compile(f.read(), flags=flags)
		if args.asyncio:
			# we need a new loop because using asyncio.run here breaks the console
			loop = asyncio.new_event_loop()
			loop.run_until_complete(eval(prelude, repl_locals))
		else:
			import_expression.exec(prelude, globals=repl_locals)
		if not args.interactive:
			sys.exit(0)

	setup_history_and_tab_completion(repl_locals)

	interact_kwargs = dict(banner='' if args.quiet else None, exitmsg='' if args.quiet else None)

	if args.asyncio:
		sys.exit(asyncio_main(repl_locals, interact_kwargs))

	ImportExpressionInteractiveConsole(repl_locals).interact(**interact_kwargs)

if __name__ == '__main__':
	main()
