"""Fonte de verdade eletrica do adaptador EPROM, revisao 0.1.
Conectores NAO sao encaixe direto no Mega; usam cabos ponto a ponto.
"""
import json
from pathlib import Path

AP=list(range(22,37))
RP=[47,38,37,40,41,42,43,44]
WP=list(range(2,10))
EP={1:'VPP',2:'A12',3:'A7',4:'A6',5:'A5',6:'A4',7:'A3',8:'A2',
    9:'A1',10:'A0',11:'Q0',12:'Q1',13:'Q2',14:'GND',15:'Q3',16:'Q4',
    17:'Q5',18:'Q6',19:'Q7',20:'CE_N',21:'A10',22:'OE_N',23:'A11',
    24:'A9',25:'A8',26:'A13',27:'A14',28:'VCC_EP'}
PARTS={}
def part(ref,value,kind,pins):
    PARTS[ref]={'value':value,'kind':kind,'pins':{str(k):v for k,v in pins.items()}}
part('U1','ST TS27C256Q / DIP28','dip28',EP)
for ref in ['U2','U3']:
    part(ref,'LM339N / DIP14','dip14',{3:'V_AUX',12:'GND'})
part('J1','ENDERECOS - MEGA','header16',dict([(i+1,f'A{i}') for i in range(15)]+[(16,'GND')]))
part('J2','LEITURA +5M - MEGA','header10',dict([(i+1,f'RD{i}') for i in range(8)]+[(9,'+5M'),(10,'GND')]))
part('J3','ESCRITA E CONTROLES - MEGA','header12',dict([(i+1,f'WR{i}') for i in range(8)]+[(9,'CE_DRV'),(10,'OE_DRV'),(11,'GND'),(12,'NC')]))
part('J4','FONTES EXTERNAS','terminal6',{1:'VCC_EP',2:'GND',3:'VPP',4:'GND',5:'V_AUX',6:'GND'})
comparators=[(5,4,2),(7,6,1),(9,8,14),(11,10,13)]
for i in range(8):
    part(f'Q{i+1}','2N7000 Microchip TO92 S-G-D','mos',{1:'GND',2:f'G{i}',3:f'Q{i}'})
    part(f'R{i+1}','220R','res',{1:f'WR{i}',2:f'G{i}'})
    part(f'R{i+9}','100k','res',{1:f'G{i}',2:'GND'})
    part(f'R{i+17}','10k','res',{1:'VCC_EP',2:f'Q{i}'})
    part(f'R{i+25}','4k7','res',{1:'+5M',2:f'RD{i}'})
    chip='U2' if i<4 else 'U3'
    plus,minus,out=comparators[i%4]
    PARTS[chip]['pins'].update({str(plus):f'Q{i}',str(minus):'VREF',str(out):f'RD{i}'})
for n,sig,drv,base in [(9,'CE_N','CE_DRV',33),(10,'OE_N','OE_DRV',36)]:
    part(f'Q{n}','2N7000 Microchip TO92 S-G-D','mos',{1:'GND',2:f'G{n}',3:sig})
    part(f'R{base}','220R','res',{1:drv,2:f'G{n}'})
    part(f'R{base+1}','100k','res',{1:f'G{n}',2:'GND'})
    part(f'R{base+2}','10k','res',{1:'VCC_EP',2:sig})
part('R39','22k 1%','res',{1:'+5M',2:'VREF'})
part('R40','10k 1%','res',{1:'VREF',2:'GND'})
for i,net in enumerate(['VCC_EP','VPP','V_AUX','V_AUX','VREF'],1):
    part(f'C{i}','100nF 25V','cap',{1:net,2:'GND'})
for i,net in enumerate(['GND','+5M','VCC_EP','VPP','V_AUX','VREF','CE_N','OE_N'],1):
    part(f'TP{i}',net,'test',{1:net})
for i in range(1,5): part(f'H{i}','M3 NPTH','hole',{})

if __name__=='__main__':
    dest=Path(__file__).resolve().parents[1]/'contrato_eletrico.json'
    dest.write_text(json.dumps({'revision':'0.1','AP':AP,'RP':RP,'WP':WP,
        'parts':PARTS,'board_mm':[200,140],'mode':'PROGRAMMER_HARDWARE=1',
        'manual_rails':True},ensure_ascii=False,indent=2))
    print(dest)
