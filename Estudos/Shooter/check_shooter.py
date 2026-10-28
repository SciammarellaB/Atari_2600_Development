"""Executa a ROM no py65 e confere controles, tiro e escritas/ciclos do TIA.

O barramento modela RAM, entradas e WSYNC; nao simula os pixels fisicos do TIA.
"""
from pathlib import Path
import re

try:
    from py65.devices.mpu6502 import MPU
except ImportError:
    raise SystemExit("Instale requirements-dev.txt no ambiente Python de testes")

ROOT = Path(__file__).resolve().parent
ROM = (ROOT / "build/main.bin").read_bytes()
SYMBOLS = {}
for line in (ROOT / "build/main.sym").read_text().splitlines():
    match = re.match(r"^(\w+)\s+([0-9a-fA-F]{4})\s", line)
    if match:
        SYMBOLS[match[1]] = int(match[2], 16)

SHIP = (0x18, 0x18, 0x3C, 0x3C, 0x7E, 0xFF, 0xE7, 0x42)
HUD_DIGITS = (
    ("###", "#.#", "#.#", "#.#", "#.#", "#.#", "###"),
    (".#.", "##.", ".#.", ".#.", ".#.", ".#.", "###"),
    ("###", "..#", "..#", "###", "#..", "#..", "###"),
    ("###", "..#", "..#", "###", "..#", "..#", "###"),
    ("#.#", "#.#", "#.#", "###", "..#", "..#", "..#"),
    ("###", "#..", "#..", "###", "..#", "..#", "###"),
    ("###", "#..", "#..", "###", "#.#", "#.#", "###"),
    ("###", "..#", "..#", ".#.", ".#.", ".#.", ".#."),
    ("###", "#.#", "#.#", "###", "#.#", "#.#", "###"),
    ("###", "#.#", "#.#", "###", "..#", "..#", "###"),
)
# (coluna do playfield de 0..39, linha logica, altura): referencia espacial
# independente das tabelas de bytes da ROM e de sua ordem de bits.
STARS = ((2, 6, 1), (1, 32, 2), (3, 64, 1), (0, 89, 1),
         (7, 14, 1), (10, 38, 1), (4, 58, 2), (9, 80, 1),
         (16, 2, 1), (13, 26, 2), (19, 49, 1), (15, 73, 1),
         (21, 19, 1), (23, 43, 2), (20, 69, 1), (22, 92, 1),
         (29, 9, 1), (25, 35, 1), (31, 61, 2), (27, 85, 1),
         (36, 22, 1), (33, 46, 2), (39, 55, 1), (35, 77, 1))
PICKUP_MASKS = {1: (1, 0, 1, 1, 1, 1, 1, 1),
                2: (0, 1, 1, 0, 1, 1, 0, 0),
                3: (1, 0, 1, 0, 1, 0, 1, 0)}


def star_field(phase, row):
    """Converte a disposicao espacial para os seis bytes do playfield."""
    result = [0] * 6
    for column, top, height in STARS:
        if not top <= (phase + row) % 96 < top + height:
            continue
        side, local = divmod(column, 20)
        if local < 4:
            index, bit = 0, local + 4
        elif local < 12:
            index, bit = 1, 11 - local
        else:
            index, bit = 2, local - 12
        result[side * 3 + index] |= 1 << bit
    return result


class Bus:
    def __init__(self):
        self.ram = bytearray(128)
        self.joystick = 0xFF
        self.fire = 0x80
        self.pending = []
        self.events = []

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
        assert not address & 0x1000, "Escrita na ROM"
        if address & 0x80 and not address & 0x200:
            self.ram[address & 0x7F] = value
        elif not address & 0x80:
            self.pending.append((address & 0x3F, value))


