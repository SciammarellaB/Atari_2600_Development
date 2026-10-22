    processor 6502

VSYNC   = $00
VBLANK  = $01
WSYNC   = $02
COLUBK  = $09
HMOVE   = $2A

; CENARIO - PLAYFIELD DO TIA
COLUPF = $08        ; cor das paredes
CTRLPF = $0A        ; controla o espelhamento do playfield
PF0    = $0D        ; primeiros 4 blocos da metade esquerda
PF1    = $0E        ; proximos 8 blocos
PF2    = $0F        ; ultimos 8 blocos

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
    lda #0
    sta COLUBK
    lda #$0E
    sta COLUP0
    lda #$84
    sta COLUPF          ; paredes azuis sobre o fundo preto
    lda #%00000001
    sta CTRLPF          ; metade direita reflete a metade esquerda
    lda ScenePF0
    sta PF0
    lda ScenePF1
    sta PF1
    lda ScenePF2
    sta PF2             ; prepara o desenho da primeira faixa
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
    jsr ReadJoystick ; 3 linhas da preparacao para ler o controle
    jsr PositionPlayer ; mais 2 linhas: 37 - 3 - 2 = 32
    ldx #0
    ldy #32
WaitVerticalBlank
    sta WSYNC
    dey
    bne WaitVerticalBlank
    sty VBLANK
DrawLine
; Cada faixa do cenario ocupa 8 linhas: Y = X / 8, de 0 ate 23.
; X continua sendo o contador das 192 linhas visiveis.
    txa
    lsr
    lsr
    lsr
    tay

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
; Atualiza o playfield a tempo de cada trecho da linha ser desenhado.
    lda ScenePF0,y
    sta PF0
    lda ScenePF1,y
    sta PF1
    lda ScenePF2,y
    sta PF2
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

; CENARIO - 24 faixas de 8 linhas = 192 linhas.
; Cada bit ligado desenha uma parede com largura de 4 pixels do TIA.
; Ordem da esquerda para a direita: PF0 bits 4..7, PF1 bits 7..0,
; PF2 bits 0..7. CTRLPF espelha esses 20 blocos na metade direita.
; As tabelas ficam na ROM; nao ocupam os 128 bytes de RAM.
; Este desenho e visual: a colisao com as paredes ainda nao e tratada.
    align 256          ; evita ciclos extras nas leituras com indice Y
ScenePF0
    byte $F0, $10, $10, $10, $10, $10, $10, $10
    byte $10, $10, $00, $00, $00, $00, $10, $10
    byte $10, $10, $10, $10, $10, $10, $10, $F0
ScenePF1
    byte $FF, $00, $00, $00, $04, $04, $04, $04
    byte $07, $00, $00, $00, $00, $00, $00, $07
    byte $04, $04, $04, $04, $00, $00, $00, $FF
ScenePF2
    byte $3F, $00, $00, $00, $00, $00, $00, $00
    byte $07, $00, $08, $08, $08, $08, $00, $07
    byte $00, $00, $00, $00, $00, $00, $00, $3F

    org $FFFA
    word Reset
    word Reset
    word Reset
