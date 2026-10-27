; Nove salas fixas em 3 x 3, movimento em 8 direcoes, tiro e HUD.
; Atari 2600, 4 KiB, NTSC: 160 scanlines de cena + 32 reservadas ao HUD.
; Cena logica: 160 x 80; cada linha do sprite ocupa 2 scanlines.
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
CTRLPF = $0A
PF0 = $0D
PF1 = $0E
PF2 = $0F
RESP0 = $10
RESP1 = $11
GRP0 = $1B
GRP1 = $1C
INPT4 = $0C
HMP0 = $20
HMP1 = $21
HMOVE = $2A
SWCHA = $0280
SWACNT = $0281

MinX = 4
MaxX = 148
MinY = 4
SceneRows = 80
SceneLines = SceneRows * 2
HudLines = 192 - SceneLines
BottomWallY = SceneRows - 4
MaxY = BottomWallY - 8
StartY = (SceneRows - 8) / 2
HudColor = $06
HudTextTop = 9
HudTextHeight = 14
HudTextBottom = HudLines - HudTextTop - HudTextHeight
XPos = $80
XFrac = $81
YPos = $82
YFrac = $83
Heading = $84
InputHeading = $86
Travel = $87
DeltaX = $89
DeltaY = $8A
SignX = $8B
SignY = $8C
SpritePtr = $8D             ; dois bytes, ponteiro para 8 linhas na ROM
CurrentRoom = $85
RoomMask = $88              ; N=1, S=2, W=4, E=8
PreviousY = $8F
RoomChanged = $90
EntryX = $91
EntryY = $92
WallRest = EntryX           ; reutilizado somente durante o kernel
ShotActive = $93            ; $C0 = dois pixels brancos; zero = inativo
ShotX = $94
ShotXFrac = $95
ShotY = $96
ShotYFrac = $97
ShotHeading = $98
NewShot = $99
ShotRowBefore = $9A
ShotPixels = $9B
NextRoom = ShotRowBefore    ; temporario, antes de UpdateShot preparar a faixa
RoomDigitPtr = $9C          ; dois bytes
LeftWallPtr = $9E           ; dois bytes
PlayerBuffer = $A0         ; 80 bytes: $A0..$EF, uma linha logica por byte
RightWallPtr = $F0          ; dois bytes
WallPF2Ptr = $F2            ; dois bytes; $F4..$FF ficam livres para a pilha
; Nao aninhar mais de seis JSR: a pilha compartilha os 128 bytes de RAM.

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
    sta COLUBK
    lda #$0E
    sta COLUP0
    sta COLUP1
    sta COLUPF
    lda #1
    sta CTRLPF              ; reflete o playfield: bordas simetricas
    lda #4
    sta CurrentRoom
    lda #76
    sta XPos
    lda #StartY
    sta YPos
    lda #2
    sta VBLANK
    sta WSYNC
Frame
    lda #2
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC

; 8 controles + 8 sala + 6 tiro + 5 buffer + 3/2 posicao + 4 espera + 1 = 37.
    jsr ReadJoystick
    jsr UpdateRoom
    jsr UpdateShot
    jsr BuildPlayerBuffer
    jsr PositionShot
    jsr PositionPlayer
    ldy #4
WaitVerticalBlank
    sta WSYNC
    dey
    bne WaitVerticalBlank
    ldy #0
    lda #$FF
    sta WallRest
    lda #0
    sta ShotPixels
    sta WSYNC
    sta VBLANK

; Y indexa 80 faixas de duas scanlines. O buffer evita calcular o sprite
; durante o raster. PF0 esquerdo/direito sao independentes, preservando a
; reflexao de PF1/PF2. A escrita direita acontece depois de PF0 esquerdo.
; Primeira linha: GRP1/PF0L/GRP0/PF1/PF2/PF0R = 6/14/21/27/35/43.
; Segunda linha: os mesmos registradores = 3/11/18/24/32/40.
DrawFirstLine
    sta GRP1
    lda (LeftWallPtr),y
    sta PF0
    lda PlayerBuffer,y
    sta GRP0
    lda WallRest
    sta PF1
    lda (WallPF2Ptr),y
    sta PF2
    lda (RightWallPtr),y
    sta PF0
    lda ShotPixels
    sta WSYNC
