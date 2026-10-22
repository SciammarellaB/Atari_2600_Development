; Space Invaders basico: ROM de 4 KiB, CPU 6507, sintaxe DASM, video NTSC.
; Invasores = players 0/1 no alto; nave = player 0 na base; tiro = missile 0.
; Nao ha framebuffer: o programa acompanha a geracao de cada linha do TIA.
        processor 6502
        
        include "hardware.h"

; --- Coordenadas e limites ---
; X usa pixels de 0..159. Y usa PARES de linhas de 0..95: um passo Y vale
; duas linhas fisicas. Os sprites de oito bytes ficam com 16 linhas de altura.
; Duas colunas, separadas por 48 pixels, e duas fileiras, separadas por 12 pares.
ShipY       = 88
MinShipX    = 16
MaxShipX    = 144
MinFleetX   = 16
MaxFleetX   = 96         ; ultima coluna termina em 96 + 48 + 7 = 151
Offscreen   = 128        ; Y fora de 0..95: missile desativado
Playing     = 0
Won         = 1
Lost        = 2

; --- RAM do RIOT, a partir de $80 ---
; A pilha usa o espelho $0180..$01FF da mesma RAM. Estas variaveis terminam
; em $BF, deixando espaco para JSR/RTS crescerem a partir do topo $FF.
ShipX       = $80
ShotX       = $81
ShotY       = $82
FleetX      = $83
FleetY      = $84
Direction   = $85        ; 1 = direita; $FF = esquerda
MoveClock   = $86
Remaining   = $87        ; quatro invasores no inicio; zero significa vitoria
State       = $88        ; 0 = jogando; 1 = venceu; 2 = perdeu
DisplayX    = $8A
FireReady   = $8B        ; exige soltar o botao antes de reiniciar uma partida
SoundClock  = $8C
NextLeft    = $8D        ; pixels da coluna esquerda preparados antecipadamente
NextShot    = $8E
NextRight   = $8F
Alive       = $90        ; quatro bytes: superior [0..1], inferior [2..3]
HitX        = $96        ; limites temporarios para a colisao por retangulos
HitY        = $97
LeftPixels  = $98        ; 20 bytes: sprite de 8, intervalo de 4, sprite de 8
RightPixels = $AC        ; outros 20 bytes: coluna direita, sem alternar quadros

; --- Inicializacao do console ---
; SEI/CLD preparam a CPU. A limpeza escreve somente TIA ($00..$7F) e RAM
; ($80..$FF), sem tocar na ROM. O RIOT recebe SWACNT=0 para ler o joystick.
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
        lda #$10        ; missile de dois pixels, nave em tamanho normal
        sta NUSIZ0
        lda #$0E        ; nave e tiro brancos
        sta COLUP0
        lda #$C8        ; invasores verdes na paleta NTSC
        sta COLUP1
        jsr NewGame
        lda #2
        sta VBLANK
        sta WSYNC

; --- Quadro NTSC: 3 + 37 + 192 + 30 = 262 linhas ---
; VSYNC dura tres linhas. TIM64T=44 chega a zero em (44-1)*64+1 ciclos:
; o primeiro decremento do RIOT ocorre apos um ciclo, os demais apos 64.
; A expiracao ocorre na 37a linha; WSYNC alinha o inicio da regiao visivel.
Frame
        lda #2
        sta VSYNC
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC
        lda #44
        sta TIM64T
        jsr UpdateGame
        jsr PrepareSprites

; --- Posicionamento dos tres objetos durante a imagem oculta ---
; X escolhe o registrador: 0=P0, 1=P1, 2=M0. O missile precisa receber
; coordenada +1 pela diferenca entre o reset de players e de misseis do TIA.
; HMOVE so e escrito imediatamente depois de WSYNC, no inicio da linha.
        lda FleetX
        ldx #0
        jsr PositionObject
        lda DisplayX
        ldx #1
        jsr PositionObject
        lda ShotX
        clc
        adc #1
        ldx #2
        jsr PositionObject
        sta WSYNC
        sta HMOVE
        lda #0
        sta GRP0
        sta GRP1
        sta ENAM0
        sta NextLeft
        sta NextRight
        sta NextShot
        lda #$C8
        sta COLUP0
        sta COLUP1
        ldx #0
WaitBlank
        lda INTIM
        bne WaitBlank
        sta WSYNC
        sta VBLANK      ; A=0 permite a imagem; X=0 inicia o primeiro par
        jmp DrawPair    ; pula o preenchimento inserido por ALIGN

