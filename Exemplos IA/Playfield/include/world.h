; Coletas e puzzles persistem ate Reset. Macros ocupam as folgas dos mapas.
        MAC WORLD_COLLECT
UpdateWorld
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
        jmp CheckBlueDoor
        ENDM

        MAC WORLD_EFFECTS
ApplyObject
        cmp #1
        beq CollectWeapon
        cmp #2
        beq CollectAmmo
        cmp #3
        beq CollectHealth
        cmp #4
        beq CollectSwitch
        lda Weapon
        ora #2
        sta Weapon
        jmp WorldAction
CollectWeapon
        lda Weapon
        ora #1
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
        lda PuzzleFlags
        ora #2
        sta PuzzleFlags
        jmp WorldAction
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
        lda ObjectTypes,x
        cmp #4
        bne PreparePickup
        lda PuzzleFlags
        and #2
        beq ColorWorldObject
        lda #$81
        sta ObjectMask
        bne ColorWorldObject
PreparePickup
        lda RoomPickMasks,x
        sta InputBits
        lda PickedLo
        cpx #8
        bcc WorldPickupByte
        lda PickedHi
WorldPickupByte
        and InputBits
        beq ColorWorldObject
        lda #0
        sta ObjectMask
ColorWorldObject
        rts
        ENDM

        MAC WORLD_SWITCH
CheckBlueDoor
        lda GateMask
        beq WorldPrepared
        lda Weapon
        and #2
        beq WorldPrepared
        ldx Room
        lda GateBits,x
        cmp #4
        bne WorldPrepared
        lda PlayerY
        cmp #17
        bcc WorldPrepared
        cmp #28
        bcs WorldPrepared
        lda GateColumns,x
        beq BlueDoorLeft
        lda PlayerX
        cmp #144
        bcc WorldPrepared
        bcs UnlockBlueDoor
BlueDoorLeft
        lda PlayerX
        cmp #8
        bcs WorldPrepared
UnlockBlueDoor
        lda PuzzleFlags
        ora #4
        sta PuzzleFlags
        lda Weapon
        and #$FD
        sta Weapon
        jmp WorldAction
WorldPrepared
        jmp PrepareWorld
        ENDM

        MAC WORLD_FINISH
WorldAction
        jsr PlayActionSound
        jmp PrepareWorld
RoomPickMasks
        byte 1,2,4,8,16,32,64,128,1
        ENDM
