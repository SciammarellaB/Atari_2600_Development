; H.E.R.O. didatico: CPU 6507, DASM, ROM de 4 KiB, video NTSC.
; P0 = heroi; M0 = laser; M1 = dinamite; P1 e reutilizado VERTICALMENTE.
; Morcego, bateria, cristal e mineiro aparecem em TODOS os quadros, sem flicker.
; O playfield espelhado desenha a mina. Sprites e mapas sao deste estudo.
        processor 6502
        include "hardware.h"

; --- Unidades e limites ---
; X mede pixels de 0..159; Y mede pares de linhas de 0..87 na caverna.
; O painel ocupa outras 16 linhas: 16 + 88*2 = 192 linhas visiveis.
; O heroi mede 8 pixels por 8 pares (16 linhas); cada tile mede 4 por 8 pares.
MinX        = 20
MaxX        = 132
Offscreen   = 128
Playing     = 0
Won         = 1
Lost        = 2
MaxEnergy   = 64

; --- RAM do RIOT: estado persistente entre os quadros ---
; A RAM termina em $FF e e espelhada na pilha $0180..$01FF. Os dados abaixo
; terminam em $D6, deixando $D7..$FF livres para a pilha dos JSR/RTS.
HeroX       = $80
HeroY       = $81
Facing      = $82       ; 0 = direita; 8 = esquerda, valor aceito por REFP0
Clock       = $83
Room        = $84       ; 0 = mina ocre; 1 = galeria azul
State       = $85       ; 0 jogando, 1 resgate concluido, 2 derrota
Energy      = $86
EnergyClock = $87       ; perde uma unidade a cada 32 quadros
Bombs       = $88
BombTimer   = $89       ; 60..1 = pavio; 0 = nenhuma bomba
BombX       = $8A
BombY       = $8B
WallAlive   = $8C
WallHits    = $8D       ; oito impactos de laser tambem destroem a parede
EnemyAlive  = $8E
EnemyX      = $8F
EnemyDir    = $90       ; 1 = direita; $FF = esquerda
FuelAlive   = $91
GemAlive    = $92
Gems        = $93       ; 0..2 cristais coletados nesta partida
ShotX       = $94
ShotY       = $95       ; 128 desliga o missile
ShotDir     = $96
DownReady   = $97       ; exige soltar baixo entre duas bombas
FireReady   = $98       ; exige novo clique para reiniciar um estado final
SoundClock  = $99
Flash       = $9A       ; quadros restantes do clarao da explosao

; --- Preparacao do proximo quadro e temporarios ---
; O kernel le Next*, preparados um par antes. Candidate* guarda a posicao
; tentada antes de aceitar um movimento; Point* representa um ponto do mapa.
ActorX      = $9B
ActorY      = $9C
ActorColor  = $9D
SpritePtr   = $9E       ; dois bytes: ponteiro indireto para o bitmap de P1
NextHero    = $A0
NextActor   = $A1
FirstActorPixel = $A2   ; prefill do mineiro no evento72; zero nos demais
NextPF1     = $A3
NextPF2     = $A4
CandidateX  = $A5
CandidateY  = $A6
PointX      = $A7
PointY      = $A8
TileRow     = $AA
FuelMask    = $AB
BombMask    = $AC
StatusMask  = $AD
Background  = $AE
RockColor   = $AF
VisibleSlots = $B0      ; tres bytes: bateria, cristal e mineiro presentes
BombDisplayY = $B3      ; linha da carga M1; 128 enquanto nao houver pavio
HeroPixels  = $B8       ; oito bytes do heroi, com helice animada
Map1        = $C0       ; onze bandas do PF1, cada banda com 16 linhas
Map2        = $CB       ; onze bandas do PF2, incluindo a parede removivel
HudColor    = $D6

; --- Inicializacao ---
; SEI desliga interrupcoes, CLD escolhe aritmetica binaria, TXS prepara a
; pilha. A limpeza so percorre TIA e RAM; nao tenta escrever no cartucho.
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
        lda #1
        sta CTRLPF      ; repete a metade esquerda como um espelho
        lda #$30
        sta NUSIZ0      ; missile de oito pixels; heroi em tamanho normal
        sta NUSIZ1      ; M1 tambem tem oito pixels; P1 nao usa copias
        jsr NewGame
        lda #2
        sta VBLANK
        sta WSYNC
        jmp Frame       ; iguala a fase inicial a do retorno do overscan

