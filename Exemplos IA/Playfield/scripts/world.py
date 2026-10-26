"""Contrato do mundo: 15 salas, tres andares e progressao sem atalhos."""

NONE, OUTSIDE = 255, 254
ROOM_NAMES = ("Deposito", "Sala de servico", "Despensa", "Gerador",
              "Saguao", "Galeria", "Hall", "Biblioteca", "Escadaria",
              "Quarto", "Enfermaria", "Escritorio", "Patamar",
              "Sala de retratos", "Suite")
ROOM_IDS = ("B1", "B2", "B3", "B4", "T1", "T2", "T3", "T4", "T5",
            "A1", "A2", "A3", "A4", "A5", "A6")
FLOORS = (0,) * 4 + (1,) * 5 + (2,) * 6
# esquerda, direita, cima, baixo. OUTSIDE e apenas a saida final do Saguao.
# B4 e A6 tem uma unica entrada para que os bloqueios nao sejam contornados.
EXITS = ((NONE, 1, NONE, 2), (0, NONE, 6, NONE),
         (NONE, 3, 0, NONE), (2, NONE, NONE, NONE),
         (OUTSIDE, 5, NONE, NONE), (4, 6, NONE, NONE),
         (5, NONE, 7, 1), (NONE, NONE, 8, 6),
         (NONE, NONE, 12, 7), (NONE, 10, NONE, 12),
         (9, 11, NONE, NONE), (10, NONE, NONE, NONE),
         (NONE, 13, 9, 8), (12, 14, NONE, NONE),
         (13, NONE, NONE, NONE))
STAIRS = ((1, 2, 6), (6, 3, 1), (8, 2, 12), (12, 3, 8))
START_ROOM = 4
# As duas galerias compartilham desenho, piso, objeto vazio e colisao.
# A cor do PF e o estado da porta continuam proprios de cada sala logica.
ROOM_MAPS = tuple(range(13)) + (5, 13)
MAP_ROOMS = tuple(range(13)) + (14,)
ROOM_BANKS = tuple(slot // 2 for slot in ROOM_MAPS)

RED, GREEN, BLUE, SUITE, EXIT_OPEN, ESCAPED = 1, 2, 4, 8, 16, 128
GUN, GREEN_KEY, BLUE_KEY, GOLD_KEY = 1, 2, 4, 8
# 0 vazio,1 arma,2 balas,3 vida,4 switch vermelho,5/6/7 chaves,8 switch suite.
OBJECT_TYPES = (1, 0, 4, 6, 0, 0, 0, 2, 3, 2, 5, 8, 0, 0, 7)
OBJECT_COLORS = (0, 0x1C, 0x1C, 0xC4, 0x48, 0xC6, 0x86, 0x1C, 0x68)
GATE_BITS = (0, 0, GREEN, GREEN, EXIT_OPEN, 0, RED, RED,
             0, 0, BLUE, BLUE, 0, SUITE, SUITE)
GATE_DIRECTIONS = (NONE, NONE, 1, 0, 0, NONE, 2, 3,
                   NONE, NONE, 1, 0, NONE, 1, 0)
GATE_KEYS = (0, 0, GREEN_KEY, GREEN_KEY, GOLD_KEY, 0, 0, 0,
             0, 0, BLUE_KEY, BLUE_KEY, 0, 0, 0)
GATE_COLORS = (0x46, 0x46, 0xC6, 0xC6, 0x1C, 0x66, 0x46, 0x46,
               0x46, 0x46, 0x86, 0x86, 0x46, 0x66, 0x66)


def gate_rect(room):
    direction = GATE_DIRECTIONS[room]
    return ((0, 20, 1, 27), (38, 20, 39, 27),
            (19, 0, 20, 0), (19, 47, 20, 47))[direction] if direction != NONE else (255,) * 4


def visual_gate(room):
    """Uma porta pode existir no template e estar sempre aberta numa galeria."""
    slot = ROOM_MAPS[room]
    return next((r for r in range(len(EXITS)) if ROOM_MAPS[r] == slot and GATE_BITS[r]), room)
