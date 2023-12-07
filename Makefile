version := $(shell python3 -c "import configparser; config = configparser.ConfigParser(); config.read('pyproject.toml'); print(config['tool.poetry']['version'][1:-1])")

daml_dit_ddit_files := $(shell find daml_dit_ddit -name '*.py') README.md
daml_dit_ddit_bdist := dist/daml_dit_ddit-$(version)-py3-none-any.whl
daml_dit_ddit_sdist := dist/daml_dit_ddit-$(version).tar.gz

build_dir := build/.dir
poetry_build_marker := build/.poetry.build
poetry_install_marker := build/.poetry.install

SRC_FILES=$(shell find daml_dit_ddit -type f)

## General Targets

.PHONY: all
all: clean test

.PHONY: clean
clean:
	find . -name *.pyc -print0 | xargs -0 rm
	find . -name __pycache__ -print0 | xargs -0 rm -fr
	rm -fr build dist $(LIBRARY_NAME).egg-info test-reports

.PHONY: deps
deps: $(poetry_install_marker)

.PHONY: publish
publish: build
	poetry publish

.PHONY: install
install: build
	pip3 install --force $(daml_dit_ddit_bdist)

.PHONY: build
build: typecheck $(daml_dit_ddit_bdist) $(daml_dit_ddit_sdist)

.PHONY: format
format:
	poetry run isort daml_dit_ddit
	poetry run black daml_dit_ddit


.PHONY: version
version:
	@echo $(version)

## Test Targets

.PHONY: typecheck
typecheck:
	poetry run python3 -m mypy --config-file pytest.ini -p daml_dit_ddit

.PHONY: test
test: typecheck

## File Targets

$(build_dir):
	@mkdir -p build
	@touch $@

$(daml_dit_ddit_bdist): $(poetry_build_marker)

$(daml_dit_ddit_sdist): $(poetry_build_marker)

$(poetry_build_marker): $(build_dir) pyproject.toml $(SRC_FILES)
	poetry build
	touch $@

$(poetry_install_marker): $(build_dir) poetry.lock
	touch $@

