"""Verifica a ROM com py65: controles, limites, raster e ciclos de CPU.

Nao simula o circuito de video do TIA; confere suas escritas e prazos.
Requer py65 no ambiente Python (dependencia opcional de desenvolvimento).
"""
from pathlib import Path
import re

from py65.devices.mpu6502 import MPU

ROOT = Path(__file__).resolve().parent
ROM = (ROOT / 'build/main.bin').read_bytes()
SYMBOLS = {}
for line in (ROOT / 'build/main.sym').read_text().splitlines():
    match = re.match(r'^(\w+)\s+([0-9a-fA-F]{4})\s', line)
    if match:
        SYMBOLS[match[1]] = int(match[2], 16)


class Bus:
    def __init__(self):
        self.ram = bytearray(128)
        self.joystick = 0xFF
        self.fire = 0x80
        self.pending = []
        self.events = []
        self.tia = {}

    def __getitem__(self, address):
        address &= 0x1FFF
        if address & 0x1000:
            return ROM[address & 0xFFF]
        if address == 0x280:
            return self.joystick
        if address == 0x0C:
            return self.fire
        if address & 0x80 and not address & 0x200:
            return self.ram[address & 0x7F]
        return 0

    def __setitem__(self, address, value):
        address &= 0x1FFF
        assert not address & 0x1000, 'Escrita na ROM'
        if address & 0x80 and not address & 0x200:
            self.ram[address & 0x7F] = value
        elif not address & 0x80:
            self.pending.append((address & 0x3F, value))
            self.tia[address & 0x3F] = value


