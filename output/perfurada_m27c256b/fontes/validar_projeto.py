"""Validacao estrutural; NAO e DRC, simulacao analogica ou ensaio de bancada."""
from pathlib import Path
from collections import defaultdict
import json,csv,re,xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parents[1]
C=json.loads((OUT/'contrato_eletrico.json').read_text());P=C['parts']
holes={};nodes=defaultdict(set);n=0
for ref,o in P.items():
    assert set(o['pins'])==set(o['holes']),ref
    for pin,net in o['pins'].items():
        n+=1;x,y=o['holes'][pin];key=(o['board'],x,y)
        assert key not in holes,(ref,pin,key);holes[key]=(ref,pin)
        assert 1<=x<=C['boards'][o['board']][0] and 1<=y<C['boards'][o['board']][1],(ref,pin,key)
        if net:nodes[(o['board'],net)].add(f'{ref}.{pin}')
graph=defaultdict(lambda:defaultdict(set));count=0;cable=0
def terminal(t):return t.split(' [')[0]
for row in csv.DictReader((OUT/'ligacoes_ponto_a_ponto.csv').open()):
    b,net=row['Placa'],row['Rede'];a=terminal(row['De']);z=terminal(row['Para'])
    if b=='A-B':
        cable+=1
        assert a.startswith('JA4.') and z.startswith('JB1.')
        pin=a.split('.')[1];assert z.split('.')[1]==pin and P['JA4']['pins'][pin]==net
        continue
    assert a in nodes[(b,net)] and (z in nodes[(b,net)] or z=='BARRA_GND'),row
    graph[(b,net)][a].add(z);graph[(b,net)][z].add(a);count+=1
for key,ends in nodes.items():
    start=next(iter(ends));seen={start};todo=[start]
    while todo:
        for z in graph[key][todo.pop()]-seen:seen.add(z);todo.append(z)
    assert ends<=seen,(key,ends-seen)
idx=list(csv.DictReader((OUT/'esquemas/indice_ligacoes.csv').open()))
validation=json.loads((OUT/'esquemas/validacao.json').read_text())
assert validation['componentes']==len(P) and validation['pinos']==n and validation['cobertura_exata_contrato']
assert len(idx)==n
indexed={(r['Referencia'],r['Pino']):(r['Rede'],r['Placa'],int(r['Coluna']),int(r['Linha'])) for r in idx}
expected={(ref,pin):(net or 'NC',o['board'],*o['holes'][pin]) for ref,o in P.items() for pin,net in o['pins'].items()}
assert indexed==expected,'Indice de esquemas diverge dos pinos/redes/furos do contrato'
for svg in list((OUT/'esquemas').glob('*.svg'))+list(OUT.glob('montagem_*.svg')):ET.parse(svg)
assert C['relay_states']=={'READ':[1,1,0,0],'PROGRAM':[0,0,0,1],'VERIFY_HIGH':[1,0,0,0],'VERIFY_LOW':[1,1,1,0]}
assert P['K4']['pins']['4']=='VPP' and P['K4']['pins']['6']=='VCC_EP' and P['K4']['pins']['8']=='+12P75'
assert P['DF4']['pins']['2']=='CLAMP_K4' and P['ZF4']['pins']['1']=='COIL4_PLUS'
assert P['JA4']['pins']==P['JB1']['pins']
assert P['QP9']['pins']['1']=='G9' and P['QP10']['pins']['1']=='G10'
assert P['UC2']['pins']['8']=='BUS_OE'
assert all(P[f'QS{i}']['pins']['2']=='+5M' for i in range(1,5))
for state,relays in C['relay_states'].items():
    v=6.25-sum(delta*energized for delta,energized in zip([.25,1,.8],relays))
    assert abs(v-{'READ':5,'PROGRAM':6.25,'VERIFY_HIGH':6,'VERIFY_LOW':4.2}[state])<1e-9
print(f'PASS {len(P)} referencias unicas, {n} terminais, zero sobreposicoes de furos.')
print(f'PASS {count} ligacoes internas e {cable} fios A-B: cobertura e continuidade do grafo.')
print(f'PASS {len(idx)} pinos nos esquemas; SVGs XML validos; estados e pinos criticos conferidos.')
print('LIMITES: nao verifica tensoes, corpos arbitrarios, comportamento analogico ou bancada.')