; --- Quadro NTSC: 3 VSYNC + 37 VBLANK + 192 visiveis + 30 overscan ---
; O timer cobre preparacao e posicionamento. TIM64T=44 expira dentro da
; 37a linha; WSYNC alinha a imagem. A logica do jogo fica no overscan abaixo.
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
        jsr PrepareGraphics
        lda HeroX
        ldx #0
        jsr PositionObject
        lda ActorX
        ldx #1
        jsr PositionObject
        lda ShotX
        clc
        adc #1          ; reset de M0 difere um pixel do reset de um player
        ldx #2
        jsr PositionObject
        lda BombX
        clc
        adc #1
        ldx #3
        jsr PositionObject
        sta WSYNC
        sta HMOVE       ; sempre no inicio da linha, durante VBLANK
        lda Facing
        sta REFP0
        lda #$2E
        sta COLUP0
        lda ActorColor
        sta COLUP1
        lda #0
        sta GRP0
        sta GRP1
        sta ENAM0
        sta ENAM1
        sta PF0
        sta PF2
        sta NextHero
        sta NextActor
        sta FirstActorPixel
        lda FuelMask
        sta PF1
        lda HudColor
        sta COLUPF
        lda #0
        sta COLUBK
WaitBlank
        lda INTIM
        bne WaitBlank
        sta WSYNC
        sta VBLANK

; --- Painel: oito linhas de energia e oito de inventario ---
; A barra verde/vermelha possui oito segmentos, cada qual vale oito unidades.
; A segunda barra e laranja: PF1 mostra seis dinamites; PF2 mostra cristais
; nos bits 4/5 e um marcador de cenario no bit 7 quando Room=1.
        ldx #8
EnergyLines
        sta WSYNC
        dex
        bne EnergyLines
        lda BombMask
        sta PF1
        lda StatusMask
        sta PF2
        lda #$2C
        sta COLUPF
        ldx #7          ; sete WSYNC; o oitavo vem depois de preparar a caverna
InventoryLines
        sta WSYNC
        dex
        bne InventoryLines
        lda #$F0        ; margens de 16 pixels sempre solidas
        sta PF0
        lda RockColor
        sta COLUPF
        lda Background
        sta COLUBK
        ldx #0
        lda NextHero
        sta WSYNC       ; ultima linha do painel termina com o mapa preparado
        jmp DrawPair

; --- Kernel de duas linhas: cada iteracao desenha um par ---
; A primeira linha escreve P0/M0 ate os ciclos 6/18, PF1/PF2 ate 24/30 e P1
; ate 36. P1 usa X>=56 (pixel inicial no ciclo ~41); nao cortamos seu desenho.
; PF0 nao muda na caverna. ALIGN impede penalidade de pagina nos desvios.
; A segunda linha calcula P1 e atualiza o mapa somente a cada oito pares.
        align 256
HeroBlank
        lda #0
        sta NextHero
        jmp EndLineA

; --- Reposicionamento de P1 numa segunda linha sem pixels desse player ---
; Os eventos chegam com A=X_alvo-30. O despacho e SEC consomem 13 ciclos;
; as escritas diretas de 3 ciclos compensam as indexadas de 5/4 da rotina
; inicial: 13*3 - (2+1)*3 = 30 pixels. HMCLR zerou os ajustes de P0/M0/M1.
; O WSYNC fecha B e HMOVE inicia A seguinte. Cair em DrawPair custa os
; mesmos tres ciclos do JMP normal: nao alonga o kernel nem move o heroi.
PositionActor
        sec
ActorDivide15
        sbc #15
        bcs ActorDivide15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP1
        sta RESP1
        lda FirstActorPixel ; evento72 precisa do bitmap[0]; demais usam zero
        sta NextActor
        lda NextHero    ; antecipa leitura para dar folga a linha A
        sta WSYNC
        sta HMOVE
DrawPair
        sta GRP0        ; A veio de NextHero antes do WSYNC da linha anterior

