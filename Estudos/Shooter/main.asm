; Shooter vertical: estrelas em movimento, nave e tiro. NTSC, ROM de 4 KiB.
; Painel superior de 24 scanlines e cena 160 x 84 com linhas duplicadas.
    processor 6502

VSYNC = $00
VBLANK = $01
WSYNC = $02
COLUP0 = $06
COLUP1 = $07
COLUPF = $08
COLUBK = $09
NUSIZ0 = $04
NUSIZ1 = $05
PF0 = $0D
PF1 = $0E
PF2 = $0F
RESP0 = $10
RESP1 = $11
RESM0 = $12
RESM1 = $13
GRP0 = $1B
GRP1 = $1C
ENAM0 = $1D
ENAM1 = $1E
HMP0 = $20
HMP1 = $21
HMM0 = $22
HMM1 = $23
HMOVE = $2A
INPT4 = $0C
SWCHA = $0280
SWACNT = $0281

HudLines = 24
SceneRows = 84
StarRows = 96
ShipHeight = 8
MinX = 8
MaxX = 144
MinY = 4
MaxY = 72
ShotHeight = 3
ShotSpeed = 3
PickupHeight = 8
PickupInterval = 120
HoldFrames = 60
BombSpeed = 4

XPos = $80
YPos = $81
Input = $82
ShotActive = $83             ; $80, com P1 duplicado em largura: dois pixels
ShotX = $84
ShotY = $85
ShipPtr = $86               ; ponteiro de duas posicoes, sem cruzar paginas
ShotPixels = $88
; $89 livre
StarPhase = $8A              ; deslocamento circular 0..95
StarTick = $8B               ; divide a velocidade por quatro quadros
Lives = $8C
BombCount = $8D
ShotLevel = $8E
ScoreLo = $8F                ; seis digitos em tres bytes BCD
ScoreMid = $90
ScoreHi = $91
ShotStep = $92
FireHold = $93
BombLatch = $94
BombActive = $95
BombX = $96
BombY = $97
FlashTimer = $98
SceneColor = $99
PickupType = $9A             ; 0 nenhum, 1 bomba, 2 vida, 3 velocidade
PickupY = $9B
PickupX = $9C
PickupTick = $9D
PickupWait = $9E
NextPickup = $9F
HudBuffer = $A0              ; seis registros de sete linhas: $A0..$C9
HudDigit0 = $CA              ; ponteiros de duas posicoes para fontes de HUD
HudDigit1 = $CC
HudDigit2 = $CE
HudDigit3 = $D0
HudDigit4 = $D2
HudDigit5 = $D4
HudLife = $D6
HudBomb = $D8
ShotPtr = $DA
BombPtr = $DC
PickupPtr = $DE
NewBomb = $E0
BlastPulse = $E1             ; evento de explosao, valido durante um quadro
CollectedType = $E2
; $E3..$EF livres; pilha em $F0..$FF

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
    lda #$AE
    sta COLUP0               ; nave azul-clara, fundo preto
    lda #$1E
    sta COLUP1               ; tiro amarelo
    lda #$06
    sta COLUPF               ; estrelas cinzas, atras dos sprites
    lda #76
    sta XPos
    lda #68
    sta YPos
    lda #3
    sta Lives
    lda #ShotSpeed
    sta ShotStep
    lda #PickupInterval
    sta PickupWait
    lda #1
    sta NextPickup
    lda #$35
    sta NUSIZ1               ; P1 largo com um bit; M1 especial de oito pixels
    lda #>HudFontLow
    sta HudDigit0+1
    sta HudDigit5+1
    lda #>HudFontHigh
    sta HudLife+1
    sta HudDigit4+1
    lda #>HudFontReverseMid
    sta HudDigit1+1
    lda #>HudFontReverseHigh
    sta HudDigit2+1
    sta HudDigit3+1
    sta HudBomb+1
    lda #2
    sta VBLANK
    sta WSYNC
    jsr PrepareHud
    jsr BuildHud

Frame
    lda #2
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC

; 1 estrelas + 3 controles + 3 tiro + 1 nave + 3 efeitos + 4 objetos*2 + 17 + 1 = 37.
    jsr UpdateStars
    jsr ReadJoystick
    jsr UpdateShot
    jsr PrepareShip
    jsr PrepareEffects
    jsr PositionShot
    jsr PositionPickup
    jsr PositionBomb
    jsr PositionPlayer
    ldx #17
