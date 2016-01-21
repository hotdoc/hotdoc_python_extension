import os
from hotdoc.formatters.html.html_formatter import HtmlFormatter
from hotdoc.core.symbols import FunctionSymbol

class PythonHtmlFormatter(HtmlFormatter):
    def __init__(self, doc_tool, extension):
        module_path = os.path.dirname(__file__)
        searchpath = [os.path.join(module_path, "templates")]
        self.__extension = extension
        HtmlFormatter.__init__(self, doc_tool, searchpath)

    def _format_prototype(self, function, is_pointer, title):
        template = self.engine.get_template('python_prototype.html')

        res = template.render ({'function_name': title,
            'parameters': function.parameters,
            'comment': '',
            'throws': function.throws,
            'is_method': function.is_method})

        return res

    def _format_parameter_symbol (self, parameter):
        if parameter.type_tokens:
            parameter.extension_contents['type-link'] = \
                    self._format_type_tokens(parameter.type_tokens)
        return HtmlFormatter._format_parameter_symbol(self, parameter)

    def _format_class_symbol(self, klass):
        constructor = self.doc_tool.session.query(FunctionSymbol).filter(
                FunctionSymbol.is_ctor_for==klass.unique_name).first()
        if constructor is None:
            return HtmlFormatter._format_class_symbol(self, klass)

        hierarchy = self._format_hierarchy(klass)
        template = self.engine.get_template('python_class.html')

        self._format_symbols(constructor.get_children_symbols())
        constructor.formatted_doc = self._format_doc(constructor.comment)
        constructor.link.title = klass.display_name
        constructor = self._format_callable(constructor, 'class',
                klass.link.title)[0]
        return (template.render({'symbol': klass,
                                 "editing_link":
                                 self._format_editing_link(klass),
                                 'klass': klass,
                                 'constructor': constructor,
                                 'hierarchy': hierarchy}),
                False)
