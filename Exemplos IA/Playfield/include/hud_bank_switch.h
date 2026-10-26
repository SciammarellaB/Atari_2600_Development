; Mesmo endereco e mesmos bytes em todos os bancos, inclusive o banco 7.
HudEnter
        lda $FFFB        ; F4: seleciona banco 7
        jmp $F100
HudReturn
        ldx Room
        lda RoomBanks,x  ; salas logicas podem compartilhar um template
        tax
        lda $FFF4,x
        jmp EndVisible
HudSwitchEnd
        if HudSwitchEnd > $FFF4
        err
        endif
