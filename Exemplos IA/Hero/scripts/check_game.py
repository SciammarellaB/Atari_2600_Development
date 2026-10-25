"""Executa a ROM no py65: instrucoes reais, entradas e prazos do kernel.

O barramento abaixo modela RAM, ROM, WSYNC e timer; nao renderiza pixels,
nao reproduz audio e nao substitui a observacao no Stella/hardware.
Instale a dependencia somente aqui: pip install --target .tools/python py65==1.2.0
"""

from pathlib import Path
import re

from py65.devices.mpu6502 import MPU


# Os simbolos permitem observar a RAM e chamar rotinas montadas. O teste nao
# reimplementa a logica do jogo; a CPU executa os bytes gerados pelo DASM.
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/01-jogos/01-hero"
SYMBOLS = {}
for line in (OUTPUT / "main.sym").read_text().splitlines():
    match = re.match(r"^(\w+)\s+([0-9a-fA-F]{4})\s", line)
    if match:
        SYMBOLS[match[1]] = int(match[2], 16)


class Bus:
    """Barramento 6507: 13 bits de endereco e espelhos da RAM do RIOT."""

    def __init__(self):
        self.rom = (OUTPUT / "main.bin").read_bytes()
        self.ram = bytearray(256)
        self.joystick = 255
        self.switches = 255
        self.fire = 128
        self.cpu = None
        self.pending = []
        self.events = []
        self.timer_value = 0
        self.timer_start = 0

    def __getitem__(self, address):
        """Entradas ativas em zero; INTIM decresce conforme os ciclos da CPU."""
        address &= 0x1FFF
        if address & 0x1000:
            return self.rom[address & 0xFFF]
        if not address & 0x80:
            return self.fire if address & 0xF == 0xC else 0
        if not address & 0x200:
            return self.ram[address & 255]
        if address == 0x280:
            return self.joystick
        if address == 0x282:
            return self.switches
        if address == 0x284:
            # O primeiro decremento vem um ciclo depois do STA TIM64T.
            # A leitura absoluta termina quatro ciclos depois de seu inicio.
            elapsed = self.cpu.processorCycles + 4 - self.timer_start
            ticks = (elapsed + 63) // 64
            if ticks <= self.timer_value:
                return self.timer_value - ticks
            zero_at = (self.timer_value - 1) * 64 + 1
            return (-(elapsed - zero_at - 63)) & 255
        return 0

    def __setitem__(self, address, value):
        """Aplica perifericos depois do step, quando o STA termina."""
        address &= 0x1FFF
        if address & 0x1000:
            raise AssertionError("Escrita indevida na ROM")
        if address & 0x80 and not address & 0x200:
            self.ram[address & 255] = value
        else:
            self.pending.append((address, value))


