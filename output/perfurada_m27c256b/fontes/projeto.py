"""Fonte de verdade da revisao 0.2: perfurada com ilhas isoladas, passo 2.54 mm.
Coordenadas SEMPRE vistas pelo lado dos componentes. Nao e arquivo de PCB.
"""
from pathlib import Path
import json, csv
OUT=Path(__file__).resolve().parents[1]
PARTS={}
def add(ref,value,kind,pins,board='B',group='controle',xy=None):
    assert ref not in PARTS,('referencia duplicada',ref)
    PARTS[ref]=dict(value=value,kind=kind,pins={str(p):n for p,n in pins.items()},board=board,group=group)
    if xy: PARTS[ref]['origin']=xy
def passive(ref,value,a,b,kind='res',**kw): add(ref,value,kind,{1:a,2:b},**kw)

# A - soquete e interface, preservando o mapa logico do Mega anterior.
EP={1:'VPP',2:'A12',3:'A7',4:'A6',5:'A5',6:'A4',7:'A3',8:'A2',9:'A1',10:'A0',
    11:'Q0',12:'Q1',13:'Q2',14:'GND',15:'Q3',16:'Q4',17:'Q5',18:'Q6',19:'Q7',
    20:'CE_N',21:'A10',22:'OE_N',23:'A11',24:'A9',25:'A8',26:'A13',27:'A14',28:'VCC_EP'}
add('U1','M27C256B-10F1 + soquete DIP28 600 mil','dip28',EP,'A',xy=[10,9])
for n,y in [(2,7),(3,27)]:add(f'U{n}','LM339N DIP14','dip14',{3:'VIN_HOLD',12:'GND'},'A',xy=[56,y])
add('JA1','Mega D22..D36, GND','header16',{**{i+1:f'MA{i}' for i in range(15)},16:'GND'},'A',xy=[2,6])
add('JA2','Mega RD0..7, 5V USB, GND','header10',{**{i+1:f'RD{i}' for i in range(8)},9:'+5M',10:'GND'},'A',xy=[72,5])
add('JA3','Mega D2..9, D45, D46, GND, NC','header12',{**{i+1:f'WR{i}' for i in range(8)},9:'CE_DRV',10:'OE_DRV',11:'GND',12:None},'A',xy=[2,30])
HARNESS={1:'VCC_EP',2:'VPP',3:'VIN_HOLD',4:'GND',5:'+5B',6:'BUS_OE',7:'+5M',8:'UV_FAIL',9:None,10:None}
add('JA4','Para JB1, cabo numerado 1:1','header10',HARNESS,'A',xy=[72,43])
for i in range(8):
    y=5+5*i
    add(f'Q{i+1}','2N7000 Microchip: 1S 2G 3D','mos',{1:'GND',2:f'G{i}',3:f'Q{i}'},'A',xy=[35,y])
    for ref,val,a,b,x,dy in [(i+1,'220R',f'WR{i}',f'G{i}',27,0),
         (i+9,'100k',f'G{i}','GND',31,2),(i+17,'10k','VCC_EP',f'Q{i}',42,0),
         (i+25,'4k7','+5M',f'RD{i}',61,0)]:
        passive(f'R{ref}',val,a,b,board='A',xy=[x,y+dy])
    chip=f'U{2 if i<4 else 3}'; plus,minus,out=[(5,4,2),(7,6,1),(9,8,14),(11,10,13)][i%4]
    PARTS[chip]['pins'].update({str(plus):f'Q{i}',str(minus):'VREF_DATA',str(out):f'RD{i}'})
for n,sig,drv,base,x in [(9,'CE_N','CE_DRV',33,28),(10,'OE_N','OE_DRV',36,44)]:
    add(f'Q{n}','2N7000 Microchip: 1S 2G 3D','mos',{1:'GND',2:f'G{n}',3:sig},'A',xy=[x,46])
    passive(f'R{base}','1k',drv,f'G{n}',board='A',xy=[x-7,46])
    passive(f'R{base+1}','100k',f'G{n}','GND',board='A',xy=[x-1,49])
    passive(f'R{base+2}','1k','VCC_EP',sig,board='A',xy=[x+5,46])
passive('R39','22k 1%','+5M','VREF_DATA',board='A',xy=[55,45])
passive('R40','10k 1%','VREF_DATA','GND',board='A',xy=[62,45])
for n,net,x,y in [(1,'VCC_EP',18,8),(2,'VPP',6,8),(3,'VIN_HOLD',54,5),(4,'VIN_HOLD',54,25),(5,'VREF_DATA',59,49),(6,'+5B',5,27),(7,'+5B',17,27)]:
    passive(f'C{n}','100nF 25V',net,'GND','cap',board='A',xy=[x,y])
