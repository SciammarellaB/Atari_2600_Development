from pathlib import Path
from xml.sax.saxutils import escape
import math, json
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak, Image, Preformatted, Flowable, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/pdf'
TMP=ROOT/'output/pdf/fontes_manual/assets'
FONT=Path('/usr/share/fonts/truetype/dejavu')
for name, file in [('Sans','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),
                   ('Mono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='Bold', italic='Sans', boldItalic='Bold')
NAVY=colors.HexColor('#142b43'); TEAL=colors.HexColor('#007d83')
GRAY=colors.HexColor('#536477'); LIGHT=colors.HexColor('#edf3f6')
AMBER=colors.HexColor('#fff1d8'); INK=colors.HexColor('#1d2935')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body',fontName='Sans',fontSize=9.3,leading=14,
                         textColor=INK,spaceAfter=9))
styles.add(ParagraphStyle(name='Small2',parent=styles['Body'],fontSize=8,leading=11,spaceAfter=6))
styles.add(ParagraphStyle(name='H1x',fontName='Bold',fontSize=21,leading=26,textColor=NAVY,spaceAfter=17))
styles.add(ParagraphStyle(name='H2x',fontName='Bold',fontSize=11,leading=15,textColor=TEAL,spaceBefore=9,spaceAfter=8))
styles.add(ParagraphStyle(name='Kicker',fontName='Bold',fontSize=9,leading=13,textColor=TEAL,spaceAfter=10))
styles.add(ParagraphStyle(name='Code2',fontName='Mono',fontSize=7,leading=9.5,textColor=INK,
                         backColor=LIGHT,borderPadding=8,spaceAfter=10))
story=[]

def p(txt, small=False): return Paragraph(txt,styles['Small2' if small else 'Body'])
def add(txt, small=False): story.append(p(txt,small))
def title(n,txt):
    if story: story.append(PageBreak())
    story.append(Paragraph(n,styles['Kicker']))
    story.append(Paragraph(txt,styles['H1x']))
def sub(txt): story.append(Paragraph(txt,styles['H2x']))
def code(txt): story.append(Preformatted(txt.strip('\n'),styles['Code2']))
def table(rows,widths=None,size=8.1,pad=5):
    cells=[[Paragraph(escape(str(x)).replace('\n','<br/>'),
         ParagraphStyle('cell',fontName='Bold' if r==0 else 'Sans',fontSize=size,
         leading=size+3,textColor=colors.white if r==0 else INK)) for x in row]
         for r,row in enumerate(rows)]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),
      ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),
      ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
      ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),pad),
      ('BOTTOMPADDING',(0,0),(-1,-1),pad),
      ('LINEBELOW',(0,0),(-1,0),0.7,TEAL)]))
    story.extend([t,Spacer(1,10)])
def note(txt):
    t=Table([[p(txt)]],colWidths=[499])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),AMBER),
      ('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#deb96c')),
      ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
      ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    story.extend([t,Spacer(1,10)])

class Circuit(Flowable):
    def __init__(self,kind): super().__init__(); self.width=499; self.height=225; self.kind=kind
    def draw(self):
        c=self.canv; c.setStrokeColor(NAVY); c.setFillColor(INK); c.setLineWidth(1)
        def text(x,y,t,size=8,b=False): c.setFont('Bold' if b else 'Sans',size);c.drawString(x,y,t)
        def wire(x,y,X,Y): c.line(x,y,X,Y)
        def dot(x,y): c.circle(x,y,2,fill=1,stroke=0)
        def resistor(x,y,w=40):
            c.rect(x,y-4,w,8,fill=0,stroke=1)
        def ground(x,y):
            wire(x,y,x,y-7);wire(x-9,y-7,x+9,y-7);wire(x-6,y-11,x+6,y-11);wire(x-3,y-15,x+3,y-15)
        # One open-drain stage: reproducible for data or enables.
        text(9,207,'Célula de dreno aberto - repetir conforme as tabelas',10,True)
        text(224,182,'VCC da EPROM (5 V / 6 V)',8)
        wire(250,172,250,160);c.rect(246,134,8,26);wire(250,134,250,110)
        text(263,145,'10 kΩ',8);dot(250,110)
        wire(250,110,366,110)
        text(369,107,'NÓ',9,True)
        wire(250,110,250,86)
        # MOS symbol with named terminals to avoid manufacturer pin ambiguity.
        wire(238,52,238,85);wire(246,53,246,84)
        wire(246,80,250,80);wire(246,58,250,58)
        wire(250,86,250,80);wire(250,58,250,34);ground(250,34)
        text(261,75,'D',8);text(261,46,'S',8);text(204,73,'G',8)
        text(280,55,'2N7000',9,True)
        wire(45,69,103,69);resistor(103,69,35);wire(138,69,238,69)
        text(45,85,'Mega: GATE',8);text(105,84,'220 Ω',8)
        dot(185,69);wire(185,69,185,52);c.rect(181,28,8,24);wire(185,28,185,20);ground(185,20)
        text(129,33,'100 kΩ',8)
        if self.kind=='data':
            text(12,170,'NÓ = Qn da EPROM + entrada IN+ do LM339',8,True)
            text(12,152,'Gate LOW: libera o dado (1 por pull-up).',8)
            text(12,136,'Gate HIGH: força o dado para 0.',8)
        else:
            text(12,170,'NÓ = /CE ou /OE da EPROM',8,True)
            text(12,152,'Gate LOW: controle fica HIGH / inativo.',8)
            text(12,136,'Gate HIGH: controle fica LOW / ativo.',8)

