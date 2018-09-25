import py.test

import import_expression_parser
from import_expression_parser import parse_import_expressions

def test_invalid_syntax():
	for invalid in (
		'<< <<x>>.y >>',
		'<<.x>>',
		'<<',
		'>>',
		'<<"foo">>',
		'<<a>>.<<b>>',
	):
		with py.test.raises(SyntaxError):
			parse_import_expressions(invalid)

def _replace_header(string):
	left, header, right = string.partition(import_expression_parser.HEADER)
	return right

def _test(input, output):
	assert _replace_header(parse_import_expressions(input)) == output

imp = '__import_module'

def test_basic():
	_test('<<x.y>>.z', f'{imp}("x.y").z')
