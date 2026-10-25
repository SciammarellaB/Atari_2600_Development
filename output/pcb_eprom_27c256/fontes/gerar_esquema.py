#!/usr/bin/env python3
"""Gera esquema vetorial e KiCad legado; fonte de verdade: contrato_eletrico.json."""
import json
import uuid
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from html import escape

BASE = Path(__file__).resolve().parents[1]
C = json.loads((BASE / 'contrato_eletrico.json').read_text())
P = C['parts']
coverage = set()
W, H = 1680, 1188
FP = {}
if (BASE/'bom.csv').exists():
    with (BASE/'bom.csv').open(newline='') as source:
        FP={r['Referencia']:r['Biblioteca']+':'+r['Footprint'] for r in csv.DictReader(source)}

class Canvas:
    def __init__(self, n, title):
        self.n = n
        self.a = [f'<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 {W} {H}">', '<rect width="1680" height="1188" fill="white"/>', '<style>text{font-family:DejaVu Sans,sans-serif;fill:#142231;font-size:15px}.wire{fill:none;stroke:#23654d;stroke-width:2}.sym{fill:white;stroke:#142231;stroke-width:2}.pin{font-size:11px;fill:#536272}.small{font-size:12px}.title{font-size:25px;font-weight:bold}.panel{fill:#f8fafc;stroke:#c7d0db;stroke-width:1}</style>']
        self.text(35, 42, f'LEITOR / GRAVADOR ST TS27C256Q — {title}', 'title')
        self.text(35, 71, f'REVISÃO 0.1 • PROTÓTIPO • folha {n}/3 • PROGRAMMER_HARDWARE=1 • pinos físicos numerados')
        self.line(30, 90, 1650, 90, 'sym')
        self.line(30, 1130, 1650, 1130, 'sym')
        self.text(35, 1154, 'Mesmo nome de rede = conexão elétrica, inclusive entre folhas. J1/J2/J3: cabos ponto a ponto ao Mega; não é shield.', 'small')
        self.text(35, 1174, 'Fontes externas ajustadas manualmente. SEM proteção contra polaridade invertida. Circuito não ensaiado fisicamente.', 'small')
    def text(self, x, y, t, cls='', anchor='start'):
        self.a.append(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(str(t))}</text>')
    def line(self, x1,y1,x2,y2,cls='wire'):
        self.a.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="{cls}"/>')
    def rect(self,x,y,w,h,cls='sym'):
        self.a.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}"/>')
    def dot(self,x,y):
        self.a.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#23654d"/>')
    def circle(self,x,y,r,cls='sym'):
        self.a.append(f'<circle cx="{x}" cy="{y}" r="{r}" class="{cls}"/>')
    def poly(self, pts):
        self.a.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in pts)+'" class="sym"/>')
    def panel(self,x,y,w,h,title):
        self.rect(x,y,w,h,'panel'); self.text(x+15,y+27,title)
    def net(self,x,y,name,side='right'):
        self.line(x,y,x+(40 if side=='right' else -40),y)
        self.text(x+(45 if side=='right' else -45),y-5,name,'small','start' if side=='right' else 'end')
    def pin(self,ref,pin,x,y,net=None,side='right',showlabel=True):
        pin=str(pin); net = net or P[ref]['pins'][pin]
        coverage.add((ref,pin,net))
        self.a.append(f'<g data-ref="{ref}" data-pin="{pin}" data-net="{escape(net)}">')
        self.text(x+4,y-7,pin,'pin')
        if showlabel:self.net(x,y,net,side)
        self.a.append('</g>')
    def resistor(self,ref,x,y,horiz=False):
        val=P[ref]['value']; self.text(x+18,y-12,f'{ref} {val}','small')
        if horiz:
            self.line(x-50,y,x-25,y); self.rect(x-25,y-8,50,16); self.line(x+25,y,x+50,y)
            self.pin(ref,1,x-50,y,side='left'); self.pin(ref,2,x+50,y,showlabel=False)
        else:
            self.line(x,y-36,x,y-20); self.rect(x-8,y-20,16,40); self.line(x,y+20,x,y+36)
            self.pin(ref,1,x,y-36); self.pin(ref,2,x,y+36)
    def capacitor(self,ref,x,y):
        self.text(x+18,y-12,f'{ref} 100 nF / 25 V','small')
        self.line(x,y-30,x,y-5); self.line(x-13,y-5,x+13,y-5,'sym'); self.line(x-13,y+5,x+13,y+5,'sym'); self.line(x,y+5,x,y+30)
        self.pin(ref,1,x,y-30); self.pin(ref,2,x,y+30)
    def mos(self,ref,x,y):
        self.circle(x,y,31)
        self.line(x-13,y-19,x-13,y+19,'sym')
        for yy in (-16,0,16): self.line(x-5,y+yy-4,x-5,y+yy+4,'sym')
        self.line(x-5,y-16,x+14,y-16,'sym');self.line(x+14,y-16,x+14,y-50)
        self.line(x-5,y+16,x+14,y+16,'sym');self.line(x+14,y+16,x+14,y+50)
        self.line(x-55,y,x-13,y); self.line(x+14,y+16,x+14,y,'sym'); self.line(x+14,y,x-5,y,'sym')
        self.poly([(x-4,y),(x+3,y-4),(x+3,y+4)])
        self.text(x+38,y-10,f'{ref} 2N7000','small')
        self.pin(ref,1,x+14,y+50); self.pin(ref,2,x-55,y,side='left'); self.pin(ref,3,x+14,y-50)
    def comparator(self,ref,u,chan,x,y):
        # Pinagem física LM339N: canal A 5+/4-/2; B 7+/6-/1; C 9+/8-/14; D 11+/10-/13.
        plus,minus,out=[(5,4,2),(7,6,1),(9,8,14),(11,10,13)][u]
        self.poly([(x-40,y-45),(x-40,y+45),(x+45,y)])
        self.line(x-75,y-23,x-40,y-23);self.line(x-75,y+23,x-40,y+23);self.line(x+45,y,x+75,y)
        self.text(x-33,y-18,'+');self.text(x-33,y+28,'−')
        self.text(x-35,y-58,f'{ref}{chr(65+u)} LM339N','small')
        self.text(x-22,y+64,'saída coletor aberto','small')
        self.pin(ref,plus,x-75,y-23,side='left');self.pin(ref,minus,x-75,y+23,side='left');self.pin(ref,out,x+75,y)
    def power(self,ref,x,y,cap):
        self.rect(x-65,y-40,130,80);self.text(x-52,y-13,f'{ref}E LM339N');self.text(x-52,y+10,'alimentação','small')
        self.pin(ref,3,x,y-70); self.line(x,y-70,x,y-40)
        self.pin(ref,12,x,y+70);self.line(x,y+40,x,y+70)
        self.capacitor(cap,x+220,y)
    def dip(self,ref,x,y):
        w=210; spacing=30; h=14*spacing+90
        self.rect(x,y,w,h);self.text(x+w/2,y+22,ref,'','middle')
        self.text(x+w/2,y+45,'TS27C256Q','small','middle')
        for p in range(1,29):
            left=p<=14; row=(p-1 if left else 28-p); yy=y+65+row*spacing
            xx=x if left else x+w
            self.pin(ref,p,xx,yy,side='left' if left else 'right')
        self.text(x+w/2,y+h-6,'DIP-28 • vista superior','small','middle')
    def connector(self,ref,x,y):
        part=P[ref]; pins=part['pins'];h=len(pins)*25+45
        self.text(x,y-10,f'{ref} {part["value"]}','small');self.rect(x,y,36,h)
        for pin,net in pins.items():
            pp=int(pin); yy=y+30+(pp-1)*25
            self.rect(x+11,yy-4,8,8);self.line(x+19,yy,x+36,yy)
            self.pin(ref,pin,x+36,yy)
            if ref=='J1': info=f'Mega D{C["AP"][pp-1]}' if pp<=15 else 'Mega GND'
            elif ref=='J2': info=f'Mega D{C["RP"][pp-1]}' if pp<=8 else ('Mega 5V' if pp==9 else 'Mega GND')
            elif ref=='J3': info=f'Mega D{C["WP"][pp-1]}' if pp<=8 else {9:'Mega D45',10:'Mega D46',11:'Mega GND',12:'sem ligação'}[pp]
            else: info={1:'5V / 6V',2:'comum',3:'5V / 12,5V',4:'comum',5:'9 a 15V',6:'comum'}[pp]
            self.text(x+147,yy+5,info,'small')
    def finish(self):
        self.a.append('</svg>');out=BASE/f'esquema_{self.n:02d}.svg';out.write_text('\n'.join(self.a));ET.parse(out)