WaitVerticalBlank
    sta WSYNC
    dex
    bne WaitVerticalBlank
    sta WSYNC
    lda #0
    sta VBLANK
    lda #$82
    sta COLUBK
    lda #$0E
    sta COLUPF
    ldx #4
HudTopMargin
    sta WSYNC
    dex
    bne HudTopMargin
    ldy #0
DrawHudFirst
    lda HudBuffer,y
    sta PF0
    lda HudBuffer+7,y
    sta PF1
    lda HudBuffer+14,y
    sta PF2
    REPEAT 6
    nop
    REPEND
    lda HudBuffer+21,y
    sta PF0
    lda HudBuffer+28,y
    sta PF1
    lda HudBuffer+35,y
    sta PF2
    sta WSYNC
DrawHudSecond
    lda HudBuffer,y
    sta PF0
    lda HudBuffer+7,y
    sta PF1
    lda HudBuffer+14,y
    sta PF2
    REPEAT 6
    nop
    REPEND
    lda HudBuffer+21,y
    sta PF0
    lda HudBuffer+28,y
    sta PF1
    lda HudBuffer+35,y
    sta PF2
    iny
    cpy #7
    beq HudTextDone
    sta WSYNC
    jmp DrawHudFirst
HudTextDone
    sta WSYNC               ; linha 18: margem inferior
    lda #0
    sta PF0
    sta PF1
    sta PF2
    ldx #4
HudBottomMargin
    sta WSYNC
    dex
    bne HudBottomMargin
    lda #$06
    sta COLUBK              ; linha 22: separador cinza
    sta WSYNC               ; linha 23: intervalo preto antes da cena
    lda SceneColor
    sta COLUBK
    lda #$06
    sta COLUPF
    ldx StarPhase
    ldy #0
    lda #0
    sta ENAM0
    sta ENAM1
    lda (ShotPtr),y
    and #$80
    sta ShotPixels
SceneFirstSync
    sta WSYNC

; Janela de ROM alinhada substitui o buffer da nave e libera RAM para o HUD.
; GRP0/GRP1 sao escritos antes do ciclo 23 nas duas linhas de cada faixa.
DrawFirstLine
    sta GRP1
    lda (ShipPtr),y
    sta GRP0
; Lados independentes: PF0/PF1/PF2 nos ciclos 18/25/32 e 39/46/53.
; X=StarPhase+Y, no maximo 190; tabelas duplicadas evitam wrap no raster.
    lda StarPF0Left,x
    sta PF0
    lda StarPF1Left,x
    sta PF1
    lda StarPF2Left,x
    sta PF2
    lda StarPF0Right,x
    sta PF0
    lda StarPF1Right,x
    sta PF1
    lda StarPF2Right,x
    sta PF2
; Janelas de ROM preparam o proximo tiro e a bomba, sem calculos de altura.
    iny
    lda (ShotPtr),y
    and #$80
    sta ShotPixels
    lda (BombPtr),y
    dey
    sta WSYNC
DrawSecondLine
; Os sprites persistem. A carrega a bomba da proxima faixa (adiantada em uma
; scanline); M0 usa o item atual (atrasado em uma). Colisao usa a caixa 8x8.
    sta ENAM1
    lda (PickupPtr),y
    sta ENAM0
    lda StarPF0Left,x
    sta PF0
    lda StarPF1Left,x
    sta PF1
    lda StarPF2Left,x
    sta PF2
    lda StarPF0Right,x
    sta PF0
    lda StarPF1Right,x
    sta PF1
    lda StarPF2Right,x
    sta PF2
    iny
    inx
    cpy #SceneRows
    beq SceneDone
    lda ShotPixels
    jmp SceneFirstSync
SceneDone
    sta WSYNC
    lda #2
    sta VBLANK
    lda #0
    sta GRP0
    sta GRP1
    sta PF0
    sta PF1
    sta PF2
    sta ENAM0
    sta ENAM1
; 4 bomba + 5 coleta + 4 fontes + 14 buffer + 3 espera = 30 de overscan.
    jsr UpdateBomb
    jsr UpdatePickup
    jsr PrepareHud
    jsr BuildHud
    ldx #3
