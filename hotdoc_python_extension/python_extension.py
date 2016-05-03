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

import os, glob, io

import pypandoc
import jedi
from jedi.evaluate.helpers import get_module_names

from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.file_includer import find_md_file
from hotdoc.core.symbols import *
from hotdoc.core.doc_tree import Page
from hotdoc.core.comment_block import comment_from_tag

from .python_doc_parser import google_doc_to_native
from .python_html_formatter import PythonHtmlFormatter


def get_definitions(script):
    def def_ref_filter(_def):
        is_def = _def.is_definition()
        return is_def

    defs = [jedi.api.classes.Definition(script._evaluator, name_part)
            for name_part in get_module_names(script._parser.module(), False)]
    return sorted(filter(def_ref_filter, defs), key=lambda x: (x.line,
        x.column))

class PythonScanner(object):
    def __init__(self, doc_repo, extension, sources):
        self.doc_repo = doc_repo

        self.class_nesting = 0

        self.fundamentals = self.__create_fundamentals()

        self.__extension = extension
        self.mod_comments = {}

        self.__seen_attrs = set()

        for source in sources:
            self.__current_filename = source
            self.__parse_module (source)

    def __create_fundamentals(self):
        string_link = \
                Link('https://docs.python.org/2.7/library/functions.html#str',
                    'str', 'str')
        boolean_link = \
                Link('https://docs.python.org/2.7/library/functions.html#bool',
                        'bool', 'bool')
        true_link = \
                Link('https://docs.python.org/2/library/constants.html#True',
                    'True', 'True')
        false_link = \
               Link('https://docs.python.org/2/library/constants.html#False',
                    'False', 'False')
        integer_link = \
                Link('https://docs.python.org/2/library/functions.html#int',
                        'int', 'int')
        float_link = \
                Link('https://docs.python.org/2/library/functions.html#float',
                        'float', 'float')
        none_link = \
                Link('https://docs.python.org/2/library/constants.html#None',
                        'None', 'None')
        unicode_link = \
                Link('https://docs.python.org/2/library/functions.html#unicode',
                        'unicode', 'unicode')
        dict_link = \
                Link('https://docs.python.org/2/tutorial/datastructures.html#dictionaries',
                        'dict', 'dict')

        callable_link = \
                Link('https://docs.python.org/2/library/functions.html#callable',
                        'callable', 'callable')

        fundamentals = {
                "none": none_link,
                "None": none_link,
                "boolean": boolean_link,
                "bool": boolean_link,
                "int": integer_link,
                "integer": integer_link,
                "float": float_link,
                "unicode": unicode_link,
                "str": string_link,
                "string": string_link,
                "True": true_link,
                "true": true_link,
                "False": false_link,
                "false": false_link,
                "dict": dict_link,
                "callable": callable_link,
                "dictionary": dict_link,
        }

        return fundamentals

    def __parse_module(self, source):
        relpath = os.path.relpath(source, self.__extension.package_root)
        # FIXME: ahem
        modname = os.path.splitext(relpath)[0].replace('/', '.')
        with io.open(source, 'r', encoding='utf-8') as _:
            source = _.read()
        script = jedi.Script(source, line=1, column=0)
        mod = script._parser.module()
        modcomment, attribute_comments = google_doc_to_native(mod.raw_doc)
        if modcomment:
            self.mod_comments[self.__current_filename] = modcomment
        defs = get_definitions(script)
        for definition in defs:
            if definition.type == 'class':
                self.__parse_class(definition, modname)
            elif definition.type == 'function':
                self.__parse_function(definition, {}, modname)

    def __parse_class(self, definition, parent_name):
        self.class_nesting += 1
        klass_name = '.'.join((parent_name, str(definition.name)))
        comment, attr_comments = google_doc_to_native(definition.raw_doc)
        if comment:
            comment.filename = self.__current_filename
        for subdef in definition.defined_names():
            if subdef.type == 'function':
                self.__parse_function(subdef, attr_comments, klass_name)
        class_symbol = self.__extension.get_or_create_symbol(ClassSymbol,
                comment=comment,
                filename=self.__current_filename,
                display_name=klass_name)
        self.class_nesting -= 1

    def __type_tokens_from_comment(self, comment):
        if comment is None:
            return []

        try:
            pytype = comment.tags.pop('type')
        except KeyError:
            return []

        try:
            link = self.fundamentals[pytype]
        except KeyError:
            link = Link(None, pytype, pytype)

        return [link]

    def __parse_attribute(self, definition, attr_comments, parent_name):
        for subdef in definition._definition.children:
            if subdef.type != 'power':
                continue
            if len(subdef.children) != 2:
                continue
            if subdef.children[0].value != 'self':
                continue
            if subdef.children[1].type != 'trailer':
                continue
            attr = subdef.children[1]
            if len(attr.children) != 2:
                continue
            if attr.children[0].type != 'operator' or \
                    attr.children[0].value != '.':
                continue
            attr_name = attr.children[1].value
            if attr_name.startswith('__'):
                continue
            attr_comment = attr_comments.get(str(attr_name))
            attr_name = '.'.join((parent_name, attr_name))
            if attr_name in self.__seen_attrs:
                continue
            self.__seen_attrs.add(attr_name)
            type_tokens = self.__type_tokens_from_comment(attr_comment)

            type_ = QualifiedSymbol(type_tokens=type_tokens)

            self.__extension.get_or_create_symbol(PropertySymbol,
                comment=attr_comment,
                filename=self.__current_filename,
                display_name=attr_name,
                prop_type=type_)

    def __params_doc_to_dict (self, params_doc):
        dict_ = {}
        for param in params_doc:
            dict_[param[0]] = (param[1], param[2])

        return dict_

    def __parse_function(self, definition, klass_attr_comments, parent_name):
        is_method = self.class_nesting > 0
        if is_method:
            try:
                defs = definition.defined_names()
            except IndexError: # https://github.com/davidhalter/jedi/issues/697
                defs = []
            for subdef in defs:
                if subdef.type == 'statement':
                    self.__parse_attribute(subdef, klass_attr_comments,
                            parent_name)

        name = definition.name

        is_ctor_for = None

        if name == '__init__':
            is_ctor_for = parent_name

        if is_ctor_for is None and name.startswith('__'):
            return

        if not is_method and is_ctor_for is None and name.startswith('_'):
            return

        func_name = str('.'.join((parent_name, name)))
        if definition.raw_doc:
            comment, attr_comments = google_doc_to_native(definition.raw_doc)
            comment.filename = self.__current_filename
        else:
            comment = None

        parameters = self.__parse_parameters(definition.params, comment)
        retval = self.__parse_return_value(comment)

        if is_method:
            parameters = parameters[1:]


        func_symbol = self.__extension.get_or_create_symbol(FunctionSymbol,
                parameters=parameters,
                return_value=retval,
                comment=comment,
                is_method = is_method,
                filename=self.__current_filename,
                is_ctor_for=is_ctor_for,
                display_name=func_name)

    def __parse_return_value(self, comment):
        if not comment:
            return [None]

        try:
            ret_comments = comment.tags.pop('returns')
            return_value = []
            for ret_comment in ret_comments:
                type_tokens = self.__type_tokens_from_comment(ret_comment)
                return_value.append(ReturnItemSymbol(type_tokens=type_tokens,
                        comment=ret_comment))
            return return_value or [None]
        except KeyError:
            return [None]

    def __parse_parameters(self, args, comment):
        parameters = []

        if comment:
            param_comments = comment.params
        else:
            param_comments = {}

        for arg in args or []:
            param_comment = param_comments.get (arg.name)
            type_tokens = self.__type_tokens_from_comment(param_comment)

            param = ParameterSymbol (argname=arg.name,
                    type_tokens=type_tokens,
                    comment=param_comment)
            parameters.append (param)

        return parameters