; --- Laser calculado no proprio par ---
; Comparar X depois de LDA preserva a igualdade. ENAM0 recebe 2 somente em
; ShotY; calcular aqui dispensa preparar e ler outro cache de pixels.
        lda #0
        cpx ShotY
        bne StoreLaser
        lda #2
StoreLaser
        sta ENAM0
        lda NextPF1
        sta PF1
        lda NextPF2
        sta PF2
        lda NextActor
        sta GRP1

; --- Dinamite como carga de oito pixels por duas linhas ---
; M1 aparece perto dos pes de quem plantou, em BombY+6. E um objeto
; independente de P1: tambem permanece visivel em todos os quadros do pavio.
        lda #0
        cpx BombDisplayY
        bne StoreBomb
        lda #2
StoreBomb
        sta ENAM1

; --- Pixels do heroi para o par seguinte ---
; A subtracao sem sinal exclui tanto valores antes de HeroY quanto apos
; HeroY+7. LDA HeroPixels,Y consulta a RAM e nao cruza pagina.
        inx
        txa
        sec
        sbc HeroY
        cmp #8
        bcs HeroBlank
        tay
        lda HeroPixels,y
        sta NextHero
EndLineA
        sta WSYNC

; --- Despacho de eventos, somente nas janelas verticais vazias de P1 ---
; Zero segue o desenho; valores negativos preparam o proximo ator; positivos
; reposicionam. A tabela evita seis comparacoes em todas as linhas do kernel.
        lda KernelEvents,x
        beq RegularActor
        bmi PrepareSlot
        jmp PositionActor
RegularActor
        txa
        sec
        sbc ActorY
        cmp #8
        bcs ActorBlank
        tay
        lda (SpritePtr),y
        jmp SaveActor
ActorBlank
        lda #0
SaveActor
        sta NextActor
        cpx #88
        beq LastPair
        txa
        and #7
        bne SameBand
        txa
        lsr
        lsr
        lsr
        tay
        lda Map1,y
        sta NextPF1
        lda Map2,y
        sta NextPF2
SameBand
        lda NextHero
        sta WSYNC
        jmp DrawPair
LastPair
        sta WSYNC       ; completa exatamente 176 linhas de caverna

; --- Overscan de 30 linhas: logica com a imagem oculta ---
; TIM64T=36 expira na 30a linha; o WSYNC final fecha essa linha. O teste
; da ROM verifica o prazo inclusive em colisao, explosao e troca de sala.
        lda #2
        sta VBLANK
        lda #36
        sta TIM64T
        lda #0
        sta GRP0
        sta GRP1
        sta ENAM0
        sta ENAM1
        sta PF0
        sta PF1
        sta PF2
        jsr UpdateGame
WaitOverscan
        lda INTIM
        bne WaitOverscan
        sta WSYNC
        jmp Frame

; --- Troca de bitmap, altura e cor sem alternar quadros ---
; As preparacoes em X=29/59/71 antecedem os resets em 30/60/72. Cristal
; termina com byte zero em Y=71: sua ultima linha visivel nao e cortada.
; Bandas 8 e 9 tem o mesmo mapa, permitindo omitir sua recarga no evento72.
PrepareSlot
        and #3
        tay
        lda #0
        sta FirstActorPixel
        lda VisibleSlots,y
        beq HideSlot
        lda SlotFirstPixels,y
        sta FirstActorPixel
        lda SlotY,y
        bne SaveSlotY
HideSlot
        lda #Offscreen
SaveSlotY
        sta ActorY
        lda SlotBitmaps,y
        sta SpritePtr
        lda SlotColors,y
        sta COLUP1
        lda #0
        sta NextActor
        sta HMCLR       ; zera P0, M0 e M1: os proximos HMOVE so movem P1
        lda NextHero
        sta WSYNC
        jmp DrawPair

; --- Nova partida e carregamento de uma sala ---
; Energia, seis dinamites e contador de cristais pertencem a partida. Cada
; sala recebe seu mapa, uma bateria, um cristal, uma parede e um morcego.
NewGame
        lda #0
        sta Room
        sta State
        sta Clock
        sta EnergyClock
        sta Gems
        sta FireReady
        sta SoundClock
        sta AUDV0
        lda #MaxEnergy
        sta Energy
        lda #6
        sta Bombs
