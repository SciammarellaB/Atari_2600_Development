"""Monta, verifica a estrutura e executa somente este estudo de movimento em 8 direcoes."""

# Biblioteca padrao: caminhos, ferramentas existentes e processos com argumentos
# separados, sem interpretar texto no shell. ROOT e a pasta deste estudo.
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


# Reutiliza o DASM instalado; DASM pode indicar outro executavel.
# A propria ferramenta gera as tres saidas dentro de build/.
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


# 4 KiB cobrem $F000..$FFFF. Os seis bytes finais sao tres enderecos little
# endian; devem apontar ao SEI ($78) de Reset em $F000. Nao valida video/ciclos.
def check(rom):
    data = rom.read_bytes()
    if len(data) != 4096:
        raise ValueError(f"ROM com {len(data)} bytes; esperados 4096")
    vectors = [int.from_bytes(data[i:i + 2], "little") for i in (4090, 4092, 4094)]
    if vectors != [0xF000] * 3 or data[0] != 0x78:
        raise ValueError("Vetores invalidos ou Reset sem SEI em $F000")
    print("OK: 4096 bytes; NMI/RESET/IRQ = $F000", flush=True)


# STELLA tem prioridade; depois busca no PATH e no aplicativo macOS instalado.
# NTSC e cartucho 4K sao explicitos. Nada e instalado por este comando.
def run(rom):
    requested = os.environ.get("STELLA")
    stella = shutil.which(requested or "stella")
    if not stella and not requested:
        app = Path("/Applications/Stella.app/Contents/MacOS/stella")
        if app.is_file():
            stella = str(app)
    if not stella:
        raise ValueError("Stella indisponivel; informe STELLA=/caminho/do/stella")
    subprocess.run(
        [stella, "-format", "NTSC", "-bs", "4K", str(rom)], cwd=ROOT, check=True,
    )


# O alvo seleciona a acao; falhas encerram o make com codigo nao zero.
# Nao existe selecao de outros exemplos: o escopo e somente esta pasta.
if __name__ == "__main__":
    try:
        action = sys.argv[1]
        if action not in ("build", "check", "run"):
            raise ValueError("Use build, check ou run")
        result = build()
        if action in ("check", "run"):
            check(result)
        if action == "run":
            run(result)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
