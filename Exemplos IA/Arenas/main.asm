; ARENAS: quatro chefes e portas entre arenas. Atari 2600, NTSC, F8 8K.
; Cena 160 x 80 (duas scanlines por linha) e HUD de 32 scanlines.
    processor 6502
VSYNC = $00
VBLANK = $01
WSYNC = $02
NUSIZ0 = $04
NUSIZ1 = $05
COLUP0 = $06
COLUP1 = $07
COLUPF = $08
COLUBK = $09
CTRLPF = $0A
PF0 = $0D
PF1 = $0E
PF2 = $0F
RESP0 = $10
RESP1 = $11
RESM0 = $12
RESM1 = $13
AUDC0 = $15
AUDF0 = $17
AUDV0 = $19
GRP0 = $1B
GRP1 = $1C
ENAM0 = $1D
ENAM1 = $1E
HMP0 = $20
HMP1 = $21
HMM0 = $22
HMM1 = $23
HMOVE = $2A
HMCLR = $2B
INPT4 = $0C
SWCHA = $0280
SWACNT = $0281
SWCHB = $0282

XPos = $80
XFrac = $81
YPos = $82
YFrac = $83
Heading = $84
InputHeading = $85
Travel = $86
DeltaX = $87
DeltaY = $88
SignX = $89
SignY = $8A
BossX = $8B
BossY = $8C
BossHeading = $8D
BossPhase = $8E            ; 0 espera, 1 aviso, 2 investida, 3 recuperacao
PhaseTimer = $8F
BossHP = $90
Lives = $91
GameState = $92            ; 0 combate, 1 vitoria final, 2 derrota, 3 porta aberta
InvulnTimer = $93
BossFlash = $94
ShotActive = $95           ; bit 1 habilita o missile 0
ShotX = $96
ShotXFrac = $97
ShotY = $98
ShotYFrac = $99
ShotHeading = $9A
NewShot = $9B
FireDown = $9C
FirePressed = $9D
RestartRequest = $9E
FrameCounter = $9F
PlayerPtr = $A0            ; ponteiros de dois bytes
BossPtr = $A2
PlayerPixels = $A4
BossPixels = $A5
ShotPixels = $A6
PlayerMask = $A7
BossMask = $A8
AimRequest = $A9
AimBits = $AA
Target = $AB
Moving = $AC
WallHit = $AD
HitBoss = $AE
Touch = $AF
SoundKind = $B0            ; 1 dano, 2 acerto, 3 vitoria, 4 aviso/investida
SoundTimer = $B1
PlayerBar = $B2
BossBar = $B3
BossColor = $B4
SceneColor = $B5
WallColor = $B6
MessageLeftPtr = $B7
MessageRight0Ptr = $B9
MessageRight1Ptr = $BB
RoomIndex = $BD            ; 0 Touro, 1 Sentinela, 2 Guardiao, 3 Senhor
ExitDirection = $BE        ; 0 nenhuma, 1 norte, 2 leste
DoorOpen = $BF
EnemyActive = $C0
EnemyX = $C1
EnemyY = $C2
EnemyHeading = $C3
EnemyPixels = $C4
EnemySpawn = $C5
HazardAxis = $C6           ; 0 horizontal, 1 vertical, 2 diagonal direita, 3 esquerda
HazardActive = $C7
HazardVisible = $C8
PhaseChanged = $C9
WallPF1Ptr = $CA
WallPF2Ptr = $CC
RightWallPtr = $CE
EnemyTouch = $D0
HazardTouch = $D1
PlayerHit = $D2
TransitionRequested = $D3
EnemyPtr = $D4
RightSecondPtr = $D6
PatrolNode = $D8
PatrolMoving = $D9
BeamMotion = $DA
BeamMode = $DB
BeamStartX = $DC
; $DD..$DF livres. Pilha em $E0..$FF (32 bytes).
CheckHits = $FFA0
UpdateBoss = $FFC0         ; trampoline F8, identico nos dois bancos

; A entrada do quadro e o loop compartilham a mesma sequencia de escritas.
; O JMP do loop fica antes do WSYNC, preservando o prazo do PF1 esquerdo.
    MAC DRAW_SCENE_OBJECTS
    sta GRP0
    stx GRP1
    lda ShotPixels
    sta ENAM0
    lda WallPF0,y
    sta PF0
    lda (WallPF1Ptr),y
    sta PF1
    lda (WallPF2Ptr),y
    sta PF2
    lda (RightWallPtr),y
    sta PF0
    ENDM

