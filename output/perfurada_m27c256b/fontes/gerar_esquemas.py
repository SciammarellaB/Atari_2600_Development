#!/usr/bin/env python3
"""Pranchas de ligação física por redes, exclusivamente do contrato elétrico."""
import json, math, re, textwrap, csv, sys
from pathlib import Path
from html import escape
from collections import defaultdict
from xml.etree import ElementTree as ET

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'esquemas';OUT.mkdir(exist_ok=True)
C=json.loads((BASE/'contrato_eletrico.json').read_text());P=C['parts']
COVER={};REFS={};W=1680;H=1188

def natural(s):return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)',s)]
def wrap(s,n):return textwrap.wrap(s,n,break_long_words=False,break_on_hyphens=False) or ['']

class Page:
    def __init__(self,n,title,notes):
        self.n=n;self.a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 {W} {H}">', '<rect width="1680" height="1188" fill="white"/>', '<style>text{font-family:DejaVu Sans,sans-serif;fill:#1a2d3d}.title{font-size:25px;font-weight:700}.subtitle{font-size:15px}.card{fill:#f8fafc;stroke:#becbd5;stroke-width:1}.wire{fill:none;stroke:#227054;stroke-width:1.8}.sym{fill:white;stroke:#1a2d3d;stroke-width:1.8}.small{font-size:12px}.value{font-size:12px;fill:#394e60}.ref{font-size:16px;font-weight:bold}.pin{font-size:12px;font-family:DejaVu Sans Mono,monospace}.hint{font-size:11px;fill:#61707c}.flow{fill:#edf5ef;stroke:#739880;stroke-width:1}</style>']
        self.text(28,37,f'M27C256B • LIGAÇÕES PARA PLACA PERFURADA • {title}','title')
        self.text(28,65,f'Revisão {C["revision"]} • protótipo sem ensaio físico • prancha {n}/6 • todos os pinos e furos extraídos do contrato','subtitle')
        self.text(28,88,notes,'small')
        self.line(25,100,1655,100,'sym')
        self.line(25,1137,1655,1137,'sym')
        self.text(28,1158,'MESMO NOME DE REDE = ligação elétrica entre todos os terminais, inclusive entre placas. NC = deixar sem ligação.','small')
        self.text(28,1178,'(c,l) = coluna e linha do furo, vista superior. +5M = USB do Mega; +5B = buck externo: NÃO interligar esses positivos.','small')
    def text(self,x,y,t,cl='small',anchor='start'):
        self.a.append(f'<text x="{x:.2f}" y="{y:.2f}" class="{cl}" text-anchor="{anchor}">{escape(str(t))}</text>')
    def line(self,x1,y1,x2,y2,cl='wire'):
        self.a.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="{cl}"/>')
    def rect(self,x,y,w,h,cl='card'):
        self.a.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" class="{cl}"/>')
    def circle(self,x,y,r):self.a.append(f'<circle cx="{x}" cy="{y}" r="{r}" class="sym"/>')
    def poly(self,pts,fill='white'):
        self.a.append(f'<polygon points="'+ ' '.join(f'{x},{y}' for x,y in pts)+f'" fill="{fill}" stroke="#1a2d3d" stroke-width="1.8"/>')
    def symbol(self,ref,x,y):
        """Símbolo auxiliar. A pinagem completa ao lado é normativa para montagem."""
        p=P[ref];k=p['kind']
        if k=='res':
            self.line(x-26,y,x-15,y);self.rect(x-15,y-6,30,12,'sym');self.line(x+15,y,x+26,y)
        elif k in ('cap','bulk','elect'):
            self.line(x,y-20,x,y-5);self.line(x-12,y-5,x+12,y-5,'sym');self.line(x-12,y+5,x+12,y+5,'sym');self.line(x,y+5,x,y+20)
            if k!='cap':self.text(x-23,y-9,'+','ref')
        elif k=='diode':
            self.line(x,y-25,x,y-12);self.poly([(x-12,y-12),(x+12,y-12),(x,y+10)]);self.line(x-13,y+11,x+13,y+11,'sym');self.line(x,y+11,x,y+25)
            self.text(x+17,y+15,'K','hint');self.text(x+17,y-12,'A','hint')
        elif k in ('mos','to220','npn'):
            if ref=='UR1':
                self.poly([(x-12,y+12),(x+12,y+12),(x,y-10)]);self.line(x-14,y-12,x+14,y-12,'sym');self.text(x+17,y+17,'A3','hint');self.text(x+17,y-15,'K2','hint')
            elif k=='npn':
                self.circle(x,y,21);self.line(x-8,y-12,x-8,y+12,'sym');self.line(x-27,y,x-8,y);self.line(x-8,y-6,x+12,y-18,'sym');self.line(x+12,y-18,x+12,y-29);self.line(x-8,y+6,x+12,y+18,'sym');self.line(x+12,y+18,x+12,y+29);self.poly([(x+12,y+18),(x+4,y+16),(x+8,y+11)],'#1a2d3d')
                self.text(x-30,y-5,'B2','hint');self.text(x+15,y-22,'C1','hint');self.text(x+15,y+32,'E3','hint')
            elif ref.startswith('UP'):
                self.rect(x-26,y-22,52,44,'sym');self.text(x,y+3,'317','small','middle');self.line(x-40,y-10,x-26,y-10);self.line(x+26,y-10,x+40,y-10);self.line(x,y+22,x,y+34)
            else:
                self.circle(x,y,21);self.line(x-10,y-12,x-10,y+12,'sym');self.line(x-29,y,x-10,y);self.line(x-3,y-12,x-3,y+12,'sym');self.line(x-3,y-10,x+12,y-10,'sym');self.line(x+12,y-10,x+12,y-29);self.line(x-3,y+10,x+12,y+10,'sym');self.line(x+12,y+10,x+12,y+29)
        elif k=='trim':
            self.line(x,y-25,x,y-14);self.rect(x-7,y-14,14,28,'sym');self.line(x,y+14,x,y+25);self.line(x+24,y,x+7,y);self.poly([(x+7,y),(x+14,y-4),(x+14,y+4)],'#1a2d3d')
        elif k=='test':self.circle(x,y,6);self.line(x,y+6,x,y+20)
        elif k=='relay':
            self.rect(x-25,y-30,50,20,'sym');self.text(x,y-16,'bobina','hint','middle');self.line(x-25,y-20,x-35,y-20);self.line(x+25,y-20,x+35,y-20)
            self.line(x-25,y+24,x-5,y+24);self.circle(x-5,y+24,2);self.line(x-5,y+24,x+18,y+9,'sym');self.circle(x+25,y+7,2);self.circle(x+25,y+28,2)
            self.text(x-32,y+41,'COM4','hint');self.text(x+20,y-1,'NC6','hint');self.text(x+20,y+43,'NO8','hint')
        else:
            hh=54 if k.startswith('dip') else 28
            self.rect(x-22,y-hh/2,44,hh,'sym');self.text(x,y+4,'CI' if k.startswith('dip') else 'J','small','middle')
    def card(self,ref,x,y,w):
        p=P[ref];pins=list(p['pins'].items());np=len(pins)
        split=np>=9;cols=2 if split else 1;rows=math.ceil(np/cols)
        value_lines=wrap(p['value'],48 if split else 43)
        head=25+14*len(value_lines)
        h=head+rows*18+12
        self.rect(x,y,w,h)
        REFS[ref]=self.n
        self.text(x+10,y+20,f'{ref}  •  placa {p["board"]}','ref')
        for i,t in enumerate(value_lines):self.text(x+10,y+36+i*14,t,'value')
        content=y+head+9
        if not split:self.symbol(ref,x+42,content+(rows-1)*9)
        for i,(pin,net) in enumerate(pins):
            col=i//rows if split else 0;row=i%rows
            xx=x+10+col*(w/2) if split else x+90
            yy=content+row*18
            hole=p['holes'][pin];label='NC' if net is None else net
            self.a.append(f'<g data-ref="{ref}" data-pin="{pin}" data-net="{escape(label)}" data-hole="{hole[0]},{hole[1]}">')
            self.text(xx,yy,f'{pin:>2}  {label}','pin')
            self.text(x+(w/2 if split and col==0 else w)-8,yy,f'({hole[0]},{hole[1]})','hint','end')
            self.a.append('</g>')
            key=(ref,pin);assert key not in COVER,key;COVER[key]=net
        return h
    def flow(self,items,y=116):
        x=28;gap=22;w=(1624-gap*(len(items)-1))/len(items)
        for i,(title,detail) in enumerate(items):
            self.rect(x,y,w,60,'flow');self.text(x+10,y+22,title,'ref')
            for j,t in enumerate(wrap(detail,int(w/7.4))):self.text(x+10,y+40+j*13,t,'small')
            if i<len(items)-1:self.text(x+w+gap/2,y+34,'→','ref','middle')
            x+=w+gap
    def finish(self):
        self.a.append('</svg>');path=OUT/f'ligacoes_{self.n:02d}.svg';path.write_text('\n'.join(self.a));ET.parse(path)

