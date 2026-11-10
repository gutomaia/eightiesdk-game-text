# This project's documentation: `make html` builds it alone; the 8tsdk
# site builds it with the same sources. The toolchain is requirements.txt
# (`pip install -r requirements.txt`), or SPHINXBUILD= another install.

SPHINXBUILD ?= sphinx-build
SPHINXINTL  ?= sphinx-intl
SOURCEDIR    = .
BUILDDIR     = _build
LANGUAGE    ?= pt_BR

.PHONY: html gettext intl clean versions

html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)

# the translatable strings, then the .po files of LANGUAGE under locale/
gettext:
	$(SPHINXBUILD) -b gettext "$(SOURCEDIR)" "$(BUILDDIR)/gettext" $(SPHINXOPTS)

intl: gettext
	$(SPHINXINTL) update -p "$(BUILDDIR)/gettext" -l $(LANGUAGE)

# every published ref, when sphinx-multiversion is installed
versions:
	sphinx-multiversion "$(SOURCEDIR)" "$(BUILDDIR)/versions" $(SPHINXOPTS)

clean:
	rm -rf "$(BUILDDIR)"
