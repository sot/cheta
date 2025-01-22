# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib
import sys
from pathlib import Path

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'cheta'
copyright = '2025, Smithsonian Astrophysical Observatory'
author = 'Tom Aldcroft'

# -- Path setup --------------------------------------------------------------
rootpath = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(rootpath))

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.viewcode',
              'sphinx_copybutton',
              'matplotlib.sphinxext.plot_directive',
             ]

templates_path = ['_templates']

# Version information from the package.
pkg = importlib.import_module(project)
version = pkg.__version__
release = version

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Do not show type hints in the documentation
autodoc_typehints = 'none'

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'pydata_sphinx_theme'

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": f"https://github.com/sot/{{project}}",
            "icon": "fab fa-github-square",
        },
    ],
    "navbar_start": ["navbar-project-version"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "secondary_sidebar_items": ["page-toc"],
}

# No left sidebar
html_sidebars = {
  "**": []
}

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# Copybutton configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# Plot directive configuration
plot_formats = ['png']
plot_html_show_formats = False
plot_html_show_source_link = False
plot_pre_code = """\
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from cheta import fetch_eng, fetch_sci
from ska_matplotlib import plot_cxctime

matplotlib.style.use("bmh")
"""
