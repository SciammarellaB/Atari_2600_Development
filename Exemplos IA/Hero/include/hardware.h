; Registradores de escrita do TIA. Cada STA altera o hardware imediatamente:
; nao existe framebuffer. WSYNC suspende a CPU ate a proxima linha de video.
VSYNC   = $00          ; bit 1: pulso de sincronismo vertical
VBLANK  = $01          ; bit 1: oculta a imagem durante a logica
WSYNC   = $02
NUSIZ0  = $04          ; bits 5..4: largura do missile; P0 normal nos bits 2..0
NUSIZ1  = $05          ; largura do missile 1, usado como carga de dinamite
COLUP0  = $06          ; cor do heroi e do laser, que usam P0/M0
COLUP1  = $07          ; cor do ator selecionado para P1 neste quadro
COLUPF  = $08          ; cor das rochas e das barras do painel
COLUBK  = $09          ; cor do fundo da caverna
CTRLPF  = $0A          ; bit 0: espelha a metade direita do playfield
REFP0   = $0B          ; bit 3: espelha horizontalmente o heroi
PF0     = $0D          ; quatro bits, na ordem 4,5,6,7
PF1     = $0E          ; oito bits, na ordem 7,6,5,4,3,2,1,0
PF2     = $0F          ; oito bits, na ordem 0,1,2,3,4,5,6,7
RESP0   = $10          ; +1 = RESP1, +2 = RESM0: reset grosso horizontal
RESP1   = $11
AUDC0   = $15          ; forma de onda do canal de efeitos
AUDF0   = $17          ; divisor da frequencia
AUDV0   = $19          ; volume 0..15
GRP0    = $1B          ; oito pixels horizontais do heroi
GRP1    = $1C          ; oito pixels horizontais do ator
ENAM0   = $1D          ; bit 1: mostra o laser
ENAM1   = $1E          ; bit 1: mostra a carga de dinamite, oito por dois pixels
HMP0    = $20          ; +1 = HMP1, +2 = HMM0: ajuste fino horizontal
HMP1    = $21
HMOVE   = $2A          ; aplica ajustes; escrever no inicio de uma linha
HMCLR   = $2B          ; zera ajustes sem mover: HMOVE posterior so movera P1

; Registradores de leitura: entradas ativas em zero. Os enderecos baixos
; mudam de significado ao ler; INPT4 nao e o registrador de cor $0C.
INPT4   = $0C          ; bit 7: botao do joystick 1
SWCHA   = $0280        ; bits 7,6,5,4: direita, esquerda, baixo, cima
SWACNT  = $0281        ; zero configura o joystick como entrada
SWCHB   = $0282        ; bit 0: chave Game Reset
INTIM   = $0284        ; valor atual do timer do RIOT
TIM64T  = $0296        ; inicia a contagem com intervalo de 64 ciclos
