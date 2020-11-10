#
# Makefile for building/packaging qgis for lizmap hosting
#
.PHONY: package dist

ifndef FABRIC
FABRIC:=$(shell [ -e .fabricrc ] && echo "fab -c .fabricrc" || echo "fab")
endif

ifdef CI_COMMIT_TAG
VERSION=$(CI_COMMIT_TAG)
else
ifdef CI_COMMIT_REF_NAME
VERSION=$(CI_COMMIT_REF_NAME)
else
VERSION=$(shell cat ../lizmap/metadata.txt | grep "version=" |  cut -d '=' -f2)
endif
endif


main:
	echo "Makefile for packaging infra components: select a task"

PACKAGE=qgis310_lizmap
PACKAGEDIR=lizmap
FILES = ../lizmap/__init__.py ../lizmap/server ../README.md

build2/$(PACKAGEDIR):
	@echo "Packaging version '$(VERSION)'"
	@rm -rf build2/$(PACKAGEDIR)
	@mkdir -p build2/$(PACKAGEDIR)
	@cp -rLp $(FILES) build2/$(PACKAGEDIR)/
	@sed "/^version=/c\version=$(VERSION)" ../lizmap/metadata.txt > build2/$(PACKAGEDIR)/metadata.txt

dist: build2/$(PACKAGEDIR)

package: dist
	@echo "Building package $(PACKAGE)"
	$(FABRIC) package:$(PACKAGE),versiontag=$(VERSION),files=$(PACKAGEDIR),directory=./build2

clean:
	@rm -r build2
