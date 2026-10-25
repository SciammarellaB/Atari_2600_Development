"""Gera PCB KiCad de referencia a partir de contrato_eletrico.json.
Requer pcbnew do KiCad 7 ou posterior e footprints padrao KiCad 7.
Nao envia para fabricacao nem gera Gerbers automaticamente.
"""
import json, os, csv
from pathlib import Path
import pcbnew as k

OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
LIB=Path(os.environ.get('EPROM_FOOTPRINTS',str(ROOT/'tmp/pcb_eprom/footprints')))
C=json.loads((OUT/'contrato_eletrico.json').read_text())
P=C['parts']
F={
 'dip28':('Package_DIP','DIP-28_W15.24mm_LongPads'),
 'dip14':('Package_DIP','DIP-14_W7.62mm_LongPads'),
 'mos':('Package_TO_SOT_THT','TO-92_Inline_Wide'),
 'res':('Resistor_THT','R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'),
 'cap':('Capacitor_THT','C_Disc_D5.0mm_W2.5mm_P2.50mm'),
 'header16':('Connector_PinHeader_2.54mm','PinHeader_1x16_P2.54mm_Vertical'),
 'header10':('Connector_PinHeader_2.54mm','PinHeader_1x10_P2.54mm_Vertical'),
 'header12':('Connector_PinHeader_2.54mm','PinHeader_1x12_P2.54mm_Vertical'),
 'terminal6':('TerminalBlock_Phoenix','TerminalBlock_Phoenix_MKDS-1,5-6-5.08_1x06_P5.08mm_Horizontal'),
 'hole':('MountingHole','MountingHole_3.2mm_M3'),
 'test':('TestPoint','TestPoint_THTPad_D2.0mm_Drill1.0mm')}
POS={'U1':(57,34),'U2':(150,24),'U3':(150,66),
     'J1':(10,25),'J2':(190,22),'J3':(10,90),'J4':(120,125),
     'Q9':(58,91),'Q10':(58,111),
     'R33':(37,91),'R34':(47,97),'R35':(70,91),
     'R36':(37,111),'R37':(47,117),'R38':(70,111),
     'R39':(146,103),'R40':(160,103),
     'C1':(77,34),'C2':(49,34),'C3':(141,24),'C4':(141,66),'C5':(156,114),
     'H1':(4,4),'H2':(196,4),'H3':(196,136),'H4':(4,136)}
for i in range(8):
    y=16+12*i
    POS[f'Q{i+1}']=(110,y)
    POS[f'R{i+1}']=(87,y)
    POS[f'R{i+9}']=(99,y+6)
    POS[f'R{i+17}']=(126,y)
    POS[f'R{i+25}']=(166,y)
for i in range(8): POS[f'TP{i+1}']=(10+11*i,131)

def vec(x,y): return k.VECTOR2I(k.FromMM(x),k.FromMM(y))
def mm(n): return k.FromMM(n)
board=k.BOARD()
board.SetCopperLayerCount(2)
board.GetDesignSettings().SetCopperLayerCount(2)
board.GetDesignSettings().m_BoardThickness=mm(1.6)
netnames=sorted({net for v in P.values() for net in v['pins'].values() if net!='NC'})
nets={}
for name in netnames:
    n=k.NETINFO_ITEM(board,name); board.Add(n); nets[name]=n

pad_rows=[]
for ref,v in P.items():
    lib,name=F[v['kind']]
    fp=k.FootprintLoad(str(LIB/(lib+'.pretty')),name)
    if fp is None: raise RuntimeError('Footprint ausente: '+str((lib,name)))
    fp.SetReference(ref); fp.SetValue(v['value'])
    fp.SetFPID(k.LIB_ID(lib,name))
    fp.SetPosition(vec(*POS[ref]))
    # Mantem as referencias opcionais aos modelos 3D padrao da biblioteca.
    for text in [fp.Reference(),fp.Value()]:
        text.SetTextSize(vec(.9,.9)); text.SetTextThickness(mm(.15))
    fp.Value().SetVisible(False)
    if v['kind']=='res':
        fp.Reference().SetPosition(vec(POS[ref][0]+3.81,POS[ref][1]-2))
    elif v['kind']=='mos':
        fp.Reference().SetPosition(vec(POS[ref][0]+2.54,POS[ref][1]-3.3))
    elif v['kind']=='test':
        fp.Reference().SetPosition(vec(POS[ref][0],POS[ref][1]+2.2))
    elif v['kind']=='hole':
        fp.Reference().SetPosition(vec(POS[ref][0],POS[ref][1]+(5 if POS[ref][1]<70 else -5)))
    elif v['kind']=='terminal6':
        fp.Reference().SetPosition(vec(154,125))
    for pad in fp.Pads():
        num=pad.GetNumber()
        net=v['pins'].get(num)
        if net and net!='NC': pad.SetNet(nets[net])
        if num and num not in v['pins']:
            raise RuntimeError(f'Pad nao contratado: {ref}.{num}')
        xy=pad.GetPosition()
        pad_rows.append([ref,num,net or 'NC',round(k.ToMM(xy.x),4),round(k.ToMM(xy.y),4)])
    assert set(v['pins'])=={pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()},ref
    board.Add(fp)

for a,b in [((0,0),(200,0)),((200,0),(200,140)),((200,140),(0,140)),((0,140),(0,0))]:
    line=k.PCB_SHAPE();line.SetShape(k.SHAPE_T_SEGMENT);line.SetLayer(k.Edge_Cuts)
    line.SetStart(vec(*a));line.SetEnd(vec(*b));line.SetWidth(mm(.1));board.Add(line)

def label(text,x,y,size=1,layer=k.F_SilkS):
    t=k.PCB_TEXT(board);t.SetText(text);t.SetPosition(vec(x,y));t.SetTextSize(vec(size,size))
    t.SetTextThickness(mm(.15));t.SetLayer(layer);board.Add(t)
label('EPROM 27C256 + MEGA | REV 0.1 | PROTOTIPO',99,5,1.4)
label('FONTES MANUAIS - NAO HA PROTECAO CONTRA INVERSAO',99,8,1)
label('U1: SOQUETE DIP28 600mil - ENCAIXE ZIF NAO VERIFICADO',58,76,.85)
label('J1 -> D22..D36 / GND',24,19,.9)
label('J2 -> RP / +5M / GND',180,11,.9)
label('J3 -> D2..D9 / D45 / D46',34,84,.9)
label('VCC | GND | VPP | GND | AUX | GND',132.7,115,.85)
label('5/6V       5/12.5V       9..15V',132.7,118,.85)
label('PROGRAMMER_HARDWARE = 1',132,136,1)
for i,net in enumerate(['GND','+5M','VCC','VPP','AUX','VREF','/CE','/OE']):
    label(net,10+11*i,126.8,.8)
board.BuildListOfNets()
k.SaveBoard(str(OUT/'eprom27_rev01_nao_roteada.kicad_pcb'),board)
with (OUT/'pads_redes.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Referencia','Pad','Rede','X_mm','Y_mm']);w.writerows(pad_rows)
with (OUT/'bom.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Referencia','Valor','Tipo','Biblioteca','Footprint'])
    for ref,v in P.items(): w.writerow([ref,v['value'],v['kind'],*F[v['kind']]])
if not k.ExportSpecctraDSN(board,str(OUT/'fontes/eprom27_rev01.dsn')):
    raise RuntimeError('Falha na exportacao DSN')
print(f'{len(P)} footprints; {len(nets)} redes; {len(pad_rows)} pads. DSN exportado.')
