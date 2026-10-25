"""Executa a ROM montada no py65, sem simular pixels ou audio do TIA.

Instalacao opcional, restrita a este exemplo:
python3 -m pip install --target .tools/python py65==1.2.0
PYTHONPATH=.tools/python python3 scripts/check_menu.py
"""

from collections import defaultdict
from pathlib import Path
import re

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build"
SYMBOLS = {}
for line in (OUTPUT / "main.sym").read_text().splitlines():
    match = re.match(r"^(\w+)\s+([0-9a-fA-F]{4})\s", line)
    if match:
        SYMBOLS[match[1]] = int(match[2], 16)


class Bus:
    """Mapa minimo 6507: ROM, espelhos de RAM, entradas, timer e TIA."""

    def __init__(self):
        self.rom = (OUTPUT / "main.bin").read_bytes()
        assert len(self.rom) == 4096, len(self.rom)
        self.ram = bytearray(256)
        self.joystick = 0xFF
        self.switches = 0xFF
        self.fire = 0x80
        self.cpu = None
        self.pending = []
        self.events = []
        self.timer_value = 0
        self.timer_start = 0

    def __getitem__(self, address):
        address &= 0x1FFF
        if address & 0x1000:
            return self.rom[address & 0xFFF]
        if not address & 0x80:
            return self.fire if address & 0xF == 0xC else 0
        if not address & 0x200:
            return self.ram[address & 255]
        if address == 0x280:
            return self.joystick
        if address == 0x282:
            return self.switches
        if address == 0x284:
            # A leitura absoluta termina quatro ciclos apos o inicio da
            # instrucao. O primeiro decremento segue a escrita do timer.
            elapsed = self.cpu.processorCycles + 4 - self.timer_start
            ticks = (elapsed + 63) // 64
            if ticks <= self.timer_value:
                return self.timer_value - ticks
            zero_at = (self.timer_value - 1) * 64 + 1
            return (-(elapsed - zero_at - 63)) & 255
        return 0

    def __setitem__(self, address, value):
        address &= 0x1FFF
        if address & 0x1000:
            raise AssertionError("A ROM recebeu uma escrita")
        if address & 0x80 and not address & 0x200:
            self.ram[address & 255] = value
        else:
            # O periferico recebe a escrita no ultimo ciclo da instrucao.
            self.pending.append((address, value))


