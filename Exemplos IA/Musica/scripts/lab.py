"""Monta/verifica o exemplo e abre o Stella com estado local a este projeto."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from graphics import generate

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build"


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
    generate(OUTPUT / "menu.inc")
    rom = OUTPUT / "main.bin"
    subprocess.run([
        executable("DASM", "dasm"), str(ROOT / "main.asm"), "-f3",
        f"-I{ROOT / 'include'}", f"-I{OUTPUT}", f"-o{rom}",
        f"-l{OUTPUT / 'main.lst'}", f"-s{OUTPUT / 'main.sym'}",
    ], cwd=ROOT, check=True)
    data = rom.read_bytes()
    if len(data) != 4096:
        raise ValueError(f"ROM com {len(data)} bytes; esperado: 4096")
    vectors = [int.from_bytes(data[i:i + 2], "little") for i in (4090, 4092, 4094)]
    if len(set(vectors)) != 1 or not 0xF000 <= vectors[0] < 0xFFFA:
        raise ValueError("Vetores invalidos")
    if data[vectors[0] - 0xF000] != 0x78:
        raise ValueError("Vetor nao aponta para SEI em Reset")
    print(f"OK: ROM 4K; NMI/RESET/IRQ = ${vectors[0]:04X}")
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
            "-format", "NTSC", "-bs", "4K", "-audio.enabled", "1", str(rom),
        ], cwd=ROOT)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