def control(s, q, rs, x, y, title):
    s.panel(x,y,500,250,title)
    s.resistor(rs[0],x+150,y+145,True)
    s.mos(q,x+320,y+145)
    s.line(x+200,y+145,x+265,y+145)
    s.resistor(rs[1],x+150,y+205)
    s.resistor(rs[2],x+320,y+75)

def channels(s,start,ref,cap):
    for c in range(start,start+4):
        col=(c-start)%2; row=(c-start)//2;x=35+col*820;y=110+row*435
        s.panel(x,y,790,420,f'CANAL Q{c} — escrita com inversão / leitura sem inversão')
        s.resistor(f'R{c+1}',x+160,y+210,True)
        s.resistor(f'R{c+9}',x+150,y+320)
        s.mos(f'Q{c+1}',x+330,y+220)
        s.line(x+210,y+210,x+245,y+210);s.line(x+245,y+210,x+245,y+220);s.line(x+245,y+220,x+275,y+220)
        s.resistor(f'R{c+17}',x+344,y+90)
        s.comparator(ref,c-start,c,x+555,y+220)
        s.resistor(f'R{c+25}',x+690,y+90)
        s.text(x+20,y+385,f'WR{c}=HIGH → Q{c}=LOW. WR{c}=LOW → MOSFET desligado; Q{c} liberado pelo pull-up.', 'small')
        s.text(x+20,y+405,f'RD{c}=HIGH quando Q{c} > VREF. Conectar apenas RD{c} à entrada do Mega.', 'small')
    s.power(ref,160,1045,cap)
    s.text(550,1020,'Cada entrada + lê Qn; cada entrada − recebe VREF ≈ 1,56 V.', 'small')
    s.text(550,1045,'Pull-up de Qn em VCC_EP; pull-up de RDn em +5M. Estas redes são diferentes.', 'small')
    s.text(550,1070,'2N7000 Microchip: 1=S, 2=G, 3=D. Gates em GND por 100 kΩ no reset.', 'small')
    s.text(550,1095,'Escrita depende de /OE desabilitado. Não unir dados da EPROM diretamente ao Mega.', 'small')

