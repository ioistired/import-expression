import sys
from collections import namedtuple

# https://github.com/python/cpython/blob/5d04cc50e51cb262ee189a6ef0e79f4b372d1583/Objects/exceptions.c#L2438-L2441
_sec_fields = 'filename lineno offset text'.split()
if sys.version_info >= (3, 10):
	_sec_fields.extend('end_lineno end_offset'.split())

SyntaxErrorContext = namedtuple('SyntaxErrorContext', _sec_fields)
