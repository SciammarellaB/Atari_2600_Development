"""Executa a ROM F4 no py65: mansao, coletas, audio e ciclos. Nao simula o TIA.

Dependencia opcional: python3 -m pip install --target .tools/python py65==1.2.0
"""

from collections import defaultdict, deque
from pathlib import Path
import re

from py65.devices.mpu6502 import MPU
from hud import hud_data
from rooms import (HEIGHT, REPEAT, EXITS, NONE, OBJECT_TYPES, OBJECT_GLYPHS, OBJECT_COLORS, maps)

WALK_POSES = ("DownIdle", "DownWalkA", "DownWalkB", "UpIdle", "UpWalkA",
              "UpWalkB", "LeftIdle", "LeftWalkA", "LeftWalkB", "RightIdle",
              "RightWalkA", "RightWalkB")
ATTACK_POSES = ("DownFire", "DownRecoil", "UpFire", "UpRecoil", "LeftFire",
                "LeftRecoil", "RightFire", "RightRecoil")
POSES = WALK_POSES + ATTACK_POSES
AUDIO_REGISTERS = tuple(range(0x15, 0x1B))

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build"
SYMBOLS = {}
for line in (OUTPUT / "main.sym").read_text().splitlines():
    match = re.match(r"^(\w+)\s+([0-9a-fA-F]{4})\s", line)
    if match:
        SYMBOLS[match[1]] = int(match[2], 16)


class Bus:
    def __init__(self):
        self.rom = (OUTPUT / "main.bin").read_bytes()
        assert len(self.rom) == 32768
        self.bank = 7
        self.ram = bytearray(256)
        self.joystick = self.switches = 0xFF
        self.fire = 0x80
        self.cpu = None
        self.pending = []
        self.events = []
        self.timer_value = self.timer_start = 0

    def __getitem__(self, address):
        address &= 0x1FFF
        if address & 0x1000:
            if 0x1FF4 <= address <= 0x1FFB:
                self.bank = address - 0x1FF4
            return self.rom[self.bank * 4096 + (address & 0xFFF)]
        if not address & 0x80:
            return self.fire if address & 0xF == 0xC else 0
        if not address & 0x200:
            return self.ram[address & 255]
        if address == 0x280:
            return self.joystick
        if address == 0x282:
            return self.switches
        if address == 0x284:
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
            if 0x1FF4 <= address <= 0x1FFB:
                self.bank = address - 0x1FF4
                return
            raise AssertionError("Escrita em ROM")
        if address & 0x80 and not address & 0x200:
            self.ram[address & 255] = value
        else:
            self.pending.append((address, value))


class Machine:
    def __init__(self):
        self.bus = Bus()
        self.cpu = MPU(memory=self.bus, pc=None)
        self.bus.cpu = self.cpu
        self.min_sp = self.cpu.sp
        self.until("Frame")

    def step(self):
        self.cpu.step()
        self.min_sp = min(self.min_sp, self.cpu.sp)
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

    def frame_with_visible_snapshot(self):
        """Fotografa o cenario antes de DrawHud reutilizar os buffers."""
        self.bus.events.clear()
        self.step()
        self.until("DrawHud")
        snapshot = bytes(self.bus.ram)
        self.until("Frame")
        return snapshot

    def frame_with_hud_snapshots(self):
        """Fotografa buffers ao fim do cenario e depois de montar o HUD."""
        self.bus.events.clear()
        self.step()
        self.until("DrawHud")
        scene = bytes(self.bus.ram)
        self.until("WaitHudBlank")
        hud = bytes(self.bus.ram)
        self.until("Frame")
        return scene, hud

    def get(self, label):
        return self.bus[SYMBOLS[label]]

    def call(self, label):
        self.cpu.stPushWord(SYMBOLS["Frame"] - 1)
        self.cpu.pc = SYMBOLS[label]
        self.until("Frame")

    def room(self, index):
        self.bus[SYMBOLS["Room"]] = index
        self.call("LoadRoom")


def decode(values):
    """Leitura independente do empacotador: ordem real dos bits no TIA."""
    pf0, pf1, pf2 = values
    return [bool(pf0 & (1 << i)) for i in range(4, 8)] + [
        bool(pf1 & (1 << i)) for i in range(7, -1, -1)
    ] + [bool(pf2 & (1 << i)) for i in range(8)]


def put(machine, label, value):
    machine.bus[SYMBOLS[label]] = value


def player(machine):
    return machine.get("PlayerX"), machine.get("PlayerY")


def animation(machine):
    return (machine.get("Facing"), machine.get("WalkFrame"),
            machine.get("AnimClock"), machine.get("Moving"))


def shot(machine):
    return (machine.get("ShotX"), machine.get("ShotY"), machine.get("ShotDir"),
            machine.get("AttackTimer"))


def place(machine, room, x, y, gate=0, facing=0, walk=0, clock=0, moving=0):
    machine.room(room)
    put(machine, "PlayerX", x)
    put(machine, "PlayerY", y)
    put(machine, "GateMask", gate)
    put(machine, "StepClock", 0)
    put(machine, "Facing", facing)
    put(machine, "WalkFrame", walk)
    put(machine, "AnimClock", clock)
    put(machine, "Moving", moving)
    machine.bus.joystick = machine.bus.switches = 0xFF
    machine.call("ClearSpriteRows")
    put(machine, "Weapon", 1)
    put(machine, "Ammo", 0x30)


def tick_twice(machine, joystick):
    machine.bus.joystick = joystick
    machine.call("UpdateGame")
    machine.call("UpdateGame")


