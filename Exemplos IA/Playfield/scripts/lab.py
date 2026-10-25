"""Gera os mapas, monta/verifica a ROM e abre o Stella com estado local."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from rooms import BANK_COUNT, generate
from hud import generate as generate_hud

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build"
BANK_SIZE = 4096


def executable(variable, name):
    requested = os.environ.get(variable)
    found = shutil.which(requested or name)
    if not found and not requested and name == "stella":
        mac = Path("/Applications/Stella.app/Contents/MacOS/Stella")
        if mac.is_file():
            found = str(mac)
    if not found:
        raise ValueError(f"{name} indisponivel; informe {variable}=/caminho/{name}")
    return found


def build():
    OUTPUT.mkdir(exist_ok=True)
    generate_hud(OUTPUT / "hud.inc")
    banks, baseline_symbols, reset = [], None, None
    assembler = executable("DASM", "dasm")
    for bank in range(BANK_COUNT):
        destination = OUTPUT / f"bank{bank}"
        destination.mkdir(exist_ok=True)
        generate(destination / "rooms.inc", bank=bank)
        shutil.copyfile(destination / "rooms.inc", OUTPUT / f"rooms-bank{bank}.inc")
        bank_rom = destination / "main.bin"
        subprocess.run([
            assembler, str(ROOT / "main.asm"), "-f3", f"-DBANK_ID={bank}",
            f"-I{ROOT / 'include'}", f"-I{destination}", f"-I{OUTPUT}",
            f"-o{bank_rom}", f"-l{destination / 'main.lst'}",
            f"-s{destination / 'main.sym'}",
        ], cwd=ROOT, check=True)
        data = bank_rom.read_bytes()
        if len(data) != BANK_SIZE:
            raise ValueError(f"Banco {bank} com {len(data)} bytes; esperado: {BANK_SIZE}")
        vectors = [int.from_bytes(data[i:i + 2], "little") for i in (4090, 4092, 4094)]
        if len(set(vectors)) != 1 or not 0xF000 <= vectors[0] < 0xFFF4:
            raise ValueError(f"Banco {bank}: vetores invalidos")
        if data[vectors[0] - 0xF000] != 0x78:
            raise ValueError(f"Banco {bank}: vetor nao aponta para SEI em Reset")
        if reset is not None and vectors[0] != reset:
            raise ValueError(f"Banco {bank}: Reset mudou de endereco")
        reset = vectors[0]
        symbols = {}
        for line in (destination / "main.sym").read_text().splitlines():
            match = re.match(r"^(\S+)\s+([0-9a-fA-F]{4,8})(?:\s|$)", line)
            if match and match[1] != "BANK_ID":
                symbols[match[1]] = int(match[2], 16)
        if not symbols:
            raise ValueError(f"Banco {bank}: tabela de simbolos vazia")
        if baseline_symbols is not None and symbols != baseline_symbols:
            changed = sorted(name for name in symbols.keys() | baseline_symbols.keys()
                             if symbols.get(name) != baseline_symbols.get(name))
            raise ValueError(f"Banco {bank}: enderecos divergentes: {', '.join(changed[:8])}")
        baseline_symbols = symbols
        banks.append(data)
    rom = OUTPUT / "main.bin"
    rom.write_bytes(b"".join(banks))
    # Ferramentas de diagnostico usam os mesmos enderecos nos oito bancos.
    for suffix in ("lst", "sym"):
        shutil.copyfile(OUTPUT / "bank0" / f"main.{suffix}", OUTPUT / f"main.{suffix}")
    print(f"OK: ROM F4 32K; 8 bancos de 4K; NMI/RESET/IRQ = ${reset:04X}")
    return rom


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "check", "run"))
    args = parser.parse_args()
    rom = build()
    if args.action == "run":
        state = ROOT / ".tools/stella"
        state.mkdir(parents=True, exist_ok=True)
        subprocess.Popen([
            executable("STELLA", "stella"), "-basedir", str(state),
            "-format", "NTSC", "-bs", "F4", "-audio.enabled", "1", str(rom),
        ], cwd=ROOT)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