LoadRoom
        lda #24
        sta HeroX
        lda #8
        sta HeroY
        sta WallHits
        lda #0
        sta Facing
        sta BombTimer
        sta Flash
        lda #Offscreen
        sta ShotY
        lda #32
        sta ShotX
        lda #56
        sta EnemyX
        lda #1
        sta WallAlive
        sta EnemyAlive
        sta EnemyDir
        sta FuelAlive
        sta GemAlive
        sta DownReady

; --- Copia das onze bandas para a RAM ---
; Room=0 usa indices 0..10, Room=1 usa 11..21. PF0 e constante $F0.
; PF2 bits 4..7 cobre X=64..95 por espelhamento: a parede ocupa Y=24..47.
        ldy #0
        lda Room
        beq CopyMapStart
        ldy #11
CopyMapStart
        ldx #0
CopyMap
        lda LevelPF1,y
        sta Map1,x
        lda LevelPF2,y
        sta Map2,x
        iny
        inx
        cpx #11
        bne CopyMap
        ldx #3
InsertWall
        lda Map2,x
        ora #$F0
        sta Map2,x
        inx
        cpx #6
        bne InsertWall
        rts

; --- Reset, estados finais e efeitos com duracao limitada ---
; SWCHB bit 0 e o Game Reset. Apos vencer/perder, um novo clique reinicia;
; segurar o laser durante o ultimo encontro nao apaga o resultado.
UpdateGame
        lda SWCHB
        and #1
        bne CheckState
        jmp NewGame
CheckState
        lda SoundClock
        beq SoundDone
        dec SoundClock
        bne SoundDone
        lda #0
        sta AUDV0
SoundDone
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
PlayingFrame
        inc Clock
        lda Flash
        beq DrainEnergy
        dec Flash
DrainEnergy
        inc EnergyClock
        lda EnergyClock
        and #31
        bne MoveFrame
        dec Energy
        bne MoveFrame
        jmp Lose
MoveFrame
        jsr MoveHero
        jsr MoveEnemy
        jsr UpdateLaser
        jsr UpdateBomb
        lda State
        bne UpdateDone
        jsr CollectItems
        lda State
        bne UpdateDone
        lda EnemyAlive
        beq UpdateDone
        lda EnemyX
        sta PointX
        lda #16
        sta PointY
        jsr TouchHero
        bcc UpdateDone
        jmp Lose

; --- Movimento horizontal, sem atravessar as rochas ---
; Cada direcao tenta mover um pixel. Testamos os dois cantos da borda que
; avanca; a borda traseira ja era valida. Direcoes opostas priorizam esquerda.
MoveHero
        lda HeroX
        sta CandidateX
        lda #$40
        bit SWCHA
        bne TryRight
        lda #8
        sta Facing
        lda HeroX
        cmp #MinX
        beq VerticalMovement
        dec CandidateX
        lda CandidateX
        jmp CheckHorizontal
TryRight
        lda #$80
        bit SWCHA
        bne VerticalMovement
        lda #0
        sta Facing
        lda HeroX
        cmp #MaxX
        beq VerticalMovement
        inc CandidateX
        lda CandidateX
        clc
        adc #7
CheckHorizontal
        sta PointX
        lda HeroY
        sta PointY
        jsr SolidPoint
        bcs VerticalMovement
        lda HeroY
        clc
        adc #7
        sta PointY
        jsr SolidPoint
        bcs VerticalMovement
        lda CandidateX
        sta HeroX

; --- Voo e gravidade ---
; Cima sobe um par por quadro. Sem cima, a gravidade desce um par a cada
; dois quadros. O chao impede a descida. Nao ha inercia neste recorte.
VerticalMovement
        lda HeroY
        sta CandidateY
        lda #$10
        bit SWCHA
        bne Gravity
        lda HeroY
        cmp #8
        beq MovementDone
        dec CandidateY
        lda CandidateY
        jmp CheckVertical
Gravity
        lda Clock
        and #1
        bne MovementDone
        inc CandidateY
        lda CandidateY
        clc
        adc #7
