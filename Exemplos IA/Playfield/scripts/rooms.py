"""Mapas da mansao: 40 x 48 celulas, com duas salas por banco F4.

Cada celula ocupa 4 pixels TIA x 4 scanlines. A grade de navegacao e:
6--7--8 / 3--4--5 / 0--1--2. Objetos sao desenhados por P0, nao pelo PF.
"""

WIDTH, HEIGHT, REPEAT = 40, 48, 4
NONE = 255
BANK_COUNT = 8
ROOMS_PER_BANK = 2
ROOM_NAMES = ("Cozinha", "Vestibulo", "Enfermaria", "Jantar", "Hall",
              "Biblioteca", "Galeria", "Escritorio", "Quarto")
# Ordem: esquerda, direita, cima, baixo. Indices comecam em zero.
EXITS = tuple((room - 1 if room % 3 else NONE,
               room + 1 if room % 3 < 2 else NONE,
               room + 3 if room < 6 else NONE,
               room - 3 if room >= 3 else NONE) for room in range(9))
# Biblioteca e quarto dependem das portas vermelha e azul, respectivamente.
# Fechar estas duas ligacoes impede contornar os puzzles por outro corredor.
EXITS = tuple(tuple(NONE if (room, target) in ((2, 5), (5, 2), (5, 8), (8, 5))
                    else target for target in exits)
              for room, exits in enumerate(EXITS))
# Um objeto por sala: vazio, arma, balas, vida, switch vermelho, chave azul.
OBJECT_TYPES = (4, 0, 2, 1, 0, 5, 2, 0, 3)
OBJECT_COLORS = (0, 0x1C, 0x1C, 0xC4, 0x48, 0x84)
OBJECT_GLYPHS = ((0, 0, 0, 0), (0, 0x7E, 0x38, 0x30),
                 (0x66, 0xFF, 0xFF, 0x66), (0x18, 0x7E, 0x7E, 0x18),
                 (0xFF, 0xFF, 0xFF, 0xFF), (0x70, 0x50, 0x7E, 0x0A))
# Retangulos inclusivos de mobiliario. Os corredores centrais ficam livres.
FURNITURE = (
    ((4, 7, 13, 8), (27, 7, 35, 9), (27, 35, 35, 37)),
    ((7, 11, 11, 13), (28, 11, 32, 13), (18, 32, 21, 33)),
    ((5, 8, 11, 10), (28, 8, 34, 10), (28, 33, 34, 35)),
    ((10, 10, 15, 16), (25, 10, 30, 16), (25, 33, 30, 37)),
    ((8, 9, 10, 12), (29, 9, 31, 12), (29, 35, 31, 38)),
    ((4, 6, 14, 7), (26, 6, 35, 7), (26, 32, 35, 33), (26, 39, 35, 40)),
    ((6, 8, 9, 9), (29, 8, 32, 9), (29, 36, 32, 37)),
    ((8, 10, 14, 13), (27, 10, 34, 11), (27, 34, 34, 36)),
    ((26, 7, 34, 14), (5, 8, 11, 10), (27, 36, 33, 38)),
)


def _make_map(room):
    rows = [["#" if x in (0, WIDTH - 1) or y in (0, HEIGHT - 1) else "."
             for x in range(WIDTH)] for y in range(HEIGHT)]
    left, right, up, down = EXITS[room]
    for y in range(20, 28):
        if left != NONE:
            rows[y][0] = "."
        if right != NONE:
            rows[y][-1] = "."
    for x in range(18, 22):
        if up != NONE:
            rows[0][x] = "."
        if down != NONE:
            rows[-1][x] = "."
    for x0, y0, x1, y1 in FURNITURE[room]:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                rows[y][x] = "#"
    return "\n".join("".join(row) for row in rows)


MAPS = tuple(_make_map(room) for room in range(len(EXITS)))


def maps():
    result = [value.strip().splitlines() for value in MAPS]
    if len(result) != len(EXITS) or len(result) > BANK_COUNT * ROOMS_PER_BANK:
        raise ValueError("Mapas/conexoes inconsistentes ou excedem os bancos F4")
    opposite = (1, 0, 3, 2)
    for room, rows in enumerate(result):
        if len(rows) != HEIGHT or any(len(row) != WIDTH for row in rows):
            raise ValueError(f"Sala {room}: esperado {WIDTH} x {HEIGHT}")
        if any(set(row) - {"#", "."} for row in rows):
            raise ValueError(f"Sala {room}: use somente # e .")
        for direction, target in enumerate(EXITS[room]):
            if target != NONE and (not 0 <= target < len(result) or
                                   EXITS[target][opposite[direction]] != room):
                raise ValueError(f"Sala {room}: conexao invalida ou sem retorno")
        if any(rows[y][x] != "." for y in range(34, 38) for x in (8, 9)):
            raise ValueError(f"Sala {room}: mobiliario sobre o objeto")
    return result


