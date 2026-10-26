"""Arte e colisao dos tres andares da mansao, em celulas de 4 x 4.

O playfield mostra contornos, detalhes dos moveis e decoracao atravessavel.
Os retangulos inclusivos sao a fonte de verdade da colisao: um tapete nunca
vira parede. Nenhum destes desenhos usa os objetos moveis do TIA.
"""

from world import EXITS, NONE, ROOM_NAMES, STAIRS

WIDTH, HEIGHT = 40, 48

# Cor NTSC do mobiliario e do piso. Nivel de luminancia baixo no piso deixa
# os detalhes do PF, o jogador ciano e os objetos coletaveis bem destacados.
_PALETTES = (0x2A, 0x0A, 0xCA, 0x1A, 0x1A, 0x6A, 0x0A, 0x2A,
             0x3A, 0x4A, 0x8A, 0xCA, 0x0A, 0x8A, 0x1A)
_FLOORS = (0x02, 0x82, 0x02, 0x02, 0x22, 0x62, 0x02, 0x22,
           0x22, 0x42, 0x82, 0xC2, 0x22, 0x62, 0x42)

# (tipo, x0, y0, x1, y1). Cada movel tem um unico footprint; suas partes
# vazadas pertencem ao desenho, mas o jogador nao atravessa camas ou mesas.
_INTERIORS = (
    # Cozinha em L: pia, despensa e ilha de preparo. O armario comprido
    # forma um recanto de servico para o switch, com entrada pelo norte.
    (("sink", 4, 5, 14, 10), ("stove", 29, 5, 35, 12),
     ("cupboard", 4, 11, 8, 17), ("table", 25, 32, 34, 40),
     ("chair", 28, 14, 33, 19), ("wardrobe", 12, 29, 16, 40),
     ("cupboard", 4, 40, 13, 43)),
    # Entrada mais aberta: bancos junto as colunas e uma jardineira.
    (("column", 6, 9, 9, 15), ("column", 30, 9, 33, 15),
     ("column", 6, 40, 9, 43), ("column", 30, 36, 33, 42),
     ("console", 26, 5, 35, 8), ("bench", 4, 28, 13, 30),
     ("bench", 27, 29, 35, 32), ("plant", 3, 5, 9, 11)),
    # Macas desencontradas, biombo e carrinho deixam a enfermaria menos
    # simetrica; o armario inferior protege a area dos suprimentos.
    (("bed", 4, 5, 11, 15), ("bed", 28, 8, 35, 18),
     ("curtain", 14, 4, 15, 17), ("medical", 29, 33, 36, 41),
     ("curtain", 13, 30, 14, 40), ("trolley", 4, 28, 9, 30),
     ("cupboard", 4, 40, 13, 43)),
    # Mesa principal e cadeiras; o buffet ocupa a outra metade da sala.
    (("dining", 5, 6, 15, 16), ("chair", 7, 17, 12, 19),
     ("sideboard", 27, 5, 35, 10), ("chair", 27, 13, 32, 19),
     ("sideboard", 25, 33, 35, 40), ("wardrobe", 12, 31, 16, 40),
     ("cupboard", 4, 40, 13, 43)),
    # A simetria dos pilares orienta o hall; bancos laterais interrompem
    # o eixo longo sem ocupar o cruzamento das quatro passagens.
    (("column", 7, 8, 10, 15), ("column", 29, 8, 32, 15),
     ("column", 7, 40, 10, 43), ("column", 29, 37, 32, 43),
     ("bench", 4, 28, 13, 30), ("bench", 26, 29, 35, 32),
     ("console", 25, 4, 35, 7)),
    # Estantes em L e uma mesa de leitura com cadeira. A chave fica no
    # nicho formado pela estante lateral, acessivel por cima.
    (("books", 3, 5, 14, 11), ("books", 25, 5, 36, 11),
     ("shelf", 33, 12, 36, 18), ("shelf", 12, 29, 15, 41),
     ("reading", 25, 29, 31, 34), ("chair", 26, 37, 31, 43),
     ("shelf", 33, 35, 36, 43), ("books", 3, 41, 13, 44)),
    # Molduras desencontradas e esculturas em pedestais, com banco para
    # observar os quadros. A escultura inferior prolonga o pequeno recanto.
    (("picture", 4, 5, 13, 12), ("picture", 26, 7, 35, 14),
     ("vase", 28, 31, 34, 39), ("vase", 4, 40, 10, 44),
     ("bench", 11, 40, 16, 43), ("partition", 13, 30, 16, 39),
     ("plant", 5, 14, 11, 19)),
    # Escrivaninha com cadeira, arquivo alto e um canto de leitura.
    (("desk", 4, 5, 15, 13), ("chair", 7, 14, 12, 19),
     ("files", 29, 6, 35, 17), ("reading", 27, 29, 35, 33),
     ("sofa", 25, 36, 35, 42), ("shelf", 13, 31, 16, 41),
     ("cupboard", 4, 41, 13, 44)),
    # Quarto: cama, penteadeira com espelho e um canto com poltrona.
    (("bed", 25, 5, 35, 18), ("nightstand", 32, 31, 36, 36),
     ("vanity", 4, 5, 13, 15), ("chair", 27, 31, 31, 38),
     ("wardrobe", 12, 30, 16, 41), ("cupboard", 4, 41, 13, 44),
     ("dresser", 28, 41, 36, 44)),
)

