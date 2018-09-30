# run this like `python3 -i repl_helper.py`
# to get a repl with everything imported

import ast

from astpp import parseprint
from astpretty import pprint

import import_expression as ie

test1 = ie.parse('x!.y.z')
