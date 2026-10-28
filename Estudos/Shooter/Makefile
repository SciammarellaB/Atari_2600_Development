PYTHON ?= python3
export DASM STELLA

.PHONY: build check run test
build check run:
	@$(PYTHON) lab.py $@

test: check
	@$(PYTHON) check_shooter.py
	@$(PYTHON) check_powerups.py