; Banco 0: mecanicas dos chefes. O banco 1 mantem kernel e estado do jogo.
    org $0000
    rorg $F000
    include "bosses.asm"
    include "combat.asm"
    org $0FA0
    rorg $FFA0
    bit $1FF8
    jsr UpdateCombatBank
    bit $1FF9
    rts
    org $0FC0
    rorg $FFC0
    bit $1FF8
    jsr UpdateBossBank
    bit $1FF9
    rts
    org $0FD0
    rorg $FFD0
    bit $1FF9
    jmp Reset
    org $0FFA
    rorg $FFFA
    word $FFD0,$FFD0,$FFD0

    org $1000
    rorg $F000
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
    lda #2
    sta VBLANK
    jsr StartNewGame
    sta WSYNC

Frame
    lda #2
    sta VSYNC
    sta WSYNC
    sta WSYNC
    sta WSYNC
    lda #0
    sta VSYNC
; 6 tiro + 11 impactos + 9 desenho + 3/2/3/2 posicao + 1 setup = 37.
    jsr UpdateShot
    jsr CheckHits
    jsr PrepareRender
    jsr PositionShot
    jsr PositionBoss
    jsr PositionEnemy
    jsr PositionPlayer
    lda SceneColor
    sta COLUBK
    lda WallColor
    sta COLUPF
    lda #1
    sta CTRLPF
    ldy #0
    ldx #0
    sta HMCLR              ; mais de 24 ciclos depois do HMOVE de posicionamento
    lda BeamMotion
    sta HMM1               ; so o feixe se move; jogador, chefe e tiro ficam fixos
    lda #$FF                ; primeira linha comeca no topo fechado em PF1
    sta PF1
    lda BeamMode
    beq NormalSceneEntry
    jmp BeginBeamScene
NormalSceneEntry
    lda #0
    sta WSYNC               ; setup termina na ultima linha de VBLANK
    sta VBLANK

; A/X trazem os pixels da faixa atual. A segunda scanline prepara o chefe
; e o tiro seguintes; a primeira prepara o jogador seguinte. As alturas
; sao verificadas antes das leituras: sprites vizinhos na ROM nao vazam.
SceneFirst
    DRAW_SCENE_OBJECTS
    jmp NextPlayerLine
SceneFirstSync
    sta WSYNC
SceneRepeat
    DRAW_SCENE_OBJECTS
NextPlayerLine
    iny
    tya
    sec
    sbc YPos
    cmp #8
    bcs PlayerOutside
    lda (PlayerPtr),y
    jmp NextPlayerReady
PlayerOutside
    lda #0
NextPlayerReady
    sta PlayerPixels
    lda EnemyPixels
    sta WSYNC
SceneSecond
    sta ENAM1
    lda WallPF0-1,y
    sta PF0
    tya
    sec
    sbc BossY
    cmp #12
    bcs BossOutside
    lda (BossPtr),y
    jmp NextBossReady
BossOutside
    lda #0
NextBossReady
    tax
    lda (RightSecondPtr),y
    sta PF0
    lda #0
    cpy ShotY
    bne NextShotReady
    lda ShotActive
NextShotReady
    sta ShotPixels
    lda (EnemyPtr),y
    sta EnemyPixels
    cpy #80
    beq SceneDone
    lda PlayerPixels
    jmp SceneFirstSync
SceneDone
    sta WSYNC               ; HUD linha 0
    lda #0
    sta GRP0
    sta GRP1
    sta ENAM0
    sta ENAM1
    sta PF0
    sta PF1
    sta PF2
    sta CTRLPF              ; duas metades independentes no HUD
    lda #$02
    sta COLUBK
    ldx #4
HudTopMargin
    sta WSYNC               ; linhas 1..4
    dex
    bne HudTopMargin
    ldx #6
HudBarLine
    sta WSYNC               ; linhas 5..10: jogador a esquerda, chefe a direita
    lda PlayerBar
    sta PF1
    lda #$AE
    sta COLUPF
    REPEAT 14
    nop
    REPEND
    lda BossColor
    sta COLUPF
    lda BossBar
    sta PF1
    dex
    bne HudBarLine
    sta WSYNC               ; linha 11
    lda #0
    sta PF1
    lda #$0E
    sta COLUPF
    ldx #6
