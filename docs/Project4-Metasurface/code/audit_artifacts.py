"""Read-only integrity and locally reproducible publication checks."""
from pathlib import Path
import hashlib,json,sys,math,re
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def finite(x):
    if isinstance(x,float):assert math.isfinite(x),'Non-finite numeric result'
    elif isinstance(x,dict):
        for v in x.values():finite(v)
    elif isinstance(x,list):
        for v in x:finite(v)

class Inspect(HTMLParser):
    def __init__(self):super().__init__();self.refs=[];self.rows=[];self.row=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for name in ['href','src']:
            if name in a:self.refs.append(a[name])
        if tag=='tr':self.row=0
        if tag in ['th','td'] and self.row is not None:self.row+=1
    def handle_endtag(self,tag):
        if tag=='tr' and self.row is not None:self.rows.append(self.row);self.row=None

def main():
    data=json.loads((ROOT/'assets/results.json').read_text(encoding='utf-8'));finite(data)
    assert data['verification']['passed']
    for name,digest in data['provenance']['source_sha256'].items():assert sha(ROOT/'code'/name)==digest,name
    for arm in ['linear','nonlinear']:
        assert data[arm]['kkt']['accepted'] and data[arm]['final']['feasible']
        assert len(data[arm]['runs'])==5
        assert all(min(row['constraints'])>=-1e-7 for row in next(x for x in data['mesh_refinement'] if x['chi']==data[arm]['chi'])['levels'])
    for prefix,script in [('two-pinn','two_pinn_study.py'),('smooth-pinn','smooth_pinn_study.py')]:
        path=ROOT/'assets'/f'{prefix}-protocol.json'
        if not path.exists():raise AssertionError('Missing '+prefix+' protocol')
        plan=json.loads(path.read_text(encoding='utf-8'));receipt=json.loads((ROOT/'assets'/f'{prefix}-freeze-receipt.json').read_text(encoding='utf-8'))
        assert sha(path)==receipt['protocol_sha256']
        assert sha(ROOT/'code'/script)==plan['source_sha256']
        result=json.loads((ROOT/'assets'/f'{prefix}-results.json').read_text(encoding='utf-8'));finite(result)
        assert len(result['runs'])==6
    # 23 Nov supplemental evidence: finite, bound to the unchanged solver source.
    studies=json.loads((ROOT/'assets/rubric-studies.json').read_text(encoding='utf-8'));finite(studies)
    for name in ['wave_fem.py','run_design.py']:assert sha(ROOT/'code'/name)==studies['provenance']['source_sha256'][name],'rubric-studies source '+name
    loop=json.loads((ROOT/'assets/surrogate-optimizer-loop.json').read_text(encoding='utf-8'));finite(loop)
    assert len(loop['models'])==12
    report=(ROOT/'report.md').read_text(encoding='utf-8')
    preview=(ROOT/'preview.html').read_text(encoding='utf-8')
    body=(ROOT/'site/report-body.html').read_text(encoding='utf-8')
    assert '{%' not in preview and '{{ report_content' not in preview,'Unrendered Liquid in standalone preview'
    assert '{{' not in body and '{%' not in body,'Liquid-sensitive text in included report body'
    assert body in preview,'preview must embed the same report body as the Pages include'
    assert 'mathjax@3.2.2' in preview,'MathJax version must be pinned'
    assert f"{data['nonlinear']['final']['objective']:.6g}" in report,'Stale objective'
    parser=Inspect();parser.feed(preview)
    missing=[]
    for ref in parser.refs:
        if ref.startswith(('http:','https:','#','mailto:','data:')):continue
        clean=ref.split('#')[0].split('?')[0]
        if clean and not (ROOT/clean).exists():
            # Referenced P3 report/interview files aren't copied into isolated
            # numerical reproduction; they remain in the canonical repository.
            if clean.startswith('../Project3-Metasurface/') and not (ROOT.parent/'Project3-Metasurface/report.md').exists():continue
            missing.append(clean)
    assert not missing,missing
    # The generated first report table has eight columns; the viewer ledger
    # precedes it and has four. This catches Markdown header pipe regressions.
    assert parser.rows.count(8)>=4,'Malformed numerical results table'
    for path in ROOT.rglob('*.py'):
        if '__pycache__' not in path.parts:compile(path.read_text(encoding='utf-8'),str(path),'exec')
    outcome={'status':'passed','results_sha256':sha(ROOT/'assets/results.json'),'checks':['finite results','source/protocol hashes','selected feasibility/KKT','finer-mesh feasibility','both six-model experiments','generated report objective','rendered preview without Liquid','local links','result table columns','Python syntax'],'note':'No deployment or student-independent derivation is certified by this audit.'}
    print(json.dumps(outcome,indent=2))

if __name__=='__main__':main()
