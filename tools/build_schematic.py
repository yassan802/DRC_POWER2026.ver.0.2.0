"""Deterministic, project-local KiCad 9 schematic and library authoring.
Run with Python 3. Source and validation records are in docs/.
"""
from pathlib import Path
from copy import deepcopy
import json, re, uuid, math, csv, shutil, sys
from inspect_sources import parse, kids, one, val, Atom

ROOT=Path(__file__).resolve().parents[1]
KI=Path(r'C:/Users/yasum/AppData/Local/Programs/KiCad/9.0/share/kicad')
NAME='DRC_POWER2026.ver.0.2.0'
NS=uuid.UUID('3015ecaa-6c6b-4e4d-a799-7b5472b07efc')
def uid(key): return str(uuid.uuid5(NS,str(key)))
def A(s): return Atom(str(s))
def n(v): return A(f'{float(v):.4f}'.rstrip('0').rstrip('.') if float(v) else '0')
def node(k,*args): return [A(k),*args]
def enc(x):
    if isinstance(x,list):
        flat='('+' '.join(enc(i) for i in x)+')'
        if len(flat)<140 and '\n' not in flat:return flat
        return '('+enc(x[0])+'\n'+'\n'.join('  '+enc(i).replace('\n','\n  ') for i in x[1:])+'\n)'
    if isinstance(x,Atom):return str(x)
    return json.dumps(str(x),ensure_ascii=False)
def fx(size=1.27,just=None,hide=False,bold=False):
    f=node('font',node('size',n(size),n(size)))
    if bold:f.append(node('bold',A('yes')))
    e=node('effects',f)
    if just:e.append(node('justify',*[A(k) for k in just.split()]))
    if hide:e.append(node('hide',A('yes')))
    return e
def prop(key,value,x=0,y=0,hide=False,size=1.27,just=None):
    return node('property',key,value,node('at',n(x),n(y),A('0')),fx(size,just,hide))

SYMS={}; PINMAP={}; LIBLOG=[]; FPLOG=[]; BOM=[]; PINASSIGN=[]
def std(lib,name,new=None):
    key=new or name
    if key in SYMS:return key
    tree=parse((KI/'symbols'/f'{lib}.kicad_sym').read_text(encoding='utf-8'))
    by={x[1]:x for x in kids(tree,'symbol')}
    def resolve(nm):
        s=deepcopy(by[nm]); ext=one(s,'extends')
        if ext:
            base=resolve(ext[1]); basenm=base[1]
            base=[x for x in base if not(isinstance(x,list) and x and x[0] in ['property','extends'])]
            base.extend(kids(s,'property'))
            base[1]=nm
            for sub in kids(base,'symbol'):sub[1]=sub[1].replace(basenm+'_',nm+'_',1)
            s=base
        return s
    s=resolve(name);s[1]=key
    for sub in kids(s,'symbol'):sub[1]=sub[1].replace(name+'_',key+'_',1)
    SYMS[key]=s
    LIBLOG.append({'symbol':key,'origin':f'KiCad 9 {lib}:{name}','change':'project-local copy; instance values and footprints set in schematic'})
    return key
def rect(x1,y1,x2,y2):
    return node('rectangle',node('start',n(x1),n(y1)),node('end',n(x2),n(y2)),node('stroke',node('width',n(.254)),node('type',A('default'))),node('fill',node('type',A('background'))))
def pin(num,name,x,y,angle=0,typ='passive',length=5.08,hide=False):
    p=node('pin',A(typ),A('line'),node('at',n(x),n(y),n(angle)),node('length',n(length)),node('name',name,fx(1.1)),node('number',str(num),fx(1.1)))
    if hide:p.append(node('hide',A('yes')))
    return p
def custom(name,ref,w,h,pins,ds='',fp='',units=None):
    s=node('symbol',name,node('pin_names',node('offset',n(1.016))),node('in_bom',A('yes')),node('on_board',A('yes')),
           prop('Reference',ref,0,h/2+6),prop('Value',name,0,h/2+3),prop('Footprint',fp,hide=True),prop('Datasheet',ds,hide=True),prop('Description',name,hide=True))
    if units is None: units=[(w,h,pins)]
    for i,(uw,uh,ps) in enumerate(units,1):
        s.append(node('symbol',f'{name}_{i}_1',rect(-uw/2,uh/2,uw/2,-uh/2),*ps))
    SYMS[name]=s
    LIBLOG.append({'symbol':name,'origin':ds,'change':'created from manufacturer pin table; grouped by function; physical pin numbers retained'})
    return name
def fp_copy(lib,name,new=None):
    key=new or name;p=KI/'footprints'/f'{lib}.pretty'/f'{name}.kicad_mod'
    target=ROOT/'lib'/'DRC_Power.pretty'/f'{key}.kicad_mod'
    FPLOG.append({'footprint':key,'origin':f'KiCad 9 {lib}:{name}','change':'unmodified pad geometry; optional external 3D model omitted'})
    if target.exists():return 'DRC_Power:'+key
    s=p.read_text(encoding='utf-8')
    s=s.replace(f'(footprint "{name}"',f'(footprint "{key}"',1)
    # Omit installation-dependent 3D model paths from the portable library.
    t=parse(s); t=[x for x in t if not(isinstance(x,list) and x and x[0]=='model')]
    target.write_text(enc(t)+'\n',encoding='utf-8')
    return 'DRC_Power:'+key

