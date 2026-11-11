"""Confere a ROM F8 8K com py65: campanha, chefes e estabilidade do raster.

Requer py65 somente para desenvolvimento. O barramento registra as escritas
do TIA e os WSYNCs; nao substitui a verificacao visual no Stella/hardware.
"""
from pathlib import Path
import re
import sys

from py65.devices.mpu6502 import MPU

ROOT = Path(__file__).resolve().parent
ROM = (ROOT / "build/main.bin").read_bytes()
SYMBOLS = {}
for line in (ROOT / "build/main.sym").read_text().splitlines():
    match = re.match(r"^(\w+)\s+([0-9a-fA-F]{4})\s", line)
    if match:
        SYMBOLS[match[1]] = int(match[2], 16)


class Bus:
    def __init__(self, bank=0):
        self.bank = bank
        self.banks = [bank]
        self.ram = bytearray(128)
        self.joystick = 0xFF
        self.fire = 0x80
        self.switches = 0xFF
        self.pending = []
        self.events = []
        self.tia = {}

    def __getitem__(self, address):
        address &= 0x1FFF
        if address in (0x1FF8, 0x1FF9):
            self.bank = address - 0x1FF8
            self.banks.append(self.bank)
        if address & 0x1000:
            return ROM[self.bank * 4096 + (address & 0xFFF)]
        if address == 0x280:
            return self.joystick
        if address == 0x282:
            return self.switches
        if address == 0x0C:
            return self.fire
        if address & 0x80 and not address & 0x200:
            return self.ram[address & 0x7F]
        return 0

    def __setitem__(self, address, value):
        address &= 0x1FFF
        if address in (0x1FF8, 0x1FF9):
            self.bank = address - 0x1FF8
            self.banks.append(self.bank)
            return
        assert not address & 0x1000, ("Escrita na ROM", hex(address))
        if address & 0x80 and not address & 0x200:
            self.ram[address & 0x7F] = value
        elif not address & 0x80:
            self.pending.append((address & 0x3F, value))
            self.tia[address & 0x3F] = value