; --- Kernel superior: 84 pares = 168 linhas, quatro invasores sem flicker ---
; Cada player desenha uma coluna nos MESMOS quadros. Entre as duas fileiras,
; o buffer contem zeros. Escrevemos os desenhos antes do pixel X=16 aparecer.
; A linha A prepara os pixels do proximo par; B prepara seu tiro. ALIGN evita
; penalidades de pagina nos desvios. Nenhuma linha ultrapassa 76 ciclos.
        align 256
DrawPair
        lda NextLeft
        sta GRP0
        lda NextRight
        sta GRP1
        lda NextShot
        sta ENAM0

; --- Prepara as duas colunas do proximo par ---
; Delta negativo vira byte alto e tambem e excluido por CMP #20. O mesmo
; indice Y seleciona as duas imagens; cada buffer ja considera os mortos.
        inx
        txa
        sec
        sbc FleetY
        cmp #20
        bcs AliensBlank
        tay
        lda LeftPixels,y
        sta NextLeft
        lda RightPixels,y
        jmp SaveRight
AliensBlank
        lda #0
        sta NextLeft
SaveRight
        sta NextRight
        sta WSYNC       ; termina A, comeca B; os pixels permanecem no TIA

; --- Tiro do proximo par, quatro linhas fisicas de altura ---
; ENAM0 recebe 2 dentro do retangulo ou 0 fora. Y=128 desativa o tiro.
        txa
        sec
        sbc ShotY
        cmp #2
        lda #0
        bcs SaveShot
        lda #2
SaveShot
        sta NextShot
        sta WSYNC       ; termina B
        cpx #84
        bne DrawPair

; --- Faixa de troca: oito linhas reservadas, de 168 ate 175 ---
; O player 0 deixa a coluna esquerda e passa a nave. Ocultamos somente esta
; faixa para reposicionar sem desenhar residuos. O tiro tambem fica oculto
; ao atravessa-la. HMCLR zera ajustes antigos: HMOVE deve mover apenas P0.
; TIM64T=10 chega a zero em 577 ciclos, na oitava linha desta faixa.
; O WSYNC seguinte inicia a nave na linha 176 da regiao visivel.
        lda #2
        sta VBLANK
        lda #10
        sta TIM64T
        lda #0
        sta GRP0
        sta GRP1
        sta ENAM0
        sta HMCLR
        lda ShipX
        ldx #0
        jsr PositionObject
        sta WSYNC
        sta HMOVE
        lda #$0E
        sta COLUP0      ; nave branca; o tiro compartilha esta cor no rodape
        ldx #0
WaitShip
        lda INTIM
        bne WaitShip
        sta WSYNC
        sta VBLANK      ; A=0, permite as ultimas 16 linhas da regiao visivel

; --- Nave: oito pares = 16 linhas, de 176 ate 191 ---
; O bitmap fornece oito pixels por linha. O tiro pode nascer acima da nave;
; nesta regiao ele ja esta desativado, pois seu Y inicial e ShipY-2.
DrawShip
        lda ShipBitmap,x
        sta GRP0
        sta WSYNC
        sta WSYNC
        inx
        cpx #8
        bne DrawShip

; --- Overscan: 30 linhas com a imagem oculta ---
; Apagar GRP0/GRP1/ENAM0 impede residuos no proximo quadro. Toda a logica
; fica em VBLANK; aqui o contador garante exatamente 30 linhas adicionais.
        lda #2
        sta VBLANK
        lda #0
        sta GRP0
        sta GRP1
        sta ENAM0
        ldx #30
Overscan
        sta WSYNC
        dex
        bne Overscan
        jmp Frame

; --- Nova partida: quatro vivos, nave centralizada, nenhum tiro ---
; Esta rotina tambem atende Game Reset e o reinicio depois do fim da partida.
; FireReady=0 evita que o tiro que encerrou a partida reinicie automaticamente.
NewGame
        lda #76
        sta ShipX
        sta ShotX
        lda #Offscreen
        sta ShotY
        lda #32
        sta FleetX
        lda #12
        sta FleetY
        lda #1
        sta Direction
        ldx #3
Revive
        sta Alive,x
        dex
        bpl Revive
        lda #4
        sta Remaining
        lda #0
        sta State
        sta MoveClock
        sta FireReady
        sta SoundClock
        sta AUDV0
        sta COLUBK
        rts