def svg_all():
    s=Canvas(1,'EPROM, conexões e controles')
    s.dip('U1',180,125)
    s.connector('J1',590,125);s.connector('J2',940,125);s.connector('J3',1280,125);s.connector('J4',940,470)
    s.text(1260,525,'FONTES MANUAIS — conferir antes de ligar','small')
    s.text(1260,550,'VCC_EP: leitura 5 V; programação 6 V','small')
    s.text(1260,575,'VPP: leitura 5 V; programação 12,5 V','small')
    s.text(1260,600,'+5M: somente os 5 V do Mega','small')
    s.text(1260,625,'V_AUX: LM339; GND comum em todo circuito','small')
    s.capacitor('C1',100,715);s.capacitor('C2',350,715)
    for i in range(8):
        x=650+(i%4)*240;y=690+(i//4)*80;ref=f'TP{i+1}';s.circle(x,y,6);s.text(x-18,y-15,ref,'small');s.pin(ref,1,x,y)
    control(s,'Q9',['R33','R34','R35'],35,850,'/CE: CE_DRV alto ativa CE_N baixo')
    control(s,'Q10',['R36','R37','R38'],555,850,'/OE: OE_DRV alto ativa OE_N baixo')
    s.panel(1090,850,555,250,'Referência para os comparadores')
    s.resistor('R39',1200,940);s.resistor('R40',1200,1035);s.capacitor('C5',1465,995)
    s.text(1105,1090,'VREF = +5M × 10k / (22k + 10k) ≈ 1,56 V','small')
    s.finish()
    s=Canvas(2,'canais de dados Q0 a Q3');channels(s,0,'U2','C3');s.finish()
    s=Canvas(3,'canais de dados Q4 a Q7');channels(s,4,'U3','C4');s.finish()

def sym_for(ref):
    """Geometria do símbolo legado; cada pino físico termina em rótulo global."""
    p=P[ref]; k=p['kind']; shapes=[]; pins={}
    if k=='res':
        shapes=['S -40 100 40 -100 0 1 10 N'];pins={'1':(0,200,'D'),'2':(0,-200,'U')}
    elif k=='cap':
        shapes=['P 2 0 1 10 -90 25 90 25 N','P 2 0 1 10 -90 -25 90 -25 N','P 2 0 1 10 0 50 0 25 N','P 2 0 1 10 0 -25 0 -50 N'];pins={'1':(0,150,'D'),'2':(0,-150,'U')}
    elif k=='mos':
        shapes=['C 0 0 150 0 1 10 N','P 2 0 1 10 -70 90 -70 -90 N','P 2 0 1 10 -20 90 -20 50 N','P 2 0 1 10 -20 20 -20 -20 N','P 2 0 1 10 -20 -50 -20 -90 N','P 3 0 1 10 -20 70 70 70 70 200 N','P 3 0 1 10 -20 -70 70 -70 70 -200 N','P 3 0 1 10 70 -70 70 0 -20 0 N','P 4 0 1 10 -20 0 15 20 15 -20 -20 0 F']
        shapes += ['P 2 0 1 10 -200 0 -70 0 N']
        pins={'1':(70,-300,'U'),'2':(-300,0,'R'),'3':(70,300,'D')}
    elif k=='test':
        shapes=['C 0 0 40 0 1 10 N','P 2 0 1 10 0 -50 0 -40 N'];pins={'1':(0,-150,'U')}
    elif k in ('header16','header10','header12','terminal6'):
        n=len(p['pins']);top=(n-1)*75;shapes=[f'S -150 {top+100} 100 {-top-100} 0 1 10 N']
        for i, pin in enumerate(p['pins']):
            yy=top-i*150;shapes.append(f'S -50 {yy+25} 0 {yy-25} 0 1 10 N');pins[pin]=(300,yy,'L')
    elif k=='dip28':
        shapes=['S -400 1500 400 -1500 0 1 10 N']
        for n in range(1,29):
            left=n<=14;row=n-1 if left else 28-n;pins[str(n)]=(-600 if left else 600,1300-row*200,'R' if left else 'L')
    elif k=='dip14':
        for i,(plus,minus,out) in enumerate([(5,4,2),(7,6,1),(9,8,14),(11,10,13)]):
            yy=900-i*600
            shapes.extend([f'P 4 0 1 10 -250 {yy+200} -250 {yy-200} 200 {yy} -250 {yy+200} N',f'T 0 -180 {yy+100} 60 0 0 1 + Normal 0 C C',f'T 0 -180 {yy-100} 60 0 0 1 - Normal 0 C C'])
            pins[str(plus)]=(-450,yy+100,'R');pins[str(minus)]=(-450,yy-100,'R');pins[str(out)]=(400,yy,'L')
        pins['3']=(0,1400,'D');pins['12']=(0,-1400,'U')
        shapes += ['P 2 0 1 10 0 1200 0 1300 N','P 2 0 1 10 0 -1200 0 -1300 N']
    return shapes,pins

def legacy():
    lib=['EESchema-LIBRARY Version 2.4','#encoding utf-8']
    geometries={}
    for ref,p in P.items():
        if p['kind']=='hole':continue
        shapes,pins=sym_for(ref);geometries[ref]=pins
        lib += [f'# {ref}',f'DEF EP_{ref} {ref.rstrip("0123456789")} 0 30 Y Y 1 F N',f'F0 "{ref}" 0 1700 60 H V C CNN',f'F1 "{p["value"]}" 0 -1700 50 H V C CNN','DRAW']+shapes
        for pin,(x,y,d) in pins.items():
            name=p['pins'][pin];length=100 if p['kind'] in ('res','cap','mos','test') else 200
            lib.append(f'X {name} {pin} {x} {y} {length} {d} 40 40 1 1 P')
        lib+=['ENDDRAW','ENDDEF']
    lib+=['#End Library'];(BASE/'esquema-cache.lib').write_text('\n'.join(lib)+'\n')
    sheet1=['U1','J1','J2','J3','J4','Q9','Q10']+[f'R{i}' for i in range(33,41)]+['C1','C2','C5']+[f'TP{i}' for i in range(1,9)]
    sheets=[sheet1, ['U2','C3']+sum(([f'Q{i+1}',f'R{i+1}',f'R{i+9}',f'R{i+17}',f'R{i+25}'] for i in range(4)),[]), ['U3','C4']+sum(([f'Q{i+1}',f'R{i+1}',f'R{i+9}',f'R{i+17}',f'R{i+25}'] for i in range(4,8)),[])]
    def header(n,title):
        return ['EESchema Schematic File Version 4','LIBS:esquema-cache','EELAYER 29 0','EELAYER END','$Descr A2 23386 16535',f'Sheet {n} 3',f'Title "{title}"','Date "2026-10-24"','Rev "0.1 PROTOTIPO"','Comp "Leitor gravador ST TS27C256Q - Mega ponto a ponto"','Comment1 "Fontes manuais; SEM protecao contra inversao; nao ensaiado fisicamente"','Comment2 "Cada rotulo global conecta todas as ocorrencias da mesma rede"','$EndDescr']
    for n,refs in enumerate(sheets,1):
        data=header(n,f'EPROM 27C256 - folha {n}')
        for i,ref in enumerate(refs):
            if n==1:
                # A primeira linha reserva altura para os conectores e a EPROM.
                if i<5:x=2000+i*4300;y=3500
                else:j=i-5;x=1800+(j%6)*3600;y=7400+(j//6)*2000
            else:
                if i==0:x,y=1800,4000
                else:j=i-1;x=5100+(j%5)*3500;y=2300+(j//5)*2400
            value=P[ref]['value'];uid=f'{n:02X}{i+1:06X}'
            data+=['$Comp',f'L EP_{ref} {ref}',f'U 1 1 {uid}',f'P {x} {y}',f'F 0 "{ref}" H {x+300} {y+350} 50 0000 L CNN',f'F 1 "{value}" H {x+300} {y+250} 45 0000 L CNN',f'F 2 "{FP.get(ref, "")}" H {x} {y} 50 0001 C CNN',f'\t1 {x} {y}','\t1 0 0 -1','$EndComp']
            for pin,(px,py,d) in geometries[ref].items():
                xx,yy=x+px,y-py; net=P[ref]['pins'][pin]
                if net=='NC':data += [f'NoConn ~ {xx} {yy}'];continue
                # Extend in direction away from symbol, then attach global label.
                dx,dy={'R':(-250,0),'L':(250,0),'D':(0,-200),'U':(0,200)}[d]
                tx,ty=xx+dx,yy+dy
                data+=['Wire Wire Line',f'\t{xx} {yy} {tx} {ty}',f'Text GLabel {tx} {ty} 0 40 BiDi ~ 0',net]
        data+=['Text Notes 1000 15500 0 70 ~ 0','REVISAO 0.1 / PROTOTIPO. Fontes externas manuais. Sem protecao contra polaridade invertida.','$EndSCHEMATC']
        (BASE/f'esquema_{n:02d}.sch').write_text('\n'.join(data)+'\n')
    data=header(1,'Leitor e gravador 27C256 - indice')
    for i in range(1,4):
        y=2500+(i-1)*2500
        data+=['$Sheet',f'S 2000 {y} 7000 1500',f'U 0000000{i}',f'F0 "Folha {i}" 70',f'F1 "esquema_{i:02d}.sch" 70','$EndSheet']
    data+=['$EndSCHEMATC'];(BASE/'esquema.sch').write_text('\n'.join(data)+'\n')

def modern():
    """Arquivo moderno autossuficiente para KiCad 7+, sem bibliotecas externas."""
    def uid(name):return str(uuid.uuid5(uuid.NAMESPACE_URL,'eprom-27c256-rev01:'+name))
    def q(s):return json.dumps(str(s),ensure_ascii=False)
    def mm(x):return f'{float(x)*0.0254:.5f}'.rstrip('0').rstrip('.') or '0'
    def n(x):return f'{float(x):.5f}'.rstrip('0').rstrip('.') or '0'
    stroke='(stroke (width 0.254) (type default))'
    font='(effects (font (size 1.016 1.016)))'
    root=uid('schematic')
    out=['(kicad_sch (version 20230121) (generator eeschema)',f'(uuid {root})','(paper "A0")', '(title_block (title "Leitor e gravador ST TS27C256Q") (date "2026-10-24") (rev "0.1 PROTOTIPO") (comment 1 "Fontes manuais. SEM protecao contra inversao. Nao ensaiado fisicamente."))','(lib_symbols']
    parts=[(ref,p) for ref,p in P.items() if p['pins']]
    for ref,p in parts:
        shapes,pins=sym_for(ref)
        out += [f'(symbol "Local:EP_{ref}" (pin_names (offset 0.762)) (in_bom yes) (on_board yes)',f'(property "Reference" {q(ref.rstrip("0123456789"))} (at 0 44 0) {font})',f'(property "Value" {q(p["value"])} (at 0 -44 0) {font})',f'(symbol "EP_{ref}_0_1"']
        for s in shapes:
            t=s.split()
            if t[0]=='S':
                out.append(f'(rectangle (start {mm(t[1])} {mm(t[2])}) (end {mm(t[3])} {mm(t[4])}) {stroke} (fill (type none)))')
            elif t[0]=='C':
                out.append(f'(circle (center {mm(t[1])} {mm(t[2])}) (radius {mm(t[3])}) {stroke} (fill (type none)))')
            elif t[0]=='P':
                count=int(t[1]);pts=t[5:5+count*2]
                xy=' '.join(f'(xy {mm(pts[i])} {mm(pts[i+1])})' for i in range(0,len(pts),2))
                out.append(f'(polyline (pts {xy}) {stroke} (fill (type {"outline" if t[-1]=="F" else "none"})))')
            elif t[0]=='T':
                out.append(f'(text {q(t[8])} (at {mm(t[2])} {mm(t[3])} 0) {font})')
        out += [')',f'(symbol "EP_{ref}_1_1"']
        for pin,(x,y,d) in pins.items():
            length=100 if p['kind'] in ('res','cap','mos','test') else 200
            angle={'R':0,'L':180,'U':90,'D':270}[d]
            out.append(f'(pin passive line (at {mm(x)} {mm(y)} {angle}) (length {mm(length)}) (name {q(p["pins"][pin])} {font}) (number {q(pin)} {font}))')
        out+=['))']
    out+=[')']
    for i,(ref,p) in enumerate(parts):
        x=60+(i%10)*110;y=65+(i//10)*105
        instance=uid(ref);pins=sym_for(ref)[1]
        out += [f'(symbol (lib_id "Local:EP_{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {instance})',f'(property "Reference" {q(ref)} (at {x+12} {y-40} 0) {font})',f'(property "Value" {q(p["value"])} (at {x+12} {y-35} 0) {font})',f'(property "Footprint" {q(FP.get(ref,""))} (at {x} {y} 0) (effects (font (size 1.016 1.016)) hide))']
        for pin in pins:out.append(f'(pin {q(pin)} (uuid {uid(ref+"pin"+pin)}))')
        out += [f'(instances (project "esquema" (path "/{root}" (reference {q(ref)}) (unit 1))))',')']
        for pin,(px,py,d) in pins.items():
            xx=x+px*.0254;yy=y-py*.0254;net=p['pins'][pin]
            if net=='NC':out += [f'(no_connect (at {n(xx)} {n(yy)}) (uuid {uid(ref+pin+"NC")}))'];continue
            dx,dy={'R':(-6.35,0),'L':(6.35,0),'D':(0,-5.08),'U':(0,5.08)}[d]
            tx,ty=xx+dx,yy+dy
            out += [f'(wire (pts (xy {n(xx)} {n(yy)}) (xy {n(tx)} {n(ty)})) (stroke (width 0) (type default)) (uuid {uid(ref+pin+"wire")}))',f'(global_label {q(net)} (shape bidirectional) (at {n(tx)} {n(ty)} 0) {font} (uuid {uid(ref+pin+"net")}))']
    out += ['(text "REVISAO 0.1 / PROTOTIPO - SEM PROTECAO CONTRA INVERSAO - FONTES EXTERNAS MANUAIS" (at 20 820 0) (effects (font (size 2 2)) (justify left)) (uuid '+uid('note')+'))', '(sheet_instances (path "/" (page "1")))',')']
    (BASE/'fontes/esquema_intermediario.kicad_sch').write_text('\n'.join(out)+'\n')

if __name__=='__main__':
    svg_all();legacy();modern()
    expected={(ref,pin,net) for ref,p in P.items() for pin,net in p['pins'].items()}
    missing=expected-coverage
    assert not missing,missing
    print(f'SVG XML valido: 3 folhas; componentes eletricos: {sum(p["kind"]!="hole" for p in P.values())}; pinos/redes cobertos: {len(coverage)}/{len(expected)}; faltantes: {len(missing)}')
    print('KiCad legado: esquema.sch + esquema_01/02/03.sch + esquema-cache.lib')
