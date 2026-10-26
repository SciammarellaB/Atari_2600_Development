"""Gera dados TIA de Heartache a partir da reducao musical salva em JSON."""

import json
from math import log2
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pitch(note):
    """Tom puro mais proximo: bit 5 seleciona AUDC=12; sem ele, AUDC=4."""
    target = 440 * 2 ** ((note - 69) / 12)
    choices = [(abs(1200 * log2((31400 / (division * (frequency + 1))) / target)),
                frequency | (32 if division == 6 else 0))
               for division in (2, 6) for frequency in range(32)]
    return min(choices)[1]


def score():
    data = json.loads((ROOT / "music/heartache.json").read_text())
    if data["steps_per_bar"] != 12 or data["bar_count"] != 72 or data["tempo_us"] != 251077:
        raise ValueError("Heartache: esperado 72 compassos x 12 passos, tempo 251077")
    for voice in ("lead", "bass"):
        pool, order = data[f"{voice}_patterns"], data[f"{voice}_order"]
        if len(order) != 72 or not pool or any(not 0 <= i < len(pool) for i in order):
            raise ValueError(f"Heartache: ordem invalida em {voice}")
        if any(len(pattern) != 12 for pattern in pool):
            raise ValueError(f"Heartache: motivos de {voice} devem ter 12 passos")
        if any(note is not None and (not isinstance(note, int) or note not in range(-1, 128))
               for pattern in pool for note in pattern):
            raise ValueError(f"Heartache: nota invalida em {voice}")
    return data


def generate(destination):
    data = score()
    lines = ["; Gerado por scripts/heartache.py. Fonte: music/heartache.json.",
             "; Heartache, Toby Fox; referencia MIDI sequenciada por Revle.",
             "HEART_BARS = 72", "HEART_STEPS = 12", "HEART_FRACTION = 136"]

    def emit(name, values):
        lines.append(name)
        for i in range(0, len(values), 12):
            lines.append("        byte " + ",".join(f"${v:02X}" if isinstance(v, int) else v
                                                   for v in values[i:i + 12]))

    for voice in ("lead", "bass"):
        prefix = "Heart" + voice.title()
        patterns = data[f"{voice}_patterns"]
        emit(prefix + "Order", data[f"{voice}_order"])
        labels = [f"{prefix}Pattern{i}" for i in range(len(patterns))]
        emit(prefix + "Lo", ["<" + label for label in labels])
        emit(prefix + "Hi", [">" + label for label in labels])
        for label, pattern in zip(labels, patterns):
            emit(label, [255 if n is None else 254 if n == -1 else pitch(n) for n in pattern])
    emit("HeartEnvelope", [6, 6, 5, 4, 4, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2])
    lines.append("HeartDataEnd")
    destination.write_text("\n".join(lines) + "\n")
