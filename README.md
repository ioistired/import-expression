# Import Expression Parser (for lack of a better name)

[![Build Status](https://img.shields.io/travis/iomintz/import-expression-parser/main.svg?label=tests)](https://travis-ci.org/iomintz/import-expression-parser)
[![Coverage Status](https://coveralls.io/repos/github/iomintz/import-expression-parser/badge.svg?branch=main)](https://coveralls.io/github/iomintz/import-expression-parser?branch=main)

Import Expression Parser converts code like this:

```py
urllib.parse!.quote('hello there')
```

Into this equivalent code:
```py
importlib.import_module('urllib.parse').quote('hello there')
```

## Usage

```py
>>> import import_expression
>>> import_expression.eval('collections!.Counter("bccdddeeee")')
Counter({'e': 4, 'd': 3, 'c': 2, 'b': 1})
```

The other public functions are `exec`, `compile`, `parse`, and `find_imports`. See their docstrings for details.

By default, the filename for `SyntaxError`s is `<string>`.
To change this, pass in a filename via the `filename` kwarg.

### AST usage

<!-- TODO document usage like jishaku or how one could build a REPL -->

### REPL usage

Run `import_expression` for an import expression enabled REPL. \
Run `import_expression -a` for a REPL that supports both import expressions and top level `await` (3.8+).

See `import_expression --help` for more details. 

## Limitations / Known Issues

* Due to the hell that is f-string parsing, and because `!` is already an operator inside f-strings,
  import expressions inside f-strings will likely never be supported.
* Due to python limitations, results of `import_expression.exec` will have no effect on the caller's globals or locals
  without an explicit `globals` argument.
* Unlike real operators, spaces before and after the import expression operator (such as `x ! .y` are not supported).

## [License](https://github.com/bmintz/import-expression-parser/blob/main/LICENSE)

Copyright © 2018–2019 Io Mintz <<io@mintz.cc>>. All Rights Reserved. \
Licensed under the MIT License. See the LICENSE.md file for details.
