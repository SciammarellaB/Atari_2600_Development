; Atari 2600 - fundo azul e quadrado branco controlado pelo joystick 1.
; Arquivo unico: nao usa headers, macros ou tabelas de imagem.
; NTSC: 262 linhas por quadro, aproximadamente 60 quadros por segundo.

        processor 6502  ; o console usa o 6507, com o mesmo conjunto de instrucoes

; ============================================================
; 1. HARDWARE - nomes para enderecos fixos, nao variaveis na RAM
; ============================================================
; --- Quem faz o que ---
; CPU 6507: executa as instrucoes da ROM; usa A, X e Y para trabalhar
; com bytes (8 bits, valores de 0 a 255). No NTSC, opera a cerca de 1,19 MHz.
; TIA: gera video e dois canais de audio; tambem recebe botoes e paddles.
; RIOT 6532: contem 128 bytes de RAM, portas de entrada/saida e timer.
; Cartucho: contem a ROM do jogo; neste exemplo sao 4 KiB (4096 bytes).
;
; --- Endereco nao e a mesma coisa que memoria RAM ---
; A CPU acessa RAM, ROM e perifericos por enderecos: E/S mapeada em memoria.
; O circuito seleciona o componente que responde a cada acesso.
; COLUBK = $09 apenas da um nome a esse endereco para o montador.
; Essa definicao nao executa nada, nao reserva RAM e nao escreve no TIA.
; Ja STA COLUBK executa uma escrita no TIA e muda a cor do fundo.
; O simbolo $ indica hexadecimal; # indica um valor imediato:
;   LDA #$84    -> coloca o numero hexadecimal 84 em A.
;   STA COLUBK  -> envia A ao registrador de cor no endereco $09.
;   LDA XPos    -> le em A o byte da RAM no endereco $80.
;
; --- Memorias usadas aqui (mapa resumido, sem todos os espelhos) ---
; $0080..$00FF: 128 bytes de RAM no RIOT; XPos e YPos usam dois deles.
; $0180..$01FF: espelho da mesma RAM, usado pela pilha da CPU.
;              JSR/RTS usam essa pilha; ela compartilha espaco com variaveis.
; $F000..$FFFF: ROM de 4 KiB, com instrucoes e vetores no fim do arquivo.
;              ORG escolhe o endereco de montagem; nao cria RAM.
; O 6507 expoe 13 bits de endereco: $F000..$FFFF chega ao barramento
; como $1000..$1FFF. Sao dois nomes para o mesmo acesso ao cartucho.
; A ROM permanece sem energia; o conteudo da RAM nao e persistente.
; A, X e Y ficam dentro da CPU e nao fazem parte dos 128 bytes de RAM.
;
; --- TIA: escritas usadas para a saida de video ---
; Nao existe um framebuffer com a imagem inteira: o programa prepara
; os objetos enquanto o TIA gera as linhas. Aqui sao 192 linhas visiveis.
; Player 0 e um objeto grafico do TIA, nao uma referencia ao joystick.
; GRP0 fornece 8 pixels horizontais; repetir o padrao por 16 linhas
; produz a figura. YPos e uma variavel do programa: nao ha escrita
; de coordenada vertical neste hardware.
; Cores e padroes ficam retidos ate nova escrita. Ja os registradores
; de disparo (strobe) agem na escrita e ignoram o valor enviado.
; Ler um endereco do TIA nao devolve necessariamente o que foi escrito:
; leitura e escrita podem selecionar registradores diferentes.
;
; --- Players 0 e 1: recursos fixos do TIA, validos para qualquer jogo ---
; O chip possui dois objetos do tipo Player. Cada um tem os controles
; abaixo: as funcoes e os enderecos sao fixos; os valores sao configuraveis.
;
; Funcao                                Player 0       Player 1
; Desenho de 8 bits                     GRP0   $1B     GRP1   $1C
; Cor e brilho                          COLUP0 $06     COLUP1 $07
; Posicao horizontal por tempo          RESP0  $10     RESP1  $11
; Ajuste fino horizontal                HMP0   $20     HMP1   $21
; Espelhamento horizontal               REFP0  $0B     REFP1  $0C
; Largura e copias                      NUSIZ0 $04     NUSIZ1 $05
; Selecao do desenho atrasado           VDELP0 $25     VDELP1 $26
;
; NUSIZ oferece modos predefinidos: um Player com largura normal (8 pixels),
; dupla (16) ou quadrupla (32); ou duas/tres copias de largura normal,
; com espacamentos determinados pelo hardware. Nao sao novos Players
; independentes: as copias repetem o desenho do mesmo objeto.
; REFP espelha o padrao: permite, por exemplo, virar uma nave para o outro lado.
; VDELP seleciona um padrao grafico atrasado para sincronizar o desenho;
; nao recebe uma coordenada Y. Nao ha registrador de altura ou posicao Y:
; o programa decide em quais linhas fornece pixels para cada Player.
;
; Comandos compartilhados: HMOVE ($2A) aplica os ajustes horizontais de
; todos os objetos; HMCLR ($2B) zera os ajustes, sem zerar suas posicoes.
; Player 0 e Missile 0 compartilham COLUP0; Player 1 e Missile 1, COLUP1.
; Os misseis sao outros dois objetos graficos, separados dos Players.
;
; --- Enderecos nomeados neste arquivo ---
VSYNC   = $00           ; bit 1: 1 inicia, 0 termina o sincronismo vertical
VBLANK  = $01           ; bit 1: 1 esconde a imagem, 0 permite desenhar
WSYNC   = $02           ; disparo: pausa a CPU ate o inicio da proxima linha
COLUBK  = $09           ; cor do fundo
HMOVE   = $2A           ; disparo: aplica os ajustes horizontais dos objetos
;
; --- PLAYER 0: desenho, posicao e ajuste horizontal ---
COLUP0  = $06           ; cor do objeto grafico player 0
RESP0   = $10           ; disparo: instante da escrita posiciona o player 0
GRP0    = $1B           ; os 8 bits que desenham uma linha do player 0
HMP0    = $20           ; bits 7..4: ajuste horizontal de -8 a +7 color clocks
;
; --- Entradas: divididas entre RIOT e TIA ---
; SWCHA tambem e uma entrada: os registradores INPT nao sao as unicas
; entradas do Atari. Cada chip recebe sinais diferentes dos controles.
;
; Entrada                         Registrador       Chip
; Direcoes dos dois joysticks      SWCHA  $0280      RIOT
; Botao de tiro do joystick 1      INPT4  $0C        TIA
; Botao de tiro do joystick 2      INPT5  $0D        TIA
; Posicao dos paddles              INPT0..3 $08..$0B TIA
; Chaves do console                SWCHB  $0282      RIOT
;
; O mesmo joystick envia as direcoes ao RIOT e o botao de tiro ao TIA.
; Neste projeto, ReadJoystick consulta SWCHA para mover o quadrado;
; para reconhecer o tiro do joystick 1, seria preciso consultar INPT4.
; SWACNT configura os pinos de SWCHA; nao informa quais botoes estao apertados.
;
; --- RIOT: entrada de direcoes e configuracao da porta A ---
; Joystick 1: bits 7=direita, 6=esquerda, 5=baixo, 4=cima.
; Joystick 2: bits 3=direita, 2=esquerda, 1=baixo, 0=cima.
; Em SWCHA, 0 significa direcao pressionada; 1 significa solta.
; Em SWACNT, cada bit escolhe 0=entrada ou 1=saida para o pino da porta.
; A inicializacao escreve zero em SWACNT para receber os dois joysticks.
SWCHA   = $0280         ; le os niveis dos pinos configurados como entrada
SWACNT  = $0281         ; configuracao de direcao dos pinos, nao movimento
;
; --- Outros recursos existentes, nao usados na logica deste exemplo ---
; Botao de tiro: TIA INPT4 ($0C), joystick 1; INPT5 ($0D), joystick 2.
;               O bit 7 indica 0=pressionado, 1=solto; nao fica em SWCHA.
; Paddles: TIA INPT0..INPT3 ($08..$0B), leitura por tempo de carga.
; Chaves do console: RIOT SWCHB ($0282), incluindo Select e Game Reset.
;               Game Reset e lido pelo jogo; nao reinicia a CPU sozinho.
; Timer: RIOT INTIM ($0284) para leitura; TIM64T ($0296) inicia uma
;        contagem com intervalo de 64 ciclos da CPU por decremento.
; Som: TIA AUDC0/1 ($15/$16), AUDF0/1 ($17/$18), AUDV0/1 ($19/$1A)
;      controlam tipo de som, divisao de frequencia e volume dos canais.
; No console original, video e audio seguem ao circuito de modulacao RF
; e saem pelo cabo para a entrada de antena da TV.
; Referencias: Stella Programmer's Guide (Steve Wright, Atari, 1979)
; https://www.atariage.com/2600/programming/2600_101/docs/stella.html
; Atari VCS Field Service Manual, secao 1 (diagrama e descricao dos chips).

