; Mansao de nove salas com trilha Tensao. DASM / F4 32K / NTSC.
        processor 6502
        include "hardware.h"
        include "sound_effects.h"
        include "hud.inc"
        include "hud_kernel.h"
        include "world.h"

Room          = $80
RowStart      = $81
RowEnd        = $82
SelectReady   = $83
ResetReady    = $84
GateMask      = $85       ; porta da sala: 2 fechada, 0 aberta
PlayerX       = $86       ; pixels TIA, 0..152; passo de dois pixels
PlayerY       = $87       ; linhas logicas, 0..44; quatro scanlines por linha
StepClock     = $88       ; movimento a cada dois quadros (30 Hz)
Facing        = $89       ; 0 baixo, 1 cima, 2 esquerda, 3 direita
WalkFrame     = $8A       ; 0 parado, 1/2 passos alternados
AnimClock     = $8B       ; quatro movimentos bem-sucedidos por pose
Moving        = $8C
CurrentSprite = $8D
NextGate      = $8E
Aim           = $8F       ; bits SWCHA: ultima direcao valida, incluindo diagonais
ShotX         = $90
ShotY         = $91       ; linha logica; 128 desliga o projetil
ShotDir       = $92       ; direcao capturada no disparo
AttackTimer   = $93       ; 12 quadros: disparo e recuo
NextShot      = $94
CameraY       = $95       ; linhas logicas 0..8: janela vertical de 40 das 48
ShotViewY     = $96       ; altura do tiro relativa a camera; $FF = corte no topo
Health        = $97       ; 0..3 segmentos
Ammo          = $98       ; BCD 00..99; decrementa somente ao disparar
Weapon        = $99       ; bit 0 arma; bit 1 chave azul
SpriteRows    = $9A       ; 40 linhas visiveis + sentinela
SpriteTopRows = SpriteRows
SpriteBottomRows = $C3   ; 41 bytes, ate $EB
MusicStep     = $EC
MusicClock    = $ED
SfxState      = $EE       ; pilha em $F3..$FF, separada dos buffers e estado do mundo

PuzzleFlags   = $EF       ; bit 1 switch vermelho; bit 2 porta azul aberta
PickedLo      = $F0       ; objetos recolhidos nas salas 0..7
PickedHi      = $F1       ; objeto da sala 8
ObjectGraphic = SpriteRows+40 ; sentinelas reutilizadas durante o desenho
NextColor     = SpriteBottomRows+40
ObjectMask    = $F2       ; $FF visivel, 0 recolhido; pilha em $F3..$FF

; Temporarios dos periodos de apagamento reutilizam o inicio do buffer.
; BuildSpriteRows os substitui antes de comecar o desenho seguinte.
InputBits     = $9A
CandX         = $9B
CandY         = $9C
LeftCol       = $9D
RightCol      = $9E
BottomRow     = $9F
ScanRow       = $A0
ScanCol       = $A1
CollisionPtr  = $A2
MoveExit      = $A4

; Depois do cenario, os mesmos buffers guardam os 30 bytes do painel.
HudLeft0      = SpriteRows
HudLeft1      = SpriteRows+5
HudLeft2      = SpriteRows+10
HudRight0     = SpriteRows+15
HudRight1     = SpriteRows+20
HudRight2     = SpriteRows+25
HudHealthPtr  = SpriteBottomRows
HudTensPtr    = SpriteBottomRows+2
HudOnesPtr    = SpriteBottomRows+4
HudWeaponPtr  = SpriteBottomRows+6
HudIndex      = SpriteBottomRows+8

