; Banco 7 F4: painel de sprites, 32 scanlines, sem alternancia de quadros.
        processor 6502
        include "hardware.h"
        include "hud_link.inc"

Room          = $80
Health        = $97
Ammo          = $98
Weapon        = $99
PuzzleFlags   = $EF
SpriteRows    = $9A
HudHeart0     = SpriteRows
HudHeart1     = SpriteRows+9
HudHeart2     = SpriteRows+18
HudAmmoIcon   = SpriteRows+27
HudAmmoTens   = SpriteRows+36
HudAmmoOnes   = SpriteRows+45
HudInventoryRows = SpriteRows+54
HudTemp       = SpriteRows+72
HudColorGun   = SpriteRows+73
HudColorGreen = SpriteRows+74
HudColorBlue  = SpriteRows+75
HudColorGold  = SpriteRows+76
EndVisible    = HUD_END_VISIBLE

; X e o deslocamento da variante, constante durante as nove linhas.
        MAC HUD_COPY
        lda {1}+0,x
        sta {2}+0
        lda {1}+1,x
        sta {2}+1
        lda {1}+2,x
        sta {2}+2
        lda {1}+3,x
        sta {2}+3
        lda {1}+4,x
        sta {2}+4
        lda {1}+5,x
        sta {2}+5
        lda {1}+6,x
        sta {2}+6
        lda {1}+7,x
        sta {2}+7
        lda {1}+8,x
        sta {2}+8
        ENDM

        MAC HUD_COPY_INVENTORY
        lda {1}+0,x
        sta HudInventoryRows+0
        lda {1}+1,x
        sta HudInventoryRows+1
        lda {1}+2,x
        sta HudInventoryRows+2
        lda {1}+3,x
        sta HudInventoryRows+3
        lda {1}+4,x
        sta HudInventoryRows+4
        lda {1}+5,x
        sta HudInventoryRows+5
        lda {1}+6,x
        sta HudInventoryRows+6
        lda {1}+7,x
        sta HudInventoryRows+7
        lda {1}+8,x
        sta HudInventoryRows+8
        lda {1}+9,x
        sta HudInventoryRows+9
        lda {1}+10,x
        sta HudInventoryRows+10
        lda {1}+11,x
        sta HudInventoryRows+11
        lda {1}+12,x
        sta HudInventoryRows+12
        lda {1}+13,x
        sta HudInventoryRows+13
        lda {1}+14,x
        sta HudInventoryRows+14
        lda {1}+15,x
        sta HudInventoryRows+15
        lda {1}+16,x
        sta HudInventoryRows+16
        lda {1}+17,x
        sta HudInventoryRows+17
        ENDM

; P0: coracoes x12/28/44; P1: bala x72, numeros x88/104, inventario x136.
; Parametros: linha dos numeros (0..8), linha do inventario (0..17), cor.
; X entra branco. Y recebe o byte do inventario antes da quarta copia;
; a cor muda depois do ultimo numero e volta ao branco no inicio seguinte.
        MAC HUD_SCAN
        sta WSYNC
        lda #3
        sta NUSIZ1       ; ciclo 5
        stx COLUP1       ; ciclo 8: bala e numeros sempre brancos
        lda HudHeart0+{1}
        sta GRP0         ; ciclo 14
        lda HudBulletTimes+{1}
        sta GRP1         ; ciclo 21: icone estatico lido direto da ROM
        bit HudTemp
        lda HudHeart1+{1}
        sta GRP0         ; ciclo 30
        lda HudHeart2+{1}
        sta GRP0         ; ciclo 36
        ldy HudInventoryRows+{2}
        ldx {3}
        nop
        lda HudAmmoTens+{1}
        sta GRP1         ; ciclo 50
        lda HudAmmoOnes+{1}
        sta GRP1         ; ciclo 56
        lda #6
        sta NUSIZ1       ; ciclo 61: quarta copia em x136
        stx COLUP1       ; ciclo 64: cor exclusiva do inventario
        sty GRP1         ; ciclo 67
        ldx #$0E         ; ciclo 69: branco da proxima scanline
        ENDM

        org $F000
Reset
        sei
        cld
        bit $FFF4        ; proxima instrucao vem do Reset do banco 0

        org $F100
HudBankStart
        lda #$0E
        sta COLUP0
        sta COLUP1
        lda #13
        sta TIM64T
        jsr BuildHud
        lda #3
        sta NUSIZ0
        sta NUSIZ1
        lda #21          ; x12, primeiro coracao
        jsr HudPositionObject
        lda #81          ; x72, posicionamento exato sem movimento fino
        jsr HudPositionPlayer
        sta WSYNC        ; ambos posicionados sem HMOVE: evita a barra preta lateral
        ldx #$0E