DrawSecondLine
    sta GRP1
    lda (LeftWallPtr),y
    sta PF0
    lda PlayerBuffer,y
    sta GRP0
    lda WallRest
    sta PF1
    lda (WallPF2Ptr),y
    sta PF2
    lda (RightWallPtr),y
    sta PF0
    iny
    lda RoomWallPF1,y
    sta WallRest
    lda #0
    cpy ShotY
    bne NextShotReady
    lda ShotActive
NextShotReady
    sta ShotPixels
    cpy #SceneRows
    beq SceneDone
    lda ShotPixels
    sta WSYNC
    jmp DrawFirstLine
SceneDone
; Termina a linha 159 da sala e entra na primeira das 32 linhas do HUD.
; O playfield fica vazio; o fundo cinza ocupa toda a largura.
; COLUBK e escrito no ciclo 22, antes do primeiro pixel visivel da linha.
    sta WSYNC
    lda #0
    sta GRP0
    sta GRP1
    sta PF0
    sta PF1
    sta PF2
    lda #HudColor
    sta COLUBK
; Duas copias de A e uma de I usam Player 0; T/R usam Player 1.
; Cada letra usa cinco pixels de largura, com espacos entre os objetos.
    lda #3
    sta NUSIZ0              ; 3 copias proximas: X, X+16, X+32
    lda #1
    sta NUSIZ1              ; 2 copias proximas: X, X+16
    sta WSYNC              ; HUD linha 1: posicionamento fixo do texto
; RESP0 no ciclo 41 -> X=60; RESP1 no ciclo 44 -> X=69.
; A/I tem um pixel vazio a esquerda: letras em X=61,69,77,85,93.
; Sem HMOVE nesta faixa: evita a barra preta lateral sobre o fundo cinza.
    REPEAT 19
    nop
    REPEND
    sta RESP0
    sta RESP1
    ldx #HudTextTop-2
WaitHudTop
    sta WSYNC
    dex
    bne WaitHudTop
    ldy #0
DrawHudText
    sta WSYNC              ; primeira linha de texto: HUD linha 9
    lda (RoomDigitPtr),y
    sta PF1                ; ciclo 8: numero da sala em X=16..27
    lda HudFontA,y
    sta GRP0               ; ciclo 15: A na primeira e segunda copias
    lda HudFontT,y
    sta GRP1               ; ciclo 22: T na primeira copia
    lda HudFontR,y
    tax
    lda HudFontI,y
    bit XPos               ; 3 ciclos, completa a espera de 15 ciclos
    REPEAT 6
    nop
    REPEND
    stx GRP1               ; ciclo 50: R na segunda copia
    sta GRP0               ; ciclo 53: I na terceira copia
    lda #0
    sta PF1                ; ciclo 58: apaga a copia refletida do numero
    iny
    cpy #HudTextHeight
    bne DrawHudText
    sta WSYNC              ; HUD linha 23: comeca a margem inferior
    lda #0
    sta GRP0
    sta GRP1
    sta NUSIZ0             ; uma copia normal para a cena seguinte
    sta NUSIZ1
    ldx #HudTextBottom
WaitHud
    sta WSYNC
    dex
    bne WaitHud
VisibleDone
    lda #2
    sta VBLANK
    lda #0
    sta COLUBK             ; preto para a sala do proximo quadro
    sta GRP0
    sta GRP1
    sta PF0
    sta PF1
    sta PF2
    ldx #30
WaitOverscan
    sta WSYNC
    dex
    bne WaitOverscan
    jmp Frame

; Oito WSYNC fixos, mesmo parado ou encostado na parede. Cada direcao
; move no eixo da tela e escolhe a seta imediatamente; opostas se anulam.
ReadJoystick
    sta WSYNC               ; 1: converte os quatro bits ativos em zero
    lda SWCHA
    eor #$FF
    lsr
    lsr
    lsr
    lsr
    tax
    lda InputHeadings,x
    sta InputHeading
    sta WSYNC               ; 2: parado conserva a ultima orientacao
    lda #0
    sta Travel
    lda InputHeading
    bmi TravelDone
    sta Heading
    inc Travel
