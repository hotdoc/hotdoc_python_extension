import re

from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon import docstring
from docutils.core import publish_parts
from docutils import nodes
from hotdoc.core.comment_block import Comment
from docutils.statemachine import ViewList
from docutils.writers.html4css1 import Writer as HtmlWriter
from docutils.parsers.rst import roles, directives

class MyGoogleDocString(docstring.GoogleDocstring):
    def __init__(self, *args, **kwargs):
        self.param_fields = []
        docstring.GoogleDocstring.__init__(self, *args, **kwargs)

    def _parse_parameters_section(self, section):
        self.param_fields.extend(self._consume_fields())
        return []

config = Config(napoleon_use_param=True, napoleon_use_rtype=True)

def google_doc_to_native(doc):
    docstring = MyGoogleDocString(doc, config)
    comment = Comment(description=docstring.__unicode__(),
            raw_comment=doc)

    for field in docstring.param_fields:
        param_comment = Comment(name=field[0],
                description='\n'.join(field[2]))
        comment.params[field[0]] = param_comment

    return comment

class HotdocRestHtmlWriter(HtmlWriter):
    pass

# I can not say what's happening here, please bear with me

def _nested_parse(state, text, node, with_titles=False):
    result = ViewList()
    if isinstance(text, str):
        for line in text.split("\n"):
            result.append(line, '<nested>')
    else:
        for line in text:
            result.append(line, '<nested>')
    if with_titles:
        _nested_parse_with_titles(state, result, node)
    else:
        state.nested_parse(result, 0, node)

def _nested_parse_with_titles(state, content, node):
    # hack around title style bookkeeping
    surrounding_title_styles = state.memo.title_styles
    surrounding_section_level = state.memo.section_level
    state.memo.title_styles = []
    state.memo.section_level = 0
    state.nested_parse(content, 0, node, match_titles=1)
    state.memo.title_styles = surrounding_title_styles
    state.memo.section_level = surrounding_section_level

_CALLABLE_RE = \
re.compile(r"^(?P<pre>.*?)(?P<module>[a-zA-Z0-9_.]*?)(?P<name>[a-zA-Z0-9_]+)\s*\((?P<args>.*?)\)(?P<rest>\s*->.*?)?$")
_OTHER_RE = \
re.compile(r"^(?P<pre>.*?)(?P<module>[a-zA-Z0-9_.]*?)(?P<name>[a-zA-Z0-9_]+)\s*$")

def codeitem_directive(dirname, arguments, options, content,
        lineno, content_offset, block_set, state, state_machine):
    if not content:
        content = [u""]
  
    m = _CALLABLE_RE.match(u"".join(arguments))
    m2 = _OTHER_RE.match(u"".join(arguments))
    if m:
        g = m.groupdict()
        if g['rest'] is None:
            g['rest'] = ''
        if g['args'].strip():
            firstline = "%s%s **%s** (``%s``) %s" % (g['pre'].replace('*', r'\*'),
                                                     g['module'], g['name'],
                                                     g['args'], g['rest'])
        else: 
            firstline = "%s%s **%s** () %s" % (g['pre'].replace('*', r'\*'),
                                               g['module'], g['name'],
                                               g['rest'])
        if g['module']:
            target = '%s%s' % (g['module'], g['name'])
        else:
            target = g['name']
    elif m2:
        g = m2.groupdict()
        firstline = "%s%s **%s**" % (g['pre'].replace('*', r'\*'),
                                     g['module'], g['name'])
        if g['module']:
            target = '%s%s' % (g['module'], g['name'])
        else:
            target = g['name']
    else:
        firstline = u"".join(arguments)
        target = None
  
  
    dl = nodes.definition_list()
    di = nodes.definition_list_item()
    dl += di
  
    title_stuff, messages = state.inline_text(firstline, lineno)
    dt = nodes.term(firstline, *title_stuff)
    di += dt
  
    dd = nodes.definition()
    di += dd
  
    if target:
        dt['ids'] += [target]
  
    dl['classes'] += [dirname, 'code-item']
    _nested_parse(state, content, dd)
  
    return [dl]

codeitem_directive.arguments = (1, 0, True)
codeitem_directive.content = True
directives.register_directive ('attribute', codeitem_directive)

# This I think I understand, can't promise

def ref_role (name, raw_text, text, lineno, inliner,
        options=None, content=None):
    doc_tool = inliner.document.settings.doc_tool
    if options is None:
        options = {}
    if content is None:
        content = []

    link = doc_tool.link_resolver.get_named_link(text)

    if link is None:
        node = nodes.Text(text)
    else:
        node = nodes.reference(link.title, link.title, refuri=link.get_link(),
                **options)

    return [node], []

roles.register_local_role ('func', ref_role)
roles.register_local_role('mod', ref_role)
roles.register_local_role('data', ref_role)
roles.register_local_role('const', ref_role)
roles.register_local_role('class', ref_role)
roles.register_local_role('meth', ref_role)
roles.register_local_role('attr', ref_role)
roles.register_local_role('exc', ref_role)
roles.register_local_role('obj', ref_role)
roles.register_local_role('cdata', ref_role)
roles.register_local_role('cfunc', ref_role)
roles.register_local_role('cmacro', ref_role)
roles.register_local_role('ctype', ref_role)
roles.register_local_role('ref', ref_role)


class MyRestParser(object):
    def __init__(self, doc_tool=None):
        self.doc_tool = doc_tool
        self.writer = HotdocRestHtmlWriter()

    def translate(self, text, format_):
        if format_ != 'html':
            raise Exception("Unhandled format %s" % format_)
        parts = publish_parts(text, writer=self.writer,
                settings_overrides={'doc_tool': self.doc_tool})
        return parts['fragment']