HudMessageMargin
    sta WSYNC               ; linhas 12..17
    dex
    bne HudMessageMargin
    ldx #5
    ldy #0
DrawMessageRow
    sta WSYNC               ; linhas 18..27: BOSS / WIN! / LOSE
    lda #0
    sta PF0
    sta PF1
    lda (MessageLeftPtr),y
    sta PF2
    REPEAT 5
    nop
    REPEND
    lda (MessageRight0Ptr),y
    sta PF0
    lda (MessageRight1Ptr),y
    sta PF1
    lda #0
    nop
    nop                     ; preserva PF2 esquerdo ate seu ultimo pixel
    sta PF2
    sta WSYNC
    lda #0
    sta PF0
    sta PF1
    lda (MessageLeftPtr),y
    sta PF2
    REPEAT 5
    nop
    REPEND
    lda (MessageRight0Ptr),y
    sta PF0
    lda (MessageRight1Ptr),y
    sta PF1
    lda #0
    nop
    nop
    sta PF2
    iny
    dex
    bne DrawMessageRow
    sta WSYNC               ; linha 28
    lda #0
    sta PF0
    sta PF1
    sta PF2
    ldx #3
HudBottomMargin
    sta WSYNC               ; linhas 29..31
    dex
    bne HudBottomMargin
    sta WSYNC               ; overscan linha 0
    lda #2
    sta VBLANK
; 5 entrada/reinicio + 7 movimento + 4 porta + 12 chefes + 2 som = 30.
    jsr UpdateInput
    jsr ReadJoystick
    jsr UpdateRoom
    jsr UpdateBoss
    jsr UpdateAudio
    jmp Frame

; Cinco linhas em qualquer caminho. RESET funciona durante toda a partida.
; Na tela final, o tiro precisa ser solto e pressionado novamente.
UpdateInput
    sta WSYNC
    inc FrameCounter
    lda #0
    sta FirePressed
    sta RestartRequest
    bit INPT4
    bmi FireReleased
    lda FireDown
    bne FireSampled
    inc FirePressed
    inc FireDown
    bne FireSampled
FireReleased
    sta FireDown
FireSampled
    lda SWCHB
    and #1
    beq RequestRestart
    lda GameState
    beq InputDone
    cmp #3
    beq InputDone
    lda FirePressed
    beq InputDone
RequestRestart
    inc RestartRequest
InputDone
    sta WSYNC
    lda RestartRequest
    bne StartNewGame
    sta WSYNC
    sta WSYNC
    sta WSYNC
    rts
StartNewGame
    sta WSYNC
    lda #76
    sta XPos
    lda #58
    sta YPos
    lda #72
    sta BossX
    lda #18
    sta BossY
    lda #3
    sta Lives
    lda #6
    sta BossHP
    lda #0
    sta RoomIndex
    sta ExitDirection
    sta DoorOpen
    sta WSYNC
    lda #0
    sta XFrac
    sta YFrac
    sta Heading
    sta BossHeading
    sta BossPhase
    sta GameState
    sta InvulnTimer
    sta BossFlash
    sta ShotActive
    sta ShotXFrac
    sta ShotYFrac
    sta SoundKind
    sta SoundTimer
    sta EnemyActive
    sta HazardActive
    sta HazardVisible
    sta WSYNC
    sta EnemySpawn
    sta HazardAxis
    sta PatrolNode
    sta PatrolMoving
    sta AimRequest
    sta WallHit
    sta Travel
    lda #90
    sta PhaseTimer
    rts

; Movimento 8.8, modulo 0,75 pixel logico/quadro. Diagonais normalizadas.
ReadJoystick
    sta WSYNC
    lda GameState
    beq ReadMovement
    cmp #3
    beq ReadMovement
    REPEAT 6
    sta WSYNC
    REPEND
    rts
ReadMovement
    lda SWCHA
    eor #$FF
    lsr
    lsr
    lsr
    lsr
    tax
    lda InputHeadings,x
    sta InputHeading
    sta WSYNC
    lda #0
    sta Travel
    lda InputHeading
    bmi MovementReady
    sta Heading
    inc Travel
