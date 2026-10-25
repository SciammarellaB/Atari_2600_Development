; Laboratorio de musica: escala, tensao em duas vozes e silencio.
; DASM / 6507 / cartucho 4K / NTSC, 262 linhas por quadro.
        processor 6502
        include "hardware.h"

Track       = $80       ; 0 = silencio; 1 = escala; 2 = tensao (inicial).
SelectReady = $81
ResetReady  = $82
MusicStep   = $83       ; indice na trilha selecionada
MusicClock  = $84       ; quadros decorridos no passo atual
InputBits   = $85
FireReady   = $86
JoyReady    = $87       ; uma mudanca por pressao; soltar para navegar de novo
CursorRows  = $A0       ; 48 bytes ate $CF; longe da pilha no topo da RAM

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
        sta CTRLPF
        lda #$66
        sta COLUPF
        lda #$2E
        sta COLUP0
        lda #2
        sta Track
        lda #1
        sta SelectReady
        sta ResetReady
        sta FireReady
        sta JoyReady
        jsr RestartAudio
        lda #2
        sta VBLANK
        sta WSYNC

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
        ldx Track
        ldy CursorLastRow,x
        ldx #47
CopyCursor
        lda CursorMasks,y
        sta CursorRows,x
        dey
        dex
        bpl CopyCursor
        lda #23         ; indicador a esquerda das tres linhas do menu
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

; Seis escritas PF por scanline; linhas logicas repetidas quatro vezes.
; Manter as tabelas alinhadas em paginas evita ciclos extras por indexacao.
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
        sta WSYNC
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

RestartAudio
        lda #0
        sta MusicStep
        sta MusicClock
        sta AUDV0
        sta AUDV1
        rts

; Cima/esquerda = anterior; baixo/direita/Select = proxima (1,2,0).
; Uma pressao por mudanca. Direcoes opostas sao ignoradas.
; Prioridade: Reset, Select, joystick, Fire. Botoes exigem nova pressao.
UpdateMenu
        lda SWCHB
        and #1
        bne ResetReleased
        lda ResetReady
        bne DoReset
        rts
DoReset
        lda #0
        sta ResetReady
        lda #2
        sta Track
        jmp RestartAudio
ResetReleased
        lda #1
        sta ResetReady
        lda SWCHB
        and #2
        bne SelectReleased
        lda SelectReady
        beq CheckFire
        lda #0
        sta SelectReady
        jmp NextTrack
SelectReleased
        lda #1
        sta SelectReady
        lda SWCHA
        eor #$FF
        and #$F0
        sta InputBits
        beq JoyReleased
        lda JoyReady
        beq CheckFire
        lda #0
        sta JoyReady
        lda InputBits
        and #$50
        beq TryNext
        lda InputBits
        and #$A0
        bne CheckFire
        lda Track
        bne PreviousTrack
        lda #3
PreviousTrack
        sec
        sbc #1
        sta Track
        jmp RestartAudio
TryNext
        lda InputBits
        and #$A0
        beq CheckFire
NextTrack
        lda Track
        clc
        adc #1
        cmp #3
        bcc ApplyTrack
        lda #0
ApplyTrack
        sta Track
        jmp RestartAudio
JoyReleased
        lda #1
        sta JoyReady
CheckFire
        lda INPT4
        bmi FireReleased
        lda FireReady
        beq MenuDone
        lda #0
        sta FireReady
        jmp RestartAudio
FireReleased
        lda #1
        sta FireReady
MenuDone
        rts

; AUDC=12: onda quadrada com divisao adicional por 6.
; f ~= 31400 / (6 * (AUDF+1)), NTSC. Alturas aproximadas, sem samples.
; Do4 Re4 Mi4 Fa4 | Mi4 Re4 Do4 Sib3 | pausa. Cada nota tem release.
UpdateMusic
        lda Track
        cmp #2
        bne CheckScale
        jmp PlayTension
CheckScale
        lda #0
        sta AUDV1      ; canal 1 reservado para efeitos futuros
        lda Track
        bne PlaySuspense
        lda #0
        sta AUDV0
        rts