for u,start,x in [(4,0,7),(5,8,16)]:
    pins={1:'BUS_OE',19:'BUS_OE',20:'+5B',10:'GND'}
    for j in range(8):
        pins[j+2]=f'MA{start+j}' if start+j<15 else 'GND'
        pins[18-j]=f'A{start+j}' if start+j<15 else None
    add(f'U{u}','TI SN74AHCT541N DIP20 (nao HCT541)','dip20',pins,'A',xy=[x,29])
for ref,start,y in [('RN1',0,6),('RN2',8,22)]:
    add(ref,'SIP9 8x100k comum no pino1','header9',{1:'GND',**{j+2:f'MA{start+j}' if start+j<15 else 'GND' for j in range(8)}},'A',xy=[23,y])
passive('R41','100k','+5B','BUS_OE',board='A',xy=[6,42])
for n,gate,x,r in [(9,'G9',28,42),(10,'G10',44,44)]:
    add(f'QP{n}','BC337-40 onsemi: 1C 2B 3E','npn',{1:gate,2:f'UV_GATE{n}',3:'GND'},'A',xy=[x,43])
    passive(f'R{r}','4k7','UV_FAIL',f'UV_GATE{n}',board='A',xy=[x-7,43])
    passive(f'R{r+1}','100k',f'UV_GATE{n}','GND',board='A',xy=[x-7,49])
for i,net in enumerate(['GND','+5M','VCC_EP','VPP','VIN_HOLD','VREF_DATA','CE_N','OE_N'],1):
    add(f'TPA{i}',net,'test',{1:net},'A',xy=[5+9*(i-1),52])

# B - alimentacao. Modulos e chaves externos usam bornes de interface; nenhum
# footprint de modulo generico e presumido.
add('JB1','Para JA4, cabo numerado 1:1','header10',HARNESS,group='controle',xy=[74,27])
add('JB2','Entrada apos fusivel e S0','header2',{1:'VIN_FUSED',2:'GND'},group='entrada')
add('QP1','IRF9540N TO220 1G 2D 3S','to220',{1:'G_REVERSE',2:'VIN_FUSED',3:'VIN_PROT'},group='entrada')
passive('RP1','100k','G_REVERSE','GND',group='entrada')
add('ZP1','1N4742A 12V 1W','diode',{1:'G_REVERSE',2:'VIN_PROT'},group='entrada') #1A2K
add('DP1','1N5819','diode',{1:'VIN_PROT',2:'VIN_HOLD'},group='entrada')
passive('CP1','4700uF 25V','VIN_HOLD','GND','bulk',group='entrada')
passive('CP2','100nF 25V','VIN_HOLD','GND','cap',group='entrada')
add('JM1','MODULO BUCK: IN+, IN-, OUT+, OUT-','header4',{1:'VIN_PROT',2:'GND',3:'+5B',4:'GND'},group='entrada')
add('JM2','MODULO BOOST: IN+, IN-, OUT+, OUT-','header4',{1:'+5B',2:'GND',3:'+18B',4:'GND'},group='entrada')
passive('CP3','470uF 16V','+5B','GND','elect',group='entrada')
passive('CP4','100nF 25V','+5B','GND','cap',group='entrada')