WaitOverscan
    sta WSYNC
    dex
    bne WaitOverscan
    jmp Frame

; Desloca o mapa para baixo uma linha logica a cada quatro quadros.
; Ao diminuir a origem da leitura, as estrelas avancam em direcao ao rodape.
UpdateStars
    sta WSYNC
    inc StarTick
    lda StarTick
    and #3
    sta StarTick
    bne StarsUpdated
    ldx StarPhase
    bne DecrementStarPhase
    ldx #StarRows
DecrementStarPhase
    dex
    stx StarPhase
StarsUpdated
    rts

; Tres linhas fixas. Bits ativos em zero no joystick 1.
; Direcoes opostas se anulam por eixo; diagonais combinam os dois eixos.
ReadJoystick
    sta WSYNC
    lda SWCHA
    eor #$FF
    and #$F0
    sta Input
    and #$C0
    cmp #$40
    bne CheckRight
    lda XPos
    cmp #MinX
    beq HorizontalDone
    dec XPos
    jmp HorizontalDone
CheckRight
    cmp #$80
    bne HorizontalDone
    lda XPos
    cmp #MaxX
    beq HorizontalDone
    inc XPos
HorizontalDone
    sta WSYNC
    lda Input
    and #$30
    cmp #$10
    bne CheckDown
    lda YPos
    cmp #MinY
    beq VerticalDone
    dec YPos
    jmp VerticalDone
CheckDown
    cmp #$20
    bne VerticalDone
    lda YPos
    cmp #MaxY
    beq VerticalDone
    inc YPos
VerticalDone
    sta WSYNC
    rts

; Um projetil por vez. Segurar fogo repete apos ele sair pelo topo.
; A origem e o centro do bico; mover a nave nao muda ShotX.
UpdateShot
    sta WSYNC
    lda ShotActive
    beq TryFire
    lda ShotY
    sec
    sbc ShotStep
    bcc RemoveShot
    sta ShotY
    jmp ShotUpdated
RemoveShot
    lda #0
    sta ShotActive
    jmp ShotUpdated
TryFire
    bit INPT4
    bmi ShotUpdated
    lda XPos
    clc
    adc #3
    sta ShotX
    lda YPos
    sec
    sbc #ShotHeight
    sta ShotY
    lda #$80
    sta ShotActive
ShotUpdated
    sta WSYNC
    sta WSYNC
    rts

; Quatro linhas fixas. Uma tentativa de bomba por pressionamento, aos 60
; quadros. Falta de carga ou uma bomba em voo tambem exigem soltar e rearmar.
UpdateBomb
    sta WSYNC
    lda #0
    sta BlastPulse
    sta NewBomb
    lda FlashTimer
    beq ReadBombButton
    dec FlashTimer
ReadBombButton
    bit INPT4
    bmi ReleaseBombButton
    lda BombLatch
    bne BombInputDone
    inc FireHold
    lda FireHold
    cmp #HoldFrames
    bne BombInputDone
    lda #1
    sta BombLatch
    lda BombCount
    beq BombInputDone
    lda BombActive
    bne BombInputDone
    inc NewBomb
    jmp BombInputDone
ReleaseBombButton
    lda #0
    sta FireHold
    sta BombLatch
BombInputDone
    sta WSYNC
    lda NewBomb
    beq MoveBomb
    dec BombCount
    lda #2
    sta BombActive
    lda XPos
    sta BombX
    lda YPos
    sec
    sbc #4
    sta BombY
    jmp BombFlightDone
MoveBomb
    lda BombActive
    beq BombFlightDone
    lda BombY
    sec
    sbc #BombSpeed
    bcc DestroyScene
    sta BombY
    jmp BombFlightDone
DestroyScene
; Limpa os objetos existentes. BlastPulse fica disponivel ao futuro sistema
; de inimigos no quadro seguinte; jogador, fundo, vidas e HUD sao preservados.
    lda #0
    sta BombActive
    sta ShotActive
    sta PickupType
    lda #PickupInterval
    sta PickupWait
    lda #8
    sta FlashTimer
    lda #1
    sta BlastPulse
BombFlightDone
    sta WSYNC
    sta WSYNC
    rts