MovementReady
    sta WSYNC
    ldx Heading
    lda VelocityX,x
    sta DeltaX
    lda VelocityY,x
    sta DeltaY
    lda VelocitySignX,x
    sta SignX
    lda VelocitySignY,x
    sta SignY
    sta WSYNC
    lda Travel
    beq XAdded
    clc
    lda XFrac
    adc DeltaX
    sta XFrac
    lda XPos
    adc SignX
    sta XPos
XAdded
    sta WSYNC
    lda XPos
    cmp #8
    bcc ClampLeft
    cmp #144
    bcc XClamped
    lda #144
    bne ClampX
ClampLeft
    lda #8
ClampX
    sta XPos
    lda #0
    sta XFrac
XClamped
    sta WSYNC
    lda Travel
    beq YAdded
    clc
    lda YFrac
    adc DeltaY
    sta YFrac
    lda YPos
    adc SignY
    sta YPos
YAdded
    sta WSYNC
    lda YPos
    cmp #6
    bcc ClampTop
    cmp #66
    bcc YClamped
    lda #66
    bne ClampY
ClampTop
    lda #6
ClampY
    sta YPos
    lda #0
    sta YFrac
YClamped
    rts


; O jogador so atravessa a abertura depois de derrotar o chefe da sala.
UpdateRoom
    sta WSYNC               ; 1: norte, corpo inteiro entre X=64..95
    lda #0
    sta TransitionRequested
    lda GameState
    cmp #3
    bne NorthDoorDone
    lda DoorOpen
    beq NorthDoorDone
    lda ExitDirection
    cmp #1
    bne NorthDoorDone
    lda Travel
    beq NorthDoorDone
    lda SignY
    bpl NorthDoorDone
    lda YPos
    cmp #6
    bne NorthDoorDone
    lda XPos
    cmp #64
    bcc NorthDoorDone
    cmp #89
    bcs NorthDoorDone
    inc TransitionRequested
NorthDoorDone
    sta WSYNC               ; 2: leste, corpo inteiro entre Y=28..51
    lda GameState
    cmp #3
    bne EastDoorDone
    lda DoorOpen
    beq EastDoorDone
    lda ExitDirection
    cmp #2
    bne EastDoorDone
    lda Travel
    beq EastDoorDone
    lda SignX
    bmi EastDoorDone
    lda DeltaX
    beq EastDoorDone
    lda XPos
    cmp #144
    bne EastDoorDone
    lda YPos
    cmp #28
    bcc EastDoorDone
    cmp #45
    bcs EastDoorDone
    lda #2
    sta TransitionRequested
EastDoorDone
    lda TransitionRequested
    beq RoomHeightReady
    ldx RoomIndex
    lda NextBossY,x
    sta Target
RoomHeightReady
    sta WSYNC               ; 3: novo encontro, preservando as vidas restantes
    lda TransitionRequested
    beq RoomStateDone
    inc RoomIndex
    lda #6
    sta BossHP
    lda #90
    sta PhaseTimer
    lda #72
    sta BossX
    lda Target
    sta BossY
    lda #0
    sta GameState
    sta DoorOpen
    sta ExitDirection
    sta XFrac
    sta YFrac
    sta BossPhase
    sta BossHeading
    sta ShotActive
    sta EnemyActive
    sta HazardActive
    sta HazardVisible
RoomStateDone
    sta WSYNC               ; 4: chegada e remocao dos efeitos do chefe anterior
    lda TransitionRequested
    beq RoomDone
    cmp #1
    bne ArriveFromWest
    lda #66
    sta YPos
    bne RoomEntryDone
ArriveFromWest
    lda #8
    sta XPos
RoomEntryDone
    lda #0
    sta InvulnTimer
    sta BossFlash
    sta SoundTimer
    sta AimRequest
    sta WallHit
    sta EnemySpawn
    sta PatrolNode
    sta PatrolMoving
    sta Travel
RoomDone
    rts

UpdateShot
    sta WSYNC               ; 1: um projetil por vez; segurar repete
    lda #0
    sta NewShot
    lda GameState
    bne ShotInputDone
    lda ShotActive
    bne ShotInputDone
    bit INPT4
    bmi ShotInputDone
    lda #2
    sta ShotActive
    inc NewShot
    lda Heading
    sta ShotHeading
ShotInputDone
    sta WSYNC               ; 2: nasce a frente do jogador
    lda NewShot
    beq ShotSpawnDone
    ldx ShotHeading
    lda XPos
    clc
    adc ShotSpawnX,x
    sta ShotX
    lda YPos
    clc
    adc ShotSpawnY,x
    sta ShotY
    lda #0
    sta ShotXFrac
    sta ShotYFrac
