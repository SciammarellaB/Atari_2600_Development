    processor 6502

VSYNC   = $00
VBLANK  = $01
WSYNC   = $02
COLUBK  = $09

; JOGADOR 0
COLUP0 = $06
GRP0   = $1B
HMP0   = $20

; COMANDOS CONTROLE
SWCHA = $0280
SWACNT = $0281

; MEMORIA RAM $80 - $FF
XPos = $80
YPos = $81

; PROGRAMA
    org $F000
Reset
    sei
    cld
    ldx #$FF
    txs
    lda #0
ClearMemory
    sta $00,x
    dex
    bne ClearMemory
    sta $00
    sta SWACNT
    lda #$84
    sta COLUBK
    lda #$0E
    sta COLUP0
    lda #2
    sta VBLANK
    sta WSYNC
Clear
    lda #$0
    sta XPos
    sta YPos
Frame
; 3 linhas de sincronismo vertical do tubo
    lda #2
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC
; 37 linhas antes da imagem visivel
; A conta feita em cima de 37 menos a quantidade de chamadas wsync dentro das subrotinas
    jsr ReadJoystick
    jsr PositionPlayer
    ldx #0
    ldy #33
WaitVerticalBlank
    sta WSYNC
    dey
    bne WaitVerticalBlank
    sty VBLANK
DrawLine
    txa
    sec
    ;CONTINUAR DAQUI
StorePixels
; INPUT
ReadJoystick
    sta WSYNC
    sta WSYNC
    rts
PositionPlayer
    sta WSYNC
    sta WSYNC
    rts