CheckVertical
        sta PointY
        lda HeroX
        sta PointX
        jsr SolidPoint
        bcs MovementDone
        lda HeroX
        clc
        adc #7
        sta PointX
        jsr SolidPoint
        bcs MovementDone
        lda CandidateY
        sta HeroY
        cmp #80
        bcc MovementDone
        lda #1
        sta Room
        jmp LoadRoom    ; a abertura inferior da primeira sala leva a segunda
MovementDone
        rts

; --- Consulta de um ponto do mapa, retornando Carry=1 para rocha ---
; O lado direito espelha X com 159-X. Dividir por quatro encontra uma das
; vinte colunas; cada mascara respeita a ordem particular de PF0/PF1/PF2.
; A consulta usa os mesmos bytes desenhados, inclusive depois da explosao.
SolidPoint
        lda PointY
        cmp #88
        bcs Solid
        lsr
        lsr
        lsr
        sta TileRow
        lda PointX
        cmp #80
        bcc LeftHalf
        eor #$FF
        clc
        adc #160        ; ~X + 160 = 159-X, modulo 256
LeftHalf
        lsr
        lsr
        tax
        cpx #4
        bcc Solid       ; PF0=$F0: as quatro primeiras colunas sao margens
        ldy TileRow
        cpx #12
        bcs TestPF2
        lda Map1,y
        jmp MaskPoint
TestPF2
        lda Map2,y
MaskPoint
        and TileMasks,x
        beq Empty
Solid
        sec
        rts
Empty
        clc
        rts

; --- Morcego: patrulha a faixa superior sem atravessar a parede central ---
; Seu topo e Y=16 e a parede comeca em 24. A cada quatro quadros anda um
; pixel; ao chegar a X=56 ou X=120 inverte a direcao. Morto, fica parado.
; X>=56 permite escrever GRP1 antes de seu primeiro pixel no kernel.
MoveEnemy
        lda EnemyAlive
        beq EnemyDone
        lda Clock
        and #3
        bne EnemyDone
        lda EnemyDir
        bmi EnemyLeft
        inc EnemyX
        lda EnemyX
        cmp #120
        bcc EnemyDone
        lda #$FF
        sta EnemyDir
        rts
EnemyLeft
        dec EnemyX
        lda EnemyX
        cmp #56
        bne EnemyDone
        lda #1
        sta EnemyDir
EnemyDone
        rts

; --- Laser horizontal unico; segurar o botao permite repetir ---
; ShotDir captura o lado no disparo: virar o heroi nao curva um laser ja
; lancado. A origem fica na altura do capacete (HeroY+2).
UpdateLaser
        lda ShotY
        cmp #Offscreen
        bne MoveShot
        lda INPT4
        bpl FireLaser
        rts
FireLaser
        lda HeroX
        sta ShotX
        lda HeroY
        clc
        adc #2
        sta ShotY
        lda Facing
        sta ShotDir
        lda #4
        ldx #10
        ldy #4
        jsr StartSound
MoveShot
        lda ShotDir
        bne ShotLeft
        lda ShotX
        clc
        adc #3
        cmp #144
        bcs RemoveShot
        sta ShotX
        clc
        adc #7
        jmp TestShotMap
ShotLeft
        lda ShotX
        sec
        sbc #3
        cmp #16
        bcc RemoveShot
        sta ShotX
TestShotMap
        sta PointX
        lda ShotY
        sta PointY
        jsr SolidPoint
        bcc TestShotEnemy

; --- O laser desgasta somente a parede removivel ---
; Os oito impactos sao uma alternativa a dinamite. Rocha comum nao muda.
; PointX/PointY guardam o primeiro ponto solido atingido pelo missile.
        lda WallAlive
        beq RemoveShot
        lda PointX
        cmp #64
        bcc RemoveShot
        cmp #96
        bcs RemoveShot
        lda PointY
        cmp #24
        bcc RemoveShot
        cmp #48
        bcs RemoveShot
        dec WallHits
        bne RemoveShot
        jsr DestroyWall
        jmp RemoveShot
