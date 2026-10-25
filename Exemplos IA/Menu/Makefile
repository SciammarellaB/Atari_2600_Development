PYTHON ?= python3
export DASM STELLA

.PHONY: build check run test
build check run:
	@$(PYTHON) scripts/lab.py $@

test: build
	@PYTHONPATH=.tools/python $(PYTHON) scripts/check_menu.py