ShotSpawnDone
    sta WSYNC               ; 3: X em ponto fixo
    lda GameState
    bne ShotXDone
    lda ShotActive
    beq ShotXDone
    lda NewShot
    bne ShotXDone
    ldx ShotHeading
    clc
    lda ShotXFrac
    adc ShotVelocityXLo,x
    sta ShotXFrac
    lda ShotX
    adc ShotVelocityXHi,x
    sta ShotX
ShotXDone
    sta WSYNC               ; 4: Y em ponto fixo
    lda GameState
    bne ShotYDone
    lda ShotActive
    beq ShotYDone
    lda NewShot
    bne ShotYDone
    ldx ShotHeading
    clc
    lda ShotYFrac
    adc ShotVelocityYLo,x
    sta ShotYFrac
    lda ShotY
    adc ShotVelocityYHi,x
    sta ShotY
ShotYDone
    sta WSYNC               ; 5: nunca desenha fora da arena
    lda ShotX
    cmp #4
    bcc RemoveShot
    cmp #154
    bcs RemoveShot
    lda ShotY
    cmp #4
    bcc RemoveShot
    cmp #76
    bcc ShotBoundsDone
RemoveShot
    lda #0
    sta ShotActive
ShotBoundsDone
    sta WSYNC               ; 6
    rts


; AABB: jogador8x8, chefe16x12, tiro2x1, bala4x2. Um dano por quadro.
PrepareRender
    sta WSYNC               ; 1: direcao e janela vertical do jogador
    lda Heading
    asl
    asl
    asl
    clc
    adc #<ArrowSprites
    sec
    sbc YPos
    sta PlayerPtr
    lda #>ArrowSprites
    sta PlayerPtr+1
    lda #$10
    sta NUSIZ0              ; M0 dois pixels
    lda #$25
    sta NUSIZ1              ; P1 dobrado, M1 quatro pixels
    lda #$AE
    sta COLUP0
    sta WSYNC               ; 2: sprite e cor do chefe
    ldx RoomIndex
    lda BossSpriteOffsets,x
    clc
    adc #<BullSprite
    sec
    sbc BossY
    sta BossPtr
    lda #>BullSprite
    sta BossPtr+1
    ldx BossPhase
    lda PhaseColors,x
    cpx #1
    bne NotWarningColor
    lda FrameCounter
    and #4
    beq WarningDark
    lda #$1E
    bne BossColorReady
WarningDark
    lda #$26
    bne BossColorReady
NotWarningColor
    cpx #2
    bne BossColorReady
    ldx RoomIndex
    cpx #2
    bne BossColorReady
    lda #$CE                ; nucleo exposto do Guardiao
BossColorReady
    ldx BossFlash
    beq BossNotFlashing
    lda #$0E
BossNotFlashing
    sta BossColor
    sta COLUP1
    sta WSYNC               ; 3: mascaras e cores da arena
    lda #$FF
    sta PlayerMask
    sta BossMask
    lda InvulnTimer
    beq PlayerVisible
    lda FrameCounter
    and #4
    bne PlayerVisible
    lda #0
    sta PlayerMask
PlayerVisible
    lda Lives
    bne PlayerAliveRender
    sta PlayerMask
PlayerAliveRender
    lda PlayerMask
    bne PlayerPointerReady
    lda #0                  ; zona vazia antes dos sprites, sem AND no raster
    sta PlayerPtr
PlayerPointerReady
    ldx GameState
    lda SceneColors,x
    sta SceneColor
    lda WallColors,x
    sta WallColor
    lda BossHP
    bne MasksReady
    lda #0
    sta BossMask
    sta BossPtr
MasksReady
    sta WSYNC               ; 4: barras e mensagem (indice de encontro ou estado)
    ldx Lives
    lda PlayerBars,x
    sta PlayerBar
    ldx BossHP
    lda BossBars,x
    sta BossBar
    ldx RoomIndex
    lda GameState
    beq CombatMessage
    tax
    lda StateMessages,x
    tax
