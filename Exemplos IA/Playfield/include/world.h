; Estado de quinze salas: coletas, chaves, switches e saida final.
        MAC WORLD_COLLECT
UpdateWorld
        bit PuzzleFlags
        bpl WorldActive
        rts
WorldActive
        lda PlayerX
        clc
        adc #4
        cmp #32
        bcc WorldDone
        cmp #40
        bcs WorldDone
        lda PlayerY
        clc
        adc #2
        cmp #34
        bcc WorldDone
        cmp #38
        bcs WorldDone
        ldx Room
        lda ObjectTypes,x
        beq WorldDone
        lda RoomPickMasks,x
        sta InputBits
        cpx #8
        bcc CollectLow
        lda PickedHi
        and InputBits
        bne WorldDone
        lda PickedHi
        ora InputBits
        sta PickedHi
        jmp CollectedObject
CollectLow
        lda PickedLo
        and InputBits
        bne WorldDone
        lda PickedLo
        ora InputBits
        sta PickedLo
CollectedObject
        lda ObjectTypes,x
        jmp ApplyObject
WorldDone
        jmp CheckDoor
        ENDM

        MAC WORLD_EFFECTS
ApplyObject
        cmp #2
        beq CollectAmmo
        cmp #3
        beq CollectHealth
        cmp #4
        beq CollectSwitch
        cmp #8
        beq CollectSuiteSwitch
        tax
        lda ItemWeaponBits,x
        ora Weapon
        sta Weapon
        jmp WorldAction
CollectAmmo
        sed
        clc
        lda Ammo
        adc #$12
        bcc AmmoStored
        lda #$99
AmmoStored
        sta Ammo
        cld
        jmp WorldAction
CollectHealth
        lda #3
        sta Health
        jmp WorldAction
CollectSwitch
        lda #1
        bne StoreSwitch
CollectSuiteSwitch
        lda #8
StoreSwitch
        ora PuzzleFlags
        sta PuzzleFlags
        jmp WorldAction
ItemWeaponBits
        byte 0,1,0,0,0,2,4,8,0
        ENDM

        MAC WORLD_PREPARE
PrepareWorld
        ldx Room
        lda GateBits,x
        beq WorldGateOpen
        and PuzzleFlags
        bne WorldGateOpen
        lda #2
        bne StoreWorldGate
WorldGateOpen
        lda #0
StoreWorldGate
        sta GateMask
        lda #$FF
        sta ObjectMask
        lda RoomPickMasks,x
        sta InputBits
        lda PickedLo
        cpx #8
        bcc WorldPickupByte
        lda PickedHi
WorldPickupByte
        and InputBits
        beq WorldPrepared
        lda ObjectTypes,x
        cmp #4
        beq UsedSwitch
        cmp #8
        beq UsedSwitch
        lda #0
        beq StoreObjectMask
UsedSwitch
        lda #$81
StoreObjectMask
        sta ObjectMask
WorldPrepared
        rts
        ENDM

        MAC WORLD_SWITCH
CheckDoor
        lda GateMask
        beq WorldPrepare
        ldx Room
        lda GateKeys,x
        and Weapon
        beq WorldPrepare
        lda GateDirections,x
        cmp #2
        bcs CheckVerticalDoor
        lda PlayerY
        cmp #17
        bcc WorldPrepare
        cmp #28
        bcs WorldPrepare
        lda GateDirections,x
        beq DoorLeft
        lda PlayerX
        cmp #140
        bcc WorldPrepare
        bcs UnlockDoor
DoorLeft
        lda PlayerX
        cmp #9
        bcs WorldPrepare
        bcc UnlockDoor
CheckVerticalDoor
        lda PlayerX
        cmp #64
        bcc WorldPrepare
        cmp #85
        bcs WorldPrepare
        lda GateDirections,x
        cmp #2
        bne DoorDown
        lda PlayerY
        cmp #3
        bcs WorldPrepare
        bcc UnlockDoor
DoorDown
        lda PlayerY
        cmp #41
        bcc WorldPrepare
UnlockDoor
        lda GateBits,x
        ora PuzzleFlags
        sta PuzzleFlags
        lda GateKeys,x
        eor #$FF
        and Weapon
        sta Weapon
        jmp WorldAction
WorldPrepare
        jmp PrepareWorld
        ENDM

        MAC WORLD_FINISH
WorldAction
        jsr PlayActionSound
        jmp PrepareWorld
RoomPickMasks
        byte 1,2,4,8,16,32,64,128,1,2,4,8,16,32,64
        ENDM