class Machine:
    def __init__(self):
        self.bus = Bus()
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
        for _ in range(20000):
            if self.cpu.pc == SYMBOLS[label]:
                return
            self.step()
        raise AssertionError(f"Execucao nao chegou a {label}")

    def get(self, label):
        return self.bus[SYMBOLS[label]]

    def set(self, **state):
        for label, value in state.items():
            self.bus[SYMBOLS[label]] = value

    def call(self, label):
        self.cpu.stPushWord(SYMBOLS["Frame"] - 1)
        self.cpu.pc = SYMBOLS[label]
        self.until("Frame")

    def frame(self):
        self.bus.events.clear()
        before = self.cpu.processorCycles
        self.step()
        self.until("SceneFirstSync")
        # O overscan atualiza bombas, itens e o proximo HUD apos a imagem.
        self.render_state = {key: self.get(key) for key in
                             ("XPos", "YPos", "ShotActive", "ShotX", "ShotY",
                              "StarPhase", "BombActive", "BombX", "BombY",
                              "PickupType", "PickupX", "PickupY", "SceneColor")}
        self.until("Frame")
        return self.cpu.processorCycles - before


def check_controls():
    m = Machine()
    assert (m.get("XPos"), m.get("YPos"), m.get("ShotActive")) == (76, 68, 0)
    cases = 0
    for mask in range(16):
        dx = int(bool(mask & 8)) - int(bool(mask & 4))
        dy = int(bool(mask & 2)) - int(bool(mask & 1))
        m.bus.joystick = 0xFF ^ (mask << 4)
        for x, y in ((8, 4), (144, 72), (8, 72), (144, 4), (76, 44)):
            m.set(XPos=x, YPos=y)
            m.call("ReadJoystick")
            assert m.get("XPos") == max(8, min(144, x + dx))
            assert m.get("YPos") == max(4, min(72, y + dy))
            for _ in range(160):
                m.call("ReadJoystick")
            assert m.get("XPos") == (144 if dx > 0 else 8 if dx < 0 else x)
            assert m.get("YPos") == (72 if dy > 0 else 4 if dy < 0 else y)
            cases += 1
    m.bus.joystick = 0xFF
    m.set(XPos=76, YPos=44)
    for _ in range(60):
        m.call("ReadJoystick")
    assert (m.get("XPos"), m.get("YPos")) == (76, 44)
    print(f"OK: {cases} combinacoes de controles/limites; diagonais, opostas e parada")


def check_shots():
    m = Machine()
    for x, y in ((8, 4), (144, 72), (76, 68)):
        m.set(XPos=x, YPos=y, ShotActive=0)
        m.bus.fire = 0x80
        m.call("UpdateShot")
        assert m.get("ShotActive") == 0
        m.bus.fire = 0
        m.call("UpdateShot")
        assert (m.get("ShotX"), m.get("ShotY"), m.get("ShotActive")) == (x + 3, y - 3, 0x80)
    for y in range(96):
        m.set(ShotActive=0x80, ShotX=79, ShotY=y, XPos=8, YPos=4)
        m.bus.fire = 0
        m.call("UpdateShot")
        assert m.get("ShotActive") == (0x80 if y >= 3 else 0)
        if y >= 3:
            assert m.get("ShotY") == y - 3
        assert m.get("ShotX") == 79
    # Soltar o botao nao remove o tiro. Segurar repete somente no quadro seguinte.
    m.set(ShotActive=0, XPos=76, YPos=68)
    m.bus.fire = 0
    m.call("UpdateShot")
    m.bus.fire = 0x80
    for y in range(62, -1, -3):
        m.call("UpdateShot")
        assert m.get("ShotY") == y and m.get("ShotActive") == 0x80
    m.call("UpdateShot")
    assert m.get("ShotActive") == 0
    m.call("UpdateShot")
    assert m.get("ShotActive") == 0
    m.bus.fire = 0
    m.call("UpdateShot")
    assert m.get("ShotY") == 65 and m.get("ShotActive") == 0x80
    for _ in range(22):
        m.call("UpdateShot")
    assert m.get("ShotActive") == 0
    m.call("UpdateShot")
    assert m.get("ShotY") == 65 and m.get("ShotActive") == 0x80
    print("OK: origem, subida, independencia da nave, saida pelo topo e repeticao do tiro")


