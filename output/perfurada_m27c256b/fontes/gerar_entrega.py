"""Mapas de montagem, lista ponto a ponto e manual do projeto perfurado.
Requer reportlab, pypdf e cairosvg (apenas para incorporar esquemas SVG).
"""
from pathlib import Path
from collections import defaultdict,Counter
from math import hypot
import csv,json,io,re
from html import escape
from reportlab.graphics.shapes import Drawing,Line,Rect,Circle,String
from reportlab.graphics import renderPDF,renderSVG
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4,A3,landscape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader,PdfWriter
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
TMP=(ROOT/'tmp/perfurada') if OUT.parent.name=='output' else OUT/'_build'
TMP.mkdir(parents=True,exist_ok=True)
C=json.loads((OUT/'contrato_eletrico.json').read_text());P=C['parts']
FONTS=Path('/usr/share/fonts/truetype/dejavu')
for name,file in [('DS','DejaVuSans.ttf'),('DB','DejaVuSans-Bold.ttf'),('DM','DejaVuSansMono.ttf')]:pdfmetrics.registerFont(TTFont(name,str(FONTS/file)))
INK=colors.HexColor('#15314b');TEAL=colors.HexColor('#007d80');PALE=colors.HexColor('#eaf2f4')

def color(net):
    return {'GND':'preto','+5M':'laranja','+5B':'vermelho','VIN_PROT':'violeta','VIN_HOLD':'violeta',
        '+18B':'marrom','+12P75':'rosa','VCC_EP':'amarelo','VPP':'rosa'}.get(net,'verde' if net.startswith(('A','MA')) and net[1:].replace('A','').isdigit() else 'azul')
def endpoint(ref,pin):
    o=P[ref];x,y=o['holes'][pin]
    return f'{ref}.{pin} [C{x:02d},L{y:02d}]'

# Uma arvore por rede, com extremos fisicos completos. GND usa barramento
# dedicado no ultimo alinhamento, em vez de 60 fios no mesmo furo.
net_nodes=defaultdict(list)
for ref,o in P.items():
    for pin,net in o['pins'].items():
        if net:net_nodes[(o['board'],net)].append((ref,pin,*o['holes'][pin]))
wires=[]
LOCAL_GND={'C1.2':'U1.14','C2.2':'U1.14','C3.2':'U2.12','C4.2':'U3.12',
 'C5.2':'R40.2','C6.2':'U4.10','C7.2':'U5.10','CP5.2':'RV4.3','CP6.2':'RV4.3',
 'CP7.2':'RV4.3','CP9.2':'CP8.2','CP11.2':'RV5.3','CP13.2':'UR1.3',
 'CP14.2':'UC1.4','CP15.2':'UC2.7',**{f'CS{i}.2':f'RS{i}B.2' for i in range(1,5)}}
for (b,net),nodes in sorted(net_nodes.items(),key=lambda x:(x[0][0],x[0][1]!='GND',x[0][1])):
    if net=='GND':
        free=set(range(1,76));row=C['boards'][b][1]
        for ref,pin,x,y in sorted(nodes,key=lambda t:t[2]):
            local=LOCAL_GND.get(f'{ref}.{pin}')
            if local:
                r,pin2=local.split('.');assert P[r]['pins'][pin2]=='GND'
                wires.append((b,net,endpoint(ref,pin),endpoint(r,pin2)));continue
            col=min(free,key=lambda v:abs(v-x));free.remove(col)
            wires.append((b,net,endpoint(ref,pin),f'BARRA_GND [C{col:02d},L{row:02d}]'))
        continue
    connected=[nodes[0]];left=nodes[1:]
    while left:
        _,i,j=min((hypot(a[2]-v[2],a[3]-v[3]),i,j) for i,a in enumerate(connected) for j,v in enumerate(left))
        a=connected[i];v=left.pop(j);connected.append(v)
        wires.append((b,net,endpoint(a[0],a[1]),endpoint(v[0],v[1])))
