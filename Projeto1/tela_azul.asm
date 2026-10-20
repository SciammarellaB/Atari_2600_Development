; Atari 2600 - tela azul, NTSC (262 linhas por quadro).
; Abra este arquivo no Atari Dev Studio e use o comando
; "ads: Compile source code and run in emulator".
; Nao requer arquivos include.

        processor 6502

VSYNC   = $00
VBLANK  = $01
WSYNC   = $02
COLUBK  = $09

        org $F000

Reset
        sei
        cld
        ldx #$FF
        txs
        lda #0

; Limpa RAM e registradores do TIA.
Clear
        sta $00,x
        dex
        bne Clear
        sta $00

        lda #$80
        sta COLUBK
        lda #2
        sta VBLANK
        sta WSYNC

Frame
; 3 linhas de sincronismo vertical.
        lda #2
        sta VSYNC
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC

; 37 linhas de blanking vertical.
        ldx #37
VerticalBlank
        sta WSYNC
        dex
        bne VerticalBlank

; 192 linhas visiveis com fundo azul (paleta NTSC).
        lda #0
        sta VBLANK
        lda #$84
        sta COLUBK
        ldx #192
Visible
        sta WSYNC
        dex
        bne Visible

; 30 linhas de overscan.
        lda #2
        sta VBLANK
        ldx #30
Overscan
        sta WSYNC
        dex
        bne Overscan
        jmp Frame

; ROM de 4 KiB e vetores de inicializacao.
        org $FFFA
        word Reset
        word Reset
        word Reset