def make_libraries():
    (ROOT/'lib'/'DRC_Power.pretty').mkdir(parents=True,exist_ok=True)
    for lib,name in [('Device','R_Small'),('Device','C_Small'),('Device','C_Polarized'),('Device','D_Zener_Small'),('Device','D_Schottky_Small'),('Device','LED_Small'),('Device','L'),('Isolator','LTV-817S'),('Jumper','SolderJumper_2_Open'),('Switch','SW_Push'),('Connector','USB_C_Receptacle_USB2.0_16P'),('power','GND'),('power','PWR_FLAG')]:std(lib,name)
    std('power','+5V','P5V_MCU')
    for p in kids(SYMS['P5V_MCU'],'property'):
        if p[1]=='Value':p[2]='+5V_MCU'
    for sub in kids(SYMS['P5V_MCU'],'symbol'):
        for p in kids(sub,'pin'):one(p,'name')[1]='+5V_MCU'
    # Main FET uses the standard MOSFET drawing, with physical terminals 1,2..8,Tab.
    std('Transistor_FET','Q_NMOS_GDS','IPT008N06NM5LF')
    s=SYMS['IPT008N06NM5LF']
    for sub in kids(s,'symbol'):
        for p in list(kids(sub,'pin')):
            num=val(p,'number')
            if num=='2':one(p,'number')[1]='Tab';one(p,'name')[1]='D/Tab'
            if num=='3':
                one(p,'number')[1]='2';one(p,'name')[1]='S(2-8)'
                for j in range(3,9):
                    z=deepcopy(p);one(z,'number')[1]=str(j);z.append(node('hide',A('yes')));sub.append(z)
    LIBLOG[-1]['change']='MOSFET graphic reused; gate=1, sources=2..8 stacked, drain=Tab per Infineon Rev 2.1 p1'
    custom('LM5060MMX_NOPB','U',40.64,35.56,[
        pin(2,'VIN',-10.16,22.86,270,'power_in'),pin(1,'SENSE',-2.54,22.86,270,'input'),
        pin(10,'GATE',5.08,22.86,270,'output'),pin(9,'OUT',12.7,22.86,270,'input'),
        pin(4,'UVLO',-25.4,5.08,0,'input'),pin(5,'EN',-25.4,-5.08,0,'input'),
        pin(8,'~{PGD}',25.4,5.08,180,'open_collector'),pin(7,'TIMER',25.4,-5.08,180,'input'),
        pin(3,'OVP',-10.16,-22.86,90,'input'),pin(6,'GND',5.08,-22.86,90,'power_in')],
        'https://www.ti.com/lit/ds/symlink/lm5060.pdf')
    custom('LMR51610XDBVR','U',30.48,25.4,[pin(5,'VIN',-20.32,7.62,0,'power_in'),pin(4,'EN',-20.32,0,0,'input'),
        pin(1,'CB',20.32,7.62,180,'passive'),pin(6,'SW',20.32,0,180,'power_out'),pin(3,'FB',20.32,-7.62,180,'input'),pin(2,'GND',0,-17.78,90,'power_in')],
        'https://www.ti.com/lit/ds/symlink/lmr51610.pdf')
    custom('LM66100DCKR','U',25.4,20.32,[pin(1,'VIN',-17.78,5.08,0,'power_in'),pin(6,'VOUT',17.78,5.08,180,'power_out'),
        pin(3,'~{CE}',-17.78,-5.08,0,'input'),pin(5,'ST',17.78,-5.08,180,'passive'),pin(2,'GND',0,-15.24,90,'power_in'),pin(4,'NC',0,15.24,270,'no_connect')],
        'https://www.ti.com/lit/ds/symlink/lm66100.pdf')
    custom('TMUX2821DSGR','U',30.48,30.48,[pin(1,'S1',-20.32,7.62,0,'passive'),pin(2,'D1',20.32,7.62,180,'passive'),
        pin(5,'S2',-20.32,-2.54,0,'passive'),pin(6,'D2',20.32,-2.54,180,'passive'),
        pin(7,'SEL1',-7.62,20.32,270,'input'),pin(3,'SEL2',7.62,20.32,270,'input'),pin(8,'VDD',0,20.32,270,'power_in'),
        pin(4,'GND',-5.08,-20.32,90,'power_in'),pin(9,'EP/GND',5.08,-20.32,90,'power_in')],
        'https://www.ti.com/lit/ds/symlink/tmux2821.pdf')
    custom('Power_Input_2','J',10.16,15.24,[pin(2,'+',10.16,3.81,180),pin(1,'-',10.16,-3.81,180)])
    custom('Power_Output_2','J',10.16,15.24,[pin(2,'+',-10.16,3.81,0),pin(1,'-',-10.16,-3.81,0)])
    custom('EMG_VH_2','J',15.24,15.24,[pin(1,'12V_SEND',-12.7,3.81,0),pin(2,'NC_RETURN',-12.7,-3.81,0)])
    custom('SWD_1x06','J',20.32,22.86,[pin(i,nm,-15.24,10.16-(i-1)*3.81,0) for i,nm in enumerate(['VTREF_5V','SWDIO','SWCLK','SWO','~{RESET}','GND'],1)])
    # Three units: supplies, system/USB, then GPIO. All 64 physical terminals appear once.
    power=[pin(11,'VCC',-12.7,25.4,270,'power_in'),pin(39,'VCC',0,25.4,270,'power_in'),pin(56,'AVCC0',12.7,25.4,270,'power_in'),
           pin(8,'VSS',-12.7,-25.4,90,'power_in'),pin(40,'VSS',0,-25.4,90,'power_in'),pin(57,'AVSS0',12.7,-25.4,90,'power_in'),
           pin(5,'VCL',-30.48,10.16,0,'passive'),pin(4,'VBATT',-30.48,-5.08,0,'power_in'),
           pin(59,'P010/VREFH0',30.48,10.16,180,'power_in'),pin(58,'P011/VREFL0',30.48,0,180,'power_in'),
           pin(55,'P012/VREFH',30.48,-10.16,180,'power_in'),pin(54,'P013/VREFL',30.48,-20.32,180,'power_in')]
    system=[pin(21,'VCC_USB_LDO',-10.16,33.02,270,'power_in'),pin(20,'VCC_USB/3V3_OUT',10.16,33.02,270,'power_out'),pin(17,'VSS_USB',0,-33.02,90,'power_in'),
            pin(25,'~{RES}',-35.56,20.32,0,'input'),pin(26,'P201/MD',-35.56,10.16,0,'input'),pin(27,'P200/NMI',-35.56,0,0,'input'),
            pin(18,'P915/USB_DM',35.56,20.32,180,'bidirectional'),pin(19,'P914/USB_DP',35.56,10.16,180,'bidirectional'),pin(16,'P407/USB_VBUS',35.56,0,180,'input'),
            pin(32,'P300/SWCLK',35.56,-10.16,180,'input'),pin(33,'P108/SWDIO',35.56,-20.32,180,'bidirectional'),
            pin(6,'P215/XCIN',-35.56,-10.16,0,'input'),pin(7,'P214/XCOUT',-35.56,-15.24,0,'input'),pin(9,'P213/XTAL',-35.56,-20.32,0,'bidirectional'),pin(10,'P212/EXTAL',-35.56,-25.4,0,'input')]
    used=[(64,'P000/AN000'),(63,'P001/AN001'),(62,'P002/AN002'),(61,'P003/AN003'),(35,'P110/MAIN_RUN'),(34,'P109/nPGD_3S'),(38,'P113/nPGD_6S'),(36,'P111/SEG_DIN'),(37,'P112/SEG_CLK'),(41,'P107/STATUS')]
    unused=[(1,'P400'),(2,'P401'),(3,'P402'),(12,'P411'),(13,'P410'),(14,'P409'),(15,'P408'),(22,'P206'),(23,'P205'),(24,'P204'),(28,'P304'),(29,'P303'),(30,'P302'),(31,'P301'),(42,'P106'),(43,'P105'),(44,'P104'),(45,'P103'),(46,'P102'),(47,'P101'),(48,'P100'),(49,'P500'),(50,'P501'),(51,'P502'),(52,'P015'),(53,'P014'),(60,'P004')]
    io=[pin(num,nm,-35.56,45.72-i*7.62,0,'bidirectional') for i,(num,nm) in enumerate(used)]
    io += [pin(num,nm,35.56,53.34-i*3.81,180,'bidirectional') for i,(num,nm) in enumerate(unused)]
    custom('R7FA4M1AB3CFM_AA0','U',50.8,40.64,[], 'https://www.renesas.com/en/document/dst/ra4m1-group-datasheet',units=[(50.8,40.64,power),(60.96,55.88,system),(60.96,116.84,io)])
    # OptoSupply LX p2: A..G share cathode9; the independent DP is A6/K7.
    # The original circuit incorrectly treated6/9 as common cathodes and7 as DP anode.
    # Reuse only the KiCad 9 standard drawing to avoid newer file-format fields.
    std('Display_Character','D148K','OSL10326_LRA')
    s=SYMS['OSL10326_LRA']
    segnums={'A':'1','B':'10','C':'8','D':'5','E':'4','F':'2','G':'3','DP':'6'}
    common_count=0
    for sub in kids(s,'symbol'):
        for r in kids(sub,'rectangle'):
            one(r,'start')[1]=n(-7.62);one(r,'end')[1]=n(7.62)
        for p in kids(sub,'pin'):
            p[1]=A('passive');nm=str(val(p,'name'))
            at=one(p,'at');at[1]=n(-10.16 if float(at[1])<0 else 10.16)
            if nm in segnums:
                one(p,'number')[1]=segnums[nm]
                if nm=='DP':one(p,'name')[1]='DP_A'
            elif nm=='CC':
                one(p,'number')[1]='7' if common_count==0 else '9'
                one(p,'name')[1]='DP_K' if common_count==0 else 'CC_AG'
                common_count+=1
    for p in kids(s,'property'):
        if p[1]=='Reference':p[2]='DS'
        elif p[1]=='Description':p[2]='OptoSupply OSL10326-LRA red display; A-G common cathode9; independent decimal-point anode6/cathode7'
        elif p[1]=='ki_fp_filters':p[2]='OSL10326_LRA*'
    LIBLOG[-1]['change']='Standard display graphic reused; A1 B10 C8 D5 E4 F2 G3 share CC_AG9; independent DP_A6/DP_K7 per OptoSupply Rev A.1.2 p2. Old DP7/CC6,9 wiring corrected. Body widened to15.24mm for legible polarity labels; electrical type passive.'
    custom('TM1640_SOP28','U',40.64,83.82,[pin(17,'VDD',0,46.99,270,'power_in'),pin(6,'VSS',0,-46.99,90,'power_in'),
        pin(7,'DIN',-25.4,33.02,0,'input'),pin(8,'SCLK',-25.4,25.4,0,'input')]+
        [pin(9+i,f'SEG{i+1}',25.4,35.56-i*3.81,180,'output') for i in range(8)]+
        [pin((18+i if i<11 else i-10),f'GRID{i+1}',-25.4,17.78-i*3.81,0,'open_collector') for i in range(16)],
        'https://akizukidenshi.com/goodsaffix/TM1640_V1.0_EN.PDF')

    fps={}
    for key,lib,name in [
        ('R0603','Resistor_SMD','R_0603_1608Metric'),('R0805','Resistor_SMD','R_0805_2012Metric'),
        ('C0603','Capacitor_SMD','C_0603_1608Metric'),('C0805','Capacitor_SMD','C_0805_2012Metric'),('C1206','Capacitor_SMD','C_1206_3216Metric'),('C1210','Capacitor_SMD','C_1210_3225Metric'),
        ('CP18','Capacitor_THT','CP_Radial_D18.0mm_P7.50mm'),('LM5060','Package_SO','MSOP-10_3x3mm_P0.5mm'),
        ('LMR','Package_TO_SOT_SMD','SOT-23-6'),('LM66100','Package_TO_SOT_SMD','SOT-363_SC-70-6'),
        ('TMUX','Package_SON','WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm'),('MCU','Package_QFP','LQFP-64_10x10mm_P0.5mm'),
        ('OPTO','Package_DIP','SMDIP-4_W9.53mm'),('TM1640','Package_SO','SOP-28_8.4x18.16mm_P1.27mm'),
        ('XT60M','Connector_AMASS','AMASS_XT60PW-M_1x02_P7.20mm_Horizontal'),('XT60F','Connector_AMASS','AMASS_XT60PW-F_1x02_P7.20mm_Horizontal'),
        ('XT30F','Connector_AMASS','AMASS_XT30PW-F_1x02_P2.50mm_Horizontal'),('VH','Connector_JST','JST_VH_B2P-VH_1x02_P3.96mm_Vertical'),
        ('USB','Connector_USB','USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'),('D_SCH','Diode_SMD','D_SOD-123F'),('D_Z','Diode_SMD','D_SOD-123'),
        ('LED','LED_SMD','LED_0603_1608Metric'),('JP','Jumper','SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'),
        ('RESET','Button_Switch_SMD','SW_SPST_EVQPE1'),('SWD','Connector_PinHeader_2.54mm','PinHeader_1x06_P2.54mm_Vertical')]:
        fps[key]=fp_copy(lib,name)
    # Physical source pins are not collapsed into a generic three-terminal footprint.
    key='IPT008N06NM5LF_PG_HSOF8';p=KI/'footprints/Package_TO_SOT_SMD.pretty/Infineon_PG-HSOF-8-1.kicad_mod'
    t=parse(p.read_text(encoding='utf-8'));t[1]=key
    t=[x for x in t if not(isinstance(x,list) and x and x[0]=='model')]
    for pd in list(kids(t,'pad')):
        if pd[1]=='2':
            t.remove(pd)
            for j in range(2,9):t.append(node('pad',str(j),A('smd'),A('rect'),node('at',n(-5.25),n(-4.2+(j-1)*1.2)),node('size',n(2.8),n(.8)),node('layers','F.Cu','F.Mask')))
        elif pd[1]=='3':pd[1]='Tab'
    for p in kids(t,'property'):
        if p[1]=='Value':p[2]='IPT008N06NM5LF'
    (ROOT/'lib/DRC_Power.pretty'/f'{key}.kicad_mod').write_text(enc(t)+'\n',encoding='utf-8')
    fps['FET']='DRC_Power:'+key
    FPLOG.append({'footprint':key,'origin':'KiCad Infineon_PG-HSOF-8-1 + Infineon Rev 2.1 pp1,10','change':'gate pad1; split source copper into physical pads2..8 on 1.20mm pitch; drain pad named Tab; paste geometry retained'})
    # OSL footprint: origin at body center, pin1 upper left viewed from the front.
    key='OSL10326_LRA_7x11_P2.00_W4.88'
    t=node('footprint',key,node('version',A('20241229')),node('generator','pcbnew'),node('layer','F.Cu'),node('descr','OptoSupply OSL10326-LRA, common cathode, 7x11x5mm; 2mm lead pitch; rows 4.88mm'),node('attr',A('through_hole')),
        node('fp_text',A('reference'),'REF**',node('at',n(0),n(-7)),node('layer','F.SilkS'),fx(1)),node('fp_text',A('value'),'OSL10326-LRA',node('at',n(0),n(7)),node('layer','F.Fab'),fx(1)))
    for layer,margin,width in [('F.Fab',0,.1),('F.SilkS',.15,.12),('F.CrtYd',.5,.05)]:
        t.append(node('fp_rect',node('start',n(-3.5-margin),n(-5.5-margin)),node('end',n(3.5+margin),n(5.5+margin)),node('stroke',node('width',n(width)),node('type',A('solid'))),node('fill',A('none')),node('layer',layer)))
    for j in range(1,11):
        x=-2.44 if j<=5 else 2.44;y=-4+(j-1)*2 if j<=5 else 4-(j-6)*2
        t.append(node('pad',str(j),A('thru_hole'),A('rect' if j==1 else 'circle'),node('at',n(x),n(y)),node('size',n(1.5),n(1.5)),node('drill',n(.8)),node('layers','*.Cu','*.Mask')))
    t.append(node('fp_circle',node('center',n(2.7),n(4.5)),node('end',n(3),n(4.5)),node('stroke',node('width',n(.12)),node('type',A('solid'))),node('fill',A('none')),node('layer','F.SilkS')))
    (ROOT/'lib/DRC_Power.pretty'/f'{key}.kicad_mod').write_text(enc(t)+'\n',encoding='utf-8');fps['DIGIT']='DRC_Power:'+key
    FPLOG.append({'footprint':key,'origin':'OptoSupply OSL10326 LX/IX Rev A.1.2 p2; original PCB pad order independently compared','change':'new centered footprint; body7x11, height5, pin pitch2, row spacing4.88, drill0.8 for 0.45mm lead; pad1 upper left'})
    key='CYA0650_33UH_6.6x7.2_CustomLand'
    t=node('footprint',key,node('version',A('20241229')),node('generator','pcbnew'),node('layer','F.Cu'),node('descr','SHOUHAN CYA0650-33UH; body6.6x7.2 H5max; contacts D1.5+/-0.5 E3.0+/-0.2; enlarged derived lands; nonpolar'),node('attr',A('smd')),
        node('fp_text',A('reference'),'REF**',node('at',n(0),n(-5)),node('layer','F.SilkS'),fx(1)),node('fp_text',A('value'),'CYA0650-33UH',node('at',n(0),n(5)),node('layer','F.Fab'),fx(1)))
    for layer,hx,hy,width in [('F.Fab',3.3,3.6,.1),('F.SilkS',3.45,3.75,.12),('F.CrtYd',4.3,4.1,.05)]:
        t.append(node('fp_rect',node('start',n(-hx),n(-hy)),node('end',n(hx),n(hy)),node('stroke',node('width',n(width)),node('type',A('solid'))),node('fill',A('none')),node('layer',layer)))
    for i,x in [(1,-2.1),(2,2.1)]:
        t.append(node('pad',str(i),A('smd'),A('roundrect'),node('at',n(x),n(0)),node('size',n(3.8),n(3.4)),node('layers','F.Cu','F.Mask'),node('roundrect_rratio',n(.08))))
        t.append(node('pad','',A('smd'),A('roundrect'),node('at',n(x),n(0)),node('size',n(3.0),n(1.8)),node('layers','F.Paste'),node('roundrect_rratio',n(.08))))
    (ROOT/'lib/DRC_Power.pretty'/f'{key}.kicad_mod').write_text(enc(t)+'\n',encoding='utf-8');fps['L1']='DRC_Power:'+key
    FPLOG.append({'footprint':key,'origin':'SHOUHAN CYA0650-33UH approval specification p2; linked in original specification','change':'new derived land: body6.6x7.2 H5; two enlarged3.8x3.4 copper pads at +/-2.1; separate3.0x1.8 paste apertures; nonpolar pad1/2 assigned. Manufacturer gives contact outline, not a recommended land pattern; PCBA review required.'})
    # PANJIT's FL recommended lands differ from the generic KiCad F lands.
    key='PANJIT_SS2040FL_SOD123FL'
    t=parse((ROOT/'lib/DRC_Power.pretty/D_SOD-123F.kicad_mod').read_text(encoding='utf-8'));t[1]=key
    t=[x for x in t if not(isinstance(x,list) and val(x,'layer')=='F.CrtYd')]
    for pd in kids(t,'pad'):
        if pd[1] in ['1','2']:
            pd[3]=A('rect');one(pd,'at')[1:3]=[n(-1.55 if pd[1]=='1' else 1.55),n(0)];one(pd,'size')[1:]=[n(1.15),n(1.22)]
            pd[:]=[z for z in pd if not(isinstance(z,list) and z and z[0]=='roundrect_rratio')]
    for p in kids(t,'property'):
        if p[1]=='Value':p[2]='SS2040FL'
    t.append(node('fp_rect',node('start',n(-2.4),n(-1.2)),node('end',n(2.4),n(1.2)),node('stroke',node('width',n(.05)),node('type',A('solid'))),node('fill',A('none')),node('layer','F.CrtYd')))
    (ROOT/'lib/DRC_Power.pretty'/f'{key}.kicad_mod').write_text(enc(t)+'\n',encoding='utf-8');fps['D_SCH']='DRC_Power:'+key
    FPLOG.append({'footprint':key,'origin':'PANJIT SS2020FL series Rev10S p3 recommended SOD-123FL land pattern','change':'derived from KiCad D_SOD-123F drawing; pad1=K pad2=A; exact recommended1.15x1.22 lands at +/-1.55,3.10mm centers; enlarged courtyard to4.8x2.4'})
    # Part-specific library defaults must be correct independently of instance
    # overrides, so a later insertion does not restore a generic pinout/footprint.
    defaults={
        'IPT008N06NM5LF':('IPT008N06NM5LF',fps['FET']),
        'LM5060MMX_NOPB':('LM5060MMX/NOPB',fps['LM5060']),
        'LMR51610XDBVR':('LMR51610XDBVR',fps['LMR']),
        'LM66100DCKR':('LM66100DCKR',fps['LM66100']),
        'TMUX2821DSGR':('TMUX2821DSGR',fps['TMUX']),
        'R7FA4M1AB3CFM_AA0':('R7FA4M1AB3CFM#AA0',fps['MCU']),
        'OSL10326_LRA':('OSL10326-LRA',fps['DIGIT']),
        'TM1640_SOP28':('TM1640',fps['TM1640']),
        'LTV-817S':('LTV-817S-TA1-C',fps['OPTO']),
        'USB_C_Receptacle_USB2.0_16P':('USB4105-GF-A',fps['USB']),
        'EMG_VH_2':('B2P-VH(LF)(SN)',fps['VH']),
        'SWD_1x06':('TSW-106-07-G-S',fps['SWD']),
        'D_Schottky_Small':('SS2040FL',fps['D_SCH']),
    }
    for name,(value,footprint) in defaults.items():
        for p in kids(SYMS[name],'property'):
            if p[1]=='Value':p[2]=value
            elif p[1]=='Footprint':p[2]=footprint
            elif p[1]=='Datasheet' and name=='OSL10326_LRA':p[2]='https://www.optosupply.com/uppic/2025822601151.pdf'
    return fps

