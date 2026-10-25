; Macros emitidas nas folgas entre tabelas PF por scripts/rooms.py.
; Cada bloco confere o limite da pagina para preservar mapas e ROM 4K.
SFX_SHOT_FRAMES   = 6
SFX_ACTION_FRAMES = 12
SFX_ACTION_FLAG   = $80

        MAC SFX_ROUTINES
; API futura: JSR PlayActionSound. Dois tons ascendentes, 12 quadros.
; Ainda sem chamada na logica do jogo. Altera A e flags; preserva X/Y.
; A acao interrompe o tiro e tem prioridade ate terminar; nao ha fila.
PlayActionSound
        lda #SFX_ACTION_FLAG+SFX_ACTION_FRAMES
        sta SfxState
        rts

; Chamado somente ao iniciar um disparo; Fire mantido segue o cooldown.
; Uma acao ativa prevalece. Fora dela, um novo tiro reinicia o efeito.
PlayShotSound
        lda SfxState
        bmi SfxDone
        lda #SFX_SHOT_FRAMES
        sta SfxState
        rts

; UpdateMusic transfere para ca depois de avancar o sequenciador.
; Um efeito usa CH1 por poucos quadros; CH0 segue tocando a melodia.
; Ao terminar, CH1 volta a musica no quadro seguinte, sem reiniciar a frase.
UpdateSfx
        lda SfxState
        beq SfxDone
        bmi ActionSound
        tax
        lda ShotPitch-1,x
        sta AUDF1
        lda #8
        sta AUDC1
        lda ShotVolume-1,x
        sta AUDV1
        dec SfxState
        rts
ActionSound
        and #$7F
        tax
        lda ActionPitch-1,x
        sta AUDF1
        lda #4
        sta AUDC1
        lda ActionVolume-1,x
        sta AUDV1
        dec SfxState
        lda SfxState
        cmp #SFX_ACTION_FLAG
        bne SfxDone
        lda #0
        sta SfxState
SfxDone
        rts
SfxCodeEnd
        if SfxCodeEnd > LeftPF0+$100
        err             ; efeitos invadiram a proxima pagina de playfield
        endif
        ENDM

        MAC SFX_DATA
; Indexadas pela quantidade de quadros restantes: ler do fim ao inicio.
ShotPitch
        byte 15,12,9,6,4,2
ShotVolume
        byte 0,1,2,3,4,6
ActionPitch
        byte 5,5,5,5,5,5,8,8,8,8,8,8
ActionVolume
        byte 0,1,2,3,5,5,0,1,2,3,5,5
SfxDataEnd
        if SfxDataEnd > LeftPF1+$100
        err             ; tabelas de efeitos invadiram a proxima pagina
        endif
        ENDM
