# Copyright © 2018–2019 Io Mintz <io@mintz.cc>

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
import importlib
import inspect
import os.path
import sys
import traceback
import threading
import types
import warnings
from asyncio import futures
from codeop import PyCF_DONT_IMPLY_DEDENT

import import_expression

features = [getattr(__future__, fname) for fname in __future__.all_feature_names]

try:
	from ast import PyCF_ALLOW_TOP_LEVEL_AWAIT
except ImportError:
	SUPPORTS_ASYNCIO_REPL = False
else:
	SUPPORTS_ASYNCIO_REPL = True

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
		self.flags = PyCF_DONT_IMPLY_DEDENT

	def __call__(self, source, filename, symbol):
		codeob = import_expression.compile(source, filename, symbol, self.flags, dont_inherit=True)
		for feature in features:
			if codeob.co_flags & feature.compiler_flag:
				self.flags |= feature.compiler_flag
		return codeob

class ImportExpressionInteractiveConsole(code.InteractiveConsole):
	def __init__(self, locals=None, filename='<console>'):
		super().__init__(locals, filename)
		self.locals.update({import_expression.constants.IMPORTER: importlib.import_module})
		self.compile = ImportExpressionCommandCompiler()

# we must vendor this class because it creates global variables that the main code depends on
class ImportExpressionAsyncIOInteractiveConsole(ImportExpressionInteractiveConsole):
	def __init__(self, locals, loop):
		super().__init__(locals)
		self.loop = loop
		self.locals.update(dict(asyncio=asyncio, loop=loop))
		self.compile.compiler.flags |= PyCF_ALLOW_TOP_LEVEL_AWAIT

		self.loop = loop

	def runcode(self, code):
		future = concurrent.futures.Future()

		def callback():
			global repl_future
			global repl_future_interrupted

			repl_future = None
			repl_future_interrupted = False

			func = types.FunctionType(code, self.locals)
			try:
				coro = func()
			except SystemExit:
				raise
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
				repl_future = self.loop.create_task(coro)
				futures._chain_future(repl_future, future)
			except BaseException as exc:
				future.set_exception(exc)

		self.loop.call_soon_threadsafe(callback)

		try:
			return future.result()
		except SystemExit:
			raise
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
			console.interact(**self.interact_kwargs)
		finally:
			warnings.filterwarnings(
				'ignore',
				message=r'^coroutine .* was never awaited$',
				category=RuntimeWarning)

			loop.call_soon_threadsafe(loop.stop)

def asyncio_main(repl_locals, interact_kwargs):
	global console
	global loop
	global repl_future
	global repl_future_interrupted

	loop = asyncio.get_event_loop()

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
			if repl_future and not repl_future.done():
				repl_future.cancel()
				repl_future_interrupted = True
			continue
		else:
			break

def parse_args():
	import argparse

	version_info = (
		f'Import Expression Parser {import_expression.__version__}\n'
		f'Python {sys.version}'
	)

	parser = argparse.ArgumentParser(prog='import_expression')
	parser.add_argument('-q', '--quiet', action='store_true', help='hide the intro banner and exit message')
	parser.add_argument('-a', '--asyncio', action='store_true', help='use the asyncio REPL (python 3.8+)')
	parser.add_argument('-V', '--version', action='version', version=version_info)

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

	# inform tab completion of what variables were set at the REPL
	readline.set_completer(rlcompleter.Completer(locals).complete)

def main():
	repl_locals = {
		key: globals()[key] for key in [
			'__name__', '__package__',
			'__loader__', '__spec__',
			'__builtins__', '__file__']
		if key in globals()
	}

	setup_history_and_tab_completion(repl_locals)

	args = parse_args()
	interact_kwargs = dict(banner='' if args.quiet else None, exitmsg='' if args.quiet else None)

	if args.asyncio:
		if not SUPPORTS_ASYNCIO_REPL:
			print('Python3.8+ required for the AsyncIO REPL.', file=sys.stderr)
			sys.exit(2)
		asyncio_main(repl_locals, interact_kwargs)
		sys.exit(0)

	ImportExpressionInteractiveConsole(repl_locals).interact(**interact_kwargs)

if __name__ == '__main__':
	main()
