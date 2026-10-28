"""Package the official converter output; add one Reveal API replay binding."""
import json,hashlib,shutil,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'presentation/rehearsal-2026-10-30-light'

REPLAY='''\n<script id="presenter-replay-binding">
// Official RevealJS keyboard extension. The framework owns navigation/media.
Reveal.addKeyBinding({keyCode:82,key:'R',description:'Replay current beat'},()=>{
  const video=Reveal.getCurrentSlide()?.slideBackgroundContentElement?.querySelector('video');
  if(video){ video.currentTime=0; video.play(); }
});
</script>\n'''

LIGHT_STYLE='''<style id="light-presentation-shell">
html,body,.reveal,.reveal-viewport,.reveal .slide-background{background-color:#FAFAF7;color:#1E293B}
</style>'''

def main():
    original=DEST/'official-offline.html'
    text=original.read_text(encoding='utf-8')
    assert '</body>' in text and 'Reveal.initialize' in text
    text=re.sub(r'<title>.*?</title>','<title>MAE494 Project 3 | Light Mode</title>',text,count=1,flags=re.DOTALL)
    target=DEST/'MAE494-Project3-Light-Mode.html'
    assert '</head>' in text
    text=text.replace('</head>',LIGHT_STYLE+'</head>')
    prefix,suffix=text.rsplit('</body>',1)
    output=prefix+REPLAY+'</body>'+suffix
    assert output.count('id="presenter-replay-binding"')==1
    target.write_text(output,encoding='utf-8')
    config=json.loads((DEST/'slides/OptimizationPresentation.json').read_text())
    bundle=DEST/'native';bundle.mkdir(exist_ok=True)
    for slide in config['slides']:
        assert not slide['loop'] and not slide['auto_next']
        for key in ('file','rev_file'):
            source=Path(slide[key]);relative=Path('files')/source.name
            (bundle/'files').mkdir(exist_ok=True)
            shutil.copy2(source,bundle/relative);slide[key]=relative.as_posix()
    (bundle/'OptimizationPresentation.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (bundle/'present-windows.cmd').write_text('@echo off\ncd /d "%~dp0"\nmanim-slides present OptimizationPresentation --folder . --full-screen --hide-mouse --hide-info-window\n',encoding='utf-8')
    (bundle/'present.sh').write_text('#!/bin/sh\ncd "$(dirname "$0")" || exit 1\nexec manim-slides present OptimizationPresentation --folder . --full-screen --hide-mouse --hide-info-window\n',encoding='utf-8')
    (bundle/'README.txt').write_text('Light Mode. Native files for official Manim Slides 5.7.0 with the PySide6 extra.\nRequires an existing compatible runtime. This bundle is not an installer.\nRun present-windows.cmd or sh present.sh from an environment where manim-slides is available.\nRight: next. Left: previous segment. R: replay. Space: pause/resume.\nV: previous segment in reverse. Q: quit. No automatic advancement or loops.\nUse ../MAE494-Project3-Light-Mode.html for the portable offline browser version.\n',encoding='utf-8')
    record=dict(html=str(target.relative_to(ROOT)),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),segments=len(config['slides']),native_media_paths='relative to native working directory',framework='Official Manim Slides 5.7.0 converter and player',replay_extension='Reveal.addKeyBinding only')
    (DEST/'export-manifest.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))

if __name__=='__main__':main()