; ============================================================
; 2. CONSTANTES E VARIAVEIS
; X cresce para a direita; Y cresce para baixo.
; XPos/YPos ficam na RAM. A, X e Y sao registradores da CPU.
; ============================================================
SquareHeight = 16       ; 8 pixels de largura x 16 linhas: quadrado na exibicao NTSC
MinX         = 16       ; margem esquerda para terminar os calculos de cada linha
MaxX         = 144      ; margem direita para posicionar o objeto na mesma linha
MaxY         = 192 - SquareHeight
XPos    = $80           ; posicao horizontal, em pixels
YPos    = $81           ; linha em que comeca o quadrado

; ============================================================
; 3. INICIALIZACAO - executada uma vez ao ligar o programa
; ============================================================
        org $F000
Reset
        sei             ; desabilita interrupcoes
        cld             ; usa aritmetica binaria
        ldx #$FF
        txs             ; inicializa a pilha
        lda #0
ClearMemory
        sta $00,x       ; limpa RAM e registradores do TIA
        dex
        bne ClearMemory
        sta $00
        sta SWACNT      ; todos os bits da porta dos joysticks sao entradas

        lda #$84        ; azul na paleta NTSC
        sta COLUBK
        lda #$0E        ; branco na paleta NTSC
        sta COLUP0
        lda #80
        sta XPos
        lda #88
        sta YPos
        lda #2
        sta VBLANK      ; esconde a imagem durante a preparacao
        sta WSYNC