class Machine:
    """Executa instrucoes da ROM e a parada da CPU causada por WSYNC."""

    def __init__(self):
        self.bus = Bus()
        self.cpu = MPU(memory=self.bus, pc=None)
        self.bus.cpu = self.cpu
        self.until("Frame")

    def step(self):
        self.cpu.step()
        cycle = self.cpu.processorCycles
        for address, value in self.bus.pending:
            if address == 0x296:
                self.bus.timer_start = cycle
                self.bus.timer_value = value
            elif not address & 0x80:
                register = address & 0x3F
                self.bus.events.append((cycle, register, value))
                if register == 2:
                    self.cpu.processorCycles = ((cycle + 75) // 76) * 76
        self.bus.pending.clear()

    def until(self, label):
        for _ in range(40000):
            if self.cpu.pc == SYMBOLS[label]:
                return
            self.step()
        raise AssertionError(f"Execucao nao chegou a {label}")

    def frame(self):
        self.bus.events.clear()
        self.step()
        self.until("Frame")

    def get(self, label):
        return self.bus[SYMBOLS[label]]

    def set(self, label, value):
        self.bus[SYMBOLS[label]] = value

    def call(self, label):
        # Endereco de retorno artificial para exercitar a rotina montada.
        self.cpu.stPushWord(SYMBOLS["Frame"] - 1)
        self.cpu.pc = SYMBOLS[label]
        self.until("Frame")


def check_timing():
    machine = Machine()
    machine.frame()
    for players in (1, 2):
        machine.set("Players", players)
        for _ in range(12):
            before = machine.cpu.processorCycles
            music_before = (machine.get("MusicStep"), machine.get("MusicClock"))
            machine.frame()
            elapsed = machine.cpu.processorCycles - before
            assert elapsed == 262 * 76, (players, elapsed / 76)
            step, clock = music_before
            music_expected = ((step + 1) % 32, 0) if clock == 14 else (step, clock + 1)
            assert (machine.get("MusicStep"), machine.get("MusicClock")) == music_expected
            events = machine.bus.events
            sync = [(cycle, value) for cycle, reg, value in events if reg == 0]
            assert [value for _, value in sync] == [2, 0], sync
            assert sync[1][0] // 76 - sync[0][0] // 76 == 3, sync
            blank = [(cycle, value) for cycle, reg, value in events if reg == 1]
            assert [value for _, value in blank] == [0, 2], blank
            visible_start, visible_end = blank[0][0], blank[1][0]
            assert visible_end // 76 - visible_start // 76 == 192, blank
            assert visible_start // 76 - sync[1][0] // 76 == 37, (sync, blank)
            rows = defaultdict(list)
            for cycle, reg, value in events:
                if visible_start <= cycle < visible_end and reg in (0x0D, 0x0E, 0x0F):
                    rows[cycle // 76].append((reg, value))
            assert len(rows) == 192, len(rows)
            lines = sorted(rows)
            assert lines == list(range(lines[0], lines[0] + 192)), lines
            for line in lines:
                assert [reg for reg, _ in rows[line]] == [0x0D, 0x0E, 0x0F] * 2, (
                    line, rows[line])
            for offset in range(0, 192, 4):
                assert all(rows[lines[offset]] == rows[lines[offset + repeat]]
                           for repeat in range(1, 4)), offset
    print("OK: 24 quadros de 262 linhas; 3 VSYNC + 37 blank + 192 visiveis + 30 overscan")
    print("OK: 48 linhas logicas repetidas 4 vezes; seis escritas PF por scanline")


def check_controls():
    machine = Machine()
    assert machine.get("Players") == 1
    for joystick, expected in ((0x7F, 2), (0xEF, 1), (0xDF, 2), (0xBF, 1),
                               (0x5F, 2), (0xAF, 1)):
        machine.bus.joystick = joystick
        machine.call("UpdateMenu")
        assert machine.get("Players") == expected, (hex(joystick), expected)
    for players in (1, 2):
        for joystick in (0xFF, 0x3F, 0xCF, 0x0F, 0x6F, 0x9F):
            machine.set("Players", players)
            machine.bus.joystick = joystick
            machine.call("UpdateMenu")
            assert machine.get("Players") == players, (players, hex(joystick))
    machine.bus.joystick = 0xFF
    machine.bus.switches = 0xFD
    machine.call("UpdateMenu")
    selected = machine.get("Players")
    assert selected == 1
    for _ in range(20):
        machine.call("UpdateMenu")
        assert machine.get("Players") == selected
    machine.bus.switches = 0xFF
    machine.call("UpdateMenu")
    machine.bus.switches = 0xFD
    machine.call("UpdateMenu")
    assert machine.get("Players") == 2
    machine.bus.switches = 0xFF
    machine.call("UpdateMenu")
    machine.set("MusicStep", 7)
    machine.set("MusicClock", 9)
    machine.bus.switches = 0xFE
    machine.call("UpdateMenu")
    assert machine.get("Players") == 1
    assert (machine.get("MusicStep"), machine.get("MusicClock")) == (0, 0)
    machine.set("Players", 2)
    machine.set("MusicStep", 5)
    machine.set("MusicClock", 7)
    for _ in range(20):
        machine.call("UpdateMenu")
        assert machine.get("Players") == 2
        assert (machine.get("MusicStep"), machine.get("MusicClock")) == (5, 7)
    machine.bus.switches = 0xFF
    machine.call("UpdateMenu")
    machine.bus.switches = 0xFE
    machine.call("UpdateMenu")
    assert machine.get("Players") == 1
    assert (machine.get("MusicStep"), machine.get("MusicClock")) == (0, 0)
    print("OK: direcoes, diagonais e opostos; Select e Reset somente em nova pressao")


def check_music():
    machine = Machine()
    machine.bus.events.clear()
    initial = (machine.get("MusicStep"), machine.get("MusicClock"))
    previous = initial
    states = set()
    for _ in range(480):
        event_start = len(machine.bus.events)
        machine.call("UpdateMusic")
        current = (machine.get("MusicStep"), machine.get("MusicClock"))
        step, clock = previous
        expected = ((step + 1) % 32, 0) if clock == 14 else (step, clock + 1)
        assert current == expected, (previous, current, expected)
        volumes = [value for _, reg, value in machine.bus.events[event_start:]
                   if reg == 0x19]
        assert len(volumes) == 1, volumes
        if clock == 14:
            assert volumes == [0], (step, clock, volumes)
        states.add(current)
        previous = current
    assert previous == initial and len(states) == 480
    audio = defaultdict(list)
    for _, reg, value in machine.bus.events:
        if reg in (0x15, 0x17, 0x19):
            audio[reg].append(value)
    assert audio[0x15] and set(audio[0x15]) == {4}, audio[0x15]
    assert audio[0x17] and all(0 <= value <= 31 for value in audio[0x17])
    assert len(set(audio[0x17])) >= 4, set(audio[0x17])
    assert audio[0x19] and all(0 <= value <= 4 for value in audio[0x19])
    assert 0 in audio[0x19] and any(audio[0x19]), set(audio[0x19])
    print("OK: musica percorre 32 notas/480 atualizacoes, volta ao inicio e inclui pausas")
    print("OK: canal 0 com AUDC=4, frequencias 0..31 e volumes 0..4")


def check_cursor_and_fire():
    machine = Machine()
    positions = []
    for players in (1, 2):
        machine.set("Players", players)
        machine.frame()
        cursor = [(cycle, value) for cycle, reg, value in machine.bus.events
                  if reg == 0x1B and value]
        assert 1 <= len({cycle // 76 for cycle, _ in cursor}) <= 32, cursor
        positions.append([(reg, cycle % 76, value)
                          for cycle, reg, value in machine.bus.events
                          if reg in (0x10, 0x20)])
        assert positions[-1], "Cursor sem posicionamento horizontal"
    assert positions[0] != positions[1], positions
    for players in (1, 2):
        machine.set("Players", players)
        machine.bus.fire = 0
        for _ in range(40):
            before = machine.cpu.processorCycles
            machine.frame()
            assert machine.get("Players") == players
            assert machine.cpu.processorCycles - before == 262 * 76
            assert any(reg == 0x1B and value for _, reg, value in machine.bus.events)
        machine.bus.fire = 0x80
        machine.frame()
        assert machine.get("Players") == players
    print("OK: cursor muda de posicao; botao fire mantem o menu para 1 e 2 jogadores")


if __name__ == "__main__":
    check_timing()
    check_controls()
    check_music()
    check_cursor_and_fire()