TravelDone
    sta WSYNC               ; 3: vetores assinados em ponto fixo 8.8
    ldx Heading
    lda VelocityX,x
    sta DeltaX
    lda VelocityY,x
    sta DeltaY
    lda #0
    sta SignX
    sta SignY
    lda DeltaX
    bpl PositiveX
    dec SignX
PositiveX
    lda DeltaY
    bpl PositiveY
    dec SignY
PositiveY
    sta WSYNC               ; 4: soma X (fracao e parte inteira)
    lda Travel
    beq XAdded
    clc
    lda XFrac
    adc DeltaX
    sta XFrac
    lda XPos
    adc SignX
    sta XPos
XAdded
    sta WSYNC               ; 5: limite X, sem acumular fracao contra parede
    lda XPos
    cmp #MinX
    bcc ClampLeft
    cmp #MaxX
    bcc XClamped
    lda #MaxX
    jmp ClampX
ClampLeft
    lda #MinX
ClampX
    sta XPos
    lda #0
    sta XFrac
XClamped
    sta WSYNC               ; 6: soma Y em faixas de duas scanlines
    lda Travel
    beq YAdded
    clc
    lda YFrac
    adc DeltaY
    sta YFrac
    lda YPos
    adc SignY
    sta YPos
YAdded
    sta WSYNC               ; 7: limite Y
    lda YPos
    cmp #MinY
    bcc ClampTop
    cmp #MaxY
    bcc YClamped
    lda #MaxY
    jmp ClampY
ClampTop
    lda #MinY
ClampY
    sta YPos
    lda #0
    sta YFrac
YClamped
    sta WSYNC               ; 8: sprite da direcao de movimento
    lda Heading
    asl
    asl
    asl
    clc
    adc #<ArrowSprites
    sta SpritePtr
    lda #>ArrowSprites
    sta SpritePtr+1
    lda XPos
    sta EntryX
    lda YPos
    sta EntryY
    lda #0
    sta RoomChanged
    rts

; Passagens centrais: X=64..95 em norte/sul; Y=28..51 em oeste/leste.
; A caixa inteira de 8 x 8 precisa caber. A troca ocorre ao encostar na
; abertura movendo-se para fora, depois do clamp de ReadJoystick.
; Oito WSYNC em todos os caminhos, inclusive nas bordas externas do mapa.
UpdateRoom
    sta WSYNC               ; 1: oeste
    lda Travel
    beq WestDone
    lda DeltaX
    bpl WestDone
    lda XPos
    cmp #MinX
    bne WestDone
    lda YPos
    cmp #28
    bcc WestDone
    cmp #45
    bcs WestDone
    ldx CurrentRoom
    lda RoomWest,x
    bmi WestDone
    sta NextRoom
    lda #MaxX
    sta EntryX
    lda #1
    sta RoomChanged
WestDone
    sta WSYNC               ; 2: leste
    lda Travel
    beq EastDone
    lda DeltaX
    beq EastDone
    bmi EastDone
    lda XPos
    cmp #MaxX
    bne EastDone
    lda YPos
    cmp #28
    bcc EastDone
    cmp #45
    bcs EastDone
    ldx CurrentRoom
    lda RoomEast,x
    bmi EastDone
    sta NextRoom
    lda #MinX
    sta EntryX
    lda #1
    sta RoomChanged
EastDone
    sta WSYNC               ; 3: norte
    lda Travel
    beq NorthDone
    lda DeltaY
    bpl NorthDone
    lda YPos
    cmp #MinY
    bne NorthDone
    lda XPos
    cmp #64
    bcc NorthDone
    cmp #89
    bcs NorthDone
    ldx CurrentRoom
    lda RoomNorth,x
    bmi NorthDone
    sta NextRoom
    lda #MaxY
    sta EntryY
    lda #1
    sta RoomChanged
NorthDone
    sta WSYNC               ; 4: sul
    lda Travel
    beq SouthDone
    lda DeltaY
    beq SouthDone
    bmi SouthDone
    lda YPos
    cmp #MaxY
    bne SouthDone
    lda XPos
    cmp #64
    bcc SouthDone
    cmp #89
    bcs SouthDone
    ldx CurrentRoom
    lda RoomSouth,x
    bmi SouthDone
    sta NextRoom
    lda #MinY
    sta EntryY
    lda #1
    sta RoomChanged
