"""Connected, operation-based presentation using official Manim Slides.

The switch/port world persists between chapters. All numbers use retained
historical checkpoints or the verified synthetic circuit. No training occurs.
"""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
from manim import *
from manim_slides_ce22 import CompatibleThreeDSlide
from rehearsal_presentation_theme import ROOT,BG,WHITE,MUTED,GRID,ON,OFF,ERR,PURPLE,txt,pt,ln,path,equation,line_world,arrow,axes
from switched_line import Config,response,phase_metrics,wave_reference

DEST=ROOT/'presentation/rehearsal-2026-10-30-light';D=json.loads((DEST/'operation-data.json').read_text());OLD=json.loads((DEST/'scene-data.json').read_text());CFG=Config()
config.media_dir=str(DEST/'media');config.frame_rate=24
CX=np.array(D['probes']['xi'])
def complex_array(values):return np.array([complex(*q) for q in values])
V=complex_array(D['probes']['learned_v']);I=complex_array(D['probes']['learned_i']);VX=complex_array(D['probes']['learned_v_xi']);EV=complex_array(D['probes']['exact_v']);EI=complex_array(D['probes']['exact_i'])
G=CFG.gamma*.208395

# Independent wave solve, then differentiate voltage without using the ODE.
_wave=wave_reference(.36,.151605/.36,1)
def exact_voltage_wave(x):
    return np.exp(CFG.gamma*.151605)*(_wave[1]*np.exp(-G*x)+_wave[2]*np.exp(G*x))
def exact_derivative_fd(x,h=1e-4):
    return (exact_voltage_wave(x-2*h)-8*exact_voltage_wave(x-h)+8*exact_voltage_wave(x+h)-exact_voltage_wave(x+2*h))/(12*h)
def required_exact_derivative(x):
    terminal=2/(np.sinh(G)+(1+CFG.z_off)*np.cosh(G))
    return -G*terminal*np.cosh(G*(1-x))
def at(values,x):return complex(np.interp(x,CX,values.real),np.interp(x,CX,values.imag))
def fmt(z):return f'{z.real:+.3f} {z.imag:+.3f}i'
WEIGHTS=json.loads((ROOT/'outputs/switched-surrogate/pinn_seed-0_weights.json').read_text())['weights']
def neural_R(a,d):
    features=np.array([[-1,2*(d-.03)/(.357-.03)-1,-1],[-1,2*(d-.03)/(.357-.03)-1,1.]])
    h=features
    for layer in ('first','second'):h=np.tanh(h@np.array(WEIGHTS[layer+'.weight']).T+WEIGHTS[layer+'.bias'])
    y=h@np.array(WEIGHTS['last.weight']).T+WEIGHTS['last.bias']
    return np.exp(-2*CFG.gamma*a)*(1-y[:,2]-1j*y[:,3])
for row in D['geometry_path']:
    assert max(abs(neural_R(row['a'],row['d'])-complex_array(row['learned_R'])))<1e-10

