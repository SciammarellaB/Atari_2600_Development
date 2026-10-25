"""Desenho do menu em 40 colunas de playfield por 48 linhas logicas.

Cada celula ocupa 4 pixels TIA por 4 scanlines. A montagem gera menu.inc;
o layout e a fonte abaixo sao a fonte de verdade, sem assets externos.
"""

FONT = {
    " ": ("000",) * 5,
    "A": ("010", "101", "111", "101", "101"),
    "C": ("111", "100", "100", "100", "111"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "G": ("111", "100", "101", "101", "111"),
    "J": ("001", "001", "001", "101", "111"),
    "L": ("100", "100", "100", "100", "111"),
    "O": ("111", "101", "101", "101", "111"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
}
TITLE = {
    "C": ("01111", "11000", "11000", "11000", "11000", "11000", "01111"),
    "O": ("01110", "11011", "11011", "11011", "11011", "11011", "01110"),
    "S": ("01111", "11000", "11000", "01110", "00011", "00011", "11110"),
    "M": ("11011", "11111", "11111", "11011", "11011", "11011", "11011"),
}


def layout():
    pixels = [[0] * 40 for _ in range(48)]

    def text(value, y, font=FONT, x=None):
        width = sum(len(font[c][0]) + 1 for c in value) - 1
        x = (40 - width) // 2 if x is None else x
        assert 0 <= x and x + width <= 40
        for char in value:
            glyph = font[char]
            for dy, row in enumerate(glyph):
                for dx, bit in enumerate(row):
                    pixels[y + dy][x + dx] = int(bit)
            x += len(glyph[0]) + 1

    text("COSMOS", 6, TITLE)
    text("JOGADORES", 21)
    text("1", 29, x=10)
    text("2", 29, x=26)
    text("SELECT", 41)
    # Estrelas e pequenos tracos emolduram a tela sem competir com o texto.
    for x, y in ((3, 2), (29, 2), (36, 17), (5, 17), (1, 37), (36, 37)):
        pixels[y][x] = 1
    for x in range(3, 37):
        pixels[16][x] = int(x % 2 == 0)
    return pixels


def generate(destination):
    """Empacota a ordem peculiar PF0 ascendente/PF1 descendente/PF2 ascendente."""
    data = {f"{side}PF{index}": [] for side in ("Left", "Right") for index in range(3)}
    for row in layout():
        for side, bits in (("Left", row[:20]), ("Right", row[20:])):
            data[f"{side}PF0"].append(sum(bits[i] << (4 + i) for i in range(4)))
            data[f"{side}PF1"].append(sum(bits[4 + i] << (7 - i) for i in range(8)))
            data[f"{side}PF2"].append(sum(bits[12 + i] << i for i in range(8)))
    # Seta para cima sob o numero selecionado, desenhada pelo player 0.
    data["CursorRows"] = [0x18 if y == 35 else 0x3C if y == 36 else 0 for y in range(48)]
    lines = ["; Gerado durante o build. Edite scripts/graphics.py."]
    for name, values in data.items():
        lines += ["        align 256", name]
        for offset in range(0, len(values), 12):
            lines.append("        byte " + ",".join(f"${v:02X}" for v in values[offset:offset + 12]))
    destination.write_text("\n".join(lines) + "\n")
