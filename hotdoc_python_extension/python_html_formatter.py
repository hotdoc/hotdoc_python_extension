import os
from hotdoc.formatters.html.html_formatter import HtmlFormatter

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
