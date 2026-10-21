"""Historically informed, bounded sampling-gap/objective diagnosis.

No prior result is replaced. This is not a new pristine holdout or a search
for a successful remedy. All six continuations are reported, including failures.
"""
import copy,csv,hashlib,json,platform,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
import optimizer_control as budget_control
from switched_surrogate import load,complex_channels,impedance,reference_right,CFG,write_csv
from switched_line import wave_reference,phase_metrics
from summarize_switched_surrogate import classification

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/gap-objective-diagnosis'
PRIMARY=ROOT/'outputs/switched-surrogate'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def vector_sha(m):return hashlib.sha256(budget_control.vector(m).numpy().tobytes()).hexdigest()

def freeze():
    OUT.mkdir(exist_ok=True)
    path=OUT/'frozen-protocol.json'
    if path.exists():return json.loads(path.read_text())
    covered=ROOT/'outputs/neural-coverage-control/frozen-control.json'
    base=[r for r in json.loads(covered.read_text())['arms']['reallocated']['designs'] if r['split']=='train']
    primary=json.loads((PRIMARY/'frozen-protocol.json').read_text())
    evaluation=[r for r in primary['designs'] if r['split'] in ('test_offgrid','test_blocked')]
    levels=[]
    for width in (0.,.0135,.027):
        train=[r for r in base if width==0 or abs(r['d']-.2085)>=width/2]
        levels.append(dict(width=width,training_designs=train,training_count=len(train)))
    for low,high in zip(levels,levels[1:]):assert {r['id'] for r in high['training_designs']}<={r['id'] for r in low['training_designs']}
    assert not {r['d'] for r in base}&{r['d'] for r in evaluation}
    plan=dict(status='Historically informed prospective audit repair; primary evaluation cohorts previously inspected.',
      question='Separate missing input support from dependence on the physics versus reference-training objective, conditional on fixed checkpoint, architecture, optimizer and budget.',
      knob='Width of a centered missing-training interval in d. Larger width removes a nested set of constraints near the same resonant field family; no physical equation changes. Empirical error need not be strictly monotone and is never forced to be.',
      levels=levels,evaluation_designs=evaluation,seed=0,
      starting_weights=dict(path='outputs/switched-surrogate/pinn_seed-0_weights.json',sha256=sha(PRIMARY/'pinn_seed-0_weights.json')),
      source_sha256=sha(Path(__file__)),budget_helper_sha256=sha(ROOT/'code/optimizer_control.py'),
      primary_protocol_sha256=sha(PRIMARY/'frozen-protocol.json'),covered_protocol_sha256=sha(covered),
      architecture='Same 3-64-64-4 tanh, 4676 parameters; float64, one CPU thread.',
      objectives=['physics','supervised'],spatial_training_nodes=17,evaluation_midpoints=128,
      optimizer='L-BFGS strong Wolfe; fresh state per arm; lr1, history50, inner max_iter20/max_eval30, tolerances1e-9/1e-12',
      maximum_gradient_calls_per_fit=1200,maximum_fits=6,terminal_accepted_weights_only=True,
      early_convergence='Report actual calls. A pair with unequal calls is not a matched-budget causal comparison. No rerun or padding.',
      order='Increasing width; physics then supervised. Every level/arm retained, no validation-based selection.',
      diagnostic_criteria=dict(fully_covered_supervised_median_joint_right_L2_at_most=.05,physics_to_supervised_field_error_ratio_at_least=3.,
        largest_to_smallest_gap_supervised_error_ratio_at_least=3.,require_matched_gradient_calls=True),
      deployment_gate_retained=dict(blocked_R95_at_most=.03,median_joint_right_L2_at_most=.05,sensitivity_at_least=.9,specificity_at_least=.9,both_classes_required=True),
      cautions=['Diagnostic contrast thresholds are historically informed, not researcher tolerances.','One retained seed does not establish population-wide behavior.','Sampling sparsity is the controlled knob; G remains a separate non-monotone output stability diagnostic.','No unique finer optimization mechanism or Path C success follows automatically.'],
      hardware=dict(platform=platform.platform(),torch=torch.__version__,numpy=np.__version__))
    path.write_text(json.dumps(plan,indent=2))
    (OUT/'freeze-receipt.json').write_text(json.dumps(dict(protocol_sha256=sha(path),source_sha256=plan['source_sha256'],before_new_training_or_reference_generation=True,retained_evaluation_cohorts='Historical, already inspected'),indent=2))
    return plan