class Machine:
    def __init__(self, bank=0):
        self.bus = Bus(bank)
        self.cpu = MPU(memory=self.bus, pc=None)
        self.until("Frame")

    def step(self):
        self.cpu.step()
        cycle = self.cpu.processorCycles
        for register, value in self.bus.pending:
            self.bus.events.append((cycle, register, value))
            if register == 2:
                self.cpu.processorCycles = ((cycle + 75) // 76) * 76
        self.bus.pending.clear()

    def until(self, label):
        for _ in range(30000):
            if self.cpu.pc == SYMBOLS[label] and self.bus.bank == 1:
                return
            self.step()
        raise AssertionError(f"CPU nao chegou a {label}; PC=${self.cpu.pc:04X}")

    def get(self, label):
        return self.bus[SYMBOLS[label]]

    def set(self, **values):
        for label, value in values.items():
            self.bus[SYMBOLS[label]] = value

    def fire(self, pressed):
        self.bus.fire = 0 if pressed else 0x80
        if "FireDown" in SYMBOLS:
            self.set(FireDown=int(pressed))

    def call(self, label, lines=None):
        self.bus.events.clear()
        self.cpu.stPushWord(SYMBOLS["Frame"] - 1)
        self.cpu.pc = SYMBOLS[label]
        self.until("Frame")
        if lines is not None:
            sync = [c for c, r, _ in self.bus.events if r == 2]
            assert len(sync) == lines, (label, "WSYNCs", len(sync), lines)
            assert all(b // 76 - a // 76 == 1 for a, b in zip(sync, sync[1:])), (
                label, "linha perdida", [c % 76 for c in sync],
                [b // 76 - a // 76 for a, b in zip(sync, sync[1:])])

    def frame(self):
        self.bus.events.clear()
        before = self.cpu.processorCycles
        self.rendered = None
        self.step()
        for _ in range(30000):
            if self.cpu.pc == SYMBOLS["Frame"] and self.bus.bank == 1:
                break
            if self.cpu.pc in (SYMBOLS["SceneFirst"], SYMBOLS["BeamSceneFirst"]) and self.bus.bank == 1 and self.rendered is None:
                self.rendered = {name: self.get(name) for name in
                                 ("Heading", "XPos", "YPos", "BossX", "BossY",
                                  "ShotActive", "ShotY", "PlayerMask", "BossMask",
                                  "RoomIndex", "DoorOpen", "ExitDirection", "EnemyActive",
                                  "EnemyX", "EnemyY", "HazardAxis", "HazardVisible",
                                  "BeamMode", "BeamMotion", "BeamStartX")}
            self.step()
        else:
            raise AssertionError("Quadro nao terminou")
        return self.cpu.processorCycles - before


HEADINGS = {(0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
            (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7}
SHOT_VECTORS = ((0, -512), (362, -362), (512, 0), (362, 362),
                (0, 512), (-362, 362), (-512, 0), (-362, -362))
SHOT_ORIGINS = ((3, -2), (7, -1), (8, 3), (7, 7),
                (3, 8), (-1, 7), (-2, 3), (-1, -1))
BOSS_VECTORS = ((0, -1), (1, -1), (2, 0), (1, 1),
                (0, 1), (-1, 1), (-2, 0), (-1, -1))


def clamp_fixed(value, delta, low, high):
    return max(low * 256, min(high * 256, value + delta))


def state(machine, labels):
    return tuple(machine.get(label) for label in labels)


def check_rom():
    assert len(ROM) == 8192, len(ROM)
    assert ROM[4096] == 0x78
    for bank in range(2):
        data = ROM[bank * 4096:(bank + 1) * 4096]
        assert [int.from_bytes(data[p:p + 2], "little")
                for p in (4090, 4092, 4094)] == [0xFFD0] * 3
        assert data[0xFD0:0xFD3] == bytes((0x2C, 0xF9, 0x1F)), "Boot deve selecionar banco 1"
        machine = Machine(bank)
        labels = ("XPos", "YPos", "Heading", "BossX", "BossY", "BossHP", "Lives",
                  "BossPhase", "PhaseTimer", "GameState", "ShotActive", "RoomIndex", "DoorOpen")
        assert state(machine, labels) == (76, 58, 0, 72, 18, 6, 3, 0, 90, 0, 0, 0, 0)
        assert machine.bus.bank == 1
        machine.set(XFrac=37, YFrac=91, ShotHeading=7)
        before = state(machine, ("XFrac", "YFrac", "ShotHeading", "Lives", "BossHP"))
        machine.call("UpdateBoss", 12)
        assert state(machine, ("XFrac", "YFrac", "ShotHeading", "Lives", "BossHP")) == before
        assert machine.bus.bank == 1 and 0 in machine.bus.banks
    bus = Bus()
    for entry in (0xFA0, 0xFC0):
        assert ROM[entry:entry + 10] == ROM[4096 + entry:4096 + entry + 10]
        assert ROM[entry:entry + 3] == bytes((0x2C, 0xF8, 0x1F))
    machine = Machine()
    machine.set(GameState=3, BossHP=0)
    machine.call("CheckHits", 11)
    assert machine.bus.bank == 1 and 0 in machine.bus.banks
    for address, expected in ((0xFFF9, 1), (0x1FF8, 0), (0x5FF9, 1), (0xBFF8, 0)):
        bus[address]
        assert bus.bank == expected
    bus[0xFFF9] = 0
    assert bus.bank == 1
    print("OK: ROM 8K F8, boot em ambos os bancos, hotspots espelhados e retorno do banco de chefes")


def check_controls():
    machine = Machine()
    cases = 0
    for mask in range(16):
        dx = int(not mask & 8) - int(not mask & 4)
        dy = int(not mask & 2) - int(not mask & 1)
        speed = 136 if dx and dy else 192
        for heading in range(8):
            for x, y in ((8, 6), (144, 66), (8, 66), (144, 6), (76, 36)):
                for frac in (0, 127, 255):
                    machine.set(GameState=0, XPos=x, YPos=y, XFrac=frac,
                                YFrac=frac, Heading=heading)
                    machine.bus.joystick = (mask << 4) | 15
                    machine.call("ReadJoystick", 7)
                    actual = (machine.get("XPos") * 256 + machine.get("XFrac"),
                              machine.get("YPos") * 256 + machine.get("YFrac"),
                              machine.get("Heading"))
                    expected = (clamp_fixed(x * 256 + frac, dx * speed, 8, 144),
                                clamp_fixed(y * 256 + frac, dy * speed, 6, 66),
                                HEADINGS.get((dx, dy), heading))
                    assert actual == expected, (mask, heading, x, y, frac, actual, expected)
                    cases += 1
    for game in (1, 2):
        machine.set(GameState=game, XPos=76, YPos=36, XFrac=17, YFrac=29, Heading=4)
        before = state(machine, ("XPos", "YPos", "XFrac", "YFrac", "Heading"))
        machine.bus.joystick = 0x6F
        machine.call("ReadJoystick", 7)
        assert state(machine, ("XPos", "YPos", "XFrac", "YFrac", "Heading")) == before
    machine.set(GameState=3, XPos=76, YPos=36, XFrac=0, YFrac=0, Heading=0)
    machine.bus.joystick = 0x7F
    machine.call("ReadJoystick", 7)
    assert state(machine, ("XPos", "XFrac", "Heading")) == (76, 192, 2)
    print(f"OK: {cases} casos de controles, limites e congelamento final")


def shot_state(machine):
    return state(machine, ("ShotActive", "ShotX", "ShotXFrac", "ShotY", "ShotYFrac", "ShotHeading"))


def valid_shot(x, y):
    return 4 <= x <= 153 and 4 <= y <= 75


def check_shots():
    machine = Machine()
    cases = 0
    for heading, (ox, oy) in enumerate(SHOT_ORIGINS):
        for x, y in ((8, 6), (144, 66), (76, 36)):
            machine.set(GameState=0, XPos=x, YPos=y, Heading=heading, ShotActive=0)
            machine.fire(False)
            machine.call("UpdateShot", 6)
            assert machine.get("ShotActive") == 0
            machine.fire(True)
            machine.call("UpdateShot", 6)
            sx, sy = x + ox, y + oy
            assert shot_state(machine) == (2 if valid_shot(sx, sy) else 0, sx, 0, sy, 0, heading)
            cases += 1
    for heading, (dx, dy) in enumerate(SHOT_VECTORS):
        for x in (4, 5, 76, 152, 153):
            for y in (4, 5, 36, 74, 75):
                for frac in (0, 127, 255):
                    yf = (frac + 91) & 255
                    machine.set(GameState=0, ShotActive=2, ShotX=x, ShotY=y,
                                ShotXFrac=frac, ShotYFrac=yf, ShotHeading=heading,
                                Heading=(heading + 3) % 8)
                    machine.fire(frac == 127)
                    machine.call("UpdateShot", 6)
                    sx = (x * 256 + frac + dx) & 0xFFFF
                    sy = (y * 256 + yf + dy) & 0xFFFF
                    expected = (2 if valid_shot(sx >> 8, sy >> 8) else 0,
                                sx >> 8, sx & 255, sy >> 8, sy & 255, heading)
                    assert shot_state(machine) == expected, (heading, x, y, frac, shot_state(machine), expected)
                    cases += 1
        machine.set(GameState=0, XPos=76, YPos=36, Heading=heading, ShotActive=0)
        machine.fire(True)
        machine.call("UpdateShot", 6)
        machine.fire(False)
        for _ in range(80):
            machine.call("UpdateShot", 6)
            if machine.get("ShotActive") == 0:
                break
        else:
            raise AssertionError(("Tiro nao chegou a parede", heading))
        stopped = shot_state(machine)
        machine.call("UpdateShot", 6)
        assert shot_state(machine) == stopped
        machine.fire(True)
        machine.call("UpdateShot", 6)
        assert machine.get("ShotActive") == 2
    for game in (1, 2, 3):
        machine.set(GameState=game, ShotActive=2, ShotX=76, ShotY=36,
                    ShotXFrac=0, ShotYFrac=0, ShotHeading=0)
        before = shot_state(machine)
        machine.call("UpdateShot", 6)
        assert shot_state(machine) == before
    print(f"OK: {cases} casos de tiros, oito rumos, paredes, repeticao e congelamento")


def check_boss():
    machine = Machine()
    for dx in (-13, -12, -11, 0, 11, 12, 13):
        for dy in (-9, -8, -7, 0, 7, 8, 9):
            machine.set(GameState=0, BossX=72, BossY=30, XPos=76 + dx,
                        YPos=32 + dy, BossPhase=0, PhaseTimer=1,
                        BossHeading=3, BossFlash=0)
            machine.call("UpdateBoss", 12)
            horizontal = int(dx >= 12) - int(dx <= -12)
            vertical = int(dy >= 8) - int(dy <= -8)
            expected = HEADINGS.get((horizontal, vertical), 3)
            assert machine.get("BossHeading") == expected, (dx, dy, machine.get("BossHeading"), expected)
    for (dx, dy), heading in HEADINGS.items():
        machine.set(GameState=0, BossX=72, BossY=30, XPos=72 + 40 * dx,
                    YPos=30 + 20 * dy, BossPhase=0, PhaseTimer=1, BossFlash=0)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("BossPhase", "PhaseTimer", "BossHeading")) == (1, 48, heading)
        machine.set(XPos=72 - 40 * dx, YPos=30 - 20 * dy)
        for _ in range(47):
            machine.call("UpdateBoss", 12)
            assert machine.get("BossPhase") == 1
            assert machine.get("BossHeading") == heading
        machine.call("UpdateBoss", 12)
        assert state(machine, ("BossPhase", "PhaseTimer", "BossHeading")) == (2, 64, heading)
    for heading, (dx, dy) in enumerate(BOSS_VECTORS):
        machine.set(GameState=0, BossX=72, BossY=30, BossPhase=2,
                    BossHeading=heading, PhaseTimer=40)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("BossX", "BossY", "BossPhase")) == (72 + dx, 30 + dy, 2)
        machine.set(BossX=136 if dx > 0 else 8 if dx < 0 else 72,
                    BossY=62 if dy > 0 else 6 if dy < 0 else 30,
                    BossPhase=2, PhaseTimer=40)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("BossPhase", "PhaseTimer")) == (3, 90)
        assert 8 <= machine.get("BossX") <= 136 and 6 <= machine.get("BossY") <= 62
    machine.set(GameState=0, BossPhase=2, PhaseTimer=1, BossX=72, BossY=30)
    machine.call("UpdateBoss", 12)
    assert state(machine, ("BossPhase", "PhaseTimer")) == (3, 90)
    machine.set(BossPhase=3, PhaseTimer=1)
    machine.call("UpdateBoss", 12)
    assert state(machine, ("BossPhase", "PhaseTimer")) == (0, 45)
    machine.set(InvulnTimer=1, BossFlash=1, PhaseTimer=20)
    machine.call("UpdateBoss", 12)
    assert state(machine, ("InvulnTimer", "BossFlash", "PhaseTimer")) == (0, 0, 19)
    for game in (1, 2, 3):
        machine.set(GameState=game, BossPhase=2, BossX=72, BossY=30,
                    PhaseTimer=31, BossHeading=2, BossFlash=3, InvulnTimer=4)
        frozen = ("BossX", "BossY", "BossPhase", "PhaseTimer", "BossFlash", "InvulnTimer")
        before = state(machine, frozen)
        machine.call("UpdateBoss", 12)
        assert state(machine, frozen) == before
    durations = ((45, 48, 64, 90), (50, 45, 1, 75), (60, 36, 64, 60), (45, 60, 60, 75))
    for room, timers in enumerate(durations):
        for phase in range(4):
            machine.set(RoomIndex=room, GameState=0, BossPhase=phase, PhaseTimer=1,
                        BossX=72, BossY=30, BossHeading=2, XPos=120, YPos=30,
                        EnemyActive=0, HazardAxis=0, HazardActive=0, HazardVisible=0)
            machine.call("UpdateBoss", 12)
            following = (phase + 1) % 4
            assert state(machine, ("BossPhase", "PhaseTimer")) == (following, timers[following]), (
                room, phase, state(machine, ("BossPhase", "PhaseTimer")))
    # Guardiao e Touro usam exatamente os mesmos oito vetores de investida.
    for room, recovery in ((0, 90), (2, 60)):
        for heading, (dx, dy) in enumerate(BOSS_VECTORS):
            machine.set(RoomIndex=room, GameState=0, BossPhase=1, PhaseTimer=1,
                        BossX=72, BossY=30, BossHeading=heading, EnemyActive=0,
                        PatrolMoving=0)
            machine.call("UpdateBoss", 12)
            assert state(machine, ("BossX", "BossY", "BossPhase", "PhaseTimer")) == (
                72 + dx, 30 + dy, 2, 64), (room, heading)
            if room == 2:
                assert state(machine, ("EnemyActive", "EnemyHeading")) == (2, heading)
            machine.set(BossX=136 if dx > 0 else 8 if dx < 0 else 72,
                        BossY=62 if dy > 0 else 6 if dy < 0 else 30,
                        BossPhase=2, PhaseTimer=40)
            machine.call("UpdateBoss", 12)
            assert state(machine, ("BossPhase", "PhaseTimer")) == (3, recovery)
    machine.set(RoomIndex=3, GameState=0, BossPhase=2, PhaseTimer=30,
                BossX=72, BossY=30, EnemyActive=0)
    machine.call("UpdateBoss", 12)
    assert state(machine, ("BossX", "BossY")) == (72, 30)
    # Todos os quatro desenhos passam por aviso seguro, ativacao e descanso.
    for axis in range(4):
        machine.set(RoomIndex=3, GameState=0, BossPhase=0, PhaseTimer=1,
                    HazardAxis=axis, HazardVisible=0, HazardActive=0)
        machine.call("UpdateBoss", 12)
        expected_axis = (axis + 1) % 4
        assert state(machine, ("HazardAxis", "HazardVisible", "HazardActive")) == (expected_axis, 1, 0)
        machine.set(BossPhase=1, PhaseTimer=1)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("HazardAxis", "HazardVisible", "HazardActive")) == (expected_axis, 1, 1)
        machine.set(BossPhase=2, PhaseTimer=1)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("HazardAxis", "HazardVisible", "HazardActive")) == (expected_axis, 0, 0)
    print("OK: quatro chefes, 49 limiares, investidas iguais do Touro/Guardiao com tiro e quatro padroes de piso")


