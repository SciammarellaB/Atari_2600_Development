"""Gera as tabelas compactas do HUD para o playfield assimetrico.

Os desenhos abaixo usam bits em ordem visual, da esquerda para a direita.
``hud_data`` converte cada linha para a ordem eletrica real de PF0/PF1/PF2,
de modo que o Assembly apenas leia bytes prontos para escrever no TIA.
"""

from pathlib import Path


HUD_ROWS = 5

# Fonte 3x5 dos digitos, em ordem visual. Cada inteiro representa uma linha.
DIGIT_GLYPHS = (
    (0b111, 0b101, 0b101, 0b101, 0b111),  # 0
    (0b010, 0b110, 0b010, 0b010, 0b111),  # 1
    (0b111, 0b001, 0b111, 0b100, 0b111),  # 2
    (0b111, 0b001, 0b111, 0b001, 0b111),  # 3
    (0b101, 0b101, 0b111, 0b001, 0b001),  # 4
    (0b111, 0b100, 0b111, 0b001, 0b111),  # 5
    (0b111, 0b100, 0b111, 0b101, 0b111),  # 6
    (0b111, 0b001, 0b010, 0b010, 0b010),  # 7
    (0b111, 0b101, 0b111, 0b101, 0b111),  # 8
    (0b111, 0b101, 0b111, 0b001, 0b111),  # 9
)

HEART_GLYPH = (0b101, 0b111, 0b111, 0b111, 0b010)
BULLET_GLYPH = (0b01, 0b11, 0b11, 0b11, 0b01)
WEAPON_GLYPH = (0b00000, 0b01111, 0b11110, 0b00100, 0b00100)


def _visual_bits(value, width):
    if not 0 <= value < 1 << width:
        raise ValueError(f"Linha {value!r} nao cabe em {width} bits")
    return [(value >> (width - 1 - column)) & 1 for column in range(width)]


def encode_pf(register, start_column, value, width):
    """Codifica um fragmento visual nas posicoes reais do registrador PF."""
    if register not in (0, 1, 2):
        raise ValueError("Registrador PF deve ser 0, 1 ou 2")
    half_column = start_column % 20
    limits = ((0, 4), (4, 12), (12, 20))[register]
    if not limits[0] <= half_column or half_column + width > limits[1]:
        raise ValueError("Glifo cruza o limite do registrador PF")
    result = 0
    for column, bit in enumerate(_visual_bits(value, width), half_column):
        if not bit:
            continue
        if register == 0:
            result |= 1 << (4 + column)
        elif register == 1:
            result |= 1 << (7 - (column - 4))
        else:
            result |= 1 << (column - 12)
    return result


def _encode_glyph(glyph, width, start_column, register):
    if len(glyph) != HUD_ROWS:
        raise ValueError(f"Glifo deve ter {HUD_ROWS} linhas")
    return [encode_pf(register, start_column, row, width) for row in glyph]


def hud_data():
    """Retorna as tabelas finais, prontas para PF0/PF1/PF2."""
    tens = [value for glyph in DIGIT_GLYPHS
            for value in _encode_glyph(glyph, 3, 20, 0)]
    ones = [value for glyph in DIGIT_GLYPHS
            for value in _encode_glyph(glyph, 3, 24, 1)]
    heart = _encode_glyph(HEART_GLYPH, 3, 0, 0)
    bullet = _encode_glyph(BULLET_GLYPH, 2, 15, 2)

    health = []
    for segments in range(4):
        row = 0
        for start in (4, 7, 10)[:segments]:
            row |= encode_pf(1, start, 0b11, 2)
        health.extend((0, row, row, row, 0))

    weapon = []
    key = (0b11, 0b11, 0b01, 0b01, 0b01)
    for inventory in range(4):
        gun_rows = (_encode_glyph(WEAPON_GLYPH, 5, 34, 2)
                    if inventory & 1 else [0] * HUD_ROWS)
        key_rows = (_encode_glyph(key, 2, 32, 2)
                    if inventory & 2 else [0] * HUD_ROWS)
        weapon.extend(gun | carried for gun, carried in zip(gun_rows, key_rows))
    data = {
        "HudTens": tens,
        "HudOnes": ones,
        "HudHeart": heart,
        "HudBullet": bullet,
        "HudHealth": health,
        "HudWeapon": weapon,
    }
    expected = {
        "HudTens": 50, "HudOnes": 50, "HudHeart": 5,
        "HudBullet": 5, "HudHealth": 20, "HudWeapon": 20,
    }
    if {name: len(values) for name, values in data.items()} != expected:
        raise AssertionError("Tamanho inesperado nas tabelas do HUD")
    return data


def _emit_table(lines, name, values):
    lines.append(name)
    for offset in range(0, len(values), 10):
        chunk = values[offset:offset + 10]
        lines.append("        byte " + ",".join(f"${value:02X}" for value in chunk))


def generate(destination):
    """Escreve ``hud.inc`` com as duas macros DASM do HUD."""
    data = hud_data()
    lines = ["; Gerado por scripts/hud.py; nao editar.", "        MAC HUD_DIGITS"]
    for name in ("HudTens", "HudOnes"):
        _emit_table(lines, name, data[name])
    lines.append("        ENDM")
    lines.append("        MAC HUD_STATUS")
    for name in ("HudHeart", "HudBullet", "HudHealth", "HudWeapon"):
        _emit_table(lines, name, data[name])
    lines.append("        ENDM")
    Path(destination).write_text("\n".join(lines) + "\n")

