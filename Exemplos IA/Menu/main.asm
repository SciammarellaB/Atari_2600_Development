; COSMOS: somente um menu, sem iniciar uma partida.
; DASM / 6507 / cartucho 4K / NTSC, 262 linhas por quadro.
        processor 6502
        include "hardware.h"

Players     = $80       ; 1 ou 2; ponto de integracao com um jogo futuro
SelectReady = $81       ; exige soltar Select antes de alternar novamente
ResetReady  = $82       ; exige soltar Reset antes de reiniciar novamente
MusicStep   = $83       ; indice da melodia: 0..31
MusicClock  = $84       ; posicao dentro da nota: 0..14 quadros
InputBits   = $85

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
        sta CTRLPF      ; metade direita independente, sem espelhamento
        lda #$9C
        sta COLUPF
        lda #$2E
        sta COLUP0      ; indicador dourado
        jsr InitMenu
        lda #1
        sta SelectReady
        sta ResetReady
        lda #2
        sta VBLANK
        sta WSYNC

; 3 VSYNC + 37 VBLANK + 192 visiveis + 30 overscan.
; O timer absorve os caminhos diferentes de entrada e posicionamento.
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
        jsr UpdateMenu
        jsr UpdateMusic
        ldx Players
        lda CursorX-1,x
        jsr PositionCursor
        sta WSYNC
        sta HMOVE
WaitBlank
        lda INTIM
        bne WaitBlank
        ldx #0
        ldy #4
        sta WSYNC
        sta VBLANK
        jmp DrawLine

; 48 linhas logicas de 4 scanlines. Cada tabela fica numa pagina propria:
; nenhuma leitura indexada ganha um ciclo por atravessar pagina.
; PF esquerdo escrito ate 14/21/28 ciclos; direito ate 45/52/59.
; As escritas da direita ocorrem depois do consumo dos bits da esquerda.
        align 256
NextRow
        ldy #4
NextLine
        sta WSYNC
DrawLine
        lda CursorRows,x
        sta GRP0
        lda LeftPF0,x
        sta PF0
        lda LeftPF1,x
        sta PF1
        lda LeftPF2,x
        sta PF2
        lda RightPF0,x
        nop
        nop
        nop
        nop
        nop
        sta PF0
        lda RightPF1,x
        sta PF1
        lda RightPF2,x
        sta PF2
        dey
        bne NextLine
        inx
        cpx #48
        bne NextRow
        sta WSYNC       ; fecha a ultima das 192 linhas visiveis
        lda #2
        sta VBLANK
        lda #0
        sta PF0
        sta PF1
        sta PF2
        sta GRP0
        ldx #30
Overscan
        sta WSYNC
        dex
        bne Overscan
        jmp Frame

InitMenu
        lda #1
        sta Players
        lda #0
        sta MusicStep
        sta MusicClock
        sta AUDV0
        rts

; Direcoes sao idempotentes: segurar uma seta mantem a opcao escolhida.
; Diagonais contraditorias e direcoes opostas sao tratadas como neutras.
; Reset tem prioridade sobre Select e joystick.
UpdateMenu
        lda SWCHB
        and #1
        bne ResetReleased
        lda ResetReady
        beq MenuDone
        lda #0
        sta ResetReady
        jsr InitMenu
        rts
ResetReleased
        lda #1
        sta ResetReady
        lda SWCHA
        eor #$FF
        and #$F0
        sta InputBits
        and #$50        ; esquerda / cima
        beq TryTwo
        lda InputBits
        and #$A0        ; direita / baixo
        bne CheckSelect
        lda #1
        sta Players
        jmp CheckSelect
TryTwo
        lda InputBits
        and #$A0
        beq CheckSelect
        lda #2
        sta Players
CheckSelect
        lda SWCHB
        and #2
        bne SelectReleased
        lda SelectReady
        beq MenuDone
        lda #0
        sta SelectReady
        lda Players
        eor #3          ; 1 XOR 3 = 2; 2 XOR 3 = 1
        sta Players
MenuDone
        rts
SelectReleased
        lda #1
        sta SelectReady
        rts

; Melodia original de oito segundos: 32 notas, 15 quadros por nota.
; AUDC=4 produz tom puro. Os divisores sao aproximacoes da escala do TIA.
; O volume baixo decai e silencia os tres ultimos quadros de cada nota.
UpdateMusic
        lda #4
        sta AUDC0
        ldx MusicStep
        lda Melody,x
        sta AUDF0
        ldx MusicClock
        lda Envelope,x
        sta AUDV0
        inc MusicClock
        lda MusicClock
        cmp #15
        bcc MusicDone
        lda #0
        sta MusicClock
        inc MusicStep
        lda MusicStep
        and #31
        sta MusicStep
MusicDone
        rts

; Posiciona o player 0 durante VBLANK. RESP0 faz o ajuste grosseiro;
; HMP0/HMOVE compensam o resto da divisao por 15.
PositionCursor
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
        sta HMP0
        sta RESP0
        rts

CursorX
        byte 51,115      ; compensa a fase de RESP0 desta rotina sem indice
Melody
        byte 29,23,19,14,19,23,29,23
        byte 26,21,17,13,17,21,26,21
        byte 23,19,14,11,14,19,23,19
        byte 26,21,17,14,19,23,29,29
Envelope
        byte 4,4,4,3,3,3,3,2,2,2,2,1,0,0,0

; Gerado por scripts/graphics.py durante a montagem; editar a fonte Python.
        include "menu.inc"

        org $FFFA
        word Reset,Reset,Reset
