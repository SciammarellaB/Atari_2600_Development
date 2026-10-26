; Retangulos inclusivos. O primeiro footprint do template e a porta.
; Portas abertas pulam esse retangulo; os demais volumes sao sempre solidos.
        MAC COLLISION_BOX
CollisionBox
        ldx Room
        lda RoomSolidEnds,x
        sta CollisionPtr
        ldy RoomSolidStarts,x
        lda GateMask
        bne NextSolidRect
        iny
        iny
        iny
        iny
NextSolidRect
        cpy CollisionPtr
        beq PointClear
        lda SolidRects,y
        cmp RightCol
        beq RectCheckRight
        bcs SkipSolidRect
RectCheckRight
        lda SolidRects+2,y
        cmp LeftCol
        bcc SkipSolidRect
        lda SolidRects+1,y
        cmp BottomRow
        beq RectCheckBottom
        bcs SkipSolidRect
RectCheckBottom
        lda SolidRects+3,y
        cmp ScanRow
        bcs PointBlocked
SkipSolidRect
        iny
        iny
        iny
        iny
        jmp NextSolidRect
PointBlocked
        sec
        rts
PointClear
        clc
        rts
        ENDM
