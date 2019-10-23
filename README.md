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

By default, the filename for `SyntaxError`s is `<string>`.
To change this, pass in a filename via the `filename` kwarg.

### AST usage

<!-- TODO document usage like jishaku or how one could build a REPL -->

### Monkey Patching the REPL

```py
>>> urllib.parse!.quote
  File "<stdin>", line 1
    urllib.parse!.quote
                ^
SyntaxError: invalid syntax
>>> import import_expression.patch
>>> import_expression.patch.patch(globals())
>>> urllib.parse!.quote
<function quote at 0xdeadbeef>
```

For convenience, you can also add the following two lines to your `sitecustomize.py`:

```py
import import_expression.patch
import_expression.patch.patch()
```

And all REPL sessions will use the import expression syntax.

## Limitations / Known Issues

* Some invalid syntax, such as `urllib!.parse!` is not yet detected,
  though that still works as though it was `urllib.parse!` (see [issue #5]).
* Due to the hell that is f-string parsing, and because `!` is already an operator inside f-strings,
  import expressions inside f-strings will likely never be supported.
* Due to python limitations, results of `import_expression.exec` will have no effect on the caller's globals
  without an explicit `globals` argument.

[issue #5]: https://github.com/iomintz/import-expression-parser/issues/5

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

## [License](https://github.com/bmintz/import-expression-parser/blob/main/LICENSE)

Copyright © 2018–2019 Benjamin Mintz <<io@mintz.cc>>. All Rights Reserved. \
Licensed under the MIT License. See the LICENSE.md file for details.
