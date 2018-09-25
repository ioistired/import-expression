# Import Expression Parser (for lack of a better name)

[![Build Status](https://travis-ci.org/bmintz/import-expression-parser.svg?branch=main)](https://travis-ci.org/bmintz/import-expression-parser)
[![Coverage Status](https://coveralls.io/repos/github/bmintz/import-expression-parser/badge.svg?branch=main)](https://coveralls.io/github/bmintz/import-expression-parser?branch=main)

Import Expression Parser converts code like this:

```py
x = <<collections.deque>>(maxsize=2)
```

Into this roughly equivalent code:
```py
from collections import deque
x = deque(maxsize=2)
del deque
```

## Usage

```py
>>> from import_expression_parser import parse_import_expressions
>>> print(parse_import_expressions('<<datetime>>.datetime.utcnow()'))
from importlib import import_module as __import_module
__import_module("datetime").datetime.utcnow
```

Nicely formatted syntax errors are also raised:
```py
>>> parse_import_expressions('<<"invalid">>')
Traceback (most recent call last):
  ...
  File "<repl session>", line 1
    <<"invalid">>
              ^
SyntaxError: expected only (possibly dotted) names inside of an import expression
```

By default, the filename for `SyntaxError`s is `<repl session>`.
To change this, pass in a filename via the `filename` kwarg:

```py
> parse('<<"invalid">>', filename='foo')
Traceback (most recent call last):
  ...
  File "foo", line 1
    <<"invalid">>
              ^
SyntaxError: expected only (possibly dotted) names inside of an import expression
```

## <i lang=lat>Caveat Emptor</i>

To keep the code simple, this library does *not* detect invalid syntax
other than invalid import expression syntax.
To detect these, you must also use [the `ast` module](https://docs.python.org/3/library/ast.html)
or [`compile()`](https://docs.python.org/3/library/functions.html#compile).

## FAQ

*Actually asked questions for a new project! Golly gee!*

* Why not just use `__import__('x')`?
	From the [discord.py server](https://discord.gg/r3sSKJJ):
	> devon#4089: if i want to type `_("thing")` \
	> devon#4089: i have to move my fingers between three different locations \
	> devon#4089: both at the end and start of the string \
	> lambda#0987: yeah and [*it's*] also a pain to type on mobile so ok \
	> devon#4089: \<\<x\>\> is slightly less grating

*OK you got me, **this** one's just anticipated.*

* What about bitshifts?
  The astute reader will have noticed that this syntax totally conflicts with the bitshift operators. \
  That's true. If you use this code, you may not use bit shifts. \
  I'm working on a version which would let you just write $x instead of <<x>>, so stay tuned for that.

## [License](/LICENSE)

Copyright © 2018 Benjamin Mintz <bmintz@protonmail.com>. All Rights Reserved. \
Licensed under this new hipster cool cat license called the Charity Public License. \
If you are not a hipster cool cat, please contact me to arrange a private license.