def pack_half(bits):
    """Ordem horizontal: PF0 bits 4..7; PF1 bits 7..0; PF2 bits 0..7."""
    return (sum(bits[i] << (4 + i) for i in range(4)),
            sum(bits[4 + i] << (7 - i) for i in range(8)),
            sum(bits[12 + i] << i for i in range(8)))


def generate(destination, bank=0):
    if not 0 <= bank < BANK_COUNT:
        raise ValueError(f"Banco F4 invalido: {bank}")
    rooms = maps()
    slots = [bank * ROOMS_PER_BANK + index for index in range(ROOMS_PER_BANK)]
    data = {f"{side}PF{i}": [] for side in ("Left", "Right") for i in range(3)}
    for room in slots:
        # Bancos sem salas tambem mantem os mesmos enderecos de codigo e tabelas.
        rows = rooms[room] if room < len(rooms) else ["#" * WIDTH] * HEIGHT
        for row in rows:
            bits = [int(cell == "#") for cell in row]
            for side, half in (("Left", bits[:20]), ("Right", bits[20:])):
                for i, value in enumerate(pack_half(half)):
                    data[f"{side}PF{i}"].append(value)
    data["ObjectRows"] = [OBJECT_GLYPHS[OBJECT_TYPES[room]][y - 34]
                          if room < len(rooms) and 34 <= y < 38 else 0
                          for room in slots for y in range(HEIGHT)]
    # Bit 0 de COLUP0 nao muda a cor NTSC: ele marca a faixa da porta.
    # A cor-base persiste fora da faixa para a primeira scanline de M0 em x=0.
    data["GateRows"] = [
        ((0x46 if room in (4, 5) else 0x86) | int(20 <= y < 28))
        if room in (4, 5, 7, 8) and not 34 <= y < 38 else
        OBJECT_COLORS[OBJECT_TYPES[room]]
        if room < len(rooms) and 34 <= y < 38 else 0
        for room in slots for y in range(HEIGHT)
    ] + [0]
    pages, masks = [], []
    for column in range(WIDTH):
        packed = pack_half([int(i == column % 20) for i in range(20)])
        index = next(i for i, value in enumerate(packed) if value)
        side = "Left" if column < 20 else "Right"
        pages.append(f">{side}PF{index}")
        masks.append(packed[index])
    metadata = {
        "RoomStarts": [(room % 2) * HEIGHT for room in range(len(rooms))],
        "RoomEnds": [(room % 2 + 1) * HEIGHT for room in range(len(rooms))],
        "RoomBanks": [room // 2 for room in range(len(rooms))],
        "GateBits": [0, 0, 0, 0, 2, 2, 0, 4, 4],
        "GateColumns": [39, 39, 39, 39, 39, 0, 39, 39, 0],
        "GateCoordinates": [166, 166, 166, 166, 166, 4, 166, 166, 4],
        "ObjectTypes": list(OBJECT_TYPES),
        "ObjectColors": [OBJECT_COLORS[kind] for kind in OBJECT_TYPES],
        "CollisionPages": pages, "CollisionMasks": masks,
    }
    for i, direction in enumerate(("Left", "Right", "Up", "Down")):
        metadata[f"Exit{direction}"] = [exits[i] for exits in EXITS]
    tails = {
        "LeftPF0": ("SFX_ROUTINES", "WORLD_COLLECT"),
        "LeftPF1": ("SFX_DATA", "MUSIC_ENVELOPES", "WORLD_EFFECTS"),
        "LeftPF2": ("HUD_DIGITS", "RoomStarts", "RoomEnds", "RoomBanks",
                    "GateBits", "GateColumns"),
        "RightPF0": ("HUD_STATUS", "HUD_POPULATE", "GateCoordinates",
                     "ObjectTypes", "ObjectColors"),
        "RightPF1": ("HUD_CAMERA", "WORLD_PREPARE"),
        "RightPF2": ("HUD_POINTERS", "WORLD_SWITCH"),
        "ObjectRows": ("HUD_DRAW", "WORLD_FINISH"),
        "GateRows": ("CollisionPages", "CollisionMasks", "ExitLeft", "ExitRight",
                     "ExitUp", "ExitDown"),
    }
    lines = ["; Gerado por scripts/rooms.py; nao editar.",
             f"ROOM_COUNT = {len(rooms)}", f"ROW_REPEAT = {REPEAT}"]

    def emit(name, values):
        lines.append(name)
        for offset in range(0, len(values), 12):
            lines.append("        byte " + ",".join(
                f"${v:02X}" if isinstance(v, int) else v
                for v in values[offset:offset + 12]))

    for name, values in data.items():
        lines.append("        align 256")
        emit(name, values)
        for tail in tails[name]:
            if tail in metadata:
                emit(tail, metadata[tail])
            else:
                lines.append(f"        {tail}")
        lines.extend((f"        if * > {name}+$100", "        err", "        endif"))
    destination.write_text("\n".join(lines) + "\n")
