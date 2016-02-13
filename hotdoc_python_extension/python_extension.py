import os, glob
import astroid as ast
import pypandoc
from hotdoc.core.base_extension import BaseExtension
from hotdoc.core.file_includer import find_md_file
from hotdoc.core.symbols import *
from hotdoc.core.wizard import HotdocWizard
from hotdoc.core.doc_tree import Page
from hotdoc.utils.wizard import QuickStartWizard
from hotdoc.core.comment_block import comment_from_tag

from .python_doc_parser import google_doc_to_native
from .python_html_formatter import PythonHtmlFormatter

class PythonScanner(object):
    def __init__(self, doc_repo, extension, sources):
        self.doc_repo = doc_repo

        self.class_nesting = 0

        self.fundamentals = self.__create_fundamentals()

        self.__node_parsers = {
                    ast.ClassDef: self.__parse_class,
                    ast.FunctionDef: self.__parse_function,
                }

        self.__extension = extension
        self.mod_comments = {}

        for source in sources:
            relpath = os.path.relpath(source, self.__extension.package_root)
            # FIXME: ahem
            modname = os.path.splitext(relpath)[0].replace('/', '.')
            self.__current_filename = source
            builder = ast.builder.AstroidBuilder()
            tree = builder.file_build(source)
            modcomment, attribute_comments = google_doc_to_native(tree.doc)
            if modcomment:
                self.mod_comments[modname] = modcomment

            self.__parse_module (tree.body, modname)

    def __create_fundamentals(self):
        string_link = \
                Link('https://docs.python.org/2.7/library/functions.html#str',
                    'str', None)
        boolean_link = \
                Link('https://docs.python.org/2.7/library/functions.html#bool',
                        'bool', None)
        true_link = \
                Link('https://docs.python.org/2/library/constants.html#True',
                    'True', None)
        false_link = \
               Link('https://docs.python.org/2/library/constants.html#False',
                    'False', None)
        integer_link = \
                Link('https://docs.python.org/2/library/functions.html#int',
                        'int', None)
        float_link = \
                Link('https://docs.python.org/2/library/functions.html#float',
                        'float', None)
        none_link = \
                Link('https://docs.python.org/2/library/constants.html#None',
                        'None', None)
        unicode_link = \
                Link('https://docs.python.org/2/library/functions.html#unicode',
                        'unicode', None)
        dict_link = \
                Link('https://docs.python.org/2/tutorial/datastructures.html#dictionaries',
                        'dict', None)

        callable_link = \
                Link('https://docs.python.org/2/library/functions.html#callable',
                        'callable', None)

        fundamentals = {
                "none": none_link,
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

    def __parse_module (self, body, modname):
        for node in body:
            f = self.__node_parsers.get(type(node))
            if f:
                f (node, modname)

    def __parse_class (self, klass, parent_name):
        self.class_nesting += 1
        klass_name = '.'.join((parent_name, klass.name))
        comment, attr_comments = google_doc_to_native(klass.doc)

        if comment:
            comment.filename = self.__current_filename

        for method in sorted(klass.mymethods(), key=lambda x: x.name):
            self.__parse_function(method, klass_name, is_method=True)

        for method in klass.methods():
            if method.name == '__init__' and method.parent.parent.name != \
                    '__builtin__':
                self.__parse_function(method, klass_name, is_method=True,
                        is_ctor_for=klass_name)

        for attr_name, attr in sorted(klass.instance_attrs.items()):
            attr_comment = attr_comments.get(attr_name)
            self.__parse_attribute(klass_name, attr_comment, attr_name, attr)

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

    def __parse_attribute(self, parent_name, attr_comment, attr_name, attr):
        if attr_name.startswith('__'):
            return

        attr_name = '.'.join((parent_name, attr_name))

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

    def __parse_function (self, function, parent_name,
            is_method=False, is_ctor_for=None):
        if function.name.startswith('__'):
            return

        if not is_method and function.name.startswith('_'):
            return

        func_name = '.'.join ((parent_name, function.name))

        if function.doc:
            comment, attr_comments = google_doc_to_native(function.doc)
            comment.filename = self.__current_filename
        else:
            comment = None

        parameters = self.__parse_parameters(function.args, comment)
        retval = self.__parse_return_value(comment)

        is_method = self.class_nesting > 0

        if is_method:
            parameters = parameters[1:]

        func_symbol = self.__extension.get_or_create_symbol(FunctionSymbol,
                parameters=parameters,
                return_value=retval,
                comment=comment,
                is_method = is_method,
                is_ctor_for = is_ctor_for,
                filename=self.__current_filename,
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

        for arg in args.args or []:
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

PYTHON_SOURCES_PROMPT=\
"""
Please pass a list of python source files.

You can pass wildcards here, for example:

>>> ['../foo/*.py', '../foo//bar/*.py]

These wildcards will be evaluated each time hotdoc is run.

You will be prompted for source files to ignore afterwards.
"""

PYTHON_FILTERS_PROMPT=\
"""
Please pass a list of python source files to ignore.

You can pass wildcards here, for example:

>>> ['../foo/*priv*.py']

These wildcards will be evaluated each time hotdoc is run.
"""

def validate_filters(wizard, thing):
    if thing is None:
        return True

    if not QuickStartWizard.validate_globs_list(wizard, thing):
        return False

    source_files = resolve_patterns(wizard.config.get('python_sources', []), wizard)

    filters = resolve_patterns(thing, wizard)

    source_files = [item for item in source_files if item not in filters]

    print "The files to be parsed would now be %s" % source_files

    return wizard.ask_confirmation()

def resolve_patterns(source_patterns, conf_path_resolver):
    source_files = []
    for item in source_patterns:
        item = conf_path_resolver.resolve_config_path(item)
        source_files.extend(glob.glob(item))

    return source_files

def source_files_from_config(config, conf_path_resolver):
    sources = resolve_patterns(config.get('python_sources') or [], conf_path_resolver)
    filters = resolve_patterns(config.get('python_source_filters') or [],
            conf_path_resolver)
    sources = [item for item in sources if item not in filters]
    return [os.path.abspath(source) for source in sources]

class PythonExtension(BaseExtension):
    EXTENSION_NAME = 'python-extension'
    sources = None
    package_root = None
    index = None

    def __init__(self, doc_repo):
        BaseExtension.__init__(self, doc_repo)
        doc_repo.doc_tree.page_parser.register_well_known_name('python-api',
                self.python_index_handler)
        self.formatters['html'] = PythonHtmlFormatter(
            self, doc_repo.doc_database)

    def setup(self):
        stale, unlisted = self.get_stale_files(PythonExtension.sources)
        if not stale:
            return

        self.stale = stale

        self.scanner = PythonScanner (self.doc_repo, self,
                stale)

        if not PythonExtension.index:
            self.update_naive_index()

    def python_index_handler (self, doc_tree):
        if not PythonExtension.index:
            return self.create_naive_index(PythonExtension.sources)

        index_path = find_md_file(PythonExtension.index, self.doc_repo.include_paths)
        return index_path, '', 'python-extension'

    @staticmethod
    def add_arguments (parser):
        group = parser.add_argument_group('Python extension',
                DESCRIPTION)
        group.add_argument ("--python-sources", action="store", nargs="+",
                dest="python_sources", help="Python source files to parse",
                extra_prompt=PYTHON_SOURCES_PROMPT,
                validate_function=QuickStartWizard.validate_globs_list,
                finalize_function=HotdocWizard.finalize_paths)
        group.add_argument ("--python-source-filters", action="store", nargs="+",
                dest="python_source_filters", help="Python source files to ignore",
                extra_prompt=PYTHON_FILTERS_PROMPT,
                validate_function=validate_filters,
                finalize_function=HotdocWizard.finalize_paths)
        group.add_argument ("--python-package-root", action="store", nargs="+",
                dest="python_package_root", help="Path to the root of the"
                " documented package / application",
                validate_function=HotdocWizard.validate_folder,
                finalize_function=HotdocWizard.finalize_path)
        group.add_argument ("--python-index", action="store",
                dest="python_index",
                help="Path to the python root markdown file",
                finalize_function=HotdocWizard.finalize_path)

    @staticmethod
    def parse_config (doc_repo, config):
        PythonExtension.sources = source_files_from_config(config, doc_repo)
        PythonExtension.package_root = config.get('python_package_root')
        if not PythonExtension.package_root:
            PythonExtension.package_root = os.path.commonprefix(PythonExtension.sources)
        PythonExtension.package_root = os.path.abspath(
            os.path.join(PythonExtension.package_root, '..'))
        PythonExtension.index = config.get('python_index')

    def _get_naive_link_title(self, source_file):
        relpath = os.path.relpath(source_file, PythonExtension.package_root)
        modname = os.path.splitext(relpath)[0].replace('/', '.')
        return modname

    def _get_naive_page_description(self, link_title):
        modcomment = self.scanner.mod_comments.get(link_title)
        if modcomment is None:
            return ''

        if modcomment.description:
            out = '## %s\n\n' % link_title
            out += pypandoc.convert(modcomment.description, to='md',
                    format='rst')
            return out

        return BaseExtension._get_naive_page_description(self, link_title)

def get_extension_classes():
    return [PythonExtension]
