; Jogador branco (8 x 16) e quatro caixas fixas (16 x 32), com colisao AABB.
; ROM de 4 KiB, sem bankswitching. NTSC: 3 + 37 + 192 + 30 = 262 linhas.
    processor 6502

; 1. HARDWARE: constantes nomeiam enderecos, sem reservar RAM.
; WSYNC pausa ate a proxima linha; cada linha NTSC tem 76 ciclos de CPU.
VSYNC   = $00
VBLANK  = $01
WSYNC   = $02
COLUBK  = $09
HMOVE   = $2A

; Playfield: cada bit tem 4 pixels. CTRLPF bit 0 espelha a metade direita.
; PF0 fica zerado no Reset; PF1/PF2 desenham dois pares de caixas espelhadas.
COLUPF  = $08
CTRLPF  = $0A
PF1     = $0E
PF2     = $0F

; Player 0: GRP0 fornece 8 pixels; RESP0 posiciona por tempo; HMP0 ajusta
; os pixels restantes. HMOVE aplica o ajuste durante a preparacao da tela.
COLUP0  = $06
RESP0   = $10
GRP0    = $1B
HMP0    = $20

; Joystick 1: bits 4/5/6/7 = cima/baixo/esquerda/direita, ativos em 0.
; SWACNT = 0 configura as portas como entrada.
SWCHA   = $0280
SWACNT  = $0281

; 2. GEOMETRIA: X/Y sao o canto superior esquerdo; Y cresce para baixo.
; Preservamos as bordas e os passos anteriores: 1 pixel em X, 2 linhas em Y.
PlayerWidth  = 8
SquareHeight = 16
MinX = 8
MaxX = 160 - 16
MinY = 16
MaxY = 192 - SquareHeight - 16

; Quatro retangulos: direita/base sao exclusivas, encostar e permitido.
; As duas caixas de cima usam PF1; as duas de baixo usam PF2.
; Cada caixa tem 16 pixels por 32 linhas. Os pares sao espelhados em X = 80.
BlockCount = 4
Block1Left = 32
Block1Right = 48
Block1Top = 40
Block1Bottom = 72
Block2Left = 160 - Block1Right
Block2Right = 160 - Block1Left
Block2Top = Block1Top
Block2Bottom = Block1Bottom
Block3Left = 56
Block3Right = 72
Block3Top = 112
Block3Bottom = 144
Block4Left = 160 - Block3Right
Block4Right = 160 - Block3Left
Block4Top = Block3Top
Block4Bottom = Block3Bottom

; 3. RAM: PreviousPos desfaz o eixo bloqueado. CollisionFound acumula o
; resultado das quatro caixas; PlayerPixels guarda GRP0 enquanto Y indexa
; o cenario. A pilha usa o espelho da RAM; nao deve atingir estas variaveis.
XPos           = $80
YPos           = $81
PreviousPos    = $82
CollisionFound = $83
PlayerPixels   = $84

; 4. RESET: desabilita interrupcoes, usa aritmetica binaria e limpa RAM/TIA.
; NUSIZ0 fica em 0: uma unica copia do player, com largura normal de 8 pixels.
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

; Fundo azul, jogador branco e caixas amarelas em NTSC. A imagem fica apagada
; durante a preparacao; o jogador inicia no corredor entre as duas faixas.
    lda #$84
    sta COLUBK
    lda #$0E
    sta COLUP0
    lda #$1E
    sta COLUPF
    lda #1
    sta CTRLPF
    lda #2
    sta VBLANK
    sta WSYNC
    lda #40
    sta XPos
    lda #80
    sta YPos

; 5. QUADRO: VSYNC fica ligado por 3 linhas. A preparacao usa VBLANK = 2.
Frame
    lda #2
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC

; ReadJoystick usa 13 WSYNC: 5 de leitura/retorno e 4 caixas em cada eixo.
; PositionPlayer usa 2; a espera usa 21: 13 + 2 + 21 + 1 = 37.
; O primeiro WSYNC de DrawLine completa a 37a linha de preparacao.
; Todo caminho entre esperas deve terminar antes dos 76 ciclos da linha.
    jsr ReadJoystick
    jsr PositionPlayer
    ldx #0
    ldy #21
WaitVerticalBlank
    sta WSYNC
    dey
    bne WaitVerticalBlank

; 6. KERNEL: X conta 0..191. (linha - YPos) < 16 seleciona o jogador.
; Acima do topo, a subtracao de 8 bits produz um valor alto, tambem rejeitado.
; PlayerPixels guarda seus 8 pixels. Tres LSR calculam linha / 8 em Y para
; selecionar uma das 24 faixas do cenario, como no estudo Movimentacao Cenario.
DrawLine
    txa
    sec
    sbc YPos
    cmp #SquareHeight
    lda #0
    bcs PlayerReady
    lda #%11111111
PlayerReady
    sta PlayerPixels
    txa
    lsr
    lsr
    lsr
    tay
    lda ScenePF1,y
    sta WSYNC
    sta PF1
    lda ScenePF2,y
    sta PF2
    lda PlayerPixels
    sta GRP0

; PF1 e escrito no ciclo 3, PF2 no 10, GRP0 no 16 e VBLANK no 21.
; Tudo fica pronto antes dos respectivos pixels; VBLANK ainda muda no blank
; horizontal. Repetir VBLANK = 0 evita um caso especial na primeira linha.
; As tabelas estao na mesma pagina para evitar custo extra por indice Y.
    lda #0
    sta VBLANK
    inx
    cpx #192
    bne DrawLine