TestShotEnemy
        lda EnemyAlive
        beq LaserDone
        lda ShotX
        sec
        sbc EnemyX
        clc
        adc #7
        cmp #15
        bcs LaserDone
        lda ShotY
        sec
        sbc #16
        cmp #8
        bcs LaserDone
        lda #0
        sta EnemyAlive
        lda #8
        ldx #8
        ldy #8
        jsr StartSound
RemoveShot
        lda #Offscreen
        sta ShotY
LaserDone
        rts

; --- Dinamite: pressionar baixo quando apoiado no chao ---
; DownReady registra a borda de entrada. Apenas uma bomba pode estar ativa;
; plantar consome uma unidade e inicia 60 quadros de pavio (~um segundo).
UpdateBomb
        lda #$20
        bit SWCHA
        beq DownPressed
        lda #1
        sta DownReady
        jmp TickBomb
DownPressed
        lda DownReady
        beq TickBomb
        lda #0
        sta DownReady
        lda BombTimer
        bne TickBomb
        lda Bombs
        beq TickBomb
        lda HeroX
        clc
        adc #4
        sta PointX
        lda HeroY
        clc
        adc #8
        sta PointY
        jsr SolidPoint
        bcc TickBomb
        dec Bombs
        lda HeroX
        sta BombX
        lda HeroY
        sta BombY
        lda #60
        sta BombTimer
        rts
TickBomb
        lda BombTimer
        beq BombDone
        dec BombTimer
        bne BombDone

; --- Explosao: remove parede proxima, mas tambem pode atingir o heroi ---
; A parede aceita bombas em X=40..111 e Y=8..63. O retangulo letal ao redor
; da bomba tem deltas X=-15..15 e Y=-11..11; afaste-se durante o pavio.
        lda #10
        sta Flash
        lda #8
        ldx #3
        ldy #15
        jsr StartSound
        lda BombX
        cmp #40
        bcc BlastHero
        cmp #112
        bcs BlastHero
        lda BombY
        cmp #8
        bcc BlastHero
        cmp #64
        bcs BlastHero
        jsr DestroyWall
BlastHero
        lda HeroX
        sec
        sbc BombX
        clc
        adc #15
        cmp #31
        bcs BombDone
        lda HeroY
        sec
        sbc BombY
        clc
        adc #11
        cmp #23
        bcs BombDone
        jmp Lose
BombDone
        rts

; --- Remocao sincronizada: imagem e colisao compartilham o mesmo mapa ---
; AND $0F conserva a rocha fixa das bandas e remove os quatro tiles centrais.
; Chamadas repetidas sao inofensivas; nao existe uma parede invisivel restante.
DestroyWall
        lda #0
        sta WallAlive
        ldx #3
ClearWallBand
        lda Map2,x
        and #$0F
        sta Map2,x
        inx
        cpx #6
        bne ClearWallBand
        rts

; --- Contato de retangulos 8x8, retornando Carry=1 para sobreposicao ---
; Somar sete antes de comparar com quinze aceita deltas -7..7, inclusive
; quando a subtracao fica negativa. Os eixos usam as unidades X/Y do jogo.
TouchHero
        lda HeroX
        sec
        sbc PointX
        clc
        adc #7
        cmp #15
        bcs NoTouch
        lda HeroY
        sec
        sbc PointY
        clc
        adc #7
        cmp #15
        bcs NoTouch
        sec
        rts
NoTouch
        clc
        rts

; --- Coletaveis: bateria e cristal em cada sala ---
; Bateria em (120,40) recupera 24 unidades, limitada a 64. Cristal em
; (56,64) soma um ao inventario. As alturas deixam janelas para reutilizar P1.
; Cada item so pode ser recolhido uma vez.
CollectItems
        lda FuelAlive
        beq CheckGem
        lda #120
        sta PointX
        lda #40
        sta PointY
        jsr TouchHero
        bcc CheckGem
        lda #0
        sta FuelAlive
        lda Energy
        clc
        adc #24
        cmp #MaxEnergy+1
        bcc SaveEnergy
        lda #MaxEnergy
SaveEnergy
        sta Energy
        jsr PickupSound
CheckGem
        lda GemAlive
        beq CheckMiner
        lda #56
        sta PointX
        lda #64
        sta PointY
        jsr TouchHero
        bcc CheckMiner
        lda #0
        sta GemAlive
        inc Gems
        jsr PickupSound

