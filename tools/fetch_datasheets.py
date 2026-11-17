from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'datasheets'
OUT.mkdir(exist_ok=True)
SOURCES={
 'LM5060':'https://www.ti.com/lit/ds/symlink/lm5060.pdf',
 'LMR51610':'https://www.ti.com/lit/ds/symlink/lmr51610.pdf',
 'LM66100':'https://www.ti.com/lit/ds/symlink/lm66100.pdf',
 'TMUX2821':'https://www.ti.com/lit/ds/symlink/tmux2821.pdf',
 'RA4M1_datasheet':'https://www.renesas.com/en/document/dst/ra4m1-group-datasheet',
 'RA4M1_hardware':'https://www.renesas.com/en/document/mah/renesas-ra4m1-group-users-manual-hardware?language=en',
 'IPT008N06NM5LF':'https://www.infineon.com/assets/row/public/documents/24/49/infineon-ipt008n06nm5lf-datasheet-en.pdf',
 'OSL10326':'https://www.optosupply.com/uppic/2025822601151.pdf',
 'TM1640':'https://akizukidenshi.com/goodsaffix/TM1640_V1.0_EN.PDF',
 'XT60PW_M':'https://www.tme.eu/Document/b13629717d44ae038681dba08d18c0b6/XT60PW-M.pdf',
 'XT60PW_F':'https://www.tme.eu/Document/1191bc2fa3aee3c446e5a895fd8f7983/XT60PW-F.pdf',
 'XT30PW_F':'https://www.tme.eu/Document/f383737e340bfdab1f665284174b4ea2/XT30PW-F.pdf',
 'LTV817':'https://s3.amazonaws.com/snapeda/datasheet/LTV-817S-TA1-C_Lite-On.pdf',
 'JST_VH':'https://www.jst-mfg.com/product/pdf/eng/eVH.pdf',
 'USB4105':'https://gct.co/files/drawings/usb4105.pdf',
 'CYA0650':'https://xonstorage.z8.web.core.windows.net/pdf/shou_cya065033uh_apr22_xonlink.pdf',
 'Rubycon_PX':'https://akizukidenshi.com/goodsaffix/j_px.pdf',
 'OSL10326_LRA':'https://akizukidenshi.com/goodsaffix/OSL10326-LRA.pdf',
 'SS2040FL':'https://www.panjit.com.tw/en/Product/downloadPDF/SS2040FL',
 'BZT52':'https://www.diodes.com/assets/Datasheets/ds18004.pdf',
}
def fetch(item):
 name,url=item; p=OUT/(name+'.pdf')
 try:
  if not p.exists():
   req=Request(url,headers={'User-Agent':'Mozilla/5.0'})
   with urlopen(req,timeout=35) as r: data=r.read()
   if not data.startswith(b'%PDF'): raise ValueError('Not PDF '+str(data[:60]))
   p.write_bytes(data)
  from pypdf import PdfReader
  import logging
  logging.disable(logging.CRITICAL)
  d=PdfReader(p)
  if name!='RA4M1_hardware' and not (OUT/(name+'.txt')).exists():
   (OUT/(name+'.txt')).write_text('\n'.join(f'\nPAGE {i+1}\n'+page.extract_text() for i,page in enumerate(d.pages)),encoding='utf-8')
  return {'name':name,'url':url,'pages':len(d.pages),'bytes':p.stat().st_size,'status':'OK'}
 except Exception as e: return {'name':name,'url':url,'error':str(e)}
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=4) as pool:
  results=list(pool.map(fetch,SOURCES.items()))
 (OUT/'sources.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
 for r in results: print(json.dumps(r,ensure_ascii=False))
