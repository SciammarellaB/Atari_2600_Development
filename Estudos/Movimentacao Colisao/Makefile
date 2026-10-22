# Este estudo permanece na pasta original. O script monta somente main.asm.
# build gera ROM/listagem/simbolos; check verifica; run abre apos verificar.
PYTHON ?= python3
export DASM STELLA

# $@ passa o nome do alvo; @ oculta apenas a receita do make.
.PHONY: build check run
build check run:
	@$(PYTHON) lab.py $@