WaitHudBlank
        lda INTIM
        bne WaitHudBlank
        jmp HudScan0A

BuildHud
        lda #$0E
        sta HudColorGun
        sta COLUP0
        lda #$C6
        sta HudColorGreen
        lda #$86
        sta HudColorBlue
        lda #$1C
        sta HudColorGold
        bit PuzzleFlags
        bpl HudColorsReady
        sta HudColorGun
        sta HudColorGreen
        sta HudColorBlue
        sta COLUP0
HudColorsReady
        ldx #0
        lda Health
        cmp #1
        bcc HudHealth0Ready
        ldx #9
HudHealth0Ready
        HUD_COPY HudHearts,HudHeart0
        ldx #0
        lda Health
        cmp #2
        bcc HudHealth1Ready
        ldx #9
HudHealth1Ready
        HUD_COPY HudHearts,HudHeart1
        ldx #0
        lda Health
        cmp #3
        bcc HudHealth2Ready
        ldx #9
HudHealth2Ready
        HUD_COPY HudHearts,HudHeart2
        lda Ammo
        lsr
        lsr
        lsr
        lsr
        beq HudNoTens
        tax
        lda HudDigitOffsets,x
        tax
        jmp HudTensReady
HudNoTens
        tax
HudTensReady
        HUD_COPY HudDigitsTens,HudAmmoTens
        lda Ammo
        and #$0F
        tax
        lda HudDigitOffsets,x
        tax
        HUD_COPY HudDigitsOnes,HudAmmoOnes
        bit PuzzleFlags
        bpl HudInventoryNormal
        jmp HudInventoryVictory
HudInventoryNormal
        lda Weapon
        and #7
        sta HudTemp
        asl
        asl
        asl
        clc
        adc HudTemp
        asl
        tax
        lda Weapon
        and #8
        bne HudInventoryGold
        HUD_COPY_INVENTORY HudInventoryLow
        rts
HudInventoryGold
        HUD_COPY_INVENTORY HudInventoryHigh
        rts
HudInventoryVictory
        ldx #0
        HUD_COPY_INVENTORY HudVictory
        rts

HudDigitOffsets
        byte 9,18,27,36,45,54,63,72,81,90

HudPositionObject
        sec
        sta WSYNC
HudObjectDivide15
        sbc #15
        bcs HudObjectDivide15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP0
        sta RESP0
        rts

HudPositionPlayer
        sec
        sta WSYNC
HudDivide15
        sbc #15
        bcs HudDivide15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP1
        sta RESP1
        rts

HudScan0A
        HUD_SCAN 0,0,HudColorGun
        jmp HudScan0B
HudScan0B
        HUD_SCAN 0,1,HudColorGun
        jmp HudScan1A
HudScan1A
        HUD_SCAN 1,2,HudColorGun
        jmp HudScan1B
HudScan1B
        HUD_SCAN 1,3,HudColorGun
        jmp HudScan2A
HudScan2A
        HUD_SCAN 2,4,HudColorGun
        jmp HudScan2B
HudScan2B
        HUD_SCAN 2,5,HudColorGun
        jmp HudScan3A
HudScan3A
        HUD_SCAN 3,6,HudColorGreen
        jmp HudScan3B
HudScan3B
        HUD_SCAN 3,7,HudColorGreen
        jmp HudScan4A
HudScan4A
        HUD_SCAN 4,8,HudColorGreen
        jmp HudScan4B
HudScan4B
        HUD_SCAN 4,9,HudColorGreen
        jmp HudScan5A
HudScan5A
        HUD_SCAN 5,10,HudColorBlue
        jmp HudScan5B
HudScan5B
        HUD_SCAN 5,11,HudColorBlue
        jmp HudScan6A
HudScan6A
        HUD_SCAN 6,12,HudColorBlue
        jmp HudScan6B
HudScan6B
        HUD_SCAN 6,13,HudColorBlue
        jmp HudScan7A
HudScan7A
        HUD_SCAN 7,14,HudColorGold
        jmp HudScan7B
HudScan7B
        HUD_SCAN 7,15,HudColorGold
        jmp HudScan8A
HudScan8A
        HUD_SCAN 8,16,HudColorGold
        jmp HudScan8B
HudScan8B
        HUD_SCAN 8,17,HudColorGold
        jmp HudBottom
HudBottom
        sta WSYNC
        lda #0
        sta GRP0
        sta GRP1
        sta WSYNC
        jmp HudReturn
HudCodeEnd
        if HudCodeEnd > $F900
        err
        endif

        org $F900
        include "hud.inc"
HudDataEnd
        if HudDataEnd > $FFD0
        err
        endif
        org $FFD0
        include "bank-map.inc"
        org $FFE0
        include "hud_bank_switch.h"
        org $FFFA
        word Reset,Reset,Reset