def expected_stand(room, x, y, gate):
    if x > 152 or y > 44:
        return False
    rows = maps()[room]
    gate_column = 0 if room in (5, 8) else 39
    return not any(rows[row][column] == "#" or
                   gate == 2 and 20 <= row <= 27 and column == gate_column
                   for row in range(y, y + 4)
                   for column in range(x // 4, (x + 7) // 4 + 1))


def expected_row_color(room, row):
    """Bit0 e metadado; a cor NTSC ocupa os demais sete bits."""
    if 34 <= row < 38:
        return OBJECT_COLORS[OBJECT_TYPES[room]]
    if room in (4, 5, 7, 8):
        base = 0x46 if room in (4, 5) else 0x86
        return base | int(20 <= row < 28)
    return 0

def check_maps():
    machine = Machine()
    table_names = ("LeftPF0", "LeftPF1", "LeftPF2", "RightPF0", "RightPF1",
                   "RightPF2", "ObjectRows", "GateRows")
    for name in table_names:
        assert SYMBOLS[name] % 256 == 0
    for room, rows in enumerate(maps()):
        machine.room(room)
        assert machine.bus.bank == room // 2
        assert machine.get("RowStart") == room % 2 * HEIGHT
        start = room % 2 * HEIGHT
        for y, row in enumerate(rows):
            rendered = []
            for side in ("Left", "Right"):
                values = [machine.bus[SYMBOLS[f"{side}PF{i}"] + start + y]
                          for i in range(3)]
                assert values[0] & 15 == 0
                rendered += decode(values)
            assert rendered == [cell == "#" for cell in row], (room, y)
            encoded = machine.bus[SYMBOLS["GateRows"] + start + y]
            assert encoded == expected_row_color(room, y)
            assert encoded & 1 == int(room in (4, 5, 7, 8) and 20 <= y < 28)
            assert machine.bus[SYMBOLS["ObjectRows"] + start + y] == (
                OBJECT_GLYPHS[OBJECT_TYPES[room]][y - 34] if 34 <= y < 38 else 0)
    # O mesmo programa deve continuar no mesmo PC depois do hotspot.
    for bank in range(8):
        machine.bus[0xFFF4 + bank]
        assert machine.bus.bank == bank
        assert machine.bus[SYMBOLS["Frame"]] == machine.bus.rom[SYMBOLS["Frame"] & 4095]
    assert SYMBOLS["PlayerGraphic"] == SYMBOLS["ROMPlayerGraphics"] == SYMBOLS[POSES[0]]
    assert [SYMBOLS[name] for name in WALK_POSES] == [
        SYMBOLS["ROMPlayerGraphics"] + pose * 8 for pose in range(12)
    ]
    assert [SYMBOLS[name] for name in ATTACK_POSES] == [
        SYMBOLS["ROMPlayerGraphics"] + 96 + pose * 8 for pose in range(8)
    ]
    assert [machine.bus[SYMBOLS["ROMPlayerGraphics"] + i] for i in range(8)] == [
        0x3C, 0x7E, 0x5A, 0x3C, 0x7E, 0xBD, 0x24, 0x66
    ]
    assert [machine.bus[SYMBOLS["FacingOffsets"] + i] for i in range(4)] == [0, 24, 48, 72]
    expected_ram = {
        "Facing": 0x89, "WalkFrame": 0x8A, "AnimClock": 0x8B, "Moving": 0x8C,
        "CurrentSprite": 0x8D, "NextGate": 0x8E, "Aim": 0x8F,
        "ShotX": 0x90, "ShotY": 0x91, "ShotDir": 0x92,
        "AttackTimer": 0x93, "NextShot": 0x94, "CameraY": 0x95,
        "ShotViewY": 0x96, "Health": 0x97, "Ammo": 0x98, "Weapon": 0x99,
        "SpriteRows": 0x9A, "SpriteTopRows": 0x9A, "SpriteBottomRows": 0xC3,
        "InputBits": 0x9A, "CandX": 0x9B, "CandY": 0x9C,
        "LeftCol": 0x9D, "RightCol": 0x9E, "BottomRow": 0x9F,
        "ScanRow": 0xA0, "ScanCol": 0xA1, "CollisionPtr": 0xA2,
        "MoveExit": 0xA4, "MusicStep": 0xEC, "MusicClock": 0xED,
        "SfxState": 0xEE, "PuzzleFlags": 0xEF, "PickedLo": 0xF0,
        "PickedHi": 0xF1, "ObjectMask": 0xF2,
    }
    assert {name: SYMBOLS[name] for name in expected_ram} == expected_ram
    assert SYMBOLS["SpriteRows"] + 40 == SYMBOLS["ObjectGraphic"] == 0xC2
    assert SYMBOLS["SpriteBottomRows"] + 40 == 0xEB
    assert [SYMBOLS[name] for name in table_names] == list(range(SYMBOLS["LeftPF0"], SYMBOLS["LeftPF0"] + 0x800, 0x100))
    assert SYMBOLS["SfxCodeEnd"] <= 0xF700
    assert SYMBOLS["SfxDataEnd"] <= 0xF800
    assert SYMBOLS["MusicDataEnd"] <= 0xFFF4
    source = (ROOT / "main.asm").read_text()
    for name in POSES:
        body = source.split(f"{name}\n", 1)[1].split("\n", 9)[:8]
        assert all(re.fullmatch(r"\s*byte\s+%[01]{8}", line) for line in body), name
    print("OK: mapas, GateRows, 20 poses binarias e layout RAM/buffers/pilha")


def check_collision():
    machine = Machine()
    xs = (0, 2, 26, 28, 30, 34, 36, 40, 72, 136, 150, 152)
    ys = (0, 1, 19, 20, 24, 27, 28, 31, 32, 34, 35, 36, 37, 39, 44)
    checked = 0
    for room in range(9):
        machine.room(room)
        for gate in (0, 2):
            put(machine, "GateMask", gate)
            for x in xs:
                for y in ys:
                    put(machine, "CandX", x)
                    put(machine, "CandY", y)
                    put(machine, "CollisionPtr", 0xA5)
                    machine.call("CanStand")
                    free = not (machine.cpu.p & 1)
                    assert free == expected_stand(room, x, y, gate), (room, gate, x, y)
                    checked += 1
        for x, y in ((153, 20), (40, 45)):
            put(machine, "CandX", x)
            put(machine, "CandY", y)
            put(machine, "CollisionPtr", 0xA5)
            machine.call("CanStand")
            assert machine.cpu.p & 1, ("limite externo", room, x, y)
            checked += 1
    print(f"OK: {checked} bboxes; mobiliario, objetos caminhaveis e portas nos dois lados")


def check_sprite_rows():
    machine = Machine()
    for facing in range(4):
        for walk in range(3):
            y = (facing * 11 + walk * 5) % 45
            place(machine, 0, 40, y, facing=facing, walk=walk)
            put(machine, "CameraY", 0)
            machine.call("UpdateCamera")
            machine.call("BuildSpriteRows")
            pose = SYMBOLS["ROMPlayerGraphics"] + facing * 24 + walk * 8
            glyph = [machine.bus[pose + i] for i in range(8)]
            top = [machine.bus[SYMBOLS["SpriteTopRows"] + row] for row in range(41)]
            bottom = [machine.bus[SYMBOLS["SpriteBottomRows"] + row] for row in range(41)]
            expected_top = [0] * 41
            expected_bottom = [0] * 41
            view_y = y - machine.get("CameraY")
            expected_top[view_y:view_y + 4] = glyph[::2]
            expected_bottom[view_y:view_y + 4] = glyph[1::2]
            assert top == expected_top, (facing, walk, "top")
            assert bottom == expected_bottom, (facing, walk, "bottom")
            assert machine.get("CurrentSprite") == expected_top[0]
    for facing in range(4):
        for timer, attack_pose in ((12, 0), (7, 0), (6, 1), (1, 1)):
            y = 8 + facing * 5
            place(machine, 0, 40, y, facing=facing)
            put(machine, "CameraY", 0)
            machine.call("UpdateCamera")
            put(machine, "AttackTimer", timer)
            machine.call("BuildSpriteRows")
            pose = SYMBOLS["ROMPlayerGraphics"] + 96 + facing * 16 + attack_pose * 8
            glyph = [machine.bus[pose + i] for i in range(8)]
            top = [machine.bus[SYMBOLS["SpriteTopRows"] + row] for row in range(41)]
            bottom = [machine.bus[SYMBOLS["SpriteBottomRows"] + row] for row in range(41)]
            view_y = y - machine.get("CameraY")
            assert top[view_y:view_y + 4] == glyph[::2], (facing, timer, "top")
            assert bottom[view_y:view_y + 4] == glyph[1::2], (facing, timer, "bottom")
            assert sum(bool(value) for value in top[:view_y] + top[view_y + 4:]) == 0
            assert sum(bool(value) for value in bottom[:view_y] + bottom[view_y + 4:]) == 0
    print("OK: 12 poses de marcha e 8 de ataque em top/bottom, com sentinelas")


def check_movement():
    machine = Machine()
    for joystick, delta, facing in ((0xBF, (-2, 0), 2), (0x7F, (2, 0), 3),
                                    (0xEF, (0, -1), 1), (0xDF, (0, 1), 0),
                                    (0xAF, (-2, -1), 2), (0x6F, (2, -1), 3),
                                    (0x9F, (-2, 1), 2), (0x5F, (2, 1), 3)):
        place(machine, 0, 40, 39)
        tick_twice(machine, joystick)
        assert player(machine) == (40 + delta[0], 39 + delta[1])
        assert animation(machine) == (facing, 1, 1, 1)
    for joystick in (0xFF, 0x3F, 0xCF, 0x0F, 0x2F, 0x1F, 0x8F, 0x4F,
                     0xF0, 0xF5, 0xFA):
        place(machine, 0, 40, 39)
        tick_twice(machine, joystick)
        assert player(machine) == (40, 39)
        assert animation(machine) == (0, 0, 0, 0)
    place(machine, 0, 40, 0)
    tick_twice(machine, 0xEF)
    assert player(machine) == (40, 0) and machine.get("Room") == 0
    assert animation(machine) == (1, 0, 0, 0)
    place(machine, 4, 148, 20, gate=2)
    tick_twice(machine, 0x7F)
    assert player(machine) == (148, 20) and machine.get("Room") == 4
    place(machine, 5, 4, 20, gate=2)
    tick_twice(machine, 0xBF)
    assert player(machine) == (4, 20) and machine.get("Room") == 5
    assert animation(machine) == (2, 0, 0, 0)

    # Cada pose de marcha dura quatro passos bem-sucedidos.
    place(machine, 0, 40, 39, facing=3)
    expected = [(1, 1), (1, 2), (1, 3), (2, 0),
                (2, 1), (2, 2), (2, 3), (1, 0), (1, 1)]
    for step, (walk, clock) in enumerate(expected, 1):
        tick_twice(machine, 0x7F)
        assert player(machine) == (40 + step * 2, 39)
        assert animation(machine) == (3, walk, clock, 1)
    # O frame pulado preserva a marcha; neutro para imediatamente nesse frame.
    before = (*player(machine), *animation(machine))
    machine.call("UpdateGame")
    assert (*player(machine), *animation(machine)) == before
    machine.bus.joystick = 0xFF
    machine.call("UpdateGame")
    assert animation(machine) == (3, 0, 0, 0)
    place(machine, 0, 40, 39, facing=2, walk=2, clock=3, moving=1)
    machine.bus.joystick = 0x3F
    machine.call("UpdateGame")
    assert player(machine) == (40, 39)
    assert animation(machine) == (2, 0, 0, 0)
    # Mudar de direcao atualiza Facing e reinicia a pose mesmo antes do passo.
    place(machine, 0, 40, 39, facing=3, walk=2, clock=3, moving=1)
    machine.bus.joystick = 0xEF
    machine.call("UpdateGame")
    assert player(machine) == (40, 39)
    assert animation(machine) == (1, 0, 0, 0)
    print("OK: oito direcoes a 30 Hz, opostos, parada, Facing e cadencia de 4 passos")


def check_diagonals():
    machine = Machine()
    checked = 0
    for room in range(9):
        for x in range(4, 149, 8):
            for y in range(1, 41, 4):
                if not expected_stand(room, x, y, 0):
                    continue
                for joystick, dx, dy in ((0xAF, -2, -1), (0x6F, 2, -1),
                                         (0x9F, -2, 1), (0x5F, 2, 1)):
                    place(machine, room, x, y)
                    tick_twice(machine, joystick)
                    expected = (x + dx, y + dy) if expected_stand(
                        room, x + dx, y + dy, 0) else (x, y)
                    assert player(machine) == expected, (room, x, y, joystick)
                    checked += 1
    print(f"OK: {checked} diagonais verificadas contra mobiliario e paredes")

def portal_cases():
    for room, exits in enumerate(EXITS):
        for direction, target in enumerate(exits):
            if target == NONE:
                continue
            x, y, joystick, new_x, new_y = (
                (0, 22, 0xBF, 152, 22), (152, 22, 0x7F, 0, 22),
                (76, 0, 0xEF, 76, 44), (76, 44, 0xDF, 76, 0))[direction]
            yield room, x, y, joystick, target, new_x, new_y


def check_transitions():
    machine = Machine()
    cases = list(portal_cases())
    for room, x, y, joystick, target, new_x, new_y in cases:
        put(machine, "PuzzleFlags", 6)
        place(machine, room, x, y)
        put(machine, "Health", 2)
        put(machine, "Ammo", 0x54)
        put(machine, "Weapon", 3)
        tick_twice(machine, joystick)
        assert (machine.get("Room"), *player(machine)) == (target, new_x, new_y)
        assert machine.bus.bank == target // 2
        assert machine.get("RowStart") == target % 2 * HEIGHT
        assert machine.get("RowEnd") == (target % 2 + 1) * HEIGHT
        assert (machine.get("Health"), machine.get("Ammo"), machine.get("Weapon")) == (2, 0x54, 3)
    for room, x, joystick in ((4, 148, 0x7F), (5, 4, 0xBF),
                               (7, 148, 0x7F), (8, 4, 0xBF)):
        put(machine, "PuzzleFlags", 0)
        place(machine, room, x, 22, gate=2)
        tick_twice(machine, joystick)
        assert (machine.get("Room"), *player(machine)) == (room, x, 22)
    print(f"OK: {len(cases)} portais com retorno/banco correto; quatro lados bloqueados")

def check_switch_and_console():
    machine = Machine()
    assert (machine.get("Room"), *player(machine), machine.get("Health"),
            machine.get("Ammo"), machine.get("Weapon")) == (1, 76, 36, 3, 0, 0)
    for room, kind in enumerate(OBJECT_TYPES):
        if not kind:
            continue
        for x, y in ((28, 32), (34, 35)):
            machine = Machine()
            machine.room(room)
            put(machine, "PlayerX", x)
            put(machine, "PlayerY", y)
            put(machine, "Health", 1)
            machine.call("UpdateWorld")
            assert machine.get("PickedHi" if room == 8 else "PickedLo") & 1 << (room % 8)
            assert machine.get("ObjectMask") == (0x81 if kind == 4 else 0)
            expected = (3 if kind == 3 else 1, 0x12 if kind == 2 else 0,
                        1 if kind == 1 else 2 if kind == 5 else 0, 2 if kind == 4 else 0)
            actual = tuple(machine.get(label) for label in ("Health", "Ammo", "Weapon", "PuzzleFlags"))
            assert actual == expected, (room, actual, expected)
            machine.call("UpdateWorld")
            assert tuple(machine.get(label) for label in ("Health", "Ammo", "Weapon", "PuzzleFlags")) == expected
            machine.room(1)
            machine.room(room)
            assert machine.get("ObjectMask") == (0x81 if kind == 4 else 0)
    for ammo in range(100):
        machine = Machine()
        machine.room(2)
        put(machine, "PlayerX", 28)
        put(machine, "PlayerY", 32)
        put(machine, "Ammo", (ammo // 10) * 16 + ammo % 10)
        machine.call("UpdateWorld")
        result = min(99, ammo + 12)
        assert machine.get("Ammo") == result // 10 * 16 + result % 10
        assert not machine.cpu.p & 8, "Coleta deixa decimal mode desligado"
    # Limites do centro: chegar perto nao basta; botao de tiro nao interfere.
    for room in (0, 2, 3, 5, 6, 8):
        for x, y in ((26, 32), (36, 32), (28, 31), (28, 36)):
            machine = Machine()
            machine.room(room)
            put(machine, "PlayerX", x)
            put(machine, "PlayerY", y)
            machine.call("UpdateWorld")
            assert machine.get("PickedLo") == machine.get("PickedHi") == 0
    machine = Machine()
    put(machine, "PuzzleFlags", 6)
    put(machine, "PickedLo", 0xFF)
    put(machine, "PickedHi", 1)
    put(machine, "Health", 1)
    put(machine, "Ammo", 0x47)
    put(machine, "Weapon", 3)
    for room in (2, 3, 4, 5, 6, 7, 8, 0, 1):
        machine.bus.switches = 0xFD
        machine.call("UpdateGame")
        assert (machine.get("Room"), *player(machine)) == (room, 76, 36)
        assert tuple(machine.get(label) for label in ("Health", "Ammo", "Weapon", "PuzzleFlags", "PickedLo", "PickedHi")) == (1, 0x47, 3, 6, 255, 1)
        machine.call("UpdateGame")
        assert machine.get("Room") == room
        machine.bus.switches = 0xFF
        machine.call("UpdateGame")
    machine.bus.switches = 0xFC
    machine.call("UpdateGame")
    assert (machine.get("Room"), *player(machine)) == (1, 76, 36)
    assert tuple(machine.get(label) for label in ("Health", "Ammo", "Weapon", "PuzzleFlags", "PickedLo", "PickedHi")) == (3, 0, 0, 0, 0, 0)
    print("OK: coleta automatica/limites/uma vez por sala, BCD cap99, cura, Select preserva e Reset limpa")

def check_world_frames():
    costs = []
    for room, kind in enumerate(OBJECT_TYPES):
        if not kind:
            continue
        machine = Machine()
        machine.room(room)
        put(machine, "PlayerX", 40)
        put(machine, "PlayerY", 32)
        put(machine, "Health", 1)
        machine.frame()  # estabiliza Frame -> Frame, ainda fora do objeto
        put(machine, "PlayerX", 28)
        put(machine, "Weapon", 1)
        put(machine, "ShotX", 80)
        put(machine, "ShotY", 20)
        put(machine, "ShotDir", 0x50)
        put(machine, "AttackTimer", 12)
        if room == 6:
            put(machine, "Ammo", 0x99)  # inclui caminho de saturacao da coleta
        before = machine.cpu.processorCycles
        machine.step()
        machine.until("WaitOverscan")
        cost = machine.cpu.processorCycles - machine.bus.timer_start
        costs.append(cost)
        assert cost <= 35 * 64 - 128, (room, kind, cost)
        machine.until("Frame")
        assert machine.cpu.processorCycles - before == 262 * 76, (room, kind)
        assert machine.get("SfxState") == 0x8B
        for _ in range(2):
            before = machine.cpu.processorCycles
            machine.frame()
            assert machine.cpu.processorCycles - before == 262 * 76, (room, kind)
        assert machine.min_sp >= 0xF3, hex(machine.min_sp)
    # Chave nao abre de longe nem fora da altura da porta. Abre dos dois lados.
    for room, x, y, opens in ((7, 142, 22, False), (7, 144, 16, False),
                              (7, 144, 28, False), (7, 144, 17, True),
                              (8, 8, 22, False), (8, 6, 22, True)):
        machine = Machine()
        machine.room(room)
        put(machine, "Weapon", 3)
        put(machine, "PlayerX", x)
        put(machine, "PlayerY", y)
        machine.call("UpdateWorld")
        assert machine.get("PuzzleFlags") == (4 if opens else 0), (room, x, y)
        assert machine.get("Weapon") == (1 if opens else 3)
        assert machine.get("GateMask") == (0 if opens else 2)
        machine.frame()
        before = machine.cpu.processorCycles
        machine.frame()
        assert machine.cpu.processorCycles - before == 262 * 76
    print(f"OK: coletas/puzzles com tiro ativo; overscan ate {max(costs)} ciclos, acao e chave nos dois lados")


def check_mansion_route():
    """BFS independente encontra o caminho; a ROM executa cada passo real."""
    machine = Machine()
    visited = {machine.get("Room")}
    count = 0
    directions = ((-2, 0, 0xBF), (2, 0, 0x7F), (0, -1, 0xEF), (0, 1, 0xDF))

    def walk(target):
        nonlocal count
        room = machine.get("Room")
        initial = player(machine)
        queue = deque([initial])
        previous = {initial: None}
        while queue and target not in previous:
            x, y = queue.popleft()
            for dx, dy, joystick in directions:
                new = x + dx, y + dy
                if new not in previous and min(new) >= 0 and expected_stand(
                        room, *new, machine.get("GateMask")):
                    previous[new] = ((x, y), joystick)
                    queue.append(new)
        assert target in previous, ("objeto/porta inacessivel", room, target)
        path = []
        current = target
        while current != initial:
            prior, joystick = previous[current]
            path.append((current, joystick))
            current = prior
        for position, joystick in reversed(path):
            tick_twice(machine, joystick)
            assert player(machine) == position and machine.get("Room") == room
            machine.call("UpdateWorld")
            machine.call("ClearSpriteRows")
            count += 1

    def travel(target):
        source = machine.get("Room")
        direction = EXITS[source].index(target)
        start, joystick = (((0, 22), 0xBF), ((152, 22), 0x7F),
                           ((76, 0), 0xEF), ((76, 44), 0xDF))[direction]
        walk(start)
        tick_twice(machine, joystick)
        assert machine.get("Room") == target
        assert machine.bus.bank == target // 2
        machine.call("UpdateWorld")
        machine.call("ClearSpriteRows")
        visited.add(target)

    def collect():
        walk((28, 32))
        assert machine.get("PickedHi" if machine.get("Room") == 8 else "PickedLo") & 1 << (machine.get("Room") % 8)

    def reachable(puzzles):
        queue, seen = [1], {1}
        for room in queue:
            for target in EXITS[room]:
                if target == NONE or target in seen:
                    continue
                if {room, target} == {4, 5} and not puzzles & 2:
                    continue
                if {room, target} == {7, 8} and not puzzles & 4:
                    continue
                seen.add(target)
                queue.append(target)
        return seen

    assert reachable(0) == {0, 1, 2, 3, 4, 6, 7}
    assert reachable(2) == set(range(8))
    assert reachable(6) == set(range(9))
    # Sem arma, Fire nao gera ataque nem gasta municao.
    machine.bus.fire = 0
    machine.call("UpdateShot")
    assert machine.get("ShotY") == 128 and machine.get("Ammo") == 0
    machine.bus.fire = 0x80
    travel(4)
    walk((148, 22))
    tick_twice(machine, 0x7F)
    assert machine.get("Room") == 4 and player(machine) == (148, 22)
    travel(3)
    collect()
    assert machine.get("Weapon") == 1 and machine.get("Ammo") == 0
    travel(0)
    collect()
    assert machine.get("PuzzleFlags") == 2 and machine.get("ObjectMask") == 0x81
    travel(1)
    travel(2)
    collect()
    assert machine.get("Ammo") == 0x12
    travel(1)
    travel(4)
    assert machine.get("GateMask") == 0
    travel(5)
    collect()
    assert machine.get("Weapon") == 3
    travel(4)
    travel(7)
    assert machine.get("GateMask") == 2
    walk((144, 22))
    assert machine.get("PuzzleFlags") == 6 and machine.get("Weapon") == 1
    assert machine.get("GateMask") == 0
    travel(8)
    put(machine, "Health", 1)  # sem inimigos: injecao diagnostica para a cura
    collect()
    assert machine.get("Health") == 3
    travel(7)
    assert machine.get("GateMask") == 0 and machine.get("Weapon") == 1
    travel(6)
    collect()
    assert machine.get("Ammo") == 0x24
    assert visited == set(range(9)) and machine.get("PickedLo") == 0x6D
    assert machine.get("PickedHi") == 1
    assert machine.min_sp >= 0xF3, hex(machine.min_sp)
    print(f"OK: percurso fisico BFS de {count} passos nas nove salas, arma/balas/switch/chave/cura e retorno")


def check_camera():
    machine = Machine()
    cases = (
        # camera inicial, PlayerY, camera resultante
        (0, 0, 0), (0, 7, 0), (0, 8, 0), (0, 28, 0), (0, 29, 1),
        (4, 11, 3), (4, 12, 4), (4, 32, 4), (4, 33, 5), (8, 44, 8),
    )
    for room in range(9):
        machine.room(room)
        for initial, y, expected in cases:
            put(machine, "CameraY", initial)
            put(machine, "PlayerY", y)
            put(machine, "ShotY", 128)
            machine.call("UpdateCamera")
            assert machine.get("CameraY") == expected, (room, initial, y)
            assert machine.get("RowStart") == room % 2 * HEIGHT
            assert machine.get("RowEnd") == room % 2 * HEIGHT + expected + 40
            assert 0 <= y - expected <= 36

    machine.room(0)
    for camera, player_y, shot_y, expected in (
            (0, 20, 0, 0), (0, 20, 39, 39), (0, 20, 40, 128),
            (4, 20, 3, 0xFF), (4, 20, 4, 0), (4, 20, 43, 39),
            (8, 36, 47, 39), (8, 36, 128, 128)):
        put(machine, "CameraY", camera)
        put(machine, "PlayerY", player_y)
        put(machine, "ShotY", shot_y)
        machine.call("UpdateCamera")
        assert machine.get("CameraY") == camera
        assert machine.get("ShotViewY") == expected, (camera, shot_y)
    print("OK: CameraY 0..8, deadzone 8/28, RowEnd e recorte vertical do tiro")


def check_hud_data():
    machine = Machine()
    tables = hud_data()
    heart_columns = {column for value in tables["HudHeart"]
                     for column, enabled in enumerate(decode((value, 0, 0))) if enabled}
    bullet_columns = {column for value in tables["HudBullet"]
                      for column, enabled in enumerate(decode((0, 0, value))) if enabled}
    weapon_off = tables["HudWeapon"][:5]
    weapon_columns = {column for value in tables["HudWeapon"][5:10]
                      for column, enabled in enumerate(decode((0, 0, value))) if enabled}
    assert heart_columns == {0, 1, 2}
    assert bullet_columns == {15, 16}
    assert weapon_off == [0] * 5 and weapon_columns == {14, 15, 16, 17, 18}
    cases = ((health, ammo // 10 * 16 + ammo % 10, weapon)
             for health in range(4) for ammo in range(100) for weapon in range(4))
    for health, ammo, weapon in cases:
        machine.call("ClearSpriteRows")
        put(machine, "Health", health)
        put(machine, "Ammo", ammo)
        put(machine, "Weapon", weapon)
        machine.call("BuildHud")
        tens, ones = ammo >> 4, ammo & 15
        expected = {
            "HudLeft0": tables["HudHeart"],
            "HudLeft1": tables["HudHealth"][health * 5:health * 5 + 5],
            "HudLeft2": tables["HudBullet"],
            "HudRight0": tables["HudTens"][tens * 5:tens * 5 + 5],
            "HudRight1": tables["HudOnes"][ones * 5:ones * 5 + 5],
            "HudRight2": tables["HudWeapon"][weapon * 5:weapon * 5 + 5],
        }
        for label, values in expected.items():
            assert list(machine.bus.ram[SYMBOLS[label]:SYMBOLS[label] + 5]) == values
        for row in range(5):
            left = decode([expected[f"HudLeft{i}"][row] for i in range(3)])
            right = decode([expected[f"HudRight{i}"][row] for i in range(3)])
            assert not any(left[column] for column in (3, 6, 9, 12, 13, 14, 17, 18, 19))
            assert not any(right[column] for column in range(20) if column not in (
                0, 1, 2, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18))
            if row in (1, 2, 3):
                assert sum(left[start] and left[start + 1] for start in (4, 7, 10)) == health
            else:
                assert not any(left[4:12])
    print("OK: 1600 HUDs: vida0..3, balas00..99, arma/chave0..3 e colunas PF")


def set_shot(machine, room, x, y, direction, gate=0, timer=0):
    machine.room(room)
    put(machine, "GateMask", gate)
    put(machine, "ShotX", x)
    put(machine, "ShotY", y)
    put(machine, "ShotDir", direction)
    put(machine, "AttackTimer", timer)
    machine.bus.fire = 0x80


def shot_blocked(machine, room, x, y, gate=0):
    set_shot(machine, room, x, y, 0, gate)
    machine.call("ShotBlocked")
    return bool(machine.cpu.p & 1)


def check_shots():
    machine = Machine()
    trajectories = ((0x40, -2, 0), (0x80, 2, 0), (0x10, 0, -1), (0x20, 0, 1),
                    (0x50, -2, -1), (0x90, 2, -1), (0x60, -2, 1), (0xA0, 2, 1))
    for direction, dx, dy in trajectories:
        set_shot(machine, 0, 80, 20, direction, timer=12)
        put(machine, "Ammo", 0x30)
        machine.call("UpdateShot")
        assert shot(machine) == (80 + dx, 20 + dy, direction, 11)
        assert machine.get("Ammo") == 0x30
    set_shot(machine, 0, 80, 20, 0x50, timer=4)
    put(machine, "Aim", 0xA0)
    machine.call("UpdateShot")
    assert shot(machine) == (78, 19, 0x50, 3)
    rows = maps()
    checked = 0
    for room in range(9):
        for gate in (0, 2):
            for x in range(0, 160, 8):
                for y in range(0, 48, 3):
                    col = x // 4
                    gate_col = 0 if room in (5, 8) else 39
                    expected = y >= 47 or any(rows[room][row][col] == "#" or
                        gate == 2 and col == gate_col and 20 <= row <= 27
                        for row in (y, y + 1) if row < 48)
                    assert shot_blocked(machine, room, x, y, gate) == expected, (room, gate, x, y)
                    checked += 1
    muzzle = ((4, 3, 0x20), (4, -2, 0x10), (-2, 1, 0x40), (8, 1, 0x80))
    for facing, (dx, dy, aim) in enumerate(muzzle):
        place(machine, 0, 80, 20, facing=facing)
        put(machine, "Aim", aim)
        put(machine, "ShotY", 128)
        put(machine, "AttackTimer", 0)
        machine.bus.fire = 0
        machine.call("UpdateShot")
        assert shot(machine) == (80 + dx, 20 + dy, aim, 12)
        assert machine.get("Ammo") == 0x29
    for ammo in range(1, 100):
        place(machine, 0, 40, 0, facing=1)
        put(machine, "Aim", 0x10)
        put(machine, "ShotY", 128)
        put(machine, "AttackTimer", 0)
        put(machine, "Ammo", ammo // 10 * 16 + ammo % 10)
        machine.bus.fire = 0
        machine.call("UpdateShot")
        assert machine.get("ShotY") == 128 and machine.get("AttackTimer") == 12
        assert machine.get("Ammo") == (ammo - 1) // 10 * 16 + (ammo - 1) % 10
        assert not machine.cpu.p & 8
    for weapon, ammo in ((0, 0x30), (2, 0x30), (1, 0), (3, 0)):
        put(machine, "ShotY", 128)
        put(machine, "AttackTimer", 0)
        put(machine, "Weapon", weapon)
        put(machine, "Ammo", ammo)
        machine.bus.fire = 0
        machine.call("UpdateShot")
        assert machine.get("ShotY") == 128 and machine.get("AttackTimer") == 0, (weapon, ammo)
        assert machine.get("Ammo") == ammo
    place(machine, 0, 80, 20, facing=3)
    put(machine, "Aim", 0x80)
    put(machine, "ShotY", 128)
    put(machine, "AttackTimer", 2)
    put(machine, "Ammo", 1)
    machine.bus.fire = 0
    machine.call("UpdateShot")
    assert machine.get("ShotY") == 128 and machine.get("AttackTimer") == 1
    machine.call("UpdateShot")
    assert shot(machine) == (88, 21, 0x80, 12) and machine.get("Ammo") == 0
    for room in range(9):
        put(machine, "ShotY", 20)
        put(machine, "AttackTimer", 9)
        machine.room(room)
        assert machine.get("ShotY") == 128 and machine.get("AttackTimer") == 0
    print(f"OK: oito trajetorias, {checked} colisoes M1, BCD, arma/chave, cooldown e autofire")

def check_shot_frames():
    simultaneous = Machine()
    place(simultaneous, 0, 40, 39)
    put(simultaneous, "StepClock", 1)
    simultaneous.bus.joystick = 0x6F
    simultaneous.bus.fire = 0
    simultaneous.frame()
    assert player(simultaneous) == (42, 38)
    assert shot(simultaneous) == (50, 39, 0x90, 12)

    machine = Machine()
    place(machine, 0, 36, 39, facing=2)
    machine.frame()
    put(machine, "PlayerX", 36)
    put(machine, "PlayerY", 39)
    put(machine, "Facing", 2)
    put(machine, "StepClock", 1)
    put(machine, "AttackTimer", 12)
    put(machine, "ShotX", 80)
    put(machine, "ShotY", 20)
    put(machine, "ShotDir", 0x50)
    machine.min_sp = machine.cpu.sp
    machine.bus.joystick = 0xAF       # esquerda+cima; destino x=34 ocupa 3 colunas
    machine.bus.fire = 0
    before = machine.cpu.processorCycles
    visible = machine.frame_with_visible_snapshot()
    assert machine.cpu.processorCycles - before == 262 * 76
    assert (machine.get("Room"), *player(machine)) == (0, 34, 38)
    assert animation(machine) == (2, 1, 1, 1)
    assert shot(machine) == (78, 19, 0x50, 11)
    assert visible[SYMBOLS["AttackTimer"]] == 12
    assert visible[SYMBOLS["ShotY"]] == 20
    assert machine.min_sp >= 0xF3
    sync = [(cycle, value) for cycle, reg, value in machine.bus.events if reg == 0]
    blank = [(cycle, value) for cycle, reg, value in machine.bus.events if reg == 1]
    assert [value for _, value in sync] == [2, 0]
    assert [value for _, value in blank] == [0, 2]
    assert sync[1][0] // 76 - sync[0][0] // 76 == 3
    assert blank[0][0] // 76 - sync[1][0] // 76 == 37
    assert blank[1][0] // 76 - blank[0][0] // 76 == 192
    projectile = [(cycle, value) for cycle, reg, value in machine.bus.events
                  if reg == 0x1E and blank[0][0] <= cycle < blank[1][0]]
    first = blank[0][0] // 76
    scene_projectile = [(cycle, value) for cycle, value in projectile
                        if cycle // 76 < first + 160]
    assert len(scene_projectile) == 40
    assert [(row, cycle % 76, value)
            for row, (cycle, value) in enumerate(scene_projectile) if value] == [(12, 6, 2)]
    print("OK: movimento+tiro e pior quadro diagonal/ataque/bala mantem 262/37/192")


def check_shot_clipping():
    for shot_y, view_y in ((3, 0xFF), (43, 39)):
        machine = Machine()
        place(machine, 0, 40, 20)
        machine.frame()
        put(machine, "CameraY", 4)
        put(machine, "PlayerY", 20)
        put(machine, "ShotX", 80)
        put(machine, "ShotY", shot_y)
        put(machine, "ShotDir", 0)
        put(machine, "AttackTimer", 12)
        machine.frame_with_visible_snapshot()
        assert machine.get("CameraY") == 4
        blank = [(cycle, value) for cycle, reg, value in machine.bus.events if reg == 1]
        first = blank[0][0] // 76
        before = [(cycle, value) for cycle, reg, value in machine.bus.events
                  if reg == 0x1E and cycle < blank[0][0]]
        scene = [(cycle, value) for cycle, reg, value in machine.bus.events
                 if reg == 0x1E and blank[0][0] <= cycle < blank[1][0]
                 and cycle // 76 < first + 160]
        assert len(scene) == 40
        assert [(row, value) for row, (_, value) in enumerate(scene) if value] == (
            [] if view_y == 0xFF else [(39, 2)])
        assert before[-1][1] == (2 if view_y == 0xFF else 0)
        cleanup = [(cycle // 76 - first, value) for cycle, reg, value in machine.bus.events
                   if reg == 0x1E and cycle // 76 == first + 160]
        assert cleanup == [(160, 0)]
    print("OK: M1 recortado em ShotViewY=$FF no topo e 39 no fundo, sem vazar no HUD")


def check_closed_gate_budget():
    costs = []
    for room in (4, 5, 7, 8):
        for puzzle in (0, 6):
            for attack in (False, True):
                for joystick in (0x7F, 0x5F, 0x6F):
                    machine = Machine()
                    put(machine, "PuzzleFlags", puzzle)
                    place(machine, room, 34, 20, 0 if puzzle else 2)
                    machine.frame()
                    put(machine, "StepClock", 1)
                    if attack:
                        put(machine, "AttackTimer", 12)
                        put(machine, "ShotX", 150)
                        put(machine, "ShotY", 23)
                        put(machine, "ShotDir", 0x40)
                    machine.bus.joystick = joystick
                    machine.bus.fire = 0 if attack else 0x80
                    machine.bus.events.clear()
                    before = machine.cpu.processorCycles
                    machine.step()
                    machine.until("WaitBlank")
                    cost = machine.cpu.processorCycles - machine.bus.timer_start
                    costs.append(cost)
                    assert cost <= 43 * 64 - 128, (room, puzzle, attack, joystick, cost)
                    machine.until("Frame")
                    assert machine.cpu.processorCycles - before == 262 * 76
                    assert machine.get("GateMask") == (0 if puzzle else 2)
    print(f"OK: portas vermelha/azul fechadas/abertas e bbox3; VBLANK ate {max(costs)} ciclos")

def check_buffer_lifecycle():
    machine = Machine()
    machine.frame()  # estabilizar a fase apos Reset
    machine.bus.joystick = 0x6F
    machine.bus.fire = 0
    for frame in range(16):
        before = machine.cpu.processorCycles
        visible = machine.frame_with_visible_snapshot()
        assert machine.cpu.processorCycles - before == 262 * 76
        facing = visible[SYMBOLS["Facing"]]
        attack = visible[SYMBOLS["AttackTimer"]]
        index = (96 + facing * 16 + (8 if attack < 7 else 0)) if attack else (
            facing * 24 + visible[SYMBOLS["WalkFrame"]] * 8)
        glyph = [machine.bus[SYMBOLS["PlayerGraphics"] + index + i] for i in range(8)]
        y = visible[SYMBOLS["PlayerY"]] - visible[SYMBOLS["CameraY"]]
        for label, rows in (("SpriteTopRows", glyph[::2]),
                            ("SpriteBottomRows", glyph[1::2])):
            start = SYMBOLS[label]
            expected = [0] * 41
            expected[y:y + 4] = rows
            assert list(visible[start:start + 40]) == expected[:40], (frame, label)
            assert not any(machine.bus[start + i] for i in range(41)), (frame, label)
    print("OK: 16 quadros seguidos, buffers limpos apos tiro e sem rastro de sprites")


def check_positions():
    for room in range(9):
        machine = Machine()
        place(machine, room, 40, 28)
        machine.frame()
        events = machine.bus.events
        for regs in ((0x11, 0x21), (0x12, 0x22), (0x10, 0x20)):
            writes = [(cycle % 76, reg, value) for cycle, reg, value in events if reg in regs]
            assert len(writes) == 2 and writes[1][0] - writes[0][0] == 3
        obj = [(cycle % 76, reg, value) for cycle, reg, value in events if reg in (0x10, 0x20)]
        assert obj == [(27, 0x20, 0xB0), (30, 0x10, 0xB0)], obj
    print("OK: P0 em x32 e posicionamento de P1/M0 em todas as nove salas")

def check_shot_positions():
    cases = (
        # ShotX, ciclos HMM1/RESM1, ajuste fino
        (0, (17, 20), 0x20), (4, (17, 20), 0xE0),
        (6, (22, 25), 0x50), (40, (32, 35), 0x10),
        (158, (72, 75), 0x30),
    )
    for x, expected_cycles, expected_value in cases:
        machine = Machine()
        place(machine, 0, 40, 20)
        put(machine, "ShotX", x)
        put(machine, "ShotY", 20)
        machine.frame()
        events = [(cycle % 76, reg, value) for cycle, reg, value in machine.bus.events
                  if reg in (0x13, 0x23)]
        assert events == [
            (expected_cycles[0], 0x23, expected_value),
            (expected_cycles[1], 0x13, expected_value),
        ], (x, events)
    print("OK: M1 posicionado em x=0/4/6/40/158 com HMM1/RESM1 esperados")


def check_video():
    checked = 0
    for room in range(9):
        for camera in (0, 4, 8):
            for collected in (False, True):
                machine = Machine()
                if collected:
                    put(machine, "PickedLo", 255)
                    put(machine, "PickedHi", 1)
                    put(machine, "PuzzleFlags", 6)
                machine.room(room)
                put(machine, "PlayerX", 76)
                put(machine, "PlayerY", camera + 20)
                put(machine, "CameraY", camera)
                machine.frame()
                before = machine.cpu.processorCycles
                scene, hud = machine.frame_with_hud_snapshots()
                assert machine.cpu.processorCycles - before == 262 * 76, (room, camera, collected)
                events = machine.bus.events
                blank = [(cycle, value) for cycle, reg, value in events if reg == 1]
                sync = [(cycle, value) for cycle, reg, value in events if reg == 0]
                assert [v for _, v in blank] == [0, 2]
                assert sync[1][0] // 76 - sync[0][0] // 76 == 3
                assert blank[0][0] // 76 - sync[1][0] // 76 == 37
                assert blank[1][0] // 76 - blank[0][0] // 76 == 192
                first = blank[0][0] // 76
                lines = defaultdict(list)
                for cycle, reg, value in events:
                    if blank[0][0] <= cycle < blank[1][0] and reg in (13, 14, 15):
                        lines[cycle // 76 - first].append((cycle % 76, reg, value))
                assert all(row in lines for row in range(160))
                for row in range(160):
                    writes = lines[row]
                    assert [reg for _, reg, _ in writes] == [13, 14, 15] * 2
                    values = [v for _, _, v in writes]
                    rendered = decode(values[:3]) + decode(values[3:])
                    assert rendered == [cell == "#" for cell in maps()[room][camera + row // 4]]
                    # Janelas TIA: completar esquerda antes de seu primeiro pixel;
                    # somente sobrescrever cada registrador depois do ultimo pixel
                    # de sua metade esquerda. Um atraso apenas no PF0 nao basta.
                    cycles = [cycle for cycle, _, _ in writes]
                    assert cycles[0] <= 22 and cycles[1] < 28 and cycles[2] <= 38, (row, cycles)
                    assert 28 <= cycles[3] <= 49, (row, cycles)
                    assert 39 <= cycles[4] <= 54, (row, cycles)
                    assert 50 <= cycles[5] <= 65, (row, cycles)
                for glyph in range(5):
                    expected = [hud[SYMBOLS[f"HudLeft{i}"] + glyph] for i in range(3)] + [hud[SYMBOLS[f"HudRight{i}"] + glyph] for i in range(3)]
                    for repeat in range(4):
                        writes = lines[168 + glyph * 4 + repeat]
                        assert [cycle for cycle, _, _ in writes] == [7, 14, 21, 40, 47, 54]
                        assert [value for _, _, value in writes] == expected
                # P1 continua com dois bytes por linha logica; M0/M1 nao
                # mudam de linha quando a camera anda nem invadem o painel.
                sprite = [(cycle // 76 - first, cycle % 76, value) for cycle, reg, value in events
                          if reg == 0x1C and blank[0][0] <= cycle < blank[1][0] and cycle // 76 < first + 160]
                expected_sprite = []
                for row in range(40):
                    if row:
                        expected_sprite.append((row * 4, 9, scene[SYMBOLS["SpriteTopRows"] + row]))
                    expected_sprite.append((row * 4 + 2, 7, scene[SYMBOLS["SpriteBottomRows"] + row]))
                assert sprite == expected_sprite
                gate = [(cycle // 76 - first, cycle % 76, value) for cycle, reg, value in events
                        if reg == 0x1D and blank[0][0] <= cycle < blank[1][0] and cycle // 76 < first + 160]
                assert len(gate) == 39
                for row, (offset, cycle, value) in enumerate(gate, 1):
                    assert offset == row * 4 and cycle == 3
                    expected = 2 if room in (4, 5, 7, 8) and 20 <= camera + row < 28 else 0
                    assert value == expected & scene[SYMBOLS["GateMask"]]
                # GRP0 seguinte muda depois de x32 passar na quarta scanline.
                # O ultimo byte pode vir da folga ROM, mas so apos a sua posicao
                # fisica e e apagado antes do HUD. O valor inicial vem do VBLANK.
                object_writes = [(cycle // 76 - first, cycle % 76, value) for cycle, reg, value in events
                                 if reg == 0x1B and blank[0][0] <= cycle < blank[1][0]]
                assert len(object_writes) == 41
                initial_object = [value for cycle, reg, value in events if reg == 0x1B and cycle < blank[0][0]][-1]
                mask = scene[SYMBOLS["ObjectMask"]]
                values = [initial_object] + [value for _, _, value in object_writes[:39]]
                for row, value in enumerate(values):
                    logical = camera + row
                    expected = OBJECT_GLYPHS[OBJECT_TYPES[room]][logical - 34] if 34 <= logical < 38 else 0
                    assert value == expected & mask, (room, logical, value, mask)
                for row, (offset, cycle, _) in enumerate(object_writes[:40]):
                    assert offset == row * 4 + 3 and cycle == 58
                assert object_writes[-1] == (160, 8, 0)
                # PF0 a tempo da borda esquerda e paleta P0/M0 sincronizada.
                for row in range(40):
                    assert lines[row * 4][0][0] <= 22
                    colors = [(cycle % 76, value) for cycle, reg, value in events
                              if reg == 6 and cycle // 76 == first + row * 4]
                    logical = camera + row
                    expected_color = expected_row_color(room, logical)
                    assert colors == [(26 if row == 0 else 29, expected_color)]
                    # M0 no extremo esquerdo ja passou quando COLUP0 muda.
                    # Manter a cor-base na linha anterior garante sua primeira
                    # scanline; o flag bit0 nao interfere na cor do TIA NTSC.
                    if room in (5, 8) and 20 <= logical < 28:
                        earlier = [value for cycle, reg, value in events
                                   if reg == 6 and cycle // 76 < first + row * 4]
                        assert earlier[-1] & 0xFE == expected_color & 0xFE
                for reg in (0x1B, 0x1C, 0x1D, 0x1E):
                    cleanup = [(cycle // 76 - first, value) for cycle, register, value in events
                               if register == reg and first + 160 <= cycle // 76 < first + 192]
                    assert cleanup == [(160, 0)], (room, reg, cleanup)
                checked += 1
    print(f"OK: {checked} quadros; 160 cenario + 32 HUD, objetos P0/coleta/camera, sem sprites no painel")

def tension_tables():
    """Referencia externa ao player integrado: dados originais do laboratorio."""
    source = (ROOT.parent / "Musica" / "main.asm").read_text()
    tables = {}
    for name, length in (("TensionMelody", 64), ("TensionBass", 64),
                         ("LeadEnvelope", 15), ("BassEnvelope", 15),
                         ("NoiseEnvelope", 15)):
        body = source.split(f"\n{name}\n", 1)[1]
        values = []
        for line in body.splitlines():
            match = re.match(r"\s*byte\s+([^;]+)", line)
            if not match:
                break
            for token in match[1].strip().split(","):
                token = token.strip()
                values.append(int(token[1:], 16) if token.startswith("$") else int(token))
        assert len(values) == length, (name, len(values))
        tables[name] = values
    return tables


def expected_audio(tables, step, clock, previous, sfx=0):
    """Referencia por registradores: musica a meia amplitude e efeito no canal 1."""
    state = previous.copy()
    melody = tables["TensionMelody"][step]
    bass = tables["TensionBass"][step]
    state[0x19] = 0 if melody == 0xFF else tables["LeadEnvelope"][clock] // 2
    if melody != 0xFF:
        state.update({0x15: 4, 0x17: melody})
    if sfx:
        if sfx & 0x80:
            age = 12 - (sfx & 0x7F)
            frequency = 8 if age < 6 else 5
            volume = (5, 5, 3, 2, 1, 0)[age % 6]
            state.update({0x16: 4, 0x18: frequency, 0x1A: volume})
        else:
            age = 6 - sfx
            state.update({0x16: 8, 0x18: (2, 4, 6, 9, 12, 15)[age],
                          0x1A: (6, 4, 3, 2, 1, 0)[age]})
    elif bass == 0xFF:
        state[0x1A] = 0
    elif bass == 0x80:
        state.update({0x16: 8, 0x18: 10, 0x1A: tables["NoiseEnvelope"][clock] // 2})
    else:
        state.update({0x16: 6, 0x18: bass, 0x1A: tables["BassEnvelope"][clock] // 2})
    return state


def assert_music_frame(machine, before, expected, reset=False):
    events = machine.bus.events
    assert machine.cpu.processorCycles - before == 262 * 76
    sync = [(cycle, value) for cycle, reg, value in events if reg == 0]
    blank = [(cycle, value) for cycle, reg, value in events if reg == 1]
    assert [value for _, value in sync] == [2, 0]
    assert [value for _, value in blank] == [0, 2]
    assert sync[1][0] // 76 - sync[0][0] // 76 == 3
    assert blank[0][0] // 76 - sync[1][0] // 76 == 37
    assert blank[1][0] // 76 - blank[0][0] // 76 == 192
    writes = [(cycle, reg, value) for cycle, reg, value in events
              if reg in AUDIO_REGISTERS]
    early = [(reg, value) for cycle, reg, value in writes if cycle < blank[1][0]]
    assert early == ([(0x19, 0), (0x1A, 0)] if reset else []), early
    playback = [(reg, value) for cycle, reg, value in writes if cycle >= blank[1][0]]
    for volume in (0x19, 0x1A):
        assert [value for reg, value in playback if reg == volume] == [expected[volume]]
    assert all(value == expected[reg] for reg, value in playback), playback
    assert machine.min_sp >= 0xF3, hex(machine.min_sp)
    assert not any(machine.bus.ram[0x9A:0xEC]), "Audio deve manter buffers limpos"


def check_music():
    tables = tension_tables()
    machine = Machine()
    for name, expected in tables.items():
        assert [machine.bus[SYMBOLS[name] + i] for i in range(len(expected))] == expected
    assert machine.get("MusicStep") == machine.get("MusicClock") == 0
    assert machine.get("SfxState") == 0
    # Os 82 bytes de desenho terminam em EB; audio ocupa EC/ED/EE.
    # Limpar o desenho nao pode silenciar ou reiniciar a musica.
    for address in range(0x9A, 0xEC):
        machine.bus.ram[address] = 0xA5
    put(machine, "MusicStep", 63)
    put(machine, "MusicClock", 14)
    put(machine, "SfxState", 0x8C)
    machine.call("ClearSpriteRows")
    assert not any(machine.bus.ram[0x9A:0xEC])
    assert (machine.get("MusicStep"), machine.get("MusicClock")) == (63, 14)
    assert machine.get("SfxState") == 0x8C
    # Uma chamada do player so pode alterar seus tres bytes, alem da pilha.
    game_ram = bytes(machine.bus.ram[0x80:0xEC])
    machine.call("UpdateMusic")
    assert bytes(machine.bus.ram[0x80:0xEC]) == game_ram
    assert (machine.get("MusicStep"), machine.get("MusicClock")) == (0, 0)
    assert machine.get("SfxState") == 0x8B

    machine = Machine()
    machine.frame()  # estabiliza a fase real Frame -> Frame apos Reset
    state = {reg: 0 for reg in AUDIO_REGISTERS}
    state = expected_audio(tables, 0, 0, state)
    traces = []
    for frame in range(2 * 64 * 15):
        step, clock = divmod((frame + 1) % 960, 15)
        assert (machine.get("MusicStep"), machine.get("MusicClock")) == (step, clock)
        expected = expected_audio(tables, step, clock, state)
        before = machine.cpu.processorCycles
        machine.frame()
        assert_music_frame(machine, before, expected)
        for _, reg, value in machine.bus.events:
            if reg in AUDIO_REGISTERS:
                state[reg] = value
        assert state == expected, (frame, step, clock, state, expected)
        assert (machine.get("MusicStep"), machine.get("MusicClock")) == divmod(
            (frame + 2) % 960, 15)
        traces.append(tuple(state[reg] for reg in AUDIO_REGISTERS))
    assert traces[:960] == traces[960:]
    print("OK: Tensao a meio volume, dois loops de 960 quadros e audio no overscan; 262/37/192")


def check_music_controls():
    tables = tension_tables()
    machine = Machine()
    put(machine, "MusicStep", 23)
    put(machine, "MusicClock", 7)
    put(machine, "SfxState", 0x88)
    machine.room(1)
    assert (machine.get("MusicStep"), machine.get("MusicClock")) == (23, 7)
    assert machine.get("SfxState") == 0x88
    machine.bus.switches = 0xFD
    machine.call("UpdateGame")
    assert machine.get("Room") == 2
    assert (machine.get("MusicStep"), machine.get("MusicClock")) == (23, 7)
    assert machine.get("SfxState") == 0x88
    put(machine, "SfxState", 0)
    machine.bus.switches = 0xFF
    machine.call("UpdateGame")

    # Todas as passagens com disparo simultaneo: tom, pausa e percussao,
    # incluindo fim de envelope e virada do passo, sem reinicio musical.
    portals = ((0, 152, 22, 0x6F, 1, 0, 21),
               (1, 0, 22, 0xAF, 0, 152, 21),
               (1, 72, 0, 0x6F, 4, 74, 44),
               (4, 76, 44, 0x9F, 1, 74, 0))
    for room, x, y, joystick, target, new_x, new_y in portals:
        for step, clock in ((0, 0), (1, 13), (3, 14)):
            place(machine, room, x, y)
            machine.bus.fire = 0x80
            machine.frame()
            put(machine, "MusicStep", step)
            put(machine, "MusicClock", clock)
            put(machine, "StepClock", 1)
            machine.bus.joystick = joystick
            machine.bus.fire = 0
            put(machine, "SfxState", 0)
            expected = expected_audio(tables, step, clock, {}, sfx=6)
            before = machine.cpu.processorCycles
            machine.frame()
            assert_music_frame(machine, before, expected)
            assert (machine.get("Room"), *player(machine)) == (target, new_x, new_y)
            assert machine.get("AttackTimer") == 12
            assert machine.get("SfxState") == 5
            assert (machine.get("MusicStep"), machine.get("MusicClock")) == divmod(
                step * 15 + clock + 1, 15)

    machine.bus.fire = 0x80
    machine.bus.switches = 0xFC
    put(machine, "SfxState", 0x8C)
    before = machine.cpu.processorCycles
    machine.frame()
    assert_music_frame(machine, before, expected_audio(tables, 0, 0, {}), reset=True)
    assert (machine.get("MusicStep"), machine.get("MusicClock")) == (0, 1)
    assert (machine.get("Room"), *player(machine)) == (1, 76, 36)
    assert machine.get("GateMask") == 0 and machine.get("AttackTimer") == 0
    assert machine.get("SfxState") == 0
    print("OK: musica/efeito preservados em LoadRoom/Select, 12 portais+tiro; Reset cancela efeito")


def check_sound_effects():
    tables = tension_tables()
    machine = Machine()
    # API publica apenas agenda: nao toca registradores nem avanca a musica.
    for initial in (0, 1, 3, 6, 0x81, 0x86, 0x8C):
        put(machine, "SfxState", initial)
        preserved = bytes(machine.bus.ram[0x80:0xEE])
        writes = len(machine.bus.events)
        machine.call("PlayShotSound")
        assert machine.get("SfxState") == (initial if initial & 0x80 else 6)
        assert bytes(machine.bus.ram[0x80:0xEE]) == preserved
        assert len(machine.bus.events) == writes
        machine.call("PlayActionSound")
        assert machine.get("SfxState") == 0x8C
        assert bytes(machine.bus.ram[0x80:0xEE]) == preserved
        assert len(machine.bus.events) == writes

    # Quadros inteiros: os efeitos atravessam notas, pausas, percussao e a
    # volta do loop. O ponto musical avanca inclusive durante a sobreposicao.
    for initial, duration in ((6, 6), (0x8C, 12)):
        for start in ((0, 13), (1, 0), (3, 13), (63, 13)):
            machine = Machine()
            machine.frame()
            state = {reg: value for _, reg, value in machine.bus.events
                     if reg in AUDIO_REGISTERS}
            put(machine, "MusicStep", start[0])
            put(machine, "MusicClock", start[1])
            put(machine, "SfxState", initial)
            for age in range(duration + 2):
                step, clock = divmod((start[0] * 15 + start[1] + age) % 960, 15)
                active = (initial - age) if age < duration else 0
                assert machine.get("SfxState") == active
                assert (machine.get("MusicStep"), machine.get("MusicClock")) == (step, clock)
                expected = expected_audio(tables, step, clock, state, sfx=active)
                before = machine.cpu.processorCycles
                machine.frame()
                assert_music_frame(machine, before, expected)
                assert machine.get("SfxState") == (active - 1 if age < duration - 1 else 0)
                state = expected
                assert (machine.get("MusicStep"), machine.get("MusicClock")) == divmod(
                    (start[0] * 15 + start[1] + age + 1) % 960, 15)

    # Prioridade tambem durante um disparo real: a bala nasce, mas a acao
    # continua no seu segundo quadro, em vez de ser substituida pelo tiro.
    machine = Machine()
    place(machine, 0, 80, 20, facing=3)
    machine.frame()
    put(machine, "Aim", 0x80)
    put(machine, "SfxState", 0x87)
    state = {reg: value for _, reg, value in machine.bus.events
             if reg in AUDIO_REGISTERS}
    step, clock = machine.get("MusicStep"), machine.get("MusicClock")
    expected = expected_audio(tables, step, clock, state, sfx=0x87)
    machine.bus.fire = 0
    before = machine.cpu.processorCycles
    machine.frame()
    assert_music_frame(machine, before, expected)
    assert shot(machine) == (88, 21, 0x80, 12)
    assert machine.get("SfxState") == 0x86

    # Fire segurado: tiro bloqueado pela borda ainda soa a cada novo ataque,
    # exatamente a cada 12 quadros; os quadros intermediarios nao reiniciam o som.
    machine = Machine()
    place(machine, 0, 40, 0, facing=1)
    machine.frame()
    put(machine, "Aim", 0x10)
    machine.bus.fire = 0
    state = {reg: value for _, reg, value in machine.bus.events
             if reg in AUDIO_REGISTERS}
    for frame in range(30):
        phase = frame % 12
        active = 6 - phase if phase < 6 else 0
        step, clock = machine.get("MusicStep"), machine.get("MusicClock")
        expected = expected_audio(tables, step, clock, state, sfx=active)
        before = machine.cpu.processorCycles
        machine.frame()
        assert_music_frame(machine, before, expected)
        assert machine.get("ShotY") == 128
        assert machine.get("AttackTimer") == 12 - phase
        assert machine.get("SfxState") == max(0, 5 - phase)
        state = expected
    print("OK: efeitos 6/12 quadros, prioridade/reinicio, retomada imediata e autofire bloqueado")


if __name__ == "__main__":
    check_maps()
    check_collision()
    check_sprite_rows()
    check_movement()
    check_diagonals()
    check_transitions()
    check_switch_and_console()
    check_world_frames()
    check_mansion_route()
    check_camera()
    check_hud_data()
    check_shots()
    check_shot_frames()
    check_shot_clipping()
    check_closed_gate_budget()
    check_buffer_lifecycle()
    check_positions()
    check_shot_positions()
    check_video()
    check_music()
    check_music_controls()
    check_sound_effects()
