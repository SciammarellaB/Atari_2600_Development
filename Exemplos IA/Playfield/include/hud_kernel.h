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

        MAC HUD_POINTERS
BuildHud
        lda Health
        jsr HudTimesFive
        clc
        adc #<HudHealth
        sta HudHealthPtr
        lda #>HudHealth
        sta HudHealthPtr+1
        lda Ammo
        lsr
        lsr
        lsr
        lsr
        jsr HudTimesFive
        clc
        adc #<HudTens
        sta HudTensPtr
        lda #>HudTens
        sta HudTensPtr+1
        lda Ammo
        and #$0F
        jsr HudTimesFive
        clc
        adc #<HudOnes
        sta HudOnesPtr
        lda #>HudOnes
        sta HudOnesPtr+1
        lda Weapon
        and #3
        jsr HudTimesFive
        clc
        adc #<HudWeapon
        sta HudWeaponPtr
        lda #>HudWeapon
        sta HudWeaponPtr+1
        jmp PopulateHud
HudTimesFive
        sta HudIndex
        asl
        asl
        clc
        adc HudIndex
        rts
        ENDM

        MAC HUD_POPULATE
PopulateHud
        ldx #0
        ldy #0
HudCopyRow
        lda HudHeart,y
        sta HudLeft0,x
        lda (HudHealthPtr),y
        sta HudLeft1,x
        lda HudBullet,y
        sta HudLeft2,x
        lda (HudTensPtr),y
        sta HudRight0,x
        lda (HudOnesPtr),y
        sta HudRight1,x
        lda (HudWeaponPtr),y
        sta HudRight2,x
        inx
        iny
        cpx #5
        bne HudCopyRow
        rts
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
        lda #0
        sta GRP1
        sta GRP0
        sta ENAM0
        sta ENAM1
        sta PF0
        sta PF1
        sta PF2
        lda #$02
        sta COLUBK
        lda #$0E
        sta COLUPF
        lda #9
        sta TIM64T
        jsr BuildHud
WaitHudBlank
        lda INTIM
        bne WaitHudBlank
        ldx #0
HudRow
        ldy #4
HudScan
        sta WSYNC
        lda HudLeft0,x
        sta PF0
        lda HudLeft1,x
        sta PF1
        lda HudLeft2,x
        sta PF2
        nop
        nop
        nop
        nop
        nop
        nop
        lda HudRight0,x
        sta PF0
        lda HudRight1,x
        sta PF1
        lda HudRight2,x
        sta PF2
        dey
        bne HudScan
        inx
        cpx #5
        bne HudRow
        sta WSYNC
        lda #0
        sta PF0
        sta PF1
        sta PF2
        ldx #3
HudBottom
        sta WSYNC
        dex
        bne HudBottom
        jmp EndVisible
        ENDM