def check_patrol():
    machine = Machine()
    nodes = ((72, 6), (136, 34), (72, 62), (8, 34))
    machine.set(RoomIndex=1, GameState=0, BossX=72, BossY=6, PatrolNode=0,
                PatrolMoving=0, BossPhase=0, PhaseTimer=30, EnemyActive=0)
    for _ in range(5):
        machine.call("UpdateBoss", 12)
        assert state(machine, ("BossX", "BossY", "PatrolNode", "PatrolMoving")) == (72, 6, 0, 0)
    steps = 0
    for leg in range(8):
        old = state(machine, ("BossX", "BossY"))
        node = (leg + 1) % 4
        machine.set(BossPhase=1, PhaseTimer=1, EnemyActive=0, BossHeading=2)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("EnemyActive", "EnemyHeading", "PatrolNode", "PatrolMoving")) == (2, 2, node, 1)
        assert state(machine, ("BossX", "BossY")) == old, "Sentinela andou antes de disparar"
        target = nodes[node]
        expected = old
        for tick in range(1, 65):
            expected = tuple(v + (1 if t > v else -1 if t < v else 0)
                             for v, t in zip(expected, target))
            machine.call("UpdateBoss", 12)
            assert state(machine, ("BossX", "BossY")) == expected, (leg, tick, expected)
            assert machine.get("PatrolNode") == node
            assert machine.get("PatrolMoving") == int(expected != target)
            assert 8 <= expected[0] <= 136 and 6 <= expected[1] <= 62
            steps += 1
        assert expected == target
        for _ in range(3):
            machine.call("UpdateBoss", 12)
            assert state(machine, ("BossX", "BossY", "PatrolMoving")) == (*target, 0)
    # Bala ocupada nao autoriza outra perna nem reinicia a caminhada.
    machine.set(BossX=72, BossY=6, PatrolNode=0, PatrolMoving=0,
                BossPhase=1, PhaseTimer=1, EnemyActive=2,
                EnemyX=80, EnemyY=40, EnemyHeading=6)
    machine.call("UpdateBoss", 12)
    assert state(machine, ("BossX", "BossY", "PatrolNode", "PatrolMoving", "EnemySpawn")) == (72, 6, 0, 0, 0)
    machine.set(BossX=80, BossY=14, PatrolNode=1, PatrolMoving=1,
                BossPhase=1, PhaseTimer=1, EnemyActive=2,
                EnemyX=80, EnemyY=40, EnemyHeading=6)
    machine.call("UpdateBoss", 12)
    assert state(machine, ("BossX", "BossY", "PatrolNode", "PatrolMoving")) == (81, 15, 1, 1)
    for game in (1, 2, 3):
        machine.set(GameState=game, BossX=80, BossY=14, PatrolNode=1, PatrolMoving=1)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("BossX", "BossY", "PatrolNode", "PatrolMoving")) == (80, 14, 1, 1)
    print(f"OK: Sentinela percorre topo/direita/baixo/esquerda, {steps} passos sem overshoot, somente apos tiros reais")


