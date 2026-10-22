# O exemplo e independente dos outros diretorios do repositorio.
# PATTERN permite manter o mesmo comando usado nos estudos do laboratorio.
PYTHON ?= python3
PATTERN ?= 01-jogos/01-space-invaders
export PATTERN DASM STELLA

# A logica de caminhos/checagem fica no Python para nao depender de um shell.
.PHONY: build check run
build check run:
	@$(PYTHON) scripts/lab.py $@
