; Rotinas comuns aos oito bancos F4, nas folgas das paginas PF.
; O mundo tem 48 linhas; a janela mostra 40, e o painel ocupa 32 scanlines.

        MAC HUD_CAMERA
UpdateCamera
        lda PlayerY
        sec
        sbc CameraY
        bcc CameraFollowUp
        cmp #8
        bcc CameraFollowUp
        cmp #29
        bcs CameraFollowDown
        bcc CameraReady
CameraFollowUp
        lda PlayerY
        sec
        sbc #8
        bcs CameraStore
        lda #0
        bcc CameraStore
CameraFollowDown
        lda PlayerY
        sec
        sbc #28
        cmp #9
        bcc CameraStore
        lda #8
CameraStore
        sta CameraY
CameraReady
        lda RowStart
        clc
        adc CameraY
        clc
        adc #40
        sta RowEnd
        lda ShotY
        sec
        sbc CameraY
        cmp #40
        bcc ShotInView
        cmp #$FF
        beq ShotInView
        lda #128
ShotInView
        sta ShotViewY
        rts
        ENDM

        MAC HUD_POPULATE
FacingOffsets
        byte 0,24,48,72
MuzzleX
        byte 4,4,$FE,8
MuzzleY
        byte 3,$FE,1,1
        ENDM

        MAC HUD_DRAW
DrawHud
        sta WSYNC
        lda #$02
        sta COLUBK
        lda #0
        sta PF0
        sta PF1
        sta PF2
        sta ENAM0
        sta ENAM1
        sta GRP1
        sta GRP0
        jmp HudEnter
        ENDM
