; Banco 0: quatro chefes e seus ataques. Incluido pelo cartucho F8.
; Cada chamada ocupa 12 WSYNC, inclusive fora do combate. Nao ha chamadas
; ao banco 1: todas as tabelas necessarias a esta logica ficam neste banco.
UpdateBossBank
    sta WSYNC               ; 1: relogio e transicao de fase
    lda GameState
    beq BkCombat
    lda #0
    sta EnemyActive
    sta HazardActive
    sta HazardVisible
    REPEAT 11
    sta WSYNC
    REPEND
    rts
BkCombat
    lda #0
    sta AimRequest
    sta WallHit
    sta EnemySpawn
    sta PhaseChanged
    lda PhaseTimer
    beq BkChangePhase
    dec PhaseTimer
    bne BkPhaseReady
BkChangePhase
    lda BossPhase
    clc
    adc #1
    and #3
    sta BossPhase
    inc PhaseChanged
BkPhaseReady
    sta WSYNC               ; 2: duracao, aviso e pedido de disparo
    lda PhaseChanged
    beq BkPhaseSetupDone
    ldx RoomIndex
    lda BkPhaseOffsets,x
    ora BossPhase
    tax
    lda BkPhaseDurations,x
    sta PhaseTimer
    lda BossPhase
    cmp #1
    bne BkCheckAttackStart
    inc AimRequest
    lda RoomIndex
    cmp #3
    bne BkPhaseSetupDone
    lda HazardAxis
    clc
    adc #1
    and #3
    sta HazardAxis
    jmp BkPhaseSetupDone
BkCheckAttackStart
    cmp #2
    bne BkPhaseSetupDone
    lda RoomIndex
    beq BkPhaseSetupDone
    cmp #3
    bcs BkPhaseSetupDone
    inc EnemySpawn          ; pedido; linha 9 confirma se a bala esta livre
BkPhaseSetupDone
    sta WSYNC               ; 3: mira horizontal por centros
    lda AimRequest
    beq BkAimXDone
    lda #0
    sta AimBits
    lda XPos
    clc
    adc #4
    sta Target
    lda BossX
    clc
    adc #8
    cmp Target
    bcc BkAimRight
    sec
    sbc Target
    cmp #12
    bcc BkAimXDone
    lda #4
    sta AimBits
    bne BkAimXDone
BkAimRight
    lda Target
    sec
    sbc #8
    sec
    sbc BossX
    cmp #12
    bcc BkAimXDone
    lda #8
    sta AimBits
BkAimXDone
    sta WSYNC               ; 4: mira vertical por centros
    lda AimRequest
    beq BkAimYDone
    lda YPos
    clc
    adc #4
    sta Target
    lda BossY
    clc
    adc #6
    cmp Target
    bcc BkAimDown
    sec
    sbc Target
    cmp #8
    bcc BkAimYDone
    lda AimBits
    ora #1
    sta AimBits
    bne BkAimYDone
BkAimDown
    lda Target
    sec
    sbc #6
    sec
    sbc BossY
    cmp #8
    bcc BkAimYDone
    lda AimBits
    ora #2
    sta AimBits
BkAimYDone
    sta WSYNC               ; 5: rumo travado e escolha do movimento
    lda AimRequest
    beq BkDirectionReady
    ldx AimBits
    lda BkInputHeadings,x
    bmi BkDirectionReady
    sta BossHeading
BkDirectionReady
    lda #0
    sta Moving
    lda BossPhase
    cmp #2
    bne BkMotionReady
    lda RoomIndex
    beq BkBullMoves
    cmp #2
    bne BkMotionReady
BkBullMoves
    inc Moving              ; Touro e Guardiao: mesma investida em oito rumos
BkMotionReady
    ldx BossHeading
    sta WSYNC               ; 6: investida ou caminhada da Sentinela em X
    lda RoomIndex
    cmp #1
    beq BkPatrolX
    lda Moving
    beq BkBossXDone
    lda BossX
    clc
    adc BkChargeX,x
    cmp #8
    bcc BkBossClampLeft
    cmp #137
    bcc BkBossStoreX
    lda #136
    bne BkBossWallX
BkBossClampLeft
    lda #8
BkBossWallX
    inc WallHit
BkBossStoreX
    sta BossX
    jmp BkBossXDone
BkPatrolX
    lda PatrolMoving
    beq BkBossXDone
    ldx PatrolNode
    lda BossX
    cmp BkPatrolTargetX,x
    beq BkBossXDone
    bcc BkPatrolRight
    dec BossX
    jmp BkBossXDone
BkPatrolRight
    inc BossX
BkBossXDone
    sta WSYNC               ; 7: investida ou caminhada da Sentinela em Y
    lda RoomIndex
    cmp #1
    beq BkPatrolY
    lda Moving
    beq BkBossYDone
    ldx BossHeading
    lda BossY
    clc
    adc BkChargeY,x
    cmp #6
    bcc BkBossClampTop
    cmp #63
    bcc BkBossStoreY
    lda #62
    bne BkBossWallY
