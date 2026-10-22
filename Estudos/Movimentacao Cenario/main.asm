    processor 6502

VSYNC   = $00
VBLANK  = $01
WSYNC   = $02
COLUBK  = $09
HMOVE   = $2A

; JOGADOR 0
COLUP0 = $06
RESP0  = $10
GRP0   = $1B
HMP0   = $20

; COMANDOS CONTROLE
SWCHA = $0280
SWACNT = $0281

; CONSTANTES
SquareHeight = 16
MinX = 8
MaxX = 160 - 16
MinY = 16
MaxY = 192 - SquareHeight - 16

; VARIAVEIS - MEMORIA RAM $80 - $FF
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
    lda #$50
    sta XPos
    sta YPos
; LOOP PRINCIPAL
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
    jsr ReadJoystick ; 3 linhas de sincronismo vertical
    jsr PositionPlayer
    ldx #0
    ldy #32
WaitVerticalBlank
    sta WSYNC
    dey
    bne WaitVerticalBlank
    sty VBLANK
DrawLine
    txa
    sec
    sbc YPos
    cmp #SquareHeight
    lda #0
    bcs StorePixels
    lda #%11111111
StorePixels
    sta WSYNC
    sta GRP0
    inx
    cpx #192
    bne DrawLine
; Overscan
    lda #2
    sta VBLANK
    lda #0
    sta GRP0
    ldx #30
WaitOverscan
    sta WSYNC
    dex
    bne WaitOverscan
    jmp Frame
; FIM LOOP PRINCIPAL
; INPUT
ReadJoystick
    sta WSYNC
CheckLeft
    ldx XPos
    lda #%01000000
    bit SWCHA
    bne CheckRight
    cpx #MinX
    beq CheckRight
    dex
    stx XPos
CheckRight
    ldx XPos
    lda #%10000000
    bit SWCHA
    bne HorizontalDone
    cpx #MaxX
    beq HorizontalDone
    inx
    stx XPos
HorizontalDone
    sta WSYNC
CheckUp
    ldx YPos
    lda #%00010000
    bit SWCHA
    bne CheckDown
    cpx #MinY
    beq CheckDown
    dex
    dex
    stx YPos
CheckDown
    ldx YPos
    lda #%00100000
    bit SWCHA
    bne VerticalDone
    cpx #MaxY
    beq VerticalDone
    inx
    inx
    stx YPos
VerticalDone
    sta WSYNC
    rts
PositionPlayer
    lda XPos
    sta WSYNC
    nop
    nop
    sec
DivideBy15
    sbc #15
    bcs DivideBy15
    eor #7
    asl
    asl
    asl
    asl
    sta RESP0
    sta HMP0
    sta WSYNC
    sta HMOVE
    rts

    org $FFFA
    word Reset
    word Reset
    word Reset