def check_enemy():
    machine = Machine()
    vectors = ((0, -2), (1, -1), (2, 0), (1, 1),
               (0, 2), (-1, 1), (-2, 0), (-1, -1))
    for room in (1, 2):
        for heading, (dx, dy) in enumerate(vectors):
            machine.set(RoomIndex=room, GameState=0, BossX=80, BossY=30,
                        BossHeading=heading, BossPhase=1, PhaseTimer=1, EnemyActive=0,
                        PatrolNode=0, PatrolMoving=0)
            machine.call("UpdateBoss", 12)
            origin = (machine.get("BossX") + 6, machine.get("BossY") + 5)
            assert state(machine, ("EnemyActive", "EnemyX", "EnemyY", "EnemyHeading")) == (
                2, *origin, heading), (room, heading)
            machine.set(XPos=8, YPos=6)
            machine.call("UpdateBoss", 12)
            assert state(machine, ("EnemyX", "EnemyY", "EnemyHeading")) == (
                origin[0] + dx, origin[1] + dy, heading)
            # Um disparo vivo nao pode ser substituido por um novo ataque.
            machine.set(BossPhase=1, PhaseTimer=1, EnemyX=64, EnemyY=24,
                        EnemyHeading=2, EnemyActive=2)
            machine.call("UpdateBoss", 12)
            assert state(machine, ("EnemyActive", "EnemyX", "EnemyY", "EnemyHeading")) == (2, 66, 24, 2)
    cases = 0
    for heading, (dx, dy) in enumerate(vectors):
        for x in (8, 9, 80, 147, 148):
            for y in (8, 9, 40, 72, 73):
                machine.set(RoomIndex=1, GameState=0, BossPhase=3, PhaseTimer=30,
                            EnemyActive=2, EnemyX=x, EnemyY=y, EnemyHeading=heading)
                machine.call("UpdateBoss", 12)
                expected_active = 2 if 8 <= x + dx <= 148 and 8 <= y + dy <= 73 else 0
                assert machine.get("EnemyActive") == expected_active, (heading, x, y)
                if expected_active:
                    assert state(machine, ("EnemyX", "EnemyY")) == (x + dx, y + dy)
                cases += 1
    for game in (1, 2, 3):
        machine.set(GameState=game, EnemyActive=2, HazardActive=1, HazardVisible=1)
        machine.call("UpdateBoss", 12)
        assert state(machine, ("EnemyActive", "HazardActive", "HazardVisible")) == (0, 0, 0)
    print(f"OK: balas da Sentinela/Guardiao, spawn unico e {cases} casos de direcao/limites")


def hit_setup(machine, **overrides):
    values = dict(GameState=0, RoomIndex=0, DoorOpen=0, ExitDirection=1,
                  BossX=80, BossY=20, BossHP=6, BossPhase=3,
                  BossFlash=0, XPos=24, YPos=58, Lives=3, InvulnTimer=0,
                  ShotActive=2, ShotX=86, ShotY=24, EnemyActive=0,
                  HazardActive=0, HazardVisible=0, HazardAxis=0)
    values.update(overrides)
    machine.set(**values)


def overlap(ax, ay, aw, ah, bx, by, bw, bh):
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def diagonal_overlap(axis, px, py):
    for row in range(py, py + 8):
        for second in (0, 1):
            left = 2 * row + 2 * second if axis == 2 else 152 - 2 * row - 2 * second
            if px < left + 8 and px + 8 > left:
                return True
    return False


