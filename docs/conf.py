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
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "changelog.md",
    "reference/**",
    "technical/**",
    "user-guide/boa-results.md",
    "user-guide/configuration.md",
    "user-guide/model-observation-comparison.md",
    "user-guide/model-setup.md",
    "user-guide/observation-data.md",
    "workshop/2026-07/github-ssh-setup.md",
    "workshop/2026-07/osc-basics.md",
    "workshop/2026-07/part1-osc-github-setup-instructions.md",
    "workshop/2026-07/part1-setup-email-draft.md",
    "workshop/2026-07/part2-setup.md",
    "workshop/2026-07/setup-homework.md",
    "workshop/2026-07/tutorials/**",
]

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
myst_heading_anchors = 3