; --- Entrada e estados: Game Reset funciona a qualquer momento ---
; O bit 0 de SWCHB e ativo em zero. Nos estados finais, soltar e apertar
; tiro reinicia; durante a partida, segurar tiro permite disparos sucessivos.
UpdateGame
        lda SWCHB
        and #1
        bne CheckState
        jmp NewGame
CheckState
        lda State
        beq PlayingFrame
        lda INPT4
        bpl RestartPressed
        lda #1
        sta FireReady
        rts
RestartPressed
        lda FireReady
        beq UpdateDone
        jmp NewGame
UpdateDone
        rts

; --- Som curto: o volume zera quando o contador termina ---
; O mesmo canal toca o disparo ou o impacto mais recente. Nao ha musica.
PlayingFrame
        lda SoundClock
        beq ReadMovement
        dec SoundClock
        bne ReadMovement
        lda #0
        sta AUDV0

; --- Movimento horizontal da nave, um pixel por quadro ---
; BIT testa as mascaras de esquerda/direita sem alterar A. Limites 16..144
; deixam margem para escrever os registradores antes dos objetos aparecerem.
ReadMovement
        ldx ShipX
        lda #$40
        bit SWCHA
        bne ReadRight
        cpx #MinShipX
        beq ReadRight
        dex
ReadRight
        lda #$80
        bit SWCHA
        bne SaveMovement
        cpx #MaxShipX
        beq SaveMovement
        inx
SaveMovement
        stx ShipX

; --- Atualizacao da formacao e do tiro ---
; Primeiro move os invasores, depois o tiro e finalmente testa a colisao.
; Uma derrota encerra o quadro logico sem permitir outro disparo.
        jsr MoveFleet
        lda State
        bne UpdateDone
        lda ShotY
        cmp #Offscreen
        beq TryFire
        cmp #2
        bcc RemoveShot
        sec
        sbc #2          ; sobe quatro linhas fisicas por quadro
        sta ShotY
        jmp CheckHits
RemoveShot
        lda #Offscreen
        sta ShotY
TryFire
        lda INPT4
        bmi UpdateDone
        lda ShipX
        clc
        adc #3          ; tiro alinhado com o centro da nave de oito pixels
        sta ShotX
        lda #ShipY-2
        sta ShotY
        lda #4          ; onda tonal para o disparo
        sta AUDC0
        lda #12
        sta AUDF0
        lda #5
        sta AUDV0
        lda #5
        sta SoundClock
        rts

; --- Colisao com os quatro invasores, todos visiveis em cada quadro ---
; Cada vivo tem retangulo 8 pixels x 8 pares; o tiro mede 2 pixels x 2 pares.
; (tiro - inicio + 1) < 9 aceita deltas -1..7: inclui a largura/altura do tiro.
; X percorre a fileira inferior primeiro. Uma colisao consome exatamente um tiro.
CheckHits
        ldx #3
HitLoop
        lda Alive,x
        beq NextTarget
        lda FleetX
        clc
        adc ColumnOffsets,x
        sta HitX
        lda FleetY
        clc
        adc RowOffsets,x
        sta HitY
        lda ShotX
        sec
        sbc HitX
        clc
        adc #1
        cmp #9
        bcs NextTarget
        lda ShotY
        sec
        sbc HitY
        clc
        adc #1
        cmp #9
        bcs NextTarget

; --- Impacto: apaga um invasor, encerra o tiro e toca ruido ---
; Remaining e o numero de vivos. Ao chegar a zero, o fundo verde indica
; vitoria e a logica congela ate um novo clique de tiro ou Game Reset.
        lda #0
        sta Alive,x
        lda #Offscreen
        sta ShotY
        lda #8
        sta AUDC0
        sta SoundClock
        lda #6
        sta AUDF0
        sta AUDV0
        dec Remaining
        bne HitDone
        lda #Won
        sta State
        lda #$C2
        sta COLUBK
        lda #0
        sta AUDV0
HitDone
        rts
NextTarget
        dex
        bpl HitLoop
        rts

; --- Marcha dos invasores: um pixel a cada quatro quadros ---
; Com dois ou menos vivos, o intervalo cai para dois quadros. Nos extremos,
; inverte a direcao e desce quatro pares (oito linhas), sem ultrapassar X.
MoveFleet
        inc MoveClock
        ldy #4
        lda Remaining
        cmp #3
        bcs TestClock
        ldy #2