with (OUT/'ligacoes_ponto_a_ponto.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['ID','Placa','Rede','De','Para','Cor_sugerida','Fio'])
    for i,(b,net,a,z) in enumerate(wires,1):w.writerow([f'{b}{i:04d}',b,net,a,z,color(net),'AWG22' if net in ['GND','+5B','+5M','VCC_EP','VPP','VIN_HOLD','VIN_PROT','+18B','+12P75'] else 'AWG26'])
    for n,net in P['JA4']['pins'].items():
        if net:w.writerow([f'CABO{n}','A-B',net,f'JA4.{n}',f'JB1.{n}',color(net),'AWG22'])

def mapping(board,bottom=False):
    W,H=landscape(A3);d=Drawing(W,H);cols,rows=C['boards'][board]
    s=(4.0 if board=='A' else 2.90)*mm;ox=22*mm;oy=30*mm
    def pos(x,y):return ox+((cols-x) if bottom else (x-1))*s,oy+(rows-y)*s
    def txt(x,y,t,size=7,font='DS',fill=INK,anchor='start'):d.add(String(x,y,str(t),fontName=font,fontSize=size,fillColor=fill,textAnchor=anchor))
    d.add(Rect(0,H-5*mm,W,5*mm,fillColor=TEAL,strokeColor=None))
    txt(15*mm,H-17*mm,f'Placa {board} | '+('lado da solda - ESPELHADO' if bottom else 'lado dos componentes'),18,'DB')
    txt(15*mm,H-25*mm,'REV 0.2 | M27C256B | ilhas isoladas, passo 2,54 mm | prototipo sem ensaio fisico',9)
    d.add(Rect(ox-s,oy-s,(cols+1)*s,(rows+1)*s,fillColor=colors.HexColor('#faf8ef'),strokeColor=colors.HexColor('#bfc7cf')))
    for x in range(1,cols+1):
        for y in range(1,rows+1):
            xx,yy=pos(x,y);d.add(Circle(xx,yy,.43,fillColor=colors.HexColor('#c5c7c7'),strokeColor=None))
        if x==1 or x%5==0:
            xx,yy=pos(x,1);txt(xx,yy+s*.65,x,5,anchor='middle')
            xx,yy=pos(x,rows);txt(xx,yy-s*.8,x,5,anchor='middle')
    for y in range(1,rows+1):
        if y==1 or y%5==0:
            xx,yy=pos(cols if bottom else 1,y);txt(ox-s*.55,yy-1.5,y,5,anchor='end')
    # Barramento continuo de terra, sem conectar nenhuma outra linha de ilhas.
    xa,ya=pos(1,rows);xz,yz=pos(cols,rows)
    d.add(Line(xa,ya,xz,yz,strokeColor=colors.black,strokeWidth=2))
    for ref,o in P.items():
        if o['board']!=board:continue
        points=[pos(x,y) for x,y in o['holes'].values()];xs=[p[0] for p in points];ys=[p[1] for p in points]
        x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);kind=o['kind']
        fill=colors.HexColor('#f0f6fb') if kind.startswith('dip') else colors.HexColor('#e4f1e6')
        if kind=='relay':fill=colors.HexColor('#f5e6c8')
        if bottom:fill=None
        if kind in ['bulk','elect']:
            r=(3.55 if kind=='bulk' else 1.45)*s
            d.add(Circle((x0+x1)/2,(y0+y1)/2,r,fillColor=fill,strokeColor=INK,strokeWidth=.5))
        elif kind in ['res','diode']:
            d.add(Line(x0,y0,x1,y1,strokeColor=INK,strokeWidth=.5))
            d.add(Rect((x0+x1)/2-.65*s,y0-.28*s,1.3*s,.56*s,fillColor=fill,strokeColor=INK,strokeWidth=.5))
        elif kind=='test':pass
        else:d.add(Rect(x0-.45*s,y0-.55*s,max(.9*s,x1-x0+.9*s),y1-y0+1.1*s,fillColor=fill,strokeColor=INK,strokeWidth=.5))
        label_y=y1+.78*s
        # Reserva superior do eletrolitico; demais referencias ficam acima dos terminais.
        if kind in ['bulk','elect']:label_y=y1+(3.9 if kind=='bulk' else 1.8)*s
        txt((x0+x1)/2,label_y,ref,5.3 if board=='A' else 4.9,'DB',anchor='middle')
        for pin,(x,y) in o['holes'].items():
            xx,yy=pos(x,y);is1=pin=='1'
            if is1:d.add(Rect(xx-.8,yy-.8,1.6,1.6,fillColor=TEAL,strokeColor=None))
            else:d.add(Circle(xx,yy,.72,fillColor=INK,strokeColor=None))
            txt(xx+(1.1 if not bottom else -1.1),yy+1.8,pin,3.4,anchor='start' if not bottom else 'end')
    side_x=(345 if board=='A' else 260)*mm
    notes=(['Coordenadas C=coluna, L=linha.','Origem no canto superior esquerdo','visto pelo lado dos componentes.','Na solda, as colunas aparecem','invertidas; o numero do furo e o mesmo.','',
      'Quadrado verde = terminal 1.','Consulte pinos_furos_redes.csv.','Consulte ligacoes_ponto_a_ponto.csv.','Cruzamento de fios isolados','nao significa conexao.','',
      f'GND: fio continuo na linha {rows}.','Nenhuma outra linha e barramento.','Nao usar placa de trilhas continuas.','',
      'Posicao reservada; confirme os','corpos das pecas antes de soldar.','Forme os terminais sem forcar','o encapsulamento.'])
    if board=='B':notes+=['','CP1: diametro maximo 18 mm,','passo formado 7,62 mm; se maior,','fixar externamente com fio isolado.','','Modulos buck/boost e chaves','sao ligados pelos conectores;','fixacao e dimensoes dependem','das pecas efetivamente compradas.']
    for i,t in enumerate(notes):txt(side_x,H-(48+i*6)*mm,t,7.5)
    txt(15*mm,10*mm,'Mapa de montagem por coordenadas. NAO e mascara de cobre nem gabarito para fabricar PCB.',8)
    return d