# Os interiores do terreo e do andar superior conservam a linguagem dos
# moveis existentes. O subsolo usa caixas, tubos e maquinas, enquanto as
# escadas ficam no proprio piso para nao ocupar P0/P1 nem bloquear passagem.
_FURNITURE = (
    # B1: deposito, com caixas empilhadas e estante de ferramentas.
    (("books", 3, 5, 14, 11), ("crate", 25, 5, 30, 12),
     ("crate", 32, 9, 36, 16), ("shelf", 12, 29, 15, 40),
     ("crate", 4, 40, 13, 44), ("crate", 27, 33, 35, 42)),
    # B2: sala de servico, tanques e bancadas junto a escada.
    (("sink", 4, 5, 14, 10), ("cupboard", 28, 6, 35, 15),
     ("pipe", 5, 12, 8, 18), ("bench", 4, 28, 13, 30),
     ("table", 26, 32, 35, 40), ("crate", 4, 41, 13, 44)),
    # B3: despensa; prateleiras em L deixam o switch no recanto inferior.
    (("books", 3, 5, 14, 11), ("books", 26, 5, 36, 11),
     ("shelf", 33, 12, 36, 18), ("shelf", 12, 29, 15, 40),
     ("cupboard", 4, 40, 13, 44), ("crate", 27, 34, 35, 42)),
    # B4: gerador e quadro eletrico; os tubos fazem parte dos volumes.
    (("generator", 4, 5, 15, 17), ("panel", 28, 5, 35, 14),
     ("pipe", 26, 15, 35, 18), ("pipe", 12, 29, 15, 40),
     ("crate", 4, 40, 13, 44), ("generator", 27, 33, 35, 42)),
    _INTERIORS[1],  # T1: saguão.
    _INTERIORS[6],  # T2: galeria.
    _INTERIORS[4],  # T3: hall.
    _INTERIORS[5],  # T4: biblioteca.
    # T5: escadaria, com corrimaos laterais e bancos de descanso.
    (("rail", 12, 5, 15, 17), ("rail", 25, 5, 28, 17),
     ("picture", 30, 7, 36, 14), ("bench", 4, 28, 13, 30),
     ("column", 28, 33, 31, 41), ("plant", 4, 40, 10, 45)),
    _INTERIORS[8],  # A1: quarto.
    _INTERIORS[2],  # A2: enfermaria.
    _INTERIORS[7],  # A3: escritorio.
    # A4: patamar aberto, com quadros e banco entre as duas escadas.
    (("plant", 5, 7, 11, 14), ("picture", 27, 5, 35, 12),
     ("bench", 4, 28, 13, 30), ("column", 29, 34, 32, 42),
     ("console", 26, 15, 35, 18)),
    _INTERIORS[6],  # A5 compartilha o template de T2.
    # A6: suite maior, penteadeira, cama e canto com sofa.
    (("bed", 25, 5, 36, 18), ("vanity", 4, 5, 14, 16),
     ("wardrobe", 12, 29, 16, 41), ("cupboard", 4, 41, 13, 44),
     ("sofa", 25, 35, 36, 42), ("plant", 30, 28, 36, 34)),
)

