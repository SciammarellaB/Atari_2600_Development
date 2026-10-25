import random
from pathlib import Path
r = random.Random(2600)
dados = bytes(r.randrange(256) for _ in range(32768))
Path('teste32k.bin').write_bytes(dados)