; Intervalos antes da metade direita evitam sobrescrever o PF ainda visivel.
; Os atrasos dependem dos ciclos gastos em objetos no inicio da scanline.
        MAC DRAW_PF
        lda LeftPF0,x
        sta PF0
        lda LeftPF1,x
        sta PF1
        lda LeftPF2,x
        sta PF2
        nop
        nop
        nop
        nop
        lda RightPF0,x
        sta PF0
        lda RightPF1,x
        sta PF1
        lda RightPF2,x
        sta PF2
        ENDM

        MAC DRAW_LAST
        lda LeftPF0,x
        sta PF0
        lda LeftPF1,x
        sta PF1
        lda LeftPF2,x
        sta PF2
        nop
        nop
        lda RightPF0,x
        sta PF0
        lda RightPF1,x
        sta PF1
        lda RightPF2,x
        sta PF2
        ENDM

        MAC MUSIC_ENVELOPES
LeadEnvelope
        byte 5,5,4,4,3,3,2,2,2,1,1,1,1,0,0
BassEnvelope
        byte 4,4,3,3,2,2,2,1,1,1,0,0,0,0,0
NoiseEnvelope
        byte 2,2,1,0,0,0,0,0,0,0,0,0,0,0,0
        ENDM

; Mesmo PF branco nas quatro scanlines; P0/M0 tem cor propria por linha.
        MAC DRAW_FIRST
        lda LeftPF0,x
        sta PF0
        lda LeftPF1,x
        sta PF1
        lda NextColor
        sta COLUP0
        lda LeftPF2,x
        sta PF2
        lda RightPF0,x
        sta PF0
        lda RightPF1,x
        sta PF1
        lda RightPF2,x
        sta PF2
        ENDM

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
        sta COLUBK
        sta CTRLPF
        jsr InitGame
        lda #$0E
        sta COLUPF
        lda #$48
        sta COLUP0       ; cor do missil M0; P0 continua disponivel
        lda #$9C
        sta COLUP1       ; personagem azul/ciano, independente da porta
        lda #$20
        sta NUSIZ0       ; M0 com quatro pixels
        lda #$10
        sta NUSIZ1       ; M1 com dois pixels, P1 sem copias
        lda #1
        sta SelectReady
        sta ResetReady
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
        sta COLUBK
        lda #43
        sta TIM64T
        jsr UpdateGame
        jsr UpdateCamera
        jsr BuildSpriteRows
        ldx Room
        lda GateCoordinates,x
        jsr PositionGate
        lda #41          ; objeto P0 em x=32, com a mesma fase de RESP1
        jsr PositionObject
        lda PlayerX
        cmp #6
        bcc PlayerNearLeft
        clc
        adc #9           ; compensa a fase de RESP1 desta rotina
        bne PlayerCoordinate
PlayerNearLeft
        clc
        adc #3           ; RESP1 ainda dentro de HBLANK: compensar seis pixels
PlayerCoordinate
        jsr PositionPlayer
        lda ShotX
        cmp #6
        bcc ShotNearLeft
        clc
        adc #10
        bne ShotCoordinate
ShotNearLeft
        clc
        adc #4
ShotCoordinate
        jsr PositionShot
        sta WSYNC
        sta HMOVE
WaitBlank
        lda INTIM
        bne WaitBlank
        lda #0
        ldx ShotViewY
        cpx #$FF
        bne FirstShotReady
        lda #2
FirstShotReady
        sta ENAM1        ; tiro parcialmente cortado no topo: tres scanlines
        lda RowStart
        clc
        adc CameraY
        tax
        lda GateRows,x
        sta NextColor
        sta COLUP0
        asl
        and GateMask
        sta ENAM0
        lda ObjectRows,x
        and ObjectMask
        sta GRP0
        lda CurrentSprite
        sta GRP1
        ldy #0
        lda #0
        sta WSYNC
        sta VBLANK
        jmp DrawLine

; 40 linhas visiveis x 4 scanlines. X percorre a janela do mapa em ROM;
; Y percorre SpriteRows em RAM. M1 e atualizado no HBLANK da quarta linha.
        align 256
NextRow
        sta WSYNC
        sta ENAM0        ; A preparado no fim da linha logica anterior
        lda CurrentSprite
        sta GRP1