def components(model,grid,target=None):
    xi,d,state=grid;value,dx=model.jets(xi,d,state)
    v,i=complex_channels(value);vx,ix=complex_channels(dx);zero=torch.zeros_like(xi)
    v0,i0=complex_channels(model.values(zero,d,state));v1,_=complex_channels(model.values(zero+1,d,state))
    terms=dict(pde_voltage=abs(vx+CFG.gamma*d*i).square().mean(),pde_current=abs(ix+CFG.gamma*d*v).square().mean(),
      drive=abs(v0+(1+impedance(state))*i0-2).square().mean()/4,short=abs(v1).square().mean())
    terms['physics']=sum(terms.values())
    if target is not None:terms['data']=(value-target).square().sum(1).mean()
    return terms

def evaluate(model,designs,n=128):
    rows=[];pairs=[]
    with torch.no_grad():
        for start in range(0,len(designs),16):
            batch=designs[start:start+16];d=torch.tensor([r['d'] for r in batch]).repeat_interleave(2*n)
            state=torch.tensor([0.]*n+[1.]*n).repeat(len(batch));xi=((torch.arange(n)+.5)/n).repeat(2*len(batch))
            value=model.values(xi,d,state).reshape(len(batch),2,n,4);target=reference_right(xi,d,state).reshape(len(batch),2,n,4)
            joint=torch.sqrt((value-target).square().sum((2,3))/target.square().sum((2,3))).numpy()
            voltage=torch.sqrt((value[...,:2]-target[...,:2]).square().sum((2,3))/target[...,:2].square().sum((2,3))).numpy()
            ds=torch.tensor([r['d'] for r in batch]).repeat_interleave(2);ss=torch.tensor([0.,1.]).repeat(len(batch))
            v0,i0=complex_channels(model.values(torch.zeros_like(ds),ds,ss));aa=torch.tensor([r['a'] for r in batch]).repeat_interleave(2)
            pred=(torch.exp(-2*CFG.gamma*aa)*(1-i0)).numpy().reshape(-1,2)
            for j,r in enumerate(batch):
                exact=[wave_reference(r['length'],r['switch_fraction'],s)[0] for s in (0,1)]
                for s in (0,1):rows.append(dict(id=r['id'],split=r['split'],state=s,d=r['d'],a=r['a'],reference_real=exact[s].real,reference_imag=exact[s].imag,predicted_real=pred[j,s].real,predicted_imag=pred[j,s].imag,complex_R_error=float(abs(pred[j,s]-exact[s])),joint_right_relative_L2=float(joint[j,s]),voltage_right_relative_L2=float(voltage[j,s])))
                em,pm=phase_metrics(*exact),phase_metrics(*pred[j]);pairs.append(dict(id=r['id'],split=r['split'],exact_phase_valid=em['phase_valid'],predicted_phase_valid=pm['phase_valid'],exact_separation=em['separation_degrees'],predicted_separation=pm['separation_degrees'],exact_min_magnitude=em['min_magnitude'],predicted_min_magnitude=pm['min_magnitude'],error=float(max(abs(pred[j]-exact)))))
    groups={}
    for split in ('test_offgrid','test_blocked'):
        rr=[r for r in rows if r['split']==split];pp=[r for r in pairs if r['split']==split];rates=classification(pp,15,.8)
        groups[split]=dict(states=len(rr),designs=len(pp),median_joint_right_L2=float(np.median([r['joint_right_relative_L2'] for r in rr])),median_voltage_right_L2=float(np.median([r['voltage_right_relative_L2'] for r in rr])),R95=float(np.quantile([r['error'] for r in pp],.95)),decisions=rates)
        g=groups[split];g['deployment_gate_passed']=bool(g['R95']<=.03 and g['median_joint_right_L2']<=.05 and rates['actual_feasible']>0 and rates['actual_infeasible']>0 and rates['sensitivity']>=.9 and rates['specificity']>=.9)
    return rows,pairs,groups

