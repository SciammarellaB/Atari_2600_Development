; Atari 2600 - fundo azul e quadrado branco controlado pelo joystick 1.
; Arquivo unico: nao usa headers, macros ou tabelas de imagem.
; NTSC: 262 linhas por quadro, aproximadamente 60 quadros por segundo.

        processor 6502

; ============================================================
; 1. HARDWARE - nomes para enderecos fixos, nao variaveis na RAM
; ============================================================
VSYNC   = $00           ; inicia/termina o sincronismo vertical
VBLANK  = $01           ; bit 1: 1 esconde a imagem, 0 permite desenhar
WSYNC   = $02           ; escrever aqui espera a proxima linha de video
COLUP0  = $06           ; cor do objeto grafico player 0
COLUBK  = $09           ; cor do fundo
RESP0   = $10           ; fixa a posicao horizontal aproximada do player 0
GRP0    = $1B           ; os 8 bits que desenham uma linha do player 0
HMP0    = $20           ; ajuste fino da posicao horizontal do player 0
HMOVE   = $2A           ; aplica o ajuste fino preparado em HMP0
SWCHA   = $0280         ; direcoes dos dois joysticks
SWACNT  = $0281         ; configura os bits de SWCHA como entrada ou saida

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
