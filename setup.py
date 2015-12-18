from setuptools import setup, find_packages

setup(
    name = "hotdoc_python_extension",
    version = "0.6.5",
    keywords = "python ast sphinx napoleon hotdoc",
    url='https://github.com/hotdoc/hotdoc_python_extension',
    author_email = 'mathieu.duponchelle@opencreed.com',
    license = 'LGPL',
    description = ("An extension for hotdoc that parses python using the"
        " standard ast module and napoleon from sphinx"),
    author = "Mathieu Duponchelle",
    packages = find_packages(),
    entry_points = {'hotdoc.extensions': 'get_extension_classes = hotdoc_python_extension.python_extension:get_extension_classes'},
    install_requires = [
        'hotdoc>=0.6.5',
        'sphinx>=1.3.3',
    ]
)