DrawLine
        DRAW_FIRST
        lda GateRows+1,x
        sta NextColor
        asl              ; bit 0 da tabela vira bit 1 de ENAM0
        and GateMask
        sta NextGate
        sta WSYNC
        DRAW_PF
        lda #0
        cpy ShotViewY
        bne NoShotHere
        lda #2
NoShotHere
        sta NextShot
        sta WSYNC
        lda SpriteBottomRows,y
        sta GRP1         ; terceiro scanline: proximo byte do desenho 8x8
        DRAW_LAST
        lda ObjectRows+1,x
        and ObjectMask
        sta ObjectGraphic
        iny
        lda SpriteRows,y
        sta CurrentSprite
        sta WSYNC
        lda NextShot
        sta ENAM1        ; quarto scanline: projetil com altura de quatro linhas
        DRAW_LAST
        lda ObjectGraphic
        sta GRP0         ; proximo glifo apos os pixels P0 da linha atual
        lda NextGate
        inx
        cpy #40          ; um ciclo livre para entrar no painel sem linha extra
        beq EndScene
        jmp NextRow
EndScene
        jmp DrawHud
EndVisible
        sta WSYNC
        lda #2
        sta VBLANK
        lda #0
        sta PF0
        sta PF1
        sta PF2
        sta ENAM0
        sta GRP1
        sta GRP0
        sta ENAM1
        lda #35
        sta TIM64T
        jsr UpdateShot
        jsr UpdateWorld
        jsr ClearSpriteRows
        jsr UpdateMusic
WaitOverscan
        lda INTIM
        bne WaitOverscan
        sta WSYNC
        nop
        nop
        jmp Frame

InitGame
        lda #1
        sta Room
        lda #0
        sta StepClock
        sta MusicStep
        sta MusicClock
        sta SfxState
        sta AUDV0
        sta AUDV1
        sta CameraY
        lda #3
        sta Health
        lda #0
        sta Ammo
        sta Weapon
        sta PuzzleFlags
        sta PickedLo
        sta PickedHi
        jsr LoadRoom
        jmp SpawnPlayer

LoadRoom
        lda #128
        sta ShotY
        lda #0
        sta AttackTimer
        ldx Room
        lda RoomBanks,x
        tax
        lda $FFF4,x      ; F4: proxima instrucao identica nos oito bancos
        ldx Room
        lda RoomStarts,x
        sta RowStart
        lda RoomEnds,x
        sta RowEnd
        jmp PrepareWorld

SpawnPlayer
        lda #76
        sta PlayerX
        lda #36
        sta PlayerY
        lda #0
        sta Facing
        lda #$20
        sta Aim
        jmp StopWalking

; Reset > Select > movimento. Select permanece como visita de estudo.
; Oito direcoes; opostos no mesmo eixo sao ignorados.
UpdateGame
        lda SWCHB
        and #1
        bne ResetReleased
        lda ResetReady
        bne DoReset
        rts
DoReset
        lda #0
        sta ResetReady
        sta SelectReady
        jmp InitGame
ResetReleased
        lda #1
        sta ResetReady
        lda SWCHB
        and #2
        bne SelectReleased
        lda SelectReady
        bne DoSelect
        rts
DoSelect
        lda #0
        sta SelectReady
        inc Room
        lda Room
        cmp #ROOM_COUNT
        bcc PreviewReady
        lda #0
        sta Room
PreviewReady
        jsr LoadRoom
        jmp SpawnPlayer
SelectReleased
        lda #1
        sta SelectReady
        lda StepClock
        eor #1
        sta StepClock
        lda SWCHA
        eor #$FF
        and #$F0
        sta InputBits
        beq InvalidInput
        and #$C0
        cmp #$C0
        beq InvalidInput
        lda InputBits
        and #$30
        cmp #$30
        beq InvalidInput
        ; Na diagonal, reutilizar o sprite lateral correspondente.
        lda InputBits
        and #$40
        bne FaceLeft
        lda InputBits
        and #$80
        bne FaceRight
        lda InputBits
        and #$10
        bne FaceUp