class Comparator(Flowable):
    def __init__(self): super().__init__(); self.width=499; self.height=175
    def draw(self):
        c=self.canv;c.setStrokeColor(NAVY);c.setFillColor(INK);c.setLineWidth(1)
        def tx(x,y,t,s=8): c.setFont('Sans',s);c.drawString(x,y,t)
        # Signal input and reference.
        c.line(25,115,180,115);tx(25,130,'Qn da EPROM (0 a 6,25 V)')
        c.line(25,65,180,65);tx(25,45,'VREF ≈ 1,56 V (IN-)')
        path=c.beginPath();path.moveTo(180,40);path.lineTo(180,140);path.lineTo(280,90);path.close()
        c.drawPath(path);tx(190,112,'+');tx(190,62,'-')
        c.line(280,90,465,90);tx(340,69,'Saída para RP[n] do Mega')
        c.circle(340,90,2,fill=1);c.line(340,90,340,120)
        c.rect(336,120,8,23);c.line(340,143,340,153);tx(354,130,'4,7 kΩ');tx(312,160,'5 V do Mega')
        tx(205,155,'LM339');tx(200,18,'Alimentação fixa: 9 a 15 V; GND comum')

title('MANUAL DE BANCADA • 24/10/2026','EPROM 27C256<br/>Teste, leitura e gravação')
add('<b>Arduino Mega 2560 + ST 27C256-30CQ</b>')
story.append(Spacer(1,12))
add('Guia completo com pinagem, ligação de leitura, diagnóstico, exportação de 32 KB, apagamento UV, circuito de referência para programação e códigos integrais para Arduino e computador.')
note('<b>Dois níveis de validação.</b> A leitura de sua montagem foi demonstrada na conversa. O gravador descrito aqui é um projeto de referência com revisão técnica e software verificado; não foi montado nem ensaiado fisicamente. As fontes de programação são ajustadas manualmente, com multímetro.')
sub('O que já foi observado')
table([['Evidência','Resultado'],['Três leituras consecutivas','CRC32 = 6691559F em todas'],
       ['Troca de endereço e retorno','0 divergências; máscara 0x00'],
       ['Conteúdo lido','17.064 bytes FF; 1.378 bytes 00'],
       ['Conclusão proporcional','Leitura estável; a memória não estava vazia']], [180,319])
add('Esses resultados não identificam os jogos nem comprovam todas as células ou todas as linhas de endereço. A comparação com uma imagem conhecida e o ciclo apagar/gravar/verificar são verificações adicionais.')
sub('Como usar este manual')
add('Comece pelas seções 1 a 5 para repetir a leitura. As seções 6 a 10 descrevem o gravador de bancada. Os apêndices trazem o firmware e o cliente Python completos. Os mesmos arquivos estão no pacote de códigos que acompanha o PDF.')
add('Escopo: DIP-28, 32.768 × 8 bits. Os valores de programação são da <b>TS27C256Q antiga</b>, cujo datasheet lista TS27C256-30CQ. A imagem enviada mostra a pinagem, mas não confirma o texto completo gravado no seu chip. Confira essa identificação antes de programar; não transfira esses valores para M27C256B ou outros fabricantes.',True)

title('1 • IDENTIFICAÇÃO','Pinagem da EPROM')
add('Vista superior, com o entalhe para cima: pino 1 no canto superior esquerdo, descendo até 14; pelo lado direito, a numeração sobe de 15 até 28. A figura abaixo foi fornecida por você.')
story.append(Image(str(TMP/'pinagem_usuario.png'),width=292,height=348))
story.append(Spacer(1,12))
table([['Sinal','Função'],['A0 a A14','15 entradas de endereço; 0x0000 a 0x7FFF'],
       ['O0 a O7 / Q0 a Q7 / D0 a D7','Oito linhas de dados; nomes equivalentes neste manual'],
       ['/CE e /OE','Ativos em nível baixo; barra superior significa inversão'],
       ['VSS, VCC e VPP','Terra, alimentação e alimentação de programação']], [190,309])
add('O “A0” da EPROM não é o conector analógico A0 do Mega. Aqui, A0 da EPROM é ligado ao pino digital D22 do Mega.',True)

