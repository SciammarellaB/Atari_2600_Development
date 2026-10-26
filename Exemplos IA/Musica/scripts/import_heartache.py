"""Importa a referencia MIDI de Revle para uma reducao de Heartache em duas vozes.

Uso opcional: PYTHONPATH=.tools/python python3 scripts/import_heartache.py arquivo.mid
Requer mido==1.3.3 somente para reimportacao. O build usa o JSON salvo, sem MIDI.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def convert(path):
    import mido

    raw = path.read_bytes()
    midi = mido.MidiFile(path)
    expected = {1: "Synth Lead", 2: "Synth", 3: "Synth Bass", 5: "Oboe",
                7: "Trumpet", 11: "Flute"}
    tempo = [m.tempo for track in midi.tracks for m in track if m.type == "set_tempo"]
    if tempo != [251077] or midi.ticks_per_beat != 1000:
        raise ValueError("Referencia inesperada: esperado MIDI de Revle, PPQ 1000 e tempo 251077")
    tracks = {}
    for index, name in expected.items():
        if midi.tracks[index].name != name:
            raise ValueError(f"Trilha {index}: esperado {name}")
        tick, active, events = 0, {}, []
        for message in midi.tracks[index]:
            tick += message.time
            if message.type == "note_on" and message.velocity:
                active.setdefault(message.note, []).append(tick)
            elif message.type == "note_off" or (message.type == "note_on" and not message.velocity):
                if active.get(message.note):
                    start = active[message.note].pop(0)
                    first = round(start / 500)
                    end = max(first + 1, round(tick / 500))
                    events.append((first, end, message.note, start))
        tracks[index] = events

    voices, previous = [[], []], [None, None]
    for step in range(864):
        for channel in (0, 1):
            selected, source = None, None
            for index in ((5, 1, 7, 11, 2) if channel == 0 else (3,)):
                sounding = [event for event in tracks[index] if event[0] <= step < event[1]]
                if sounding:
                    selected = (max if channel == 0 else min)(sounding, key=lambda event: event[2])
                    source = index
                    break
            key = (source, selected) if selected else None
            if selected:
                shift = 24 if channel == 0 and source in (1, 2) else 12 if channel == 0 and source == 7 else 0
                note = selected[2] + shift
                lower, upper = (70, 93) if channel == 0 else (53, 64)
                while note < lower:
                    note += 12
                while note > upper:
                    note -= 12
                value = -1 if key == previous[channel] else note
            else:
                value = None
            voices[channel].append(value)
            previous[channel] = key

    result = {
        "title": "Heartache", "composer": "Toby Fox", "reference_sequencer": "Revle",
        "reference_url": "https://www.vgmusic.com/file/d56bcf22fbbf1c035d0065bd7d90334c.html",
        "reference_sha256": sha256(raw).hexdigest(), "tempo_us": tempo[0],
        "steps_per_bar": 12, "bar_count": 72,
        "notation": "MIDI pitch after octave adaptation; null=rest; -1=hold previous note",
    }
    for name, voice in zip(("lead", "bass"), voices):
        patterns = [tuple(voice[i:i + 12]) for i in range(0, len(voice), 12)]
        pool = list(dict.fromkeys(patterns))
        result[f"{name}_patterns"] = pool
        result[f"{name}_order"] = [pool.index(pattern) for pattern in patterns]
    destination = ROOT / "music/heartache.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Heartache: {len(voices[0])} passos, {len(result['lead_patterns'])} motivos de melodia, "
          f"{len(result['bass_patterns'])} de baixo")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("midi", type=Path)
    convert(parser.parse_args().midi)
