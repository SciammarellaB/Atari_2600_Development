; TIA: nomes dos enderecos de escrita. Definir um nome nao escreve no chip.
; WSYNC espera a proxima linha; VSYNC/VBLANK usam o bit 1 para sincronizar/ocultar.
VSYNC   = $00
VBLANK  = $01
WSYNC   = $02
NUSIZ0  = $04           ; bits 5..4 definem a largura do missile 0
COLUP0  = $06           ; player 0 e missile 0 compartilham a cor
COLUP1  = $07           ; cor dos invasores, desenhados pelo player 1
COLUBK  = $09           ; cor do fundo
RESP0   = $10           ; RESP0 + 1 = RESP1; RESP0 + 2 = RESM0
AUDC0   = $15           ; tipo de onda do canal de audio 0
AUDF0   = $17           ; divisor de frequencia: maior valor, som mais grave
AUDV0   = $19           ; volume do canal 0, de 0 a 15
GRP0    = $1B           ; oito pixels horizontais da nave
GRP1    = $1C           ; oito pixels horizontais do invasor selecionado
ENAM0   = $1D           ; bit 1 habilita o missile usado como tiro
HMP0    = $20           ; HMP0 + 1 = HMP1; HMP0 + 2 = HMM0
HMCLR   = $2B           ; zera os ajustes HMP/HMM sem mover os objetos
HMOVE   = $2A           ; aplica os ajustes finos de todos os objetos

; Leituras: o mesmo endereco pode significar outra coisa quando escrito.
; INPT4 pertence ao TIA; SWCHA, SWCHB e o timer pertencem ao RIOT.
INPT4   = $0C           ; bit 7: 0 = botao de tiro do joystick 1 pressionado
SWCHA   = $0280         ; joystick 1: bit 7 direita, bit 6 esquerda; ativos em 0
SWACNT  = $0281         ; 0 configura os pinos dos joysticks como entradas
SWCHB   = $0282         ; bit 0: 0 = chave Game Reset pressionada
INTIM   = $0284         ; valor atual do timer
TIM64T  = $0296         ; inicia timer com um decremento a cada 64 ciclos