title('2 • LEITOR DIRETO DE 5 V','Ligação pino a pino')
add('Esta é a <b>montagem A</b>: apenas leitura, com <b>PROGRAMMER_HARDWARE = 0</b>. A tabela padroniza o mapa final com D47 e conserva a troca entre Q0 e Q2 feita durante o diagnóstico. Refaça ou confira o mapa inteiro; não misture tabelas antigas da conversa.',True)
pins={1:('VPP','5V'),2:('A12','D34'),3:('A7','D29'),4:('A6','D28'),5:('A5','D27'),6:('A4','D26'),7:('A3','D25'),8:('A2','D24'),9:('A1','D23'),10:('A0','D22'),11:('Q0','D47'),12:('Q1','D38'),13:('Q2','D37'),14:('VSS','GND'),15:('Q3','D40'),16:('Q4','D41'),17:('Q5','D42'),18:('Q6','D43'),19:('Q7','D44'),20:('/CE','D45'),21:('A10','D32'),22:('/OE','D46'),23:('A11','D33'),24:('A9','D31'),25:('A8','D30'),26:('A13','D35'),27:('A14','D36'),28:('VCC','5V')}
table([['Pino EPROM','Sinal','Mega / alimentação']]+[[str(k),*pins[k]] for k in range(1,29)],[90,150,259],size=7.6,pad=3)
add('<b>Controles:</b> resistor de 10 kΩ de /CE para 5 V e outro de /OE para 5 V. <b>Desacoplamento:</b> 100 nF de 28 a 14 e outro de 1 a 14, com fios curtos. Retire a memória do cartucho antes de conectá-la ao leitor.',True)

title('3 • MONTAGEM E ALIMENTAÇÃO','Antes de iniciar a leitura')
sub('Sequência para a montagem A')
add('1. Com a EPROM desconectada, envie o firmware configurado como leitor. Escolha Arduino Mega or Mega 2560 na IDE e a porta correta.<br/>2. Retire o USB. Monte e confira as 28 conexões.<br/>3. Confirme que os pinos 1 e 28 recebem o mesmo 5 V e que 14 é GND.<br/>4. Reconecte o USB. Abra a serial em 115200 baud ou execute o cliente Python. Feche o Monitor Serial antes de abrir a mesma porta pelo Python.')
table([['Componente','Aplicação'],['2 × 100 nF cerâmicos (104), 25 V ou mais','Um de VCC para GND e outro de VPP para GND, junto ao chip'],
       ['2 × 10 kΩ','Pull-ups de /CE e /OE no leitor direto'],
       ['Eletrolíticos de 100 µF','Filtragem adicional; não equivalem a 100 nF'],
       ['Multímetro','Medir entre 28 e 14, depois entre 1 e 14']], [220,279])
add('100 nF = 0,1 µF; 100 µF é mil vezes maior. Em eletrolíticos, positivo na alimentação e negativo no GND. Para leitura a 5 V, use tensão nominal de pelo menos 6,3 V; para VPP de programação, prefira 25 V ou mais. O capacitor do Mega não substitui o capacitor perto da EPROM.')
note('Um ensaio inicial sem os cerâmicos pode funcionar, como ocorreu durante a conversa. Se houver variação, não conclua defeito no chip sem corrigir alimentação, contatos e desacoplamento. No gravador, os 100 nF fazem parte da montagem especificada.')
sub('O que não aplicar ao leitor direto')
add('A montagem A fica exclusivamente em 5 V. Não aplique 6 V ou 12,5 V a ela. O circuito da montagem B altera as conexões de dados e controles; mudar somente o código ou a fonte não transforma o leitor em gravador.')

title('4 • SOFTWARE NO COMPUTADOR','Ler os 32 KB e verificar vazio')
add('Arquivos do pacote: <b>eprom27/eprom27.ino</b> e <b>eprom_pc.py</b>. O firmware fica aguardando comandos; esta versão não inicia automaticamente as três leituras ao ligar. Todas as operações são solicitadas pelo cliente ou pelo Monitor Serial.')
sub('Preparação do Python 3')
code('''python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyserial''')
add('No Windows: crie o ambiente com <b>py -m venv .venv</b> e ative com <b>.venv\\Scripts\\activate</b> no Prompt de Comando. Troque /dev/ttyACM0 pela porta real, por exemplo COM3. Em Linux, o nome também pode ser /dev/ttyUSB0.')
sub('Operações de leitura')
code('''python eprom_pc.py --porta /dev/ttyACM0 info
python eprom_pc.py --porta /dev/ttyACM0 teste
python eprom_pc.py --porta /dev/ttyACM0 vazio
python eprom_pc.py --porta /dev/ttyACM0 ler original.bin
python eprom_pc.py --porta /dev/ttyACM0 verificar original.bin''')
add('<b>ler</b> faz três dumps completos, compara os 32.768 bytes entre si e só salva se forem idênticos. Não sobrescreve arquivo existente. <b>vazio</b> usa o mesmo teste e informa se todos os bytes são FF. <b>verificar</b> compara a memória com um arquivo de exatamente 32 KB.')
sub('Comandos pelo Monitor Serial')
table([['Enviar','Operação'],['I','Identificação do firmware e do tipo de montagem'],['T','Três CRCs/contagens e teste de troca de endereço'],['B','Uma varredura com CRC, contagens e BLANK/NOT_BLANK'],['D','Desarma e deixa endereços em alta impedância']], [75,424])
add('Não envie R no Monitor Serial para visualizar texto: R transmite um arquivo binário. Use o cliente para recebê-lo. O comando D não desconecta fontes externas.',True)