; Cinco linhas fixas. Itens de teste ciclam bomba/vida/velocidade, nascem
; sobre o X atual da nave e descem reto. Uma caixa 8x8 coleta ao se sobrepor.
UpdatePickup
    sta WSYNC
    lda #0
    sta CollectedType
    lda BlastPulse
    bne PickupMoved
    lda PickupType
    beq WaitPickup
    inc PickupTick
    lda PickupTick
    and #1
    bne PickupMoved
    inc PickupY
    lda PickupY
    cmp #SceneRows
    bcc PickupMoved
    lda #0
    sta PickupType
    lda #PickupInterval
    sta PickupWait
    jmp PickupMoved
WaitPickup
    lda PickupWait
    beq SpawnPickup
    dec PickupWait
    bne PickupMoved
SpawnPickup
    lda NextPickup
    sta PickupType
    inc NextPickup
    lda NextPickup
    cmp #4
    bcc PickupKindReady
    lda #1
    sta NextPickup
PickupKindReady
    lda XPos
    sta PickupX
    lda #0
    sta PickupY
    sta PickupTick
PickupMoved
    sta WSYNC
    lda BlastPulse
    bne PickupCollisionDone
    lda PickupType
    beq PickupCollisionDone
    lda XPos
    sec
    sbc PickupX
    clc
    adc #7
    cmp #15
    bcs PickupCollisionDone
    lda YPos
    sec
    sbc PickupY
    clc
    adc #7
    cmp #15
    bcs PickupCollisionDone
    lda PickupType
    sta CollectedType
    lda #0
    sta PickupType
    lda #PickupInterval
    sta PickupWait
PickupCollisionDone
    sta WSYNC
    lda CollectedType
    beq PickupApplied
    cmp #1
    bne ApplyLife
    lda BombCount
    cmp #9
    bcs PickupApplied
    inc BombCount
    jmp PickupApplied
ApplyLife
    cmp #2
    bne ApplyShotSpeed
    lda Lives
    cmp #9
    bcs PickupApplied
    inc Lives
    jmp PickupApplied
ApplyShotSpeed
    lda ShotLevel
    cmp #3
    bcs PickupApplied
    inc ShotLevel
    inc ShotStep
PickupApplied
    sta WSYNC
    sta WSYNC
    rts

; Tres linhas fixas; os ponteiros inativos leem a margem vazia da nave.
PrepareEffects
    sta WSYNC
    lda ShotActive
    beq EmptyShotPointer
    lda #<ShotSprite
    sec
    sbc ShotY
    sta ShotPtr
    lda #>ShotSprite
    sta ShotPtr+1
    jmp ShotPointerReady
EmptyShotPointer
    lda #0
    sta ShotPtr
    lda #>ShipSprite
    sta ShotPtr+1
ShotPointerReady
    sta WSYNC
    lda BombActive
    beq EmptyBombPointer
    lda #<BombSprite
    sec
    sbc BombY
    sta BombPtr
    lda #>BombSprite
    sta BombPtr+1
    jmp BombPointerReady
EmptyBombPointer
    lda #0
    sta BombPtr
    lda #>ShipSprite
    sta BombPtr+1
BombPointerReady
    lda #0
    ldx FlashTimer
    beq SceneColorReady
    lda #$0E
SceneColorReady
    sta SceneColor
    sta WSYNC
    ldx PickupType
    beq EmptyPickupPointer
    lda PickupWidths,x
    sta NUSIZ0
    lda PickupSpriteLo,x
    sec
    sbc PickupY
    sta PickupPtr
    lda PickupSpriteHi,x
    sta PickupPtr+1
    rts
EmptyPickupPointer
    lda #0
    sta PickupPtr
    lda #>ShipSprite
    sta PickupPtr+1
    rts

; O sprite fica no centro de uma pagina de zeros. A janela de 84 linhas
; nunca cruza pagina e devolve zero acima/abaixo das oito linhas da nave.
PrepareShip
    sta WSYNC
    lda #>ShipSprite
    sta ShipPtr+1
    lda #<ShipSprite
    sec
    sbc YPos
    sta ShipPtr
    rts