BkBossClampTop
    lda #6
BkBossWallY
    inc WallHit
BkBossStoreY
    sta BossY
    jmp BkBossYDone
BkPatrolY
    lda PatrolMoving
    beq BkBossYDone
    ldx PatrolNode
    lda BossY
    cmp BkPatrolTargetY,x
    beq BkBossYDone
    bcc BkPatrolDown
    dec BossY
    jmp BkBossYDone
BkPatrolDown
    inc BossY
BkBossYDone
    sta WSYNC               ; 8: recuperacao, protecao e faixas do Senhor
    lda WallHit
    beq BkNoWallHit
    lda #3
    sta BossPhase
    ldx RoomIndex
    lda BkRecoveryDurations,x
    sta PhaseTimer
BkNoWallHit
    lda InvulnTimer
    beq BkNoInvulnTick
    dec InvulnTimer
BkNoInvulnTick
    lda BossFlash
    beq BkNoBossFlashTick
    dec BossFlash
BkNoBossFlashTick
    lda #0
    sta HazardVisible
    sta HazardActive
    lda RoomIndex
    cmp #3
    bne BkHazardReady
    lda BossPhase
    cmp #1
    beq BkShowHazard
    cmp #2
    bne BkHazardReady
    lda #1
    sta HazardActive
BkShowHazard
    lda #1
    sta HazardVisible
BkHazardReady
    sta WSYNC               ; 9: um projetil por vez, sem mover ao nascer
    lda EnemySpawn
    beq BkSpawnDone
    lda EnemyActive
    bne BkRejectSpawn
    lda #2
    sta EnemyActive
    lda BossHeading
    sta EnemyHeading
    lda BossX
    clc
    adc #6
    sta EnemyX
    lda BossY
    clc
    adc #5
    sta EnemyY
    jmp BkSpawnDone
BkRejectSpawn
    lda #0
    sta EnemySpawn
BkSpawnDone
    sta WSYNC               ; 10: projetil em X, rumo capturado no disparo
    lda EnemyActive
    beq BkEnemyXDone
    lda EnemySpawn
    bne BkEnemyXDone
    ldx EnemyHeading
    lda EnemyX
    clc
    adc BkEnemyVelocityX,x
    sta EnemyX
    cmp #8
    bcc BkRemoveEnemyX
    cmp #149
    bcc BkEnemyXDone
BkRemoveEnemyX
    lda #0
    sta EnemyActive
BkEnemyXDone
    sta WSYNC               ; 11: projetil em Y e limite inferior/superior
    lda EnemyActive
    beq BkEnemyYDone
    lda EnemySpawn
    bne BkEnemyYDone
    ldx EnemyHeading
    lda EnemyY
    clc
    adc BkEnemyVelocityY,x
    sta EnemyY
    cmp #8
    bcc BkRemoveEnemyY
    cmp #74
    bcc BkEnemyYDone
BkRemoveEnemyY
    lda #0
    sta EnemyActive
BkEnemyYDone
    sta WSYNC               ; 12: destino apos disparo real e parada no centro
    lda RoomIndex
    cmp #1
    bne BkPatrolDone
    lda EnemySpawn
    beq BkCheckPatrolArrival
    lda PatrolNode
    clc
    adc #1
    and #3
    sta PatrolNode
    lda #1
    sta PatrolMoving
    bne BkPatrolDone
BkCheckPatrolArrival
    lda PatrolMoving
    beq BkPatrolDone
    ldx PatrolNode
    lda BossX
    cmp BkPatrolTargetX,x
    bne BkPatrolDone
    lda BossY
    cmp BkPatrolTargetY,x
    bne BkPatrolDone
    lda #0
    sta PatrolMoving
BkPatrolDone
    rts

BkPhaseOffsets
    byte 0,4,8,12
BkPhaseDurations
    byte 45,48,64,90        ; Touro de Ferro
    byte 50,45,1,75         ; Sentinela
    byte 60,36,64,60        ; Guardiao
    byte 45,60,60,75        ; Senhor da Arena
BkRecoveryDurations
    byte 90,75,60,75
BkInputHeadings
    byte $FF,0,4,$FF,6,7,5,6,2,1,3,2,$FF,0,4,$FF
BkChargeX
    byte 0,1,2,1,0,-1,-2,-1
BkChargeY
    byte -1,-1,0,1,1,1,0,-1
BkPatrolTargetX
    byte 72,136,72,8        ; topo, direita, baixo, esquerda
BkPatrolTargetY
    byte 6,34,62,34
BkEnemyVelocityX
    byte 0,1,2,1,0,-1,-2,-1
BkEnemyVelocityY
    byte -2,-1,0,1,2,1,0,-1
