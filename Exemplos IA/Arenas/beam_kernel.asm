; O Senhor reutiliza M1 para um feixe de oito pixels, movido dois pixels
; por faixa. HMCLR preserva as posicoes dos outros objetos. Este kernel so
; roda durante aviso/ativacao diagonal; os demais padroes usam o kernel normal.
; HMOVE cedo produz o recorte TIA de oito pixels na segunda linha do par.
BeginBeamScene
    lda #0
    sta WSYNC
    sta VBLANK
BeamSceneFirst
    DRAW_SCENE_OBJECTS
    jmp BeamNextPlayerLine

; O salto de retorno fica inteiramente na mesma pagina: nao perde ciclo.
    align 128
BeamSceneFirstSync
    sta WSYNC
BeamSceneRepeat
    DRAW_SCENE_OBJECTS
BeamNextPlayerLine
    iny
    tya
    sec
    sbc YPos
    cmp #8
    bcs BeamPlayerOutside
    lda (PlayerPtr),y
    jmp BeamPlayerReady
BeamPlayerOutside
    lda #0
BeamPlayerReady
    sta PlayerPixels
    lda EnemyPixels
    sta WSYNC
BeamSceneSecond
    sta ENAM1
    sta HMOVE
    lda WallPF0-1,y
    sta PF0
    tya
    sec
    sbc BossY
    cmp #12
    bcs BeamBossOutside
    lda (BossPtr),y
    jmp BeamBossReady
BeamBossOutside
    lda #0
BeamBossReady
    tax
    lda (RightSecondPtr),y
    sta PF0
    lda #0
    cpy ShotY
    bne BeamNextShotReady
    lda ShotActive
BeamNextShotReady
    sta ShotPixels
    lda (EnemyPtr),y
    sta EnemyPixels
    lda PlayerPixels
    cpy #80
    bne BeamSceneFirstSync
    jmp SceneDone