maps=[]
for b in 'AB':
    for bottom in [False,True]:
        name=f'montagem_{b}_'+('solda' if bottom else 'componentes');d=mapping(b,bottom)
        renderSVG.drawToFile(d,str(OUT/(name+'.svg')))
        svg=OUT/(name+'.svg')
        svg.write_text(svg.read_text().replace('font-family: DB;','font-family: DejaVu Sans; font-weight: bold;').replace('font-family: DS;','font-family: DejaVu Sans;').replace('<title>...</title>',f'<title>{name} - M27C256B revisao0.2</title>').replace('<desc>...</desc>','<desc>Mapa de furos da placa perfurada, nao mascara de cobre.</desc>'))
        renderPDF.drawToFile(d,str(TMP/(name+'.pdf')))
        maps.append(TMP/(name+'.pdf'))

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyBR',fontName='DS',fontSize=9,leading=13,spaceAfter=7,textColor=INK))
styles.add(ParagraphStyle(name='TitleBR',fontName='DB',fontSize=23,leading=28,spaceAfter=14,textColor=INK))
styles.add(ParagraphStyle(name='HeadBR',fontName='DB',fontSize=14,leading=19,spaceAfter=10,textColor=TEAL))
styles.add(ParagraphStyle(name='CodeBR',fontName='DM',fontSize=8,leading=12,spaceAfter=7,textColor=INK))
story=[]
def h(s):story.append(Paragraph(s,styles['HeadBR']))
def formatted(s):
    if '<link ' in s:return s  # Preservar URLs literalmente.
    s=re.sub(r'([a-z])(?=\d+(?:[.,]\d+)?(?:V|mA|uF|nF|us|ms|R|W|k|bytes|tentativas)\b)',r'\1 ',s)
    s=re.sub(r'(VCC|VPP|VIN|USB)(?=\d)',r'\1 ',s)
    s=re.sub(r'(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)(V|A|mA|uF|nF|us|ms|mm|R|bytes|tentativas|tentativa)\b',r'\1 \2',s)
    for a,b in [('ChaveLER','Chave LER'),('chaveLER','chave LER'),('semEPROM','sem EPROM'),('todos os32768','todos os 32768'),('aFF','a FF'),('emGRAVAR','em GRAVAR'),('firmwareV2','firmware V2'),('noWindows','no Windows'),('portaCOM','porta COM'),('em6V','em 6 V'),('em5V','em 5 V'),('a5V','a 5 V'),('dos12V','dos 12 V'),('desligue12V','desligue 12 V'),('de12V','de 12 V'),('VPP elevada permanece','VPP elevada permanece')]:s=s.replace(a,b)
    for a,b in [('pino1','pino 1'),('pino20','pino 20'),('conjunto2/3','conjunto 2/3'),('seguindoVCC','seguindo VCC'),('caminhoVPP','caminho VPP'),('VCCprog','VCC de programacao '),('fonte12','fonte 12'),('Fonte12','Fonte 12'),('toleranciaST','tolerancia ST'),('elevarVCC','elevar VCC'),('antesVPP','antes de VPP'),('retirarVPP','retirar VPP'),('reduzirVCC','reduzir VCC'),('lentamenteVIN','lentamente VIN'),('USB ausente','USB ausente'),('SemEPROM','Sem EPROM'),('padroes00','padroes 00'),('resistor1k','resistor 1k'),('ModuloBUCK','Modulo BUCK'),('degrau0','degrau 0'),('degrau1','degrau 1'),('reguladorVPP','regulador VPP')]:s=s.replace(a,b)
    for a,b in [('MonitorSerial','Monitor Serial'),('oBIN','o BIN'),('porbyte','por byte'),('coloqueLER','coloque LER'),('ultimoUSB','ultimo USB'),('equipamentoUV','equipamento UV'),('apagamentoUV','apagamento UV'),('deVPP','de VPP'),('inibeCE','inibe CE'),('compilacaoMega','compilacao Mega'),('CP1maiorque','CP1 maior que '),('noMega','no Mega')]:s=s.replace(a,b)
    s=re.sub(r'([,;])(?=[A-Za-z])',r'\1 ',s)
    return s