# Estilos dos detalhes atravessaveis: ladrilhos do subsolo, passadeiras
# nos saloes, juntas de madeira e pequenos mosaicos nas galerias.
_STYLES = (0, 0, 0, 0, 1, 6, 4, 5, 6, 8, 2, 7, 1, 6, 8)


def _walls(room):
    left, right, up, down = EXITS[room]
    result = []
    for x, opened in ((0, left != NONE), (39, right != NONE)):
        result.extend(((x, 0, x, 19), (x, 28, x, 47)) if opened else
                      ((x, 0, x, 47),))
    for y, opened in ((0, up != NONE), (47, down != NONE)):
        result.extend(((1, y, 17, y), (22, y, 38, y)) if opened else
                      ((1, y, 38, y),))
    return result


def solid_rects(room):
    """Paredes e volumes solidos, em coordenadas inclusivas do mapa."""
    _validate_room(room)
    return _walls(room) + [tuple(shape[1:]) for shape in _FURNITURE[room]]


def _validate_room(room):
    if not isinstance(room, int) or not 0 <= room < len(ROOM_NAMES):
        raise ValueError(f"Sala invalida: {room}")


def _blank():
    return [["."] * WIDTH for _ in range(HEIGHT)]


def _fill(grid, rect):
    x0, y0, x1, y1 = rect
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            grid[y][x] = "#"


def collision_map(room):
    grid = _blank()
    for rect in solid_rects(room):
        _fill(grid, rect)
    return ["".join(row) for row in grid]


def _outline(grid, x0, y0, x1, y1):
    for x in range(x0, x1 + 1):
        grid[y0][x] = grid[y1][x] = "#"
    for y in range(y0, y1 + 1):
        grid[y][x0] = grid[y][x1] = "#"


def _line(grid, x0, y, x1):
    for x in range(x0, x1 + 1):
        grid[y][x] = "#"


