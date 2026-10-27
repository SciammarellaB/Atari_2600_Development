PYTHON ?= python3
export DASM STELLA

.PHONY: build check run test
build check run:
	@$(PYTHON) lab.py $@

test: build
	@$(PYTHON) check_tank.py