DESCRIPTION=\
"""
Parse python source files and extract symbols and comments.
"""


class PythonExtension(BaseExtension):
    extension_name = 'python-extension'
    argument_prefix = 'python'
    package_root = None

    def __init__(self, doc_repo):
        BaseExtension.__init__(self, doc_repo)
        self.formatters['html'] = PythonHtmlFormatter(
            self, doc_repo.doc_database)

    def setup(self):
        stale, unlisted = self.get_stale_files(PythonExtension.sources)
        if not stale:
            return

        self.stale = stale

        self.scanner = PythonScanner (self.doc_repo, self,
                stale)

    def get_or_create_symbol(self, *args, **kwargs):
        kwargs['language'] = 'python'
        return super(PythonExtension, self).get_or_create_symbol(*args,
            **kwargs)

    @staticmethod
    def add_arguments (parser):
        group = parser.add_argument_group('Python extension',
                DESCRIPTION)
        PythonExtension.add_index_argument(group)
        PythonExtension.add_sources_argument(group)
        PythonExtension.add_path_argument(group, 'package-root',
            help_="Path to the root of the documented package / application")

    @staticmethod
    def parse_config (doc_repo, config):
        PythonExtension.parse_standard_config(config)
        if not PythonExtension.package_root:
            PythonExtension.package_root = os.path.commonprefix(PythonExtension.sources)
        PythonExtension.package_root = os.path.abspath(
            os.path.join(PythonExtension.package_root, '..'))

    def _get_languages(self):
        return ['python']

    def _get_naive_link_title(self, source_file):
        relpath = os.path.relpath(source_file, PythonExtension.package_root)
        modname = os.path.splitext(relpath)[0].replace('/', '.')
        return modname

    def _get_naive_page_description(self, source_file):
        modcomment = self.scanner.mod_comments.get(source_file)
        if modcomment is None:
            return ''

        if modcomment.description:
            out = '## %s\n\n' % self._get_naive_link_title(source_file)
            out += pypandoc.convert(modcomment.description, to='md',
                    format='rst')
            return out

        return BaseExtension._get_naive_page_description(self, link_title)

def get_extension_classes():
    return [PythonExtension]
