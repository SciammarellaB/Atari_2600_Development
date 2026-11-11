"""Monta e executa somente Arenas; requer DASM e, para jogar, Stella."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def build():
    dasm = shutil.which(os.environ.get("DASM") or "dasm")
    if not dasm:
        raise ValueError("DASM indisponivel; informe DASM=/caminho/do/dasm")
    output = ROOT / "build"
    output.mkdir(exist_ok=True)
    rom = output / "main.bin"
    subprocess.run(
        [dasm, str(ROOT / "main.asm"), "-f3", f"-o{rom}",
         f"-l{output / 'main.lst'}", f"-s{output / 'main.sym'}"],
        cwd=ROOT, check=True,
    )
    return rom


def check(rom):
    data = rom.read_bytes()
    if len(data) != 8192:
        raise ValueError(f"ROM com {len(data)} bytes; esperados 8192")
    boot = bytes((0x2C, 0xF9, 0x1F, 0x4C, 0x00, 0xF0))
    for bank in (0, 1):
        start = bank * 4096
        vectors = [int.from_bytes(data[start + i:start + i + 2], "little")
                   for i in (4090, 4092, 4094)]
        if vectors != [0xFFD0] * 3 or data[start + 0xFD0:start + 0xFD6] != boot:
            raise ValueError(f"Boot F8 ou vetores invalidos no banco {bank}")
    trampolines_match = all(data[offset:offset + 10] == data[4096 + offset:4096 + offset + 10]
                            for offset in (0xFA0, 0xFC0))
    if data[4096] != 0x78 or not trampolines_match:
        raise ValueError("Reset invalido ou trampolines F8 diferentes")
    print("OK: ROM 8 KiB F8 NTSC; boot e vetores dos dois bancos", flush=True)


def run(rom):
    stella = shutil.which(os.environ.get("STELLA") or "stella")
    if not stella:
        raise ValueError("Stella indisponivel; informe STELLA=/caminho/do/stella")
    subprocess.run([stella, "-format", "NTSC", "-bs", "F8", str(rom)],
                   cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        action = sys.argv[1] if len(sys.argv) == 2 else ""
        if action not in ("build", "check", "run"):
            raise ValueError("Use build, check ou run")
        result = build()
        if action in ("check", "run"):
            check(result)
        if action == "run":
            run(result)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
