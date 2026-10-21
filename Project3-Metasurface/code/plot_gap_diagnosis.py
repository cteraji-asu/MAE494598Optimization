"""Core scientific plots from the frozen paired diagnosis, without training."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw
from plot_results import portable_font
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'outputs/gap-objective-diagnosis';OUT=ROOT/'outputs/figures-switch'
COLORS={'physics':'#225ea8','supervised':'#c4492d'}
def main():
    OUT.mkdir(exist_ok=True);data=json.loads((DATA/'results.json').read_text());rows=data['records'];font=portable_font(24);small=portable_font(20);title=portable_font(34)
    im=Image.new('RGB',(1400,900),'white');d=ImageDraw.Draw(im)
    d.text((80,35),'Controlled sampling gap and objective dependence',font=title,fill='#172733')
    d.text((80,88),'Same failed starting checkpoint, architecture, L-BFGS and 1,200 gradient calls per arm',font=small,fill='#53616b')
    x0,y0,w,h=150,180,1120,520;X=lambda x:x0+w*x/.027;Y=lambda e:y0+h-h*(math.log10(e)+3)/3
    for e in (.001,.01,.1,1):
        y=Y(e);d.line((x0,y,x0+w,y),fill='#d8dee3',width=1);d.text((75,y-12),f'{e:g}',font=font,fill='#25333d')
    for x in (0,.0135,.027):
        px=X(x);d.line((px,y0+h,px,y0+h+9),fill='#25333d',width=2);d.text((px-35,y0+h+20),f'{x:g}',font=font,fill='#25333d')
    d.line((x0,y0,x0,y0+h,x0+w,y0+h),fill='#25333d',width=2)
    for n,mode in enumerate(('physics','supervised')):
        group=[r for r in rows if r['mode']==mode];points=[(X(r['gap_width']),Y(r['groups']['test_blocked']['median_joint_right_L2'])) for r in group]
        d.line(points,fill=COLORS[mode],width=4)
        for r,(x,y) in zip(group,points):
            d.ellipse((x-6,y-6,x+6,y+6),fill=COLORS[mode]);label=f"{100*r['groups']['test_blocked']['median_joint_right_L2']:.3f}%";d.text((x-45,y-34 if mode=='physics' else y+12),label,font=small,fill=COLORS[mode])
        d.line((835,135+30*n,875,135+30*n),fill=COLORS[mode],width=4);d.text((890,121+30*n),mode+' objective',font=small,fill=COLORS[mode])
    d.text((80,130),'Median relative joint right-field L2, logarithmic scale',font=small,fill='#25333d')
    d.text((380,765),'Missing-training interval width in d',font=font,fill='#25333d')
    d.text((80,815),'Historical fixed cohorts; one warm-start seed. Nested training counts: 256 / 248 / 240.',font=small,fill='#53616b')
    d.text((80,850),'Blocked-cohort gates: all six fail. Supervised off-grid gates: all three pass.',font=small,fill='#53616b')
    im.save(OUT/'gap-objective-relative-L2.png')
    # Distinct loss terms are diagnostics for both arms; only the named objective is optimized.
    im=Image.new('RGB',(1500,1050),'white');d=ImageDraw.Draw(im);d.text((55,25),'Separate losses in every paired continuation',font=title,fill='#172733')
    terms=[('pde_voltage','#225ea8'),('pde_current','#2d8c72'),('drive','#a365b1'),('short','#b07924'),('data','#c4492d')]
    import csv
    for n,row in enumerate(rows):
        col=n//2;rr=n%2;left=75+485*col;top=145+430*rr;pw,ph=365,300
        path=DATA/f"gap-{row['gap_width']:.4f}"/row['mode']/'loss-history.csv';trace=list(csv.DictReader(path.open()))
        d.text((left,top-45),f"w={row['gap_width']:g}, {row['mode']}",font=font,fill='#25333d')
        for q in (-8,-6,-4,-2,0,2):
            y=top+ph-ph*(q+8)/10;d.line((left,y,left+pw,y),fill='#e1e6e8');d.text((left-48,y-10),f'1e{q}',font=portable_font(16),fill='#65737b')
        d.line((left,top,left,top+ph,left+pw,top+ph),fill='#25333d',width=2)
        for key,color in terms:
            if key not in trace[0]:continue
            points=[]
            for r in trace:
                x=left+pw*int(r['gradient_call'])/1200;y=top+ph-ph*(max(-8,min(2,math.log10(max(float(r[key]),1e-12))))+8)/10;points.append((x,y))
            d.line(points,fill=color,width=3)
        d.text((left+72,top+ph+16),'gradient calls, 0 to 1200',font=small,fill='#53616b')
    for n,(key,color) in enumerate(terms):d.text((60+285*n,1000),key,font=small,fill=color)
    im.save(OUT/'gap-objective-losses.png');print('Saved two core plots from retained diagnosis records.')
if __name__=='__main__':main()