def check_hits():
    machine = Machine()
    cases = 0
    # Referencia geometrica independente: apenas sobreposicao de areas conta.
    for room in range(4):
        for phase in range(4):
            for flash in (0, 1):
                for sx in (78, 79, 80, 95, 96):
                    for sy in (19, 20, 31, 32):
                        hit_setup(machine, RoomIndex=room, BossPhase=phase, BossFlash=flash,
                                  ShotX=sx, ShotY=sy)
                        machine.call("CheckHits", 11)
                        contact = overlap(sx, sy, 2, 1, 80, 20, 16, 12)
                        vulnerable = phase == 3 or (room == 2 and phase == 2)
                        damage = contact and vulnerable and flash == 0
                        assert machine.get("ShotActive") == (0 if contact else 2), (room, phase, flash, sx, sy)
                        assert machine.get("BossHP") == 6 - int(damage), (room, phase, flash, sx, sy)
                        if damage:
                            assert machine.get("BossFlash") == 8
                        assert machine.get("Lives") == 3
                        cases += 1
    for px in (72, 73, 80, 95, 96):
        for py in (12, 13, 20, 31, 32):
            hit_setup(machine, XPos=px, YPos=py, ShotActive=0)
            machine.call("CheckHits", 11)
            contact = overlap(px, py, 8, 8, 80, 20, 16, 12)
            assert machine.get("Lives") == 3 - int(contact), (px, py)
            if contact:
                assert machine.get("InvulnTimer") == 60
                machine.call("CheckHits", 11)
                assert machine.get("Lives") == 2, "Contato repetiu dano durante invulnerabilidade"
            cases += 1
    for ex in (20, 21, 24, 31, 32):
        for ey in (38, 39, 40, 47, 48):
            hit_setup(machine, RoomIndex=1, ShotActive=0, XPos=24, YPos=40,
                      EnemyActive=2, EnemyX=ex, EnemyY=ey)
            machine.call("CheckHits", 11)
            contact = overlap(ex, ey, 4, 2, 24, 40, 8, 8)
            assert machine.get("Lives") == 3 - int(contact), ("bala", ex, ey)
            if contact:
                assert machine.get("InvulnTimer") == 60 and machine.get("EnemyActive") == 0
            cases += 1
    for axis in (0, 1):
        hazard = (16, 34, 128, 12) if axis == 0 else (64, 4, 32, 72)
        for px in (8, 9, 56, 57, 63, 64, 95, 96, 136, 144):
            for py in (6, 26, 27, 33, 34, 45, 46, 66):
                hit_setup(machine, RoomIndex=3, BossX=112, BossY=6,
                          BossPhase=2, ShotActive=0, XPos=px, YPos=py,
                          HazardActive=1, HazardVisible=1, HazardAxis=axis)
                # Evita que o chefe de referencia toque a caixa do jogador.
                machine.set(BossX=112 if px < 96 else 24)
                machine.call("CheckHits", 11)
                contact = overlap(px, py, 8, 8, *hazard)
                assert machine.get("Lives") == 3 - int(contact), ("faixa", axis, px, py)
                cases += 1
    # Aviso mostra o perigo, mas ainda nao causa dano. Fontes simultaneas
    # compartilham um unico acerto e o mesmo tempo de invulnerabilidade.
    hit_setup(machine, RoomIndex=3, BossPhase=1, ShotActive=0, XPos=72,
              YPos=40, HazardActive=0, HazardVisible=1, HazardAxis=0)
    machine.call("CheckHits", 11)
    assert machine.get("Lives") == 3
    for invuln in (0, 1, 60):
        hit_setup(machine, RoomIndex=3, BossPhase=2, XPos=84, YPos=24,
                  ShotActive=0, EnemyActive=2, EnemyX=86, EnemyY=26,
                  HazardActive=1, HazardVisible=1, HazardAxis=1, InvulnTimer=invuln)
        machine.call("CheckHits", 11)
        assert machine.get("Lives") == (2 if invuln == 0 else 3), ("dano simultaneo", invuln)
    for room in range(4):
        hit_setup(machine, RoomIndex=room, BossHP=1,
                  EnemyActive=2, EnemyX=8, EnemyY=8,
                  HazardActive=1, HazardVisible=1, InvulnTimer=9)
        machine.call("CheckHits", 11)
        expected = (0, 1, 0) if room == 3 else (0, 3, 1)
        assert state(machine, ("BossHP", "GameState", "DoorOpen")) == expected, room
        assert state(machine, ("ShotActive", "EnemyActive", "HazardActive", "HazardVisible")) == (0, 0, 0, 0)
        assert machine.get("InvulnTimer") == 0, "Resultado manteve a piscada de invulnerabilidade"
        hit_setup(machine, RoomIndex=room, Lives=1, BossHP=1, XPos=84, YPos=24)
        machine.call("CheckHits", 11)
        assert state(machine, ("Lives", "BossHP", "GameState")) == (0, 0, 1 if room == 3 else 2), room
    hit_setup(machine, Lives=1, ShotActive=0, XPos=84, YPos=24)
    machine.call("CheckHits", 11)
    assert state(machine, ("Lives", "GameState")) == (0, 2)
    assert machine.get("InvulnTimer") == 0
    # Diagonais: referencia por intersecao com cada faixa de oito pixels,
    # sem repetir a inequacao simplificada usada pelo cartucho.
    for axis in (2, 3):
        for py in range(6, 67):
            candidates = {8, 9, 72, 136, 143, 144}
            if axis == 2:
                candidates.update(2 * py + delta for delta in (-8, -7, -6, 22, 23, 24))
            else:
                candidates.update(value - 2 * py for value in (128, 129, 130, 158, 159, 160))
            for px in sorted(x for x in candidates if 8 <= x <= 144):
                hit_setup(machine, RoomIndex=3, BossPhase=2, ShotActive=0,
                          XPos=px, YPos=py, BossX=112 if px < 96 else 24,
                          BossY=6 if py > 22 else 50, HazardActive=1,
                          HazardVisible=1, HazardAxis=axis)
                machine.call("CheckHits", 11)
                contact = diagonal_overlap(axis, px, py)
                assert machine.get("Lives") == 3 - int(contact), ("diagonal", axis, px, py, contact)
                cases += 1
        px, py = (72, 36) if axis == 2 else (80, 36)
        for visible, active, invuln in ((1, 0, 0), (1, 1, 1), (1, 1, 60)):
            hit_setup(machine, RoomIndex=3, BossPhase=1 if not active else 2,
                      ShotActive=0, XPos=px, YPos=py, BossX=112, BossY=6,
                      HazardVisible=visible, HazardActive=active,
                      HazardAxis=axis, InvulnTimer=invuln)
            machine.call("CheckHits", 11)
            assert machine.get("Lives") == 3, ("aviso/protecao diagonal", axis, active, invuln)
    for game in (1, 2, 3):
        hit_setup(machine, GameState=game, Lives=1, BossHP=1, XPos=84, YPos=24)
        before = state(machine, ("Lives", "BossHP", "GameState", "ShotActive"))
        machine.call("CheckHits", 11)
        assert state(machine, ("Lives", "BossHP", "GameState", "ShotActive")) == before
    print(f"OK: {cases} colisoes, escudo/nucleo, balas, faixas, dano simultaneo e quatro resultados")


