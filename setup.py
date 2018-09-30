#!/usr/bin/env python3
# encoding: utf-8

import distutils.log  # stdlib not using logging smh
import importlib.util
import logging
import os
import os.path
import setuptools
import subprocess
import sys
import typing

def import_by_path(name, path):
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)

	return module

here = os.path.realpath(os.path.dirname(__file__))
init_path = os.path.join(here, 'import_expression', 'version.py')
# we put the version in a separate file because:
# A) We can't import the module directly before it's installed
# B) If we put __version__ in __init__.py, this alternate import method would fail
# because the modules that __init__ imports would not be available.
version = import_by_path('version', init_path).__version__

with open('README.md') as f:
	long_description = f.read()


command_classes = {}

class ScriptCommand(type):
	def __new__(metacls, clsname, bases, attrs, *, name, description='', command: typing.Sequence[str]):
		bases += (setuptools.Command,)
		cls = type.__new__(metacls, name, bases, attrs)

		cls.__command = command

		cls.description = description
		cls.user_options = []

		def run(self) -> typing.NoReturn:
			self.announce(repr(self.__command), level=distutils.log.INFO)
			p = subprocess.Popen(self.__command)
			status = p.wait()
			sys.exit(status)

		def noop(*args, **kwargs):
			pass

		cls.run = run
		cls.initialize_options = cls.finalize_options = noop
		command_classes[name] = cls

		return cls

class UnitTestCommand(
	metaclass=ScriptCommand,
	name='test',
	description='run unit tests',
	command='pytest tests.py --cov import_expression --cov-report html'.split()
):
	pass

class ReleaseCommand(
	metaclass=ScriptCommand,
	name='release',
	description='build and upload a release',
	command=(sys.executable, __file__, 'sdist', 'upload')
):
	pass

class ReplCommand(
	metaclass=ScriptCommand,
	name='repl',
	description='start a REPL that supports top level import expressions',
	command=(sys.executable, '-ic', 'import import_expression.patch; import_expression.patch.patch(globals())')
):
	pass

setuptools.setup(
	name='import_expression',
	version=version,

	description='Parses a superset of Python allowing for inline module import expressions',
	long_description=long_description,
	long_description_content_type='text/markdown',

	license='Charity Public License v1.1.0',

	author='Benjamin Mintz',
	author_email='bmintz@protonmail.com',
	url='https://github.com/bmintz/import-expression-parser',

	packages=['import_expression'],

	extras_require={
		'test': [
			'pytest'
			'pytest-cov',
		],
	},

	cmdclass=command_classes,
)