def _draw_furniture(grid, kind, x0, y0, x1, y1):
    """Contornos e pequenos recortes distinguem tampo, frente e pes."""
    width, height = x1 - x0 + 1, y1 - y0 + 1
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    if kind == "vase":
        _line(grid, cx - 1, y0, cx + 1)
        grid[y0 + 1][cx] = "#"
        _outline(grid, cx - 2, y0 + 2, cx + 2, y1 - 2)
        _line(grid, x0, y1 - 1, x1)
        _line(grid, x0, y1, x1)
    elif kind == "column":
        _line(grid, x0, y0, x1)
        _line(grid, x0, y1, x1)
        for y in range(y0 + 1, y1):
            grid[y][x0 + 1] = grid[y][x1 - 1] = "#"
    elif kind in ("chair", "bench", "sofa"):
        back = min(y0 + 2, y1 - 1)
        _outline(grid, x0, y0, x1, back)
        _line(grid, x0, min(y0 + 4, y1), x1)
        for y in range(back + 1, y1 + 1):
            grid[y][x0] = grid[y][x1] = "#"
        if kind == "sofa":
            for x in range(x0 + 3, x1, 3):
                grid[y0 + 3][x] = "#"
    elif kind == "shelf":
        _outline(grid, x0, y0, x1, y1)
        for y in range(y0 + 3, y1, 4):
            _line(grid, x0 + 1, y, x1 - 1)
        for y in range(y0 + 1, y1):
            if (y - y0) % 4 == 1:
                grid[y][x0 + 1] = "#"
    elif kind == "curtain":
        # A linha ondulada e os suportes deixam evidente o biombo solido.
        _line(grid, x0, y0, x1)
        _line(grid, x0, y1, x1)
        for y in range(y0 + 1, y1):
            grid[y][x0 + ((y - y0) % 2)] = "#"
    elif kind == "partition":
        _outline(grid, x0, y0, x1, y1)
        for y in range(y0 + 2, y1, 4):
            _outline(grid, x0 + 1, y, x1 - 1, min(y + 1, y1 - 1))
    elif kind == "wardrobe":
        _outline(grid, x0, y0, x1, y1)
        _line(grid, x0 + 1, y0 + 2, x1 - 1)
        for y in range(y0 + 3, y1):
            grid[y][cx] = "#"
        grid[cy][cx - 1] = grid[cy][cx + 1] = "#"
    elif kind == "plant":
        _line(grid, cx - 2, y0 + 1, cx + 2)
        _line(grid, cx - 1, y0, cx + 1)
        grid[y0 + 2][cx] = "#"
        _outline(grid, cx - 1, y0 + 3, cx + 1, y1)
    elif kind == "trolley":
        _outline(grid, x0, y0, x1, y1 - 1)
        grid[y1][x0 + 1] = grid[y1][x1 - 1] = "#"
    elif kind == "pipe":
        if width >= height:
            _outline(grid, x0, y0 + 1, x1, y1 - 1)
            for x in range(x0 + 2, x1, 3):
                grid[y0][x] = grid[y1][x] = "#"
        else:
            _outline(grid, x0 + 1, y0, x1 - 1, y1)
            for y in range(y0 + 2, y1, 4):
                _line(grid, x0, y, x1)
    elif kind == "rail":
        _outline(grid, x0, y0, x1, y1)
        for y in range(y0 + 2, y1, 3):
            _line(grid, x0 + 1, y, x1 - 1)
    else:
        # O ultimo par de linhas da frente tem apenas os pes nas mesas.
        legs = kind in ("table", "desk", "reading", "console", "dining")
        front = y1 - 2 if legs else y1
        _outline(grid, x0, y0, x1, front)
        if legs:
            for y in range(front + 1, y1 + 1):
                grid[y][x0 + 1] = grid[y][x1 - 1] = "#"
        if kind == "bed":
            _outline(grid, x0 + 2, y0 + 2, x1 - 2, y0 + 4)
            _line(grid, x0 + 1, y0 + 6, x1 - 1)
            _line(grid, x0 + 1, y1 - 1, x1 - 1)
        elif kind in ("cupboard", "dresser", "sideboard", "files"):
            for y in range(y0 + 2, y1, 3):
                _line(grid, x0 + 1, y, x1 - 1)
            if width >= 8:
                for y in range(y0 + 1, y1):
                    grid[y][cx] = "#"
            for y in range(y0 + 1, y1, 3):
                grid[y][x0 + 2] = grid[y][x1 - 2] = "#"
        elif kind == "books":
            for y in range(y0 + 3, y1 + 1, 4):
                _line(grid, x0 + 1, y, x1 - 1)
            for x in range(x0 + 2, x1, 3):
                for y in range(y0 + 1, y1):
                    if (y - y0) % 4:
                        grid[y][x] = "#"
        elif kind == "sink":
            _outline(grid, x0 + 2, y0 + 1, x0 + 5, y0 + 3)
            grid[y0 + 1][x1 - 2] = "#"
            _line(grid, x0 + 1, y1 - 1, x1 - 1)
        elif kind == "stove":
            for x in (x0 + 2, x1 - 2):
                for y in (y0 + 2, y0 + 4):
                    grid[y][x] = grid[y][x + 1] = "#"
            _line(grid, x0 + 1, y1 - 1, x1 - 1)
        elif kind == "medical":
            _line(grid, cx - 1, y0 + 3, cx + 1)
            for y in range(y0 + 1, y0 + 6):
                grid[y][cx] = "#"
            _line(grid, x0 + 1, y1 - 1, x1 - 1)
        elif kind == "picture":
            # Uma moldura dupla e uma paisagem em degraus.
            _outline(grid, x0 + 1, y0 + 1, x1 - 1, y1 - 1)
            for x in range(x0 + 3, x1 - 2):
                grid[y1 - 3 - (x % 3 == 0)][x] = "#"
            grid[y0 + 3][x1 - 3] = "#"
        elif kind in ("desk", "reading"):
            _outline(grid, x0 + 2, y0 + 1, x0 + 4, y0 + 3)
            grid[y0 + 2][x1 - 2] = "#"
        elif kind == "dining":
            # Duas mesas compridas com lugares marcados, sem fechar o eixo.
            for y in range(y0 + 2, front - 1, 3):
                grid[y][x0 + 2] = grid[y][x1 - 2] = "#"
            _line(grid, cx - 1, y0 + 4, cx + 1)
        elif kind == "nightstand":
            _line(grid, x0 + 1, y0 + 2, x1 - 1)
            grid[y0 + 4][cx] = "#"
        elif kind == "vanity":
            _outline(grid, x0 + 2, y0 + 1, x1 - 2, y0 + 5)
            _line(grid, x0 + 1, y0 + 7, x1 - 1)
            for y in range(y0 + 8, y1):
                grid[y][cx] = "#"
            grid[y1 - 1][x0 + 2] = grid[y1 - 1][x1 - 2] = "#"
        elif kind == "crate":
            # Cantoneiras e duas diagonais distinguem as caixas do armario.
            for offset in range(1, min(width, height) - 1):
                grid[y0 + offset][x0 + offset] = "#"
                grid[y0 + offset][x1 - offset] = "#"
        elif kind == "panel":
            for y in range(y0 + 2, y1 - 1, 3):
                grid[y][x0 + 2] = grid[y][x1 - 2] = "#"
            _line(grid, x0 + 1, y1 - 1, x1 - 1)
        elif kind == "generator":
            _outline(grid, x0 + 2, y0 + 2, x1 - 2, y1 - 3)
            _line(grid, x0 + 2, cy, x1 - 2)
            for y in range(y0 + 2, y1 - 2):
                grid[y][cx] = "#"
            grid[y1 - 1][x0 + 2] = grid[y1 - 1][x1 - 2] = "#"


