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
suppress_warnings = ["autoapi"]

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
autoapi_ignore = ["*tests*", "*conftest*"]
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

    Also skip public ``async_`` methods as they are only intended
    to be used internally by other sync wrapped objects.
    """
    if what == "class" and (
        # Infer that the class is a sync wrapped class if it is the kr8s.Api class,
        # or is in kr8s.objects and inherits from a class in kr8s._objects.
        name == "kr8s.Api"
        or ("kr8s.objects" in name and obj.bases and "kr8s._objects" in obj.bases[0])
        # FIXME: It would be better to just check if the class is decorated with @sync
        # but sphinx-autoapi does not currently keep track of decorators
        # See https://github.com/readthedocs/sphinx-autoapi/issues/459
    ):
        for child in obj.children:
            if (
                child.type == "method"
                and not child.name.startswith("async_")
                and not child.name.startswith("_")
                and "async" in child.properties
            ):
                child.properties.remove("async")

    if (
        what == "method"
        and ("kr8s.objects" in name or "kr8s.asyncio.objects" in name)
        and obj.name.startswith("async_")
    ):
        skip = True
    return skip


def setup(app):
    app.add_css_file("css/custom.css")
    app.connect("autoapi-skip-member", remove_async_property)
