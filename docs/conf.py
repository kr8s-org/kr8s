# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import datetime

project = "kr8s"
author = "Dask Developers, NVIDIA"
copyright = f"{datetime.date.today().year}, {author}"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxcontrib.mermaid",
    "myst_parser",
    "sphinx.ext.autodoc",
    "autoapi.extension",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- copybutton configuration ---------------------------------------------------

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# -- autoapi configuration ---------------------------------------------------

autodoc_typehints = "signature"  # autoapi respects this

autoapi_type = "python"
autoapi_dirs = ["../kr8s"]
autoapi_template_dir = "_templates/autoapi"
autoapi_options = [
    "members",
    "inherited-members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
autoapi_ignore = ["*tests*", "*conftest*", "*asyncio*"]
# autoapi_python_use_implicit_namespaces = True
autoapi_keep_files = True
# autoapi_generate_api_docs = False


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

html_theme_options = {
    "light_logo": "branding/logo-solo.png",
    "dark_logo": "branding/logo-solo.png",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}


def remove_async_property(app, what, name, obj, skip, options):
    """Remove async property from sync wrapped methods.

    Find all sync classes that inherit from async classes
    and remove the async property from their wrapped methods.
    """
    if (
        what == "class"
        and "kr8s.objects" in name
        and obj.bases
        and "kr8s._objects" in obj.bases[0]
    ):
        for child in obj.children:
            if child.type == "method":
                if child.name.startswith("async_"):
                    child.properties.append("sync-wrapped")
                    continue
                if not child.name.startswith("_"):
                    if "async" in child.properties:
                        child.properties.remove("async")

    if what == "method" and "sync-wrapped" in obj.properties:
        skip = True
    return skip


def setup(app):
    app.add_css_file("css/custom.css")
    app.connect("autoapi-skip-member", remove_async_property)
