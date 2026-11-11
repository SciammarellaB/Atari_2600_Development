; Banco 0: colisoes e resultados de combate. Sempre 11 WSYNC.
UpdateCombatBank
    sta WSYNC               ; 1: tiro contra o intervalo horizontal do chefe
    lda #0
    sta HitBoss
    sta Touch
    sta PlayerHit
    sta EnemyTouch
    lda GameState
    bne ShotHorizontalDone
    lda ShotActive
    beq ShotHorizontalDone
    lda ShotX
    clc
    adc #1
    sec
    sbc BossX
    cmp #17
    bcs ShotHorizontalDone
    inc HitBoss
ShotHorizontalDone
    sta WSYNC               ; 2: confirma Y; armadura tambem absorve o tiro
    lda HitBoss
    beq ShotVerticalDone
    lda ShotY
    sec
    sbc BossY
    cmp #12
    bcc ShotContact
    lda #0
    sta HitBoss
    beq ShotVerticalDone
ShotContact
    lda #0
    sta ShotActive
ShotVerticalDone
    sta WSYNC               ; 3: Guardiao expoe o nucleo tambem durante o ataque
    lda HitBoss
    beq BossDamageDone
    lda BossPhase
    cmp #3
    beq BossVulnerable
    cmp #2
    bne BossDamageDone
    lda RoomIndex
    cmp #2
    bne BossDamageDone
BossVulnerable
    lda BossFlash
    bne BossDamageDone
    dec BossHP
    lda #8
    sta BossFlash
    sta SoundTimer
    lda #2
    sta SoundKind
BossDamageDone
    sta WSYNC               ; 4: contato corporal em X
    lda GameState
    bne BodyHorizontalDone
    lda InvulnTimer
    bne BodyHorizontalDone
    lda XPos
    clc
    adc #7
    sec
    sbc BossX
    cmp #23
    bcs BodyHorizontalDone
    inc Touch
BodyHorizontalDone
    sta WSYNC               ; 5: contato corporal em Y
    lda Touch
    beq BodyVerticalDone
    lda YPos
    clc
    adc #7
    sec
    sbc BossY
    cmp #19
    bcs BodyVerticalDone
    inc PlayerHit
BodyVerticalDone
    sta WSYNC               ; 6: bala inimiga em X
    lda GameState
    bne EnemyHorizontalDone
    lda InvulnTimer
    bne EnemyHorizontalDone
    lda EnemyActive
    beq EnemyHorizontalDone
    lda XPos
    clc
    adc #7
    sec
    sbc EnemyX
    cmp #11
    bcs EnemyHorizontalDone
    inc EnemyTouch
EnemyHorizontalDone
    sta WSYNC               ; 7: bala inimiga em Y
    lda EnemyTouch
    beq EnemyVerticalDone
    lda YPos
    clc
    adc #7
    sec
    sbc EnemyY
    cmp #9
    bcs EnemyVerticalDone
    inc PlayerHit
    lda #0
    sta EnemyActive
EnemyVerticalDone
    sta WSYNC               ; 8: faixas do Senhor da Arena
    lda GameState
    bne HazardDone
    lda InvulnTimer
    bne HazardDone
    lda HazardActive
    beq HazardDone
    lda HazardAxis
    cmp #2
    bcs DiagonalHazard
    cmp #0
    bne VerticalHazard
    lda YPos
    clc
    adc #7
    sec
    sbc #34
    cmp #19
    bcs HazardDone
    lda XPos
    clc
    adc #7
    sec
    sbc #16
    cmp #135
    bcs HazardDone
    inc PlayerHit
    bne HazardDone
VerticalHazard
    lda XPos
    clc
    adc #7
    sec
    sbc #64
    cmp #39
    bcs HazardDone
    inc PlayerHit
    bne HazardDone
DiagonalHazard
    lda YPos
    asl
    sta HazardTouch
    lda HazardAxis
    cmp #3
    beq LeftDiagonal
    lda XPos
    clc
    adc #7
    sec
    sbc HazardTouch
    cmp #31                ; -7 <= X - 2Y <= 23
    bcs HazardDone
    inc PlayerHit
    bne HazardDone
LeftDiagonal
    lda XPos
    clc
    adc HazardTouch
    sec
    sbc #129
    cmp #31                ; 129 <= X + 2Y <= 159
    bcs HazardDone
    inc PlayerHit
HazardDone
    sta WSYNC               ; 9: aplica uma vez, mesmo com varios contatos
    lda PlayerHit
    beq PlayerDamageDone
    lda InvulnTimer
    bne PlayerDamageDone
    dec Lives
    lda #60
    sta InvulnTimer
    lda #16
    sta SoundTimer
    lda #1
    sta SoundKind
PlayerDamageDone
    sta WSYNC               ; 10: empate final vence; empate intermediario perde
    lda #0
    sta Touch
    lda GameState
    bne ResultReady
    lda BossHP
    bne CheckDefeat
    lda RoomIndex
    cmp #3
    beq FinalVictory
    lda Lives
    beq Defeat
    lda #3
    sta GameState
    lda #1
    sta DoorOpen
    ldx RoomIndex
    lda CombatRoomExits,x
    sta ExitDirection
    bne ChangedResult
FinalVictory
    lda #1
    sta GameState
    bne ChangedResult
CheckDefeat
    lda Lives
    bne ResultReady
Defeat
    lda #2
    sta GameState
ChangedResult
    inc Touch
ResultReady
    sta WSYNC               ; 11: limpa perigos antes da passagem/tela final
    lda Touch
    beq ResultDone
    lda #0
    sta ShotActive
    sta EnemyActive
    sta HazardActive
    sta HazardVisible
    sta InvulnTimer
    lda #3
    sta SoundKind
    lda #90
    sta SoundTimer
    lda GameState
    cmp #2
    bne ResultDone
    lda #1
    sta SoundKind
ResultDone
    rts
CombatRoomExits
    byte 1,2,1,0
