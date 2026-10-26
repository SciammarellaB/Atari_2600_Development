"""Empacota quinze salas logicas em catorze templates de dois por banco F4."""
from mansion import (WIDTH, HEIGHT, scene, solid_rects, collision_map,
                     floor_colors, room_palette)
from world import (NONE, OUTSIDE, EXITS, ROOM_NAMES, ROOM_MAPS, MAP_ROOMS,
                   ROOM_BANKS, OBJECT_TYPES, OBJECT_COLORS, GATE_BITS,
                   GATE_DIRECTIONS, GATE_KEYS, GATE_COLORS, START_ROOM,
                   gate_rect, visual_gate)

REPEAT, BANK_COUNT, ROOMS_PER_BANK = 4, 8, 2
OBJECT_GLYPHS = ((0, 0, 0, 0), (0, 0x7E, 0x38, 0x30),
                 (0x66, 0xFF, 0xFF, 0x66), (0x18, 0x7E, 0x7E, 0x18),
                 (0xFF, 0xFF, 0xFF, 0xFF), (0x70, 0x50, 0x7E, 0x0A),
                 (0x70, 0x50, 0x7E, 0x0A), (0x70, 0x50, 0x7E, 0x0A),
                 (0xFF, 0xFF, 0xFF, 0xFF))


def maps():
    result = [scene(room) for room in range(len(EXITS))]
    opposite = (1, 0, 3, 2)
    for room, rows in enumerate(result):
        if len(rows) != HEIGHT or any(len(row) != WIDTH for row in rows):
            raise ValueError(f"Sala {room}: esperado {WIDTH} x {HEIGHT}")
        if any(set(row) - {"#", "."} for row in rows):
            raise ValueError(f"Sala {room}: use somente # e .")
        for direction, target in enumerate(EXITS[room]):
            if target not in (NONE, OUTSIDE) and (not 0 <= target < len(result) or
                    EXITS[target][opposite[direction]] != room):
                raise ValueError(f"Sala {room}: conexao invalida ou sem retorno")
        if any(rows[y][x] != "." for y in range(34, 38) for x in (8, 9)):
            raise ValueError(f"Sala {room}: mobiliario sobre o objeto")
        canonical = MAP_ROOMS[ROOM_MAPS[room]]
        if (rows != scene(canonical) or solid_rects(room) != solid_rects(canonical)
                or floor_colors(room) != floor_colors(canonical)
                or OBJECT_TYPES[room] != OBJECT_TYPES[canonical]):
            raise ValueError(f"Sala {room}: template compartilhado inconsistente")
    return result


def collision_maps():
    return [collision_map(room) for room in range(len(EXITS))]


def pack_half(bits):
    return (sum(bits[i] << (4 + i) for i in range(4)),
            sum(bits[4 + i] << (7 - i) for i in range(8)),
            sum(bits[12 + i] << i for i in range(8)))


def slot_rects(slot):
    room = MAP_ROOMS[slot]
    return [gate_rect(visual_gate(room))] + solid_rects(room)


def generate_bank_map(destination):
    destination.write_text("; Gerado por scripts/rooms.py; nao editar.\nRoomBanks\n"
                           "        byte " + ",".join(map(str, ROOM_BANKS)) + "\n")


def generate(destination, bank=0):
    if not 0 <= bank < 7:
        raise ValueError(f"Banco de cenario F4 invalido: {bank}")
    rooms = maps()
    slots = [bank * 2, bank * 2 + 1]
    data = {f"{side}PF{i}": [] for side in ("Left", "Right") for i in range(3)}
    for slot in slots:
        rows = rooms[MAP_ROOMS[slot]]
        for row in rows:
            bits = [int(cell == "#") for cell in row]
            for side, half in (("Left", bits[:20]), ("Right", bits[20:])):
                for i, value in enumerate(pack_half(half)):
                    data[f"{side}PF{i}"].append(value)
    data["ObjectRows"] = [OBJECT_GLYPHS[OBJECT_TYPES[MAP_ROOMS[slot]]][y - 34]
                          if 34 <= y < 38 else 0 for slot in slots for y in range(HEIGHT)]
    gate_rows = []
    for slot in slots:
        room = MAP_ROOMS[slot]
        gate = visual_gate(room)
        direction = GATE_DIRECTIONS[gate]
        for y in range(HEIGHT):
            marked = (20 <= y < 28 if direction in (0, 1) else
                      y == 0 if direction == 2 else y == 47 if direction == 3 else False)
            gate_rows.append(OBJECT_COLORS[OBJECT_TYPES[room]] if 34 <= y < 38 else
                             GATE_COLORS[gate] | int(marked))
    data["GateRows"] = gate_rows + [0]
    solids = [value for slot in slots for rect in slot_rects(slot) for value in rect]
    if len(solids) > 160:
        raise ValueError(f"Banco {bank}: footprints excedem 160 bytes")
    solids += [0] * (160 - len(solids))
    starts, ends = [], []
    for slot in ROOM_MAPS:
        start = len(slot_rects(slot - 1)) * 4 if slot % 2 else 0
        starts.append(start)
        ends.append(start + len(slot_rects(slot)) * 4)
    metadata = {
        "FloorColors": [c for slot in slots for c in floor_colors(MAP_ROOMS[slot])],
        "SolidRects": solids,
        "RoomStarts": [slot % 2 * HEIGHT for slot in ROOM_MAPS],
        "RoomEnds": [(slot % 2 + 1) * HEIGHT for slot in ROOM_MAPS],
        "RoomPFColors": [room_palette(room) for room in range(len(rooms))],
        "GateBits": list(GATE_BITS), "GateDirections": list(GATE_DIRECTIONS),
        "GateKeys": list(GATE_KEYS),
        "GateCoordinates": [4 if d == 0 else 162 if d == 1 else
                            86 if d in (2, 3) else 166 for d in GATE_DIRECTIONS],
        "ObjectTypes": list(OBJECT_TYPES),
        "ObjectColors": [OBJECT_COLORS[kind] for kind in OBJECT_TYPES],
        "RoomSolidStarts": starts, "RoomSolidEnds": ends,
    }
    for i, direction in enumerate(("Left", "Right", "Up", "Down")):
        metadata[f"Exit{direction}"] = [exits[i] for exits in EXITS]
    tails = {
        "LeftPF0": ("SFX_ROUTINES", "WORLD_COLLECT"),
        "LeftPF1": ("SFX_DATA", "MUSIC_ENVELOPES", "WORLD_EFFECTS"),
        "LeftPF2": ("FloorColors", "RoomStarts", "RoomEnds", "RoomPFColors"),
        "RightPF0": ("HUD_POPULATE", "GateCoordinates", "GateDirections",
                     "ObjectTypes", "COLLISION_BOX"),
        "RightPF1": ("HUD_CAMERA", "WORLD_PREPARE"),
        "RightPF2": ("SolidRects",),
        "ObjectRows": ("HUD_DRAW", "WORLD_FINISH", "WORLD_SWITCH"),
        "GateRows": ("RoomSolidStarts", "RoomSolidEnds", "ExitLeft", "ExitRight",
                     "ExitUp", "ExitDown", "GateBits", "GateKeys"),
    }
    lines = ["; Gerado por scripts/rooms.py; nao editar.", f"ROOM_COUNT = {len(rooms)}",
             f"START_ROOM = {START_ROOM}", f"ROW_REPEAT = {REPEAT}"]
    def emit(name, values):
        lines.append(name)
        for offset in range(0, len(values), 12):
            lines.append("        byte " + ",".join(f"${v:02X}" for v in values[offset:offset + 12]))
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