FaceDown
        lda #0
        beq SetFacing
FaceUp
        lda #1
        bne SetFacing
FaceLeft
        lda #2
        bne SetFacing
FaceRight
        lda #3
        bne SetFacing
InvalidInput
        jmp StopWalking
SetFacing
        ldx InputBits
        stx Aim
        cmp Facing
        beq FacingReady
        sta Facing
        jsr StopWalking
FacingReady
        lda StepClock
        beq MovementDue
        rts
MovementDue
        lda #0
        sta MoveExit
        lda PlayerX
        sta CandX
        lda PlayerY
        sta CandY
        lda InputBits
        and #$40
        bne MoveLeft
        lda InputBits
        and #$80
        bne MoveRight
        jmp VerticalMove
MoveLeft
        lda PlayerX
        cmp #2
        bcc WantLeftExit
        sec
        sbc #2
        sta CandX
        jmp VerticalMove
WantLeftExit
        lda #1
        sta MoveExit
        bne VerticalMove
MoveRight
        lda PlayerX
        clc
        adc #2
        cmp #154
        bcs WantRightExit
        sta CandX
        jmp VerticalMove
WantRightExit
        lda #2
        sta MoveExit
VerticalMove
        lda InputBits
        and #$10
        bne MoveUp
        lda InputBits
        and #$20
        bne MoveDown
        jmp TryMove
MoveUp
        lda PlayerY
        beq WantUpExit
        dec CandY
        jmp TryMove
WantUpExit
        lda #3
        bne WantVerticalExit
MoveDown
        lda PlayerY
        cmp #44
        bcc DownInside
        lda #4
WantVerticalExit
        ldx MoveExit
        beq SetVerticalExit
        jmp StopWalking  ; nao cruzar duas bordas no mesmo passo
SetVerticalExit
        sta MoveExit
        jmp TryMove
DownInside
        inc CandY
TryMove
        jsr CanStand
        bcs GameDone
        lda MoveExit
        beq CommitMove
        cmp #1
        beq ExitToLeft
        cmp #2
        beq ExitToRight
        cmp #3
        beq ExitToUp
        jmp ExitToDown
CommitMove
        lda CandX
        sta PlayerX
        lda CandY
        sta PlayerY
        jmp AnimateStep
GameDone
        jmp StopWalking

; A colisao permite chegar a borda apenas atraves de um vao inteiro livre.
; O candidato inclui os dois eixos: validar o retangulo na nova posicao.
; Ao cruzar, entrar pelo lado oposto com a nova coordenada transversal.
ExitToLeft
        ldx Room
        lda ExitLeft,x
        cmp #$FF
        beq GameDone
        sta Room
        lda #152
        sta CandX
        jsr LoadRoom
        jmp CommitMove
ExitToRight
        ldx Room
        lda ExitRight,x
        cmp #$FF
        beq GameDone
        sta Room
        lda #0
        sta CandX
        jsr LoadRoom
        jmp CommitMove
ExitToUp
        ldx Room
        lda ExitUp,x
        cmp #$FF
        beq GameDone
        sta Room
        lda #44
        sta CandY
        jsr LoadRoom
        jmp CommitMove
ExitToDown
        ldx Room
        lda ExitDown,x
        cmp #$FF
        beq DownBlocked
        sta Room
        lda #0
        sta CandY
        jsr LoadRoom
        jmp CommitMove
DownBlocked
        jmp StopWalking

StopWalking
        lda #0
        sta WalkFrame
        sta AnimClock
        sta Moving
        rts

AnimateStep
        lda #1
        sta Moving
        lda WalkFrame
        bne CountStep
        lda #1
        sta WalkFrame