CombatMessage
    lda MessageOffsets,x
    tay
    lda #>MessageLeft
    sta MessageLeftPtr+1
    sta MessageRight0Ptr+1
    sta MessageRight1Ptr+1
    sta WSYNC               ; 5: ponteiros de mensagem e pixels iniciais
    tya
    clc
    adc #<MessageLeft
    sta MessageLeftPtr
    tya
    clc
    adc #<MessageRight0
    sta MessageRight0Ptr
    tya
    clc
    adc #<MessageRight1
    sta MessageRight1Ptr
    lda #0
    sta PlayerPixels
    sta BossPixels
    sta ShotPixels
    sta EnemyPixels
    sta WSYNC               ; 6: geometria base, portas e corredores
    lda #>WallRest
    sta WallPF1Ptr+1
    lda #<WallRest
    sta WallPF1Ptr
    lda #>WallRest
    sta WallPF2Ptr+1
    lda #<WallRest
    sta WallPF2Ptr
    lda #>RightWallClosed
    sta RightWallPtr+1
    lda #<RightWallClosed
    sta RightWallPtr
    lda DoorOpen
    beq DoorGeometryReady
    lda ExitDirection
    cmp #1
    bne EastDoorGeometry
    lda #<NorthWallOpen
    sta WallPF2Ptr
    lda #>NorthWallOpen
    sta WallPF2Ptr+1
    bne DoorGeometryReady
EastDoorGeometry
    lda #<RightWallOpen
    sta RightWallPtr
DoorGeometryReady
    sta WSYNC               ; 7: aviso/perigo de chao e geometria correspondente
    lda HazardVisible
    beq RenderReady
    lda BossColor
    sta WallColor
    lda HazardAxis
    cmp #2
    bcs RenderReady
    cmp #0
    bne VerticalGeometry
    lda #<HorizontalBand
    sta WallPF1Ptr
    sta WallPF2Ptr
    lda #>HorizontalBand
    sta WallPF1Ptr+1
    sta WallPF2Ptr+1
    bne RenderReady
VerticalGeometry
    lda #<VerticalBand
    sta WallPF2Ptr
    lda #>VerticalBand
    sta WallPF2Ptr+1
RenderReady
    sta WSYNC               ; 8: janela da bala e PF0 da segunda scanline
    lda RightWallPtr
    sec
    sbc #1
    sta RightSecondPtr
    lda RightWallPtr+1
    sta RightSecondPtr+1
    lda #0
    ldx EnemyActive
    beq EnemyPointerReady
    lda #<EnemySprite
    sec
    sbc EnemyY
EnemyPointerReady
    sta EnemyPtr
    lda #>EnemySprite
    sta EnemyPtr+1
    lda #0
    sta BeamMode
    lda HazardVisible
    beq BeamSelectionReady
    lda HazardAxis
    cmp #2
    bcc BeamSelectionReady
    sta BeamMode
BeamSelectionReady
    sta WSYNC               ; 9: M1 desenha o feixe nas duas diagonais
    lda BeamMode
    beq NoBeamMotion
    tax
    lda BeamMotions,x
    sta BeamMotion
    lda BeamStarts,x
    sta BeamStartX
    lda #<BeamPage
    sta EnemyPtr
    lda #>BeamPage
    sta EnemyPtr+1
    lda #$35                ; feixe de oito pixels, chefe permanece dobrado
    sta NUSIZ1
    rts
NoBeamMotion
    lda #0
    sta BeamMotion
    rts

; Efeitos curtos usam um canal. O aviso pulsa mesmo sem disparos/acertos.
UpdateAudio
    sta WSYNC
    lda #0
    sta AUDV0
    lda SoundTimer
    beq WarningAudio
    dec SoundTimer
    ldx SoundKind
    lda SoundControls,x
    sta AUDC0
    lda SoundFrequencies,x
    sta AUDF0
    lda #5
    sta AUDV0
    jmp AudioReady
WarningAudio
    lda GameState
    bne AudioReady
    lda BossPhase
    cmp #1
    bne ChargeAudio
    lda PhaseTimer
    and #8
    beq AudioReady
    lda #4
    sta AUDC0
    lda #12
    sta AUDF0
    lda #4
    sta AUDV0
    bne AudioReady
ChargeAudio
    cmp #2
    bne AudioReady
    lda #8
    sta AUDC0
    lda #7
    sta AUDF0
    lda #3
    sta AUDV0
AudioReady
    sta WSYNC
    rts

; Calibracao dos estudos existentes. M0 tem reset um pixel antes de P0;
; P1 dobrado comeca um pixel depois. Um HMOVE aplica os tres ao final.
    align 32