class Sheet:
    def __init__(self,file,title,page,paper='A3',sid=None):
        self.file=file;self.title=title;self.page=page;self.paper=paper;self.uuid=sid or uid(file);self.items=[];self.used=set();self.count=0;self.ports={};self.components=[]
        self.path='/'+uid(NAME)+('/'+uid('sheet:'+file) if page>1 else '')
    def add(self,x):self.items.append(x);return x
    def id(self,kind):self.count+=1;return uid(f'{self.file}:{kind}:{self.count}')
    def wire(self,*pts):
        for a,b in zip(pts,pts[1:]):
            if a==b:continue
            self.add(node('wire',node('pts',node('xy',n(a[0]),n(a[1])),node('xy',n(b[0]),n(b[1]))),node('stroke',node('width',n(0)),node('type',A('default'))),node('uuid',self.id('wire'))))
    def dot(self,x,y):self.add(node('junction',node('at',n(x),n(y)),node('diameter',n(0)),node('color',n(0),n(0),n(0),n(0)),node('uuid',self.id('junction'))))
    def label(self,name,x,y,side='left',hier=False,typ='input'):
        if hier:
            self.ports[name]=typ
            item=node('hierarchical_label',name,node('shape',A(typ)),node('at',n(x),n(y),n(180 if side=='left' else 0)),fx(1.27,'right' if side=='left' else 'left'),node('uuid',self.id('hierlabel')))
        else:item=node('label',name,node('at',n(x),n(y),A('0')),fx(1.27,'right bottom' if side=='left' else 'left bottom'),node('uuid',self.id('label')))
        self.add(item)
    def text(self,text,x,y,size=1.27,bold=False):self.add(node('text',text,node('at',n(x),n(y),A('0')),fx(size,'left top',bold=bold),node('uuid',self.id('text'))))
    def heading(self,text,x=17.78,y=15.24):self.text(text,x,y,2.0,True)
    def sym(self,key,ref,value,x,y,fp='',mpn='',manufacturer='',ds='',unit=1,angle=0,dnp=False,show_value=True,assembly='PCBA',extra=None):
        self.used.add(key);u=SYMS[key]
        inst=node('symbol',node('lib_id','DRC_Power:'+key),node('at',n(x),n(y),n(angle)),node('unit',n(unit)),node('in_bom',A('no' if ref.startswith('#') else 'yes')),node('on_board',A('no' if ref.startswith('#') else 'yes')),node('dnp',A('yes' if dnp else 'no')),node('uuid',self.id(ref)))
        # Pin coordinates transform from symbol Cartesian space to schematic screen space.
        pins={};angs={};cs=math.cos(math.radians(angle));sn=math.sin(math.radians(angle))
        for sub in kids(u,'symbol'):
            m=re.search(r'_(\d+)_(\d+)$',sub[1])
            if not m or int(m[1]) not in [0,unit]:continue
            for p in kids(sub,'pin'):
                px,py,pa=map(float,one(p,'at')[1:]);num=str(val(p,'number'))
                pins[num]=(round(x+px*cs-py*sn,4),round(y-px*sn-py*cs,4));angs[num]=(pa+angle)%360
                inst.append(node('pin',num,node('uuid',self.id(ref+':'+num))))
        passive=key in ['R_Small','C_Small','C_Polarized','D_Zener_Small','D_Schottky_Small','LED_Small','L','SolderJumper_2_Open','SW_Push']
        if passive:
            horizontal_default=key in ['D_Zener_Small','D_Schottky_Small','LED_Small','SW_Push','SolderJumper_2_Open']
            horizontal=horizontal_default if angle%180==0 else not horizontal_default
            if not horizontal:rx,ry=x+3.81,y-1.5;vx,vy=x+3.81,y+1.5;just='right' if angle%360 in [90,180] else 'left'
            else:rx,ry=x,y-6.35;vx,vy=x,y-3.81;just=None
        else:
            coords=[float(one(p,'at')[2]) for sub in kids(u,'symbol') for p in kids(sub,'pin') if re.search(fr'_{unit}_\d+$',sub[1])]
            for sub in kids(u,'symbol'):
                if not re.search(fr'_[0{unit}]_\d+$',sub[1]):continue
                for rr in kids(sub,'rectangle'):
                    coords.extend([float(one(rr,'start')[2]),float(one(rr,'end')[2])])
            top=max(coords,default=10);rx,ry=x,y-top-6.35;vx,vy=x,y-top-3.81;just=None
        inst.extend([prop('Reference',ref,rx,ry,hide=ref.startswith('#'),size=1.27,just=just),prop('Value',value,vx,vy,hide=not show_value,size=1.27,just=just),prop('Footprint',fp,x,y,True),prop('Datasheet',ds,x,y,True)])
        for field in kids(inst,'property'):
            if field[1] in ['Reference','Value']:one(field,'at')[3]=n(90 if angle%180 else 0)
        attrs={'MPN':mpn,'Manufacturer':manufacturer,'Assembly':assembly}
        if extra:attrs.update(extra)
        known_lcsc={'LMR51610XDBVR':'C20539658','CYA0650-33UH':'C5189937','1206B475K500NT':'C29823','CC0603KRX7R9BB104':'C14663','CL31A226KAHNNNE':'C12891'}
        if mpn in known_lcsc:attrs['LCSC']=known_lcsc[mpn]
        for k,v in attrs.items():
            if v:inst.append(prop(k,v,x,y,True))
        inst.append(node('instances',node('project',NAME,node('path',self.path,node('reference',ref),node('unit',n(unit))))))
        self.add(inst)
        c={'ref':ref,'value':value,'mpn':mpn,'manufacturer':manufacturer,'fp':fp,'ds':ds,'dnp':dnp,'assembly':assembly,'sheet':self.file,'pins':pins,'angles':angs,'key':key,'unit':unit,'rating':attrs.get('Rating',''),'lcsc':attrs.get('LCSC','')}
        self.components.append(c)
        if not ref.startswith('#') and not any(b['ref']==ref for b in BOM):BOM.append(c)
        return c
    def nc(self,p):self.add(node('no_connect',node('at',n(p[0]),n(p[1])),node('uuid',self.id('NC'))))
    def netpin(self,c,num,name,length=7.62,side=None):
        p=c['pins'][str(num)];a=c['angles'][str(num)]
        # extend outward, opposite the pin's inward-facing direction
        dx=-math.cos(math.radians(a));dy=math.sin(math.radians(a));q=(round(p[0]+dx*length,4),round(p[1]+dy*length,4))
        self.wire(p,q)
        self.label(name,*q,side=side or ('left' if dx<-.1 else 'right'))
        return q
    def power(self,name,x,y):
        key='GND' if name=='GND' else 'P5V_MCU'
        return self.sym(key,'#PWR'+str(self.page*100+self.count),name,x,y,show_value=name!='GND')
    def gndpin(self,c,num,dy=5.08):
        p=c['pins'][str(num)];q=(p[0],p[1]+dy);self.wire(p,q);self.power('GND',*q)
    def p5pin(self,c,num,dy=5.08):
        p=c['pins'][str(num)];q=(p[0],p[1]-dy);self.wire(p,q);self.power('+5V_MCU',*q)
    def flag(self,x,y):return self.sym('PWR_FLAG','#FLG'+str(self.page*100+self.count),'PWR_FLAG',x,y,show_value=False)
    def write(self):
        # KiCad's saved graph uses wire endpoints at each T connection. Split
        # collinear segments at pins, labels, explicit junctions and wire ends.
        # Unmarked crossings of two wire interiors remain separate.
        points=set()
        for it in self.items:
            if it[0]=='wire':
                points.update(tuple(map(float,p[1:])) for p in one(it,'pts')[1:])
            elif it[0] in ['label','hierarchical_label','junction','no_connect']:
                points.add(tuple(map(float,one(it,'at')[1:3])))
            elif it[0]=='sheet':
                points.update(tuple(map(float,one(p,'at')[1:3])) for p in kids(it,'pin'))
        for c in self.components:points.update(c['pins'].values())
        wires=[];seen=set()
        for it in [i for i in self.items if i[0]=='wire']:
            a,b=[tuple(map(float,p[1:])) for p in one(it,'pts')[1:]]
            dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
            cuts=[(0,a),(1,b)]
            for p in points:
                t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den
                if 1e-7<t<1-1e-7 and abs((p[0]-a[0])*dy-(p[1]-a[1])*dx)<1e-5:cuts.append((t,p))
            cuts=sorted(set(cuts))
            for j,((_,aa),(_,bb)) in enumerate(zip(cuts,cuts[1:])):
                sig=tuple(sorted([aa,bb]))
                if sig in seen:continue
                seen.add(sig);z=deepcopy(it);one(z,'pts')[1:]=[node('xy',n(aa[0]),n(aa[1])),node('xy',n(bb[0]),n(bb[1]))];one(z,'uuid')[1]=uid(val(it,'uuid')+':'+str(j));wires.append(z)
        items=[i for i in self.items if i[0]!='wire']+wires
        libs=[]
        for key in sorted(self.used):
            c=deepcopy(SYMS[key]);c[1]='DRC_Power:'+key;libs.append(c)
        tree=node('kicad_sch',node('version',A('20250114')),node('generator','eeschema'),node('generator_version','9.0'),node('uuid',self.uuid),node('paper',self.paper),
            node('title_block',node('title',self.title),node('date','2026-11-17'),node('rev','1.2-sch1'),node('company','DRC POWER2026'),node('comment',A('1'),'Main power board / common GND / Spec Rev 1.2')),
            node('lib_symbols',*libs),*items)
        if self.page==1:tree.append(node('sheet_instances',node('path','/',node('page','1'))))
        (ROOT/self.file).write_text(enc(tree)+'\n',encoding='utf-8')