title('5 • DIAGNÓSTICO','Estabilidade, vazio e conteúdo correto')
table([['Resultado','Interpretação'],['CRCs iguais e DIFF=0','Repetibilidade demonstrada nos ensaios realizados'],['FF=32768 e ZERO=0','Compatível com memória vazia; descartar falha de habilitação antes de aceitar'],['FF menor que 32768','Existem bytes diferentes de FF, se a leitura é estável'],['Comparação exata com BIN conhecido','Conteúdo coincide nos 32.768 endereços lidos']], [205,294])
add('“Vazia” significa apagada para todos os bits em 1. Não significa uma sequência de zeros. Um barramento desconectado ou saídas desabilitadas também pode aparentar FF; o blank check isolado não comprova integridade.')
sub('O defeito de conexão observado na conversa')
add('A máscara 0x04 apontou divergência no bit Q2 (pino 13). Após trocar as pontas de Q0 e Q2 e ajustar o array, a máscara mudou para 0x01. A falha acompanhou o caminho de fio/entrada D39. Depois da correção, o CRC ficou em 6691559F e DIFF foi zero. Isso não demonstrou que o próprio pino D39 estava danificado: jumper e contatos pertenciam ao mesmo caminho suspeito.')
table([['Máscara','Bit','Pino EPROM','Mega atual']]+[[f'0x{1<<b:02X}',f'Q{b}',str([11,12,13,15,16,17,18,19][b]),f'D{[47,38,37,40,41,42,43,44][b]}'] for b in range(8)], [80,80,125,214])
sub('Se voltar a variar')
add('Desligue antes de mexer. Revise o fio indicado pela máscara, GND, VPP e VCC, encaixe do chip e todos os endereços. Use fios curtos e os cerâmicos. Se houver multímetro, meça as tensões no próprio chip durante a varredura. Leituras corretas em um único endereço não eliminam falhas nos demais.')

title('6 • APAGAMENTO E ARQUIVO','Preparar uma nova imagem')
add('Você autorizou descartar os quatro jogos existentes. Ainda assim, o leitor permite salvar a imagem atual se quiser. A memória não é apagada pelo Mega: a versão com janela de quartzo usa apagamento UV. Se o encapsulamento não tiver janela, não presuma que possa reutilizá-lo após gravado.')
sub('Apagamento UV')
add('Use apagador fechado próprio para EPROM, com UV-C de aproximadamente 254 nm. Retire o chip do circuito e exponha a janela conforme as instruções do equipamento. O tempo depende de intensidade, distância e envelhecimento da lâmpada; não use um tempo fixo como prova de apagamento. Não exponha olhos ou pele ao UV. Depois, recoloque no leitor e execute o comando <b>vazio</b>. Só aceite 32.768 bytes FF com leitura estável. Cubra a janela após finalizar o uso. [1]')
sub('Criar uma imagem de teste de 32 KB')
add('Para o primeiro ciclo de programação, uma imagem pseudoaleatória conhecida ajuda a testar combinações de endereço e dados. O arquivo abaixo não é um jogo e não deve ser executado no Atari.')
code('''# Salve como criar_teste.py e execute: python criar_teste.py
import random
from pathlib import Path
r = random.Random(2600)
dados = bytes(r.randrange(256) for _ in range(32768))
Path('teste32k.bin').write_bytes(dados)''')
add('Esse código também está no pacote como criar_teste.py. Execute em uma pasta de trabalho; o arquivo teste32k.bin será criado ou substituído. O cliente não completa, duplica nem reorganiza arquivos automaticamente.')
sub('Quatro jogos em uma EPROM')
add('A capacidade de 32 KB não determina sozinha onde os quatro jogos ficam. O layout depende de como o cartucho seleciona os endereços e de eventual bankswitching dos jogos. Identifique a placa e os tamanhos antes de concatenar ROMs. O gravador grava bytes na ordem do BIN; ele não implementa o circuito do cartucho.')