; ============================================================
; 4. LOOP PRINCIPAL - repetido em todos os quadros
; ============================================================
Frame
; --- 3 linhas de sincronismo vertical ---
        lda #2
        sta VSYNC
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC

; --- 37 linhas antes da imagem visivel ---
; Input e posicionamento usam 4 linhas, controladas por WSYNC.
; Depois esperamos mais 33: 4 + 33 = 37 linhas.
        jsr ReadJoystick
        jsr PositionPlayer
        ldx #0          ; prepara o contador das linhas visiveis
        ldy #33
WaitVerticalBlank
        sta WSYNC
        dey
        bne WaitVerticalBlank

; --- 192 linhas visiveis ---
        sty VBLANK      ; Y terminou em 0: libera a imagem
; X conta as linhas da tela, de 0 ate 191.
DrawLine
; Dentro do quadrado quando: 0 <= linha - YPos < SquareHeight.
; SEC prepara a subtracao. Se linha < YPos, o resultado de 8 bits
; fica alto (por exemplo, 0 - 88 vira 168) e tambem cai fora do quadrado.
        txa
        sec
        sbc YPos
        cmp #SquareHeight
        lda #0          ; fora: todos os pixels desligados
        bcs StorePixels ; LDA nao altera o carry produzido por CMP
        lda #%11111111  ; dentro: oito pixels ligados formam uma linha cheia