class OptimizationPresentation(CompatibleThreeDSlide):
    num_processes=2;max_duration_before_split_reverse=2.0
    def pin(self,m):
        self.add_fixed_in_frame_mobjects(m)
        m.add_updater(lambda obj:self.camera.add_fixed_in_frame_mobjects(obj))
        return m
    def put(self,*objects,fixed=True):
        for m in objects:
            if fixed:self.pin(m)
            else:self.add(m)
            self.body.append(m)
        return objects[0] if len(objects)==1 else objects
    def dynamic(self,fn):return self.put(always_redraw(fn))
    def dependent(self,fn,*trackers):
        m=fn();m._input_values=tuple(t.get_value() for t in trackers)
        def update(obj):
            values=tuple(t.get_value() for t in trackers)
            if values!=obj._input_values:obj.become(fn());obj._input_values=values
        m.add_updater(update);return m
    def erase(self,*objects):
        self.play(*[FadeOut(m) for m in objects],run_time=.45)
        for m in objects:
            if m in self.body:self.body.remove(m)
            self.camera.remove_fixed_in_frame_mobjects(m)
    def hold(self,label):
        self.wait(.25);self.renderer.update_frame(self,ignore_skipping=True)
        folder=DEST/'keyframes';folder.mkdir(exist_ok=True)
        number=len(self.beats);file=f'beat-{number:02d}.png'
        Image.fromarray(self.renderer.get_frame()).convert('RGB').save(folder/file)
        bounds=[]
        for m in self.body:
            if m in self.camera.fixed_in_frame_mobjects:
                bounds.append(dict(left=640+100*m.get_left()[0],right=640+100*m.get_right()[0],top=360-100*m.get_top()[1],bottom=360-100*m.get_bottom()[1]))
        self.beats.append(dict(segment=number,core_scene=self.core,label=label,keyframe='keyframes/'+file,bounds=bounds))
        (DEST/'beat-manifest.json').write_text(json.dumps(dict(status='Rendering continuous Manim Slides presentation',beats=self.beats),indent=2))
        self.next_slide()
    def chapter(self,n,title,context):
        self.core=n
        target_title=txt(title,70,43,42,width=1140);target_context=txt(context,74,112,22,MUTED,width=1130)
        old_title,old_context=self.title,self.context
        self.camera.add_fixed_in_frame_mobjects(target_title,target_context)
        animations=[Succession(FadeOut(old_title,run_time=.3),FadeIn(target_title,run_time=.4)),Succession(FadeOut(old_context,run_time=.3),FadeIn(target_context,run_time=.4))]
        animations +=[FadeOut(m) for m in self.body]
        if self.takeaway is not None:animations.append(FadeOut(self.takeaway))
        if self.in3d:
            self.move_camera(phi=0,theta=-90*DEGREES,frame_center=ORIGIN,zoom=.95,run_time=.8,added_anims=animations);self.in3d=False
        else:self.play(*animations,run_time=.7)
        self.camera.remove_fixed_in_frame_mobjects(old_title,old_context)
        self.title,self.context=target_title,target_context
        for m in self.body:self.camera.remove_fixed_in_frame_mobjects(m)
        self.body=[];self.takeaway=None
    def semantic_context(self,text):
        old=self.context;new=txt(text,74,112,22,MUTED,width=1130)
        self.camera.add_fixed_in_frame_mobjects(new)
        self.play(Succession(FadeOut(old,run_time=.22),FadeIn(new,run_time=.28)),run_time=.5)
        self.camera.remove_fixed_in_frame_mobjects(old);self.context=new
    def conclude(self,text,label):
        self.takeaway=self.pin(txt(text,74,620,28,width=1110))
        self.play(FadeIn(self.takeaway),run_time=.5);self.hold(label)
    def circle(self,center=(970,430),radius=85,caption='Complex plane'):
        x,y=center
        objects=[Circle(radius=radius/100,color=GRID,stroke_width=1).move_to(pt(x,y)),ln(x-radius-12,y,x+radius+12,y,GRID,1),ln(x,y-radius-12,x,y+radius+12,GRID,1),txt('Re',x+radius+15,y+8,18,MUTED),txt('Im',x+10,y-radius-25,18,MUTED)]
        if caption:objects.append(txt(caption,125 if x<500 else 760,292,24,width=450))
        return VGroup(*objects)
    def fixed_geometry(self):self.a.set_value(.151605);self.d.set_value(.208395)
    def construct(self):
        self.body=[];self.beats=[];self.core=1;self.takeaway=None;self.in3d=False
        self.set_camera_orientation(phi=0,theta=-90*DEGREES,zoom=.95)
        self.a=ValueTracker(.11);self.d=ValueTracker(.25)
        self.title=self.pin(txt('Can one finite switch change the reflected wave?',70,43,42,width=1140))
        self.context=self.pin(txt('Illustrative target: about 180° between states, with useful reflected magnitude.',74,112,22,MUTED,width=1130))
        def device():
            aa,dd=self.a.get_value(),self.d.get_value();length=aa+dd
            return line_world(aa/length*.36,215,x=90,end=600)
        self.pin(self.dependent(device,self.a,self.d))
        self.pin(txt('L = a + d',650,166,25))
        self.pin(self.dependent(lambda:txt(f'L={self.a.get_value()+self.d.get_value():.3f}   a={self.a.get_value():.3f}   d={self.d.get_value():.3f}',650,225,21,MUTED,width=355),self.a,self.d))
        self.pin(txt('Port reflection',1010,155,21,MUTED))
        self.pin(txt('ON',1010,202,19,ON));self.pin(txt('OFF',1010,238,19,OFF))
        def ports():
            aa,dd=self.a.get_value(),self.d.get_value();rr=[response(aa+dd,aa/(aa+dd),s)[0] for s in (0,1)]
            return VGroup(Circle(radius=.42,color=GRID,stroke_width=1).move_to(pt(1140,217)),arrow(rr[0],(1140,217),42,ON,3),arrow(rr[1],(1140,217),42,OFF,3))
        self.pin(self.dependent(ports,self.a,self.d))
        self.switch_operation();self.model_operation();self.physics_operation();self.geometry_operation();self.baseline_operation();self.loss_operation();self.field_3d_operation();self.spectrum_operation();self.budget_operation();self.hard_operation();self.controlled_diagnosis_operation();self.screening_cost_operation();self.recommendation();self.references()
        (DEST/'beat-manifest.json').write_text(json.dumps(dict(status='Source-level continuous rendering complete; runtime verification required',core_scenes=13,beats=self.beats),indent=2))
    def switch_operation(self):
        ax,cv,X,Y=axes(125,335,535,185,(0,.36),(0,10),'position / wavelength','Physical current magnitude',xticks=[0,.18,.36],yticks=[0,5,10])
        self.put(ax)
        def currents():
            aa,dd=self.a.get_value(),self.d.get_value();length=aa+dd;parts=[]
            for state,color in [(0,ON),(1,OFF)]:
                r,c=response(length,aa/length,state);xl=np.linspace(0,aa,60);xr=np.linspace(aa,length,80)
                values=np.r_[np.exp(-CFG.gamma*xl)-r*np.exp(CFG.gamma*xl),c*np.cosh(CFG.gamma*(length-xr))[1:]]
                positions=np.r_[xl,xr[1:]];assert max(abs(values))<10
                parts.append(cv(list(zip(positions,abs(values))),color,state==1))
            parts.append(ln(X(aa),335,X(aa),520,MUTED,1.5,True));return VGroup(*parts)
        self.dynamic(currents)
        def metrics():
            aa,dd=self.a.get_value(),self.d.get_value();rr=[response(aa+dd,aa/(aa+dd),s)[0] for s in (0,1)];m=phase_metrics(*rr)
            return VGroup(txt(f"{m['separation_degrees']:.3f}°",795,325,43,WHITE),txt('phase separation',795,385,25),txt(f"min |R| = {m['min_magnitude']:.4f}",795,450,27),txt('Same switch, same short',795,518,23,MUTED))
        self.dynamic(metrics);self.hold('Near a current node, the finite switch has little influence')
        self.play(self.a.animate.set_value(.151605),self.d.animate.set_value(.208395),run_time=4,rate_func=smooth)
        self.conclude('The solved switch response changes when current participates.','Move the same switch; retain phase and magnitude together')
    def model_operation(self):
        self.chapter(2,'What did the minimal case keep?','A synthetic causal analogue. It is not calibrated to the researcher’s 3D copper unit cell.')
        tiles=VGroup(*[Rectangle(width=.58,height=.4,color=MUTED,stroke_width=1.5).move_to(pt(165+80*i,365+62*j)) for i in range(4) for j in range(3)])
        self.put(tiles,txt('Conceptual periodic array',100,555,24,MUTED),equation('boundaries',675,335,maxwidth=500,height=45),txt('Finite switch: voltage jump = z I',695,435,24),txt('Common termination in both states',695,490,23,MUTED))
        self.hold('Retain one switch/current mechanism; omit uncalibrated hardware physics')
        target=Rectangle(width=.48,height=.3,color=WHITE).move_to(pt(90+510*.151605/.36,215))
        self.play(Transform(tiles,target),run_time=1.8)
        self.hold('The finite switch becomes a boundary/interface relation')
        self.erase(*list(self.body))
        self.put(equation('normalized',110,330,maxwidth=1100,height=60),equation('boundaries',170,440,maxwidth=1040,height=50))
        self.conclude('Finite loading survives. Radiation, materials and hardware mapping need validation.','The reduced model preserves a testable mechanism')
    def physics_operation(self):
        self.chapter(3,'What must the derivative equal at this point?','Harmonic PDE reduction: Vξ + γd I = 0. These are complex amplitudes, not a transient.')
        ax,cv,X,Y=axes(125,335,515,185,(0,1),(0,7),'normalized position ξ','Reference Im V',xticks=[0,.5,1],yticks=[0,3.5,7])
        self.put(ax,cv(list(zip(CX,EV.imag)),WHITE),self.circle(caption='Complex derivative, common scale'))
        probe=ValueTracker(.12);scale=8
        def evaluation():
            q=probe.get_value();v=exact_voltage_wave(q);der=exact_derivative_fd(q);required=required_exact_derivative(q)
            return VGroup(Dot(pt(X(q),Y(v.imag)),radius=.045,color=ERR),arrow(der,(970,430),scale,WHITE,5),arrow(required,(970,430),scale,ON,2),txt(f'FD derivative: {fmt(der)}',765,535,20,WHITE,width=435),txt(f'Required −γd I: {fmt(required)}',765,568,20,ON,width=435),txt(f'ξ = {q:.2f}, independent wave-voltage FD',765,597,18,MUTED,width=435))
        self.dynamic(evaluation);self.hold('Choose a position and compare the two complex equation terms')
        self.play(probe.animate.set_value(.86),run_time=4,rate_func=linear)
        self.conclude('Agreement at one point does not establish the whole field or its boundaries.','Evaluate the local differential relation along space')
    def geometry_operation(self):
        self.chapter(4,'Which change controls phase separation?','Move the switch at fixed L, then vary upstream a while holding right length d fixed.')
        ax,cv,X,Y=axes(125,335,520,185,(.195,.25),(0,180),'right length d','Exact phase separation',xticks=[.195,.2225,.25],yticks=[0,90,180])
        rows=D['geometry_path'];self.put(ax,cv([(r['d'],r['reference_phase']) for r in rows],WHITE),equation('factor',715,325,maxwidth=480,height=60))
        def gain():
            aa,dd=self.a.get_value(),self.d.get_value();c=np.cosh(CFG.gamma*dd);s=np.sinh(CFG.gamma*dd);kn=np.sinh(2*CFG.alpha*dd)/(2*CFG.alpha*dd)
            return max(abs(np.exp(-2*CFG.gamma*aa))/abs((1+z)*c+s)*np.sqrt(4*abs(c)**2+1+kn) for z in (CFG.z_on,CFG.z_off))
        def read():
            aa,dd=self.a.get_value(),self.d.get_value();m=phase_metrics(*[response(aa+dd,aa/(aa+dd),s)[0] for s in (0,1)])
            return VGroup(Dot(pt(X(dd),Y(m['separation_degrees'])),radius=.05,color=ERR),txt(f'Output-residual gain G = {gain():.3f}',715,445,24,ERR),txt(f"Δφ = {m['separation_degrees']:.3f}°",715,505,27),txt('The common factor rotates and attenuates.',715,560,20,MUTED))
        self.dynamic(read);self.play(self.a.animate.set_value(.12),self.d.animate.set_value(.24),run_time=3);self.hold('Geometry changes propagate into exact fields and reflection')
        self.play(self.a.animate.set_value(.151605),self.d.animate.set_value(.208395),run_time=3)
        self.play(self.a.animate.set_value(.18),run_time=2.5);self.hold('At fixed d, a changes common phase and attenuation, not separation')
        self.play(self.a.animate.set_value(.151605),run_time=1.8)
        self.conclude('The response and measured gain are non-monotonic in geometry.','Separate controllability, stability gain and neural error')
    def baseline_operation(self):
        self.chapter(5,'Does the conventional solution converge?','Same finite switch and boundary conditions. Independent wave and ABCD checks agree.')
        self.put(self.circle(center=(350,430),radius=88,caption='Complex reflection error, ×8,000'),txt('Refine the spatial solve',760,315,30),txt('Doubling resolution shrinks the error.',760,525,24,MUTED))
        n=ValueTracker(16);exact=response(.36,.151605/.36,1)[0]
        def refiner():
            intervals=int(round(n.get_value()));r=response(.36,.151605/.36,1,intervals=intervals)[0];e=r-exact
            return VGroup(arrow(e,(350,430),8000,ERR),txt(f'{intervals} intervals / segment',760,385,28),txt(f'|ΔR| = {abs(e):.7f}',760,450,28,ERR))
        self.dynamic(refiner);self.hold('A computed approximation differs from the reference')
        for target in (32,64,128,256,512):self.play(n.animate.set_value(target),run_time=.65,rate_func=linear)
        self.conclude('The spatial baseline converges at second order; power checks add independent evidence.','Mesh refinement, an independent wave solve and power balance support P1')
    def loss_operation(self):
        self.chapter(6,'How does a local residual enter the loss?','Saved primary PINN seed 0, OFF, d = 0.208395. Physics-only training contains no field labels.')
        self.put(self.circle(center=(340,425),radius=86,caption=''),equation('loss',735,305,maxwidth=460,height=54))
        p=ValueTracker(.15);amount=ValueTracker(0)
        equation_kind=['V'];fi=complex_array(D['probes']['learned_fi']);ix=fi-G*V
        f=np.abs(complex_array(D['probes']['learned_fv']))**2+np.abs(complex_array(D['probes']['learned_fi']))**2
        cumulative=np.r_[0,np.cumsum((f[1:]+f[:-1])*.5*np.diff(CX))]
        b0=V[0]+(1+CFG.z_off)*I[0]-2;b1=V[-1];boundary=abs(b0)**2/4+abs(b1)**2
        def local():
            q=p.get_value();lhs=at(VX if equation_kind[0]=='V' else ix,q);rhs=-G*at(I if equation_kind[0]=='V' else V,q);res=lhs-rhs;length=amount.get_value()
            return VGroup(txt(f'{equation_kind[0]} equation: derivative − required',125,292,24,width=490),arrow(lhs,(340,425),140,WHITE),arrow(rhs,(340,425),140,PURPLE),arrow(res,(340+140*rhs.real,425-140*rhs.imag),140,ERR),txt(f'ξ = {q:.2f}',250,550,24),txt(f'fV = {fmt(at(complex_array(D["probes"]["learned_fv"]),q))}',715,392,22,ERR),txt(f'fI = {fmt(at(fi,q))}',715,435,22,ERR),txt(f'Integrated interior = {np.interp(length,CX,cumulative):.5f}',715,490,22),txt(f'Boundary contribution = {boundary:.5f}',715,540,22,MUTED))
        moving=self.dynamic(local);self.hold('Subtract the required derivative from the actual derivative')
        self.play(p.animate.set_value(.85),amount.animate.set_value(1),run_time=4,rate_func=linear)
        self.hold('Both complex residuals contribute to the continuous diagnostic norm')
        self.erase(moving);equation_kind[0]='I';moving=self.dynamic(local)
        self.play(FadeIn(moving),p.animate.set_value(.35),run_time=2.5)
        self.hold('Repeat the coupled I relation at another spatial point')
        self.erase(*list(self.body))
        ax,cv,X,Y=axes(125,335,1050,185,(0,4000),(-7,1),'gradient calls','Separate training loss terms',logy=True,xticks=[0,2000,4000],yticks=[-7,-4,-1]);self.put(ax)
        history=OLD['primary_loss'];progress=ValueTracker(0)
        for key,color,label,xlabel in [('pde_voltage',WHITE,'fV',620),('pde_current',PURPLE,'fI',720),('driven_interface',ON,'drive',820),('terminal_short',OFF,'short',970)]:
            self.put(cv([(r['step'],r[key]) for r in history],color),txt(label,xlabel,290,21,color))
        def history_probe():
            step=progress.get_value();return VGroup(ln(X(step),335,X(step),520,MUTED,1,True),*[Dot(pt(X(step),Y(np.interp(step,[r['step'] for r in history],[r[key] for r in history]))),radius=.04,color=color) for key,color in [('pde_voltage',WHITE),('pde_current',PURPLE),('driven_interface',ON),('terminal_short',OFF)]])
        self.dynamic(history_probe);self.play(progress.animate.set_value(4000),run_time=3,rate_func=linear)
        self.conclude('Small sampled loss and exact endpoints still need field and output checks.','Accumulate the squared complex residual without adding a hidden data loss')
    def field_3d_operation(self):
        self.chapter(7,'What can the real projection hide?','Example: seed 0, OFF, d = 0.208395. Axes are ξ, Re V, Im V, not device geometry.')
        ax=ThreeDAxes(x_range=[0,1,.25],y_range=[-2,2,1],z_range=[0,7,2],x_length=4.8,y_length=1.5,z_length=1.8,axis_config={'color':GRID,'stroke_width':1.5,'include_tip':False}).shift(LEFT*2.1+DOWN*1.3)
        curve=lambda values,color:ParametricFunction(lambda t:ax.c2p(t,at(values,t).real,at(values,t).imag),t_range=[0,1,.008],color=color,stroke_width=3)
        self.put(ax,curve(V,PURPLE),curve(EV,WHITE),fixed=False)
        labels=[]
        for name,where in [('ξ',ax.c2p(1.08,0,0)),('Re V',ax.c2p(0,2.2,0)),('Im V',ax.c2p(0,0,7.8))]:
            m=Text(name,font='Georgia',font_size=22,color=MUTED).move_to(where);labels.append(m)
        self.add_fixed_orientation_mobjects(*labels);self.body.extend(labels);labels[-1].set_opacity(0)
        self.put(txt('learned',795,315,24,PURPLE),txt('reference',980,315,24,WHITE));self.hold('Compare the real projection before revealing its missing component')
        self.move_camera(phi=65*DEGREES,theta=-65*DEGREES,frame_center=OUT*1.4,zoom=.95,run_time=3);self.in3d=True
        self.play(labels[-1].animate.set_opacity(1),run_time=.4)
        p=ValueTracker(.35)
        for values,color in [(EV,WHITE),(V,PURPLE)]:
            m=always_redraw(lambda values=values,color=color:Line(ax.c2p(p.get_value(),0,0),ax.c2p(p.get_value(),at(values,p.get_value()).real,at(values,p.get_value()).imag),color=color,stroke_width=3));self.put(m,fixed=False)
        self.hold('Camera settles; a fixed-position cross-section is a voltage phasor')
        self.play(p.animate.set_value(.75),run_time=3,rate_func=linear)
        self.conclude('A smooth projection can hide a large complex-field disagreement.','The same arrays persist through the projection, camera move and evaluation')
    def spectrum_operation(self):
        self.chapter(8,'Which spatial components remain in the error?','Complex voltage error at one fixed geometry. DFT uses 128 samples, excluding the duplicate endpoint.')
        f=OLD['field'];error=(np.array(f['v_real'])-np.array(f['exact_v_real']))+1j*(np.array(f['v_imag'])-np.array(f['exact_v_imag']));error=error[:-1];j=np.arange(128)
        ax,cv,X,Y=axes(125,335,510,185,(0,1),(0,7),'normalized position ξ','Absolute complex V error',xticks=[0,.5,1],yticks=[0,3.5,7]);self.put(ax,cv(list(zip(j/128,abs(error))),ERR),self.circle(center=(975,430),radius=85,caption='Weighted Fourier sum / 128'))
        count=ValueTracker(0);frequency=ValueTracker(0)
        def dft():
            n=int(round(count.get_value()));k=int(round(frequency.get_value()));terms=error*np.exp(-2j*np.pi*k*j/128)/128;partial=terms[:n].sum()
            return VGroup(arrow(partial,(975,430),22,ERR),Dot(pt(X(min(n,127)/128),Y(abs(error[min(n,127)]))),radius=.04,color=WHITE),txt(f'k = {k}    samples = {n}/128',775,550,23))
        self.dynamic(dft);self.hold('Evaluate and add each weighted error sample')
        self.play(count.animate.set_value(128),run_time=4,rate_func=linear);self.hold('The zero-frequency coefficient measures the mean complex error')
        self.play(count.animate.set_value(0),run_time=1.2,rate_func=linear)
        self.play(frequency.animate.set_value(4),run_time=.6)
        self.play(count.animate.set_value(128),run_time=4,rate_func=linear)
        self.hold('A new frequency changes the weights and their cancellation')
        self.erase(*list(self.body))
        self.semantic_context('Left: held-out state errors versus measured gain. Right: the fixed-geometry spatial spectrum.')
        ax,cv,X,Y=axes(125,335,515,185,(0,6),(0,1.1),'output-residual gain G','Voltage relative L2',xticks=[0,3,6],yticks=[0,.55,1.1])
        self.put(ax,VGroup(*[Dot(pt(X(g),Y(e)),radius=.012,color=ERR,fill_opacity=.6) for g,e in OLD['field_error_vs_gain']]))
        ag,cg,XX,YY=axes(755,335,430,185,(-12,12),(-5,1),'cycles per segment','Spatial error DFT amplitude',logy=True,xticks=[-12,0,12],yticks=[-5,-3,-1,1])
        spectrum=OLD['field']['spectrum'];self.put(ag,cg(spectrum,ERR));mode=ValueTracker(-12)
        self.dynamic(lambda:Dot(pt(XX(mode.get_value()),YY(np.interp(mode.get_value(),[r[0] for r in spectrum],[r[1] for r in spectrum]))),radius=.05,color=WHITE))
        self.play(mode.animate.set_value(12),run_time=3,rate_func=linear)
        self.conclude('Gain and spectra locate errors; they do not identify the training-failure cause.','P4 spectrum and stability gain differ from the controlled sampling knob')
    def budget_operation(self):
        self.chapter(9,'How does residual error reach the reflected wave?','Actual saved checkpoint and geometry. The verified identity transports output error, not training causes.')
        self.put(equation('identity',100,285,maxwidth=1110,height=65),self.circle(center=(350,465),radius=65,caption=''))
        t=ValueTracker(0);px=np.array([r['xi'] for r in D['partial_residual_integral']]);q=complex_array([r['q'] for r in D['partial_residual_integral']]);den=(1+CFG.z_off)*np.cosh(G)+np.sinh(G);up=np.exp(-2*CFG.gamma*.151605);multiplier=-up/den
        phase=ValueTracker(0);integral_scale=75/max(max(abs(q)),max(abs(q*multiplier)))
        def integral():
            value=complex(np.interp(t.get_value(),px,q.real),np.interp(t.get_value(),px,q.imag));m=np.exp(phase.get_value()*(np.log(abs(multiplier))+1j*np.angle(multiplier)))
            return VGroup(arrow(value*m,(350,465),integral_scale,ERR),txt(f'ξ = {t.get_value():.2f}',705,410,25),txt(f'q = {fmt(value)}',705,465,24,ERR),txt('Divide by complex D: rotate and scale',705,535,22,MUTED))
        moving=self.dynamic(integral);self.hold('Accumulate the correctly weighted interior residual')
        self.play(t.animate.set_value(1),run_time=4,rate_func=linear);self.hold('The quadrature endpoint agrees with the verified q')
        self.play(phase.animate.set_value(1),run_time=2.6);self.hold('Complex multiplication applies both rotation and scaling')
        self.erase(moving)
        terms=[complex(*D['signed_budget'][k]) for k in ('port','interior','short')];scale=130/max(abs(sum(terms[:i])) for i in range(1,4));start=0j
        for term,color in zip(terms,(ON,ERR,OFF)):
            m=arrow(term,(350+scale*start.real,465-scale*start.imag),scale,color);self.put(m);self.play(GrowArrow(m),run_time=.8);start+=term
        self.put(arrow(start,(350,465),scale,WHITE,2),txt('thin dark = measured ΔR',700,450,25),txt('The signed contributions can cancel.',700,515,23,MUTED))
        self.conclude('Their actual complex sum matches predicted minus reference reflection.','Add drive, interior and short contributions head-to-tail')
    def hard_operation(self):
        self.chapter(10,'Does enforcing the endpoints repair the model?','One trained hard-model raw field is transformed in stages. The separate paired experiment used six fresh fits.')
        h=D['hard_transform'];raw=complex_array(h['raw_v']);short=complex_array(h['after_short']);hard=complex_array(h['hard_v']);current=complex_array(h['current']);stage=ValueTracker(0)
        ax,cv,X,Y=axes(125,335,515,185,(0,1),(-2,7),'normalized position ξ','Im V, common scale',xticks=[0,.5,1],yticks=[-2,2.5,7]);self.put(ax,equation('transform',720,305,maxwidth=490,height=52))
        def transformed():
            s=stage.get_value();values=raw+(short-raw)*min(s,1)+(hard-short)*max(0,s-1)
            b0=values[0]+(1+CFG.z_off)*current[0]-2;b1=values[-1]
            return VGroup(cv(list(zip(CX,values.imag)),ON),txt(f'|drive residual| = {abs(b0):.5f}',720,430,24),txt(f'|V(1)| = {abs(b1):.5f}',720,485,24))
        self.dynamic(transformed);self.hold('Raw V does not automatically satisfy either endpoint')
        self.play(stage.animate.set_value(1),run_time=2.8);self.hold('Subtract ξ v(1): evaluate the exact short condition')
        self.play(stage.animate.set_value(2),run_time=2.8);self.put(cv(list(zip(CX,EV.imag)),WHITE));self.hold('Subtract the drive correction; interior accuracy remains a separate question')
        self.put(txt('All six validation gates failed.',720,550,24,ERR))
        self.conclude('Exact endpoint enforcement was insufficient to repair this model at the fixed budget.','The intervention also changes trial representation; the original training cause remains unresolved')
    def controlled_diagnosis_operation(self):
        self.chapter(11,'What do controlled comparisons establish?','P3: increase the missing-training width w around d = 0.2085. Equations stay fixed.')
        q=json.loads((DEST/'controlled-diagnosis-data.json').read_text());rows=q['levels']
        ax,cv,X,Y=axes(125,335,515,185,(0,.027),(-3,0),'missing-training width w','Median joint-field relative L2',logy=True,xticks=[0,.0135,.027],yticks=[-3,-2,-1,0])
        self.put(ax,txt('physics objective',760,305,24,PURPLE),txt('direct-reference objective',760,348,24,ON),txt('One shared primary warm start per pair',760,405,21),txt('Same network, inputs, L-BFGS, 1,200 calls',760,442,20),txt('Training counts: 256 / 248 / 240',760,480,21),txt('One seed; historical evaluation cohorts',760,520,20,MUTED))
        for key,color in [('physics',PURPLE),('supervised',ON)]:
            line=cv([(r['width'],r[key]) for r in rows],color);self.put(line);self.play(Create(line),run_time=1.1)
        self.hold('Nested support removal increases observed error in both objective arms')
        self.erase(*list(self.body));self.semantic_context('Same six fits: diagnostic improvement is separate from the unchanged deployment gate.')
        self.put(txt(f"{q['objective_ratio']:.2f}x",125,310,48,ON),txt('lower median field error at w = 0',125,375,23),txt('Change physics to reference objective',125,420,22),txt(f"{q['sampling_ratio']:.2f}x",125,475,42,PURPLE),txt('higher reference-fit error at largest gap',125,532,22),txt('All six BLOCKED gates failed',760,310,27,ERR),txt('Three supervised OFF-GRID gates passed',760,355,22,ON),txt('Full coverage: retains 10/10 feasible',760,405,21),txt('but promotes 10/150 infeasible designs',760,445,21,ERR),txt('R95 = 0.04135 exceeds 0.03',760,485,22),txt('Nested removal changes N, not fixed-N location.',760,532,19,MUTED))
        self.hold('Objective and support contrasts are real; none passes the blocked deployment gate')
        self.erase(*list(self.body));self.semantic_context('Separate optimizer control: covered checkpoint, physical two-segment voltage metric; do not mix metrics.')
        ax,cv,X,Y=axes(125,335,515,185,(0,1),(0,.5),'Adam                         L-BFGS','Median physical-voltage relative L2',xticks=[],yticks=[0,.25,.5]);self.put(ax)
        bars=[]
        for x,key,color in [(.25,'adam',PURPLE),(.75,'lbfgs',ON)]:
            value=q['optimizer'][key];h=(520-Y(value))/100;m=Rectangle(width=1.0,height=h,fill_color=color,fill_opacity=.85,stroke_color=color).move_to(pt(X(x),520),aligned_edge=DOWN)
            self.put(m,txt(f'{100*value:.2f}%',X(x)-45,Y(value)-35,23,color));bars.append(m)
        self.play(*[GrowFromEdge(m,DOWN) for m in bars],run_time=1.5)
        self.put(txt('Same start, physics objective and inputs',760,315,21),txt('Same architecture and 1,200 gradient calls',760,355,21),txt('204/256 blocked state errors improve',760,405,23),txt('Both arms retain 0/8 feasible designs',760,450,22,ERR),txt('Both validation gates fail',760,490,23,ERR),txt('Conditional effect; one seed, not a unique cause.',760,535,19,MUTED))
        self.conclude('Optimizer, objective and support affect attained error. No Path C success is claimed.','Bounded Path B diagnosis; the finer original training mechanism remains unresolved')

    def screening_cost_operation(self):
        self.chapter(12,'Would this support useful, cheaper design screening?','Illustrative requirements: phase ≥165°, minimum magnitude ≥0.8. They are not the researcher’s stated tolerances.')
        self.put(txt('Reference decision',125,305,28,WHITE),txt('Saved neural decision',760,305,28,PURPLE))
        def decision():
            aa,dd=self.a.get_value(),self.d.get_value();exact=phase_metrics(*[response(aa+dd,aa/(aa+dd),s)[0] for s in (0,1)]);pred=phase_metrics(*neural_R(aa,dd));items=[]
            for x,m,color in [(125,exact,WHITE),(760,pred,PURPLE)]:
                passed=m['phase_valid'] and m['separation_degrees']>=165 and m['min_magnitude']>=.8
                items +=[txt(f"Δφ = {m['separation_degrees']:.3f}°",x,380,30,color),txt(f"min |R| = {m['min_magnitude']:.4f}",x,440,27,color),txt('FEASIBLE' if passed else 'INFEASIBLE',x,510,29,ON if passed else ERR)]
            return VGroup(*items)
        display=self.dynamic(decision)
        self.play(self.a.animate.set_value(.11),self.d.animate.set_value(.25),run_time=1.5);self.hold('Choose a weak design and evaluate both criteria')
        self.play(self.a.animate.set_value(.151605),self.d.animate.set_value(.208395),run_time=4)
        self.hold('The actual reference crosses acceptance; the learned decision still rejects it')
        self.erase(*list(self.body))
        self.put(txt('Primary held-out design cohorts',125,305,27),txt('Off-grid: 21/21 feasible retained',125,370,25),txt('Blocked: 0/10 feasible retained',125,420,25,ERR),txt('Same blocked failure in all three PINN seeds.',125,480,22,MUTED),txt('Original thresholds and saved cohorts.',125,535,21,MUTED),txt('Fresh paired boundary control',760,305,27,width=450),txt('All six validation gates failed.',760,370,25,ERR),txt('Blocked final: 30 infeasible cases',760,420,23),txt('No feasible cases; sensitivity undefined.',760,475,23,width=445),txt('Historical cohorts remain diagnostic.',760,535,21,MUTED))
        self.hold('Separate the representative design from full-cohort screening evidence')
        self.erase(*list(self.body))
        self.put(equation('cost',170,285,height=50));n=ValueTracker(0);row=OLD['hard_results']['models'][0];tim=row['timing'];train=row['training_seconds']+row['reference_generation_seconds'];sol=tim['factorized_single_seconds_per_two_state_query'];inf=tim['neural_single_seconds_per_two_state_query']
        def totals():
            queries=10**n.get_value()
            return VGroup(txt(f'{queries:,.0f} two-state queries',125,365,30),txt(f'Conventional: {queries*sol:.4f} s',125,440,29),txt(f'Neural + fit: {train+queries*inf:.4f} s',760,440,29,PURPLE),txt('CPU float64, one thread. One-fit lower bound; full setup/history is unmeasured.',125,550,22,MUTED,width=1080))
        self.dynamic(totals);self.play(n.animate.set_value(7),run_time=4,rate_func=linear)
        self.conclude('There is no positive break-even here, and the neural accuracy gate fails.','Measured query costs cannot establish an HFSS or hardware speedup')
    def recommendation(self):
        self.chapter(13,'What should the researcher do next?','A bounded synthetic result with a concrete next researcher decision.')
        self.put(txt('Established in this analogue',110,315,29,ON),txt('Finite-switch influence depends on participation.',110,380,25),txt('Exact endpoints alone did not repair the model.',110,430,25),txt('Needed for hardware transfer',740,315,29,OFF),txt('One permitted unit-cell family and switch model',740,380,23),txt('paired responses and useful tolerances',740,430,23),txt('solver, storage and orchestration cost separately',740,480,23,MUTED))
        self.conclude('Keep the conventional reference. Validate this mechanism before claiming device benefit.','Recommendation, limitations and next decision')
    def references(self):
        self.chapter(13,'Sources for the physical and diagnostic argument','Full derivations, source hashes, frozen protocols and uncertainty markers are retained in the report.')
        entries=[('Team interview brief and recording','Approved source copies linked from the report'),('Chew: lossy transmission lines','wcchew.ece.illinois.edu/chew/ece350/ee350-11.pdf'),('Costa & Borgese, 2021','doi.org/10.1109/OJCOMS.2021.3092217'),('Krishnapriyan et al., 2021','arxiv.org/abs/2109.01050'),('Sukumar & Srivastava, 2021','arxiv.org/abs/2104.08426'),('Grossmann et al., 2024','doi.org/10.1093/imamat/hxae011')]
        for n,(name,link) in enumerate(entries):
            column=n//3;row=n%3;x=110+640*column;y=300+90*row
            self.put(txt(name,x,y,24,width=490),txt(link,x,y+38,20,MUTED,width=490))
        self.hold('Sources; the signed residual identity is derived for this analogue')

if __name__=='__main__':
    import tempfile
    (DEST/'render-temp').mkdir(exist_ok=True)
    tempfile.tempdir=str(DEST/'render-temp')
    with tempconfig({'format':'mp4','preview':False,'output_file':'OptimizationPresentation','disable_caching':True}):
        OptimizationPresentation(output_folder=DEST/'slides').render()