title('7 • GRAVADOR DE REFERÊNCIA','Montagem B: componentes e arquitetura')
note('<b>Somente para a TS27C256Q antiga confirmada.</b> Montagem de bancada ainda não ensaiada fisicamente. Configuração do firmware: PROGRAMMER_HARDWARE = 1. Os sinais do Mega em D45/D46 são gates de MOSFETs, e não conexões diretas aos pinos 20/22.')
add('A interface usa oito MOSFETs para escrever dados, dois para /CE e /OE, e dois LM339 para receber os dados. Os comparadores têm saída de coletor aberto puxada para 5 V; assim, as entradas do Mega não recebem os até 6,25 V possíveis no lado da EPROM. Os endereços continuam diretos, pois os níveis de entrada da EPROM são TTL.')
table([['Quantidade','Componente / função'],['1','Mega 2560 e soquete DIP-28 de 600 mil, preferencialmente ZIF'],['2','LM339 em DIP-14; não confundir com LM393 de dois canais'],['10','2N7000 em TO-92: oito dados e dois controles'],['10','220 Ω, um em série com cada gate'],['10','100 kΩ, de cada gate para GND'],['10','10 kΩ, pull-ups de Q0..Q7, /CE e /OE para VCC da EPROM'],['8','4,7 kΩ, saídas dos comparadores para 5 V do Mega'],['1 + 1','22 kΩ e 10 kΩ para gerar VREF; resistores 1%'],['5','100 nF cerâmicos: VCC, VPP, U1, U2 e VREF; 25 V ou mais'],['3 linhas','VCC ajustável 5/6 V; VPP ajustável 5/12,5 V; V_AUX fixa 9..15 V'],['1','Multímetro; osciloscópio recomendado para validar pulsos'],['Conforme a fonte','Capacitores, limitação de corrente e proteção dos módulos de alimentação']], [72,427],size=8)
add('As três linhas podem vir de fontes de bancada ou módulos regulados adequados. Este guia usa as saídas prontas e medidas: não inclui o projeto interno de conversores. Todos os negativos são unidos ao GND do circuito. A linha auxiliar dos comparadores não é a VPP comutada.')

title('8 • INTERFACE DE DADOS','Escrita por MOSFET e leitura por LM339')
story.append(Circuit('data'))
add('Repita a célula para Q0 a Q7. O dreno vai ao nó do dado; source ao GND. O gate recebe o pino WP[n] através de 220 Ω e tem pull-down de 100 kΩ. O pull-up de 10 kΩ vai para VCC da EPROM. Antes de habilitar a saída da memória, todos os gates de dados ficam LOW, liberando o barramento.',True)
story.append(Comparator())
add('VREF: 5 V do Mega → 22 kΩ → VREF → 10 kΩ → GND, com 100 nF de VREF ao GND. Valor nominal 1,5625 V. Cada saída do LM339 tem seu próprio pull-up de 4,7 kΩ para 5 V do Mega. O nível lógico não é invertido. [2]',True)
note('Nos 2N7000, identifique G, D e S pelo datasheet do fabricante comprado. Na referência Microchip TO-92: pino 1 = S, 2 = G, 3 = D; a orientação do desenho do encapsulamento é essencial. Não suponha que BS170 ou outro MOSFET tenha a mesma ordem. [3]')

title('8 • INTERFACE DE DADOS / CONTINUAÇÃO','Tabela completa dos oito canais')
add('U1 e U2 são LM339 DIP-14. Em ambos: <b>pino 3 = V_AUX fixa 9..15 V</b>, <b>pino 12 = GND</b>, e 100 nF entre esses dois pinos. A numeração dos nomes internos de canais varia entre fabricantes; use os números físicos abaixo. [2]')
table([['Dado','EPROM','Gate WP','LM339','IN+','IN-','OUT','RP Mega'],
       ['Q0','11','D2','U1','5','4','2','D47'],['Q1','12','D3','U1','7','6','1','D38'],
       ['Q2','13','D4','U1','9','8','14','D37'],['Q3','15','D5','U1','11','10','13','D40'],
       ['Q4','16','D6','U2','5','4','2','D41'],['Q5','17','D7','U2','7','6','1','D42'],
       ['Q6','18','D8','U2','9','8','14','D43'],['Q7','19','D9','U2','11','10','13','D44']],
      [43,54,60,60,44,44,44,150],size=7.8)
add('Todas as entradas IN- da tabela vão a VREF. Todas as IN+ vão ao respectivo nó Qn. Cada OUT vai apenas ao RP indicado e ao seu pull-up para 5 V. <b>Retire os oito fios diretos EPROM → Mega da montagem A.</b> Na montagem B, o Mega recebe os dados somente pelas saídas dos comparadores.')
sub('Autoteste antes de inserir a EPROM')
add('Com o soquete vazio, VCC e VPP em 5 V, V_AUX ligada e a interface montada, execute:')
code('python eprom_pc.py --porta /dev/ttyACM0 autoteste')
add('Devem aparecer quatro pares iguais: EXPECT=0 GOT=0, EXPECT=FF GOT=FF, EXPECT=AA GOT=AA e EXPECT=55 GOT=55. O teste confirma o caminho MOSFET → nó → comparador → Mega. Não verifica a EPROM nem a exatidão das fontes. Se falhar, não prossiga para 6 V/12,5 V.')
sub('Margens elétricas')
add('Com 10 kΩ para VCC de no máximo 6,25 V, a corrente em um dado LOW é de até 0,625 mA, abaixo dos 2,1 mA usados na especificação do nível baixo da EPROM. A referência próxima de 1,56 V fica entre os níveis TTL de 0 e 1. Com V_AUX de pelo menos 9 V, a faixa de entrada do LM339 cobre o barramento de até 6,25 V. Esta análise não substitui ensaio de montagem e temporização. [1,2]')

