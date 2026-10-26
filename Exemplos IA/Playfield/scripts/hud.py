"""Gera os glifos de nove linhas do painel desenhado com P0/P1.

Corações e dígitos repetem cada linha em duas scanlines; o inventário usa
as 18 scanlines individualmente. Os bits seguem a ordem visual dos
sprites do TIA: bit 7 à esquerda e bit 0 à direita. Os dígitos ocupam seis
pixels e têm versões alinhadas para cada lado do par de sprites.
"""

from pathlib import Path


HUD_ROWS = 9
HUD_INVENTORY_ROWS = 18

# Fonte 6x9: cada inteiro representa uma linha, da esquerda para a direita.
DIGIT_GLYPHS = (
    (0b011110, 0b110011, 0b110011, 0b110111, 0b111011,
     0b110011, 0b110011, 0b110011, 0b011110),  # 0
    (0b001100, 0b011100, 0b001100, 0b001100, 0b001100,
     0b001100, 0b001100, 0b001100, 0b111111),  # 1
    (0b011110, 0b110011, 0b000011, 0b000011, 0b000110,
     0b001100, 0b011000, 0b110000, 0b111111),  # 2
    (0b011110, 0b110011, 0b000011, 0b000110, 0b001110,
     0b000011, 0b000011, 0b110011, 0b011110),  # 3
    (0b000110, 0b001110, 0b011110, 0b110110, 0b110110,
     0b111111, 0b000110, 0b000110, 0b000110),  # 4
    (0b111111, 0b110000, 0b110000, 0b111110, 0b000011,
     0b000011, 0b000011, 0b110011, 0b011110),  # 5
    (0b001110, 0b011000, 0b110000, 0b110000, 0b111110,
     0b110011, 0b110011, 0b110011, 0b011110),  # 6
    (0b111111, 0b000011, 0b000110, 0b000110, 0b001100,
     0b001100, 0b011000, 0b011000, 0b011000),  # 7
    (0b011110, 0b110011, 0b110011, 0b110011, 0b011110,
     0b110011, 0b110011, 0b110011, 0b011110),  # 8
    (0b011110, 0b110011, 0b110011, 0b110011, 0b011111,
     0b000011, 0b000011, 0b000110, 0b011100),  # 9
)

HEART_EMPTY_GLYPH = (
    0b01100110,
    0b10011001,
    0b10000001,
    0b10000001,
    0b01000010,
    0b01000010,
    0b00100100,
    0b00011000,
    0b00011000,
)
HEART_FULL_GLYPH = (
    0b01100110,
    0b11111111,
    0b11111111,
    0b11111111,
    0b01111110,
    0b01111110,
    0b00111100,
    0b00011000,
    0b00011000,
)
BULLET_GLYPH = (
    0b010, 0b111, 0b101, 0b101, 0b101, 0b101, 0b111, 0b111, 0b000,
)
TIMES_GLYPH = (
    0b000, 0b000, 0b000, 0b101, 0b010, 0b101, 0b000, 0b000, 0b000,
)
# O inventario usa as 18 scanlines individualmente: arma com seis linhas e
# tres chaves com quatro linhas cada, em posicoes e cores independentes.
WEAPON_GLYPH = (0b11111111, 0b11111111, 0b11111110,
                0b11111110, 0b00111000, 0b01110000)
KEY_GLYPH = (0b01100000, 0b10011111, 0b01100101, 0b00000101)
CROWN_GLYPH = (0b10011001, 0b11011011, 0b11111111,
               0b01111110, 0b01111110, 0b01111110)


def _validate_glyph(glyph, width, rows=HUD_ROWS):
    if len(glyph) != rows:
        raise ValueError(f"Glifo deve ter {rows} linhas")
    if any(not 0 <= row < 1 << width for row in glyph):
        raise ValueError(f"Glifo deve conter linhas de {width} bits")


def hud_data():
    """Retorna os bytes dos sprites; índice zero dos dígitos fica em branco.

    Os offsets de cada dígito são ``(digito + 1) * HUD_ROWS``. Dezenas usam
    bits 5..0; unidades usam os mesmos desenhos deslocados para bits 7..2.
    Corações têm contorno/cheio. Inventário usa arma=1, verde=2, azul=4, ouro=8.
    Suas 18 linhas usam uma scanline por linha, sem alternar os objetos.
    """
    for glyph in DIGIT_GLYPHS:
        _validate_glyph(glyph, 6)
    for glyph in (HEART_EMPTY_GLYPH, HEART_FULL_GLYPH):
        _validate_glyph(glyph, 8)
    _validate_glyph(WEAPON_GLYPH, 8, 6)
    _validate_glyph(KEY_GLYPH, 8, 4)
    _validate_glyph(CROWN_GLYPH, 8, 6)
    for glyph in (BULLET_GLYPH, TIMES_GLYPH):
        _validate_glyph(glyph, 3)

    digits = [0] * HUD_ROWS + [row for glyph in DIGIT_GLYPHS for row in glyph]
    inventory = [row for state in range(16)
                 for row in ((list(WEAPON_GLYPH) if state & 1 else [0] * 6) +
                             [row for bit in (2, 4, 8)
                              for row in (KEY_GLYPH if state & bit else [0] * 4)])]
    data = {
        "HudHearts": list(HEART_EMPTY_GLYPH + HEART_FULL_GLYPH),
        "HudDigitsTens": digits,
        "HudDigitsOnes": [row << 2 for row in digits],
        "HudBulletTimes": [(bullet << 5) | times
                           for bullet, times in zip(BULLET_GLYPH, TIMES_GLYPH)],
        "HudInventoryLow": inventory[:8 * HUD_INVENTORY_ROWS],
        "HudInventoryHigh": inventory[8 * HUD_INVENTORY_ROWS:],
        "HudVictory": list(CROWN_GLYPH) + [0] * 12,
    }
    expected = {
        "HudHearts": 18, "HudDigitsTens": 99, "HudDigitsOnes": 99,
        "HudBulletTimes": 9, "HudInventoryLow": 144,
        "HudInventoryHigh": 144, "HudVictory": 18,
    }
    if {name: len(values) for name, values in data.items()} != expected:
        raise AssertionError("Tamanho inesperado nas tabelas do HUD")
    return data


def generate(destination):
    """Escreve tabelas DASM diretas, cada uma alinhada em uma página."""
    lines = ["; Gerado por scripts/hud.py; nao editar."]
    for name, values in hud_data().items():
        lines.extend(("        align 256", name))
        for offset in range(0, len(values), HUD_ROWS):
            chunk = values[offset:offset + HUD_ROWS]
            lines.append("        byte " + ",".join(f"%{value:08b}" for value in chunk))
    Path(destination).write_text("\n".join(lines) + "\n")