PlaySuspense
        lda #12
        sta AUDC0
        ldx MusicStep
        lda Melody,x
        sta AUDF0
        lda MusicClock
        cmp Sustain,x
        bcs ReleaseNote
        lda #5
        bne WriteVolume
ReleaseNote
        cmp ReleaseEnd,x
        bcs SilentTail
        lda #2
        bne WriteVolume
SilentTail
        lda #0
WriteVolume
        sta AUDV0
        inc MusicClock
        lda MusicClock
        cmp Duration,x
        bcc MusicDone
        lda #0
        sta MusicClock
        inc MusicStep
        lda MusicStep
        cmp #9
        bcc MusicDone
        lda #0
        sta MusicStep
MusicDone
        rts

; Composicao original: quatro frases de 16 colcheias, 120 BPM, 16 segundos.
; Canal 0: motivo cromatico em onda quadrada; $FF representa uma pausa.
; Canal 1 alterna baixo (AUDC=6) e ruido percussivo ($80, AUDC=8).
; Envelopes curtos deixam espaco entre ataques e acentuam os deslocamentos.
PlayTension
        ldx MusicStep
        ldy MusicClock
        lda TensionMelody,x
        cmp #$FF
        beq LeadSilent
        sta AUDF0
        lda #4
        sta AUDC0
        lda LeadEnvelope,y
        jmp LeadVolume
LeadSilent
        lda #0
LeadVolume
        sta AUDV0
        lda TensionBass,x
        cmp #$FF
        beq BassSilent
        bmi Percussion
        sta AUDF1
        lda #6
        sta AUDC1
        lda BassEnvelope,y
        jmp BassVolume
Percussion
        lda #10
        sta AUDF1
        lda #8
        sta AUDC1
        lda NoiseEnvelope,y
        jmp BassVolume
BassSilent
        lda #0
BassVolume
        sta AUDV1
        inc MusicClock
        lda MusicClock
        cmp #15
        bcc TensionDone
        lda #0
        sta MusicClock
        inc MusicStep
        lda MusicStep
        and #63
        sta MusicStep
TensionDone
        rts

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

CursorLastRow
        byte 143,47,95 ; ultimo indice do cursor: mudo, escala, tensao
Melody
        byte 19,17,15,14,15,17,19,21,21
Duration
        byte 30,30,30,30,30,30,30,60,45
Sustain
        byte 22,22,22,22,22,22,22,46,0
ReleaseEnd
        byte 27,27,27,27,27,27,27,56,0

; Frases A, A', B, A'': repeticao reconhecivel, contraste e volta ao inicio.
; Alturas aproximadas: Do5 Mib5 Sol5 Solb5 Re5 Si4 Reb5; Fa5/Lab5 no B.
TensionMelody
        byte 29,$FF,24,29,19,$FF,20,24,26,$FF,31,27,29,$FF,31,$FF
        byte 29,$FF,24,29,18,19,20,$FF,26,24,31,27,29,$FF,27,$FF
        byte 22,$FF,18,22,24,23,24,$FF,20,$FF,19,20,27,$FF,31,$FF
        byte 29,24,19,20,26,24,31,27,29,31,27,31,29,$FF,$FF,$FF
TensionBass
        byte 7,$FF,7,$80,7,$FF,7,$80,9,$FF,9,$80,9,$FF,9,$80
        byte 7,$FF,7,$80,7,$FF,7,$80,9,$FF,9,$80,9,$FF,9,$80
        byte 11,$FF,11,$80,11,$FF,11,$80,9,$FF,9,$80,9,$FF,9,$80
        byte 7,$FF,7,$80,9,$FF,9,$80,7,$FF,9,$80,7,$FF,$FF,$FF
LeadEnvelope
        byte 5,5,4,4,3,3,2,2,2,1,1,1,1,0,0
BassEnvelope
        byte 4,4,3,3,2,2,2,1,1,1,0,0,0,0,0
NoiseEnvelope
        byte 2,2,1,0,0,0,0,0,0,0,0,0,0,0,0

        include "menu.inc"
        org $FFFA
        word Reset,Reset,Reset