def setup():
    (ROOT/'docs'/'original').mkdir(exist_ok=True)
    for ext in ['kicad_pro','kicad_sch','kicad_pcb']:
        p=ROOT/(NAME+'.'+ext);backup=ROOT/'docs/original'/p.name
        if not backup.exists():shutil.copy2(p,backup)
    fps=make_libraries()
    return fps

def resistor(s,ref,value,x,y,f,angle=0,precise=False,power=False):
    code=value.replace('k','K').replace('.','K') if '.' in value and value.endswith('k') else value.upper()
    # Explicit Yageo order codes; resistance and tolerance are independently recorded.
    codes={'10':'10R','330':'330R','1k':'1K','1.5k':'1K5','2.4k':'2K4','4.7k':'4K7','5.1k':'5K1','9.1k':'9K1','10k':'10K','22k':'22K','22.1k':'22K1','51.1k':'51K1','100k':'100K','110k':'110K','118k':'118K','1M':'1M'}
    stem=('RT0603BRD07' if precise else ('RC0805FR-07' if power else 'RC0603FR-07'))
    return s.sym('R_Small',ref,value+(' 0.1%' if precise else ' 1%'),x,y,f['R0805' if power else 'R0603'],stem+codes[value]+'L','Yageo',
        'https://www.yageo.com/en/ProductSearch' ,angle=angle,extra={'Tolerance':'0.1%' if precise else '1%','Rating':'0.125W 150V' if power else ('0.1W 75V' if precise else '0.1W 75V')})
def cap(s,ref,value,x,y,f,kind='100n',angle=0,dnp=False):
    parts={
        '100n':('CC0603KRX7R9BB104','Yageo','C0603','50V X7R 10%'),
        '22u25':('CL31A226KAHNNNE','Samsung','C1206','25V X5R 10%'),
        '10u50':('CL31A106KBHNNNE','Samsung','C1206','50V X5R 10%'),
        '4u7_50':('1206B475K500NT','FH','C1206','50V X7R 10%'),
        '220n100':('C1206C224K1RACTU','KEMET','C1206','100V X7R 10%'),
        '2u2_10':('GRM21BR71A225KA01L','Murata','C0805','10V X7R 10%'),
        '4u7_10':('GRM188R61A475KE15D','Murata','C0603','10V X5R 10%'),
        '1u10':('GRM188R71A105KA61D','Murata','C0603','10V X7R 10%'),
        '47u10':('GRM32ER61A476KE20L','Murata','C1210','10V X5R 10%'),
        '3300u50':('50PX3300MEFC18X35.5','Rubycon','CP18','50V 20% 105C D18 H35.5 P7.5'),
    }
    mpn,maker,pkg,rating=parts[kind]
    ds='https://www.rubycon.co.jp/wp-content/uploads/catalog-aluminum/PX.pdf' if kind=='3300u50' else ('https://product.samsungsem.com/mlcc/'+mpn+'.do' if maker=='Samsung' else 'https://www.murata.com/en-us/products/capacitor/mlcc' if maker=='Murata' else 'https://www.yageo.com/en/ProductSearch' if maker=='Yageo' else 'https://www.kemet.com/' if maker=='KEMET' else 'https://www.fenghua.com/')
    return s.sym('C_Polarized' if kind=='3300u50' else 'C_Small',ref,value,x,y,f[pkg],mpn,maker,ds,angle=angle,dnp=dnp,assembly='Hand/THT' if kind=='3300u50' else 'PCBA',extra={'Rating':rating})
def ic(s,key,ref,value,x,y,f,pkg,maker,mpn=None,unit=1):
    return s.sym(key,ref,value,x,y,f[pkg],mpn or value,maker,val(SYMS[key],'Datasheet') or next((p[2] for p in kids(SYMS[key],'property') if p[1]=='Datasheet'),''),unit=unit)
def port_at_pin(s,c,num,name,typ='input',length=15.24):
    p=c['pins'][str(num)];a=c['angles'][str(num)];dx=-math.cos(math.radians(a));dy=math.sin(math.radians(a))
    q=(round(p[0]+dx*length,4),round(p[1]+dy*length,4));s.wire(p,q);s.label(name,*q,side='left' if dx<0 else 'right',hier=True,typ=typ)
    return q