; --- Resgate: apenas a segunda sala tem mineiro, em (128,72) ---
; Os cristais sao opcionais. Encostar no mineiro vence, congela a logica e
; troca o fundo para verde. Nao e necessario voltar a entrada.
CheckMiner
        lda Room
        beq ItemsDone
        lda #128
        sta PointX
        lda #72
        sta PointY
        jsr TouchHero
        bcc ItemsDone
        lda #Won
        sta State
        lda #0
        sta FireReady
        lda #4
        ldx #5
        ldy #30
        jmp StartSound
ItemsDone
        rts
PickupSound
        lda #4
        ldx #4
        ldy #10
        jmp StartSound

; --- Derrota e som: um canal, efeito mais recente tem prioridade ---
; Nao ha vidas extras. A derrota ocorre por energia zero, morcego ou bomba.
; StartSound recebe A=forma de onda, X=frequencia, Y=duracao em quadros.
Lose
        lda #Lost
        sta State
        lda #0
        sta FireReady
        lda #8
        ldx #20
        ldy #25
StartSound
        sta AUDC0
        stx AUDF0
        sty SoundClock
        lda #6
        sta AUDV0
        rts

; --- Preparacao grafica fora da imagem: animacao e cores ---
; A helice alterna a cada quatro quadros. O mapa inicial precisa estar em
; NextPF* antes do primeiro par; no kernel as proximas bandas sao antecipadas.
PrepareGraphics
        ldy #7
CopyHero
        lda HeroBitmap,y
        sta HeroPixels,y
        dey
        bpl CopyHero
        lda Clock
        and #4
        beq RotorReady
        lda #%00111100
        sta HeroPixels
RotorReady
        lda Map1
        sta NextPF1
        lda Map2
        sta NextPF2
        ldx Room
        lda RoomBackground,x
        sta Background
        lda RoomRocks,x
        sta RockColor
        lda Flash
        beq StateColors
        lda #$3E
        sta Background
StateColors
        lda State
        beq ChooseActor
        cmp #Won
        bne LostColor
        lda #$C2
        bne SaveStateColor
LostColor
        lda #$42
SaveStateColor
        sta Background

; --- P1 comeca no morcego em todos os quadros ---
; A partir daqui nao ha Clock & 3 nem rodizio de objetos. O kernel troca
; posicao/bitmap/cor por ALTURA, depois que o ator anterior terminou.
ChooseActor
        lda #Offscreen
        sta ActorY
        lda EnemyX
        sta ActorX
        lda #>BatBitmap
        sta SpritePtr+1
        lda EnemyAlive
        beq BatHidden
        lda #16
        sta ActorY
BatHidden
        lda #$6C
        sta ActorColor
        lda #<BatBitmap
        sta SpritePtr
        lda FuelAlive
        sta VisibleSlots
        lda GemAlive
        sta VisibleSlots+1
        lda Room
        sta VisibleSlots+2
        lda #Offscreen
        sta BombDisplayY
        lda BombTimer
        beq BombHidden
        lda BombY
        clc
        adc #6
        sta BombDisplayY
BombHidden

; --- Conversao dos contadores em barras de bits ---
; Arredondamos energia para cima: 1..8 = um segmento, 57..64 = oito.
; A tabela evita contas no kernel. Barras espelhadas aparecem dos dois lados.
        lda Energy
        clc
        adc #7
        lsr
        lsr
        lsr
        tax
        lda BarMasks,x
        sta FuelMask
        ldx Bombs
        lda BarMasks,x
        sta BombMask
        lda #$C8
        ldx Energy
        cpx #17
        bcs SaveHudColor
        lda #$46
SaveHudColor
        sta HudColor
        ldx Gems
        lda GemMasks,x
        ldx Room
        beq SaveStatus
        ora #$80
SaveStatus
        sta StatusMask
        rts

; --- Posicao horizontal por ciclos ---
; A=coordenada, X=0 P0, 1 P1, 2 M0. Cada volta SBC/BCS leva cinco ciclos,
; ou quinze pixels TIA. EOR/ASL calcula o ajuste fino, aplicado por HMOVE.
; STA.wx forca absoluto,X (cinco ciclos); usar zero-page,X muda a posicao.
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

