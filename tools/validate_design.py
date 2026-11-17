"""Independent checks on KiCad's EXPORTED netlist, plus physical pad closure.
Run after kicad-cli sch export netlist --format kicadxml.
"""
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
import json, sys, csv, hashlib, math
from inspect_sources import parse, kids, one, val
ROOT=Path(__file__).resolve().parents[1]
NAME='DRC_POWER2026.ver.0.2.0'
CHECKS=[]
def check(name,condition,detail=''):
    CHECKS.append({'check':name,'pass':bool(condition),'detail':detail})
def main():
    tree=ET.parse(ROOT/'docs/main_power.net.xml')
    nets={};nodes={}
    for net in tree.findall('.//nets/net'):
        name=net.get('name');members={(n.get('ref'),n.get('pin')) for n in net.findall('node')}
        nodes[name]=members
        for k in members:nets[k]=name
    def k(s):return tuple(s.rsplit('.',1))
    def same(name,*ps):
        ns=[nets.get(k(p)) for p in ps]
        check(name,None not in ns and len(set(ns))==1,'; '.join(ps)+' -> '+str(ns[0]))
    def exact(name,*ps):
        same(name,*ps);ns=nets.get(k(ps[0]));check(name+' has no added components',nodes.get(ns)=={k(p) for p in ps},str(nodes.get(ns)))
    for i,rail,jbase,rbase,cbase in [(1,'3S',0,0,0),(2,'6S',3,10,10)]:
        raw=[f'J{jbase+1}.2',f'Q{i}.Tab',f'U{i}.2',f'R{rbase+2}.1',f'R{rbase+3}.1',f'C{cbase+1}.1',f'JP1.{1 if i==1 else 3}',f'R{51 if i==1 else 55}.1']
        if i==2:raw.append('C12.1')
        else:raw.append('J7.1')
        same(rail+' raw input',*raw)
        same(rail+' switched output',*[f'Q{i}.{p}' for p in range(2,9)],f'J{jbase+2}.2',f'J{jbase+3}.2',f'U{i}.9',f'C{cbase+3}.1',f'C{cbase+4}.1',f'R{rbase+8}.1',f'R{53 if i==1 else 57}.1')
        same(rail+' gate path',f'Q{i}.1',f'R{rbase+1}.1')
        same(rail+' gate slew capacitor',f'U{i}.10',f'R{rbase+1}.2',f'C{cbase+5}.1')
        same(rail+' SENSE resistor',f'U{i}.1',f'R{rbase+2}.2')
        same(rail+' UVLO divider',f'U{i}.4',f'R{rbase+3}.2',f'R{rbase+4}.1')
        same(rail+' TIMER',f'U{i}.7',f'C{cbase+6}.1')
        same(rail+' PGD to MCU',f'U{i}.8',f'R{rbase+6}.2',f'U7.{34 if i==1 else 38}')
        same(rail+' fixed grounds',f'U{i}.3',f'U{i}.6',f'R{rbase+4}.2',f'R{rbase+5}.2',f'C{cbase+5}.2',f'C{cbase+6}.2',f'J{jbase+1}.1',f'J{jbase+2}.1',f'J{jbase+3}.1','U7.8')
    same('Shared enable and two pulldowns','U1.5','U2.5','R5.1','R15.1','U6.3')
    same('Series optotransistors','U5.3','U6.4')
    same('MCU permit GPIO','U7.35','R24.1')
    same('MCU opto LED','R24.2','U6.1')
    same('NC loop return','J7.2','R23.1')
    same('Stop opto LED','R23.2','U5.1')
    same('Opto cathodes ground','U5.2','U6.2','U7.8')
    same('Buck VIN directly enables IC','JP1.2','U3.5','U3.4','C21.1','C22.1')
    same('Bootstrap CB','U3.1','C23.1')
    same('Bootstrap SW','U3.6','C23.2','L1.1')
    same('Buck output before ideal diode','L1.2','C24.1','C25.1','R21.1','U4.1','C26.1')
    same('Buck feedback divider','U3.3','R21.2','R22.1')
    same('5V OR node and CE','U4.6','U4.3','D2.1','C27.1','C28.1','U7.11','U7.39','U7.56','U7.21','U5.4','U10.17','U8.8','U8.7','U8.3','U9.8','U9.7','U9.3','J8.1')
    same('Unused ST grounded','U4.5','U4.2','U3.2','R22.2','U7.8')
    check('Ideal-diode NC is open',len(nodes[nets[('U4','4')]])==1)
    same('USB VBUS to diode anode','J9.A4','J9.A9','J9.B4','J9.B9','D2.2','C41.1','R43.1')
    same('USB D+','J9.A6','J9.B6','U7.19')
    same('USB D-','J9.A7','J9.B7','U7.18')
    same('USB CC1 termination','J9.A5','R41.1')
    same('USB CC2 termination','J9.B5','R42.1')
    same('USB sense divider','U7.16','R43.2','R44.1')
    same('USB CC and sense returns','R41.2','R42.2','R44.2','J9.S1','J9.A1','J9.A12','J9.B1','J9.B12','U7.8')
    same('USB LDO 3.3V output and VBATT','U7.20','C38.1','C39.1','U7.4')
    same('ADC positive references and power','U7.59','U7.55','U7.56','U7.11','C36.1','C37.1')
    same('ADC negative references and power','U7.58','U7.54','U7.57','U7.8','C36.2','C37.2')
    exact('VCL smoothing only','U7.5','C35.1')
    same('Reset pin pullup and pushbutton','U7.25','R31.2','SW1.1','J8.5')
    same('BOOT jumper and pullup','U7.26','R32.2','JP2.1')
    same('Reset and BOOT ground terminals','SW1.2','JP2.2','U7.8')
    same('NMI pulled high','U7.27','R33.2')
    same('SWD clock','U7.32','J8.3');same('SWD data','U7.33','J8.2')
    for idx in range(4):
        rt=51+idx*2;rb=rt+1;cap=51+idx;dz=7+idx;u=8+idx//2;sp=1 if idx%2==0 else 5;dp=2 if idx%2==0 else 6;mc=64-idx
        same(f'ADC{idx} divider and input switch',f'R{rt}.2',f'R{rb}.1',f'C{cap}.1',f'D{dz}.1',f'U{u}.{sp}')
        same(f'ADC{idx} filter and zener return',f'R{rb}.2',f'C{cap}.2',f'D{dz}.2','U7.8')
        exact(f'ADC{idx} switch-to-MCU / no pulldown',f'U{u}.{dp}',f'U7.{mc}')
    same('TMUX GND and exposed pads','U8.4','U8.9','U9.4','U9.9','U7.8')
    same('Display DIN','U7.36','U10.7','R61.2');same('Display SCLK','U7.37','U10.8','R62.2')
    dpins=[1,10,8,5,4,2,3,6]
    for i,p in enumerate(dpins):exact('Display SEG'+str(i+1),f'U10.{9+i}',*[f'DS{d}.{p}' for d in range(1,13)])
    for d,grid in enumerate([12,7,8,9,10,11,5,6,4,1,2,3],1):
        gpin=17+grid if grid<=11 else grid-11
        exact(f'Digit{d} DP cathode7 and A-G cathode9 to GRID{grid}',f'DS{d}.7',f'DS{d}.9',f'U10.{gpin}')
    # Check manufacturer terminal functions as well as the physical pin set.
    symbol_lib=parse((ROOT/'lib/DRC_Power.kicad_sym').read_text(encoding='utf-8'))
    display_symbol=next(s for s in kids(symbol_lib,'symbol') if s[1]=='OSL10326_LRA')
    display_names={str(val(p,'number')):str(val(p,'name')) for sub in kids(display_symbol,'symbol') for p in kids(sub,'pin')}
    for num,name in [('6','DP_A'),('7','DP_K'),('9','CC_AG')]:
        check('OSL manufacturer pin '+num+' function',display_names.get(num)==name,str(display_names.get(num)))
    rails=[nets[k(p)] for p in ['J1.2','J4.2','J2.2','J5.2','U4.6','U4.1','U7.8']]
    check('3S/6S raw, switched, buck, logic and GND are separate nets',len(set(rails))==len(rails),str(rails))
    manifest=json.loads((ROOT/'docs/schematic_manifest.json').read_text(encoding='utf-8'))
    comps={}
    for sh in manifest:
        for c in sh['components']:
            if c['ref'].startswith('#'):continue
            comps.setdefault(c['ref'],{'fp':c['fp'],'pins':set(),'value':c['value'],'mpn':c['mpn'],'dnp':c['dnp']})['pins'].update(c['pins'])
    check('Board component count',len(comps)==124,str(len(comps)))
    check('Exactly two single main MOSFETs',sorted(r for r in comps if r.startswith('Q'))==['Q1','Q2'])
    check('Optional second output capacitors are DNP',comps['C4']['dnp'] and comps['C14']['dnp'])
    values={'R3':'51.1k','R4':'9.1k','R13':'110k','R14':'9.1k','R1':'10 ','R11':'10 ','R2':'10k','R12':'10k','R5':'10k','R15':'10k','R6':'4.7k','R16':'4.7k','R21':'118k','R22':'22.1k','R23':'2.4k','R24':'1.5k','R41':'5.1k','R42':'5.1k','C5':'220n','C15':'220n','C6':'2.2u','C16':'2.2u'}
    for ref,v in values.items():check(ref+' specified constant',comps[ref]['value'].startswith(v),comps[ref]['value'])
    for i in range(4):
        check('ADC divider '+str(i)+' specified constants',comps[f'R{51+2*i}']['value']=='22k 0.1%' and comps[f'R{52+2*i}']['value']=='4.7k 0.1%')
    padreport=[]
    for ref,c in comps.items():
        p=ROOT/'lib/DRC_Power.pretty'/(c['fp'].split(':')[1]+'.kicad_mod')
        t=parse(p.read_text(encoding='utf-8'));ps={str(p[1]) for p in kids(t,'pad') if p[1]}
        passed=ps==c['pins'];check(ref+' symbol/footprint pin closure',passed,f'pins={sorted(c["pins"])}; pads={sorted(ps)}')
        padreport.append({'ref':ref,'mpn':c['mpn'],'footprint':c['fp'],'symbol_pins':';'.join(sorted(c['pins'])),'footprint_pads':';'.join(sorted(ps)),'result':'PASS' if passed else 'FAIL'})
    with (ROOT/'docs/PIN_PAD_AUDIT.csv').open('w',encoding='utf-8-sig',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(padreport[0]));w.writeheader();w.writerows(padreport)
    erc=json.loads((ROOT/'docs/ERC.json').read_text(encoding='utf-8'))
    v=[v for s in erc['sheets'] for v in s['violations']]
    check('ERC all severities and exclusions',len(v)==0,str(Counter(x['severity'] for x in v)))
    check('10 hierarchical sheets in ERC',len(erc['sheets'])==10)
    for ext in ['kicad_pro','kicad_pcb']:
        a=(ROOT/(NAME+'.'+ext)).read_bytes();b=(ROOT/'docs/original'/(NAME+'.'+ext)).read_bytes()
        check('Existing '+ext+' preserved byte-for-byte',a==b,hashlib.sha256(a).hexdigest())
    result={'checks':len(CHECKS),'passed':sum(c['pass'] for c in CHECKS),'failed':[c for c in CHECKS if not c['pass']],'results':CHECKS}
    (ROOT/'docs/CONNECTIVITY_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False,indent=2))
    return 0 if not result['failed'] else 1
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.exit(main())