def power_sheet(f,rail,page):
    is6=rail=='6S';i=1 if not is6 else 2;rbase=0 if not is6 else 10;cbase=0 if not is6 else 10;jbase=0 if not is6 else 3
    vin='VIN_'+rail;vout='VOUT_'+rail;pgd='nPGD_'+rail
    s=Sheet('02_Power_3S.kicad_sch' if not is6 else '03_Power_6S.kicad_sch',f'{rail} main power / LM5060',page)
    s.heading(f'{rail} MAIN POWER   |   '+('6S LiPo / 25.2V max / 40A continuous' if is6 else '3S LiPo / 12.6V max / 20A continuous'))
    s.text('80A for 2s is a validation requirement. Main output follows battery voltage.',17.78,23,1.27)
    ji=s.sym('Power_Input_2','J'+str(jbase+1),'XT60PW-M / INPUT',30.48,57.15,f['XT60M'],'XT60PW-M','AMASS','https://www.tme.eu/Document/b13629717d44ae038681dba08d18c0b6/XT60PW-M.pdf',assembly='Hand/THT',extra={'Pinout':'1=GND; 2=positive'})
    jo=s.sym('Power_Output_2','J'+str(jbase+2),'XT60PW-F / OUTPUT',355.6,57.15,f['XT60F'],'XT60PW-F','AMASS','https://www.tme.eu/Document/1191bc2fa3aee3c446e5a895fd8f7983/XT60PW-F.pdf',assembly='Hand/THT',extra={'Pinout':'1=GND; 2=positive'})
    jl=s.sym('Power_Output_2','J'+str(jbase+3),'XT30PW-F / P_LIGHT',355.6,105.41,f['XT30F'],'XT30PW-F','AMASS','https://www.china-amass.net/',assembly='Hand/THT',extra={'Pinout':'1=GND; 2=positive','Load':'Light branch; branch current must be below connector/wire rating'})
    q=s.sym('IPT008N06NM5LF','Q'+str(i),'IPT008N06NM5LF',165.1,55.88,f['FET'],'IPT008N06NM5LFATMA1','Infineon','https://www.infineon.com/assets/row/public/documents/24/49/infineon-ipt008n06nm5lf-datasheet-en.pdf',angle=90,extra={'Rating':'60V; 0.8mohm max at VGS=10V; one FET per rail'})
    yy=53.34
    s.wire(ji['pins']['2'],q['pins']['Tab'])
    s.wire(q['pins']['2'],(345.44,yy));s.wire((309.88,yy),(309.88,jl['pins']['2'][1]),jl['pins']['2']);s.dot(309.88,yy)
    s.wire((85.09,yy),(85.09,40.64));s.dot(85.09,yy);s.label(vin,85.09,40.64,hier=True,typ='output')
    s.wire((280.67,yy),(280.67,40.64));s.dot(280.67,yy);s.label(vout,280.67,40.64,hier=True,typ='output')
    s.flag(50.8,yy)
    for c in [ji,jo,jl]:s.gndpin(c,1,12.7)
    if not is6:
        s.flag(ji['pins']['1'][0],ji['pins']['1'][1]+6.35);s.dot(ji['pins']['1'][0],ji['pins']['1'][1]+6.35)
    cin=cap(s,'C'+str(cbase+1),'10u / 50V' if is6 else '22u / 25V',73.66,73.66,f,'10u50' if is6 else '22u25')
    s.wire((73.66,yy),cin['pins']['1']);s.dot(73.66,yy);s.gndpin(cin,2)
    if is6:
        cin2=cap(s,'C'+str(cbase+2),'10u / 50V',110.49,73.66,f,'10u50');s.wire((110.49,yy),cin2['pins']['1']);s.dot(110.49,yy);s.gndpin(cin2,2)
    for idx,x in enumerate([223.52,260.35]):
        c=cap(s,'C'+str(cbase+3+idx),'3300u / 50V'+(' DNP' if idx else ''),x,76.2,f,'3300u50',dnp=bool(idx));s.wire((x,yy),c['pins']['1']);s.dot(x,yy);s.gndpin(c,2,7.62)
    rg=resistor(s,'R'+str(rbase+1),'10',165.1,80.01,f);s.wire(q['pins']['1'],rg['pins']['1']);s.netpin(rg,2,'GATE_'+rail+'_DRV',7.62)
    # Drain-charge discharge indicator is always connected to the switched output.
    rl=resistor(s,'R'+str(rbase+8),'10k',295.91,109.22,f,power=True);s.netpin(rl,1,vout)
    led=s.sym('LED_Small','D4' if is6 else 'D1','LTST-C190KRKT',295.91,124.46,f['LED'],'LTST-C190KRKT','Lite-On','https://optoelectronics.liteon.com/',angle=90)
    s.wire(rl['pins']['2'],led['pins']['2']);s.gndpin(led,1)
    s.text('LED + 10k: residual-charge indication / slow discharge',216,140.97,1.1)

    u=ic(s,'LM5060MMX_NOPB','U'+str(i),'LM5060MMX/NOPB',142.24,185.42,f,'LM5060','Texas Instruments')
    s.netpin(u,2,vin,12.7)
    sense=resistor(s,'R'+str(rbase+2),'10k',139.7,132.08,f);s.wire(sense['pins']['2'],u['pins']['1']);s.netpin(sense,1,vin)
    s.netpin(u,9,vout,12.7)
    gp=u['pins']['10'];s.wire(gp,(gp[0],147.32),(185.42,147.32));s.label('GATE_'+rail+'_DRV',185.42,147.32,side='right')
    cg=cap(s,'C'+str(cbase+5),'220n / 100V',185.42,157.48,f,'220n100');s.wire((185.42,147.32),cg['pins']['1']);s.gndpin(cg,2)
    byp=cap(s,'C'+str(cbase+7),'100n / 50V',105.41,147.32,f);s.netpin(byp,1,vin);s.gndpin(byp,2)
    rt=resistor(s,'R'+str(rbase+3),'110k' if is6 else '51.1k',68.58,162.56,f);rb=resistor(s,'R'+str(rbase+4),'9.1k',68.58,200.66,f)
    uv=u['pins']['4'];s.netpin(rt,1,vin);s.wire(rt['pins']['2'],(68.58,uv[1]),rb['pins']['1']);s.wire((68.58,uv[1]),uv);s.dot(68.58,uv[1]);s.gndpin(rb,2)
    en=u['pins']['5'];s.wire(en,(93.98,en[1]));s.label('MAIN_EN',93.98,en[1],hier=True,typ='input')
    pd=resistor(s,'R'+str(rbase+5),'10k',104.14,210.82,f);s.wire((104.14,en[1]),pd['pins']['1']);s.dot(104.14,en[1]);s.gndpin(pd,2)
    s.gndpin(u,3,22.86);s.gndpin(u,6,22.86)
    ct=cap(s,'C'+str(cbase+6),'2.2u / 10V',213.36,210.82,f,'2u2_10');s.wire(u['pins']['7'],(213.36,u['pins']['7'][1]),ct['pins']['1']);s.gndpin(ct,2)
    pp=u['pins']['8'];s.wire(pp,(266.7,pp[1]));s.label(pgd,266.7,pp[1],side='right',hier=True,typ='output')
    pu=resistor(s,'R'+str(rbase+6),'4.7k',238.76,160.02,f);s.p5pin(pu,1);s.wire(pu['pins']['2'],(238.76,pp[1]));s.dot(238.76,pp[1])
    s.text('EXTERNAL FUSE (off PCB): '+('0498060.M / 60A' if is6 else '0498040.M / 40A')+' + holder 04980921GXM5',17.78,238.76,1.27,True)
    s.text('Fuse is near the battery, before INPUT. No reverse-polarity protection. Body diode permits output-to-battery current.',17.78,246.38,1.27)
    s.text('UVLO: '+('110k / 9.1k; OFF ~19.19V, ON ~21.55V typ.' if is6 else '51.1k / 9.1k; OFF ~9.67V, ON ~10.87V typ.')+'  OVP grounded. OUT directly senses the source.',17.78,254,1.27)
    s.text('MAIN_EN has one 10k pulldown on each power sheet: 5k total. Verify FET SOA, OUT-pin current and stop time <=500ms.',17.78,261.62,1.27)
    s.text('Second 3300u footprint is DNP by default; populate for 6600u nominal. No maximum startup-time requirement.',17.78,269.24,1.27)
    return s

def control_power(f):
    std('Jumper','SolderJumper_3_Bridged12')
    f['SELECT']=fp_copy('Jumper','SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm')
    s=Sheet('04_Control_5V.kicad_sch','Control power / 5V buck and ideal diode',4)
    s.heading('CONTROL POWER   |   LMR51610 400kHz PFM / 1A maximum load')
    s.text('Supply is tapped before the main FETs. Default solder bridge: 3S. Cut 1-2 before bridging 2-3 for 6S.',17.78,25.4)
    jp=s.sym('SolderJumper_3_Bridged12','JP1','3S SELECT 6S',50.8,60.96,f['SELECT'],'PCB_SOLDER_SELECTOR_3PAD','PCB','',assembly='PCB copper + solder',extra={'Default':'Bridge1-2 (3S); never bridge both sides'})
    port_at_pin(s,jp,1,'VIN_3S','input',15.24);port_at_pin(s,jp,3,'VIN_6S','input',15.24)
    s.netpin(jp,2,'BUCK_VIN',10.16)
    u=ic(s,'LMR51610XDBVR','U3','LMR51610XDBVR',142.24,96.52,f,'LMR','Texas Instruments')
    vp=u['pins']['5'];ep=u['pins']['4'];s.wire(vp,(60.96,vp[1]));s.label('BUCK_VIN',60.96,vp[1]);s.flag(66.04,vp[1])
    s.wire(ep,(116.84,ep[1]),(116.84,vp[1]));s.dot(116.84,vp[1])
    for c,x,kind,value in [('C21',78.74,'4u7_50','4.7u / 50V'),('C22',106.68,'100n','100n / 50V')]:
        cc=cap(s,c,value,x,109.22,f,kind);s.wire((x,vp[1]),cc['pins']['1']);s.dot(x,vp[1]);s.gndpin(cc,2)
    s.gndpin(u,2,12.7)
    cb=cap(s,'C23','100n / 50V',182.88,u['pins']['1'][1],f,angle=90)
    s.wire(u['pins']['1'],cb['pins']['1']);s.wire(cb['pins']['2'],(193.04,cb['pins']['2'][1]),(193.04,u['pins']['6'][1]));s.dot(193.04,u['pins']['6'][1])
    l=s.sym('L','L1','33u / CYA0650-33UH',218.44,96.52,f['L1'],'CYA0650-33UH','SHOUHAN','https://xonstorage.z8.web.core.windows.net/pdf/shou_cya065033uh_apr22_xonlink.pdf',angle=90,extra={'Rating':'2.3A; Isat3A; DCR0.20ohm max; 6.6x7.2x5mm'})
    s.wire(u['pins']['6'],l['pins']['1']);s.wire(l['pins']['2'],(337.82,96.52));s.label('+5V_BUCK',337.82,96.52,side='right');s.flag(233.68,96.52)
    for ref,x in [('C24',251.46),('C25',290.83)]:
        c=cap(s,ref,'22u / 25V',x,114.3,f,'22u25');s.wire((x,96.52),c['pins']['1']);s.dot(x,96.52);s.gndpin(c,2,7.62)
    rt=resistor(s,'R21','118k',330.2,119.38,f);rb=resistor(s,'R22','22.1k',330.2,149.86,f)
    s.wire((330.2,96.52),rt['pins']['1']);s.dot(330.2,96.52);fb=(330.2,134.62);s.wire(rt['pins']['2'],fb,rb['pins']['1']);s.dot(*fb);s.gndpin(rb,2)
    s.wire(fb,(193.04,134.62),(193.04,u['pins']['3'][1]),u['pins']['3']);s.text('FB senses BEFORE LM66100',209.55,137.16,1.1)
    s.text('VOUT = 0.8 x (1 + 118k/22.1k) = 5.071V nominal. Static tolerance estimate 4.91 to 5.24V.',17.78,157.48)

    d=ic(s,'LM66100DCKR','U4','LM66100DCKR',238.76,200.66,f,'LM66100','Texas Instruments')
    s.netpin(d,1,'+5V_BUCK',22.86);s.gndpin(d,2,7.62);s.gndpin(d,5,12.7)
    vo=d['pins']['6'];s.wire(vo,(314.96,vo[1]));s.power('+5V_MCU',314.96,vo[1])
    ce=d['pins']['3'];s.wire(ce,(203.2,ce[1]),(203.2,233.68),(314.96,233.68),(314.96,vo[1]));s.dot(314.96,vo[1])
    ci=cap(s,'C26','100n / 50V',172.72,208.28,f);s.netpin(ci,1,'+5V_BUCK');s.gndpin(ci,2)
    co=cap(s,'C27','4.7u / 10V',340.36,213.36,f,'4u7_10');s.p5pin(co,1);s.gndpin(co,2)
    bulk=cap(s,'C28','47u / 10V',375.92,213.36,f,'47u10');s.p5pin(bulk,1);s.gndpin(bulk,2)
    s.text('CE = VOUT: reverse-current blocking. ST to GND, NC open. USB VBUS joins +5V_MCU through SS2040FL on sheet 9.',17.78,246.38)
    s.text('CBOOT is CB-to-SW. EN is tied directly to VIN. No external rectifier. Do not sense feedback at +5V_MCU.',17.78,254)
    s.text('Budget includes MCU, TMUX, display and optocouplers. Check USB-only voltage/current separately; see design report.',17.78,261.62)
    return s

