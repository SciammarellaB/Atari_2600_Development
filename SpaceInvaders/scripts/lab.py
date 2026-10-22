"""Monta a ROM, confere tamanho/vetores e opcionalmente abre o Stella."""

import os
from pathlib import Path
import shutil
import subprocess
import sys


# Todos os caminhos partem deste laboratorio; nomes externos sao argumentos,
# nunca comandos interpolados no shell. DASM/STELLA podem indicar executaveis.
ROOT = Path(__file__).resolve().parents[1]
PATTERN = os.environ.get("PATTERN") or "01-jogos/01-space-invaders"


def executable(variable, name, extra=None):
    """Procura uma ferramenta ja instalada, sem instalar nada globalmente."""
    requested = os.environ.get(variable)
    found = shutil.which(requested or name)
    if not found and not requested and extra and Path(extra).is_file():
        found = extra
    if not found:
        raise ValueError(f"{name} indisponivel; informe {variable}=/caminho/{name}")
    return found


def build(pattern):
    """O DASM gera ROM bruta (-f3), listagem e simbolos dentro de build/."""
    source = (ROOT / "patterns" / pattern / "main.asm").resolve()
    if not source.is_relative_to(ROOT / "patterns") or not source.is_file():
        raise ValueError(f"Padrao inexistente: {pattern}")
    destination = ROOT / "build" / pattern
    destination.mkdir(parents=True, exist_ok=True)
    rom = destination / "main.bin"
    subprocess.run([
        executable("DASM", "dasm"), str(source), "-f3",
        f"-I{ROOT / 'include'}", f"-o{rom}",
        f"-l{destination / 'main.lst'}", f"-s{destination / 'main.sym'}",
    ], cwd=ROOT, check=True)

    # Uma ROM de 4 KiB mapeia $F000..$FFFF. Os tres vetores devem apontar
    # para o mesmo Reset dentro dela; o opcode SEI ($78) inicia esse codigo.
    data = rom.read_bytes()
    if len(data) != 4096:
        raise ValueError(f"ROM com {len(data)} bytes; esperado: 4096")
    vectors = [int.from_bytes(data[i:i + 2], "little") for i in (4090, 4092, 4094)]
    if len(set(vectors)) != 1 or not 0xF000 <= vectors[0] < 0xFFFA:
        raise ValueError(f"Vetores invalidos: {vectors}")
    if data[vectors[0] - 0xF000] != 0x78:
        raise ValueError("O vetor nao aponta para SEI em Reset")
    print(f"OK: {pattern}: 4096 bytes; NMI/RESET/IRQ = ${vectors[0]:04X}")
    return rom


def main():
    """check descobre as ROMs; run monta/verifica antes de abrir o emulador."""
    action = sys.argv[1]
    if action == "check":
        for source in sorted((ROOT / "patterns").glob("*/*/main.asm")):
            build(str(source.parent.relative_to(ROOT / "patterns")))
    else:
        rom = build(PATTERN)
        if action == "run":
            stella = executable("STELLA", "stella",
                                "/Applications/Stella.app/Contents/MacOS/Stella")
            subprocess.Popen([stella, "-format", "NTSC", "-bs", "4K", str(rom)], cwd=ROOT)


# Falhas do montador ou das verificacoes interrompem o make com codigo nao zero.
if __name__ == "__main__":
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