# Regulador VCC programavel: tres contatos NO curto-circuitam segmentos ADJ.
# Rtop=100R; ajustar os quatro trimpots em ordem crescente 4.2/5/6/6.25V.
add('UP1','ST LM317T TO220 1ADJ 2OUT 3IN','to220',{1:'ADJ_VCC',2:'VCC_EP',3:'VIN_HOLD'},group='vcc')
passive('RP2','100R 1%','VCC_EP','ADJ_VCC',group='vcc')
passive('RP3','15R 1%','ADJ_VCC','VCC_D025_R',group='vcc')
add('RV1','3296W 10R multivoltas','trim',{1:'VCC_D025_R',2:'VCC_T1',3:'VCC_T1'},group='vcc')
passive('RP4','68R 1%','VCC_T1','VCC_D100_R',group='vcc')
add('RV2','3296W 50R multivoltas','trim',{1:'VCC_D100_R',2:'VCC_T2',3:'VCC_T2'},group='vcc')
passive('RP5','56R 1%','VCC_T2','VCC_D080_R',group='vcc')
add('RV3','3296W 20R multivoltas','trim',{1:'VCC_D080_R',2:'VCC_T3',3:'VCC_T3'},group='vcc')
passive('RP6','200R 1%','VCC_T3','VCC_BASE_R',group='vcc')
add('RV4','3296W 100R multivoltas','trim',{1:'VCC_BASE_R',2:'GND',3:'GND'},group='vcc')
passive('CP5','47uF 16V','VCC_EP','GND','elect',group='vcc')
passive('CP6','100nF 25V','VCC_EP','GND','cap',group='vcc')
add('DP2','1N4007 OUT->IN','diode',{1:'VCC_EP',2:'VIN_HOLD'},group='vcc')
passive('CP7','100nF 25V','VIN_HOLD','GND','cap',group='vcc')
add('UP2','ST LM317T TO220 1ADJ 2OUT 3IN','to220',{1:'ADJ_VPP',2:'+12P75',3:'+18B'},group='vpp')
passive('RP7','100R 1%','+12P75','ADJ_VPP',group='vpp')
passive('RP8','820R 1%','ADJ_VPP','VPP_R',group='vpp')
add('RV5','3296W 200R multivoltas','trim',{1:'VPP_R',2:'GND',3:'GND'},group='vpp')
for ref,val,net,kind in [('CP8','10uF 35V','+18B','elect'),('CP9','100nF 50V','+18B','cap'),('CP10','10uF 25V','+12P75','elect'),('CP11','100nF 25V','+12P75','cap')]:
    passive(ref,val,net,'GND',kind,group='vpp')
add('DP3','1N4007 OUT->IN','diode',{1:'+12P75',2:'+18B'},group='vpp')
passive('RP9','2k2 0.25W','VPP','GND',group='vpp')
passive('CP12','100nF 25V','VPP','GND','cap',group='vpp')

# G5V-2-H1 DC5 (30 mA). Numeracao fisica Omron, vista inferior no datasheet:
# 1/16 bobina; 4/6/8 = COM/NC/NO; 13/11/9 = COM/NC/NO.
for i,top,bottom in [(1,'ADJ_VCC','VCC_T1'),(2,'VCC_T1','VCC_T2'),(3,'VCC_T2','VCC_T3'),(4,'VPP','+12P75')]:
    group=f'rele{i}'
    pins={1:'+5B' if i<4 else 'COIL4_PLUS',16:f'COIL{i}_LOW',
          4:top,6:None if i<4 else 'VCC_EP',8:bottom,13:None,11:None,9:None}
    add(f'K{i}','Omron G5V-2-H1 DC5 (30mA)','relay',pins,group=group)
    add(f'QP{i+1}','BC337-40 onsemi: 1C 2B 3E','npn',{1:f'COIL{i}_LOW',2:f'BASE_K{i}',3:'GND'},group=group)
    passive(f'RP{10+i}','1k5' if i==4 else '2k2',f'K{i}_DRV',f'BASE_K{i}',group=group)
    passive(f'RP{14+i}','100k',f'BASE_K{i}','GND',group=group)
    add(f'DF{i}','1N4148','diode',{1:f'COIL{i}_LOW',2:f'CLAMP_K{i}'},group=group)
    add(f'ZF{i}','BZX85C12 12V','diode',{1:'+5B' if i<4 else 'COIL4_PLUS',2:f'CLAMP_K{i}'},group=group)

# Controle, undervoltage e referencia analogica exclusiva do Mega.
add('JB3','Mega controles: D10 D11 D12 D14 D48 D49 A0 A1 A2 A3 GND','header11',
    {1:'K1_DRV',2:'K2_DRV',3:'K3_DRV',4:'K4_DRV',5:'MODE_SW',6:'BUS_EN',7:'ADC_VCC',8:'ADC_VPP',9:'ADC_VIN',10:'ADC_B5',11:'GND'},group='controle',xy=[74,46])