def estop(f):
    s=Sheet('05_Emergency_Stop.kicad_sch','NC emergency stop / shared enable',5,'A4')
    s.heading('EMERGENCY STOP   |   two optotransistors in series')
    s.text('NC switch opens on STOP or cable break. Both optocoupler LEDs must be ON to enable both rails.',17.78,25.4)
    j=s.sym('EMG_VH_2','J7','EMG / B2P-VH(LF)(SN)',66.04,60.96,f['VH'],'B2P-VH(LF)(SN)','JST','https://www.jst-mfg.com/product/pdf/eng/eVH.pdf',assembly='Hand/THT',extra={'Mating':'VHR-2N + SVH-21T-P1.1','Pinout':'1=3S input positive; 2=NC loop return'})
    p=j['pins']['1'];s.wire(p,(25.4,p[1]));s.label('VIN_3S',25.4,p[1],hier=True,typ='input')
    s.text('External NC contact\nbetween J7.1 and J7.2',21.59,76.2,1.27)
    u5=s.sym('LTV-817S','U5','LTV-817S-TA1-C',165.1,86.36,f['OPTO'],'LTV-817S-TA1-C','Lite-On','https://optoelectronics.liteon.com/',extra={'CTR':'C rank 200-400% at IF=5mA, VCE=5V'})
    u6=s.sym('LTV-817S','U6','LTV-817S-TA1-C',165.1,129.54,f['OPTO'],'LTV-817S-TA1-C','Lite-On','https://optoelectronics.liteon.com/',extra={'CTR':'C rank 200-400% at IF=5mA, VCE=5V'})
    ra=resistor(s,'R23','2.4k',111.76,u5['pins']['1'][1],f,angle=90,power=True)
    s.wire(j['pins']['2'],(45.72,j['pins']['2'][1]),(45.72,96.52),(91.44,96.52),(91.44,ra['pins']['1'][1]),ra['pins']['1']);s.wire(ra['pins']['2'],u5['pins']['1']);s.gndpin(u5,2,12.7)
    rm=resistor(s,'R24','1.5k',111.76,u6['pins']['1'][1],f,angle=90)
    s.wire(rm['pins']['1'],(35.56,rm['pins']['1'][1]));s.label('MCU_RUN',35.56,rm['pins']['1'][1],hier=True,typ='input');s.wire(rm['pins']['2'],u6['pins']['1']);s.gndpin(u6,2,12.7)
    s.p5pin(u5,4,15.24);s.wire(u5['pins']['3'],u6['pins']['4']);s.wire(u6['pins']['3'],(248.92,u6['pins']['3'][1]));s.label('MAIN_EN',248.92,u6['pins']['3'][1],side='right',hier=True,typ='output')
    s.text('1=C_A / LED anode\n2=C_K / LED cathode\n3=Emitter, 4=Collector',200.66,58.42,1.27)
    s.text('MAIN_EN: 10k pulldown on EACH LM5060 sheet (5k total). No EN series resistor.',17.78,157.48)
    s.text('Without 3S, the NC-loop LED is OFF even with 6S or USB control power.',17.78,165.1)
    s.text('Firmware: set output latch LOW before enabling GPIO output; permit HIGH only after checks.',17.78,172.72)
    s.text('No extra GPIO pulldown. Verify actual IF/CTR and contact-to-FET OFF <=500ms.',17.78,180.34)
    return s

def mcu_core(f):
    s=Sheet('06_MCU_Core.kicad_sch','RA4M1 / supplies USB boot reset and debug',6)
    s.heading('RA4M1 CORE   |   R7FA4M1AB3CFM#AA0 / 64-pin LQFP / 5V I/O')
    a=ic(s,'R7FA4M1AB3CFM_AA0','U7','R7FA4M1AB3CFM#AA0',86.36,83.82,f,'MCU','Renesas',unit=1)
    b=ic(s,'R7FA4M1AB3CFM_AA0','U7','R7FA4M1AB3CFM#AA0',271.78,88.9,f,'MCU','Renesas',unit=2)
    for num in [11,39,56]:s.p5pin(a,num,10.16)
    for num in [8,40,57]:s.gndpin(a,num,10.16)
    s.netpin(a,5,'VCL_CORE',7.62);s.netpin(a,4,'USB_3V3',7.62)
    for num in [59,55]:
        p=a['pins'][str(num)];q=(p[0]+(20.32 if num==55 else 7.62),p[1]);s.wire(p,q);s.power('+5V_MCU',*q)
    for num in [58,54]:
        p=a['pins'][str(num)];q=(p[0]+7.62,p[1]);s.wire(p,q);s.wire(q,(q[0],q[1]+5.08));s.power('GND',q[0],q[1]+5.08)
    s.text('VREFH0/59 = +5V_MCU, VREFL0/58 = GND.\nDAC reference pins55/54 also tied to valid rails.\nOriginal floating ADC-reference node is corrected.',17.78,121.92)
    for ref,x,kind,value,note in [('C31',25.4,'100n','100n / 50V','U7.11'),('C32',63.5,'100n','100n / 50V','U7.39'),('C33',101.6,'100n','100n / 50V','U7.56'),('C34',139.7,'4u7_10','4.7u / 10V','5V bulk')]:
        c=cap(s,ref,value,x,162.56,f,kind);s.p5pin(c,1);s.gndpin(c,2);s.text(note,x-3.81,177.8,1.1)
    cv=cap(s,'C35','4.7u / 10V',25.4,208.28,f,'4u7_10');s.netpin(cv,1,'VCL_CORE');s.gndpin(cv,2)
    cr=cap(s,'C36','1u / 10V',76.2,208.28,f,'1u10');s.p5pin(cr,1);s.gndpin(cr,2)
    cd=cap(s,'C37','100n / 50V',127,208.28,f);s.p5pin(cd,1);s.gndpin(cd,2)
    s.text('C35: VCL only\nC36: ADC reference\nC37: DAC reference',17.78,232.41,1.1)

    s.p5pin(b,21,10.16);s.netpin(b,20,'USB_3V3',12.7);s.gndpin(b,17,12.7)
    for ref,x,kind,value,net in [('C38',350.52,'4u7_10','4.7u / 10V','USB_3V3'),('C39',388.62,'100n','100n / 50V','USB_3V3')]:
        c=cap(s,ref,value,x,43.18,f,kind);s.netpin(c,1,net);s.gndpin(c,2)
    c=cap(s,'C40','100n / 50V',350.52,132.08,f);s.p5pin(c,1);s.gndpin(c,2);s.text('U7.21 USB-LDO bypass',333,147.32,1.1)
    port_at_pin(s,b,18,'USB_D_N','bidirectional',17.78);port_at_pin(s,b,19,'USB_D_P','bidirectional',17.78);port_at_pin(s,b,16,'USB_VBUS_SENSE','input',17.78)
    for num,net in [(25,'RESET_N'),(26,'BOOT_MD'),(27,'NMI_HIGH'),(32,'SWCLK'),(33,'SWDIO')]:s.netpin(b,num,net,10.16)
    for num in [6,7,9,10]:s.nc(b['pins'][str(num)])
    s.text('USB device: 48MHz HOCO / USBCKCR.USBCLKSEL=1.\nEnable USB LDO; USB_3V3 is its output, not a 5V rail.\nVBATT stays on USB_3V3 as in the reference circuit.',209.55,137.16,1.27)

    for ref,net,x in [('R31','RESET_N',200.66),('R32','BOOT_MD',241.3),('R33','NMI_HIGH',281.94)]:
        r=resistor(s,ref,'5.1k',x,187.96,f);s.p5pin(r,1);s.netpin(r,2,net)
    sw=s.sym('SW_Push','SW1','RESET / EVQ-PE105K',200.66,226.06,f['RESET'],'EVQ-PE105K','Panasonic','https://industrial.panasonic.com/',angle=270,assembly='PCBA')
    s.netpin(sw,1,'RESET_N');s.gndpin(sw,2)
    boot=s.sym('SolderJumper_2_Open','JP2','BOOT / open=RUN',254,224.79,f['JP'],'PCB_SOLDER_BOOT_2PAD','PCB','',angle=270,assembly='PCB copper + solder')
    s.netpin(boot,1,'BOOT_MD');s.gndpin(boot,2)
    j=s.sym('SWD_1x06','J8','SWD / 5V TARGET',363.22,195.58,f['SWD'],'TSW-106-07-G-S','Samtec','https://www.samtec.com/products/tsw',assembly='Hand/THT')
    s.p5pin(j,1);s.netpin(j,2,'SWDIO');s.netpin(j,3,'SWCLK');s.nc(j['pins']['4']);s.netpin(j,5,'RESET_N');s.gndpin(j,6)
    s.text('J8.4 SWO not routed.\nUse a debugger compatible\nwith 5V target signals.',332.74,228.6,1.1)
    s.text('Place 100n at each VCC/AVCC and USB supply pin. Place C35 at VCL. Keep analog and switching-current return paths separate.',17.78,260.35)
    s.text('Boot: close JP2 to GND and reset to enter ROM boot; open JP2 for normal operation. U7 unit C is on sheet 7.',17.78,267.97)
    return s

def mcu_io(f):
    s=Sheet('07_MCU_IO.kicad_sch','RA4M1 / ADC and control pin assignment',7)
    s.heading('RA4M1 I/O   |   ADC inputs and shared run permission')
    u=ic(s,'R7FA4M1AB3CFM_AA0','U7','R7FA4M1AB3CFM#AA0',177.8,114.3,f,'MCU','Renesas',unit=3)
    assignments=[(64,'ADC_VIN_3S','AN000 / ADC14','input'),(63,'ADC_VOUT_3S','AN001 / ADC14','input'),(62,'ADC_VIN_6S','AN002 / ADC14','input'),(61,'ADC_VOUT_6S','AN003 / ADC14','input'),
                 (35,'MCU_RUN','P110 GPIO push-pull HIGH=permit','output'),(34,'nPGD_3S','P109 GPIO input active-low status','input'),(38,'nPGD_6S','P113 GPIO input active-low status','input'),
                 (36,'SEG_DIN','P111 GPIO output','output'),(37,'SEG_CLK','P112 GPIO output','output')]
    for num,net,func,direction in assignments:
        port_at_pin(s,u,num,net,direction,25.4)
        PINASSIGN.append({'signal':net,'pin':num,'port':next(val(p,'name').split('/')[0] for sub in kids(SYMS[u['key']],'symbol') for p in kids(sub,'pin') if val(p,'number')==str(num)),'function':func,'electrical':'0..AVCC0; analog input' if net.startswith('ADC_') else '5V logic; common +5V_MCU'})
    s.netpin(u,41,'STATUS_LED',25.4)
    used={str(i[0]) for i in assignments}|{'41'}
    for num,p in u['pins'].items():
        if num not in used:s.nc(p)
    for ref,net,x in [('R38','+5V_MCU',299.72),('R40','STATUS_LED',355.6)]:
        r=resistor(s,ref,'1k',x,88.9,f)
        if ref=='R38':s.p5pin(r,1)
        else:s.netpin(r,1,net)
        d=s.sym('LED_Small','D5' if ref=='R38' else 'D6','LTST-C190KRKT',x,111.76,f['LED'],'LTST-C190KRKT','Lite-On','https://optoelectronics.liteon.com/',angle=90)
        s.wire(r['pins']['2'],d['pins']['2']);s.gndpin(d,1)
    PINASSIGN.append({'signal':'STATUS_LED','pin':41,'port':'P107','function':'GPIO output HIGH=LED on','electrical':'5V logic; 1k + red LED'})
    s.text('RUN PERMISSION',276.86,142.24,1.52,True)
    s.text('1. Set P110 output latch LOW.\n2. Configure P110 as an output.\n3. Check ADC, PGD and firmware state.\n4. Set P110 HIGH to request both rails ON.\nAny firmware STOP sets P110 LOW.',276.86,152.4)
    s.text('ADC: 3.2V/cell stop; 3.4V/cell permits recovery.\nEach LM5060 still waits for its own UVLO ON threshold.\nnPGD_3S and nPGD_6S are independent status inputs.',17.78,203.2)
    s.text('ADC14: AN000..AN003, analog mode, digital buffers OFF. Use actual reference calibration and a sampling time suited to 3.873k source impedance.',17.78,228.6)
    s.text('No current measurement. No added ADC-side pulldowns. No added MCU_RUN pulldown. Unused GPIO are explicitly marked NC.',17.78,238.76)
    s.text('Firmware defines time filtering, recovery delay, fault retry and display content. See docs/MCU_PIN_ASSIGNMENT.csv.',17.78,248.92)
    return s