def run(plan):
    assert plan['source_sha256']==sha(Path(__file__)) and plan['budget_helper_sha256']==sha(ROOT/'code/optimizer_control.py')
    assert plan['starting_weights']['sha256']==sha(PRIMARY/'pinn_seed-0_weights.json')
    if (OUT/'results.json').exists():raise RuntimeError('Completed diagnosis retained. No automatic rerun.')
    records=[]
    for level in plan['levels']:
        grid=budget_control.training_grid(level['training_designs'],17);initial=None
        for mode in plan['objectives']:
            folder=OUT/f"gap-{level['width']:.4f}"/mode;folder.mkdir(parents=True,exist_ok=True)
            if (folder/'result.json').exists():raise RuntimeError('Partial study exists. Inspect before resuming; no silent overwrite.')
            model,_=load(PRIMARY,'pinn',0);start_hash=vector_sha(model)
            if initial is None:initial=start_hash
            assert initial==start_hash
            began=time.perf_counter();target=reference_right(*grid).detach() if mode=='supervised' else None;reference_seconds=time.perf_counter()-began
            trace=[];calls=0
            def objective(m,g):
                nonlocal calls
                terms=components(m,g,target);calls+=1
                if calls==1 or calls%20==0:trace.append(dict(gradient_call=calls,**{k:float(v.detach()) for k,v in terms.items()}))
                return terms['physics' if mode=='physics' else 'data']
            # Reuse the already-tested budget/accepted-step implementation unchanged.
            with patch.object(budget_control,'physics_objective',objective):stats,accepted=budget_control.continue_model(model,grid,'lbfgs',1200)
            assert stats['evaluations']<=1200
            weights=dict(mode=mode,seed=0,width=64,protocol_sha256=sha(OUT/'frozen-protocol.json'),weights={k:v.detach().tolist() for k,v in model.state_dict().items()})
            (folder/'weights.json').write_text(json.dumps(weights))
            started=time.perf_counter();rows,pairs,groups=evaluate(model,plan['evaluation_designs']);evaluation_seconds=time.perf_counter()-started
            write_csv(folder/'states.csv',rows);write_csv(folder/'pairs.csv',pairs);write_csv(folder/'loss-history.csv',trace);write_csv(folder/'accepted-history.csv',accepted)
            result=dict(mode=mode,gap_width=level['width'],training_designs=level['training_count'],initial_vector_sha256=start_hash,weights_sha256=sha(folder/'weights.json'),training=stats,reference_generation_seconds=reference_seconds,evaluation_seconds=evaluation_seconds,groups=groups)
            (folder/'result.json').write_text(json.dumps(result,indent=2));records.append(result)
            print(json.dumps(dict(mode=mode,gap=level['width'],calls=stats['evaluations'],seconds=stats['seconds'],blocked=groups['test_blocked'])),flush=True)
    paired=all(records[i]['training']['evaluations']==records[i+1]['training']['evaluations'] for i in (0,2,4))
    p0,s0=records[:2];smax=records[-1];base=s0['groups']['test_blocked']['median_joint_right_L2']
    ratio=p0['groups']['test_blocked']['median_joint_right_L2']/max(base,1e-15);gap_ratio=smax['groups']['test_blocked']['median_joint_right_L2']/max(base,1e-15)
    evidence=dict(matched_calls_all_pairs=paired,fully_covered_supervised_field_gate=base<=.05,physics_to_supervised_ratio=ratio,gap_supervised_ratio=gap_ratio,
      objective_dependence_criterion=bool(paired and base<=.05 and ratio>=3),coverage_dependence_criterion=bool(paired and base<=.05 and gap_ratio>=3),
      monotone_physics_error=all(records[i]['groups']['test_blocked']['median_joint_right_L2']<=records[i+2]['groups']['test_blocked']['median_joint_right_L2'] for i in (0,2)),
      monotone_supervised_error=all(records[i]['groups']['test_blocked']['median_joint_right_L2']<=records[i+2]['groups']['test_blocked']['median_joint_right_L2'] for i in (1,3)))
    result=dict(status='All six historically informed continuations reported',protocol_sha256=sha(OUT/'frozen-protocol.json'),records=records,criteria=evidence,interpretation='Conditional objective and coverage contrasts; a single seed and reused diagnostic cohorts. Full results, failed gates and nonmonotone outcomes remain visible. No unique finer mechanism or remedy success asserted automatically.')
    (OUT/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(evidence),flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-only',action='store_true');args=parser.parse_args()
    torch.set_default_dtype(torch.float64);torch.set_num_threads(1);plan=freeze()
    print(json.dumps(dict(protocol_sha256=sha(OUT/'frozen-protocol.json'),levels=[dict(width=l['width'],count=l['training_count']) for l in plan['levels']])),flush=True)
    if not args.freeze_only:run(plan)
