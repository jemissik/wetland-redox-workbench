SPHINXOPTS ?=
SPHINXBUILD ?= sphinx-build
SOURCEDIR = docs
BUILDDIR = docs/_build

.PHONY: docs clean-docs

docs:
	$(SPHINXBUILD) $(SPHINXOPTS) -b html $(SOURCEDIR) $(BUILDDIR)/html

clean-docs:
	rm -rf $(BUILDDIR)