TestClock
        sty HitX        ; temporario reutilizado antes da fase de colisao
        lda MoveClock
        cmp HitX
        bcc FleetDone
        lda #0
        sta MoveClock
        lda Direction
        bmi FleetLeft
        lda FleetX
        cmp #MaxFleetX
        beq TurnLeft
        inc FleetX
        rts
FleetLeft
        lda FleetX
        cmp #MinFleetX
        beq TurnRight
        dec FleetX
        rts
TurnLeft
        lda #$FF
        bne Descend
TurnRight
        lda #1
Descend
        sta Direction
        lda FleetY
        clc
        adc #4
        sta FleetY

; --- Derrota ao atingir a faixa de troca acima da nave ---
; Em FleetY=64 a fileira inferior termina no par 83, antes da faixa de troca.
; O limite considera a fileira inferior mesmo se ela ja foi destruida:
; a formacao conserva seu retangulo original, simplificando este primeiro jogo.
        cmp #ShipY-24
        bcc FleetDone
        lda #Lost
        sta State
        lda #Offscreen
        sta ShotY
        lda #$42        ; vermelho escuro indica derrota
        sta COLUBK
        lda #0
        sta AUDV0
FleetDone
        rts

; --- Prepara as duas colunas em buffers independentes, uma vez por quadro ---
; Os dois players desenham os inimigos juntos. A reutilizacao de P0 acontece
; verticalmente, na faixa de troca, sem alternar inimigos entre quadros.
PrepareSprites
        lda FleetX
        clc
        adc #48
        sta DisplayX
        ldy #7
CopyRows
        lda Alive
        beq StoreLeftTop
        lda AlienBitmap,y
StoreLeftTop
        sta LeftPixels,y
        lda Alive+1
        beq StoreRightTop
        lda AlienBitmap,y
StoreRightTop
        sta RightPixels,y
        lda Alive+2
        beq StoreLeftBottom
        lda AlienBitmap,y
StoreLeftBottom
        sta LeftPixels+12,y
        lda Alive+3
        beq StoreRightBottom
        lda AlienBitmap,y
StoreRightBottom
        sta RightPixels+12,y
        dey
        bpl CopyRows

; --- Quatro pares vazios entre fileiras ---
; A mesma altura e usada nas tabelas de colisao. Os bytes sao renovados para
; tornar a preparacao explicita, embora zero inicial tambem fosse suficiente.
        lda #0
        ldy #3
ClearGap
        sta LeftPixels+8,y
        sta RightPixels+8,y
        dey
        bpl ClearGap
        rts

; --- Posicao horizontal por tempo: A=coordenada, X=indice do objeto ---
; Cada SBC/BCS tomado custa cinco ciclos = 15 pixels. O resto negativo
; passa por EOR/ASL para formar o ajuste fino de -8..+7 do TIA.
; STA.wx forca enderecamento absoluto,X (5 ciclos), necessario nesta formula;
; trocar por STA comum reduz um ciclo e desloca o objeto tres pixels.
; Com A <= 148, a rotina retorna antes de acabar a linha de 76 ciclos.
        align 256
PositionObject
        sec
        sta WSYNC
Divide15
        sbc #15
        bcs Divide15
        eor #7
        asl
        asl
        asl
        asl
        sta.wx HMP0,x
        sta RESP0,x
        rts

; --- Dados graficos originais deste estudo ---
; Cada bit 1 acende um pixel; o bit 7 fica a esquerda. O kernel repete cada
; linha duas vezes. ALIGN evita que LDA tabela,Y custe um ciclo adicional.
        align 256
ShipBitmap
        byte %00011000
        byte %00011000
        byte %00111100
        byte %01111110
        byte %11111111
        byte %11111111
        byte %11111111
        byte %11111111
AlienBitmap
        byte %00100100
        byte %00011000
        byte %00111100
        byte %01111110
        byte %11011011
        byte %11111111
        byte %00100100
        byte %01000010

; --- Formacao em ordem de indices 0..3 ---
; Os offsets permitem usar a mesma geometria tanto no desenho quanto no teste
; de colisao. Mudar espacamentos exige rever limites e altura da formacao.
ColumnOffsets
        byte 0,48,0,48
RowOffsets
        byte 0,0,12,12

; --- Vetores no fim da ROM: todos apontam para Reset ---
; ORG preenche o espaco ate $FFFA; $F000..$FFFF totalizam 4096 bytes sem bankswitch.
        org $FFFA
        word Reset
        word Reset
        word Reset