CountStep
        inc AnimClock
        lda AnimClock
        cmp #4
        bcc AnimationDone
        lda #0
        sta AnimClock
        lda WalkFrame
        eor #3
        sta WalkFrame
AnimationDone
        rts

; C=1 bloqueado; C=0 livre. Verificar todas as celulas do retangulo 8x16,
; inclusive as linhas do meio: testar apenas os cantos deixaria atravessar
; paredes horizontais finas. Objetos de P0 nao participam do PF solido.
CanStand
        lda #0
        sta CollisionPtr
        lda CandX
        cmp #153
        bcs StandBlocked
        lsr
        lsr
        sta LeftCol
        lda CandX
        clc
        adc #7
        lsr
        lsr
        sta RightCol
        lda CandY
        cmp #45
        bcs StandBlocked
        sta ScanRow
        clc
        adc #4
        sta BottomRow
SolidRow
        lda LeftCol
        sta ScanCol
SolidPoint
        jsr IsWall
        bcs StandBlocked
        lda ScanCol
        cmp RightCol
        beq NextSolidRow
        inc ScanCol
        jmp SolidPoint
NextSolidRow
        inc ScanRow
        lda ScanRow
        cmp BottomRow
        bne SolidRow
        clc
        rts
StandBlocked
        sec
        rts

IsWall
        ldx ScanCol
        lda GateMask
        beq ReadMap
        lda ScanRow
        cmp #20
        bcc ReadMap
        cmp #28
        bcs ReadMap
        ldy Room
        txa
        cmp GateColumns,y
        beq PointBlocked

ReadMap
        lda CollisionPages,x
        sta CollisionPtr+1
        lda RowStart
        clc
        adc ScanRow
        tay
        lda (CollisionPtr),y
        and CollisionMasks,x
        beq PointClear
PointBlocked
        sec
        rts
PointClear
        clc
        rts

; Limpeza completa no overscan, depois que UpdateShot termina de usar o
; scratch. Assim a colisao mais cara, com a porta fechada, cabe no VBLANK.
ClearSpriteRows
        lda #0
        ldx #40
ClearAllSpriteRows
        sta SpriteRows,x
        sta SpriteBottomRows,x
        dex
        bpl ClearAllSpriteRows
        rts

; Os buffers ja vieram zerados do overscan (ou de ClearMemory no Reset).
; No VBLANK, apagar apenas os 11 bytes reutilizados por UpdateGame e copiar
; os oito bytes da pose. Cada byte aparece por duas scanlines.
BuildSpriteRows
        lda #0
        ldx #MoveExit-InputBits
ClearSpriteScratch
        sta InputBits,x
        dex
        bpl ClearSpriteScratch
        ldx Facing
        lda AttackTimer
        beq WalkingPose
        txa
        asl
        asl
        asl
        asl
        clc
        adc #96          ; oito poses de ataque depois das 12 de caminhada
        ldy AttackTimer
        cpy #7
        bcs PoseSelected
        clc
        adc #8
        bne PoseSelected
WalkingPose
        lda FacingOffsets,x
        sta CurrentSprite
        lda WalkFrame
        asl
        asl
        asl
        clc
        adc CurrentSprite
PoseSelected
        tay
        lda PlayerY
        sec
        sbc CameraY
        tax
        clc
        adc #4
        sta CurrentSprite
CopyPlayer
        lda PlayerGraphics,y
        sta SpriteRows,x
        iny
        lda PlayerGraphics,y
        sta SpriteBottomRows,x
        iny
        inx
        cpx CurrentSprite
        bne CopyPlayer
        lda SpriteRows
        sta CurrentSprite
        rts

PositionObject
        sec
        sta WSYNC
ObjectDivide15
        sbc #15
        bcs ObjectDivide15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP0
        sta RESP0
        rts

PositionGate
        sec
        sta WSYNC
