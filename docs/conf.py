from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "Wetland Redox Workbench"
author = "Wetland Redox contributors"
copyright = "2026, Wetland Redox contributors"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_book_theme"
html_title = project
html_theme_options = {
    "show_navbar_depth": 3,
    "max_navbar_depth": 5,
    "show_toc_level": 3,
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