class Machine:
    def __init__(self):
        self.bus = Bus()
        self.cpu = MPU(memory=self.bus, pc=None)
        self.until('Frame')

    def step(self):
        self.cpu.step()
        cycle = self.cpu.processorCycles
        for register, value in self.bus.pending:
            self.bus.events.append((cycle, register, value))
            if register == 2:
                self.cpu.processorCycles = ((cycle + 75) // 76) * 76
        self.bus.pending.clear()

    def until(self, label):
        for _ in range(20000):
            if self.cpu.pc == SYMBOLS[label]:
                return
            self.step()
        raise AssertionError(f'Execucao nao chegou a {label}')

    def get(self, label):
        return self.bus[SYMBOLS[label]]

    def set(self, label, value):
        self.bus[SYMBOLS[label]] = value

    def call(self, label):
        self.cpu.stPushWord(SYMBOLS['Frame'] - 1)
        self.cpu.pc = SYMBOLS[label]
        self.until('Frame')

    def frame(self):
        self.bus.events.clear()
        before = self.cpu.processorCycles
        self.step()
        self.until('Frame')
        return self.cpu.processorCycles - before


def axis_expected(value, delta, low, high):
    value += delta
    if value < low * 256:
        return low * 256
    if value >= high * 256:
        return high * 256
    return value


def check_controls():
    machine = Machine()
    assert [machine.get(k) for k in ('XPos', 'YPos', 'Heading')] == [76, 36, 0]
    # Os eixos esperados sao derivados das teclas, sem usar a tabela da ROM.
    headings = {(0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3,
                (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7}
    cases = 0
    for mask in range(16):
        for heading in range(8):
            for x, y in ((4, 4), (148, 68), (4, 68), (148, 4), (76, 36)):
                for frac in (0, 127, 255):
                    machine.bus.joystick = (mask << 4) | 15
                    for key, value in dict(XPos=x, YPos=y, XFrac=frac, YFrac=frac,
                                           Heading=heading).items():
                        machine.set(key, value)
                    dx = int(not mask & 8) - int(not mask & 4)
                    dy = int(not mask & 2) - int(not mask & 1)
                    expected_heading = headings.get((dx, dy), heading)
                    speed = 90 if dx and dy else 127
                    machine.call('ReadJoystick')
                    actual = (machine.get('XPos') * 256 + machine.get('XFrac'),
                              machine.get('YPos') * 256 + machine.get('YFrac'),
                              machine.get('Heading'))
                    expected = (axis_expected(x * 256 + frac, dx * speed, 4, 148),
                                axis_expected(y * 256 + frac, dy * speed, 4, 68),
                                expected_heading)
                    assert actual == expected, (mask, heading, x, y, frac, actual, expected)
                    cases += 1
    # Direcao sustentada conserva rumo/velocidade; soltar para imediatamente.
    # A entrada oposta retorna ao ponto inicial e vira a seta no mesmo quadro.
    for (dx, dy), heading in headings.items():
        for key, value in dict(XPos=76, YPos=36, XFrac=0, YFrac=0, Heading=0).items():
            machine.set(key, value)
        pressed = ((1 if dy < 0 else 2 if dy > 0 else 0) |
                   (4 if dx < 0 else 8 if dx > 0 else 0))
        machine.bus.joystick = 0xFF ^ (pressed << 4)
        speed = 90 if dx and dy else 127
        for frame in range(1, 33):
            machine.call('ReadJoystick')
            assert machine.get('Heading') == heading
            assert machine.get('XPos') * 256 + machine.get('XFrac') == 76 * 256 + frame * dx * speed
            assert machine.get('YPos') * 256 + machine.get('YFrac') == 36 * 256 + frame * dy * speed
        machine.bus.joystick = 0xFF
        stopped = [machine.get(k) for k in ('XPos', 'YPos', 'XFrac', 'YFrac', 'Heading')]
        for _ in range(10):
            machine.call('ReadJoystick')
            assert [machine.get(k) for k in ('XPos', 'YPos', 'XFrac', 'YFrac', 'Heading')] == stopped
        opposite = ((2 if dy < 0 else 1 if dy > 0 else 0) |
                    (8 if dx < 0 else 4 if dx > 0 else 0))
        machine.bus.joystick = 0xFF ^ (opposite << 4)
        for _ in range(32):
            machine.call('ReadJoystick')
            assert machine.get('Heading') == (heading + 4) % 8
        assert [machine.get(k) for k in ('XPos', 'YPos', 'XFrac', 'YFrac')] == [76, 36, 0, 0]
    # Mudancas entre quaisquer duas direcoes sao imediatas, sem giro gradual.
    for first in range(1, 9):
        for second in range(1, 9):
            for index in (first - 1, second - 1):
                dx, dy = next(vector for vector, heading in headings.items() if heading == index)
                pressed = ((1 if dy < 0 else 2 if dy > 0 else 0) |
                           (4 if dx < 0 else 8 if dx > 0 else 0))
                machine.bus.joystick = 0xFF ^ (pressed << 4)
                machine.call('ReadJoystick')
                assert machine.get('Heading') == index
    print(f'OK: {cases} casos de controles/limites; 8 direcoes, parada e mudancas imediatas')


SHOT_VECTORS = ((0, -512), (362, -362), (512, 0), (362, 362),
                (0, 512), (-362, 362), (-512, 0), (-362, -362))
SHOT_ORIGINS = ((3, -2), (7, -1), (8, 3), (7, 7),
                (3, 8), (-1, 7), (-2, 3), (-1, -1))


def set_state(machine, **values):
    for key, value in values.items():
        machine.set(key, value)


def shot_state(machine):
    return tuple(machine.get(key) for key in
                 ('ShotActive', 'ShotX', 'ShotXFrac', 'ShotY', 'ShotYFrac', 'ShotHeading'))


def valid_shot(x, y):
    return 4 <= x <= 154 and 4 <= y <= 75


def update_shot(machine):
    machine.bus.events.clear()
    machine.call('UpdateShot')
    sync = [cycle for cycle, register, _ in machine.bus.events if register == 2]
    assert len(sync) == 6, sync
    assert all(b // 76 - a // 76 == 1 for a, b in zip(sync, sync[1:])), sync
    assert machine.get('ShotRowBefore') == (machine.get('ShotY') - 1) & 255


def check_shots():
    machine = Machine()
    assert machine.get('ShotActive') == 0
    cases = 0
    # Origem independente das tabelas da ROM; nascer nao consome o primeiro passo.
    for heading, (offset_x, offset_y) in enumerate(SHOT_ORIGINS):
        for x, y in ((4, 4), (148, 68), (4, 68), (148, 4), (76, 36)):
            set_state(machine, XPos=x, YPos=y, XFrac=255, YFrac=127,
                      Heading=heading, ShotActive=0, ShotXFrac=93, ShotYFrac=181)
            machine.bus.fire = 0x80
            update_shot(machine)
            assert machine.get('ShotActive') == 0
            machine.bus.fire = 0
            update_shot(machine)
            sx, sy = x + offset_x, y + offset_y
            expected = (0xC0 if valid_shot(sx, sy) else 0, sx, 0, sy, 0, heading)
            assert shot_state(machine) == expected, (heading, x, y, shot_state(machine), expected)
            assert machine.get('NewShot') == 1
            assert [machine.get(k) for k in ('XPos', 'YPos', 'XFrac', 'YFrac', 'Heading')] == [x, y, 255, 127, heading]
            cases += 1
    # Fracoes distintas, oito rumos e cruzamentos de cada parede. O botao
    # pressionado nao substitui um tiro vivo nem altera sua orientacao.
    for heading, (dx, dy) in enumerate(SHOT_VECTORS):
        for x in (2, 3, 4, 5, 6, 76, 152, 153, 154, 155, 156):
            for y in (2, 3, 4, 5, 6, 36, 73, 74, 75, 76, 77):
                for frac in (0, 127, 255):
                    yfrac = (frac + 91) & 255
                    set_state(machine, ShotActive=0xC0, ShotX=x, ShotY=y,
                              ShotXFrac=frac, ShotYFrac=yfrac, ShotHeading=heading,
                              Heading=(heading + 3) % 8)
                    machine.bus.fire = 0 if frac == 127 else 0x80
                    update_shot(machine)
                    sx = (x * 256 + frac + dx) & 0xFFFF
                    sy = (y * 256 + yfrac + dy) & 0xFFFF
                    expected = (0xC0 if valid_shot(sx >> 8, sy >> 8) else 0,
                                sx >> 8, sx & 255, sy >> 8, sy & 255, heading)
                    assert shot_state(machine) == expected, (heading, x, y, frac, shot_state(machine), expected)
                    assert machine.get('NewShot') == 0
                    cases += 1
    # Segurar so repete no quadro seguinte ao desaparecimento. Soltar nao
    # interrompe o tiro; quando inativo, nao cria outro. O jogador segue livre.
    for heading, (dx, dy) in enumerate(SHOT_VECTORS):
        set_state(machine, XPos=76, YPos=36, XFrac=0, YFrac=0,
                  Heading=heading, ShotActive=0)
        machine.bus.fire = 0
        update_shot(machine)
        sx, sy = machine.get('ShotX') * 256, machine.get('ShotY') * 256
        for frame in range(1, 100):
            machine.bus.joystick = (0x7F, 0xEF, 0xBF, 0xDF)[frame % 4]
            machine.call('ReadJoystick')
            update_shot(machine)
            sx = (sx + dx) & 0xFFFF
            sy = (sy + dy) & 0xFFFF
            expected = (0xC0 if valid_shot(sx >> 8, sy >> 8) else 0,
                        sx >> 8, sx & 255, sy >> 8, sy & 255, heading)
            assert shot_state(machine) == expected, (heading, frame, shot_state(machine), expected)
            if not machine.get('ShotActive'):
                assert machine.get('NewShot') == 0
                break
        else:
            raise AssertionError(f'Tiro {heading} nao chegou a parede')
        new_heading = machine.get('Heading')
        update_shot(machine)
        ox, oy = SHOT_ORIGINS[new_heading]
        assert shot_state(machine) == (0xC0, machine.get('XPos') + ox, 0,
                                       machine.get('YPos') + oy, 0, new_heading)
        machine.bus.fire = 0x80
        for _ in range(100):
            update_shot(machine)
        assert machine.get('ShotActive') == 0
        stopped = shot_state(machine)
        for _ in range(3):
            update_shot(machine)
            assert shot_state(machine) == stopped
        cases += 1
    print(f'OK: {cases} casos de tiros; 8 rumos, origem, velocidade, paredes, repeticao e independencia')


def room_mask(room):
    return ((1 if room >= 3 else 0) | (2 if room < 6 else 0) |
            (4 if room % 3 else 0) | (8 if room % 3 < 2 else 0))


def room_expected(room, x, y, dx, dy):
    mask = room_mask(room)
    if dx < 0 and x == 4 and 28 <= y <= 44 and mask & 4:
        return room - 1, 148, y
    if dx > 0 and x == 148 and 28 <= y <= 44 and mask & 8:
        return room + 1, 4, y
    if dy < 0 and y == 4 and 64 <= x <= 88 and mask & 1:
        return room - 3, x, 68
    if dy > 0 and y == 68 and 64 <= x <= 88 and mask & 2:
        return room + 3, x, 4
    return room, x, y


def update_room(machine):
    machine.bus.events.clear()
    machine.call('UpdateRoom')
    sync = [cycle for cycle, register, _ in machine.bus.events if register == 2]
    assert len(sync) == 8, sync
    assert all(b // 76 - a // 76 == 1 for a, b in zip(sync, sync[1:])), sync


def check_rooms():
    machine = Machine()
    assert machine.get('CurrentRoom') == 4
    cases, connections = 0, set()
    # Cada porta e testada antes/depois dos limites do corpo inteiro. As
    # diagonais podem atravessar o limite no eixo perpendicular neste quadro.
    edges = ((4, 'W', (4, 5, 6, 8, 0, 12)),
             (148, 'E', (8, 9, 10, 4, 0, 12)),
             (4, 'N', (1, 5, 9, 2, 0, 3)),
             (68, 'S', (2, 6, 10, 1, 0, 3)))
    for room in range(9):
        for edge, direction, inputs in edges:
            horizontal = direction in 'WE'
            for across in ((27, 28, 44, 45) if horizontal else (63, 64, 88, 89)):
                x, y = (edge, across) if horizontal else (across, edge)
                for pressed in inputs:
                    for frac in (0, 255):
                        set_state(machine, CurrentRoom=room, XPos=x, YPos=y,
                                  XFrac=frac, YFrac=frac, Heading=0,
                                  ShotActive=0xC0, ShotX=76, ShotY=36,
                                  ShotXFrac=0, ShotYFrac=0)
                        machine.bus.joystick = 0xFF ^ (pressed << 4)
                        dx = int(bool(pressed & 8)) - int(bool(pressed & 4))
                        dy = int(bool(pressed & 2)) - int(bool(pressed & 1))
                        speed = 90 if dx and dy else 127
                        fixed_x = axis_expected(x * 256 + frac, dx * speed, 4, 148)
                        fixed_y = axis_expected(y * 256 + frac, dy * speed, 4, 68)
                        expected_room, px, py = room_expected(room, fixed_x >> 8, fixed_y >> 8, dx, dy)
                        changed = expected_room != room
                        machine.call('ReadJoystick')
                        assert machine.get('RoomChanged') == 0
                        update_room(machine)
                        expected = (expected_room, px, py, 0 if changed else fixed_x & 255,
                                    0 if changed else fixed_y & 255, int(changed))
                        actual = tuple(machine.get(k) for k in
                                       ('CurrentRoom', 'XPos', 'YPos', 'XFrac', 'YFrac', 'RoomChanged'))
                        assert actual == expected, (room, direction, across, pressed, frac, actual, expected)
                        assert machine.get('ShotActive') == (0 if changed else 0xC0)
                        assert machine.get('RoomMask') == room_mask(expected_room)
                        if changed:
                            connections.add((room, expected_room))
                            machine.bus.fire = 0
                            update_shot(machine)
                            assert machine.get('ShotActive') == 0, 'Tiro recriado no quadro da transicao'
                            assert [machine.get(k) for k in ('ShotX', 'ShotY')] == [76, 36]
                        cases += 1
    expected_connections = {(room, adjacent) for room in range(9)
                            for adjacent in (room - 3, room + 3, room - 1, room + 1)
                            if 0 <= adjacent < 9 and
                            abs(room // 3 - adjacent // 3) + abs(room % 3 - adjacent % 3) == 1}
    assert connections == expected_connections and len(connections) == 24
    # Ida e volta por cada conexao, com um novo tiro permitido no quadro
    # seguinte a troca. O eixo perpendicular permanece no meio da porta.
    for room, adjacent in sorted(connections):
        delta = adjacent - room
        pressed, opposite, x, y = { -1: (4, 8, 4, 36), 1: (8, 4, 148, 36),
                                   -3: (1, 2, 76, 4), 3: (2, 1, 76, 68)}[delta]
        set_state(machine, CurrentRoom=room, XPos=x, YPos=y, XFrac=0, YFrac=0, ShotActive=0xC0)
        machine.bus.joystick = 0xFF ^ (pressed << 4)
        machine.call('ReadJoystick')
        update_room(machine)
        assert machine.get('CurrentRoom') == adjacent
        machine.bus.joystick = 0xFF
        machine.call('ReadJoystick')
        update_room(machine)
        machine.bus.fire = 0
        update_shot(machine)
        assert machine.get('ShotActive') == 0xC0, 'Novo tiro bloqueado depois da transicao'
        machine.bus.joystick = 0xFF ^ (opposite << 4)
        machine.call('ReadJoystick')
        update_room(machine)
        assert machine.get('CurrentRoom') == room
        assert [machine.get(k) for k in ('XPos', 'YPos', 'XFrac', 'YFrac', 'ShotActive')] == [x, y, 0, 0, 0]
        cases += 1
    print(f'OK: {cases} casos de salas; 9 salas, 24 conexoes, retornos, portas, diagonais e descarte de tiros')


def check_hud(events, start, room):
    registers = (0x04, 0x05, 0x09, 0x0D, 0x0E, 0x0F,
                 0x10, 0x11, 0x1B, 0x1C, 0x20, 0x21, 0x2A)
    rows = [[] for _ in range(32)]
    for cycle, register, value in events:
        row = cycle // 76 - start - 160
        if 0 <= row < 32 and register in registers:
            rows[row].append((cycle % 76, register, value))
    assert [(r, v) for _, r, v in rows[0]] == [
        (0x1B, 0), (0x1C, 0), (0x0D, 0), (0x0E, 0), (0x0F, 0),
        (0x09, 6), (0x04, 3), (0x05, 1)], rows[0]
    assert all(c <= 22 for c, r, _ in rows[0] if r in (0x1B, 0x1C, 0x0D, 0x0E, 0x0F))
    assert [(c, r) for c, r, _ in rows[1]] == [(41, 0x10), (44, 0x11)], rows[1]
    assert all(not row for row in rows[2:9]), 'Margem superior do HUD alterada'
    assert [(r, v) for _, r, v in rows[23]] == [
        (0x1B, 0), (0x1C, 0), (0x04, 0), (0x05, 0)], rows[23]
    assert all(c <= 22 for c, _, _ in rows[23]), rows[23]
    assert all(not row for row in rows[24:]), 'Margem inferior do HUD alterada'
    # Referencia visual independente dos bytes/fontes da ROM. Os espacos
    # entre caracteres sao preservados ao reconstruir as cinco copias.
    glyphs = {
        'A': ('.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'),
        'T': ('#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'),
        'R': ('####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'),
        'I': ('#####', '..#..', '..#..', '..#..', '..#..', '..#..', '#####'),
    }
    digits = (
        ('.#.', '##.', '.#.', '.#.', '.#.', '.#.', '###'),
        ('###', '..#', '..#', '###', '#..', '#..', '###'),
        ('###', '..#', '..#', '###', '..#', '..#', '###'),
        ('#.#', '#.#', '#.#', '###', '..#', '..#', '..#'),
        ('###', '#..', '#..', '###', '..#', '..#', '###'),
        ('###', '#..', '#..', '###', '#.#', '#.#', '###'),
        ('###', '..#', '..#', '.#.', '.#.', '.#.', '.#.'),
        ('###', '#.#', '#.#', '###', '#.#', '#.#', '###'),
        ('###', '#.#', '#.#', '###', '..#', '..#', '###'),
    )
    # Calibracao NTSC usada tambem pelo posicionamento da cena: strobe
    # no ciclo C coloca a copia em 3*C-63. O TIA real exige QA no emulador.
    p0 = rows[1][0][0] * 3 - 63
    p1 = rows[1][1][0] * 3 - 63
    # A/I reservam o primeiro bit vazio; T/R comecam no bit mais alto.
    positions = (p0 + 1, p1, p0 + 17, p1 + 16, p0 + 33)
    assert positions == (61, 69, 77, 85, 93)
    for row, writes in enumerate(rows[9:23]):
        assert [(c, r) for c, r, _ in writes] == [
            (8, 0x0E), (15, 0x1B), (22, 0x1C),
            (50, 0x1C), (53, 0x1B), (58, 0x0E)], (row, writes)
        digit, a, t, r, i, cleared_digit = [value for _, _, value in writes]
        assert digit & 0x1F == 0 and cleared_digit == 0
        digit_pixels = ''.join('#' if digit & (0x80 >> x) else '.' for x in range(3))
        assert digit_pixels == digits[room][row // 2], (room, row, digit_pixels)
        actual, expected = ['.'] * 37, ['.'] * 37
        for x, letter, pixels in zip(positions, 'ATARI', (a, t, a, r, i)):
            padding = int(letter in 'AI')
            outside_glyph = 0x83 if padding else 7
            assert pixels & outside_glyph == 0, (letter, row, pixels)
            for column in range(5):
                actual[x - 61 + column] = '#' if pixels & (0x80 >> (column + padding)) else '.'
                expected[x - 61 + column] = glyphs[letter][row // 2][column]
        assert actual == expected, (row, ''.join(actual), ''.join(expected))


def check_video():
    machine = Machine()
    assert [machine.bus.tia[r] for r in (0x06, 0x07)] == [0x0E, 0x0E]
    # Reset chega a Frame na fase 0; quadros seguintes chegam na fase 7.
    # A diferenca de fase nao acrescenta linha ao primeiro quadro.
    initial_line = machine.cpu.processorCycles // 76
    machine.frame()
    assert machine.cpu.processorCycles // 76 - initial_line == 262
    sync_lines = [c // 76 for c, r, _ in machine.bus.events if r == 0]
    blank_lines = [c // 76 for c, r, _ in machine.bus.events if r == 1]
    assert sync_lines[1] - sync_lines[0] == 3
    assert blank_lines[0] - sync_lines[1] == 37
    assert blank_lines[1] - blank_lines[0] == 192
    check_hud(machine.bus.events, blank_lines[0], 4)
    frames = 0
    max_wsync = 0
    scenarios = [(mask, heading, x, y, 0, 0x80, 0, 0, 0)
                 for mask in range(16) for heading in range(8)
                 for x, y in ((4, 4), (148, 68), (76, 36))]
    # Inclui posicoes que estouram HMP1 para a linha seguinte, tiro nas
    # primeiras/ultimas faixas e todos os caminhos de entrada e movimento.
    scenarios += [(mask, heading, x, y, active, fire, sx, sy, heading)
                  for mask in range(16) for heading in range(8)
                  for x, y, sx, sy in ((4, 4, 4, 4), (148, 68, 149, 75),
                                      (76, 36, 150, 36), (148, 68, 154, 75),
                                      (4, 4, 156, 4))
                  for active, fire in ((0, 0x80), (0xC0, 0x80), (0, 0))]
    scenarios += [(15, 0, 76, 36, active, 0x80, sx, sy, 0)
                  for sx in range(4, 157) for sy in (4, 75)
                  for active in (0, 0xC0)]
    scenarios = [(4, scenario) for scenario in scenarios]
    scenarios += [(room, (15, 0, 76, 36, 0, 0x80, 0, 0, 0)) for room in range(9)]
    for room in range(9):
        for bit, pressed, heading, x, y in ((4, 4, 6, 4, 36), (8, 8, 2, 148, 36),
                                           (1, 1, 0, 76, 4), (2, 2, 4, 76, 68)):
            if room_mask(room) & bit:
                scenarios.append((room, (15 ^ pressed, heading, x, y, 0xC0, 0, 76, 36, heading)))
    # Continua de verdade na borda externa sul do mapa: tiro chega a Y=75,
    # jogador para em Y=68 e tiros novos em Y=76 ja nascem bloqueados.
    scenarios += [(7, (13, 4, 76, 67, 0xC0, 0, 76, 73, 4))] + [None] * 8
    for scenario in scenarios:
        if scenario is not None:
            room, scenario = scenario
            mask, heading, x, y, active, fire, sx, sy, shot_heading = scenario
            machine.bus.joystick = (mask << 4) | 15
            machine.bus.fire = fire
            set_state(machine, CurrentRoom=room, XPos=x, YPos=y, XFrac=0, YFrac=0, Heading=heading,
                      ShotActive=active, ShotX=sx, ShotY=sy, ShotXFrac=0,
                      ShotYFrac=0, ShotHeading=shot_heading)
        before_room = machine.get('CurrentRoom')
        pressed = (machine.bus.joystick >> 4) ^ 15
        dx = int(bool(pressed & 8)) - int(bool(pressed & 4))
        dy = int(bool(pressed & 2)) - int(bool(pressed & 1))
        speed = 90 if dx and dy else 127
        next_x = axis_expected(machine.get('XPos') * 256 + machine.get('XFrac'), dx * speed, 4, 148) >> 8
        next_y = axis_expected(machine.get('YPos') * 256 + machine.get('YFrac'), dy * speed, 4, 68) >> 8
        next_room, _, _ = room_expected(before_room, next_x, next_y, dx, dy)
        elapsed = machine.frame()
        assert elapsed == 262 * 76, (mask, heading, x, y, elapsed / 76)
        assert machine.get('CurrentRoom') == next_room
        assert machine.get('RoomChanged') == int(next_room != before_room)
        if next_room != before_room:
            assert machine.get('ShotActive') == 0
        assert 4 <= machine.get('XPos') <= 148 and 4 <= machine.get('YPos') <= 68
        if machine.get('ShotActive'):
            assert valid_shot(machine.get('ShotX'), machine.get('ShotY'))
        current_room = machine.get('CurrentRoom')
        assert machine.get('RoomMask') == room_mask(current_room)
        events = machine.bus.events
        sync = [(c, v) for c, r, v in events if r == 0]
        assert [v for c, v in sync] == [2, 0]
        assert sync[1][0] // 76 - sync[0][0] // 76 == 3
        blank = [(c, v) for c, r, v in events if r == 1]
        assert [v for c, v in blank] == [0, 2]
        start, end = blank[0][0] // 76, blank[1][0] // 76
        assert start - sync[1][0] // 76 == 37
        assert end - start == 192
        background = [(c, v) for c, r, v in events if r == 0x09]
        assert [value for _, value in background] == [0x06, 0]
        assert background[0][0] // 76 - start == 160
        assert background[0][0] % 76 <= 22, background
        assert background[1][0] > blank[1][0], 'Fundo preto antes de VBLANK'
        rows = [[] for _ in range(160)]
        for cycle, register, value in events:
            row = cycle // 76 - start
            if 0 <= row < 160 and register in (0x1B, 0x1C, 0x0D, 0x0E, 0x0F):
                rows[row].append((cycle % 76, register, value))
            if register == 2:
                max_wsync = max(max_wsync, cycle % 76)
        sprite = SYMBOLS['ArrowSprites'] - 0xF000 + machine.get('Heading') * 8
        top = machine.get('YPos') * 2
        shot_top = machine.get('ShotY') * 2
        expected_buffer = [ROM[sprite + row - top // 2] if top // 2 <= row < top // 2 + 8 else 0
                           for row in range(80)]
        assert [machine.bus[SYMBOLS['PlayerBuffer'] + row] for row in range(80)] == expected_buffer
        for row, writes in enumerate(rows):
            wall = row < 8 or row >= 152
            pixels = ROM[sprite + (row - top) // 2] if top <= row < top + 16 else 0
            shot_pixels = machine.get('ShotActive') if shot_top <= row < shot_top + 2 else 0
            left = 0xF0 if wall else (0 if room_mask(current_room) & 4 and 56 <= row < 104 else 0x10)
            right = 0xF0 if wall else (0 if room_mask(current_room) & 8 and 56 <= row < 104 else 0x10)
            opening = room_mask(current_room) & (1 if row < 8 else 2)
            pf2 = (0x0F if opening else 0xFF) if wall else 0
            offset = 3 if row % 2 == 0 else 0
            expected_writes = [(3 + offset, 0x1C, shot_pixels), (11 + offset, 0x0D, left),
                               (18 + offset, 0x1B, pixels), (24 + offset, 0x0E, 0xFF if wall else 0),
                               (32 + offset, 0x0F, pf2), (40 + offset, 0x0D, right)]
            assert writes == expected_writes, (current_room, row, writes, expected_writes)
        check_hud(events, start, current_room)
        assert [(r, v) for _, r, v in events if r in (0x04, 0x05)] == [
            (0x04, 3), (0x05, 1), (0x04, 0), (0x05, 0)]
        assert [machine.bus.tia[r] for r in (0x04, 0x05)] == [0, 0]
        assert [machine.bus.tia[r] for r in (0x06, 0x07)] == [0x0E, 0x0E]
        assert all(v == 0x0E for _, r, v in events if r in (0x06, 0x07))
        # Calibracao do posicionamento e spill deliberado de HMP1.
        shot_x = machine.get('ShotX')
        resp = [(c, v) for c, r, v in events if r == 0x11]
        motion = [(c, v) for c, r, v in events if r == 0x21]
        assert len(resp) == 2 and len(motion) == 1
        assert len([c for c, r, _ in events if r == 0x10]) == 2
        coarse_cycle = 23 + 5 * (shot_x // 15)
        fine = (((shot_x % 15 - 15) & 255) ^ 7) << 4 & 255
        assert resp[0][0] % 76 == coarse_cycle
        assert resp[0][1] == motion[0][1] == fine
        assert motion[0][0] - resp[0][0] == 3
        hmove = [c for c, r, _ in events if r == 0x2A]
        assert len(hmove) == 1 and hmove[0] % 76 == 3
        frames += 1
    assert [machine.get(k) for k in ('YPos', 'YFrac', 'ShotActive')] == [68, 0, 0]
    print(f'OK: {frames} quadros de 262 linhas e quadro inicial; 9 salas, paredes/portas, buffer e HUD numerado; WSYNC ate ciclo {max_wsync}')


if __name__ == '__main__':
    check_controls()
    check_shots()
    check_rooms()
    check_video()