def partition():
    data={'U2','U3','C3','C4','R39','R40','C5'}|{f'{pre}{i}' for pre,a,b in [('Q',1,8),('R',1,32)] for i in range(a,b+1)}
    core={r for r,x in P.items() if x['board']=='A'}-data-{f'TPA{i}' for i in range(1,9)}
    power={'JB2','QP1','RP1','ZP1','DP1','JM1','JM2','UP1','UP2'}|{f'CP{i}' for i in range(1,13)}|{f'RP{i}' for i in range(2,10)}|{f'RV{i}' for i in range(1,6)}|{'DP2','DP3'}
    relays={r for r in P if r.startswith(('K','DF','ZF'))}|{f'QP{i}' for i in range(2,6)}|{f'RP{i}' for i in range(11,19)}|{'JB1','JB3','JS1'}
    adc={r for r in P if r.startswith(('RS','QS','CS','TPB','TPA'))}|{'JB4','UR1','RP19','CP13'}
    uv=set(P)-data-core-power-relays-adc
    return [core,data,power,relays,uv,adc]

def height(ref):
    p=P[ref];n=len(p['pins']);split=n>=9
    return 25+14*len(wrap(p['value'],48 if split else 43))+math.ceil(n/(2 if split else 1))*18+12

def main():
    titles=['Núcleo e interface A','Dados: escrita e leitura','Entrada e fontes reguladas','Relés e comandos B','Supervisão e intertravamento','ADC, referência e pontos de teste']
    notes=[
        'U4/U5: SN74AHCT541, não HCT541. CE/OE passam por MOSFETs e clamps UV. RN1/RN2: comum no pino 1.',
        '2N7000 Microchip: S1/G2/D3. LM339: entradas + recebem Qn; entradas − recebem VREF_DATA. Coletor aberto com pull-up +5M.',
        'LM317T ST: ADJ1/OUT2/IN3. Trimpots: cursor 2 unido ao terminal 3. Diodos: pino 1=A e pino 2=K.',
        'G5V-2-H1: bobina 1/16; contato COM4, NC6, NO8. Segundo polo 13/11/9 fica NC. Não confundir vistas superior/inferior.',
        'UC2 = SN74HC14, não HCT14. UC1 = LM393. BC337 onsemi: C1/B2/E3. CP16 = 10 nF no atraso de BUS_OE.',
        'LM4040: NC1/K2/A3. AREF externa 2,5 V; nunca unir +5M ao +5B. Testpoints A e B mantêm os nomes exatos das redes.'
    ]
    flows=[
        [('JA1 • Mega','MA0…MA14'),('U4 / U5 • AHCT541','isolamento por BUS_OE'),('U1 • M27C256B','A0…A14, Q0…Q7, CE_N/OE_N')],
        [('WRn → Rgate → 2N7000','HIGH no gate puxa Qn a zero'),('Qn → LM339 (+)','VREF_DATA no terminal −'),('RDn → Mega','pull-up alimentado por +5M')],
        [('JB2 / QP1','12 V, proteção contra inversão'),('JM1 / JM2','buck +5B; boost +18B'),('UP1 / UP2','VCC_EP e +12P75'),('K4 → VPP','seleção VCC_EP / +12P75')],
        [('Mega → resistor de base','comando K1…K4'),('BC337 → bobina','diodo + zener limitam retorno'),('Contato do relé','K1…K3: segmentos; K4: VPP')],
        [('UC1 • LM393','VIN_PROT e +5B supervisionados'),('UC2 • HC14','UV_FAIL; atraso BUS_SLOW'),('QP7/QP8 e QP9/QP10','bloqueio de BUS e gates CE/OE')],
        [('Tensão → divisor RSxA/B','SENSE_x com capacitor CSx'),('QSx • 2N7000','gate +5M; saída ADC com RSxC'),('Mega ADC / AREF','A0…A3; referência 2,5 V')]
    ]
    pages=partition()
    assert len(set().union(*pages))==len(P)
    for num,refs in enumerate(pages,1):
        s=Page(num,titles[num-1],notes[num-1]);s.flow(flows[num-1])
        # Bin packing por altura: preserva quatro colunas sem sobreposições.
        ncols=5 if num==2 else 4
        step=1640/ncols;cardw=step-16
        columns=[190]*ncols;ordered=sorted(refs,key=lambda r:(-height(r),natural(r)))
        for ref in ordered:
            col=min(range(ncols),key=lambda x:columns[x]);x=28+col*step;y=columns[col]
            h=s.card(ref,x,y,cardw);columns[col]+=h+3
        if max(columns)>1130:raise RuntimeError(f'Prancha {num} ultrapassa altura: {columns}')
        s.finish();print(f'Prancha {num}: {len(refs)} componentes, limite inferior {max(columns):.0f}px')
    expected={(ref,pin):net for ref,p in P.items() for pin,net in p['pins'].items()}
    assert COVER==expected
    with (OUT/'indice_ligacoes.csv').open('w',newline='') as f:
        wr=csv.writer(f);wr.writerow(['Referencia','Pino','Rede','Placa','Coluna','Linha','Prancha'])
        for ref,p in P.items():
            for pin,net in p['pins'].items():wr.writerow([ref,pin,net or 'NC',p['board'],*p['holes'][pin],REFS[ref]])
    (OUT/'validacao.json').write_text(json.dumps({'componentes':len(REFS),'pinos':len(COVER),'pranchas':6,'cobertura_exata_contrato':COVER==expected},indent=2)+'\n')
    print(f'PASS: {len(REFS)} componentes; {len(COVER)} pinos; cobertura exata JSON; 6 SVG XML válidos.')