def adc(f):
    s=Sheet('08_ADC_Protection.kicad_sch','Four voltage dividers / powered-off ADC protection',8)
    s.heading('VOLTAGE MEASUREMENT   |   22k / 4.7k, 0.1% / 100n / 5.1V zener / TMUX2821')
    s.text('Divider gain 0.17603. 12.6V -> 2.218V; 25.2V -> 4.436V. Return all divider bottoms to a quiet common GND.',17.78,25.4)
    for row,rail in enumerate(['3S','6S']):
        yoff=row*111.76
        for col,point in enumerate(['VIN','VOUT']):
            idx=row*2+col;x=43.18+col*111.76;net=point+'_'+rail;raw='VDIV_'+rail+'_'+('IN' if point=='VIN' else 'OUT')
            rt=resistor(s,'R'+str(51+idx*2),'22k',x,62.23+yoff,f,precise=True)
            rb=resistor(s,'R'+str(52+idx*2),'4.7k',x,102.87+yoff,f,precise=True)
            p=rt['pins']['1'];s.wire(p,(x,43.18+yoff));s.label(net,x,43.18+yoff,hier=True,typ='input')
            mid=(x,82.55+yoff);s.wire(rt['pins']['2'],mid,rb['pins']['1']);s.dot(*mid);s.gndpin(rb,2)
            cf=cap(s,'C'+str(51+idx),'100n / 50V',x+31.75,102.87+yoff,f);s.wire(mid,(x+62.23,mid[1]));s.wire((x+31.75,mid[1]),cf['pins']['1']);s.dot(x+31.75,mid[1]);s.gndpin(cf,2)
            dz=s.sym('D_Zener_Small','D'+str(7+idx),'BZT52C5V1-7-F',x+62.23,102.87+yoff,f['D_Z'],'BZT52C5V1-7-F','Diodes Incorporated','https://www.diodes.com/assets/Datasheets/ds18004.pdf',angle=270,extra={'Rating':'5.1V nominal; existing zener-to-GND topology retained'})
            s.wire((x+62.23,mid[1]),dz['pins']['1']);s.gndpin(dz,2);s.label(raw,x+62.23,mid[1],side='right')
        u=ic(s,'TMUX2821DSGR','U'+str(8+row),'TMUX2821DSGR',330.2,99.06+yoff,f,'TMUX','Texas Instruments')
        for num,name in [(1,'VDIV_'+rail+'_IN'),(5,'VDIV_'+rail+'_OUT')]:s.netpin(u,num,name,12.7)
        for num,name in [(2,'ADC_VIN_'+rail),(6,'ADC_VOUT_'+rail)]:port_at_pin(s,u,num,name,'output',15.24)
        top=66.04+yoff
        for num in [8,7,3]:p=u['pins'][str(num)];s.wire(p,(p[0],top))
        s.wire((322.58,top),(337.82,top));s.dot(330.2,top);s.power('+5V_MCU',330.2,top)
        for num in [4,9]:s.gndpin(u,num,7.62)
        cb=cap(s,'C'+str(55+row),'100n / 50V',386.08,54.61+yoff,f);s.p5pin(cb,1);s.gndpin(cb,2)
    s.text('VDD and both SEL pins share MCU 5V. GND and exposed pad9 are grounded. Power-off switches isolate all four ADC inputs.',17.78,246.38)
    s.text('No ADC-side pulldown. Leakage/floating voltage accepted by specification. MCU supply >=4.436V is a user-approved design premise.',17.78,254)
    s.text('5.1V zener is not a clamp to AVCC. Original protection topology retained; out-of-premise low-supply/surge behavior is not guaranteed.',17.78,261.62)
    s.text('Selected OSL display operating range also limits whole-board operation to <=70C; switch leakage design target remains <85C.',17.78,269.24)
    return s

def usb(f):
    s=Sheet('09_USB.kicad_sch','USB Type-C / USB2 device and diode power input',9,'A4')
    s.heading('USB TYPE-C   |   USB2 device / VBUS diode ORing')
    j=s.sym('USB_C_Receptacle_USB2.0_16P','J9','USB4105-GF-A',68.58,81.28,f['USB'],'USB4105-GF-A','GCT','https://gct.co/files/drawings/usb4105.pdf',extra={'Pinout':'A6/B6=D+; A7/B7=D-; individual CC pulldowns'})
    groups={'USB_VBUS':['A4','A9','B4','B9'],'USB_D_P':['A6','B6'],'USB_D_N':['A7','B7'],'USB_CC1':['A5'],'USB_CC2':['B5']}
    for net,nums in groups.items():
        seen=set()
        for k,num in enumerate(nums):
            p=j['pins'][num]
            if p in seen:continue
            seen.add(p)
            if k==0 and net in ['USB_D_P','USB_D_N']:port_at_pin(s,j,num,net,'bidirectional',20.32)
            else:s.netpin(j,num,net,10.16)
    seen=set()
    for num in ['A1','A12','B1','B12','S1']:
        p=j['pins'][num]
        if p in seen:continue
        seen.add(p);s.gndpin(j,num,7.62)
    for num in ['A8','B8']:s.nc(j['pins'][num])
    for ref,x,net in [('R41',116.84,'USB_CC1'),('R42',154.94,'USB_CC2')]:
        r=resistor(s,ref,'5.1k',x,139.7,f);s.netpin(r,1,net);s.gndpin(r,2)
    d=s.sym('D_Schottky_Small','D2','SS2040FL',177.8,50.8,f['D_SCH'],'SS2040FL_R1_00001','PANJIT','https://www.panjit.com.tw/en/Product/Schottky/Power_Schottky/SS2040FL',angle=180,extra={'Rating':'40V 2A SOD-123FL; original SS2040FL path retained'})
    s.netpin(d,2,'USB_VBUS',17.78);s.wire(d['pins']['1'],(231.14,50.8));s.power('+5V_MCU',231.14,50.8)
    c=cap(s,'C41','1u / 10V',162.56,78.74,f,'1u10');s.netpin(c,1,'USB_VBUS');s.gndpin(c,2)
    c=cap(s,'C42','100n / 50V',231.14,78.74,f);s.p5pin(c,1);s.gndpin(c,2)
    rt=resistor(s,'R43','5.1k',220.98,109.22,f);rb=resistor(s,'R44','1M',220.98,144.78,f)
    s.netpin(rt,1,'USB_VBUS');mid=(220.98,125.73);s.wire(rt['pins']['2'],mid,rb['pins']['1']);s.gndpin(rb,2)
    s.wire(mid,(248.92,mid[1]));s.dot(*mid);s.label('USB_VBUS_SENSE',248.92,mid[1],side='right',hier=True,typ='output')
    s.text('P407 senses actual VBUS.\n5.1k / 1M gives 0.9949 x VBUS.\nThe original 5.1k / 10k divider\nwas too low for 5V USB VIH.',175.26,139.7,1.1)
    s.text('D+ and D- go directly to the RA4M1 transceiver. Keep short, matched and impedance controlled.',17.78,167.64,1.1)
    s.text('USB-only operation is accepted by the user. Respect the USB host current budget and enumeration state.',17.78,175.26,1.1)
    s.text('Supply premise: +5V_MCU >=4.436V. TM1640 datasheet range remains 4.5..5.5V; acceptance is recorded in the report.',17.78,182.88,1.1)
    return s

