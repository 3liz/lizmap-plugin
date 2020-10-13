# Makefile for building/packaging qgis for lizmap hosting
#
.PHONY: package dist

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

FACTORY_PACKAGE_NAME ?= lizmap_qgis_plugin
FACTORY_PRODUCT_NAME ?= lizmap

PACKAGE=$(FACTORY_PACKAGE_NAME)
PACKAGEDIR=$(FACTORY_PRODUCT_NAME)
FILES = ../lizmap/__init__.py ../lizmap/server ../README.md

build/$(PACKAGEDIR):
	@echo "Packaging version '$(VERSION)'"
	@rm -rf build/$(PACKAGEDIR)
	@mkdir -p build/$(PACKAGEDIR)
	@cp -rLp $(FILES) build/$(PACKAGEDIR)/
	@sed "/^version=/c\version=$(VERSION)" ../lizmap/metadata.txt > build/$(PACKAGEDIR)/metadata.txt
  
dist: build/$(PACKAGEDIR)
  
package: dist
	@echo "Building package $(PACKAGE)"
	$(FACTORY_SCRIPTS)/make-package $(PACKAGE) $(VERSION) $(PACKAGEDIR) ./build

clean:
	@rm -r build