def render_png():
    """QA raster usando librsvg/cairo já presentes no SO, sem instalação."""
    import ctypes as ct
    cairo=ct.CDLL('libcairo.so.2');rsvg=ct.CDLL('librsvg-2.so.2');gobj=ct.CDLL('libgobject-2.0.so.0')
    cairo.cairo_image_surface_create.argtypes=[ct.c_int,ct.c_int,ct.c_int];cairo.cairo_image_surface_create.restype=ct.c_void_p
    cairo.cairo_create.argtypes=[ct.c_void_p];cairo.cairo_create.restype=ct.c_void_p
    cairo.cairo_surface_write_to_png.argtypes=[ct.c_void_p,ct.c_char_p]
    cairo.cairo_destroy.argtypes=[ct.c_void_p];cairo.cairo_surface_destroy.argtypes=[ct.c_void_p]
    rsvg.rsvg_handle_new_from_data.argtypes=[ct.c_char_p,ct.c_size_t,ct.c_void_p];rsvg.rsvg_handle_new_from_data.restype=ct.c_void_p
    class Rect(ct.Structure):_fields_=[('x',ct.c_double),('y',ct.c_double),('width',ct.c_double),('height',ct.c_double)]
    rsvg.rsvg_handle_render_document.argtypes=[ct.c_void_p,ct.c_void_p,ct.POINTER(Rect),ct.c_void_p];rsvg.rsvg_handle_render_document.restype=ct.c_bool
    gobj.g_object_unref.argtypes=[ct.c_void_p]
    for svg in OUT.glob('ligacoes_*.svg'):
        raw=svg.read_bytes();handle=rsvg.rsvg_handle_new_from_data(raw,len(raw),None);assert handle
        surface=cairo.cairo_image_surface_create(0,2100,1485);context=cairo.cairo_create(surface)
        assert rsvg.rsvg_handle_render_document(handle,context,ct.byref(Rect(0,0,2100,1485)),None)
        assert cairo.cairo_surface_write_to_png(surface,str(svg.with_suffix('.png')).encode())==0
        cairo.cairo_destroy(context);cairo.cairo_surface_destroy(surface);gobj.g_object_unref(handle)
    print('6 PNG de QA renderizados com librsvg/cairo.')

if __name__=='__main__':
    main()
    if '--png' in sys.argv:render_png()