title('9 • CONTROLES E ENDEREÇOS','/CE e /OE com estado seguro no reset')
story.append(Circuit('control'))
table([['Gate do Mega','Dreno / nó','Pull-up'],['D45 através de 220 Ω','Pino 20 da EPROM: /CE','10 kΩ para VCC da EPROM'],['D46 através de 220 Ω','Pino 22 da EPROM: /OE','10 kΩ para VCC da EPROM']], [155,190,154])
add('Cada controle usa mais um 2N7000 com source no GND e pull-down de 100 kΩ no gate. Quando o Mega reinicia, os MOSFETs ficam desligados e os pull-ups mantêm /CE e /OE altos. O firmware compensa a inversão. Não mantenha os controles ligados diretamente ao Mega nesta montagem.')
sub('Endereços e alimentações')
add('A0..A14 continuam ligados a D22..D36, exatamente na sequência da tabela da montagem A. EPROM pino 14, sources dos MOSFETs, LM339 pino 12, negativos das fontes e GND do Mega ficam no mesmo terra. VCC e VPP passam a vir das fontes externas, <b>sem ligação ao conector 5V do Mega</b>. O 5 V do Mega alimenta somente referência e pull-ups das saídas dos comparadores.')
note('Os endereços são diretos. Não deixe o Mega dirigir HIGH quando VCC da EPROM estiver desligada. Na partida, alimente V_AUX e a EPROM em 5 V/5 V antes de energizar o Mega. Ao terminar, use D para deixar endereços em alta impedância antes de retirar VCC. Não desconecte GND durante uma operação.')

title('10 • FONTES MANUAIS','Sequência de bancada para gravar')
table([['Etapa','VCC EPROM','VPP EPROM','Situação'],['Leitura / montagem','5 V','5 V','V_AUX fixa ligada'],['Preparar programação','Subir para 6 V','Manter 5 V','/CE e /OE HIGH'],['Programar / verify','6 V','Subir para 12,5 V','Somente após medir as duas'],['Retornar à leitura','Manter 6 V','Baixar para 5 V','Desarmar antes de ajustar'],['Verificação final','Baixar para 5 V','5 V','Comparar todos os bytes']], [145,92,92,170])
add('Use multímetro no próprio soquete: pino 28 contra 14 e pino 1 contra 14. Ajuste as fontes inicialmente sem o chip e confira novamente sob carga. A especificação de programação é VCC de 5,75 a 6,25 V e VPP de 12,2 a 12,8 V, em ambiente de 20 a 30 °C. Correntes de programação de VCC e VPP são especificadas em até 30 mA cada, além da corrente da interface. Evite que a limitação da fonte derrube as tensões. [1]')
sub('Passo a passo')
add('1. Faça o autoteste sem chip; desligue tudo e insira a EPROM apagada.<br/>2. Ligue V_AUX, VCC=5 V e VPP=5 V, depois o Mega. Confira leitura e vazio.<br/>3. Com controles inativos, eleve VCC para 6 V; depois VPP para 12,5 V. Meça.<br/>4. Execute o comando abaixo; confirme GRAVAR apenas com chip e tensões conferidos.<br/>5. O firmware verifica vazio no modo elevado e programa em blocos.<br/>6. Ao pedir, reduza primeiro VPP para 5 V e depois VCC para 5 V. Meça e pressione Enter. O cliente fará três leituras e comparação final exata.')
code('python eprom_pc.py --porta /dev/ttyACM0 gravar teste32k.bin')
note('<b>Em erro, timeout ou interrupção:</b> o software tenta desarmar, mas não comuta fontes. Confira /CE e /OE altos. Reduza VPP antes de VCC. Se a conexão USB caiu, os pull-downs dos gates ajudam a inibir os controles, mas não dispensam medir as tensões. Não trate DISARMED como fonte desligada.')
add('Para desligar completamente: em 5 V/5 V, envie D; retire VPP, depois VCC, depois V_AUX e USB. Os endereços devem estar em alta impedância antes da retirada de VCC. [1]',True)