PositionShot
    lda ShotX
    cmp #4
    bcc SafeShotPosition
    cmp #154
    bcc ShotPositionValid
SafeShotPosition
    lda #4                  ; tiro inativo tambem deve ter posicao segura
ShotPositionValid
    clc
    adc #1
    sta Target
    sta WSYNC
    nop
    nop
    sec
ShotDivideBy15
    sbc #15
    bcs ShotDivideBy15
    eor #7
    asl
    asl
    asl
    asl
    sta RESM0
    sta HMM0
    sta WSYNC
    lda Target
    cmp #150
    bcs ShotPositionDone
    sta WSYNC
ShotPositionDone
    rts
    align 32
PositionBoss
    lda BossX
    sec
    sbc #1
    sta WSYNC
    nop
    nop
    sec
BossDivideBy15
    sbc #15
    bcs BossDivideBy15
    eor #7
    asl
    asl
    asl
    asl
    sta RESP1
    sta HMP1
    sta WSYNC
    rts
    align 32
PositionEnemy
    lda BeamMode
    beq NormalEnemyPosition
    lda BeamStartX
    jmp EnemyPositionValid
NormalEnemyPosition
    lda EnemyX
    cmp #8
    bcc SafeEnemyPosition
    cmp #149
    bcc EnemyPositionValid
SafeEnemyPosition
    lda #8
EnemyPositionValid
    clc
    adc #1
    sta Target
    sta WSYNC
    nop
    nop
    sec
EnemyDivideBy15
    sbc #15
    bcs EnemyDivideBy15
    eor #7
    asl
    asl
    asl
    asl
    sta RESM1
    sta HMM1
    sta WSYNC
    lda Target
    cmp #150
    bcs EnemyPositionDone
    sta WSYNC
EnemyPositionDone
    rts
    align 32
PositionPlayer
    lda XPos
    sta WSYNC
    nop
    nop
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
    sta WSYNC
    sta HMOVE
    rts

    include "beam_kernel.asm"

InputHeadings
    byte $FF,0,4,$FF,6,7,5,6,2,1,3,2,$FF,0,4,$FF
; Velocidades de movimento assinadas de 16 bits (parte inteira e fracao).
VelocityX
    byte 0,136,192,136,0,120,64,120
VelocityY
    byte 64,120,0,136,192,136,0,120
; O sinal nao pode ser inferido pelo bit 7 da fracao quando modulo > 127.
VelocitySignX
    byte 0,0,0,0,0,$FF,$FF,$FF
VelocitySignY
    byte $FF,$FF,0,0,0,0,0,$FF
ShotSpawnX
    byte 3,7,8,7,3,-1,-2,-1
ShotSpawnY
    byte -2,-1,3,7,8,7,3,-1
ShotVelocityXLo
    byte $00,$6A,$00,$6A,$00,$96,$00,$96
ShotVelocityXHi
    byte $00,$01,$02,$01,$00,$FE,$FE,$FE
ShotVelocityYLo
    byte $00,$96,$00,$6A,$00,$6A,$00,$96
ShotVelocityYHi
    byte $FE,$FE,$00,$01,$02,$01,$00,$FE
PhaseColors
    byte $08,$1E,$46,$CE
SceneColors
    byte $00,$C2,$42,$00
WallColors
    byte $06,$CE,$46,$CE
NextBossY
    byte 6,18,18,18
BeamMotions
    byte 0,0,$E0,$20
BeamStarts
    byte 0,0,0,152
BossSpriteOffsets
    byte 0,12,24,36
StateMessages
    byte 0,5,6,4
PlayerBars
    byte $00,$80,$A0,$A8
BossBars
    byte $00,$80,$C0,$E0,$F0,$F8,$FC
MessageOffsets
    byte 0,5,10,15,20,25,30
SoundControls
    byte 0,8,4,4,4
SoundFrequencies
    byte 0,18,4,8,12

    align 256
WallPF0
    byte $F0,$F0,$F0,$F0
    REPEAT 72
    byte $10
    REPEND
    byte $F0,$F0,$F0,$F0
WallRest
    byte $FF,$FF,$FF,$FF
    REPEAT 72
    byte $00
    REPEND
    byte $FF,$FF,$FF,$FF
; Pares alinhados, indexados sem cruzamento de pagina.
    align 256
RightWallSecondClosed
    byte 0
