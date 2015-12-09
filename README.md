This is a python extension for [hotdoc](https://github.com/hotdoc/hotdoc)

> This is still a work in progress and very limited for now

This extension uses the standard ast module and napoleon,
which is packaged in sphinx (yeah I know) to generate symbols
for python source code.

It also uses the standard ast module.

### Install instructions:

This extension has no system-wide dependencies.

You can install it either through pip:

```
pip install hotdoc_python_extension
```

Or with setup.py if you checked out the code from git:

```
python setup.py install
```

This will of course work in a virtualenv as well.

### Usage:

Just run hotdoc's wizard for more information once the extension is installed with:

```
hotdoc conf --quickstart
```

### Hacking

Checkout the code from github, then run:

```
python setup.py develop
```