SouthDone
    sta WSYNC               ; 5: aplica a transicao antes de desenhar
    lda RoomChanged
    beq RoomUnchanged
    lda NextRoom
    sta CurrentRoom
    lda EntryX
    sta XPos
    lda EntryY
    sta YPos
    lda #0
    sta XFrac
    sta YFrac
    sta ShotActive
RoomUnchanged
    ldx CurrentRoom
    lda RoomDoors,x
    sta RoomMask
    sta WSYNC               ; 6: paredes laterais independentes
    lda #<RoomWallClosed
    ldx RoomMask
    txa
    and #4
    beq LeftWallClosed
    lda #<RoomWallOpen
    bne LeftWallSelected
LeftWallClosed
    lda #<RoomWallClosed
LeftWallSelected
    sta LeftWallPtr
    txa
    and #8
    beq RightWallClosed
    lda #<RoomWallOpen
    bne RightWallSelected
RightWallClosed
    lda #<RoomWallClosed
RightWallSelected
    sta RightWallPtr
    lda #>RoomWallClosed
    sta LeftWallPtr+1
    sta RightWallPtr+1
    sta WSYNC               ; 7: paredes norte/sul e vao central
    lda RoomMask
    and #3
    tax
    lda RoomPF2Lo,x
    sta WallPF2Ptr
    lda RoomPF2Hi,x
    sta WallPF2Ptr+1
    sta WSYNC               ; 8: digito de 1 a 9 no HUD
    ldx CurrentRoom
    lda RoomNumberLo,x
    sta RoomDigitPtr
    lda #>RoomNumberGlyphs
    sta RoomDigitPtr+1
    rts

; Somente oito linhas do personagem precisam ser apagadas e preenchidas.
; Quatro escritas por linha, desenroladas para manter os cinco WSYNC fixos.
BuildPlayerBuffer
    lda #0
    ldy PreviousY
    sta WSYNC               ; 1: apaga as quatro primeiras linhas antigas
    REPEAT 4
    sta PlayerBuffer,y
    iny
    REPEND
    sta WSYNC               ; 2: apaga as quatro restantes
    REPEAT 4
    sta PlayerBuffer,y
    iny
    REPEND
    ldx YPos
    ldy #0
    sta WSYNC               ; 3: desenha a metade superior na nova posicao
    REPEAT 4
    lda (SpritePtr),y
    sta PlayerBuffer,x
    inx
    iny
    REPEND
    sta WSYNC               ; 4: desenha a metade inferior
    REPEAT 4
    lda (SpritePtr),y
    sta PlayerBuffer,x
    inx
    iny
    REPEND
    lda YPos
    sta PreviousY
    sta WSYNC               ; 5: retorno e preparacao do posicionamento
    rts

; Um tiro por vez. Segurar o botao repete quando o anterior desaparece.
; A orientacao e copiada ao nascer; mover o personagem nao curva o tiro.
; Seis linhas fixas mantem o mesmo orcamento do quadro em todos os caminhos.
UpdateShot
    sta WSYNC               ; 1: botao e captura da orientacao
    lda #0
    sta NewShot
    lda RoomChanged
    bne ShotInputDone
    lda ShotActive
    bne ShotInputDone
    bit INPT4               ; bit 7 ativo em zero, joystick 1
    bmi ShotInputDone
    lda #$C0
    sta ShotActive
    inc NewShot
    lda Heading
    sta ShotHeading
ShotInputDone
    sta WSYNC               ; 2: origem logo a frente da seta
    lda NewShot
    beq ShotSpawnDone
    ldx ShotHeading
    lda XPos
    clc
    adc ShotSpawnX,x
    sta ShotX
    lda YPos
    clc
    adc ShotSpawnY,x
    sta ShotY
    lda #0
    sta ShotXFrac
    sta ShotYFrac
ShotSpawnDone
    sta WSYNC               ; 3: avanco horizontal em ponto fixo 8.8
    lda ShotActive
    beq ShotXDone
    lda NewShot
    bne ShotXDone
    ldx ShotHeading
    clc
    lda ShotXFrac
    adc ShotVelocityXLo,x
    sta ShotXFrac
    lda ShotX
    adc ShotVelocityXHi,x
    sta ShotX
