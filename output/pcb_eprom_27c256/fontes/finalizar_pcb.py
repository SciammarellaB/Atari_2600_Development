"""Anota UUIDs do esquema, configura bibliotecas locais e valida o PCB.
Nao modifica redes, trilhas ou posicoes dos componentes.
"""
from pathlib import Path
import os,json,csv,shutil,xml.etree.ElementTree as ET,re
import pcbnew as k
OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parents[1]
LIB=Path(os.environ['EPROM_FOOTPRINTS'])
X=Path(os.environ.get('EPROM_XML',str(OUT/'netlist.xml')))
libs={}
for row in csv.DictReader((OUT/'bom.csv').open()):
    lib,name=row['Biblioteca'],row['Footprint']
    dest=OUT/'footprints'/(lib+'.pretty');dest.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(LIB/(lib+'.pretty')/(name+'.kicad_mod'),dest/(name+'.kicad_mod'))
    libs[lib]=name
table='(fp_lib_table\n'+''.join(f'  (lib (name "{lib}")(type "KiCad")(uri "${{KIPRJMOD}}/footprints/{lib}.pretty")(options "")(descr "KiCad 7 library subset"))\n' for lib in sorted(libs))+')\n'
(OUT/'fp-lib-table').write_text(table)
# Um projeto com o mesmo nome da placa e do esquema.
pro=OUT/'eprom27_rev01.kicad_pro'
if not pro.exists():pro.write_text(json.dumps({'meta':{'filename':pro.name,'version':1}},indent=2))
schem=(OUT/'fontes/esquema_intermediario.kicad_sch').read_text()
(OUT/'eprom27_rev01.kicad_sch').write_text(schem.replace('(project "esquema"','(project "eprom27_rev01"'))
root_uuid=re.search(r'\(uuid ([0-9a-f-]+)\)',schem).group(1)
components={x.attrib['ref']:x for x in ET.parse(X).getroot().findall('./components/comp')}
b=k.LoadBoard(str(OUT/'eprom27_rev01.kicad_pcb'))
b.SetFileName(str(OUT/'eprom27_rev01.kicad_pcb'))
for fp in b.GetFootprints():
    ref=fp.GetReference()
    ident=fp.GetFPID()
    original=k.FootprintLoad(str(OUT/'footprints'/(str(ident.GetLibNickname())+'.pretty')),str(ident.GetLibItemName()))
    fp.Models().clear()
    for model in original.Models():fp.Models().push_back(model)
    if ref in components:
        instance=components[ref].findtext('tstamps').strip()
        fp.SetPath(k.KIID_PATH('/'+root_uuid+'/'+instance))
    if ref in ['H1','H2','H3','H4']:
        fp.Reference().SetPosition(fp.GetPosition()+k.VECTOR2I(0,k.FromMM(5 if fp.GetPosition().y<k.FromMM(70) else -5)))
    if ref=='J4':fp.Reference().SetPosition(k.VECTOR2I(k.FromMM(154),k.FromMM(125)))
for item in b.Drawings():
    if isinstance(item,k.PCB_TEXT) and item.GetText()=='J2 -> RP / +5M / GND':
        item.SetPosition(k.VECTOR2I(k.FromMM(180),k.FromMM(11)))
sm=k.GetSettingsManager();sm.LoadProject(str(pro));b.SetProject(sm.GetProject(str(pro)))
if not list(b.Zones()):
    zone=k.ZONE(b);zone.SetLayer(k.B_Cu);zone.SetNetCode(b.FindNet('GND').GetNetCode())
    zone.SetLocalClearance(k.FromMM(.25));zone.SetThermalReliefGap(k.FromMM(.3))
    zone.SetThermalReliefSpokeWidth(k.FromMM(.4));zone.SetMinThickness(k.FromMM(.25))
    zone.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
    poly=zone.Outline();poly.NewOutline()
    for x,y in [(.8,.8),(199.2,.8),(199.2,139.2),(.8,139.2)]:poly.Append(k.FromMM(x),k.FromMM(y))
    b.Add(zone)
filler=k.ZONE_FILLER(b)
print('Zone fill:',filler.Fill(b.Zones()))
b.BuildConnectivity();k.SaveBoard(str(OUT/'eprom27_rev01.kicad_pcb'),b)
print('DRC:',k.WriteDRCReport(b,str(OUT/'drc_rev01.txt'),k.EDA_UNITS_MILLIMETRES,True))
sm.SaveProject(str(pro))
