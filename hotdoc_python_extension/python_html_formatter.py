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
from hotdoc.formatters.html_formatter import HtmlFormatter
from hotdoc.core.symbols import FunctionSymbol, Symbol

from .python_doc_parser import MyRestParser

class PythonHtmlFormatter(HtmlFormatter):
    def __init__(self, extension, doc_database):
        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        self.__extension = extension
        self.__doc_database = doc_database
        HtmlFormatter.__init__(self, searchpath)
        self.__docstring_formatter = MyRestParser(extension)
        self.__current_module_name = None
        self.__current_package_name = None

    def _format_prototype(self, function, is_pointer, title):
        template = self.engine.get_template('python_prototype.html')

        res = template.render ({'function_name': title,
            'parameters': function.parameters,
            'comment': '',
            'throws': function.throws,
            'is_method': function.is_method})

        return res

    # pylint: disable=too-many-arguments
    def _format_callable_summary(self, callable_, return_value, function_name,
                                 is_callable, is_pointer):
        template = self.engine.get_template('callable_summary.html')

        return template.render({'symbol': callable_,
                                'return_value': [],
                                'function_name': function_name,
                                'is_callable': is_callable,
                                'is_pointer': is_pointer})

    def _format_function(self, func):
        if func.is_ctor_for is not None:
            return None, None
        return super(PythonHtmlFormatter, self)._format_function(func)

    def _format_parameter_symbol (self, parameter):
        if parameter.type_tokens:
            parameter.extension_contents['type-link'] = \
                    self._format_type_tokens(parameter.type_tokens)
        return HtmlFormatter._format_parameter_symbol(self, parameter)

    def _format_docstring(self, docstring, link_resolver, to_native):
        if to_native:                                                                                    
            format_ = 'markdown'
        else:
            format_ = 'html'
        return self.__docstring_formatter.translate(
            docstring, link_resolver, format_, self.__current_package_name)

    def _format_class_symbol(self, klass):
        constructor = self.__doc_database.get_session().query(FunctionSymbol).filter(
                FunctionSymbol.is_ctor_for==klass.unique_name).first()
        if constructor is None:
            return HtmlFormatter._format_class_symbol(self, klass)

        hierarchy = self._format_hierarchy(klass)
        template = self.engine.get_template('python_class.html')

        link_resolver = self.__extension.doc_repo.link_resolver
        self.format_symbol(constructor, link_resolver)
        constructor.link.title = klass.display_name
        constructor = self._format_callable(constructor, 'class',
                klass.link.title)[0]
        return (template.render({'symbol': klass,
                                 'klass': klass,
                                 'constructor': constructor,
                                 'hierarchy': hierarchy}),
                False)

    def format_symbol(self, symbol, link_resolver):
        if isinstance(symbol, Symbol):
            if self.__current_module_name != symbol.filename:
                self.__current_module_name = symbol.filename
                relpath = os.path.relpath(self.__current_module_name,
                        self.__extension.package_root)
                modname = os.path.splitext(relpath)[0].replace('/', '.')
                self.__current_package_name = modname

        return HtmlFormatter.format_symbol(self, symbol, link_resolver)
