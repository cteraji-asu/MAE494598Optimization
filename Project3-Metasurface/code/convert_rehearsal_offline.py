"""Official converter with a workspace asset cache reused from its pilot.

Windows platformdirs resolves the OS known folder independently of LOCALAPPDATA.
Redirect only that cache lookup so approved existing assets stay in the workspace.
"""
import hashlib,importlib,json,shutil
from pathlib import Path
from bs4 import BeautifulSoup
from manim_slides.__main__ import cli
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'presentation/rehearsal-2026-10-30-light'
if __name__=='__main__':
    assets=DEST/'framework-assets'
    cache=ROOT.parent.parent/'.native-cache';folder=cache/'revealjs6.0.1';folder.mkdir(exist_ok=True,parents=True)
    if (assets/'assets.json').exists():
        records=json.loads((assets/'assets.json').read_text())['assets']
        for row in records:
            source=assets/row['name'];assert hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256']
            shutil.copy2(source,folder/row['name'])
        converter=importlib.import_module('manim_slides.convert');converter.user_cache_path=lambda app:cache
        cli.main(args=['--silent','convert','OptimizationPresentation',str(DEST/'official-offline.html'),'--folder',str(DEST/'slides'),'--one-file','--offline','-cwidth=1280','-cheight=720','-cmargin=0','-ccontrols=false','-cprogress=false','-cbackground_color=#FAFAF7'],standalone_mode=False)
        print('Official conversion reused verified packaged framework assets.');raise SystemExit(0)
    inventory=BeautifulSoup((DEST/'asset-inventory.html').read_text(encoding='utf-8'),'html.parser')
    pilot=BeautifulSoup((DEST/'pilot-offline.html').read_text(encoding='utf-8'),'html.parser')
    css=[q['href'] for q in inventory.find_all('link',href=True) if q['href'].startswith('http')]
    js=[q['src'] for q in inventory.find_all('script',src=True) if q['src'].startswith('http')]
    cache=ROOT.parent.parent/'.native-cache';folder=cache/'revealjs6.0.1';folder.mkdir(exist_ok=True,parents=True);records=[]
    pilot_scripts=pilot.head.find_all('script')
    assert 'reveal.js' in pilot_scripts[0].get_text()[:100] and 'RevealNotes' in pilot_scripts[1].get_text()[:300]
    scripts={'reveal.js':pilot_scripts[0],'notes.js':pilot_scripts[1],'markdown.js':pilot_scripts[2]}
    for urls,tags in [(css,pilot.head.find_all('style')),(js,[scripts[url.rsplit('/',1)[1]] for url in js])]:
        assert len(urls)==len(tags),(urls,len(tags))
        for url,tag in zip(urls,tags):
            name=url.rsplit('/',1)[1];text=tag.string or tag.get_text();(folder/name).write_text(text,encoding='utf-8');records.append(dict(url=url,name=name,sha256=hashlib.sha256(text.encode()).hexdigest(),source='Existing official five-beat offline pilot'))
    converter=importlib.import_module('manim_slides.convert');converter.user_cache_path=lambda app:cache
    cli.main(args=['--silent','convert','OptimizationPresentation',str(DEST/'official-offline.html'),'--folder',str(DEST/'slides'),'--one-file','--offline','-cwidth=1280','-cheight=720','-cmargin=0','-ccontrols=false','-cprogress=false','-cbackground_color=#FAFAF7'],standalone_mode=False)
    (DEST/'offline-assets.json').write_text(json.dumps(dict(status='Existing approved pilot assets reused by official converter without download',assets=records),indent=2))
