; Quatro caixas detalhadas, playfield assimetrico e colisao AABB separada.
; Jogador de 8 x 16; caixas de 16 x 32; cada faixa grafica ocupa 2 linhas.
; ROM de 4 KiB, sem bankswitching. NTSC: 3 + 37 + 192 + 30 = 262 linhas.
    processor 6502

; 1. HARDWARE: constantes nomeiam enderecos, sem reservar RAM.
; WSYNC pausa ate a proxima linha; cada linha NTSC tem 76 ciclos de CPU.
VSYNC   = $00
VBLANK  = $01
WSYNC   = $02
COLUBK  = $09
HMOVE   = $2A

; Playfield: cada bit tem 4 pixels. CTRLPF = 0 seleciona repeticao normal.
; Para tornar as metades independentes, o kernel reescreve PF0/PF1/PF2 no
; meio de CADA linha. So desligar a reflexao ainda repetiria a metade esquerda.
COLUPF  = $08
CTRLPF  = $0A
PF0     = $0D
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

; Quatro retangulos independentes: direita/base sao exclusivas.
; As caixas continuam solidas para a AABB; os vazios no desenho sao textura,
; nao passagens. Agora nenhuma coordenada e derivada por espelhamento.
BlockCount = 4
Block1Left = 24
Block1Right = 40
Block1Top = 32
Block1Bottom = 64
Block2Left = 92
Block2Right = 108
Block2Top = 48
Block2Bottom = 80
Block3Left = 48
Block3Right = 64
Block3Top = 120
Block3Bottom = 152
Block4Left = 124
Block4Right = 140
Block4Top = 104
Block4Bottom = 136

; 3. RAM: PreviousPos desfaz o eixo bloqueado; CollisionFound acumula AABB.
; PlayerPixels vale para a faixa atual; NextPlayerPixels prepara a seguinte.
; PlayerRowBefore = YPos / 2 - 1 permite calcular essa faixa sem somar 1 no
; kernel. YPos e sempre par (inicio 80, passo 2) e a altura 16 equivale a
; 8 faixas. A pilha compartilha a RAM e nao deve atingir estas variaveis.
XPos             = $80
YPos             = $81
PreviousPos      = $82
CollisionFound   = $83
PlayerPixels     = $84
NextPlayerPixels = $85
PlayerRowBefore  = $86

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

; Fundo azul, jogador branco e caixas amarelas em NTSC. O jogador inicia
; em (40,80), fora das quatro caixas. CTRLPF = 0 desliga a reflexao.
    lda #$84
    sta COLUBK
    lda #$0E
    sta COLUP0
    lda #$1E
    sta COLUPF
    lda #0
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
; O primeiro WSYNC do kernel completa a 37a linha de preparacao.
; Todo caminho entre esperas deve terminar antes dos 76 ciclos da linha.
    jsr ReadJoystick

; Converte o topo do jogador em indice de faixa antes da imagem visivel.
; LSR divide YPos par por 2; SEC/SBC subtraem 1 sem emprestimo adicional.
    lda YPos
    lsr
    sec
    sbc #1
    sta PlayerRowBefore
    jsr PositionPlayer
    ldy #21
WaitVerticalBlank
    sta WSYNC
    dey
    bne WaitVerticalBlank

; 6. KERNEL DE DUAS LINHAS: Y indexa 96 faixas de 2 linhas (192 no total).
; O jogador nao aparece na faixa 0: MinY = 16. Inicializamos seus pixels em
; zero; o primeiro WSYNC completa a 37a linha de preparacao. STA VBLANK usa
; 3 ciclos na primeira linha; nas seguintes, JMP DrawFirstLine usa os mesmos 3.
    ldy #0
    lda #0
    sta PlayerPixels
    sta WSYNC
    sta VBLANK
DrawFirstLine

; Metade esquerda: GRP0 no ciclo 9, PF0 no 16, PF1 no 23 e PF2 no 30.
; Os dados sao buscados na ROM, em tabelas de 96 bytes alinhadas em paginas.
; Cada bit 1 desenha amarelo; cada 0 deixa aparecer o fundo azul.
    lda PlayerPixels
    sta GRP0
    lda SceneLeftPF0,y
    sta PF0
    lda SceneLeftPF1,y
    sta PF1
    lda SceneLeftPF2,y
    sta PF2

; Metade direita: PF0 no ciclo 39, PF1 no 46, PF2 no 53. O NOP faz parte do
; timing: aguardamos cada registrador terminar seu trecho esquerdo antes de
; substitui-lo. A mesma linha passa a ter OUTROS bits na metade direita.
    nop
    lda SceneRightPF0,y
    sta PF0
    lda SceneRightPF1,y
    sta PF1
    lda SceneRightPF2,y
    sta PF2

; Prepara o jogador da PROXIMA faixa, enquanto a atual ainda esta no TIA.
; Para a faixa r+1: (r - (YPos/2 - 1)) < 8 seleciona as 8 faixas do jogador.
; A subtracao acima do topo produz um byte alto, rejeitado por CMP. O desvio
; escolhe zero ou $FF; guardamos o resultado sem alterar os pixels atuais.
    tya
    sec
    sbc PlayerRowBefore
    cmp #8
    lda #0
    bcs NextPlayerReady
    lda #$FF
NextPlayerReady
    sta NextPlayerPixels
    sta WSYNC
DrawSecondLine

