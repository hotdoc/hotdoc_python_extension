# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import os

from setuptools import setup, find_packages

with open(os.path.join('hotdoc_python_extension', 'VERSION.txt'), 'r') as _:
    VERSION = _.read().strip()

setup(
    name = "hotdoc_python_extension",
    version = VERSION,
    keywords = "python jed napoleon hotdoc",
    url='https://github.com/hotdoc/hotdoc_python_extension',
    author_email = 'mathieu.duponchelle@opencreed.com',
    license = 'LGPLv2.1+',
    description = ("An extension for hotdoc that parses python using the"
        " jedi module and napoleon from sphinx"),
    author = "Mathieu Duponchelle",
    packages = find_packages(),
    package_data = {
        '': ['*.html'],
        'hotdoc_python_extension': ['VERSION.txt'],
    },
    entry_points = {'hotdoc.extensions': 'get_extension_classes = hotdoc_python_extension.python_extension:get_extension_classes'},
    install_requires = [
        'docutils==0.12',
        'pypandoc==1.1.3',
        'jedi==0.9.0',
        'six',
    ]
)
