"""Importa somente trilhas/vias de SES; verifica que componentes nao moveram.
Alternativa para o binding KiCad7 cujo ImportSpecctraSES exige GUI.
"""
from pathlib import Path
import re, json
import pcbnew as k
OUT=Path(__file__).resolve().parents[1]
text=(OUT/'fontes/eprom27_rev01.ses').read_text()
tokens=re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()]+',text)
stack=[];root=None
for t in tokens:
    if t=='(':
        x=[]
        if stack:stack[-1].append(x)
        else:root=x
        stack.append(x)
    elif t==')':stack.pop()
    else:stack[-1].append(t[1:-1] if t.startswith('"') else t)
assert not stack
def find(node,key):
    return [x for x in node if isinstance(x,list) and x and x[0]==key]
routes=find(root,'routes')[0]
unit=find(routes,'resolution')[0]
assert unit[1]=='um'
scale=1/(1000*float(unit[2]))
def pos(x,y):return k.VECTOR2I(k.FromMM(float(x)*scale),k.FromMM(-float(y)*scale))
b=k.LoadBoard(str(OUT/'eprom27_rev01_nao_roteada.kicad_pcb'))
refs={fp.GetReference():fp for fp in b.GetFootprints()}
placement=find(root,'placement')[0]
for component in find(placement,'component'):
    for part in find(component,'place'):
        p=pos(part[2],part[3]);actual=refs[part[1]].GetPosition()
        assert abs(p.x-actual.x)<=10 and abs(p.y-actual.y)<=10,part
nets={n.GetNetname():n.GetNetCode() for n in b.GetNetInfo().NetsByNetcode().values()}
segments=vias=0
for net in find(find(routes,'network_out')[0],'net'):
    name=net[1]
    assert name in nets,name
    for wire in find(net,'wire'):
        path=find(wire,'path')[0];layer=k.F_Cu if path[1]=='F.Cu' else k.B_Cu
        assert path[1] in ('F.Cu','B.Cu')
        width=k.FromMM(float(path[2])*scale)
        pts=[pos(path[i],path[i+1]) for i in range(3,len(path),2)]
        for a,z in zip(pts,pts[1:]):
            if a==z:continue
            t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(z);t.SetLayer(layer)
            t.SetWidth(width);t.SetNetCode(nets[name]);b.Add(t);segments+=1
    for via in find(net,'via'):
        m=re.search(r'_(\d+):(\d+)_um$',via[1]);assert m,via
        v=k.PCB_VIA(b);v.SetPosition(pos(via[2],via[3]));v.SetWidth(k.FromMM(int(m[1])/1000))
        v.SetDrill(k.FromMM(int(m[2])/1000));v.SetViaType(k.VIATYPE_THROUGH)
        v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNetCode(nets[name]);b.Add(v);vias+=1
b.BuildConnectivity()
k.SaveBoard(str(OUT/'eprom27_rev01.kicad_pcb'),b)
print(f'Importados {segments} segmentos e {vias} vias.')
ok=k.WriteDRCReport(b,str(OUT/'drc_rev01.txt'),k.EDA_UNITS_MILLIMETRES,True)
print('DRC gerado:',ok)