GateDivide15
        sbc #15
        bcs GateDivide15
        eor #7
        asl
        asl
        asl
        asl
        sta HMM0
        sta RESM0
        rts
PositionPlayer
        sec
        sta WSYNC
PlayerDivide15
        sbc #15
        bcs PlayerDivide15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP1
        sta RESP1
        rts
PositionShot
        sec
        sta WSYNC
ShotDivide15
        sbc #15
        bcs ShotDivide15
        eor #7
        asl
        asl
        asl
        asl
        sta HMM1
        sta RESM1
        rts

; Mesma composicao de Exemplos IA/Musica, atualizada uma vez no overscan.
; Quatro frases de 16 colcheias, 120 BPM e loop de 16 segundos em NTSC.
; Volumes divididos por dois (inteiros). Efeitos assumem apenas o canal 1.
; UpdateSfx recebe o retorno por JMP, sem aumentar o aninhamento da pilha.
UpdateMusic
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
        lsr
        sta AUDV0
        lda SfxState
        bne AdvanceMusic
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
        lsr
        sta AUDV1
AdvanceMusic
        inc MusicClock
        lda MusicClock
        cmp #15
        bcc MusicDone
        lda #0
        sta MusicClock
        inc MusicStep
        lda MusicStep
        and #63
        sta MusicStep
MusicDone
        jmp UpdateSfx

        include "rooms.inc"

; Uma bala por vez. Segurar Fire repete depois que a bala termina e o
; recuo acaba. Executado no overscan, antes de montar os buffers seguintes.
UpdateShot
        lda AttackTimer
        beq AttackCounted
        dec AttackTimer
AttackCounted
        lda ShotY
        cmp #48
        bcs WantFire
        lda ShotDir
        and #$40
        beq ShotRightTest
        lda ShotX
        cmp #2
        bcc RemoveShot
        sec
        sbc #2
        sta ShotX
        jmp ShotVertical
ShotRightTest
        lda ShotDir
        and #$80
        beq ShotVertical
        lda ShotX
        clc
        adc #2
        cmp #159
        bcs RemoveShot
        sta ShotX
ShotVertical
        lda ShotDir
        and #$10
        beq ShotDownTest
        lda ShotY
        beq RemoveShot
        dec ShotY
        jmp ProbeShot
ShotDownTest
        lda ShotDir
        and #$20
        beq ProbeShot
        inc ShotY
ProbeShot
        jsr ShotBlocked
        bcs RemoveShot
        rts
RemoveShot
        lda #128
        sta ShotY
WantFire
        lda AttackTimer
        bne ShotDone
        bit INPT4
        bmi ShotDone
        lda Weapon
        and #1
        beq ShotDone
        lda Ammo
        beq ShotDone
        sed
        sec
        sbc #1
        sta Ammo
        cld
        lda Aim
        sta ShotDir
        lda #12
        sta AttackTimer
        jsr PlayShotSound
        ldx Facing
        lda PlayerX
        clc
        adc MuzzleX,x
        sta ShotX
        lda PlayerY
        clc
        adc MuzzleY,x
        sta ShotY
        jsr ShotBlocked
        bcc ShotDone
        lda #128
        sta ShotY
ShotDone
        rts

; M1 comeca na quarta scanline de ShotY e ocupa quatro scanlines; testar
; as duas linhas logicas tocadas. X e par: os dois pixels cabem numa coluna.
ShotBlocked
        lda ShotX
        cmp #159
        bcs BulletBlocked
        lsr
        lsr
        sta ScanCol
        lda ShotY
        cmp #47
        bcs BulletBlocked
        sta ScanRow
        lda #0
        sta CollisionPtr
        jsr IsWall
        bcs BulletBlocked
        inc ScanRow
        jmp IsWall
BulletBlocked
        sec
        rts

PlayerGraphic
PlayerGraphics
ROMPlayerGraphics
DownIdle
        byte %00111100
        byte %01111110
        byte %01011010
        byte %00111100
        byte %01111110
        byte %10111101
        byte %00100100
        byte %01100110