title('11 • ALGORITMO E LIMITES','O que o firmware faz ao programar')
add('Os parâmetros abaixo são específicos do algoritmo antigo ST TS27C256Q. O perfil não é uma seleção universal de “27C256”. [1]')
table([['Passo','Comportamento'],['1. Armar','A exige montagem B e percorre toda a EPROM em verify elevado; só aceita FF em tudo'],['2. Receber bloco','Até 128 bytes, endereço e CRC32; recusa tamanho, faixa ou CRC inválidos'],['3. Programar byte','Estabiliza endereço/dados; /OE HIGH; pulso /CE LOW de 1 ms'],['4. Verificar','Libera todos os MOSFETs de dados; /CE HIGH e /OE LOW; compara o byte'],['5. Repetir / sobrepulso','Até 25 tentativas, incluindo a 25ª. Ao passar, um sobrepulso de 3 × N ms'],['6. Finalizar','Desarma; operador retorna a 5 V/5 V; leitura integral e comparação com o BIN']], [135,364])
add('Bits FF não precisam de pulsos; permanecem apagados. A rotina recusa uma transição que exija 0 → 1. O código usa margens de 20 µs nos tempos de setup e hold, superiores aos mínimos de 2 µs; o pulso inicial é de 1 ms, e o maior sobrepulso é de 75 ms. Interrupções ficam suspensas durante o pulso; o programa não depende do relógio do Arduino para medir o tempo total da gravação.')
sub('Limites explícitos desta versão')
add('Não há medição automática de tensão, desligamento por hardware, detecção confiável de chip ausente ou acionamento automático das fontes. O blank check pode ser enganado por barramento permanentemente alto. Não há gravação da identificação eletrônica, que usaria tensão elevada em A9; nunca aplique 12 V às linhas de endereço desta montagem.')
add('O leitor foi demonstrado no seu ensaio. O circuito novo com LM339/MOSFETs precisa passar pelo autoteste, leitura estável em 5 V e ensaio de programação em bancada. A compilação e os testes de software não medem ruído, overshoot, fonte sob carga, polaridade real de transistor ou largura física do pulso.')

title('12 • PROTOCOLO E CÓDIGOS','Arquivos e configuração')
table([['Arquivo','Uso'],['codigos/eprom27/eprom27.ino','Firmware único; macro 0 para leitor A ou 1 para gravador B'],['codigos/eprom_pc.py','Cliente Python 3 com pyserial'],['codigos/LEIA-ME.txt','Comandos de uso e resumo de montagem']], [240,259])
add('Os apêndices reproduzem integralmente os arquivos. Prefira os arquivos do pacote ao copiar trechos do PDF, para preservar recuos e caracteres. O código é ASCII, exceto uma mensagem de console; os comentários explicam a polaridade do circuito.')
code('''// Leitor direto:
#define PROGRAMMER_HARDWARE 0

// Gravador com a interface das secoes 7 a 10:
#define PROGRAMMER_HARDWARE 1''')
add('A macro deve ser escolhida antes de enviar o sketch. Não existe comutação automática entre as duas montagens. Troque também a fiação ao migrar de A para B. O firmware identifica o modo com I e bloqueia gravação na versão READER.')
sub('Enquadramento USB')
add('I identifica; T diagnostica; B faz estatísticas; R emite “DATA 32768”, os 32.768 bytes binários e END; S testa a interface B; A arma em verify elevado; D desarma. W recebe endereço de 16 bits little-endian, comprimento de 1 a 128 bytes, os dados e CRC32 little-endian do cabeçalho mais os dados. O computador aguarda OK antes do próximo bloco.')
add('Os dumps são comparados byte a byte em três passagens, além do CRC informativo. A entrada de gravação deve ter exatamente 32.768 bytes. Não há mudança de bancos nem interpretação de cabeçalhos de ROM.')
sub('Tempo e memória')
add('As operações percorrem 32 KB com digitalWrite/digitalRead e margens conservadoras; espere dezenas de segundos por ensaio completo. O Mega recebe apenas um bloco por vez. O timeout do cliente é de 60 s por resposta ou trecho recebido; ele não deve ser interpretado como duração máxima do processo inteiro.')

def listings(file,label,chunk=48):
    lines=file.read_text().splitlines()
    for k in range(0,len(lines),chunk):
        title(label, f'{file.name}<br/><font size="12">Linhas {k+1} a {min(k+chunk,len(lines))} de {len(lines)}</font>')
        # Numbers occupy a separate stable prefix. Original source supplied in ZIP.
        txt='\n'.join(f'{i+1:03d}  {lines[i]}' for i in range(k,min(k+chunk,len(lines))))
        story.append(Preformatted(txt,styles['Code2']))
        add('Listagem de referência. Para copiar ou compilar, use o arquivo original do pacote.',True)

listings(OUT/'codigos/eprom27/eprom27.ino','APÊNDICE A • FIRMWARE COMPLETO')
listings(OUT/'codigos/eprom_pc.py','APÊNDICE B • CLIENTE PYTHON COMPLETO')