def p(s):story.append(Paragraph(formatted(s),styles['BodyBR']))
def code(s):story.append(Paragraph(escape(s).replace('\n','<br/>'),styles['CodeBR']))
def page(title):
    if story:story.append(PageBreak())
    h(title)
def table(rows,widths=None):
    data=[[Paragraph(escape(formatted(str(t))),styles['BodyBR']) for t in r] for r in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('BOTTOMPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4)]));story.append(t)

story.append(Paragraph('Leitor e gravador<br/>M27C256B em placa perfurada',styles['TitleBR']))
p('<b>Revisao 0.2 - Arduino Mega 2560 - entrada nominal de 12 V.</b><br/>Redesenho para soldagem manual, com ilhas isoladas, fios, componentes THT e dois modulos conversores prontos.')
p('O projeto usa duas placas: A, soquete e interfaces (20 x 15 cm, minimo 75 x 53 furos); B, fontes e controle (20 x 20 cm, minimo 75 x 74 furos). O passo e 2,54 mm. Confira a quantidade real de furos antes da compra.')
p('<b>A automacao possui 200 referencias, incluindo conectores e pontos de teste, e 619 terminais.</b> E uma montagem extensa. O guia divide o trabalho em blocos; nao monte tudo de uma vez.')
p('Mega alimentado pelo USB. Os 12 V alimentam a placa de bancada. Somente os terras sao comuns; <b>+5M (USB) e +5B (buck externo) nunca devem ser unidos</b>.')
p('Perfil exclusivo ST M27C256B-10F1: 32768 bytes; algoritmo PRESTO II, ate 25 pulsos de 100 us, sem sobrepulso. O firmware antigo para TS27C256Q nao serve nesta revisao.')
p('<b>Estado da entrega:</b> esquema e codigo revisados; verificacoes digitais executadas. Circuito fisico, fontes, sensores, rele, fios e pulso ainda nao foram ensaiados. Esta documentacao e um projeto de prototipo; nenhum teste de software equivale a uma bancada aprovada.')
p('O kit contem mapas superiores e espelhados do lado da solda, esquemas por redes nomeadas, lista de componentes, ligacoes numeradas por furo, firmware, cliente e testes. Nao ha Gerbers ou placa de cobre para fabricar.')

page('1. Arquitetura e chave de modo')
table([['Bloco','Funcao'],['12 V -> protecao PMOS','Fusivel 1 A retardado e S0 ficam antes de JB2; QP1 protege a polaridade.'],['Modulo M1 buck','VIN_PROT -> +5B = 5,00 V. Saida de pelo menos 1 A, com regulacao adequada em carga leve.'],['Modulo M2 boost','+5B -> +18B = 18,0 V. Pelo menos 100 mA de saida.'],['UP1 LM317T','VIN_HOLD -> VCC_EP selecionavel: 4,2 / 5 / 6 / 6,25 V.'],['UP2 LM317T','18 V -> 12,75 V. K4 seleciona VCC_EP ou 12,75 V para VPP.'],['Comparadores + buffers','Protegem a interface de leitura e isolam os enderecos quando desabilitados.']],[45*mm,125*mm])
p('S1 e DPDT ON-ON: polo 1 informa LER/GRAVAR ao Mega; polo 2 so alimenta a bobina de K4 na posicao GRAVAR. Nao conecte os polos entre si. LER corta fisicamente a autorizacao de VPP elevada; GRAVAR apenas permite o comando do firmware.')
table([['Estado','K1 K2 K3 K4','VCC / VPP'],['Leitura','1 1 0 0','5 / 5 V'],['Programacao','0 0 0 1','6,25 / 12,75 V'],['Verificacao alta','1 0 0 0','6 / 6 V'],['Verificacao baixa','1 1 1 0','4,2 / 4,2 V'],['Reset, antes da recuperacao','0 0 0 0','6,25 / 6,25 V, controles inibidos']],[58*mm,47*mm,65*mm])
p('1 significa bobina energizada. K1/K2/K3 fecham contatos NO sobre resistencias do ajuste de UP1. Quando soltam, VCC sobe ao maximo calibrado de 6,25 V; isso evita que o reset reduza VCC antes da retirada de VPP. A partida recupera 5 V depois de confirmar VPP acompanhando VCC.')

page('2. Componentes, modulos e materiais')
table([['Item','Especificacao'],['Placas','Ilhas individuais. A: >=75x53 furos; B: >=75x74 furos. Nao usar stripboard sem cortar as trilhas.'],['Modulos prontos','Buck entrada 12 V, saida 5 V/1 A; boost entrada 5 V, saida 18 V/100 mA. LM2596 e uma opcao de buck; o modulo completo precisa cumprir os valores.'],['Rele','4 x Omron G5V-2-H1 DC5, bobina 30 mA. Nao substituir pelo G5V-2 DC5 de 100 mA com os mesmos drivers.'],['Reguladores','2 x ST LM317T TO220, pequenos dissipadores separados ou isolados. A aba metalica e OUT.'],['Buffers','2 x TI SN74AHCT541N DIP20; nao substituir por HCT541. Entradas toleram 5,5 V com VCC=0.'],['Controle UV','LM393N e TI SN74HC14N; HC14 nao e HCT14.'],['Referencia ADC','TI LM4040AIZ-2.5/NOPB, 0,1%, TO92.'],['Ajustes','3296W multivoltas: 10R, 50R, 20R, 100R, 200R (RV1..RV5).'],['Capacitores','Ceramicos 100 nF locais, alem dos eletroliticos. CP1: 4700 uF/25 V, diametro <=18 mm; montar externo se o corpo nao couber.'],['Ferramentas','Multimetro; ferro de ponta fina; lupa; suporte; osciloscopio para validar os pulsos.'],['Fios','AWG26 isolado para sinais; AWG22 para alimentacao e cabo A-B; barramento GND em cobre estanhado de 0,6 mm.']],[47*mm,123*mm])
p('A lista completa por referencia esta em componentes.csv. Os modulos nao possuem footprint universal: fixe-os por espacadores na caixa e leve IN+, IN-, OUT+, OUT- aos conectores JM1/JM2. Nao deduza esses terminais pela posicao na fotografia de outro modulo.')
p('Soquete U1: DIP28 de 600 mil, contatos torneados de boa qualidade. A area do corpo de um ZIF nao foi dimensionada. Soquetes adicionais: 2 DIP14 LM339, 2 DIP20 buffers, DIP8 LM393 e DIP14 HC14.')

page('3. Como ler os mapas e a lista de fios')
p('Toda coordenada Cxx,Lyy identifica um furo visto do lado dos componentes. C01,L01 e o canto superior esquerdo. O mapa de solda e espelhado horizontalmente, mas os numeros dos furos continuam os mesmos. <b>Nao espelhe os numeros uma segunda vez.</b>')
p('Cada componente tem pad 1 quadrado, referencia e numeros dos terminais. Para pecas de dois terminais: diodos 1=anodo, 2=catodo/faixa; eletroliticos 1=positivo, 2=negativo. Verifique a pinagem do fabricante antes de montar semicondutores.')
p('Os terminais de TO92 podem precisar de abertura para o passo 2,54 mm; resistores usam 7,62 mm; eletroliticos e capacitores podem exigir formacao dos terminais. Nao force o corpo. Os mapas reservam espaco, mas a peca efetivamente comprada deve caber.')
p('A ultima linha de cada placa e o barramento GND: linha 53 em A, linha 74 em B. Solde um fio continuo nessa linha, conferindo que nenhuma ilha adjacente recebeu ponte. Todos os outros fios devem permanecer isolados, inclusive quando cruzarem por baixo da placa.')
p('Os retornos dos capacitores de desacoplamento vao primeiro ao GND local do circuito correspondente, por fio curto. A lista ja indica essas ligacoes: nao substitua por dois fios longos independentes ate o barramento. Isso reduz a area dos lacos de alimentacao.')
p('ligacoes_ponto_a_ponto.csv fornece ID, rede, extremos com furos, cor e bitola. Cada linha e uma ligacao a executar e marcar como concluida. A lista forma uma arvore por rede; nao e necessario ligar todos os pares de pinos de uma mesma rede.')
p('pinos_furos_redes.csv permite auditar qualquer terminal. Mesmo nome de rede nos esquemas significa conexao eletrica, inclusive entre folhas. NC significa sem conexao e nunca deve ser unido a outro NC.')
p('Comece por GND e alimentacoes. Mantenha curtos os fios de /CE, /OE, dados e os cabos entre as placas; posicione A e B lado a lado. Leve a corrente das bobinas por retornos proprios ao barramento, evitando compartilhar trechos finos com a referencia analogica.')
p('Os mapas e esquemas a seguir sao vetoriais. Amplie o PDF para conferir os numeros. A escala impressa nao e gabarito de furacao: a montagem usa as coordenadas da placa ja perfurada.')

page('4. Ligações externas e pinagem do Mega')
table([['Conector','Ligacao'],['JA1.1..15','Mega D22..D36 -> MA0..MA14, entrando nos buffers; JA1.16 GND.'],['JA2.1..8','Mega D47,D38,D37,D40,D41,D42,D43,D44 -> RD0..7; JA2.9 5V USB; JA2.10 GND.'],['JA3.1..8','Mega D2..D9 -> WR0..7; JA3.9 D45; JA3.10 D46; JA3.11 GND; .12 NC.'],['JA4 -> JB1','Cabo 1:1: 1 VCC,2 VPP,3 VIN_HOLD,4 GND,5 +5B,6 BUS_OE,7 +5M,8 UV_FAIL. Pinos9/10 NC.'],['JB3.1..6','Mega D10,D11,D12,D14,D48,D49. Nunca ligar bobinas diretamente ao Mega.'],['JB3.7..11','Mega analogico A0,A1,A2,A3 e GND. Esses A0..3 NAO sao os enderecos da EPROM.'],['JB4.1 / .2','Mega AREF / GND. AREF recebe somente os 2,500 V da UR1.'],['JS1.1 / .2','Polo1 S1: C / NO. Em GRAVAR fecha entre esses dois terminais; NC sem uso.'],['JS1.3 / .4','Polo2 S1: C / NO. Em GRAVAR fornece +5B ao positivo da bobina K4; NC sem uso.'],['JM1.1..4','Modulo buck IN+, IN-, OUT+, OUT-. Ajustar saida5,00V antes de conectar ao restante.'],['JM2.1..4','Modulo boost IN+, IN-, OUT+, OUT-. Ajustar saida18,0V antes de alimentar UP2.']],[35*mm,135*mm])
p('Fonte 12 V: positivo -> fusivel 1 A retardado -> S0 -> JB2.1; negativo -> JB2.2. Use fonte regulada de 12 V/1 A. VIN_PROT precisa permanecer entre 11,1 e 13 V sob carga.')
p('LEDs sao opcionais, fora da BOM principal: D50 -> resistor1k -> anodo LED leitura -> catodo GND; D51 igual para sessao; D52 igual para falha. Podem ficar sem ligacao. Nao reutilize esses GPIOs.')

page('5. Montagem em blocos - sem EPROM')
for title,body in [
 ('A. Inspecao mecanica','Conte furos, compare corpos, oriente os soquetes e marque C01/L01 nas duas faces. Fixe placas e modulos antes de medir ou energizar. Nao conecte o Mega nem insira a EPROM.'),
 ('B. Entrada protegida','Monte JB2, QP1, RP1, ZP1, DP1 e reservatorio. Confira pinos e polaridades com multimetro. CP1 armazena energia: desligue e confirme descarga antes de alterar fios.'),
 ('C. Modulos e reguladores','Ajuste o buck isoladamente para5,00V e o boost para18,0V. Monte UP1/UP2, trimpots, diodos de protecao e capacitores. Confira as saidas antes de ligar interfaces.'),
 ('D. Rele e sensores','Monte K1..K4, drivers, clamps e flybacks. K4 retorna o flyback a COIL4_PLUS apos S1, nunca ao +5B anterior a chave. Monte referencia, UV e ADC; conecte o Mega somente depois de conferir curtos.'),
 ('E. Interface','Monte soquetes, MOSFETs de dados, LM339, buffers e clamps CE/OE. Interligue as placas. Grave o firmwareV2 no Mega. Confira que +5M e +5B nao estao unidos.'),
 ('F. Primeiro autoteste','ChaveLER, semEPROM. Execute calibracao das fontes/sensores e autoteste00/FF/AA/55. So prossiga apos validar estados, desligamento e pulso com instrumento.')]:
 h(title);p(body)

page('6. Ajuste das fontes e dos sensores')
p('Antes da primeira energizacao, coloque os cinco trimpots na menor resistencia entre pino1 e o conjunto2/3, conferindo com ohmimetro. Ajuste primeiro os modulos isolados. Com o Mega conectado, confira AREF e use tensoes para corrigir os ganhos ADC de VIN e +5B antes de selecionar alvos; a janela de +5B e estreita. Compare tambem VCC e VPP seguindoVCC no estado inicial, ainda sem chip.')
p('Mantenha U1 vazio. Mega pelo USB, chave LER. Nao confie nos valores iniciais dos trimpots. Use a acao de servico calibrar: ela mantem o alvo selecionado enquanto voce ajusta e mede; FIM pede retorno a5V. VPP elevada permanece bloqueada.')
code('python3 eprom_pc.py --porta /dev/ttyACM0 calibrar --vcc 4.2')
table([['Ordem','Alvo','Ajuste','Medir'],['1','4,20 V','RV4, base do divisor','TPB6 / GND'],['2','5,00 V','RV3, degrau0,8V','TPB6 / GND'],['3','6,00 V','RV2, degrau1,0V','TPB6 / GND'],['4','6,25 V','RV1, degrau0,25V','TPB6 / GND'],['5','12,75 V','RV5, reguladorVPP','TPB7 / GND, K4 solto'],['6','2,500 V','UR1 referencia fixa; nao ajustavel','TPB9 / GND']],[17*mm,30*mm,68*mm,55*mm])
p('Troque --vcc pelo alvo correspondente em cada passo. Volte a conferir todos os valores apos cada rodada. Cursor de cada trimpot e unido a um terminal, conforme esquema. Calibracao dos LM317 exige carga: RP2/RP7 de100R ja fornecem corrente minima nominal de12,5mA; confira tambem sob carga adicional de teste.')
p('TPB6 e VCC_EP; TPB7 e12,75V antes do rele; TPB8 e VPP realmente aplicado ao soquete. A calibracao de12,75V pode ser feita com K4 solto e chaveLER, sem aplicar essa tensao ao soquete.')
code('python3 eprom_pc.py --porta /dev/ttyACM0 tensoes')
p('Compare os quatro canais com multimetro. Em config.h: ganho_novo=ganho_atual x (multimetro / tensao_exibida). Recompile e confira novamente em4,2/5/6/6,25V e no caminhoVPP. O ganho nao ajusta a fonte e nao pode mascarar tensao errada. Verifique tambem a medicao com USB no menor valor de uso (>=4,75V); os MOSFETs dos ADCs nao sao instrumentos de precisao.')

page('7. Ensaios eletricos antes de inserir o chip')
p('<b>Esta e a etapa pendente de bancada.</b> Nao foi executada por software. Use primeiro carga resistiva e osciloscopio; ainda sem EPROM.')
table([['Ensaio','Criterio'],['Polaridade / continuidade','GND comum e correto. Ausencia de curto entre VCC,VPP,+5M,+5B. Conferir todos os pinos de U1.'],['Faixas sob carga','VCCprog6,25V e VPP12,75V dentro da toleranciaST±0,25V, com ripple/transientes incluidos; ajustes nominais e janelas de firmware sao mais estreitos.'],['Carga de VCC','100R/1W em TPB6 simula62,5mA a6,25V (mais12,5mA do regulador). Verificar dissipacao de UP1.'],['Carga de VPP','270R/1W em TPB7 simula47mA; verificar12,75V com boost carregado. Nao deixar resistor aquecendo perto do soquete.'],['Sequencia','No osciloscopio: elevarVCC antesVPP; retirarVPP elevada antes de reduzirVCC. Conferir partida, reset, chaveLER e desconexao dos12V.'],['UV','Reduzir lentamenteVIN e simular queda abrupta sob carga. UV_FAIL deve subir;CE/OE inibir; enderecos desligar depois;K4 retornar.'],['Temporizacao','/CE pino20:95..105us. Setup/hold de endereco e dados>=2us. Medir em5V e6,25V.'],['USB desligado','Com12V presentes eUSB ausente, medir ausencia de realimentacao relevante noMega e ADCs; CE/OE inativos.'],['Autoteste de interface','SemEPROM: padroes00/FF/AA/55 devem retornar exatamente os valores esperados.']],[39*mm,131*mm])
code('python3 eprom_pc.py --porta /dev/ttyACM0 pulso --vcc 6.25\npython3 eprom_pc.py --porta /dev/ttyACM0 autoteste')
p('O servico pulso mantem VPP seguindoVCC; nunca aplica12,75V. As cargas devem ser removidas apos o ensaio. Se usar100uF adicionais, mantenha os100nF ceramicos locais.')

page('8. Leitura, vazio, gravacao e verificacao')
p('Com tudo desligado, insira a EPROM nova/orientada pelo pino1. Ligue USB, depois12V. ChaveLER para ler. Feche o MonitorSerial antes de usar o cliente. Os comandos sao executados a partir da pasta codigos; noWindows use a portaCOM correta.')
code('python3 -m pip install pyserial\npython3 eprom_pc.py --porta /dev/ttyACM0 info\npython3 eprom_pc.py --porta /dev/ttyACM0 vazio\npython3 eprom_pc.py --porta /dev/ttyACM0 ler backup.bin\npython3 eprom_pc.py --porta /dev/ttyACM0 verificar imagem.bin')
p('Leitura so salva tres dumps identicos. Vazia significa todos os32768bytes iguais aFF; uma memoria usada pode precisar de apagamentoUV antes de aceitar outro conteudo. Ausencia de erros de leitura nao prova a capacidade de gravacao.')
p('Para gravar, confirme o chip M27C256B e a calibracao. Use um BIN de exatamente32768bytes. Coloque S1 emGRAVAR, execute e confirme a palavra solicitada. Mantenha a chave nessa posicao ate concluir as verificacoes.')
code('python3 eprom_pc.py --porta /dev/ttyACM0 gravar imagem.bin')
p('O firmware usa pulsos nominais100us, ate25tentativas porbyte e nenhum sobrepulso. O cliente transmite novamente oBIN para comparacao byte a byte em6V,4,2V e5V. SUCCESS so e emitido depois dessas tres passagens. CRC dos pacotes protege o transporte; nao substitui a comparacao integral.')
p('Ao terminar, confirme retorno a5V, coloqueLER, desligue12V e por ultimoUSB. Nunca remova ou insira o chip energizado. Se houver falha, nao repita automaticamente a gravacao: retireVPP, confira as fontes e leia o que ficou no chip.')
p('Essa memoria e UV EPROM, nao EEPROM. Apagamento exige equipamentoUV adequado pela janela; nao existe comando de apagar eletricamente. A organizacao dos quatro jogos depende do cartucho e do BIN, nao apenas da capacidade da memoria.')

page('9. Limites, resultados e fontes')
p('O hardware inclui protecao de polaridade, corte por subtensao, isolamento de enderecos e de sensores, autorizacao fisica deVPP e sequenciamento de software. Isso nao constitui protecao certificada contra qualquer falha de componente, erro de montagem, sobretensao ou ruido.')
p('UV_FAIL inibeCE/OE rapidamente. CP16 atrasa a retirada dos enderecos para preservar hold apos o bloqueio. O reservatorio4700uF isolado oferece retencao calculada da ordem de50ms no pior caso aproximado de100mA; isso nao e resultado de ensaio. Verifique todos esses tempos na montagem real.')
p('Uma falha de tensao detectada pelo firmware fica retida ate recuperacao explicita. Um transiente fisico menor que o intervalo de monitoramento20ms pode desaparecer antes da amostragem; nao ha latch independente de hardware para todo transiente. Reset durante um pulso pode deixar um byte parcialmente programado.')
p('A verificacao mecanica confere furos e envelopes previstos. Nao comprova compatibilidade com qualquer fabricante de capacitor, trimpot ou modulo. CP1maiorque18mm e modulos diferentes precisam de fixacao externa. Nao se trata de um novo PCB validado por DRC; a montagem e por fios isolados.')
p('Validacoes de firmware, testes, compilacaoMega e limites detalhados: codigos/VALIDACAO.txt. Validacoes do contrato, cobertura e listas de conexao: VALIDACAO_PROJETO.txt. Esquemas e mapas finais foram renderizados para inspecao visual.')
p('Fontes primarias utilizadas:')
for title,url in [
 ('ST M27C256B, rev2, maio2006, pp9/10/15/18','https://www.mouser.com/datasheet/2/389/stmicroelectronics_cd00000515-1204492.pdf'),
 ('ST LM317T, pinagem e aplicacao','https://www.st.com/resource/en/datasheet/lm317.pdf'),
 ('Omron G5V-2, bobinaH1 e pinagem p4','https://omronfs.omron.com/en_US/ecb/products/pdf/en-g5v_2.pdf'),
 ('TI SN74AHCT541','https://www.ti.com/lit/ds/symlink/sn74ahct541.pdf'),
 ('TI SN74HC14','https://www.ti.com/lit/ds/symlink/sn74hc14.pdf'),
 ('TI LM393','https://www.ti.com/lit/ds/symlink/lm393.pdf'),
 ('TI LM4040-N','https://www.ti.com/lit/ds/symlink/lm4040-n.pdf'),
 ('Microchip 2N7000 DS20005695A','https://ww1.microchip.com/downloads/en/DeviceDoc/20005695A.pdf')]:
    p(f'<link href="{url}" color="#007d80">{title}</link>')

def footer(c,doc):
    c.setFillColor(TEAL);c.rect(0,0,A4[0],3*mm,fill=1,stroke=0)
    c.setFont('DS',7);c.setFillColor(INK);c.drawString(18*mm,10*mm,'REV0.2 | 24/10/2026 | M27C256B | Prototipo sem ensaio fisico')
    c.drawRightString(A4[0]-18*mm,10*mm,str(doc.page))
base=TMP/'manual_texto.pdf'
SimpleDocTemplate(str(base),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=18*mm,bottomMargin=18*mm,title='M27C256B - montagem manual em placa perfurada',author='Projeto de bancada').build(story,onFirstPage=footer,onLaterPages=footer)
writer=PdfWriter();writer.append(str(base),outline_item='Guia de montagem e operacao')
for f in maps:writer.append(str(f),outline_item=f.stem)
schema=sorted((OUT/'esquemas').glob('ligacoes_*.svg'))
if schema:
    import cairosvg
    for f in schema:writer.append(io.BytesIO(cairosvg.svg2pdf(url=str(f))),outline_item=f.stem)
dest=(ROOT/'output/pdf/manual_perfurada_m27c256b.pdf') if OUT.parent.name=='output' else OUT/'manual_perfurada_m27c256b.pdf'
writer.add_metadata({'/Title':'M27C256B - gravador em placa perfurada - Rev0.2','/Author':'Projeto de bancada'})
writer.write(dest)
print(dest,'paginas:',len(writer.pages),'fios internos:',len(wires),'esquemas:',len(schema))
