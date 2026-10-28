"""Testa bombas e coletaveis executando as rotinas da ROM no py65.

Importa apenas o barramento e a maquina do teste de raster. Nao monta a ROM
nem verifica os pixels fisicos do TIA; requer build/main.bin e main.sym atuais.
"""
from check_shooter import Machine


def state(machine, *names):
    return tuple(machine.get(name) for name in names)


def call(machine, label, lines):
    """Confere tambem os slots fixos de WSYNC e o balanceamento da pilha."""
    machine.bus.events.clear()
    machine.call(label)
    sync = [cycle // 76 for cycle, register, _ in machine.bus.events if register == 2]
    assert len(sync) == lines, (label, sync)
    assert sync == list(range(sync[0], sync[0] + lines)), (label, sync)
    assert machine.cpu.sp == 0xFF, (label, machine.cpu.sp)


def bomb(machine):
    call(machine, "UpdateBomb", 4)


def pickup(machine):
    call(machine, "UpdatePickup", 5)


def hold(machine, frames):
    machine.bus.fire = 0
    for _ in range(frames):
        bomb(machine)


def check_initial_state():
    m = Machine()
    assert state(m, "Lives", "BombCount", "ShotLevel", "ShotStep") == (3, 0, 0, 3)
    assert state(m, "FireHold", "BombLatch", "BombActive", "FlashTimer", "BlastPulse") == (0,) * 5
    assert state(m, "PickupType", "PickupWait", "NextPickup") == (0, 120, 1)
    assert state(m, "ScoreHi", "ScoreMid", "ScoreLo") == (0, 0, 0)
    print("OK: estado inicial de vidas, bombas, tiro, coletaveis e pontos")


def check_bomb_button():
    m = Machine()
    m.set(BombCount=3)
    hold(m, 59)
    assert state(m, "FireHold", "BombLatch", "BombCount", "BombActive") == (59, 0, 3, 0)
    bomb(m)
    assert state(m, "FireHold", "BombLatch", "BombCount", "BombActive", "BombX", "BombY") == (60, 1, 2, 2, 76, 64)
    bomb(m)
    assert state(m, "FireHold", "BombLatch", "BombCount", "BombY") == (60, 1, 2, 60)
    hold(m, 300)
    assert state(m, "FireHold", "BombLatch", "BombCount", "BombActive") == (60, 1, 2, 0)
    m.bus.fire = 0x80
    bomb(m)
    assert state(m, "FireHold", "BombLatch") == (0, 0)
    hold(m, 59)
    assert m.get("BombCount") == 2
    bomb(m)
    assert state(m, "BombCount", "BombActive") == (1, 2)

    # Uma tentativa sem carga nao se repete se uma carga chegar com o botao preso.
    m = Machine()
    hold(m, 60)
    assert state(m, "FireHold", "BombLatch", "BombActive") == (60, 1, 0)
    m.set(BombCount=1)
    hold(m, 70)
    assert state(m, "BombCount", "BombActive") == (1, 0)
    m.bus.fire = 0x80
    bomb(m)
    hold(m, 60)
    assert state(m, "BombCount", "BombActive") == (0, 2)

    # Uma bomba ativa tambem trava a tentativa, mesmo depois de desaparecer.
    m = Machine()
    m.set(FireHold=59, BombCount=2, BombActive=2, BombX=76, BombY=40)
    hold(m, 1)
    assert state(m, "FireHold", "BombLatch", "BombCount", "BombY") == (60, 1, 2, 36)
    hold(m, 80)
    assert state(m, "BombCount", "BombActive", "BombLatch") == (2, 0, 1)
    # Soltar antes do limiar exige uma nova contagem inteira.
    m = Machine()
    m.set(BombCount=1)
    hold(m, 59)
    m.bus.fire = 0x80
    bomb(m)
    hold(m, 59)
    assert state(m, "FireHold", "BombCount", "BombActive") == (59, 1, 0)
    bomb(m)
    assert state(m, "BombCount", "BombActive") == (0, 2)
    print("OK: limiares 59/60/61, uma tentativa por pressao, soltura e bloqueios")


def check_bomb_flight_and_flash():
    for x, y in ((8, 4), (144, 72), (76, 68)):
        m = Machine()
        m.set(XPos=x, YPos=y, BombCount=1, FireHold=59)
        hold(m, 1)
        assert state(m, "BombX", "BombY", "BombActive") == (x, y - 4, 2)
        m.set(XPos=76 if x == 8 else 8, YPos=4)
        m.bus.fire = 0x80
        for expected in range(y - 8, -1, -4):
            bomb(m)
            assert state(m, "BombX", "BombY", "BombActive") == (x, expected, 2)
        # Y=0 ainda e visivel; a chamada seguinte detona sem wrap para 252.
        assert m.get("BombY") == 0
        m.set(ShotActive=0x80, PickupType=3, PickupWait=7)
        bomb(m)
        assert state(m, "BombActive", "ShotActive", "PickupType") == (0, 0, 0)
        assert state(m, "FlashTimer", "BlastPulse", "PickupWait") == (8, 1, 120)
        pickup(m)
        assert state(m, "PickupType", "PickupWait", "CollectedType") == (0, 120, 0)
        for timer in range(7, -1, -1):
            bomb(m)
            assert state(m, "FlashTimer", "BlastPulse") == (timer, 0)
        bomb(m)
        assert m.get("FlashTimer") == 0
    print("OK: origem, voo independente, topo, limpeza da area, pulso e flash de oito quadros")


def check_pickup_lifecycle():
    m = Machine()
    m.set(XPos=40, YPos=72)
    for remaining in range(119, 0, -1):
        pickup(m)
        assert state(m, "PickupType", "PickupWait") == (0, remaining)
    pickup(m)
    assert state(m, "PickupType", "PickupX", "PickupY", "PickupTick", "NextPickup") == (1, 40, 0, 0, 2)
    m.set(XPos=144)
    for index in range(1, 13):
        pickup(m)
        assert state(m, "PickupX", "PickupY") == (40, index // 2)
        assert m.get("PickupTick") & 1 == index % 2

    m = Machine()
    for expected in (1, 2, 3, 1, 2, 3):
        m.set(PickupType=0, PickupWait=1)
        pickup(m)
        assert state(m, "PickupType", "PickupY", "PickupTick", "NextPickup") == (expected, 0, 0, expected % 3 + 1)

    # A coleta ja vale no nascimento quando a nave esta perto do topo.
    m = Machine()
    m.set(YPos=4, PickupWait=1)
    pickup(m)
    assert state(m, "PickupType", "PickupWait", "BombCount", "CollectedType") == (0, 120, 1, 1)

    for kind in (1, 2, 3):
        m = Machine()
        m.set(XPos=144, YPos=4, PickupType=kind, PickupX=8, PickupY=83, PickupTick=0)
        pickup(m)
        assert state(m, "PickupType", "PickupY") == (kind, 83)
        pickup(m)
        assert state(m, "PickupType", "PickupWait") == (0, 120)
        pickup(m)
        assert state(m, "PickupType", "PickupWait") == (0, 119)

    # O pulso impede movimento e coleta, inclusive com as caixas sobrepostas.
    m = Machine()
    m.set(BlastPulse=1, PickupType=1, PickupX=76, PickupY=68, PickupTick=1,
          PickupWait=17, CollectedType=3, BombCount=0)
    pickup(m)
    assert state(m, "PickupType", "PickupY", "PickupTick", "PickupWait", "BombCount", "CollectedType") == (1, 68, 1, 17, 0, 0)
    print("OK: espera de 120 quadros, ciclo dos tipos, queda, independencia, saida e pulso")


def check_pickup_collisions():
    m = Machine()
    cases = 0
    for kind in (1, 2, 3):
        for dx in range(-8, 9):
            for dy in range(-8, 9):
                m.set(XPos=76, YPos=44, PickupType=kind, PickupX=76 + dx,
                      PickupY=44 + dy, PickupTick=0, PickupWait=0, BlastPulse=0,
                      CollectedType=3, BombCount=5, Lives=4, ShotLevel=1, ShotStep=4,
                      ScoreHi=0x12, ScoreMid=0x34, ScoreLo=0x56)
                pickup(m)
                hit = abs(dx) <= 7 and abs(dy) <= 7
                assert m.get("PickupType") == (0 if hit else kind), (kind, dx, dy)
                assert m.get("CollectedType") == (kind if hit else 0), (kind, dx, dy)
                assert m.get("BombCount") == 5 + int(hit and kind == 1)
                assert m.get("Lives") == 4 + int(hit and kind == 2)
                assert m.get("ShotLevel") == 1 + int(hit and kind == 3)
                assert m.get("ShotStep") == 4 + int(hit and kind == 3)
                if hit:
                    assert m.get("PickupWait") == 120
                assert state(m, "ScoreHi", "ScoreMid", "ScoreLo") == (0x12, 0x34, 0x56)
                cases += 1

    # Casos nas bordas e com grandes distancias evitam falsos hits por wrap.
    for x, y, px, py, hit in ((8, 4, 1, 0, True), (144, 72, 151, 79, True),
                              (8, 4, 0, 4, False), (144, 72, 152, 72, False),
                              (8, 72, 152, 72, False), (144, 4, 0, 4, False),
                              (76, 72, 76, 83, False)):
        m.set(XPos=x, YPos=y, PickupType=1, PickupX=px, PickupY=py,
              PickupTick=0, BlastPulse=0, BombCount=0)
        pickup(m)
        assert m.get("BombCount") == int(hit), (x, y, px, py)

    # A colisao considera a posicao ja movida neste quadro.
    for py, hit in ((36, True), (51, False)):
        m.set(XPos=76, YPos=44, PickupType=1, PickupX=76, PickupY=py,
              PickupTick=1, BombCount=0, BlastPulse=0)
        pickup(m)
        assert m.get("BombCount") == int(hit), py
    print(f"OK: {cases} colisoes AABB, bordas, ausencia de wrap e movimento antes da coleta")


def check_caps_and_shot():
    m = Machine()
    for kind, name, start, maximum in ((1, "BombCount", 8, 9), (2, "Lives", 8, 9),
                                       (3, "ShotLevel", 2, 3)):
        m.set(**{name: start}, ShotStep=5)
        for _ in range(4):
            m.set(PickupType=kind, PickupX=76, PickupY=68, PickupTick=0)
            pickup(m)
            assert m.get(name) == maximum
            if kind == 3:
                assert m.get("ShotStep") == 6
    m = Machine()
    for expected in (1, 2, 3, 3):
        m.set(PickupType=3, PickupX=76, PickupY=68, PickupTick=0)
        pickup(m)
        assert state(m, "ShotLevel", "ShotStep") == (expected, 3 + expected)
    for level in range(4):
        m = Machine()
        m.set(ShotLevel=level, ShotStep=3 + level)
        m.bus.fire = 0
        m.call("UpdateShot")
        assert state(m, "ShotActive", "ShotX", "ShotY") == (0x80, 79, 65)
        for sy in range(84):
            m.set(ShotActive=0x80, ShotX=79, ShotY=sy, XPos=8)
            m.call("UpdateShot")
            assert m.get("ShotX") == 79
            assert m.get("ShotActive") == (0x80 if sy >= 3 + level else 0)
            if sy >= 3 + level:
                assert m.get("ShotY") == sy - 3 - level

    # O mesmo botao dispara tiros normais durante a contagem da bomba.
    m = Machine()
    m.set(BombCount=1)
    m.bus.fire = 0
    spawned = 0
    for frame in range(1, 61):
        was_active = m.get("ShotActive")
        m.call("UpdateShot")
        spawned += int(not was_active and m.get("ShotActive") != 0)
        bomb(m)
        assert m.get("BombCount") == (1 if frame < 60 else 0)
    assert spawned >= 2
    assert state(m, "ShotActive", "BombActive") == (0x80, 2)
    print("OK: limites 9/9/3, velocidade 3..6 e tiro normal independente da bomba")


if __name__ == "__main__":
    check_initial_state()
    check_bomb_button()
    check_bomb_flight_and_flash()
    check_pickup_lifecycle()
    check_pickup_collisions()
    check_caps_and_shot()