DownWalkA
        byte %00111100
        byte %01111110
        byte %01011010
        byte %00111100
        byte %11111100
        byte %00111110
        byte %00100100
        byte %01100010
DownWalkB
        byte %00111100
        byte %01111110
        byte %01011010
        byte %00111100
        byte %00111111
        byte %01111100
        byte %00100100
        byte %01000110
UpIdle
        byte %00111100
        byte %01111110
        byte %01111110
        byte %00111100
        byte %01111110
        byte %10111101
        byte %00100100
        byte %01100110
UpWalkA
        byte %00111100
        byte %01111110
        byte %01111110
        byte %00111100
        byte %11111100
        byte %00111110
        byte %00100100
        byte %01100010
UpWalkB
        byte %00111100
        byte %01111110
        byte %01111110
        byte %00111100
        byte %00111111
        byte %01111100
        byte %00100100
        byte %01000110
LeftIdle
        byte %00111000
        byte %01111100
        byte %01011100
        byte %00111000
        byte %01111100
        byte %00111100
        byte %00101000
        byte %01101100
LeftWalkA
        byte %00111000
        byte %01111100
        byte %01011100
        byte %00111000
        byte %11111100
        byte %00111100
        byte %01101000
        byte %01000100
LeftWalkB
        byte %00111000
        byte %01111100
        byte %01011100
        byte %00111000
        byte %01111110
        byte %00111100
        byte %00101100
        byte %01001000
RightIdle
        byte %00011100
        byte %00111110
        byte %00111010
        byte %00011100
        byte %00111110
        byte %00111100
        byte %00010100
        byte %00110110
RightWalkA
        byte %00011100
        byte %00111110
        byte %00111010
        byte %00011100
        byte %00111111
        byte %00111100
        byte %00010110
        byte %00100010
RightWalkB
        byte %00011100
        byte %00111110
        byte %00111010
        byte %00011100
        byte %01111110
        byte %00111100
        byte %00110100
        byte %00010010
DownFire
        byte %00111100
        byte %01111110
        byte %01011010
        byte %00111100
        byte %01111110
        byte %00111100
        byte %00111100
        byte %01100110
DownRecoil
        byte %00111100
        byte %01111110
        byte %01011010
        byte %00111100
        byte %01111110
        byte %01111110
        byte %00100100
        byte %01100110
UpFire
        byte %00011000
        byte %00111100
        byte %01111110
        byte %01111110
        byte %00111100
        byte %01111110
        byte %00100100
        byte %01100110
UpRecoil
        byte %00111100
        byte %01111110
        byte %01111110
        byte %00111100
        byte %01111110
        byte %01111110
        byte %00100100
        byte %01100110
LeftFire
        byte %00111000
        byte %01111100
        byte %01011100
        byte %11111000
        byte %11111110
        byte %00111100
        byte %00101000
        byte %01101100
LeftRecoil
        byte %00011100
        byte %00111110
        byte %00101110
        byte %00011100
        byte %01111100
        byte %00111100
        byte %00010100
        byte %00110110
RightFire
        byte %00011100
        byte %00111110
        byte %00111010
        byte %00011111
        byte %01111111
        byte %00111100
        byte %00010100
        byte %00110110
RightRecoil
        byte %00111000
        byte %01111100
        byte %01110100
        byte %00111000
        byte %00111110
        byte %00111100
        byte %00101000
        byte %01101100

; Tabelas identicas a trilha 2 do laboratorio Musica. $FF = pausa;
; $80 no baixo = percussao. Melodia AUDC4, baixo AUDC6 e ruido AUDC8.
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
MusicDataEnd
        if MusicDataEnd > $FFF4
        err             ; preservar os hotspots F4 e os vetores
        endif
        org $FFFA
        word Reset,Reset,Reset