title('REFERÊNCIA RÁPIDA','Checklist e fontes técnicas')
table([['Antes de ler','Antes de gravar'],['Montagem A em 5 V/5 V ou B no modo de leitura','Família TS27C256Q e encapsulamento confirmados'],['Mapa AP/RP igual à fiação','Montagem B completa; macro = 1'],['Capacitores próximos e fios curtos','Autoteste 00/FF/AA/55 sem falhas'],['Três dumps idênticos; DIFF=0','Apagamento UV e blank check'],['BIN conhecido para afirmar conteúdo correto','VCC e VPP medidas; ordem das fontes respeitada']], [249,250])
sub('Validação dos arquivos deste manual')
add('Compilação real com Arduino CLI e core arduino:avr 1.8.8, alvo arduino:avr:mega: <b>leitor 4.860 bytes de flash / 211 bytes globais</b>; <b>gravador 5.678 bytes de flash / 223 bytes globais</b>. Cliente Python passou em compilação de sintaxe. Revisão independente verificou algoritmo, polaridades, dump e tratamento de erros. Os resultados adicionais de simulação acompanham o pacote em VALIDACAO.txt.')
note('A compilação não valida a fiação. A parte de programação continua sem ensaio físico. Confirme a marcação completa e valide a montagem B antes de inserir a EPROM ou elevar tensões.')
sub('Fontes primárias')
refs=[('[1] SGS-Thomson, Memory Products Databook, junho/1988. TS27C256Q, páginas impressas 121 a 129; parâmetros e algoritmo, 126 a 128.',
 'https://www.bitsavers.org/components/stMicroelectronics/_dataBooks/Memory_Products_Databook_Jun88.pdf'),
 ('[2] Texas Instruments, LM339, datasheet SLCS006Z. Pinagem DIP-14, modo comum e saída coletor aberto.',
 'https://www.ti.com/lit/ds/symlink/lm339.pdf'),
 ('[3] Microchip, 2N7000, DS20005695A. Terminais, encapsulamento e características elétricas.',
 'https://ww1.microchip.com/downloads/en/DeviceDoc/2N7000-N-Channel-Enhancement-Mode-Vertical-DMOS-FET-Data-Sheet-20005695A.pdf'),
 ('[4] Arduino, Mega 2560 Rev3. Placa, pinagem e especificações.',
 'https://docs.arduino.cc/hardware/mega-2560/'),
 ('[5] Microchip, ATmega2560. Limites elétricos do microcontrolador.',
 'https://www.microchip.com/en-us/product/ATmega2560')]
for label,url in refs:
    add(label+f' <link href="{url}" color="#007d83"><u>Abrir documento</u></link>',True)
add('Figura de pinagem: imagem enviada pelo usuário nesta conversa. Diagramas de interface, código e texto deste manual: elaboração original para esta montagem. Consulta e revisão: 24/10/2026.',True)

class NumberedCanvas(canvas.Canvas):
    def __init__(self,*args,**kw): super().__init__(*args,**kw);self.saved=[]
    def showPage(self): self.saved.append(dict(self.__dict__));self._startPage()
    def save(self):
        total=len(self.saved)
        for state in self.saved:
            self.__dict__.update(state)
            self.setFillColor(GRAY);self.setFont('Sans',7.5)
            self.drawString(48,28,'27C256 + Mega 2560 | Manual de bancada | 24/10/2026')
            self.drawRightString(A4[0]-48,28,f'{self._pageNumber} / {total}')
            self.setStrokeColor(colors.HexColor('#cfdce5'));self.line(48,42,A4[0]-48,42)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def header(c,doc):
    c.saveState(); c.setFillColor(TEAL);c.rect(0,A4[1]-12,A4[0],12,fill=1,stroke=0)
    c.setFillColor(GRAY);c.setFont('Sans',7.5)
    c.drawString(48,A4[1]-34,'ST 27C256-30CQ • LEITURA / DIAGNÓSTICO / PROGRAMAÇÃO')
    c.restoreState()

doc=SimpleDocTemplate(str(OUT/'manual_eprom_27c256_mega.pdf'),pagesize=A4,
    leftMargin=48,rightMargin=48,topMargin=61,bottomMargin=58,
    title='EPROM 27C256 + Arduino Mega - teste, leitura e gravação',author='Manual de bancada')
doc.build(story,onFirstPage=header,onLaterPages=header,canvasmaker=NumberedCanvas)
# Marcadores de navegacao, sem alterar o conteudo das paginas.
from pypdf import PdfReader, PdfWriter
target=OUT/'manual_eprom_27c256_mega.pdf'
reader=PdfReader(target)
writer=PdfWriter()
writer.clone_document_from_reader(reader)
for label,page in [('Apresentação e validação',0),('1. Pinagem enviada',1),
 ('2. Ligação do leitor',2),('3. Alimentação e capacitores',3),
 ('4. Instalação e leitura USB',4),('5. Diagnóstico e vazio',5),
 ('6. Apagamento e imagem de teste',6),('7. Gravador: componentes',7),
 ('8. Interface de dados',8),('8b. Canais LM339',9),
 ('9. Controles e endereços',10),('10. Fontes manuais',11),
 ('11. Algoritmo ST',12),('12. Protocolo e arquivos',13),
 ('Apêndice A. Firmware Arduino completo',14),
 ('Apêndice B. Cliente Python completo',19),('Checklist, validação e fontes',23)]:
    writer.add_outline_item(label,page)
replacement=OUT/'manual_eprom_27c256_mega.tmp.pdf'
writer.write(replacement)
replacement.replace(target)
print(OUT/'manual_eprom_27c256_mega.pdf')