add('JS1','Chave DPDT: C1 NO1 C2 NO2','header4',{1:'MODE_SW',2:'GND',3:'COIL4_PLUS',4:'+5B'},group='controle')
add('JB4','Para Mega AREF (referencia externa 2.5V)','header2',{1:'AREF_2V5',2:'GND'},group='controle')
add('UR1','LM4040AIZ-2.5/NOPB TI: 1NC 2K 3A','mos',{1:None,2:'AREF_2V5',3:'GND'},group='controle')
passive('RP19','1k','+5M','AREF_2V5',group='controle')
passive('CP13','100nF 25V','AREF_2V5','GND','cap',group='controle')
add('UC1','LM393N DIP8','dip8',{1:'UV_OK',2:'AREF_2V5',3:'UV_SENSE',4:'GND',5:'B5_UV',6:'AREF_2V5',7:'UV_OK',8:'VIN_HOLD'},group='controle')
passive('RP20','100k 0.1%','VIN_PROT','UV_SENSE',group='controle')
passive('RP21','29k4 0.1%','UV_SENSE','GND',group='controle')
passive('CP14','100nF 25V','VIN_HOLD','GND','cap',group='controle')
add('QP6','BC337-40 onsemi: 1C 2B 3E','npn',{1:'BUS_SLOW',2:'BASE_BUS',3:'GND'},group='controle')
passive('RP22','2k2','BUS_EN','BASE_BUS',group='controle')
passive('RP23','100k','BASE_BUS','GND',group='controle')
passive('RP24','10k','+5B','UV_OK',group='controle')
passive('RP25','8k2 1%','+5B','B5_UV',group='controle')
passive('RP26','10k 1%','B5_UV','GND',group='controle')
passive('RP27','10k 1%','+5B','BUS_SLOW',group='controle')
passive('CP16','10nF filme/C0G 5% 50V','BUS_SLOW','GND','cap',group='controle')
add('UC2','TI SN74HC14N DIP14 (nao HCT14)','dip14',
    {1:'UV_OK',2:'UV_FAIL',3:'GND',4:None,5:'BUS_SLOW',6:'BUS_INV',7:'GND',
     8:'BUS_OE',9:'BUS_INV',10:None,11:'GND',12:None,13:'GND',14:'+5B'},group='controle')
passive('CP15','100nF 25V','+5B','GND','cap',group='controle')
for i,target in [(7,'BASE_BUS'),(8,'BASE_K4')]:
    add(f'QP{i}','BC337-40 onsemi: 1C 2B 3E','npn',{1:target,2:f'UV_CLAMP{i}',3:'GND'},group='controle')
    passive(f'RP{21+i}','4k7','UV_FAIL',f'UV_CLAMP{i}',group='controle')
    passive(f'RP{23+i}','100k',f'UV_CLAMP{i}','GND',group='controle')

# ADC: divisores ANTES do MOSFET e pull-down de 10k DEPOIS fazem parte da escala.
for i,net,adc,rt in [(1,'VCC_EP','ADC_VCC','20k'),(2,'VPP','ADC_VPP','56k'),(3,'VIN_PROT','ADC_VIN','56k'),(4,'+5B','ADC_B5','20k')]:
    n=f'SENSE_{i}'
    passive(f'RS{i}A',rt+' 0.1%',net,n,group='sensores')
    passive(f'RS{i}B','10k 0.1%',n,'GND',group='sensores')
    passive(f'RS{i}C','10k 0.1%',adc,'GND',group='sensores')
    add(f'QS{i}','2N7000 Microchip: 1S 2G 3D','mos',{1:adc,2:'+5M',3:n},group='sensores')
    passive(f'CS{i}','100nF 25V',n,'GND','cap',group='sensores')
for i,net in enumerate(['GND','VIN_PROT','VIN_HOLD','+5B','+18B','VCC_EP','+12P75','VPP','AREF_2V5','UV_SENSE'],1):
    add(f'TPB{i}',net,'test',{1:net},group='sensores')

def shape(obj):
    k=obj['kind']; pins=obj['pins']
    if k.startswith('dip'):
        count=int(k[3:]);h=count//2;w=6 if count==28 else 3
        d=1 if obj['board']=='B' else 0
        return {str(i+1):[d,i+d] for i in range(h)}|{str(count-i):[w+d,i+d] for i in range(h)},(w+2,h+1)
    if k.startswith('header'):
        n=int(k[6:]);return {str(i+1):[0,i] for i in range(n)},(2,n+1)
    if k=='relay':
        return {'1':[8,1],'4':[5,1],'6':[3,1],'8':[1,1],'16':[8,4],'13':[5,4],'11':[3,4],'9':[1,4]},(10,6)
    if k in ['mos','npn','trim','to220']:
        d=1 if obj['board']=='B' else 0;y=2 if k=='trim' else d
        return {'1':[d,y],'2':[1+d,y],'3':[2+d,y]},(5,4 if k=='trim' else 3)
    if k=='bulk':return {'1':[3,4],'2':[6,4]},(10,10)
    if k=='elect':return {'1':[1,2],'2':[3,2]},(5,5)
    if k=='test':return {'1':[0,0]},(2,2)
    if k=='cap':
        d=1 if obj['board']=='B' else 0
        return {'1':[d,d],'2':[1+d,d]},(4,3)
    d=1 if obj['board']=='B' else 0
    return {'1':[0,d],'2':[3,d]},(5,3)

