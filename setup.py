#!/usr/bin/env python3

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

import distutils
import importlib.util
import logging
import os
import os.path
import setuptools
import subprocess
import shutil
import sys
import typing
from setuptools.command.install import install as _install

logging.basicConfig(level=logging.INFO)
here = os.path.realpath(os.path.dirname(__file__))

def import_by_path(name, path):
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)

	return module

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
	def __new__(metacls, clsname, bases, attrs, *, name, description='', commands: typing.Sequence[typing.Tuple[str, ...]]):
		bases += (setuptools.Command,)
		cls = type.__new__(metacls, name, bases, attrs)

		cls.__commands = commands
		cls.description = description
		cls.user_options = []

		def run(self):
			for command in self.__commands:
				logging.info(repr(command))
				p = subprocess.Popen(command)
				status = p.wait()
				if status != 0:
					sys.exit(status)

			sys.exit(0)

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
	commands=(
		'pytest tests.py '
		'--cov import_expression '
		'--cov-config .coveragerc '
		'--cov-report term-missing '
		'--cov-report html '
		'--cov-branch'
	.split(),)
):
	pass

class ReleaseCommand(
	metaclass=ScriptCommand,
	name='release',
	description='build and upload a release',
	commands=(
		(sys.executable, __file__, 'sdist', 'bdist_wheel'),
		('twine', 'upload', 'dist/*'),
	)
):
	pass

# `class install` is modified from future_fstrings/setup.py at 596deb0

class install(_install):
	def initialize_options(self):
		super().initialize_options()

		contents = 'import import_expression._codec.register'
		self.extra_path = (self.distribution.metadata.name, contents)

	def finalize_options(self):
		super().finalize_options()

		install_suffix = os.path.relpath(
			self.install_lib, self.install_libbase,
		)
		if install_suffix == '.':
			distutils.log.info('skipping install of .pth during easy-install')
		elif install_suffix == self.extra_path[1]:
			self.install_lib = self.install_libbase
			distutils.log.info(
				"will install .pth to '%s.pth'",
				os.path.join(self.install_lib, self.extra_path[0]),
			)
		else:
			raise AssertionError(
				'unexpected install_suffix',
				self.install_lib, self.install_libbase, install_suffix,
			)

command_classes['install'] = install

setuptools.setup(
	name='import_expression',
	version=version,

	description='Parses a superset of Python allowing for inline module import expressions',
	long_description=long_description,
	long_description_content_type='text/markdown',

	license='MIT',

	author='io mintz',
	author_email='io@mintz.cc',
	url='https://github.com/iomintz/import-expression-parser',

	packages=['import_expression', 'import_expression._codec'],

	install_requires=[
		'astunparse>=1.6.3,<2.0.0',
	],

	extras_require={
		'test': [
			'pytest',
			'pytest-cov',
		],
	},

	entry_points={
		'console_scripts': [
			'import_expression = import_expression.__main__:main',
			'import-expression = import_expression.__main__:main',
			'import-expression-rewrite = import_expression._main2:main',
		],
	},

	cmdclass=command_classes,

	classifiers=[
		'License :: OSI Approved :: MIT License',
	],
)