; Ponteiros para os seis digitos BCD e os contadores de vidas/bombas.
; Os quatro formatos da fonte ja codificam a ordem de bits do playfield.
PrepareHud
    sta WSYNC
    lda ScoreHi
    lsr
    and #$78
    clc
    adc #<HudFontLow
    sta HudDigit0
    lda ScoreHi
    and #$0F
    asl
    asl
    asl
    clc
    adc #<HudFontReverseMid
    sta HudDigit1
    sta WSYNC
    lda ScoreMid
    lsr
    and #$78
    clc
    adc #<HudFontReverseHigh
    sta HudDigit2
    lda ScoreMid
    and #$0F
    asl
    asl
    asl
    clc
    adc #<HudFontReverseHigh
    sta HudDigit3
    sta WSYNC
    lda ScoreLo
    lsr
    and #$78
    clc
    adc #<HudFontHigh
    sta HudDigit4
    lda ScoreLo
    and #$0F
    asl
    asl
    asl
    clc
    adc #<HudFontLow
    sta HudDigit5
    sta WSYNC
    lda Lives
    asl
    asl
    asl
    clc
    adc #<HudFontHigh
    sta HudLife
    lda BombCount
    asl
    asl
    asl
    clc
    adc #<HudFontReverseHigh
    sta HudBomb
    rts

; Duas scanlines por linha de fonte: 14 linhas fixas durante o VBLANK.
BuildHud
    ldy #0
BuildHudRow
    sta WSYNC
    lda HudLifeIcon,y
    sta HudBuffer,y
    lda (HudLife),y
    ora (HudDigit0),y
    sta HudBuffer+7,y
    lda (HudDigit1),y
    ora (HudDigit2),y
    sta HudBuffer+14,y
    sta WSYNC
    lda (HudDigit3),y
    sta HudBuffer+21,y
    lda (HudDigit4),y
    ora (HudDigit5),y
    sta HudBuffer+28,y
    lda HudBombIcon,y
    ora (HudBomb),y
    sta HudBuffer+35,y
    iny
    cpy #7
    bne BuildHudRow
    rts

; O alinhamento impede ciclos extras de branch ao atravessar uma pagina.
; RESP + HMP usam a calibracao horizontal dos estudos existentes.
    align 32
PositionShot
    lda ShotX
    sec
    sbc #1                   ; P1 dobrado comeca um pixel depois do player normal
    sta WSYNC
    nop
    nop
    sec
ShotDivideBy15
    sbc #15
    bcs ShotDivideBy15
    eor #7
    asl
    asl
    asl
    asl
    sta RESP1
    sta HMP1
    sta WSYNC
    rts

    align 32
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
    sta HMOVE               ; aplica os dois objetos no inicio da linha
    rts

    align 32
PositionPickup
    lda PickupX
    clc
    adc #1                   ; o reset dos misseis e um pixel antes dos players
    sta WSYNC
    nop
    nop
    sec
PickupDivideBy15
    sbc #15
    bcs PickupDivideBy15
    eor #7
    asl
    asl
    asl
    asl
    sta RESM0
    sta HMM0
    sta WSYNC
    rts

    align 32
PositionBomb
    lda BombX
    clc
    adc #1
    sta WSYNC
    nop
    nop
    sec
BombDivideBy15
    sbc #15
    bcs BombDivideBy15
    eor #7
    asl
    asl
    asl
    asl
    sta RESM1
    sta HMM1
    sta WSYNC
    rts

HudLifeIcon
    byte $40,$40,$E0,$E0,$A0,$00,$00
HudBombIcon
    byte $04,$08,$04,$0E,$0E,$0E,$04
PickupSpriteLo
    byte 0,<PickupBombSprite,<PickupLifeSprite,<PickupSpeedSprite
PickupSpriteHi
    byte 0,>PickupBombSprite,>PickupLifeSprite,>PickupSpeedSprite
PickupWidths
    byte $00,$30,$20,$10

; Oito pixels de largura, nariz para cima; duas scanlines por byte.
    align 256
    ds 128,0
ShipSprite
    byte %00011000
    byte %00011000
    byte %00111100
    byte %00111100
    byte %01111110
    byte %11111111
    byte %11100111
    byte %01000010

    ds 120,0

; Fontes 3 x 7, oito bytes por digito; duas variantes por pagina.
    align 256
HudFontLow
    byte $07,$05,$05,$05,$05,$05,$07,$00
    byte $02,$06,$02,$02,$02,$02,$07,$00
    byte $07,$01,$01,$07,$04,$04,$07,$00
    byte $07,$01,$01,$07,$01,$01,$07,$00
    byte $05,$05,$05,$07,$01,$01,$01,$00
    byte $07,$04,$04,$07,$01,$01,$07,$00
    byte $07,$04,$04,$07,$05,$05,$07,$00
    byte $07,$01,$01,$02,$02,$02,$02,$00
    byte $07,$05,$05,$07,$05,$05,$07,$00
    byte $07,$05,$05,$07,$01,$01,$07,$00
