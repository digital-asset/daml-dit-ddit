version := $(shell python3 -c "import configparser; config = configparser.ConfigParser(); config.read('pyproject.toml'); print(config['tool.poetry']['version'][1:-1])")

daml_dit_api_files := $(shell find daml_dit_api -name '*.py') README.md
daml_dit_api_bdist := dist/daml_dit_api-$(version)-py3-none-any.whl
daml_dit_api_sdist := dist/daml_dit_api-$(version).tar.gz

build_dir := build/.dir
poetry_build_marker := build/.poetry.build
poetry_install_marker := build/.poetry.install

####################################################################################################
## GENERAL TARGETS                                                                                ##
####################################################################################################

.PHONY: all
all: clean test

.PHONY: clean
clean:
	find . -name *.pyc -print0 | xargs -0 rm
	find . -name __pycache__ -print0 | xargs -0 rm -fr
	rm -fr build dist $(LIBRARY_NAME).egg-info test-reports

.PHONY: deps
deps: $(poetry_install_marker)

.PHONY: build
build: package

.PHONY: package
package: $(daml_dit_api_bdist) $(daml_dit_api_sdist)

.PHONY: publish
publish: package
	poetry publish

.PHONY: version
version:
	@echo $(version)


####################################################################################################
## TEST TARGETS                                                                                   ##
####################################################################################################

.PHONY: typecheck
typecheck:
	poetry run python3 -m mypy -p daml_dit_api

.PHONY: test
test: typecheck


####################################################################################################
## file targets                                                                                   ##
####################################################################################################

$(build_dir):
	@mkdir -p build
	@touch $@

$(poetry_build_marker): $(build_dir) pyproject.toml $(dazl_files)
	poetry build
	touch $@

$(poetry_install_marker): $(build_dir) poetry.lock
	touch $@

$(daml_dit_api_bdist): $(poetry_build_marker)

$(daml_dit_api_sdist): $(poetry_build_marker)