RightWallClosed
    byte $F0,$F0,$F0,$F0
    REPEAT 72
    byte $10
    REPEND
    byte $F0,$F0,$F0,$F0
RightWallSecondOpen
    byte 0
RightWallOpen
    byte $F0,$F0,$F0,$F0
    REPEAT 24
    byte $10
    REPEND
    REPEAT 24
    byte $00
    REPEND
    REPEAT 24
    byte $10
    REPEND
    byte $F0,$F0,$F0,$F0
NorthWallOpen
    byte $0F,$0F,$0F,$0F
    REPEAT 72
    byte $00
    REPEND
    byte $FF,$FF,$FF,$FF
    align 256
HorizontalBand
    byte $FF,$FF,$FF,$FF
    REPEAT 30
    byte 0
    REPEND
    REPEAT 12
    byte $FF
    REPEND
    REPEAT 30
    byte 0
    REPEND
    byte $FF,$FF,$FF,$FF
VerticalBand
    byte $FF,$FF,$FF,$FF
    REPEAT 72
    byte $F0
    REPEND
    byte $FF,$FF,$FF,$FF

    align 256
MessageLeft
    byte $53,$55,$53,$55,$73
    byte $57,$51,$23,$21,$27
    byte $25,$55,$75,$57,$55
    byte $75,$25,$23,$25,$75
    byte $75,$17,$37,$17,$75
    byte $75,$25,$25,$27,$75
    byte $71,$51,$51,$51,$77
MessageRight0
    byte $10,$10,$10,$10,$70
    byte $70,$10,$30,$10,$70
    byte $30,$50,$30,$50,$50
    byte $50,$70,$70,$70,$50
    byte $50,$50,$20,$50,$50
    byte $50,$70,$70,$70,$50
    byte $70,$10,$70,$40,$70
MessageRight1
    byte $80,$80,$80,$80,$E0
    byte $40,$40,$40,$00,$40
    byte $C0,$A0,$A0,$A0,$C0
    byte $E0,$80,$A0,$A0,$E0
    byte $E0,$40,$40,$40,$40
    byte $40,$40,$40,$00,$40
    byte $E0,$80,$C0,$80,$E0

; Alturas verificadas no kernel, margem inicial vazia para a piscada de P0.
    align 256
    ds 128,0
ArrowSprites
    byte $00,$18,$3C,$7E,$18,$18,$18,$00
    byte $00,$1E,$3E,$1E,$3E,$70,$20,$00
    byte $00,$08,$0C,$7E,$7E,$0C,$08,$00
    byte $00,$20,$74,$3E,$1E,$3E,$1E,$00
    byte $00,$18,$18,$18,$7E,$3C,$18,$00
    byte $00,$04,$0E,$7C,$78,$7C,$78,$00
    byte $00,$10,$30,$7E,$7E,$30,$10,$00
    byte $00,$78,$78,$78,$7C,$2E,$04,$00
BullSprite
    byte $81,$C3,$E7,$FF,$7E,$5A,$7E,$3C,$7E,$66,$42,$C3
EyeSprite
    byte $18,$3C,$7E,$FF,$C3,$99,$99,$C3,$FF,$7E,$24,$66
ShieldSprite
    byte $7E,$FF,$DB,$DB,$FF,$E7,$E7,$FF,$7E,$3C,$18,$18
KingSprite
    byte $A5,$E7,$FF,$7E,$5A,$7E,$3C,$7E,$DB,$99,$24,$66

    align 256
    ds 128,0
EnemySprite
    byte 2,2
    ds 126,0

; Dados do feixe nao sobrepoem a janela do projetil normal.
    org $1F00
    rorg $FF00
BeamPage
    ds 4,0
    ds 72,2
    ds 4,0

; O acesso F8 troca o banco antes da instrucao seguinte. Os dez bytes
; deste trampoline e o boot sao identicos nos dois bancos.
    org $1FA0
    rorg $FFA0
    bit $1FF8
    jsr UpdateCombatBank
    bit $1FF9
    rts
    org $1FC0
    rorg $FFC0
BankBoss
    bit $1FF8
    jsr UpdateBossBank
    bit $1FF9
    rts
    org $1FD0
    rorg $FFD0
ColdBoot
    bit $1FF9
    jmp Reset
    org $1FFA
    rorg $FFFA
    word $FFD0,$FFD0,$FFD0
