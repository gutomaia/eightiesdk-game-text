"""Sphinx configuration of eightiesdk-game-text.

Built alone, or by the 8tsdk site with the same sources.
"""

import os
import sys
import re as _re
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

with open(os.path.join(HERE, '..', 'pyproject.toml'), 'rb') as _f:
    _poetry = tomllib.load(_f)['tool']['poetry']

project = 'Text'
author = 'Guto Maia'
copyright = '2026, Guto Maia'
release = version = _poetry['version']
html_title = f'{project} · {_poetry["name"]} {release}'

extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_design',
    'sphinx_copybutton',
]
source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}
exclude_patterns = ['_build', 'red', 'requirements.txt']
myst_enable_extensions = ['colon_fence', 'deflist', 'fieldlist', 'tasklist']
myst_heading_anchors = 3

autodoc_default_options = {'members': True, 'show-inheritance': True}
autodoc_member_order = 'bysource'
autodoc_mock_imports = []
napoleon_google_docstring = True

html_theme = 'furo'
html_static_path = []
html_copy_source = False

language = 'en'
locale_dirs = ['locale']
gettext_compact = False

# built alone with sphinx-multiversion, the same refs the site publishes
smv_tag_whitelist = r'^v\d+\.\d+\.\d+$'
smv_branch_whitelist = r'^0.0.x$'
smv_remote_whitelist = None


# The docstrings in this package show code, register maps and cost
# tables as indented blocks. reStructuredText reads an indented block
# as a block quote and a table-shaped paragraph as a broken definition
# list; both render as literal blocks here, which is what they are.

_LIST_ITEM = _re.compile(r'^(?:[-*+] |\d+[.)] |#\. |\.\. |:)')
# ``read_*`` is a glob, not a reference to a target called read
_GLOB = _re.compile(r'(\w)_(\\?\*)')


def _indent(line):
    return len(line) - len(line.lstrip(' '))


def _is_list_item(line):
    return bool(_LIST_ITEM.match(line.lstrip(' ')))


def _literal_blocks(app, what, name, obj, options, lines):
    lines[:] = [_GLOB.sub(r'\1\\_\2', line) for line in lines]
    out = []
    i = 0
    in_literal = False
    while i < len(lines):
        line = lines[i]
        if in_literal:
            if not line.strip() or _indent(line) > 0:
                out.append(line)
                i += 1
                continue
            in_literal = False
        if not line.strip():
            out.append(line)
            i += 1
            continue
        last = len(out) - 1
        while last >= 0 and not out[last].strip():
            last -= 1
        base_context = last < 0 or (
            _indent(out[last]) == 0 and not _is_list_item(out[last])
        )
        after_blank = last < len(out) - 1
        # an indented block after a blank line: code or a table
        if _indent(line) > 0 and base_context and after_blank:
            if last >= 0 and out[last].rstrip().endswith('::'):
                pass
            elif last >= 0 and out[last].rstrip().endswith(':'):
                out[last] = out[last].rstrip() + ':'
            else:
                out.extend(['::', ''])
            out.append(line)
            in_literal = True
            i += 1
            continue
        # a paragraph with ragged indentation that is not a definition
        if _indent(line) == 0 and not _is_list_item(line):
            end = i
            while end < len(lines) and lines[end].strip():
                end += 1
            paragraph = lines[i:end]
            ragged = any(_indent(p) > 0 for p in paragraph[1:])
            definition = all(_indent(p) > 0 for p in paragraph[1:])
            if ragged and not definition:
                out.extend(['::', ''])
                out.extend('    ' + p for p in paragraph)
                i = end
                continue
        out.append(line)
        i += 1
    lines[:] = out


def setup(app):
    app.connect('autodoc-process-docstring', _literal_blocks)