class Machine:
    """Executa instrucoes, contabiliza WSYNC e oferece comandos de joystick."""

    def __init__(self):
        self.bus = Bus()
        self.cpu = MPU(memory=self.bus, pc=None)
        self.bus.cpu = self.cpu
        self.until("Frame")

    def step(self):
        """WSYNC estende o tempo ate o inicio da linha seguinte de 76 ciclos."""
        self.cpu.step()
        cycle = self.cpu.processorCycles
        for address, value in self.bus.pending:
            if address == 0x296:
                self.bus.timer_start = cycle
                self.bus.timer_value = value
            elif not address & 0x80:
                register = address & 0x3F
                self.bus.events.append((cycle, register, value))
                if register == 2:
                    self.cpu.processorCycles = ((cycle + 75) // 76) * 76
        self.bus.pending.clear()

    def until(self, label):
        """Limita a execucao para transformar loops travados em falhas claras."""
        for _ in range(20000):
            if self.cpu.pc == SYMBOLS[label]:
                return
            self.step()
        raise AssertionError(f"Execucao nao chegou a {label}")

    def frame(self):
        """Um quadro precisa ter 262 linhas, inclusive em eventos do jogo."""
        self.bus.events.clear()
        before = self.cpu.processorCycles
        self.step()
        self.until("Frame")
        elapsed = self.cpu.processorCycles - before
        assert elapsed == 262 * 76, (elapsed / 76, self.get("HeroX"),
                                    self.get("HeroY"), self.get("Room"))

    def get(self, label):
        return self.bus[SYMBOLS[label]]

    def set(self, label, value):
        self.bus[SYMBOLS[label]] = value

    def call(self, label):
        """Empilha retorno artificial para testar uma rotina isolada da ROM."""
        before = self.cpu.processorCycles
        self.cpu.stPushWord(SYMBOLS["Frame"] - 1)
        self.cpu.pc = SYMBOLS[label]
        self.until("Frame")
        # Uma chamada isolada nao representa um quadro. Conservamos a fase
        # horizontal para poder retomar posteriormente a verificacao de video.
        self.cpu.processorCycles = before

    def drive(self, frames, joystick=255, fire=False):
        """Mantem controles por N quadros, verificando timing em todos eles."""
        self.bus.joystick = joystick
        self.bus.fire = 0 if fire else 128
        for _ in range(frames):
            self.frame()

    def reach(self, label, expected, limit=250, joystick=255, fire=False):
        """Joga ate atingir um estado; falha se o trajeto nao for possivel."""
        for _ in range(limit):
            if self.get(label) == expected:
                return
            self.drive(1, joystick, fire)
            assert self.get("State") != 2, (label, "derrota inesperada")
        raise AssertionError((label, self.get(label), expected))


def check_kernel():
    """Confere regioes de video, prazos de escrita e variacoes de coordenadas."""
    machine = Machine()
    for _ in range(8):
        machine.frame()
        events = machine.bus.events
        blank = [(cycle, value) for cycle, reg, value in events if reg == 1]
        assert [value for _, value in blank] == [0, 2], blank
        assert (blank[1][0] - blank[0][0]) // 76 == 192, blank
        move = next(cycle for cycle, reg, _ in events if reg == 0x2A)
        clear = next(cycle for cycle, reg, _ in events if reg == 0x2B)
        # Motion regs devem permanecer estaveis enquanto HMOVE esta em curso.
        assert move + 24 <= clear < blank[0][0], (move, clear)
        start_line = blank[0][0] // 76 + 16
        # O kernel deve atualizar PF1 antes de X=16 e PF2 antes de X=48.
        for register, deadline in ((0x1B, 6), (0x1C, 38), (0x1D, 13),
                                   (0x06, 20), (0x0E, 26), (0x0F, 32)):
            writes = [(cycle, value) for cycle, reg, value in events
                      if reg == register and start_line <= cycle // 76
                      < start_line + 176]
            assert len(writes) == 88, (register, len(writes))
            assert all(cycle % 76 <= deadline for cycle, _ in writes), (
                register, max(cycle % 76 for cycle, _ in writes))
        # O laser inativo jamais pode deixar ENAM0 ligado na caverna.
        assert all(value == 0 for cycle, reg, value in events
                   if reg == 0x1D and start_line <= cycle // 76 < start_line + 176)

    # Varre a amplitude horizontal e vertical, incluindo a transicao de bandas.
    # State=Won congela a logica para observar apenas os caminhos do kernel.
    machine.set("State", 1)
    for x in range(20, 133):
        machine.set("HeroX", x)
        machine.set("ShotX", x)
        machine.set("HeroY", 8 + x % 65)
        machine.set("ShotY", 10 + x % 65)
        machine.frame()
    print("OK: 262 linhas; 192 visiveis; prazos de P0/P1/M0/PF; 113 posicoes")


def check_hero_colors():
    """Confere bitmap/cor por par e posicao de P1 nas janelas de troca."""
    machine = Machine()
    palette = [0x0E, 0x08, 0x2E, 0x3C, 0x86, 0x86, 0x84, 0x04]
    for room in (0, 1):
        machine.set("Room", room)
        machine.call("LoadRoom")
        machine.set("State", 1)
        for hero_y in range(8, 80):
            for facing in (0, 8):
                machine.set("HeroY", hero_y)
                machine.set("HeroX", 20 if facing else 132)
                machine.set("Facing", facing)
                machine.set("Clock", hero_y & 7)
                machine.set("ShotY", hero_y + 2)
                machine.set("BombTimer", 60)
                # A carga fica no par 30: varremos o heroi dentro e fora dela,
                # incluindo o caminho longo HeroBlank + bomba habilitada.
                machine.set("BombY", 24)
                machine.frame()
                events = machine.bus.events
                first = next(cycle // 76 for cycle, reg, value in events
                             if reg == 1 and value == 0) + 16
                cave = [(cycle, reg, value) for cycle, reg, value in events
                        if first <= cycle // 76 < first + 176]
                for register in (0x1B, 0x06, 0x1D):
                    rows = [(cycle, value) for cycle, reg, value in cave
                            if reg == register]
                    assert len(rows) == 88, (room, hero_y, register, len(rows))
                    for pair, (cycle, value) in enumerate(rows):
                        assert cycle // 76 == first + pair * 2
                        offset = pair - hero_y
                        if register == 0x06:
                            expected = palette[offset] if 0 <= offset < 8 else 0x2E
                            assert cycle % 76 <= 20
                        elif register == 0x1D:
                            expected = 2 if pair == hero_y + 2 else 0
                            value &= 2  # ENAM0 ignora os demais bits escritos.
                        else:
                            expected = (machine.bus[SYMBOLS["HeroPixels"] + offset]
                                        if 0 <= offset < 8 else 0)
                        assert value == expected, (room, hero_y, pair, register,
                                                   value, expected)
                assert next(value for _, reg, value in events if reg == 0x0B) == facing
                # Mesmo reset horizontal efetivo de P1 antes/depois da mudanca:
                # o pulso grosso mais o ajuste fino deve corresponder a X+63.
                motion = 0
                targets = iter((120, 56, 128))
                for cycle, register, value in cave:
                    if register == 0x21:
                        motion = value >> 4
                        if motion >= 8:
                            motion -= 16
                    elif register == 0x11:
                        target = next(targets)
                        assert cycle % 76 * 3 - motion == target + 63, (
                            target, cycle % 76, motion)
    print("OK: cores/bitmap do heroi em 72 alturas, dois lados e duas salas; P1 alinhado")


def check_no_flicker():
    """Cada bitmap completo deve aparecer em cada quadro, sem rodizio de P1."""
    machine = Machine()
    for room in (0, 1):
        machine.set("Room", room)
        machine.call("LoadRoom")
        for _ in range(8):
            machine.frame()
            events = machine.bus.events
            first = next(cycle // 76 for cycle, reg, value in events
                         if reg == 1 and value == 0) + 16
            pixels = {((cycle // 76 - first) // 2): value
                      for cycle, reg, value in events
                      if reg == 0x1C and first <= cycle // 76 < first + 176}
            actors = [(16, "BatBitmap"), (40, "FuelBitmap"), (64, "GemBitmap")]
            if room:
                actors.append((72, "MinerBitmap"))
            for y, label in actors:
                expected = [machine.bus[SYMBOLS[label] + row] for row in range(8)]
                assert [pixels[y + row] for row in range(8)] == expected, (
                    room, label, pixels)
        # Testa laser e bomba na mesma altura, incluindo o pior caminho de A.
        machine.set("State", 1)
        machine.set("BombTimer", 60)
        machine.set("BombY", 24)
        machine.set("BombX", 56)
        machine.set("ShotY", 30)
        machine.set("HeroY", 28)
        for _ in range(4):
            machine.frame()
            active = [(cycle, value) for cycle, reg, value in machine.bus.events
                      if reg == 0x1E and value]
            assert len(active) == 1 and active[0][1] == 2, active
        machine.set("State", 0)
    print("OK: morcego/bateria/cristal/mineiro completos em todos os quadros; M1 ativo")


def check_map_and_controls():
    """Exercita espelhamento, teto, piso, voo, gravidade e parede removivel."""
    machine = Machine()
    # Este caso isola as rochas; contatos com inimigos sao testados abaixo.
    machine.set("EnemyAlive", 0)
    for x, y, solid in ((20, 8, False), (0, 8, True), (159, 8, True),
                         (20, 0, True), (76, 24, True), (80, 24, True),
                         (63, 24, False), (96, 24, False), (40, 32, True),
                         (76, 80, False), (120, 80, True)):
        machine.set("PointX", x)
        machine.set("PointY", y)
        machine.call("SolidPoint")
        assert bool(machine.cpu.p & 1) == solid, (x, y)
    machine.drive(48)
    assert machine.get("HeroY") == 24
    machine.drive(60, 0x7F)
    assert machine.get("HeroX") == 56, machine.get("HeroX")
    machine.drive(40, 0xEF)
    assert machine.get("HeroY") == 8
    machine.drive(20, 0xBF)
    assert machine.get("HeroX") == 36
    machine.call("DestroyWall")
    machine.set("PointX", 76)
    machine.set("PointY", 24)
    machine.call("SolidPoint")
    assert not machine.cpu.p & 1
    print("OK: mapa espelhado; teto/piso; voo/gravidade; parede bloqueia e abre")


def check_laser():
    """Oito impactos abrem a parede; um acerto elimina o morcego."""
    machine = Machine()
    machine.set("HeroX", 56)
    machine.set("HeroY", 24)
    machine.drive(7, fire=True)
    assert machine.get("WallAlive") == 1 and machine.get("WallHits") == 1
    machine.drive(1, fire=True)
    assert machine.get("WallAlive") == 0
    assert machine.get("ShotY") == 128
    machine.set("HeroX", 24)
    machine.set("HeroY", 16)
    machine.set("EnemyX", 40)
    machine.set("Clock", 0)
    machine.reach("EnemyAlive", 0, limit=10, fire=True)
    # Um disparo existente conserva sua direcao mesmo quando o heroi vira.
    machine.set("Facing", 0)
    machine.set("ShotY", 128)
    machine.call("UpdateLaser")
    shot_x = machine.get("ShotX")
    machine.set("Facing", 8)
    machine.call("UpdateLaser")
    assert machine.get("ShotX") == shot_x + 3
    print("OK: laser horizontal; oito impactos na parede; morcego; direcao capturada")


def check_items_and_endings():
    """Coleta e limites de energia; derrotas e reinicio por novo clique/reset."""
    machine = Machine()
    machine.set("HeroX", 120)
    machine.set("HeroY", 40)
    machine.set("Energy", 50)
    machine.call("CollectItems")
    assert machine.get("Energy") == 64 and machine.get("FuelAlive") == 0
    machine.set("Energy", 30)
    machine.call("CollectItems")
    assert machine.get("Energy") == 30
    machine.set("HeroX", 56)
    machine.set("HeroY", 64)
    machine.call("CollectItems")
    machine.call("CollectItems")
    assert machine.get("Gems") == 1 and machine.get("GemAlive") == 0
    machine.set("Energy", 1)
    machine.set("EnergyClock", 31)
    machine.frame()
    assert machine.get("State") == 2
    machine.bus.fire = 0
    machine.call("UpdateGame")
    assert machine.get("State") == 2
    machine.bus.fire = 128
    machine.call("UpdateGame")
    machine.bus.fire = 0
    machine.call("UpdateGame")
    assert machine.get("State") == 0 and machine.get("Energy") == 64
    machine.set("HeroX", 56)
    machine.set("HeroY", 16)
    machine.set("Clock", 0)
    machine.set("EnemyX", 56)
    machine.bus.fire = 128
    machine.frame()
    assert machine.get("State") == 2
    machine.bus.switches = 254
    machine.frame()
    assert machine.get("State") == 0 and machine.get("HeroX") == 24
    print("OK: coleta unica; energia limitada; esgotamento; contato inimigo; reinicios")


def check_bomb():
    """Bomba exige apoio/novo comando; pavio, consumo e autoexplosao funcionam."""
    machine = Machine()
    machine.drive(1, 0xDF)
    assert machine.get("BombTimer") == 0 and machine.get("Bombs") == 6
    machine.set("HeroX", 56)
    machine.set("HeroY", 24)
    machine.drive(1)
    machine.drive(1, 0xDF)
    assert machine.get("BombTimer") == 60 and machine.get("Bombs") == 5
    machine.drive(59, 0xDF)
    assert machine.get("State") == 0 and machine.get("BombTimer") == 1
    machine.drive(1, 0xDF)
    assert machine.get("State") == 2 and machine.get("WallAlive") == 0
    assert machine.get("Bombs") == 5
    print("OK: apoio no chao; pavio de 60 quadros; uma bomba por comando; autoexplosao")


def open_passage(machine):
    """Joga uma demoliçao real: anda, planta, recua e espera o pavio terminar."""
    machine.reach("HeroY", 24)
    machine.reach("HeroX", 56, joystick=0x7F)
    machine.drive(1, 0xDF)
    assert machine.get("BombTimer") == 60
    machine.reach("HeroX", 24, joystick=0xBF)
    machine.reach("WallAlive", 0, limit=65)
    assert machine.get("State") == 0


def check_complete_route():
    """Percorre as duas salas por joystick, coleta cristais e resgata o mineiro."""
    machine = Machine()
    open_passage(machine)
    machine.reach("HeroX", 76, joystick=0x7F)
    machine.reach("HeroY", 64)
    machine.reach("HeroX", 32, joystick=0xBF)
    machine.reach("Gems", 1)
    machine.reach("HeroX", 76, joystick=0x7F)
    machine.reach("Room", 1)
    assert machine.get("Bombs") == 5 and machine.get("Gems") == 1
    open_passage(machine)
    machine.reach("HeroX", 76, joystick=0x7F)
    machine.reach("HeroY", 48)
    machine.reach("HeroX", 32, joystick=0xBF)
    machine.reach("HeroY", 64)
    machine.reach("HeroX", 56, joystick=0x7F)
    machine.reach("Gems", 2, joystick=0xEF)
    machine.reach("State", 1, joystick=0x7F)
    assert machine.get("Bombs") == 4 and machine.get("Room") == 1
    machine.drive(2)
    assert machine.get("Background") == 0xC2
    machine.drive(1, fire=True)
    assert machine.get("State") == 0 and machine.get("Gems") == 0
    print("OK: trajeto jogavel nas duas salas; duas bombas; dois cristais; resgate; reinicio")


# Cada falha interrompe make test. Apenas o modelo de CPU/timing e validado
# aqui; pixels, HMOVE, qualidade do flicker e som exigem Stella ou Atari real.
if __name__ == "__main__":
    check_kernel()
    check_hero_colors()
    check_no_flicker()
    check_map_and_controls()
    check_laser()
    check_items_and_endings()
    check_bomb()
    check_complete_route()