HudFontHigh
    byte $70,$50,$50,$50,$50,$50,$70,$00
    byte $20,$60,$20,$20,$20,$20,$70,$00
    byte $70,$10,$10,$70,$40,$40,$70,$00
    byte $70,$10,$10,$70,$10,$10,$70,$00
    byte $50,$50,$50,$70,$10,$10,$10,$00
    byte $70,$40,$40,$70,$10,$10,$70,$00
    byte $70,$40,$40,$70,$50,$50,$70,$00
    byte $70,$10,$10,$20,$20,$20,$20,$00
    byte $70,$50,$50,$70,$50,$50,$70,$00
    byte $70,$50,$50,$70,$10,$10,$70,$00
    ds 2,0
PickupSpeedSprite
    byte $02,$00,$02,$00,$02,$00,$02,$00
ShotSprite
    byte $80,$80,$80
    align 256
HudFontReverseMid
    byte $0E,$0A,$0A,$0A,$0A,$0A,$0E,$00
    byte $04,$06,$04,$04,$04,$04,$0E,$00
    byte $0E,$08,$08,$0E,$02,$02,$0E,$00
    byte $0E,$08,$08,$0E,$08,$08,$0E,$00
    byte $0A,$0A,$0A,$0E,$08,$08,$08,$00
    byte $0E,$02,$02,$0E,$08,$08,$0E,$00
    byte $0E,$02,$02,$0E,$0A,$0A,$0E,$00
    byte $0E,$08,$08,$04,$04,$04,$04,$00
    byte $0E,$0A,$0A,$0E,$0A,$0A,$0E,$00
    byte $0E,$0A,$0A,$0E,$08,$08,$0E,$00
HudFontReverseHigh
    byte $E0,$A0,$A0,$A0,$A0,$A0,$E0,$00
    byte $40,$60,$40,$40,$40,$40,$E0,$00
    byte $E0,$80,$80,$E0,$20,$20,$E0,$00
    byte $E0,$80,$80,$E0,$80,$80,$E0,$00
    byte $A0,$A0,$A0,$E0,$80,$80,$80,$00
    byte $E0,$20,$20,$E0,$80,$80,$E0,$00
    byte $E0,$20,$20,$E0,$A0,$A0,$E0,$00
    byte $E0,$80,$80,$40,$40,$40,$40,$00
    byte $E0,$A0,$A0,$E0,$A0,$A0,$E0,$00
    byte $E0,$A0,$A0,$E0,$80,$80,$E0,$00
    ds 2,0
BombSprite
    byte $02,$02,$02,$02

; Campo de 24 estrelas, sem reflexao nem repeticao entre as metades.
; Cada mapa de 96 linhas e repetido duas vezes e comeca numa pagina.
; Isto mantem LDA tabela,X em quatro ciclos em todas as fases.
    align 256
StarPF0Left
    REPEAT 2
    byte $00,$00,$00,$00,$00,$00,$40,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $20,$20,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $80,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$10,$00,$00,$00,$00,$00,$00
    REPEND
PickupBombSprite
    byte $02,$00,$02,$02,$02,$02,$02,$02
    align 256
StarPF1Left
    REPEAT 2
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$10,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$02,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$80,$80,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $04,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    REPEND
    align 256
StarPF2Left
    REPEAT 2
    byte $00,$00,$10,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$02,$02,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$80,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$08,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    REPEND
    align 256
StarPF0Right
    REPEAT 2
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$20,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$80,$80,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$10,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$40,$00,$00,$00
    REPEND
PickupLifeSprite
    byte $00,$02,$02,$00,$02,$02,$00,$00
    align 256
StarPF1Right
    REPEAT 2
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$04,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$40,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$01,$01,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$10,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    REPEND
    align 256
StarPF2Right
    REPEAT 2
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$10,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$02,$02
    byte $00,$00,$00,$00,$00,$00,$00,$80,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$08,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    REPEND

    org $FFFA
    word Reset
    word Reset
    word Reset