def _floor_detail(grid, room):
    # Passadeiras abertas e esparsas: deixam livre a leitura dos itens e das
    # portas. Sao decoracao, nunca volumes na collision_map.
    style = _STYLES[room]
    if style in (1, 4):
        for y in range(5, 44):
            if y not in range(19, 29):
                grid[y][16] = grid[y][23] = "#"
        _line(grid, 17, 5, 22)
        _line(grid, 17, 43, 22)
        for y in (11, 17, 31, 37):
            grid[y][19] = grid[y + 1][20] = "#"
    elif style == 6:
        for x in (16, 23):
            for y in (8, 16, 32, 40):
                grid[y][x] = "#"
    elif style in (0, 2):
        for y in (18, 30, 44):
            for x in (4, 12, 27, 35):
                grid[y][x] = "#"
    elif style in (3, 5, 7, 8):
        # Juntas curtas sugerem tabuas sem preencher o chao com xadrez claro.
        for y in (18, 30, 44):
            _line(grid, 4, y, 6)
            _line(grid, 33, y, 35)
    for origin, direction, _ in STAIRS:
        if origin == room:
            # Degraus desenhados no chao: a colisao conserva o vao aberto.
            # A largura crescente distingue uma escada de um movel solido.
            for depth in range(4):
                y = 2 + depth * 2 if direction == 2 else 45 - depth * 2
                half = 1 + depth // 2
                _line(grid, 19 - half, y, 20 + half)


def scene(room):
    _validate_room(room)
    grid = _blank()
    for rect in _walls(room):
        _fill(grid, rect)
    _floor_detail(grid, room)
    for shape in _FURNITURE[room]:
        _draw_furniture(grid, *shape)
    return ["".join(row) for row in grid]


def floor_colors(room):
    _validate_room(room)
    base = _FLOORS[room]
    # Faixas suaves sob os moveis e juntas: sem alternancia por quadro.
    if _STYLES[room] in (1, 4):
        return [base if 5 <= y <= 43 else 0x02 for y in range(HEIGHT)]
    return [base + 2 if y % 8 == 7 else base for y in range(HEIGHT)]


def room_palette(room):
    _validate_room(room)
    return _PALETTES[room]