def check_rooms():
    machine = Machine()
    # A porta exige sala limpa, abertura inteira e intencao de sair.
    cases = 0
    for room, exit_direction in ((0, 1), (1, 2), (2, 1)):
        points = ((x, y) for x in (63, 64, 76, 88, 89, 144)
                  for y in (6, 7, 27, 28, 40, 44, 45))
        for x, y in points:
            for game, opened, travel, outward in ((0, 0, 1, True), (0, 1, 1, True),
                                                  (3, 0, 1, True), (3, 1, 0, True),
                                                  (3, 1, 1, False), (3, 1, 1, True)):
                machine.set(RoomIndex=room, ExitDirection=exit_direction, DoorOpen=opened,
                            GameState=game, BossHP=0 if game == 3 else 6,
                            XPos=x, YPos=y, XFrac=127, YFrac=99, Travel=travel,
                            SignY=0xFF if exit_direction == 1 and outward else 0,
                            SignX=0 if exit_direction == 2 and outward else 0xFF,
                            DeltaX=192 if exit_direction == 2 else 0,
                            DeltaY=64 if exit_direction == 1 else 0, Lives=2)
                machine.call("UpdateRoom", 4)
                within = (64 <= x <= 88 and y == 6 if exit_direction == 1
                          else x == 144 and 28 <= y <= 44)
                change = game == 3 and opened and travel and outward and within
                assert machine.get("RoomIndex") == room + int(change), (
                    room, x, y, game, opened, travel, outward)
                if change:
                    expected_position = (x, 66) if exit_direction == 1 else (8, y)
                    assert state(machine, ("XPos", "YPos")) == expected_position
                    assert state(machine, ("GameState", "DoorOpen", "BossHP", "Lives",
                                           "PhaseTimer", "BossPhase", "XFrac", "YFrac")) == (
                        0, 0, 6, 2, 90, 0, 0, 0)
                    assert state(machine, ("BossX", "BossY", "PatrolNode", "PatrolMoving")) == (
                        72, 6 if room == 0 else 18, 0, 0)
                cases += 1
    # Caminho completo: vence cada chefe, atravessa por movimento real e
    # encontra a sala seguinte com a vida restante e portas fechadas.
    machine = Machine()
    machine.set(Lives=2)
    for room in range(4):
        assert machine.get("RoomIndex") == room
        for _ in range(6):
            hit_setup(machine, RoomIndex=room, Lives=2, BossHP=machine.get("BossHP"),
                      ExitDirection=(1, 2, 1, 0)[room])
            machine.call("CheckHits", 11)
        if room == 3:
            assert state(machine, ("GameState", "DoorOpen")) == (1, 0)
            break
        assert state(machine, ("GameState", "DoorOpen")) == (3, 1)
        machine.bus.fire = 0
        machine.set(FireDown=0)
        machine.call("UpdateInput", 5)
        assert machine.get("GameState") == 3, "Tiro reiniciou sala limpa"
        machine.call("UpdateShot", 6)
        assert machine.get("ShotActive") == 0
        if room in (0, 2):
            machine.set(XPos=76, YPos=6, XFrac=0, YFrac=128)
            machine.bus.joystick = 0xEF
        else:
            machine.set(XPos=143, YPos=40, XFrac=128, YFrac=0)
            machine.bus.joystick = 0x7F
        machine.call("ReadJoystick", 7)
        machine.call("UpdateRoom", 4)
        assert state(machine, ("RoomIndex", "GameState", "BossHP", "Lives", "DoorOpen")) == (
            room + 1, 0, 6, 2, 0)
    print(f"OK: {cases} casos de portas fechadas/abertas, limites e campanha de quatro salas")


