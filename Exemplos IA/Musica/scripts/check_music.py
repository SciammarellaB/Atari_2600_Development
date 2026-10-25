"""Executa a ROM montada no py65, sem simular pixels ou audio do TIA.

Instalacao opcional, restrita a este exemplo:
python3 -m pip install --target .tools/python py65==1.2.0
PYTHONPATH=.tools/python python3 scripts/check_music.py
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
    # Percorre a frase completa, inclusive transicoes de nota e retorno.
    for track, frames in ((2, 960), (1, 315), (0, 60)):
        machine.set("Track", track)
        machine.set("MusicStep", 0)
        machine.set("MusicClock", 0)
        for frame in range(frames):
            before = machine.cpu.processorCycles
            machine.frame()
            assert machine.cpu.processorCycles - before == 262 * 76
            events = machine.bus.events
            sync = [(c, v) for c, r, v in events if r == 0]
            assert [v for _, v in sync] == [2, 0]
            assert sync[1][0] // 76 - sync[0][0] // 76 == 3
            blank = [(c, v) for c, r, v in events if r == 1]
            assert [v for _, v in blank] == [0, 2]
            start, end = blank[0][0], blank[1][0]
            assert start // 76 - sync[1][0] // 76 == 37
            assert end // 76 - start // 76 == 192
            rows = defaultdict(list)
            for cycle, reg, value in events:
                if start <= cycle < end and reg in (0x0D, 0x0E, 0x0F):
                    rows[cycle // 76].append((reg, value))
            lines = sorted(rows)
            assert len(lines) == 192
            assert lines == list(range(lines[0], lines[0] + 192))
            for line in lines:
                assert [reg for reg, _ in rows[line]] == [0x0D, 0x0E, 0x0F] * 2
            for offset in range(0, 192, 4):
                assert all(rows[lines[offset]] == rows[lines[offset + repeat]]
                           for repeat in range(1, 4))
    # As entradas abaixo mudam a trilha no quadro, sem afetar o video.
    for joystick, switches, fire in ((0x7F, 0xFF, 0), (0xBF, 0xFF, 0x80),
                                     (0xFF, 0xFD, 0), (0xFF, 0xFF, 0x80),
                                     (0xFF, 0xFE, 0), (0x00, 0xFC, 0)):
        machine.bus.joystick = joystick
        machine.bus.switches = switches
        machine.bus.fire = fire
        before = machine.cpu.processorCycles
        machine.frame()
        assert machine.cpu.processorCycles - before == 262 * 76
    print("OK: 1341 quadros NTSC de 262 linhas; 3+37+192+30; playfield 48 x 4")


def check_controls():
    m = Machine()
    assert m.get("Track") == 2

    def release():
        m.bus.switches = m.bus.joystick = 0xFF
        m.bus.fire = 0x80
        m.call("UpdateMenu")

    def assert_restart(track):
        assert m.get("Track") == track
        assert (m.get("MusicStep"), m.get("MusicClock")) == (0, 0)
        assert {(r, v) for _, r, v in m.bus.events} >= {(0x19, 0), (0x1A, 0)}

    for joystick, delta in ((0x7F, 1), (0xDF, 1), (0xBF, -1), (0xEF, -1),
                            (0x5F, 1), (0xAF, -1)):
        for start in (0, 1, 2):
            release()
            m.set("Track", start)
            m.set("MusicStep", 7)
            m.set("MusicClock", 8)
            m.bus.events.clear()
            m.bus.joystick = joystick
            m.call("UpdateMenu")
            assert_restart((start + delta) % 3)
            m.set("MusicClock", 7)
            for _ in range(3):
                m.call("UpdateMenu")
                assert m.get("Track") == (start + delta) % 3
                assert m.get("MusicClock") == 7
    for track in (0, 1, 2):
        for joystick in (0xFF, 0x3F, 0xCF, 0x0F, 0x6F, 0x9F):
            release()
            m.set("Track", track)
            m.bus.joystick = joystick
            m.call("UpdateMenu")
            assert m.get("Track") == track
    for start in (0, 1, 2):
        release()
        m.set("Track", start)
        m.bus.switches = 0xFD
        m.bus.events.clear()
        m.call("UpdateMenu")
        assert_restart((start + 1) % 3)
        m.set("MusicClock", 7)
        for _ in range(10):
            m.call("UpdateMenu")
            assert m.get("MusicClock") == 7
            assert m.get("Track") == (start + 1) % 3
    for track in (0, 1, 2):
        release()
        m.set("Track", track)
        m.set("MusicStep", 7)
        m.set("MusicClock", 8)
        m.bus.fire = 0
        m.bus.events.clear()
        m.call("UpdateMenu")
        assert_restart(track)
        m.set("MusicClock", 7)
        for _ in range(10):
            m.call("UpdateMenu")
            assert m.get("MusicClock") == 7
    # Reset ganha de Select, joystick e Fire simultaneos; sempre volta a 2.
    release()
    m.bus.switches = 0xFC
    m.bus.joystick = 0x7F
    m.bus.fire = 0
    m.bus.events.clear()
    m.call("UpdateMenu")
    assert_restart(2)
    m.set("MusicClock", 7)
    m.call("UpdateMenu")
    assert m.get("MusicClock") == 7
    # Mudar no ultimo passo de Tensao nao pode indexar fora da Escala.
    release()
    m.set("Track", 2)
    m.set("MusicStep", 63)
    m.set("MusicClock", 14)
    m.bus.joystick = 0xBF
    m.frame()
    assert m.get("Track") == 1
    assert (m.get("MusicStep"), m.get("MusicClock")) == (0, 1)
    assert all(v == 0 for _, r, v in m.bus.events if r == 0x1A)
    print("OK: tres opcoes, navegacao circular por pressao, prioridades e troca entre canais")


def check_music():
    m = Machine()
    m.set("Track", 1)
    melody = (19, 17, 15, 14, 15, 17, 19, 21, 21)
    durations = (30,) * 7 + (60, 45)
    sustain = (22,) * 7 + (46, 0)
    release = (27,) * 7 + (56, 0)
    # AUDC=12, divisao por 6: aproxima Do4 Re4 Mi4 Fa4 ... Sib3.
    from math import log2
    targets = (261.6256, 293.6648, 329.6276, 349.2282, 329.6276,
               293.6648, 261.6256, 233.0819)
    pitches = [31400 / (6 * (value + 1)) for value in melody[:8]]
    assert pitches[:4] == sorted(pitches[:4])
    assert pitches[3:] == sorted(pitches[3:], reverse=True)
    assert all(abs(1200 * log2(actual / target)) < 40
               for actual, target in zip(pitches, targets))
    for _ in range(2):
        for step, duration in enumerate(durations):
            for clock in range(duration):
                assert (m.get("MusicStep"), m.get("MusicClock")) == (step, clock)
                m.bus.events.clear()
                m.call("UpdateMusic")
                audio = {r: v for _, r, v in m.bus.events}
                volume = 5 if clock < sustain[step] else 2 if clock < release[step] else 0
                assert audio == {0x15: 12, 0x17: melody[step], 0x19: volume, 0x1A: 0}
        assert (m.get("MusicStep"), m.get("MusicClock")) == (0, 0)
    m.set("Track", 0)
    for _ in range(100):
        m.bus.events.clear()
        m.call("UpdateMusic")
        assert {r: v for _, r, v in m.bus.events} == {0x19: 0, 0x1A: 0}
        assert (m.get("MusicStep"), m.get("MusicClock")) == (0, 0)
    print("OK: duas voltas de 315 quadros, 8 notas, Sib final longo, release e pausa")
    print("OK: Escala preservada; alturas a menos de 40 cents; mudo silencia ambos os canais")


def check_tension():
    m = Machine()
    loops = []
    for _ in range(2):
        frames = []
        for frame in range(960):
            assert (m.get("MusicStep"), m.get("MusicClock")) == (frame // 15, frame % 15)
            m.bus.events.clear()
            m.call("UpdateMusic")
            audio = {r: v for _, r, v in m.bus.events}
            assert 0x19 in audio and 0x1A in audio
            assert 0 <= audio[0x19] <= 5 and 0 <= audio[0x1A] <= 4
            assert all(0 <= v <= 31 for r, v in audio.items() if r in (0x17, 0x18))
            assert all(v in (4, 6, 8) for r, v in audio.items() if r in (0x15, 0x16))
            if frame % 15 >= 13:
                assert audio[0x19] == audio[0x1A] == 0
            frames.append(audio)
        assert (m.get("MusicStep"), m.get("MusicClock")) == (0, 0)
        loops.append(frames)
    assert loops[0] == loops[1], "Loop nao volta ao mesmo estado sonoro"
    frames = loops[0]
    phrases = [frames[i:i + 240] for i in range(0, 960, 240)]
    assert all(phrases[a] != phrases[b] for a in range(4) for b in range(a))
    assert sum(f[0x19] > 0 for f in frames) > 400
    assert any(f[0x19] and f[0x1A] for f in frames)
    assert any(f.get(0x16) == 6 and f[0x1A] for f in frames)
    assert any(f.get(0x16) == 8 and f[0x1A] for f in frames)
    assert any(f[0x19] == 0 and f[0x1A] > 0 for f in frames)
    # O motivo inicial sobe e quebra a expectativa com Sol -> Solb.
    attacks = [f.get(0x17) for f in frames[::15]]
    assert attacks[:8] == [29, None, 24, 29, 19, None, 20, 24]
    assert len({p for p in attacks if p is not None}) >= 9
    # O fim respira antes de retornar ao primeiro ataque.
    assert all(f[0x19] == f[0x1A] == 0 for f in frames[-45:])
    print("OK: Tensao em duas vozes, 64 passos/960 quadros, quatro frases distintas")
    print("OK: cromatismo, pausas, baixo, percussao, envelopes e duas voltas identicas")


def check_cursor():
    m = Machine()
    positions = []
    for track in (1, 2, 0):
        m.set("Track", track)
        m.set("MusicStep", 0)
        m.set("MusicClock", 0)
        m.frame()
        cursor = [(c, v) for c, r, v in m.bus.events if r == 0x1B and v]
        assert len({c // 76 for c, _ in cursor}) == 20
        positions.append([c // 76 - next(c // 76 for c, r, v in m.bus.events
                                       if r == 1 and v == 0) for c, _ in cursor])
    assert positions[1] == [line + 44 for line in positions[0]]
    assert positions[2] == [line + 44 for line in positions[1]]
    print("OK: indicador visivel nas tres linhas, sem alterar o timing do kernel")


if __name__ == "__main__":
    check_timing()
    check_controls()
    check_music()
    check_tension()
    check_cursor()
