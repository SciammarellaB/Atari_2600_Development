"""Pranchas de apresentacao a partir dos SVGs exportados do KiCad.
O plano de GND e omitido somente na vista explicativa de trilhas.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
import json,csv,io
import cairosvg
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A3,landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader,PdfWriter,Transformation
OUT=Path(__file__).resolve().parents[1]
TMP=OUT.parents[1]/'tmp/pcb_eprom'
TMP.mkdir(parents=True,exist_ok=True)
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
fonts=Path('/usr/share/fonts/truetype/dejavu')
pdfmetrics.registerFont(TTFont('DS',str(fonts/'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DB',str(fonts/'DejaVuSans-Bold.ttf')))

def decorate(file,name,legend):
    root=ET.fromstring(file.read_text())
    for e in root.iter():
        for att in ['style','fill','stroke']:
            if att in e.attrib:
                e.attrib[att]=e.attrib[att].replace('#ECECEC','#243b4b').replace('#F2EDA1','#243b4b')
                if name=='pcb_montagem':e.attrib[att]=e.attrib[att].replace('#C83434','#b68727')
    wrap=ET.Element('{'+NS+'}svg',{'width':'220mm','height':'164mm','viewBox':'0 0 220 164'})
    ET.SubElement(wrap,'{'+NS+'}rect',{'width':'220','height':'164','fill':'white'})
    t=ET.SubElement(wrap,'{'+NS+'}text',{'x':'10','y':'8','font-family':'DejaVu Sans','font-size':'3.1','font-weight':'bold','fill':'#142b43'})
    t.text='EPROM 27C256 + Mega | Rev. 0.1 | 200 x 140 mm | PROTOTIPO'
    g=ET.SubElement(wrap,'{'+NS+'}g',{'transform':'translate(10 13)'})
    for e in list(root):g.append(e)
    t=ET.SubElement(wrap,'{'+NS+'}text',{'x':'10','y':'159','font-family':'DejaVu Sans','font-size':'2','fill':'#365268'})
    t.text=legend
    dst=OUT/(name+'.svg');dst.write_bytes(ET.tostring(wrap,encoding='utf-8',xml_declaration=True))
    cairosvg.svg2png(url=str(dst),write_to=str(OUT/(name+'.png')),output_width=2000,background_color='white')
    return dst

trilhas=decorate(OUT/'pcb_trilhas.svg','pcb_visao_superior',
    'Vista por cima: F.Cu vermelho; B.Cu azul. Plano GND omitido nesta vista, presente no arquivo KiCad.')
montagem=decorate(OUT/'pcb_montagem_nativa.svg','pcb_montagem',
    'Mapa de montagem: componentes THT; pino 1 identificado por pad quadrado. Soquete DIP-28 de 600 mil.')

W,H=landscape(A3)
base=TMP/'pranchas_base.pdf'
c=canvas.Canvas(str(base),pagesize=(W,H))
c.setTitle('PCB EPROM 27C256 + Mega - esquema e ligacoes - Rev. 0.1')
c.setAuthor('Projeto de referencia de bancada')
def header(title,page):
    c.setFillColorRGB(.03,.46,.48);c.rect(0,H-5*mm,W,5*mm,fill=1,stroke=0)
    c.setFillColorRGB(.08,.17,.26);c.setFont('DB',16);c.drawString(15*mm,H-18*mm,title)
    c.setFont('DS',8);c.setFillColorRGB(.25,.35,.43)
    c.drawString(15*mm,9*mm,'ST TS27C256Q antiga | Fontes manuais | Rev. 0.1 - 24/10/2026 | SEM ensaio fisico')
    c.drawRightString(W-15*mm,9*mm,f'{page}/7')
def text(x,y,s,size=9,bold=False):
    c.setFont('DB' if bold else 'DS',size);c.setFillColorRGB(.08,.17,.26);c.drawString(x*mm,y*mm,s)
def lines(x,y,items,size=9,step=5):
    for t in items:text(x,y,t,size);y-=step
def grid(x,y,width,rows,widths=None):
    widths=widths or [width/len(rows[0])]*len(rows[0])
    for idx,row in enumerate(rows):
        c.setFillColorRGB(*((.08,.17,.26) if idx==0 else ((.93,.96,.97) if idx%2 else (1,1,1))))
        c.rect(x*mm,(y-6)*mm,width*mm,6*mm,fill=1,stroke=0)
        xx=x
        for word,ww in zip(row,widths):
            c.setFillColorRGB(*( (1,1,1) if idx==0 else (.08,.17,.26) ))
            c.setFont('DB' if idx==0 else 'DS',8)
            c.drawString((xx+2)*mm,(y-4)*mm,str(word));xx+=ww
        y-=6
    return y

header('1. PCB roteada - vista superior e trilhas',1)
text(15,270,'Duas camadas, FR-4 de 1,6 mm. Adaptador ligado ao Mega por cabos; nao e um shield.',9)
text(15,20,'DRC KiCad: 0 violacoes / 0 pads desconectados. Protótipo para revisao e ensaio, nao liberado para fabricacao.',9)
c.showPage()
header('2. Posicao dos componentes e orientacao',2)
text(15,270,'U1: soquete DIP-28 W15,24 mm. O encaixe de um ZIF especifico ainda nao foi verificado.',9)
text(15,20,'2N7000: footprint Microchip TO-92 com 1=S, 2=G, 3=D. Confira o fabricante comprado antes de montar.',9)
c.showPage()
for n in range(3):
    # A prancha SVG ja contem titulo, notas e rodape; preservada integralmente.
    c.showPage()
header('6. Conectores - cabos ponto a ponto para o Mega',6)
AP=list(range(22,37));RP=[47,38,37,40,41,42,43,44];WP=list(range(2,10))
grid(15,260,118,[['J1 pino','Rede','Mega']]+[[i+1,f'A{i}',f'D{AP[i]}'] for i in range(15)]+[[16,'GND','GND']],[25,40,53])
grid(145,260,118,[['J2 pino','Rede','Mega']]+[[i+1,f'RD{i}',f'D{RP[i]}'] for i in range(8)]+[[9,'+5M','5V'],[10,'GND','GND']],[25,40,53])
grid(275,260,130,[['J3 pino','Rede','Mega']]+[[i+1,f'WR{i}',f'D{WP[i]}'] for i in range(8)]+[[9,'CE_DRV','D45'],[10,'OE_DRV','D46'],[11,'GND','GND'],[12,'NC','Nao conectar']],[25,45,60])
grid(15,142,180,[['J4 pino','Fonte externa','Observacao'],[1,'VCC_EP: 5 V / 6 V','Leitura / programacao'],[2,'GND','Terra comum'],[3,'VPP: 5 V / 12,5 V','Leitura / programacao'],[4,'GND','Terra comum'],[5,'V_AUX: 9 a 15 V','Fixa para os LM339'],[6,'GND','Terra comum']],[25,75,80])
lines(210,139,['Nao conectar VCC_EP ou VPP ao 5V do Mega.',
 'O 5V do Mega entra somente como +5M pelo J2.9.',
 'J1/J2/J3 nao correspondem fisicamente a um header unico do Mega.',
 'Pino 1 dos conectores: pad quadrado. Confira numeracao no KiCad.',
 '',
 'Firmware obrigatorio nesta placa: PROGRAMMER_HARDWARE = 1.',
 'Gate HIGH ativa o MOSFET e forca o respectivo no para LOW.',
 'Fontes externas nao sao medidas nem comutadas pelo firmware.'],9,6)
lines(15,70,['Partida: fontes em 5 V / 5 V e V_AUX presente antes de acionar os enderecos do Mega.',
 'Programacao: /CE e /OE inativos; elevar VCC_EP para 6 V antes de elevar VPP para 12,5 V.',
 'Retorno: desarmar; reduzir VPP para 5 V antes de reduzir VCC_EP para 5 V.',
 'Desligamento: enderecos em alta impedancia antes de retirar VCC_EP.',
 'Sem chip: executar autoteste 00/FF/AA/55 antes de qualquer ensaio de programacao.'],9,6)
c.showPage()
header('7. Lista por referencia e verificacoes',7)
rows=[['Referencias','Quantidade','Valor / componente'],
 ['U1',1,'EPROM e soquete DIP-28 de 600 mil'],['U2, U3',2,'LM339N DIP-14'],
 ['Q1 a Q10',10,'2N7000 TO-92, pinos S-G-D'],
 ['R1..R8, R33, R36',10,'220 ohms'],['R9..R16, R34, R37',10,'100 kohms'],
 ['R17..R24, R35, R38, R40',11,'10 kohms'],['R25..R32',8,'4,7 kohms'],['R39',1,'22 kohms, 1%'],
 ['C1..C5',5,'100 nF ceramico, 25 V ou superior'],['J1 / J2 / J3','1 / 1 / 1','Headers 1x16 / 1x10 / 1x12, passo 2,54 mm'],
 ['J4',1,'Phoenix MKDS-1,5-6-5.08 ou footprint identico'],
 ['TP1..TP8',8,'Pads de teste; pino ou lacinho de fio opcional'],['H1..H4',4,'Furos 3,2 mm para M3; sem metalizacao']]
grid(15,260,245,rows,[95,27,123])
lines(275,254,['Validacoes realizadas',
 'KiCad 7.0.11 abriu esquema e PCB.',
 '227 pinos conectados conferidos contra o contrato.',
 'J3.12 explicitamente sem conexao.',
 '74 footprints, incluindo 8 TP e 4 furos.',
 '649 segmentos, 18 vias e plano GND em B.Cu.',
 'DRC: zero violacoes e zero conexoes pendentes.',
 'Revisao independente de pinagem e polaridades.',
 '',
 'Limites antes de fabricar',
 'Nenhum ensaio fisico de programacao realizado.',
 'Sem protecao contra polaridade invertida.',
 'Sem sensores ou intertravamento de tensoes.',
 'Confirmar marcacao ST TS27C256Q antiga.',
 'Conferir dimensoes dos componentes reais.',
 'Soquete ZIF nao foi dimensionado nesta revisao.',
 'Validar circuito em bancada e largura dos pulsos.'],9,6)
lines(15,147,['Fontes: ST SGS-Thomson Memory Products Databook, junho de 1988, TS27C256Q, pp. impressas 121-129.',
 'TI LM339: www.ti.com/lit/ds/symlink/lm339.pdf',
 'Microchip 2N7000: DS20005695A. Footprints oficiais KiCad 7.0.11; licenca incluida no pacote.',
 'O plano GND foi omitido na prancha 1 apenas para permitir a leitura das trilhas.',
 'Os SVGs dos esquemas usam nomes de rede: rotulos iguais sao eletricamente conectados, inclusive entre folhas.'],8.5,6)
lines(15,99,['Arquivos principais:',
 'eprom27_rev01.kicad_pro + eprom27_rev01.kicad_sch + eprom27_rev01.kicad_pcb',
 'fp-lib-table e pasta footprints/ acompanham o projeto; manter juntos ao extrair o ZIP.',
 'bom.csv, pads_redes.csv, contrato_eletrico.json e drc_rev01.txt permitem auditar o desenho.',
 'Firmware e cliente: pasta codigos/. O firmware dessa pasta ja esta configurado no modo 1.'],9,6)
c.showPage();c.save()

reader=PdfReader(base);writer=PdfWriter()
files=[trilhas,montagem]+[OUT/f'esquema_{n:02d}.svg' for n in [1,2,3]]
for index,svg in enumerate(files):
    data=cairosvg.svg2pdf(url=str(svg))
    page=PdfReader(io.BytesIO(data)).pages[0]
    dest=reader.pages[index]
    if index<2:
        x,y,maxw,maxh=15*mm,31*mm,390*mm,231*mm
        s=min(maxw/float(page.mediabox.width),maxh/float(page.mediabox.height))
        x+=(maxw-float(page.mediabox.width)*s)/2
    else:x=y=0;s=1
    dest.merge_transformed_page(page,Transformation().scale(s).translate(x,y))
for page in reader.pages:writer.add_page(page)
for label,n in [('PCB e trilhas',0),('Montagem',1),('Esquema geral',2),('Dados Q0 a Q3',3),('Dados Q4 a Q7',4),('Ligacao ao Mega',5),('BOM e verificacoes',6)]:writer.add_outline_item(label,n)
writer.add_metadata({'/Title':'PCB EPROM 27C256 + Mega - esquema e ligacoes','/Author':'Projeto de referencia de bancada'})
writer.write(OUT/'pcb_eprom_27c256_esquema.pdf')
print(OUT/'pcb_eprom_27c256_esquema.pdf')