def display(f):
    s=Sheet('10_Display.kicad_sch','TM1640 / twelve common-cathode digits',10)
    s.heading('12-DIGIT DISPLAY   |   TM1640 / OSL10326-LRA (OSL10326-L family)')
    u=ic(s,'TM1640_SOP28','U10','TM1640 / SOP28',73.66,88.9,f,'TM1640','Titan Micro','TM1640')
    s.p5pin(u,17,7.62);s.gndpin(u,6,7.62)
    port_at_pin(s,u,7,'SEG_DIN','input',15.24);port_at_pin(s,u,8,'SEG_CLK','input',15.24)
    for i in range(8):s.netpin(u,9+i,'SEG_'+('ABCDEFG'[i] if i<7 else 'DP'),10.16)
    gridpins={i+1:(18+i if i<11 else i-10) for i in range(16)}
    for i in range(1,17):
        if i<=12:s.netpin(u,gridpins[i],'GRID'+str(i),10.16)
        else:s.nc(u['pins'][str(gridpins[i])])
    for ref,x,kind,value in [('C61',30.48,'47u10','47u / 10V'),('C62',76.2,'100n','100n / 50V')]:
        c=cap(s,ref,value,x,165.1,f,kind);s.p5pin(c,1);s.gndpin(c,2)
    for ref,x,net in [('R61',30.48,'SEG_DIN'),('R62',76.2,'SEG_CLK')]:
        r=resistor(s,ref,'10k',x,203.2,f);s.p5pin(r,1);s.netpin(r,2,net)
    s.text('TM1640 internal segment drivers;\n8 segments x 16 grids scan.\nGRID13..16 unused.\n47u + 100n retained from reference.\n10k interface pullups per datasheet.',17.78,228.6,1.27)
    order=[12,7,8,9,10,11,5,6,4,1,2,3]
    dmap={'1':'SEG_A','10':'SEG_B','8':'SEG_C','5':'SEG_D','4':'SEG_E','2':'SEG_F','3':'SEG_G','6':'SEG_DP'}
    for i,grid in enumerate(order):
        x=175.26+(i%3)*87.63;y=63.5+(i//3)*55.88
        d=s.sym('OSL10326_LRA','DS'+str(i+1),'OSL10326-LRA',x,y,f['DIGIT'],'OSL10326-LRA','OptoSupply','https://www.optosupply.com/uppic/2025822601151.pdf',assembly='Hand/THT',extra={'Type':'A-G cathode9; independent DP anode6/cathode7; red; 7x11x5mm','Grid':str(grid)})
        for num,net in dmap.items():s.netpin(d,num,net,10.16)
        p7=d['pins']['7'];p9=d['pins']['9'];join=(p7[0]+7.62,p9[1]);s.wire(p7,(join[0],p7[1]),join,p9);s.wire(join,(join[0]+5.08,join[1]));s.dot(*join);s.label('GRID'+str(grid),join[0]+5.08,join[1],side='right')
    s.text('A1 B10 C8 D5 E4 F2 G3 -> SEG1..7; A-G cathode9 -> GRID. Independent DP: anode6 -> SEG8, cathode7 -> GRID.',17.78,264.16,1.1)
    s.text('DP corrected to OptoSupply Rev A.1.2 p2 for all 12 digits. Pins7 and9 share GRID externally; pin6 must not be tied to GRID.',17.78,271.78,1.1)
    return s

def root_sheet(children):
    s=Sheet(NAME+'.kicad_sch','Main power board / functional overview',1,'A3',uid(NAME))
    s.heading('DRC POWER2026   |   MAIN POWER BOARD / REV 1.2')
    s.text('3S and 6S battery switching / common GND / control power alive while main outputs are OFF',17.78,25.4,1.52)
    positions={2:(30.48,50.8,91.44,55.88),3:(30.48,137.16,91.44,55.88),4:(167.64,50.8,91.44,43.18),5:(167.64,137.16,91.44,43.18),6:(309.88,45.72,68.58,35.56),7:(309.88,167.64,68.58,60.96),8:(167.64,210.82,91.44,55.88),9:(309.88,106.68,68.58,35.56),10:(30.48,223.52,91.44,38.1)}
    shorttitles={2:'3S main switch',3:'6S main switch',4:'5V control supply',5:'NC emergency stop',6:'MCU core / USB',7:'MCU ADC / control',8:'4-point ADC protection',9:'USB Type-C',10:'12-digit display'}
    for child in children:
        x,y,w,h=positions[child.page]
        left=[(k,v) for k,v in child.ports.items() if v in ['input','bidirectional']]
        right=[(k,v) for k,v in child.ports.items() if v=='output']
        if child.page==9:left=[];right=list(child.ports.items())
        sh=node('sheet',node('at',n(x),n(y)),node('size',n(w),n(h)),node('stroke',node('width',n(.254)),node('type',A('default'))),node('fill',node('color',n(0),n(0),n(0),n(0))),node('uuid',uid('sheet:'+child.file)),
            prop('Sheetname',f'{child.page:02d} '+shorttitles[child.page],x,y-5.08,size=1.52,just='left'),prop('Sheetfile',child.file,x,y+h+2.54,hide=True))
        for side,ports in [('left',left),('right',right)]:
            for i,(name,typ) in enumerate(ports):
                py=y+10.16+i*7.62;px=x if side=='left' else x+w
                sh.append(node('pin',name,A(typ),node('at',n(px),n(py),n(180 if side=='left' else 0)),fx(1.27,'left' if side=='left' else 'right'),node('uuid',s.id('sheetpin'))))
                end=(px-6.35 if side=='left' else px+6.35,py);s.wire((px,py),end);s.label(name,*end,side=side)
        sh.append(node('instances',node('project',NAME,node('path','/'+uid(NAME),node('page',str(child.page))))))
        s.add(sh)
        if child.page==4:s.text('+5V_MCU via LM66100\n3S default / 6S solder select',x+15.24,y+25.4,1.27)
        if child.page in [2,3]:s.text('One N-MOSFET + LM5060\nExternal battery-side MIDI fuse',x+12.7,y+36.83,1.27)
        if child.page==10:s.text('TM1640 + OSL10326-L family',x+8.89,y+29.21,1.27)
    s.text('Global power: +5V_MCU and GND. Signal connections use the identical names shown at each sheet pin.',17.78,274.32,1.27)
    s.text('3S input feeds the NC stop LED. Regenerative absorber is external at the 24V output distribution, with no dedicated connector here.',17.78,281.94,1.1)
    # External returns are common by design. This is the one explicit ERC ground-source declaration.
    s.text('GND is common to batteries, USB, logic\nand the external regenerative absorber.',284.48,245.11,1.27)
    return s

def write_deliverables(sheets,f):
    lib=node('kicad_symbol_lib',node('version',A('20231120')),node('generator','kicad_symbol_editor'),*[SYMS[k] for k in sorted(SYMS)])
    (ROOT/'lib/DRC_Power.kicad_sym').write_text(enc(lib)+'\n',encoding='utf-8')
    (ROOT/'sym-lib-table').write_text('(sym_lib_table\n  (version 7)\n  (lib (name "DRC_Power") (type "KiCad") (uri "${KIPRJMOD}/lib/DRC_Power.kicad_sym") (options "") (descr "Verified main power board symbols"))\n)\n',encoding='utf-8')
    (ROOT/'fp-lib-table').write_text('(fp_lib_table\n  (version 7)\n  (lib (name "DRC_Power") (type "KiCad") (uri "${KIPRJMOD}/lib/DRC_Power.pretty") (options "") (descr "Project-local footprints and manufacturer-derived additions"))\n)\n',encoding='utf-8')
    for s in sheets:s.write()
    cols=['ref','value','mpn','manufacturer','rating','lcsc','fp','dnp','assembly','sheet','ds']
    with (ROOT/'docs/BOM.csv').open('w',encoding='utf-8-sig',newline='') as out:
        wr=csv.DictWriter(out,fieldnames=cols,extrasaction='ignore');wr.writeheader();wr.writerows(BOM)
    with (ROOT/'docs/MCU_PIN_ASSIGNMENT.csv').open('w',encoding='utf-8-sig',newline='') as out:
        cols2=['pin','port','signal','function','electrical'];wr=csv.DictWriter(out,fieldnames=cols2,extrasaction='ignore');wr.writeheader()
        assigned={str(v['pin']):v for v in PINASSIGN}
        fixed={4:('USB_3V3','VBATT from USB LDO output'),5:('VCL_CORE','4.7u to GND; no external load'),8:('GND','VSS'),11:('+5V_MCU','VCC'),16:('USB_VBUS_SENSE','P407 / USB_VBUS input'),17:('GND','VSS_USB'),18:('USB_D_N','P915 / USB_DM'),19:('USB_D_P','P914 / USB_DP'),20:('USB_3V3','USB LDO 3.3V output'),21:('+5V_MCU','USB LDO input'),25:('RESET_N','active-low reset / SW1 / SWD'),26:('BOOT_MD','MD: pulled high; JP2 grounds for ROM boot'),27:('NMI_HIGH','P200 / NMI pulled high'),32:('SWCLK','P300 / SWD clock'),33:('SWDIO','P108 / SWD data'),39:('+5V_MCU','VCC'),40:('GND','VSS'),54:('GND','VREFL DAC reference'),55:('+5V_MCU','VREFH DAC reference'),56:('+5V_MCU','AVCC0'),57:('GND','AVSS0'),58:('GND','VREFL0 ADC reference'),59:('+5V_MCU','VREFH0 ADC reference')}
        defs={str(val(p,'number')):str(val(p,'name')) for sub in kids(SYMS['R7FA4M1AB3CFM_AA0'],'symbol') for p in kids(sub,'pin')}
        for i in range(1,65):
            if str(i) in assigned:row=assigned[str(i)]
            elif i in fixed:row={'pin':i,'port':defs[str(i)],'signal':fixed[i][0],'function':fixed[i][1],'electrical':'USB 3.3V transceiver' if i in [4,18,19,20] else '5V system / common GND'}
            else:row={'pin':i,'port':defs[str(i)],'signal':'NC','function':'Unused; disable digital output / internal oscillators for clock pins','electrical':'No external connection'}
            wr.writerow(row)
    (ROOT/'docs/library_sources.json').write_text(json.dumps({'symbols':LIBLOG,'footprints':FPLOG},ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'docs/schematic_manifest.json').write_text(json.dumps([{'file':s.file,'title':s.title,'page':s.page,'ports':s.ports,'components':s.components} for s in sheets],ensure_ascii=False,indent=2),encoding='utf-8')
    with (ROOT/'docs/OFFBOARD_BOM.csv').open('w',encoding='utf-8-sig',newline='') as out:
        w=csv.writer(out);w.writerow(['Use','Manufacturer','MPN','Qty','Assembly','Note'])
        w.writerows([['3S fuse','Littelfuse','0498040.M',1,'Off-board / battery harness','MIDI 32VDC 40A; ahead of J1'],['6S fuse','Littelfuse','0498060.M',1,'Off-board / battery harness','MIDI 32VDC 60A; ahead of J4'],['Fuse holders','Littelfuse','04980921GXM5',2,'Off-board / battery harness','One per battery'],['NC stop switch','System','NC contact; specific switch unspecified',1,'Off-board','J7.1 to J7.2; opening stops both rails'],['EMG mating housing','JST','VHR-2N',1,'Harness','Use SVH-21T-P1.1 contacts appropriate for actual wire']])

def refine_layout(sheets):
    def fields(sheet,ref,x,y,unit=None,justify='left'):
        for it in kids([None,*sheet.items],'symbol'):
            ps={p[1]:p for p in kids(it,'property')}
            if ps['Reference'][2]!=ref or (unit and int(val(it,'unit'))!=unit):continue
            for j,key in enumerate(['Reference','Value']):
                p=ps[key];one(p,'at')[1:]=[n(x),n(y+j*2.54),n(0)]
                p[:]=[t for t in p if not(isinstance(t,list) and t and t[0]=='effects')]+[fx(1.27,justify)]
    for sheet in sheets:
        if sheet.page in [2,3]:
            fields(sheet,'U'+str(sheet.page-1),180.34,173.99)
            sheet.text('LM5060 GATE CONTROL / INDEPENDENT UVLO',17.78,116.84,1.52,True)
        elif sheet.page==5:
            fields(sheet,'U5',147.32,73.66,justify=None);fields(sheet,'U6',147.32,116.84,justify=None)
        elif sheet.page==6:
            fields(sheet,'U7',121.92,50.8,unit=1);fields(sheet,'U7',218.44,39.37,unit=2)
        elif sheet.page==8:
            fields(sheet,'U8',350.52,69.85);fields(sheet,'U9',350.52,181.61)
        elif sheet.page==10:fields(sheet,'U10',25.4,33.02)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    f=setup()
    children=[power_sheet(f,'3S',2),power_sheet(f,'6S',3),control_power(f),estop(f),mcu_core(f),mcu_io(f),adc(f),usb(f),display(f)]
    root=root_sheet(children)
    refine_layout([root]+children)
    write_deliverables([root]+children,f)
    print('Wrote',len(children)+1,'sheets,',len(BOM),'board components;',len(SYMS),'symbols')