def check_restart():
    machine = Machine()
    restored = ("XPos", "YPos", "XFrac", "YFrac", "Heading", "BossX", "BossY",
                "BossHP", "Lives", "BossPhase", "PhaseTimer", "GameState",
                "ShotActive", "BossFlash", "InvulnTimer", "RoomIndex", "DoorOpen",
                "EnemyActive", "HazardActive", "HazardVisible", "PatrolNode", "PatrolMoving")
    initial = (76, 58, 0, 0, 0, 72, 18, 6, 3, 0, 90, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    machine.bus.fire = 0
    machine.call("UpdateInput", 5)
    machine.set(GameState=1, Lives=1, BossHP=0, XPos=20, ShotActive=2)
    for _ in range(3):
        machine.call("UpdateInput", 5)
        assert machine.get("GameState") == 1, "Botao segurado reiniciou a partida"
    machine.bus.fire = 0x80
    machine.call("UpdateInput", 5)
    assert machine.get("GameState") == 1
    machine.bus.fire = 0
    machine.call("UpdateInput", 5)
    assert state(machine, restored) == initial, state(machine, restored)
    assert machine.get("FireDown") != 0
    machine.set(GameState=2)
    machine.call("UpdateInput", 5)
    assert machine.get("GameState") == 2
    machine.bus.fire = 0x80
    machine.call("UpdateInput", 5)
    machine.bus.fire = 0
    machine.call("UpdateInput", 5)
    assert state(machine, restored) == initial
    for game in (0, 1, 2, 3):
        machine.set(GameState=game, Lives=0, BossHP=0, ShotActive=2,
                    InvulnTimer=59, BossFlash=7, XPos=30, YPos=20,
                    RoomIndex=3, DoorOpen=1, EnemyActive=2, PatrolNode=3, PatrolMoving=1,
                    HazardVisible=1, HazardActive=1)
        machine.bus.switches = 0xFE
        machine.call("UpdateInput", 5)
        assert state(machine, restored) == initial, (game, state(machine, restored))
    print("OK: reset do console e reinicio por nova borda do botao, estados restaurados")


def check_beam_motion(events, start, end, rendered):
    """Confere o protocolo de motion; nao pretende simular o TIA inteiro."""
    mode = rendered["BeamMode"]
    expected_mode = rendered["HazardAxis"] if rendered["HazardVisible"] and rendered["HazardAxis"] >= 2 else 0
    assert mode == expected_mode, ("selecao diagonal", mode, expected_mode)
    expected_motion = {0: 0, 2: 0xE0, 3: 0x20}[mode]
    assert rendered["BeamMotion"] == expected_motion
    motion = {0x20: 0, 0x21: 0, 0x22: 0, 0x23: 0, 0x24: 0}
    reset_m1 = None
    position = None
    initial_hmove = None
    hmove_rows = []
    cleared_after_position = False
    checked_start = False
    for cycle, register, value in events:
        line = cycle // 76
        if not checked_start and line >= start:
            if mode:
                assert position == rendered["BeamStartX"] == (0 if mode == 2 else 152), (
                    "posicao inicial do feixe", mode, position, rendered["BeamStartX"])
            assert cleared_after_position, "Faltou HMCLR depois do posicionamento"
            checked_start = True
        if register == 0x13:
            # Calibracao de RESM1 dos estudos: coarse X = 3*ciclo - 64.
            reset_m1 = (3 * (cycle % 76) - 64) % 160
        elif register in motion:
            motion[register] = value
        elif register == 0x2B:
            assert initial_hmove is not None and cycle - initial_hmove >= 24, (
                "HMCLR antes de HMOVE terminar", cycle - initial_hmove if initial_hmove is not None else None)
            motion = dict.fromkeys(motion, 0)
            cleared_after_position = True
        elif register == 0x2A:
            if line < start:
                initial_hmove = cycle
                if reset_m1 is not None:
                    nibble = motion[0x23] >> 4
                    fine = nibble if nibble < 8 else nibble - 16
                    position = (reset_m1 - fine) % 160
            elif start <= line < start + 160:
                row = line - start
                assert mode and row % 2 == 1 and cycle % 76 == 6, (
                    "HMOVE visivel fora da segunda linha diagonal", mode, row, cycle % 76)
                assert all(motion[r] == 0 for r in (0x20, 0x21, 0x22, 0x24)), (
                    "HMOVE moveu jogador/chefe/tiro/ball", motion)
                assert motion[0x23] == expected_motion
                logical = row // 2
                step = 2 if mode == 2 else -2
                assert position == (rendered["BeamStartX"] + step * logical) % 160
                position = (position + step) % 160
                assert position == (rendered["BeamStartX"] + step * (logical + 1)) % 160
                hmove_rows.append(row)
            else:
                raise AssertionError(("HMOVE inesperado depois da arena", line - start))
    assert hmove_rows == (list(range(1, 160, 2)) if mode else [])
    widths = [v for c, r, v in events if r == 5 and c // 76 < start]
    assert widths and widths[-1] == (0x35 if mode else 0x25), (mode, widths)


def check_video():
    machine = Machine()
    first_line = machine.cpu.processorCycles // 76
    machine.frame()
    assert machine.cpu.processorCycles // 76 - first_line == 262
    frames = 0
    max_wsync = 0
    sprites = ("BullSprite", "EyeSprite", "ShieldSprite", "KingSprite")
    scenarios = [(room, game, phase, corner, active)
                 for room in range(4) for game in (0, 1, 2, 3)
                 for phase in range(4) for corner in range(3) for active in (0, 2)
                 if not (room == 3 and game == 3)]
    for room, game, phase, corner, active in scenarios:
        px, py, bx, by = ((8, 6, 136, 62), (144, 66, 8, 6), (76, 58, 72, 18))[corner]
        heading = (room * 2 + phase + corner * 3) % 8
        machine.set(RoomIndex=room, GameState=game, DoorOpen=int(game == 3),
                    ExitDirection=(1, 2, 1, 0)[room], BossPhase=phase, PhaseTimer=1,
                    BossHeading=heading, BossX=bx, BossY=by, BossHP=0 if game in (1, 3) else 6,
                    BossFlash=2 if corner == 2 else 0,
                    XPos=px, YPos=py, XFrac=0, YFrac=0, Heading=heading,
                    Lives=0 if game == 2 else 3,
                    InvulnTimer=0, ShotActive=active if game == 0 else 0, ShotX=153, ShotY=75,
                    ShotXFrac=0, ShotYFrac=0, ShotHeading=heading,
                    EnemyActive=active if game == 0 else 0, EnemyX=148, EnemyY=73,
                    EnemyHeading=heading, HazardAxis=(corner + phase) % 4,
                    PatrolNode=0, PatrolMoving=0,
                    HazardVisible=int(room == 3 and game == 0 and phase in (1, 2)),
                    HazardActive=int(room == 3 and game == 0 and phase == 2))
        machine.bus.joystick = (0xFF, 0x6F, 0x9F)[heading % 3]
        machine.bus.fire = 0x80
        machine.bus.switches = 0xFF
        elapsed = machine.frame()
        assert elapsed == 262 * 76, (room, game, phase, corner, "linhas", elapsed / 76)
        assert machine.bus.bank == 1
        events = machine.bus.events
        sync = [(c, v) for c, r, v in events if r == 0]
        assert [v for _, v in sync] == [2, 0], sync
        assert sync[1][0] // 76 - sync[0][0] // 76 == 3
        blank = [(c, v) for c, r, v in events if r == 1]
        assert [v for _, v in blank] == [0, 2], blank
        start, end = blank[0][0] // 76, blank[1][0] // 76
        assert start - sync[1][0] // 76 == 37
        assert end - start == 192
        pf1_before_scene = [value for cycle, register, value in events
                            if register == 0x0E and cycle < blank[0][0]]
        assert pf1_before_scene and pf1_before_scene[-1] == 0xFF, (
            "PF1 da primeira linha deve estar carregado antes de desligar VBLANK", pf1_before_scene)
        scene = [[] for _ in range(160)]
        for cycle, register, value in events:
            row = cycle // 76 - start
            if 0 <= row < 160 and register in (0x1B, 0x1C, 0x0D, 0x0E, 0x0F, 0x1D, 0x1E):
                scene[row].append((cycle % 76, register, value))
            if register == 2:
                max_wsync = max(max_wsync, cycle % 76)
        rendered = machine.rendered
        assert rendered is not None
        check_beam_motion(events, start, end, rendered)
        player_start = 4096 + SYMBOLS["ArrowSprites"] - 0xF000 + rendered["Heading"] * 8
        boss_start = 4096 + SYMBOLS[sprites[rendered["RoomIndex"]]] - 0xF000
        for row, writes in enumerate(scene):
            logical = row // 2
            pf0 = [(c, v) for c, r, v in writes if r == 0x0D]
            assert len(pf0) == 2, (room, game, row, "PF0 esquerdo/direito", pf0)
            assert pf0[0][0] <= 22, (row, "PF0 esquerdo atrasado", pf0)
            assert 28 <= pf0[1][0] <= 71, (row, "PF0 direito fora da janela", pf0)
            border = 0xF0 if logical < 4 or logical >= 76 else 0x10
            right = 0 if rendered["DoorOpen"] and rendered["ExitDirection"] == 2 and 28 <= logical <= 51 else border
            assert [v for _, v in pf0] == [border, right], (room, game, row, "paredes/porta leste", pf0)
            if row % 2:
                enemy = [v for _, r, v in writes if r == 0x1E]
                expected_enemy = (2 if 4 <= logical < 76 else 0) if rendered["BeamMode"] else (
                    rendered["EnemyActive"] if rendered["EnemyY"] <= logical < rendered["EnemyY"] + 2 else 0)
                assert enemy == [expected_enemy], (row, "M1", enemy, expected_enemy)
                assert all(c <= 22 for c, r, _ in writes if r == 0x1E)
                assert not any(r in (0x1B, 0x1C, 0x1D, 0x0E, 0x0F) for _, r, _ in writes), (
                    row, "Pixels alterados na segunda linha", writes)
                continue
            for register in (0x1B, 0x1C):
                times = [c for c, r, _ in writes if r == register]
                assert times and max(times) <= 22, (row, hex(register), times)
            player_row = logical - rendered["YPos"]
            boss_row = logical - rendered["BossY"]
            player = (ROM[player_start + player_row] & rendered["PlayerMask"]
                      if 0 <= player_row < 8 else 0)
            boss = (ROM[boss_start + boss_row] & rendered["BossMask"]
                    if 0 <= boss_row < 12 else 0)
            shot = rendered["ShotActive"] if logical == rendered["ShotY"] else 0
            values = {r: value for _, r, value in writes}
            pf1_times = [cycle for cycle, register, _ in writes if register == 0x0E]
            pf2_times = [cycle for cycle, register, _ in writes if register == 0x0F]
            if row:
                assert pf1_times and max(pf1_times) <= 28, (row, "PF1 atrasado", pf1_times)
            assert pf2_times and max(pf2_times) <= 39, (row, "PF2 atrasado", pf2_times)
            assert values[0x1B] == player, (row, "P0", values[0x1B], player)
            assert values[0x1C] == boss, (row, "P1", values[0x1C], boss)
            assert values[0x1D] == shot, (row, "M0", values[0x1D], shot)
            pf1 = 0xFF if logical < 4 or logical >= 76 else 0
            pf2 = pf1
            if rendered["DoorOpen"] and rendered["ExitDirection"] == 1 and logical < 4:
                pf2 = 0x0F
            elif rendered["HazardVisible"] and 4 <= logical < 76:
                if rendered["HazardAxis"] == 1:
                    pf2 = 0xF0
                elif rendered["HazardAxis"] == 0 and 34 <= logical < 46:
                    pf1 = pf2 = 0xFF
            assert values[0x0E] == pf1 and values[0x0F] == pf2, (
                room, game, phase, row, "faixas/porta norte", values.get(0x0E), values.get(0x0F), pf1, pf2)
        frames += 1
    # Transicoes e reset tem mais escritas de estado que quadros comuns;
    # verificamos a composicao das rotinas, nao apenas cada WSYNC isolado.
    for room, exit_direction in ((0, 1), (1, 2), (2, 1)):
        machine.set(RoomIndex=room, GameState=3, DoorOpen=1,
                    ExitDirection=exit_direction, BossHP=0, Lives=2,
                    XPos=76 if exit_direction == 1 else 144,
                    YPos=6 if exit_direction == 1 else 40,
                    XFrac=0, YFrac=0, ShotActive=0, EnemyActive=0,
                    HazardActive=0, HazardVisible=0)
        machine.bus.joystick = 0xEF if exit_direction == 1 else 0x7F
        assert machine.frame() == 262 * 76, ("transicao", room)
        assert state(machine, ("RoomIndex", "GameState", "DoorOpen", "Lives")) == (room + 1, 0, 0, 2)
        machine.bus.joystick = 0xFF
        assert machine.frame() == 262 * 76, ("chegada", room + 1)
        frames += 2
    for game in (0, 1, 2, 3):
        machine.set(RoomIndex=3, GameState=game, DoorOpen=int(game == 3),
                    Lives=2, EnemyActive=0, HazardActive=0, HazardVisible=0)
        machine.bus.switches = 0xFE
        assert machine.frame() == 262 * 76, ("reset", game)
        assert state(machine, ("RoomIndex", "GameState", "DoorOpen", "Lives")) == (0, 0, 0, 3)
        frames += 1
    machine.bus.switches = 0xFF
    for axis in (2, 3):
        for phase in (1, 2):
            for heading in (0, 2, 4, 6):
                machine.set(RoomIndex=3, GameState=0, BossHP=6, BossPhase=phase,
                            PhaseTimer=20, BossX=112, BossY=30, BossFlash=2,
                            XPos=48, YPos=30, Heading=heading, XFrac=0, YFrac=0,
                            Lives=3, InvulnTimer=1, ShotActive=2, ShotX=24, ShotY=32,
                            ShotXFrac=0, ShotYFrac=0, ShotHeading=2, EnemyActive=0,
                            EnemyX=8, EnemyY=8, HazardAxis=axis, HazardVisible=1,
                            HazardActive=int(phase == 2), DoorOpen=0, ExitDirection=0)
                machine.bus.joystick = 0xFF
                machine.bus.fire = 0x80
                assert machine.frame() == 262 * 76, ("pior caso diagonal", axis, phase, heading)
                blank = [(c, v) for c, r, v in machine.bus.events if r == 1]
                start, end = blank[0][0] // 76, blank[1][0] // 76
                check_beam_motion(machine.bus.events, start, end, machine.rendered)
                frames += 1
    machine = Machine()
    machine.frame()          # estabiliza a fase da CPU apos o boot
    machine.set(RoomIndex=1, BossX=72, BossY=6, BossPhase=0, PhaseTimer=90,
                PatrolNode=0, PatrolMoving=0, XPos=144, YPos=66, Lives=3)
    for leg in range(4):
        machine.set(BossPhase=1, PhaseTimer=1, BossHeading=0, EnemyActive=0)
        assert machine.frame() == 262 * 76, ("disparo/caminhada", leg)
        for tick in range(64):
            assert machine.frame() == 262 * 76, ("caminhada raster", leg, tick)
        assert state(machine, ("BossX", "BossY")) == ((136, 34), (72, 62), (8, 34), (72, 6))[leg]
        assert machine.get("PatrolMoving") == 0
        frames += 65
    print(f"OK: {frames} quadros F8 de 262 linhas, quatro pisos, HMOVE diagonal isolado, motion sem deriva e patrulha; WSYNC ate {max_wsync}")


CHECKS = {"rom": check_rom, "controls": check_controls, "shots": check_shots,
          "boss": check_boss, "patrol": check_patrol, "enemy": check_enemy, "hits": check_hits,
          "rooms": check_rooms, "restart": check_restart,
          "video": check_video}

if __name__ == "__main__":
    selected = sys.argv[1:] or list(CHECKS)
    for name in selected:
        if name not in CHECKS:
            raise SystemExit("Use: " + " ".join(CHECKS))
        CHECKS[name]()