ShotXDone
    sta WSYNC               ; 4: avanco vertical
    lda ShotActive
    beq ShotYDone
    lda NewShot
    bne ShotYDone
    ldx ShotHeading
    clc
    lda ShotYFrac
    adc ShotVelocityYLo,x
    sta ShotYFrac
    lda ShotY
    adc ShotVelocityYHi,x
    sta ShotY
ShotYDone
    sta WSYNC               ; 5: caixa de 2 x 1 pixels contra paredes
    lda ShotX
    cmp #4
    bcc RemoveShot
    cmp #155
    bcs RemoveShot
    lda ShotY
    cmp #4
    bcc RemoveShot
    cmp #BottomWallY
    bcc ShotBoundsDone
RemoveShot
    lda #0
    sta ShotActive
ShotBoundsDone
    sta WSYNC               ; 6: prepara faixa do kernel
    lda ShotY
    sec
    sbc #1
    sta ShotRowBefore
    rts

; Player 1 desenha o tiro usando apenas os dois bits esquerdos de GRP1.
; Mesma calibracao do jogador. X >= 150 faz a escrita de HMP1 terminar na
; linha seguinte: o WSYNC seguinte consome uma linha extra. Para X < 150,
; esperamos essa terceira linha explicitamente. Assim sao sempre 3 linhas.
    align 32
PositionShot
    lda ShotX
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
    lda ShotX
    cmp #150
    bcs ShotPositionDone
    sta WSYNC
ShotPositionDone
    rts

; Rotina calibrada nos demais estudos. NOPs e alinhamento preservam os
; ciclos do posicionamento horizontal, inclusive em X=148.
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
    sta HMOVE
    rts

; Indice: bits 0/1/2/3 = cima/baixo/esquerda/direita pressionados.
; $FF indica repouso; pares opostos se anulam e preservam o outro eixo.
InputHeadings
    byte $FF,0,4,$FF,6,7,5,6,2,1,3,2,$FF,0,4,$FF

; 8 rumos horarios: 0=norte, 2=leste, 4=sul, 6=oeste.
; Modulo ~127/256 pixel logico/quadro; diagonais nao ganham velocidade.
VelocityX
    byte 0,90,127,90,0,-90,-127,-90
VelocityY
    byte -127,-90,0,90,127,90,0,-90

; Origem: borda frontal da seta em cada uma das oito direcoes.
ShotSpawnX
    byte 3,7,8,7,3,-1,-2,-1
ShotSpawnY
    byte -2,-1,3,7,8,7,3,-1

; Velocidade 2 pixels logicos/quadro: quatro vezes a do personagem.
; Diagonais usam 362/256 por eixo (~sqrt(2)), sem ganho de velocidade.
ShotVelocityXLo
    byte $00,$6A,$00,$6A,$00,$96,$00,$96
ShotVelocityXHi
    byte $00,$01,$02,$01,$00,$FE,$FE,$FE
ShotVelocityYLo
    byte $00,$96,$00,$6A,$00,$6A,$00,$96
ShotVelocityYHi
    byte $FE,$FE,$00,$01,$02,$01,$00,$FE

; Indices de sala: 0 1 2 / 3 4 5 / 6 7 8. $FF = parede externa.
RoomNorth
    byte $FF,$FF,$FF,0,1,2,3,4,5
RoomSouth
    byte 3,4,5,6,7,8,$FF,$FF,$FF
RoomWest
    byte $FF,0,1,$FF,3,4,$FF,6,7
RoomEast
    byte 1,2,$FF,4,5,$FF,7,8,$FF
RoomDoors
    byte 10,14,6,11,15,7,9,13,5
RoomPF2Lo
    byte <RoomPF2Closed,<RoomPF2North,<RoomPF2South,<RoomPF2Both
RoomPF2Hi
    byte >RoomPF2Closed,>RoomPF2North,>RoomPF2South,>RoomPF2Both
RoomNumberLo
    byte <RoomNumber1,<RoomNumber2,<RoomNumber3,<RoomNumber4,<RoomNumber5
    byte <RoomNumber6,<RoomNumber7,<RoomNumber8,<RoomNumber9

; Tres tabelas de 80 bytes cabem na mesma pagina. Leituras por Y=0..79
; nunca cruzam pagina; o ponteiro seleciona a lateral aberta ou fechada.
    align 256