; 7. OVERSCAN: espera a ultima linha visivel terminar antes de apagar a tela.
; Depois das 30 linhas de overscan, o proximo quadro volta a ligar VSYNC.
    sta WSYNC
    lda #2
    sta VBLANK
    lda #0
    sta GRP0
    sta PF1
    sta PF2
    ldx #30
WaitOverscan
    sta WSYNC
    dex
    bne WaitOverscan
    jmp Frame

; 8. HORIZONTAL: salva X, tenta esquerda/direita e respeita as bordas.
; A ordem e o passo de 1 pixel sao preservados. O teste AABB fica na linha
; seguinte; CheckCollision reserva mais 4 linhas, uma por caixa. Assim cada
; caminho respeita o limite de 76 ciclos, mesmo sem encontrar uma colisao.
ReadJoystick
    sta WSYNC
    lda XPos
    sta PreviousPos
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
    bne CheckHorizontalCollision
    cpx #MaxX
    beq CheckHorizontalCollision
    inx
    stx XPos
CheckHorizontalCollision
    sta WSYNC
    jsr CheckCollision
    bcc HorizontalDone
    lda PreviousPos
    sta XPos
HorizontalDone

; 9. VERTICAL: salva Y e usa o X ja aceito. Se colidir, desfaz apenas Y.
; Na diagonal, o eixo livre permite deslizar pela parede. O passo continua 2.
    sta WSYNC
    lda YPos
    sta PreviousPos
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
    bne CheckVerticalCollision
    cpx #MaxY
    beq CheckVerticalCollision
    inx
    inx
    stx YPos
CheckVerticalCollision
    sta WSYNC
    jsr CheckCollision
    bcc VerticalDone
    lda PreviousPos
    sta YPos
VerticalDone
    sta WSYNC
    rts

; 10. AABB: testa as quatro caixas, uma por linha de preparacao.
; Para cada caixa, exige X < direita, X + largura > esquerda, Y < base e
; Y + altura > topo. As tabelas MinX/MinY reorganizam as duas somas:
; X + 8 > esquerda equivale a X >= esquerda - 8 + 1 (Y usa altura 16).
; X indexa 0..3; CollisionFound inicia em 0 e vira 1 se alguma caixa bloquear.
; Mesmo depois de colidir, percorremos as demais para manter 4 WSYNC fixos.
; Retorna carry = 1 se colidiu, 0 se livre; altera A/X/flags, preserva Y.
CheckCollision
    lda #0
    sta CollisionFound
    ldx #0
CheckNextBlock
    sta WSYNC
    lda XPos
    cmp BlockRights,x
    bcs NextBlock
    cmp BlockMinX,x
    bcc NextBlock
    lda YPos
    cmp BlockBottoms,x
    bcs NextBlock
    cmp BlockMinY,x
    bcc NextBlock
    lda #1
    sta CollisionFound
NextBlock
    inx
    cpx #BlockCount
    bne CheckNextBlock

; LSR leva o bit 0 de CollisionFound ao carry, o retorno usado pelo chamador.
; As caixas sao apenas dados na ROM: nenhuma instrucao altera sua posicao.
    lda CollisionFound
    lsr
    rts

; 11. POSICAO HORIZONTAL: preserva a calibracao do exemplo anterior.
; Cada subtracao de 15 com desvio tomado custa 5 ciclos = 15 color clocks.
; RESP0 posiciona; quatro ASL levam o ajuste fino ao nibble alto de HMP0.
; Os dois NOP e a ordem das escritas fazem parte do timing, nao sao enfeites.
; Em X = 144, o segundo WSYNC ainda e atingido antes dos 76 ciclos.
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

; 12. DADOS NA ROM: alinhar em 256 garante que cada tabela indexada
; permaneça na mesma pagina. O kernel usa Y = 0..23; a AABB usa X = 0..3.
; Cada byte de cenario vale por 8 linhas, totalizando 24 * 8 = 192.
; PF1 bits 3..0 cobrem X = 32..47; espelhados, cobrem X = 112..127.
; As faixas 5..8 desenham as caixas 1/2 em Y = 40..71.
    align 256
ScenePF1
    ds 5, 0
    byte $0F, $0F, $0F, $0F
    ds 15, 0

; PF2 bits 2..5 cobrem X = 56..71; espelhados, cobrem X = 88..103.
; As faixas 14..17 desenham as caixas 3/4 em Y = 112..143.
; PF0 permanece vazio, e o overscan limpa PF1/PF2 antes do quadro seguinte.
ScenePF2
    ds 14, 0
    byte $3C, $3C, $3C, $3C
    ds 6, 0

; Uma entrada por caixa, sempre na ordem 1, 2, 3, 4. As expressoes calculadas
; pelo DASM mantem o teste ligado as constantes geometricas, sem somas na CPU.
; Mudar X exige ajustar tambem as mascaras do playfield; mudar Y exige ajustar
; as faixas de 8 linhas das tabelas acima. O desenho e a AABB devem coincidir.
BlockRights
    byte Block1Right, Block2Right, Block3Right, Block4Right
BlockMinX
    byte Block1Left - PlayerWidth + 1, Block2Left - PlayerWidth + 1
    byte Block3Left - PlayerWidth + 1, Block4Left - PlayerWidth + 1
BlockBottoms
    byte Block1Bottom, Block2Bottom, Block3Bottom, Block4Bottom
BlockMinY
    byte Block1Top - SquareHeight + 1, Block2Top - SquareHeight + 1
    byte Block3Top - SquareHeight + 1, Block4Top - SquareHeight + 1

; 13. VETORES: completam a ROM ate $FFFF e apontam a Reset ($F000).
; NMI/IRQ nao sao usados pelo 6507; RESET e o vetor de inicializacao.
    org $FFFA
    word Reset
    word Reset
    word Reset
