"""Executa a ROM no py65: logica e timing, sem simular pixels/audio do TIA.

Instalacao opcional, restrita a este exemplo:
python3 -m pip install --target .tools/python py65==1.2.0
PYTHONPATH=.tools/python python3 scripts/check_game.py
"""

from pathlib import Path
import re

from py65.devices.mpu6502 import MPU


# A ROM e os simbolos vem do DASM. Os testes executam as instrucoes montadas,
# em vez de reimplementar o movimento ou a colisao em Python.
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/01-jogos/01-space-invaders"
SYMBOLS = {}
for line in (OUTPUT / "main.sym").read_text().splitlines():
    match = re.match(r"^(\w+)\s+([0-9a-fA-F]{4})\s", line)
    if match:
        SYMBOLS[match[1]] = int(match[2], 16)


class Bus:
    """Mapa minimo 6507: espelhos de RAM, entradas, timer e escritas do TIA."""

    def __init__(self):
        self.rom = (OUTPUT / "main.bin").read_bytes()
        self.ram = bytearray(256)
        self.joystick = 255
        self.switches = 255
        self.fire = 128
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
            # O primeiro decremento ocorre um ciclo apos a escrita. A leitura
            # absoluta termina quatro ciclos apos o inicio da instrucao.
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
            # py65 executa a escrita antes de atualizar processorCycles.
            # Aplicamos o periferico depois do step, no ultimo ciclo do STA.
            self.pending.append((address, value))


class Machine:
    """Avanca instrucoes e respeita a parada da CPU causada por WSYNC."""

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
        for _ in range(20000):
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
        # Empilha um endereco de retorno artificial. Isso permite testar uma
        # rotina da ROM sem gerar milhares de quadros entre casos de colisao.
        self.cpu.stPushWord(SYMBOLS["Frame"] - 1)
        self.cpu.pc = SYMBOLS[label]
        self.until("Frame")


def check_timing():
    """Verifica quadros, faixas e presenca dos dois players sem alternancia."""
    machine = Machine()
    machine.frame()
    previous = machine.cpu.processorCycles
    for _ in range(12):
        machine.frame()
        current = machine.cpu.processorCycles
        assert current - previous == 262 * 76, (current - previous) / 76
        previous = current
        blank = [(cycle // 76, value) for cycle, reg, value in machine.bus.events
                 if reg == 1]
        assert len(blank) == 4, blank
        assert [value for _, value in blank] == [0, 2, 0, 2], blank
        assert [blank[i + 1][0] - blank[i][0] for i in range(3)] == [168, 8, 16]
        # Os dois invasores superiores/inferiores aparecem em TODOS os quadros.
        for register in (0x1B, 0x1C):
            alien_writes = [(cycle, value) for cycle, reg, value in machine.bus.events
                            if reg == register and cycle // 76 < blank[1][0] and value]
            assert len(alien_writes) == 16, (register, len(alien_writes))
            assert all(cycle % 76 <= 22 for cycle, _ in alien_writes)
    print("OK: 12 quadros de 262 linhas; faixas 168/8/16; quatro invasores em cada quadro")

    # A espera da faixa de troca recebe diferentes atrasos de posicionamento.
    # Varremos todas as coordenadas da nave para detectar um quadro maior/menor
    # nas bordas de divisao por 15, inclusive com a formacao no limite inferior.
    for ship_x in range(16, 145):
        machine.set("ShipX", ship_x)
        machine.set("ShotX", ship_x + 3)
        machine.set("FleetX", 16 + (ship_x % 81))
        machine.set("FleetY", 64)
        machine.set("State", 2)
        before = machine.cpu.processorCycles
        machine.frame()
        assert machine.cpu.processorCycles - before == 262 * 76, ship_x
    print("OK: 262 linhas em todas as 129 posicoes horizontais da nave")


def check_controls():
    """Pressiona direcoes por tempo suficiente para exercitar os dois limites."""
    machine = Machine()
    machine.bus.joystick = 0xBF
    for _ in range(180):
        machine.call("UpdateGame")
    assert machine.get("ShipX") == 16
    machine.bus.joystick = 0x7F
    for _ in range(180):
        machine.call("UpdateGame")
    assert machine.get("ShipX") == 144
    machine.bus.joystick = 255
    machine.bus.fire = 0
    machine.call("UpdateGame")
    assert machine.get("ShotY") == 86
    shot_x = machine.get("ShotX")
    machine.call("UpdateGame")
    assert machine.get("ShotY") == 84 and machine.get("ShotX") == shot_x
    machine.set("ShotY", 0)
    machine.bus.fire = 128
    machine.call("UpdateGame")
    assert machine.get("ShotY") == 128
    print("OK: limites da nave; tiro unico; subida; saida pelo topo")


def check_hits():
    """Exercita acertos nas quatro posicoes e bordas do retangulo do tiro."""
    for target in range(4):
        for dx, dy, expected in ((-2, 2, False), (-1, 2, True), (7, 2, True),
                                 (8, 2, False), (2, -2, False), (2, -1, True),
                                 (2, 7, True), (2, 8, False)):
            machine = Machine()
            machine.set("ShotX", 32 + (target % 2) * 48 + dx)
            machine.set("ShotY", 12 + (target // 2) * 12 + dy)
            machine.call("CheckHits")
            assert machine.get("Remaining") == (3 if expected else 4), (target, dx, dy)
            if expected:
                assert machine.bus[SYMBOLS["Alive"] + target] == 0
                assert machine.get("ShotY") == 128
    print("OK: 32 casos de colisao, incluindo bordas e alvos das duas fileiras")


def check_endings():
    """Vence, testa clique de reinicio e provoca a chegada da formacao a base."""
    machine = Machine()
    for target in range(4):
        machine.set("ShotX", 35 + (target % 2) * 48)
        machine.set("ShotY", 14 + (target // 2) * 12)
        machine.call("CheckHits")
    assert machine.get("State") == 1 and machine.get("Remaining") == 0
    machine.bus.fire = 0
    machine.call("UpdateGame")
    assert machine.get("State") == 1
    machine.bus.fire = 128
    machine.call("UpdateGame")
    machine.bus.fire = 0
    machine.call("UpdateGame")
    assert machine.get("State") == 0 and machine.get("Remaining") == 4
    machine.set("FleetX", 96)
    machine.set("FleetY", 60)
    machine.set("MoveClock", 3)
    machine.bus.fire = 128
    machine.call("UpdateGame")
    assert machine.get("State") == 2 and machine.get("ShotY") == 128
    machine.bus.switches = 254
    machine.call("UpdateGame")
    assert machine.get("State") == 0 and machine.get("FleetY") == 12
    print("OK: vitoria; soltar/apertar para reiniciar; derrota; Game Reset")


# Estes testes nao substituem Stella: nao modelam pixels, HMOVE nem som.
# Falhas de timing ou de comportamento interrompem o comando com AssertionError.
if __name__ == "__main__":
    check_timing()
    check_controls()
    check_hits()
    check_endings()