RoomWallClosed
    byte $F0,$F0,$F0,$F0,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10
    byte $10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10
    byte $10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10
    byte $10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10
    byte $10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$F0,$F0,$F0,$F0
RoomWallOpen
    byte $F0,$F0,$F0,$F0,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10
    byte $10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10
    byte $10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$F0,$F0,$F0,$F0
RoomWallPF1
    byte $FF,$FF,$FF,$FF,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$FF,$FF,$FF,$FF
    align 256
RoomPF2Closed
    byte $FF,$FF,$FF,$FF,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$FF,$FF,$FF,$FF
RoomPF2North
    byte $0F,$0F,$0F,$0F,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$FF,$FF,$FF,$FF
    align 256
RoomPF2South
    byte $FF,$FF,$FF,$FF,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$0F,$0F,$0F,$0F
RoomPF2Both
    byte $0F,$0F,$0F,$0F,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00
    byte $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$0F,$0F,$0F,$0F

; Numeros 1..9: fonte 3 x 7 no PF1 esquerdo, 14 scanlines por digito.
; Todos ficam na mesma pagina, juntamente com as fontes de ATARI.
    align 256
RoomNumberGlyphs
RoomNumber1
    byte $40,$40,$C0,$C0,$40,$40,$40,$40,$40,$40,$40,$40,$E0,$E0
RoomNumber2
    byte $E0,$E0,$20,$20,$20,$20,$E0,$E0,$80,$80,$80,$80,$E0,$E0
RoomNumber3
    byte $E0,$E0,$20,$20,$20,$20,$E0,$E0,$20,$20,$20,$20,$E0,$E0
RoomNumber4
    byte $A0,$A0,$A0,$A0,$A0,$A0,$E0,$E0,$20,$20,$20,$20,$20,$20
RoomNumber5
    byte $E0,$E0,$80,$80,$80,$80,$E0,$E0,$20,$20,$20,$20,$E0,$E0
RoomNumber6
    byte $E0,$E0,$80,$80,$80,$80,$E0,$E0,$A0,$A0,$A0,$A0,$E0,$E0
RoomNumber7
    byte $E0,$E0,$20,$20,$20,$20,$40,$40,$40,$40,$40,$40,$40,$40
RoomNumber8
    byte $E0,$E0,$A0,$A0,$A0,$A0,$E0,$E0,$A0,$A0,$A0,$A0,$E0,$E0
RoomNumber9
    byte $E0,$E0,$A0,$A0,$A0,$A0,$E0,$E0,$20,$20,$20,$20,$E0,$E0
; Fonte 5 x 7, duas scanlines por linha. A/I tem um bit vazio inicial
; para compensar a diferenca de 9 pixels entre os strobes RESP0/RESP1.
; Uma unica pagina garante LDA tabela,Y em 4 ciclos no kernel do texto.
HudFontA
    byte $38,$38,$44,$44,$44,$44,$7C,$7C,$44,$44,$44,$44,$44,$44
HudFontT
    byte $F8,$F8,$20,$20,$20,$20,$20,$20,$20,$20,$20,$20,$20,$20
HudFontR
    byte $F0,$F0,$88,$88,$88,$88,$F0,$F0,$A0,$A0,$90,$90,$88,$88
HudFontI
    byte $7C,$7C,$10,$10,$10,$10,$10,$10,$10,$10,$10,$10,$7C,$7C

; Todos os sprites cabem na mesma pagina: ponteiro e leituras sem carry.
    align 256
ArrowSprites
    byte $00,$18,$3C,$7E,$18,$18,$18,$00 ; 0: 0 graus
    byte $00,$1E,$3E,$1E,$3E,$70,$20,$00 ; 1: 45 graus
    byte $00,$08,$0C,$7E,$7E,$0C,$08,$00 ; 2: 90 graus
    byte $00,$20,$74,$3E,$1E,$3E,$1E,$00 ; 3: 135 graus
    byte $00,$18,$18,$18,$7E,$3C,$18,$00 ; 4: 180 graus
    byte $00,$04,$0E,$7C,$78,$7C,$78,$00 ; 5: 225 graus
    byte $00,$10,$30,$7E,$7E,$30,$10,$00 ; 6: 270 graus
    byte $00,$78,$78,$78,$7C,$2E,$04,$00 ; 7: 315 graus

    org $FFFA
    word Reset,Reset,Reset