def check_ship():
    m = Machine()
    for y in range(4, 73):
        m.set(YPos=y)
        m.call("PrepareShip")
        pointer = m.get("ShipPtr") | (m.bus[SYMBOLS["ShipPtr"] + 1] << 8)
        assert (pointer & 255) + 83 < 256, "Leitura da nave cruza pagina"
        expected = bytes(y) + bytes(SHIP) + bytes(84 - y - 8)
        actual = bytes(m.bus[pointer + row] for row in range(84))
        assert actual == expected, y
    assert m.cpu.sp == 0xFF
    print("OK: janela da nave em todas as alturas, sem buffer nem rastros")


def check_stars():
    m = Machine()
    assert (m.get("StarPhase"), m.get("StarTick")) == (0, 0)
    # Dois ciclos completos: rolagem sem entrada, direcao para baixo e wrap.
    for frame in range(1, 769):
        m.call("UpdateStars")
        assert m.get("StarPhase") == (-(frame // 4)) % 96
        assert m.get("StarTick") == frame % 4
        assert (m.get("XPos"), m.get("YPos"), m.get("ShotActive")) == (76, 68, 0)
    # O movimento e circular: a mesma estrela reaparece pelo topo apos sair.
    for phase in range(96):
        previous = [star_field(phase, row) for row in range(96)]
        following = [star_field((phase - 1) % 96, row) for row in range(96)]
        assert following == previous[-1:] + previous[:-1]
    print("OK: 768 atualizacoes de estrelas; velocidade, direcao, autonomia e wrap")


def check_hud():
    m = Machine()
    assert (m.get("Lives"), m.get("BombCount")) == (3, 0)
    cases = 0
    for score in (0, 123456, 999999, 909090, *(digit * 10**place for place in range(6) for digit in range(10))):
        digits = f"{score:06d}"
        for lives, bombs in ((0, 0), (3, 1), (9, 9)):
            m.set(ScoreHi=int(digits[:2], 16), ScoreMid=int(digits[2:4], 16),
                  ScoreLo=int(digits[4:], 16), Lives=lives, BombCount=bombs)
            m.call("PrepareHud")
            m.call("BuildHud")
            actual = [[False] * 40 for _ in range(7)]
            for row in range(7):
                for col in range(40):
                    side, local = divmod(col, 20)
                    if local < 4:
                        reg, bit = 0, local + 4
                    elif local < 12:
                        reg, bit = 1, 11 - local
                    else:
                        reg, bit = 2, local - 12
                    value = m.bus[SYMBOLS["HudBuffer"] + (side * 3 + reg) * 7 + row]
                    actual[row][col] = bool(value & (1 << bit))
            expected = [[False] * 40 for _ in range(7)]
            glyphs = [(1, (".#.", ".#.", "###", "###", "#.#", "...", "...")),
                      (5, HUD_DIGITS[lives]),
                      (33, (".#.", "..#", ".#.", "###", "###", "###", ".#.")),
                      (37, HUD_DIGITS[bombs])]
            glyphs += [(9 + i * 4, HUD_DIGITS[int(digit)]) for i, digit in enumerate(digits)]
            for left, glyph in glyphs:
                for row, pixels in enumerate(glyph):
                    for col, pixel in enumerate(pixels):
                        expected[row][left + col] = pixel == "#"
            assert actual == expected, (score, lives, bombs)
            for label in ("HudDigit0", "HudDigit1", "HudDigit2", "HudDigit3", "HudDigit4", "HudDigit5", "HudLife", "HudBomb"):
                assert m.get(label) + 6 < 256, (label, "fonte cruza pagina")
            cases += 1
    print(f"OK: {cases} paineis; seis digitos BCD, vidas, bombas e icones")


def check_effect_windows():
    m = Machine()
    for kind in range(1, 4):
        for y in range(84):
            m.set(ShotActive=0x80, ShotY=y, BombActive=2, BombY=y,
                  PickupType=kind, PickupY=y)
            m.call("PrepareEffects")
            for label, mask in (("ShotPtr", 0x80), ("BombPtr", 2), ("PickupPtr", 2)):
                ptr = m.get(label) | m.bus[SYMBOLS[label] + 1] << 8
                actual = [bool(m.bus[ptr + row] & mask) for row in range(84)]
                if label == "PickupPtr":
                    expected = [bool(PICKUP_MASKS[kind][row - y]) if 0 <= row - y < 8 else False
                                for row in range(84)]
                else:
                    height = 3 if label == "ShotPtr" else 4
                    expected = [y <= row < y + height for row in range(84)]
                    assert (ptr & 255) + 84 < 256
                assert actual == expected, (kind, y, label)
    m.set(ShotActive=0, BombActive=0, PickupType=0)
    m.call("PrepareEffects")
    for label in ("ShotPtr", "BombPtr", "PickupPtr"):
        ptr = m.get(label) | m.bus[SYMBOLS[label] + 1] << 8
        assert all(m.bus[ptr + row] == 0 for row in range(84))
    print("OK: janelas dos tiros/itens em 252 posicoes; sem pixels de outras tabelas")


def check_frame(m):
    hud_before = bytes(m.bus[SYMBOLS["HudBuffer"] + i] for i in range(42))
    assert m.frame() == 262 * 76, "Quadro diferente de 262 scanlines"
    state = m.render_state
    events = m.bus.events
    sync = [(c, v) for c, r, v in events if r == 0]
    blank = [(c, v) for c, r, v in events if r == 1]
    assert [v for _, v in sync] == [2, 0]
    assert [v for _, v in blank] == [0, 2]
    assert sync[1][0] // 76 - sync[0][0] // 76 == 3
    assert blank[0][0] // 76 - sync[1][0] // 76 == 37
    assert blank[1][0] - blank[0][0] == 192 * 76
    hud_line = blank[0][0] // 76
    hud_text = [(c, r, v) for c, r, v in events if (hud_line + 4) * 76 <= c < (hud_line + 18) * 76]
    for index, register in enumerate((0x0D, 0x0E, 0x0F)):
        writes = [(c, v) for c, r, v in hud_text if r == register]
        assert len(writes) == 28
        for line in range(14):
            for side in range(2):
                cycle, value = writes[line * 2 + side]
                assert cycle // 76 == hud_line + 4 + line
                deadline = ((23, 49), (28, 54), (38, 65))[index][side]
                earliest = (0, (29, 39, 50)[index])[side]
                assert earliest <= cycle % 76 <= deadline, ("HUD", register, line, cycle % 76)
                assert value == hud_before[(side * 3 + index) * 7 + line // 2]
    scene_line = blank[0][0] // 76 + 24
    visible = [(c, r, v) for c, r, v in events if scene_line * 76 <= c < blank[1][0]]
    # Flags de misseis persistem entre scanlines. O item fica uma scanline
    # abaixo de sua coordenada logica, e a bomba, uma acima (cortada no topo).
    for register in (0x1D, 0x1E):
        writes = [(c, v) for c, r, v in events if r == register and c < blank[1][0]]
        cursor, value = 0, 0
        for line in range(168):
            deadline = (scene_line + line) * 76 + 23
            while cursor < len(writes) and writes[cursor][0] < deadline:
                cycle, value = writes[cursor]
                if cycle // 76 == scene_line + line:
                    assert cycle % 76 < 23
                cursor += 1
            if register == 0x1D:
                row = (line - 1) // 2
                index = row - state["PickupY"]
                kind = state["PickupType"]
                enabled = kind and line > 0 and 0 <= index < 8 and PICKUP_MASKS[kind][index]
            else:
                row = (line + 1) // 2
                enabled = state["BombActive"] and line > 0 and 0 <= row - state["BombY"] < 4
            assert bool(value & 2) == bool(enabled), (register, line, value, state)
    for register in (0x1B, 0x1C):
        writes = [(c, v) for c, r, v in visible if r == register]
        # Ambos os players persistem na segunda scanline.
        repeat = 2
        assert len(writes) == 168 // repeat
        for index, (cycle, value) in enumerate(writes):
            line = index * repeat
            assert cycle // 76 == scene_line + line
            assert cycle % 76 < 23, (register, line, cycle % 76)
            row = line // 2
            if register == 0x1B:
                index = row - state["YPos"]
                expected = SHIP[index] if 0 <= index < 8 else 0
            else:
                expected = state["ShotActive"] if 0 <= row - state["ShotY"] < 3 else 0
            assert value == expected, (register, line, value, expected)
    # As seis escritas por scanline desenham metades diferentes, sem espelho.
    expected_rows = [star_field(state["StarPhase"], row) for row in range(84)]
    for index, register in enumerate((0x0D, 0x0E, 0x0F)):
        writes = [(c, v) for c, r, v in visible if r == register]
        assert len(writes) == 336
        for line in range(168):
            for side in range(2):
                cycle, value = writes[line * 2 + side]
                assert cycle // 76 == scene_line + line
                deadline = ((23, 49), (28, 54), (38, 65))[index][side]
                earliest = (0, (29, 39, 50)[index])[side]
                assert earliest <= cycle % 76 <= deadline, (register, line, side, cycle % 76)
                assert value == expected_rows[line // 2][side * 3 + index]
    assert m.cpu.sp == 0xFF


def check_video():
    m = Machine()
    m.frame()  # O primeiro Frame comeca antes do JMP de sete ciclos entre quadros.
    cases = 0
    for mask in range(16):
        m.bus.joystick = 0xFF ^ (mask << 4)
        for x, y in ((8, 4), (144, 72), (8, 72), (144, 4), (76, 68)):
            for active, sy, fire in ((0, 0, 0x80), (0, 0, 0), (0x80, 77, 0), (0x80, 2, 0)):
                m.set(XPos=x, YPos=y, ShotActive=active, ShotX=x + 3, ShotY=sy)
                m.bus.fire = fire
                check_frame(m)
                cases += 1
    m.bus.joystick = 0xFF
    m.bus.fire = 0x80
    # Todas as coordenadas horizontais usadas no posicionamento do TIA.
    for x in range(8, 145):
        m.set(XPos=x, ShotX=x + 3)
        check_frame(m)
        cases += 1
    m.bus.joystick = 0x6F  # direita + cima enquanto atira continuamente
    m.bus.fire = 0
    for _ in range(180):
        check_frame(m)
        cases += 1
    # Cada origem circular, incluindo a emenda 95->0, com o tiro no topo.
    for phase in range(96):
        m.set(StarPhase=phase, StarTick=0, ShotActive=0x80, ShotY=3)
        check_frame(m)
        cases += 1
    m.bus.fire = 0x80
    m.bus.joystick = 0xFF
    for kind in range(1, 4):
        for y in range(84):
            m.set(XPos=8, YPos=68, PickupType=kind, PickupY=y, PickupX=144,
                  PickupTick=0, BombActive=2, BombX=8, BombY=(0, 3, 4, 68)[y % 4])
            check_frame(m)
            cases += 1
    print(f"OK: {cases} quadros NTSC de 262 linhas; 24 HUD + 168 cena, raster e pilha estaveis")


if __name__ == "__main__":
    check_controls()
    check_shots()
    check_ship()
    check_stars()
    check_hud()
    check_effect_windows()
    check_video()
