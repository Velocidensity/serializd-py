import os
import sys

sys.path.insert(0, os.path.abspath('../'))

project = 'Serializd-py'
copyright = '2023, Velocidensity'
author = 'Velocidensity'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.napoleon',
    'sphinxcontrib.autodoc_pydantic',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'furo'
html_static_path = ['_static']

autodoc_pydantic_model_show_json = True
autodoc_pydantic_settings_show_json = False
autodoc_pydantic_model_show_field_summary = False