def place():
    zones={**{f'rele{i}':(3+18*(i-1),4,17,19) for i in range(1,5)},
       'entrada':(3,26,22,20),'vcc':(27,26,22,20),'vpp':(51,26,22,20),
       'sensores':(3,49,34,24),'controle':(39,49,34,24)}
    cursors={k:[v[0],v[1],0] for k,v in zones.items()}
    for ref,o in PARTS.items():
        offsets,(w,h)=shape(o)
        if 'origin' not in o:
            g=o['group'];x0,y0,zw,zh=zones[g];cursor=cursors[g]
            if cursor[0]+w>x0+zw:cursor[0]=x0;cursor[1]+=cursor[2];cursor[2]=0
            if cursor[1]+h>y0+zh:raise ValueError((ref,g,'zona sem espaco',cursor,w,h))
            o['origin']=[cursor[0],cursor[1]];cursor[0]+=w;cursor[2]=max(cursor[2],h)
        x,y=o['origin'];o['holes']={p:[x+dx,y+dy] for p,(dx,dy) in offsets.items()}
    # Desacoplamentos junto aos terminais de alimentacao; os antigos lugares
    # reservados pelo empacotador ficam livres para acomodacao de fios.
    for ref,origin in {'CP6':[32,22],'CP7':[27,22],'CP11':[51,22],
                       'CP13':[44,45],'CP14':[57,45]}.items():
        o=PARTS[ref];o['origin']=origin;offsets,_=shape(o)
        o['holes']={p:[origin[0]+dx,origin[1]+dy] for p,(dx,dy) in offsets.items()}
    occupied={}
    for ref,o in PARTS.items():
        assert set(o['holes'])==set(o['pins']),ref
        for pin,(x,y) in o['holes'].items():
            assert 1<=x<=75 and 1<=y<=(53 if o['board']=='A' else 74),(ref,pin,x,y)
            key=o['board'],x,y
            assert key not in occupied,(key,occupied.get(key),(ref,pin))
            occupied[key]=(ref,pin)

AP=list(range(22,37));RP=[47,38,37,40,41,42,43,44];WP=list(range(2,10))
MEGA={**{f'D{p}':f'MA{i}' for i,p in enumerate(AP)},**{f'D{p}':f'RD{i}' for i,p in enumerate(RP)},
      **{f'D{p}':f'WR{i}' for i,p in enumerate(WP)},'D45':'CE_DRV','D46':'OE_DRV',
      'D10':'K1_DRV','D11':'K2_DRV','D12':'K3_DRV','D14':'K4_DRV','D48':'MODE_SW','D49':'BUS_EN',
      'A0':'ADC_VCC','A1':'ADC_VPP','A2':'ADC_VIN','A3':'ADC_B5','AREF':'AREF_2V5','5V':'+5M','GND':'GND'}
if __name__=='__main__':
    place()
    C=dict(revision='0.2',target='ST M27C256B-10F1',pitch_mm=2.54,boards={'A':[75,53],'B':[75,74]},parts=PARTS,mega=MEGA,
      relay_states={'READ':[1,1,0,0],'PROGRAM':[0,0,0,1],'VERIFY_HIGH':[1,0,0,0],'VERIFY_LOW':[1,1,1,0]},
      adc={'A0':5,'A1':12.2,'A2':12.2,'A3':5},AREF_mV=2500,
      external=['Fonte12Vregulada1A','Fusivel1Aretardado+porta','S0liga/desliga','S1DPDTON-ON',
                'ModuloBUCK12->5V1Amin','ModuloBOOST5->18V0.1Amin','Mega2560USB'])
    (OUT/'contrato_eletrico.json').write_text(json.dumps(C,ensure_ascii=False,indent=2))
    with (OUT/'componentes.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Placa','Referencia','Valor','Tipo','Origem_coluna','Origem_linha'])
        for r,o in PARTS.items():w.writerow([o['board'],r,o['value'],o['kind'],*o['origin']])
    with (OUT/'pinos_furos_redes.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Placa','Referencia','Pino','Coluna','Linha','Rede'])
        for r,o in PARTS.items():
            for p,net in o['pins'].items():w.writerow([o['board'],r,p,*o['holes'][p],net or 'NC'])
    with (OUT/'mega.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Mega','Rede']);w.writerows(MEGA.items())
    print(len(PARTS),'componentes;',sum(len(o['pins']) for o in PARTS.values()),'pinos sem sobreposicao')