StorePixels
        sta GRP0
        sta WSYNC       ; termina esta linha e espera a proxima
        inx
        cpx #192
        bne DrawLine

; --- 30 linhas depois da imagem visivel (overscan) ---
        lda #2
        sta VBLANK      ; esconde a imagem antes do proximo quadro
        lda #0
        sta GRP0        ; apaga os pixels do objeto
        ldx #30
WaitOverscan
        sta WSYNC
        dex
        bne WaitOverscan
        jmp Frame

; ============================================================
; 5. INPUT - consulta o joystick e altera as coordenadas na RAM
;
; SWCHA: bit 7 = direita, 6 = esquerda, 5 = baixo, 4 = cima.
; Os bits 3..0 pertencem ao segundo joystick e sao ignorados.
; ATENCAO: 0 = pressionado; 1 = solto.
;
; LDA #mascara seleciona uma direcao.
; BIT testa A AND SWCHA, sem alterar A ou SWCHA.
; BNE pula o movimento se o resultado nao for zero (direcao solta).
; As comparacoes seguintes impedem que o quadrado saia da tela.
; Cada direcao pode mover 1 pixel por quadro. Diagonais sao permitidas.
; ============================================================
ReadJoystick
        sta WSYNC       ; linha 1 da preparacao: le esquerda e direita
        ldx XPos        ; copia a coordenada para o registrador temporario X
; --- Esquerda: diminui XPos ---
        lda #%01000000
        bit SWCHA
        bne CheckRight
        cpx #MinX
        beq CheckRight
        dex
CheckRight
; --- Direita: aumenta XPos ---
        lda #%10000000
        bit SWCHA
        bne SaveX
        cpx #MaxX
        beq SaveX
        inx
SaveX
        stx XPos        ; grava a nova coordenada horizontal na RAM
        sta WSYNC       ; linha 2 da preparacao: le cima e baixo
        ldx YPos
; --- Cima: diminui YPos ---
        lda #%00010000
        bit SWCHA
        bne CheckDown
        cpx #0
        beq CheckDown
        dex
CheckDown
; --- Baixo: aumenta YPos ---
        lda #%00100000
        bit SWCHA
        bne SaveY
        cpx #MaxY
        beq SaveY
        inx
SaveY
        stx YPos        ; grava a nova coordenada vertical na RAM
        rts

; ============================================================
; 6. POSICAO HORIZONTAL - converte XPos para o formato do TIA
;
; O TIA nao recebe uma coordenada X diretamente em RESP0.
; Escrever em RESP0 fixa a posicao de acordo com o instante da escrita.
; Cada volta abaixo gasta 5 ciclos de CPU = 15 pixels horizontais
; (a ultima volta tem um ciclo a menos porque o salto nao e tomado).
; O tempo escolhe a posicao aproximada; o resto calcula o ajuste fino.
; HMP0 guarda esse ajuste e HMOVE o aplica no inicio da linha seguinte.
; ============================================================
PositionPlayer
        lda XPos
        sta WSYNC       ; linha 3 da preparacao: posicionamento horizontal
        nop             ; estes 4 ciclos alinham XPos com a origem da area visivel
        nop             ; cada NOP espera 2 ciclos (nao altera os registradores)
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
        sta WSYNC       ; linha 4 da preparacao: aplica o ajuste fino
        sta HMOVE       ; aplica o ajuste horizontal no inicio de uma linha
        rts

; ============================================================
; 7. VETORES - informam ao processador onde comecar
; ROM de 4 KiB: $F000 ate $FFFF.
; ============================================================
        org $FFFA
        word Reset      ; NMI
        word Reset      ; RESET
        word Reset      ; IRQ/BRK
