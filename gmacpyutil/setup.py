"""setup for gmacpyutil."""

import unittest

from distutils.core import Command
import setuptools

_GMACPYUTIL_VERSION = '0.1'


class TestCommand(Command):
  """setup.py command to run the whole test suite."""
  description = 'Run test full test suite.'
  user_options = []

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    suite = unittest.defaultTestLoader.discover('.', pattern='*_test.py')
    unittest.TextTestRunner().run(suite)


setuptools.setup(
    name='gmacpyutil',
    version=_GMACPYUTIL_VERSION,
    description='Python utilities for managing OS X machines.',
    url='https://github.com/google/macops/',
    author='Google Inc.',
    author_email='google-macops@googlegroups.com',

    license='Apache 2.0',

    packages=setuptools.find_packages(),

    provides=['gmacpyutil (%s)' % (_GMACPYUTIL_VERSION)],

    cmdclass={'test': TestCommand},
)
