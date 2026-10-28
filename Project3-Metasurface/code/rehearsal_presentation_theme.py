"""One question-driven Manim world, exported as motion and purposeful PDF keyframes.

Every plotted result comes from retained records. Oscillating waves illustrate
phasors; they are not a transient PDE simulation. No audience administrative slides.
"""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
from manim import *
from switched_line import Config,response,phase_metrics

# Manim 0.22's Cairo image path allocates RGBA from a float 2D array, which
# Pillow 13 rejects. A local runtime shim allocates the same transparent image
# explicitly. Installed packages stay untouched; no new dependency is installed.
import importlib,inspect,textwrap
_camera=importlib.import_module('manim.camera.camera')
_source=textwrap.dedent(inspect.getsource(_camera.Camera.display_image_mobject))
_old='full_image = Image.fromarray(\n        np.zeros((self.pixel_height, self.pixel_width)),\n        mode="RGBA",\n    )'
assert _source.count(_old)==1,'Review compatibility shim against changed Manim source.'
_namespace=dict(_camera.__dict__)
exec('from __future__ import annotations\n'+_source.replace(_old,'full_image = Image.new("RGBA", (self.pixel_width, self.pixel_height), (0, 0, 0, 0))'),_namespace)
_camera.Camera.display_image_mobject=_namespace['display_image_mobject']

ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'presentation/rehearsal-2026-10-30-light';DATA=json.loads((DEST/'scene-data.json').read_text())
W,H=1280,720;BG='#FAFAF7';WHITE='#1E293B';MUTED='#4B5563';GRID='#83909C';ON='#006B5E';OFF='#9A4B00';ERR='#9C2879';PURPLE='#6340A8'
config.pixel_width=W;config.pixel_height=H;config.frame_width=12.8;config.frame_height=7.2;config.frame_rate=18;config.background_color=BG
config.media_dir=str(DEST/'manim-media');CFG=Config()
def pt(x,y):return np.array([(x-W/2)/100,(H/2-y)/100,0])
def txt(s,x,y,size=27,color=WHITE,width=None):
    m=Text(str(s),font='Georgia',color=color,font_size=36)
    if m.height:m.scale_to_fit_height(size/100)
    if width and m.width>width/100:m.scale_to_fit_width(width/100)
    return m.move_to(pt(x,y),aligned_edge=UL)
def ln(x1,y1,x2,y2,color=WHITE,width=2,dash=False):
    cls=DashedLine if dash else Line
    return cls(pt(x1,y1),pt(x2,y2),color=color,stroke_width=width)
def path(points,color=WHITE,width=3):
    m=VMobject(stroke_color=color,stroke_width=width);m.set_points_as_corners([pt(x,y) for x,y in points]);return m
def equation(name,x,y,maxwidth=1120,height=58):
    obj=ImageMobject(str(DEST/'math'/f'{name}.png'));obj.scale_to_fit_height(height/100)
    if obj.width>maxwidth/100:obj.scale_to_fit_width(maxwidth/100)
    obj.move_to(pt(x,y),aligned_edge=UL);return obj
def arrow(z,start,scale,color=WHITE,width=4):
    end=(start[0]+z.real*scale,start[1]-z.imag*scale)
    if abs(z)<1e-12:return Dot(pt(*start),radius=.015,color=color)
    return Arrow(pt(*start),pt(*end),buff=0,color=color,stroke_width=width,max_tip_length_to_length_ratio=.12)
def line_world(a=.151605,y=190,x=90,end=650,labels=True):
    switch=x+(end-x)*a/.36
    box=Rectangle(width=.48,height=.3,color=WHITE,fill_color=BG,fill_opacity=1,stroke_width=2).move_to(pt(switch,y))
    objects=[ln(x,y,switch-24,y),ln(switch+24,y,end,y),box,txt('z',switch-8,y-13,23),ln(end,y-24,end,y+24,width=3)]
    if labels:objects +=[txt('port',x-12,y-50,22,MUTED),txt('short',end-28,y-50,22,MUTED),txt('a',x+(switch-x)/2,y+24,24),txt('d',switch+(end-switch)/2,y+24,24)]
    return VGroup(*objects)
def phasors(a=.151605,center=(1000,290),radius=126,annotate=True):
    rr=[response(.36,a/.36,s,CFG)[0] for s in (0,1)];cx,cy=center
    circle=Circle(radius=radius/100,color=GRID,stroke_width=1.3).move_to(pt(cx,cy))
    objects=[circle,ln(cx-radius-10,cy,cx+radius+10,cy,GRID,1),ln(cx,cy-radius-10,cx,cy+radius+10,GRID,1),arrow(rr[0],center,radius,ON),arrow(rr[1],center,radius,OFF),txt('Re R',cx+radius-20,cy+15,19,MUTED),txt('Im R',cx+12,cy-radius-12,19,MUTED)]
    if annotate:
        m=phase_metrics(*rr)
        objects +=[txt('ON',cx-radius,cy+radius+30,23,ON),txt('OFF',cx+35,cy+radius+30,23,OFF),txt(f"{m['separation_degrees']:.3f}° separation",cx-radius-30,cy+radius+75,25),txt(f"min |R| = {m['min_magnitude']:.4f}",cx-radius-30,cy+radius+115,23,MUTED)]
    return VGroup(*objects)
def axes(x,y,w,h,xlim,ylim,xlabel,ylabel,logy=False,xticks=None,yticks=None):
    def X(v):return x+(v-xlim[0])/(xlim[1]-xlim[0])*w
    def Y(v):
        if logy:v=math.log10(max(v,10**ylim[0]))
        return y+h-(v-ylim[0])/(ylim[1]-ylim[0])*h
    mob=VGroup(ln(x,y,x,y+h,MUTED,1.3),ln(x,y+h,x+w,y+h,MUTED,1.3),txt(ylabel,x,y-44,23),txt(xlabel,x+w/2-100,y+h+48,22,MUTED,width=w))
    for v in (xticks if xticks is not None else np.linspace(*xlim,4)):
        mob.add(txt(f'{v:g}',X(v)-16,y+h+12,19,MUTED))
    for v in (yticks if yticks is not None else np.linspace(*ylim,4)):
        py=Y(10**v if logy else v);mob.add(ln(x,py,x+w,py,GRID,1),txt(f'10^{v:g}' if logy else f'{v:g}',x-58,py-8,18,MUTED))
    def curve(points,color=WHITE,dashed=False):
        coords=[(X(a),Y(b)) for a,b in points]
        m=path(coords,color)
        return DashedVMobject(m,num_dashes=35) if dashed else m
    return mob,curve,X,Y