; Segunda linha da MESMA faixa: sem o prefixo de 3 ciclos, GRP0 e escrito no
; ciclo 6, PF0 no 13, PF1 no 20 e PF2 no 27. Usamos os mesmos dados e indice Y.
    lda PlayerPixels
    sta GRP0
    lda SceneLeftPF0,y
    sta PF0
    lda SceneLeftPF1,y
    sta PF1
    lda SceneLeftPF2,y
    sta PF2

; Atualizacoes direitas nos ciclos 36/43/50. As janelas sao diferentes para
; cada registrador: PF0 esquerdo termina no ciclo 28, PF1 em 38 2/3 e PF2
; em 49 1/3. PF2 direito so e usado a partir de 65 1/3: escrever no 50 cabe.
    nop
    lda SceneRightPF0,y
    sta PF0
    lda SceneRightPF1,y
    sta PF1
    lda SceneRightPF2,y
    sta PF2

; Promove os pixels preparados e avanca a faixa. O desvio final ocorre apenas
; depois de desenhar as duas linhas. WSYNC seguido de JMP inicia a proxima
; primeira linha com o mesmo prefixo de 3 ciclos usado por STA VBLANK.
    lda NextPlayerPixels
    sta PlayerPixels
    iny
    cpy #96
    beq VisibleDone
    sta WSYNC
    jmp DrawFirstLine
VisibleDone

; 7. OVERSCAN: espera a ultima linha visivel terminar antes de apagar a tela.
; Depois das 30 linhas de overscan, o proximo quadro volta a ligar VSYNC.
    sta WSYNC
    lda #2
    sta VBLANK
    lda #0
    sta GRP0
    sta PF0
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
; Alinhar em 32 mantem o laco SBC/BCS na mesma pagina, sem ciclos extras.
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

; 12. CENARIO: seis tabelas independentes, uma por registrador e metade.
; Cada entrada vale por 2 linhas; 96 entradas cobrem as 192 linhas visiveis.
; Cada tabela comeca em uma pagina de 256 bytes para que LDA tabela,Y sempre
; custe 4 ciclos. PF0 usa bits 4..7; PF1 usa 7..0; PF2 usa 0..7 em cada metade.
; As bordas externas coincidem com as quatro AABBs. O contorno e as travessas
; sao textura: $F e a linha cheia; $9 liga as extremidades; $D/$B acrescentam
; uma celula interna. A ROM anterior foi preservada em referencias/.
; SceneLeftPF0: metade esquerda.
    align 256
SceneLeftPF0
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 0..15
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 16..31
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 32..47
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 48..63
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 64..79
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 80..95
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 96..111
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 112..127
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 128..143
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 144..159
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 160..175
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 176..191

; SceneLeftPF1: metade esquerda.
    align 256
SceneLeftPF1
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 0..15
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 16..31
    byte $3C, $3C, $24, $34, $34, $2C, $2C, $24 ; Y = 32..47
    byte $24, $2C, $2C, $34, $34, $24, $3C, $3C ; Y = 48..63
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 64..79
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 80..95
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 96..111
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 112..127
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 128..143
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 144..159
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 160..175
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 176..191

; SceneLeftPF2: metade esquerda.
    align 256
SceneLeftPF2
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 0..15
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 16..31
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 32..47
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 48..63
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 64..79
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 80..95
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 96..111
    byte $00, $00, $00, $00, $0F, $0F, $09, $0B ; Y = 112..127
    byte $0B, $0D, $0D, $09, $09, $0D, $0D, $0B ; Y = 128..143
    byte $0B, $09, $0F, $0F, $00, $00, $00, $00 ; Y = 144..159
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 160..175
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 176..191

; SceneRightPF0: metade direita, sem reflexao.
    align 256
SceneRightPF0
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 0..15
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 16..31
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 32..47
    byte $80, $80, $80, $80, $80, $80, $80, $80 ; Y = 48..63
    byte $80, $80, $80, $80, $80, $80, $80, $80 ; Y = 64..79
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 80..95
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 96..111
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 112..127
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 128..143
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 144..159
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 160..175
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 176..191

; SceneRightPF1: metade direita, sem reflexao.
    align 256
SceneRightPF1
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 0..15
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 16..31
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 32..47
    byte $E0, $E0, $20, $A0, $A0, $60, $60, $20 ; Y = 48..63
    byte $20, $60, $60, $A0, $A0, $20, $E0, $E0 ; Y = 64..79
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 80..95
    byte $00, $00, $00, $00, $01, $01, $01, $01 ; Y = 96..111
    byte $01, $01, $01, $01, $01, $01, $01, $01 ; Y = 112..127
    byte $01, $01, $01, $01, $00, $00, $00, $00 ; Y = 128..143
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 144..159
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 160..175
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 176..191

; SceneRightPF2: metade direita, sem reflexao.
    align 256
SceneRightPF2
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 0..15
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 16..31
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 32..47
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 48..63
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 64..79
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 80..95
    byte $00, $00, $00, $00, $07, $07, $04, $05 ; Y = 96..111
    byte $05, $06, $06, $04, $04, $06, $06, $05 ; Y = 112..127
    byte $05, $04, $07, $07, $00, $00, $00, $00 ; Y = 128..143
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 144..159
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 160..175
    byte $00, $00, $00, $00, $00, $00, $00, $00 ; Y = 176..191

; Uma entrada por caixa, sempre na ordem 1, 2, 3, 4. As expressoes calculadas
; pelo DASM mantem o teste ligado as constantes geometricas, sem somas na CPU.
; Mudar X exige ajustar os bits na metade correspondente; mudar Y exige
; ajustar as faixas de 2 linhas. O contorno desenhado e a AABB devem coincidir.
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
