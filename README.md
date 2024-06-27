# Import Expression Parser (for lack of a better name)

[![Coverage Status](https://coveralls.io/repos/github/iomintz/import-expression-parser/badge.svg?branch=main)](https://coveralls.io/github/ioistired/import-expression-parser?branch=main)

Import Expression Parser converts code like this:

```py
urllib.parse!.quote('hello there')
```

Into this equivalent code:
```py
__import__('importlib').import_module('urllib.parse').quote('hello there')
```

## Usage

```py
>>> import import_expression
>>> import_expression.eval('collections!.Counter("bccdddeeee")')
Counter({'e': 4, 'd': 3, 'c': 2, 'b': 1})
```

The other public functions are `exec`, `compile`, `parse`, and `find_imports`.
See their docstrings for details.

By default, the filename for `SyntaxError`s is `<string>`.
To change this, pass in a filename via the `filename` kwarg.

### Reusing compiled code objects

import_expression.eval/exec/compile should not be passed strings in a tight loop. \
Doing so will recompile the string every time. Instead, you should pre-compile the string to a code object
and pass that to import_expression.eval / import_expression.exec.
For example, instead of this:

```py
for line in sys.stdin:
	print(import_expression.eval('foo!.bar(l)', dict(l=line))
```

Prefer this:

```py
code = import_expression.compile('foo!.bar(l)', mode='eval')
for line in sys.stdin:
	print(import_expression.eval(code, dict(l=line)))
```

### REPL usage

Run `import-expression` for an import expression enabled REPL. \
Run `import-expression -a` for a REPL that supports both import expressions and top level `await` (3.8+).

See `import-expression --help` for more details.

### Running a file

Run `import-expression <filename.py>`.

## Limitations / Known Issues

* Due to the hell that is f-string parsing, and because `!` is already an operator inside f-strings,
  import expressions inside f-strings will likely never be supported.
* Due to python limitations, results of `import_expression.exec` will have no effect on the caller's globals or locals
  without an explicit `globals` argument.
* Unlike real operators, spaces before and after the import expression operator (such as `x ! .y`) are not supported.

## [License](https://github.com/ioistired/import-expression/blob/main/LICENSE)

Copyright © io mintz <<io@mintz.cc>>. All Rights Reserved. \
Licensed under the MIT License. See the LICENSE file for details.
