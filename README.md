# Import Expression Parser (for lack of a better name)

[![Build Status](https://travis-ci.org/bmintz/import-expression-parser.svg?branch=main)](https://travis-ci.org/bmintz/import-expression-parser)
[![Coverage Status](https://coveralls.io/repos/github/bmintz/import-expression-parser/badge.svg?branch=main)](https://coveralls.io/github/bmintz/import-expression-parser?branch=main)

Import Expression Parser converts code like this:

```py
x = collections.deque!(maxsize=2)
```

Into this roughly equivalent code:
```py
from collections import deque
x = deque(maxsize=2)
del deque
```

## Usage

```py
>>> import import_expression
>>> eval('collections!.Counter("bccdddeeee")')
Counter({'e': 4, 'd': 3, 'c': 2, 'b': 1})
```

By default, the filename for `SyntaxError`s is `<string>`.
To change this, pass in a filename via the `filename` kwarg.

## Limitations / Known Issues

* Invalid syntax, such as `!a`, `urllib!.parse!`, and `def a(b!): pass`, isnot yet detected.

## FAQ

*Actually asked questions for a new project! Golly gee!*

* Why not just use `__import__('x')`? \
  From the [discord.py server](https://discord.gg/r3sSKJJ):
  > devon#4089: if i want to type `_("thing")` \
  > devon#4089: i have to move my fingers between three different locations \
  > devon#4089: both at the end and start of the string \
  > lambda#0987: yeah and [*it's*] also a pain to type on mobile so ok \
  > devon#4089: \<\<x\>\> is slightly less grating \
  For context, the originally proposed syntax was \<\<x\>\>.

## [License](/LICENSE)

Copyright © 2018 Benjamin Mintz <bmintz@protonmail.com>. All Rights Reserved. \
Licensed under this new hipster cool cat license called the Charity Public License. \
If you are not a hipster cool cat, please contact me to arrange a private license.