; --- Bitmaps: cada byte e uma linha de oito pixels ---
; Bit 7 fica a esquerda. O kernel repete cada linha duas vezes. Todos os
; bitmaps de P1 ficam nesta mesma pagina, permitindo trocar somente o byte
; baixo do ponteiro. O capacete do heroi olha para a direita antes de REFP0.
        align 256
HeroBitmap
        byte %11111111 ; helice, animada pela preparacao grafica
        byte %00011000 ; eixo do propulsor
        byte %00111110 ; capacete e visor
        byte %00111100 ; cabeca
        byte %01111110 ; mochila e bracos
        byte %00111100 ; tronco
        byte %00100100 ; pernas
        byte %01100110 ; botas
BatBitmap
        byte %10000001
        byte %11000011
        byte %11100111
        byte %01111110
        byte %00111100
        byte %00011000
        byte %00100100
        byte %00000000
FuelBitmap
        byte %00111100 ; terminal da bateria
        byte %01111110
        byte %01011010 ; sinal de carga
        byte %01011010
        byte %01111110
        byte %01011010
        byte %01111110
        byte %00000000
GemBitmap
        byte %00011000
        byte %00111100
        byte %01111110
        byte %11111111
        byte %01111110
        byte %00111100
        byte %00011000
        byte %00000000
MinerBitmap
        byte %00111100 ; capacete do mineiro
        byte %01111110
        byte %00111100
        byte %01011001 ; braco levantado pede resgate
        byte %00111110
        byte %00111100
        byte %00100100
        byte %01100110

; --- Mapas de onze bandas: teto, corredores, plataformas e piso ---
; PF0=$F0 fixa margens X=0..15 e 144..159. Na banda 4, PF2=$0F deixa
; abertura X=64..95; a parede e inserida em RAM e precisa ser destruida.
; A sala 0 termina com um poco central; na sala 1 a banda 7 tem plataforma
; CENTRAL e o piso e fechado: contorne pelos lados para chegar ao mineiro.
LevelPF1
        byte $FF,$00,$00,$00,$FF,$00,$00,$FF,$00,$00,$FF
        byte $FF,$00,$00,$00,$FF,$00,$00,$00,$00,$00,$FF
LevelPF2
        byte $FF,$00,$00,$00,$0F,$00,$00,$00,$00,$00,$0F
        byte $FF,$00,$00,$00,$0F,$00,$00,$FF,$00,$00,$FF

; --- Mascaras e paleta NTSC ---
; Indices 0..3 sao margens; 4..11 pertencem a PF1; 12..19 a PF2.
; BarMasks acende de zero a oito segmentos; GemMasks acende dois marcadores.
TileMasks
        byte $10,$20,$40,$80,$80,$40,$20,$10,$08,$04,$02,$01
        byte $01,$02,$04,$08,$10,$20,$40,$80
BarMasks
        byte $00,$80,$C0,$E0,$F0,$F8,$FC,$FE,$FF
GemMasks
        byte $00,$10,$30
RoomBackground
        byte $00,$80
RoomRocks
        byte $26,$9A

; --- Agenda vertical: indice e o proximo par X, de zero a 88 ---
; Os eventos de posicao guardam X_alvo-30: bateria120->90, cristal56->26,
; mineiro128->98. Incluimos indice88=zero para a saida final do kernel.
; Se mudar as bandas 8/9, tambem ajuste a recarga omitida no evento72.
KernelEvents
        ds 29,0
        byte $80,90
        ds 28,0
        byte $81,26
        ds 10,0
        byte $82,98
        ds 16,0
SlotY
        byte 40,64,72
SlotBitmaps
        byte <FuelBitmap,<GemBitmap,<MinerBitmap
SlotColors
        byte $CA,$AE,$0E
SlotFirstPixels
        byte 0,0,%00111100 ; primeiro byte do mineiro; os outros comecam depois

; --- Vetores do cartucho de 4 KiB ---
; Os tres apontam para Reset. O 6507 nao expoe IRQ/NMI, mas os seis bytes
; finais permanecem definidos e a verificacao de build confere seus valores.
        org $FFFA
        word Reset,Reset,Reset
