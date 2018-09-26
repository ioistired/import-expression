import ast

from astpp import parseprint
from astpretty import pprint

from import_expression_parser import *

test1 = 'def foo(): x.y!.z'
test2 = 'def foo(): x!.y!.z'
