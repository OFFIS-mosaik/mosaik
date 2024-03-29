#!/usr/bin/env python3
#
# mosaik documentation build configuration file, created by
# sphinx-quickstart on Thu Dec  5 10:36:19 2013.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

from typing import cast
import mosaik
import mosaik_components.heatpump
import sphinx_rtd_theme
from urllib.request import urlretrieve
import os
import shutil

# Create a directory for the documentation of components of the mosaik ecosystem.
component_docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ecosystem', 'components')
os.makedirs(component_docs_dir, exist_ok=True)

# Integrate mosaik-heatpump docuemtantion from https://gitlab.com/mosaik/components/energy/mosaik-heatpump
# Files will be downloaded and integrated in mosaik documentation.

# Install mosaik-heatpump to allow integration of documentation from the code.
os.system('pip uninstall mosaik-heatpump -y')
os.system('pip install git+https://gitlab.com/mosaik/components/energy/mosaik-heatpump.git')
# Create a directory for the mosaik-heatpump documentation
mosaik_heatpump_docs_dir = os.path.join(component_docs_dir, 'mosaik-heatpump')
if os.path.exists(mosaik_heatpump_docs_dir):
    shutil.rmtree(mosaik_heatpump_docs_dir)
# Download documentation from mosaik-heatpump repository.
zip_file_dir = os.path.join(component_docs_dir, "doc.zip")
urlretrieve (
   "https://gitlab.com/mosaik/components/energy/mosaik-heatpump/-/archive/master/mosaik-heatpump-master.zip?path=docs",
   zip_file_dir
)
shutil.unpack_archive(zip_file_dir, component_docs_dir)
os.remove(zip_file_dir)
shutil.move(os.path.join(os.path.join(component_docs_dir, 'mosaik-heatpump-master-docs'), 'docs'),
            mosaik_heatpump_docs_dir)
os.rmdir(os.path.join(component_docs_dir, 'mosaik-heatpump-master-docs'))

mosaik_hp_version = mosaik_components.heatpump.__version__
rst_epilog = ".. |mosaik_hp_version| replace:: v{}".format(mosaik_hp_version)

# -- General configuration ----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.graphviz',
    'sphinx.ext.imgmath',
    'sphinx.ext.linkcode',
    'sphinx_rtd_theme',
    'sphinx_toolbox.more_autodoc.autotypeddict',
]

# -- Options for Graphviz -------------------------------------------------
graphviz_dot = 'dot'
graphviz_dot_args = ['-Tsvg']
graphviz_output_format = 'svg'

# -- Options for imgmath -------------------------------------------------
imgmath_image_format = 'svg'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'mosaik'
copyright = '2012-2024 OFFIS'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The mosaik version. Both variables return the same full version string.
version = mosaik.__version__
release = mosaik.__version__

rst_epilog = """
.. |mosaik| image:: /_static/favicon.png
"""

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for
# all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'mosaikdoc'


# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
# documentclass [howto/manual]).
latex_documents = [
    ('index', 'mosaik.tex', 'mosaik Documentation',
     'Mosaik Development Team', 'manual'),
]

# Build with XeLaTeX to use unicode characters
latex_engine = 'lualatex'

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output -------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'mosaik', 'mosaik Documentation',
     ['Mosaik Development Team'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'mosaik', 'mosaik Documentation',
     'Mosaik Development Team', 'mosaik', 'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# Intersphinx configuration to automatically link to the documentation
# of other projects when we use their methods and types.
# Each key is the name of the linked project. The corresponding value
# is the root of their documentation (and the location of their
# "inventory file" if not in the standard location; here they are, so
# we use None).
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'networkx': ('https://networkx.org/documentation/stable/', None),
}

# Autodoc
autodoc_member_order = 'bysource'

autodoc_typehints = "description"

# TODO: Check once type aliases work in type annotations
autodoc_type_aliases = {
    "InputData": "mosaik_api_v3.types.InputData",
    "SimConfig": "mosaik.scenario.SimConfig",
    "mosaik.scenario.SimConfig": "mosaik.scenario.SimConfig",
}

# This method is used to generate links to the source code in the
# documentation.
def linkcode_resolve(domain, info):
    # Don't create links for non-Python code.
    if domain != "py":
        return
    # Cannot create link if we don't know the Python module of the code
    if not info["module"]:
        return
    # Turn the module name into the URL on gitlab
    module = cast(str, info["module"])
    filename = module.replace(".", "/")
    
    init_modules = {"mosaik", "mosaik_api_v3"}
    if info["module"] in init_modules:
        filename += "/__init__"

    base_module = module.split(".", 1)[0]
    repos = {
        "mosaik": "https://gitlab.com/mosaik/mosaik/-/blob/develop/",
        "mosaik_api_v3": "https://gitlab.com/mosaik/api/mosaik-api-python/-/blob/master/",
    }
    if base_module in repos:
        return repos[base_module] + filename + ".py"
    else:
        return None
