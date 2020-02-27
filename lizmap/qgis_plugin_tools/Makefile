export LOCALES
export PLUGINNAME

QGIS_VERSION = release-3_4
# VERSION := $(cat ..metadata.txt | grep "version=" |  cut -d '=' -f2)

help:
	@echo Help about the Makefile
	@echo
	@echo Run PyLint
	@echo make pylint
	@echo
	@echo Run tests inside docker:
	@echo make docker_test
	@echo
	@echo Using translation Makefile commands
	@echo make i18n_1_prepare : To get strings in TS files
	@echo make i18n_2_push : To push strings to Transifex
	@echo make i18n_3_pull : To pull strings from Transifex
	@echo make i18n_4_compile : To compile TS to QM files
	@echo
	@echo Release plugin:
	@echo Do the last commit before the release with the metadata.txt
	@echo make release_zip : To generate the ZIP file and test it
	@echo Then make the tag and push it "git push remote --tags"
	@echo make release_tag : Not finished TODO
	@echo make release_upload : To upload the ZIP on plugins.qgis.org

pylint:
	@echo Running PyLint $(PLUGINNAME)
	@pylint --ignore=$(EXCLUDED_FILES) ../

test:
	@echo Use make docker_test for now

docker_test:
	@echo Running tests inside $(PLUGINNAME)
	@./infrastructure/docker_test.sh $(PLUGINNAME) $(QGIS_VERSION)

release_zip:
	@echo
	@echo -------------------------------
	@echo Exporting plugin to zip package
	@echo -------------------------------
	@rm -f ../$(PLUGINNAME).zip
	@cd .. && git-archive-all --prefix=$(PLUGINNAME)/ $(PLUGINNAME).zip
	@echo "Created package: $(PLUGINNAME).zip"

release_tag:
	@echo
	@echo -------------------------------
	@echo Create the commit and the tag locally
	@echo -------------------------------
	@echo Version :: $(VERSION)
	# @cd .. && METADATA=$(cat metadata.txt | grep "version=" |  cut -d '=' -f2) git tag v${METADATA}
	@cd .. && git commit -am 'Release version $(VERSION)'
	@cd .. && git tag $(VERSION)
	@echo Tag created, you should use git push upstream $(VERSION)

release_upload:
	@echo
	@echo -----------------------------------------
	@echo Uploading the plugin on plugins.qgis.org.
	@echo -----------------------------------------
	@./infrastructure/plugin_upload.py ../$(PLUGINNAME).zip

i18n_1_prepare:
	@echo Updating strings locally 1/4
	./infrastructure/update_strings.sh $(LOCALES)

i18n_2_push:
	@echo Push strings to Transifex 2/4
	@cd .. && tx push -s

i18n_3_pull:
	@echo Pull strings from Transifex 3/4
	@cd .. && tx pull -a

i18n_4_compile:
	@echo Compile TS files to QM 4/4
	@for f in $(LOCALES); do lrelease ../resources/i18n/$${f}.ts -qm ../resources/i18n/$${f}.qm; done
