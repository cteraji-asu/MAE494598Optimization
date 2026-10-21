"""Freeze and evaluate a signed error budget on historical saved checkpoints."""
import csv
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from residual_error_budget import ROOT,CFG,load_checkpoint,model_case,check_known_fields
from switched_line import wave_reference,phase_metrics,write_csv
from switched_surrogate import classification

OUT=ROOT/'outputs/residual-error-budget'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def freeze():
    path=OUT/'frozen-protocol.json';OUT.mkdir(exist_ok=True)
    if path.exists():return json.loads(path.read_text())
    cases=[]
    for mode in ('pinn','supervised'):
        for seed in (0,1,2):cases.append((f'primary-{mode}-{seed}',ROOT/'outputs/switched-surrogate',mode,seed))
    for seed in (0,1,2):cases.append((f'covered-pinn-{seed}',ROOT/'outputs/neural-coverage-control/reallocated','pinn',seed))
    cases.append(('representability-supervised-0',ROOT/'outputs/representability-control/seed-0','supervised',0))
    for arm in ('lbfgs','adam'):cases.append((f'optimizer-{arm}-0',ROOT/f'outputs/optimizer-continuation-control/seed-0/{arm}','pinn',0))
    plan=dict(status='Historical diagnostic only. Existing test cohorts have already been inspected; no pristine holdout claim.',
      hypothesis='Port and/or short residuals, amplified by the finite BVP transfer map, may account for reflection failure. Interior residual contributions and cancellation are competing explanations.',
      fitting=False,quadrature_orders=[32,64,128],maximum_identity_disagreement=1e-9,maximum_64_to_128_disagreement=1e-8,
      maximum_bound_tolerance=1e-9,contribution_statistics_error_floor=1e-6,
      reporting='Signed complex contributions, sum, magnitude shares, cancellation, gain and boundary-corrected/interior-corrected counterfactuals. Do not infer a Hessian condition number or sum component magnitudes as errors.',
      counterfactuals='All are reported, not selected: remove port, short, both boundaries, interior. They are a posteriori diagnostic corrections with quadrature cost, not trained remedies.',
      source_hashes={p.name:sha(p) for p in [Path(__file__),ROOT/'code/residual_error_budget.py',ROOT/'code/switched_surrogate.py',ROOT/'code/switched_line.py']},
      known_field_validation='32 polynomial and isolated forcing cases, compared with independent wave reference, before saved-checkpoint attribution.',models=[])
    for name,folder,mode,seed in cases:
        weights=folder/f'{mode}_seed-{seed}_weights.json';states=folder/f'{mode}_seed-{seed}_states.csv'
        with states.open(newline='') as f:rows=[r for r in csv.DictReader(f) if r['split'].startswith('test')]
        plan['models'].append(dict(name=name,weights=str(weights.relative_to(ROOT)),weights_sha256=sha(weights),states=str(states.relative_to(ROOT)),states_sha256=sha(states),state_cases=len(rows)))
    path.write_text(json.dumps(plan,indent=2))
    print(json.dumps(dict(frozen_protocol_sha256=sha(path),models=len(cases),historical_state_cases=sum(r['state_cases'] for r in plan['models']))),flush=True)
    return plan

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-only',action='store_true');args=parser.parse_args()
    torch.set_num_threads(1);plan=freeze()
    for filename,digest in plan['source_hashes'].items():
        current=sha(ROOT/'code'/filename)
        if current!=digest:
            revision=json.loads((OUT/'serialization-revision.json').read_text())
            assert filename=='run_residual_error_budget.py' and digest==revision['original_source_sha256'] and current==revision['revised_source_sha256']
    if args.freeze_only:return
    if (OUT/'summary.json').exists():raise RuntimeError('Completed diagnostic retained; no automatic rerun.')
    known=check_known_fields();assert max(r['maximum_identity_error'] for r in known)<1e-11
    summaries=[];started=time.perf_counter()
    for case in plan['models']:
        weights=ROOT/case['weights'];path=ROOT/case['states']
        assert sha(weights)==case['weights_sha256'] and sha(path)==case['states_sha256']
        model=load_checkpoint(weights);rows=[];pred_pairs={};max_id=0.;max_quad=0.;max_bound=0.
        with path.open(newline='') as f:historical=[r for r in csv.DictReader(f) if r['split'].startswith('test')]
        for old in historical:
            d,a,state=float(old['d']),float(old['a']),int(old['state'])
            exact=wave_reference(a+d,a/(a+d),state,CFG)[0]
            totals=[]
            for order in plan['quadrature_orders']:
                result,pred=model_case(model,d,a,state,order);totals.append(result['total'])
            delta=pred-exact;disagreement=abs(result['total']-delta);quad=abs(totals[-1]-totals[-2])
            bound_violation=max(0,abs(delta)-result['error_bound'])
            max_id=max(max_id,disagreement);max_quad=max(max_quad,quad);max_bound=max(max_bound,bound_violation)
            if disagreement>1e-9 or quad>1e-8 or bound_violation>1e-9:raise RuntimeError((case['name'],old['id'],state,disagreement,quad,bound_violation))
            magnitudes={k:abs(result[k]) for k in ('port','short','interior')}
            sum_abs=sum(magnitudes.values());denom=abs(delta)
            row=dict(model=case['name'],id=old['id'],split=old['split'],state=state,d=d,a=a,exact_R_real=exact.real,exact_R_imag=exact.imag,predicted_R_real=pred.real,predicted_R_imag=pred.imag,complex_R_error=denom,identity_disagreement=disagreement,quadrature_64_to_128=quad,
                inverse_abs_D=result['inverse_abs_D'],error_gain=result['absolute_error_gain'],physics_eta=result['continuous_physics_eta'],error_bound=result['error_bound'],boundary_matrix_cond2=result['boundary_matrix_cond2'],loss_scaled_boundary_matrix_cond2=result['loss_scaled_boundary_matrix_cond2'],
                boundary_magnitude_share=(magnitudes['port']+magnitudes['short'])/sum_abs if sum_abs else 0.,
                cancellation_ratio=sum_abs/denom if denom>1e-6 else None)
            for key in ('port','short','interior','total'):
                z=result[key];row.update({key+'_real':z.real,key+'_imag':z.imag,key+'_abs':abs(z)})
                row[key+'_signed_projection']=(z*delta.conjugate()).real/(denom*denom) if denom>1e-6 else None
            variants=dict(original=pred,remove_port=pred-result['port'],remove_short=pred-result['short'],remove_boundaries=pred-result['port']-result['short'],remove_interior=pred-result['interior'])
            for key,z in variants.items():row[key+'_error']=abs(z-exact)
            rows.append(row)
            pair=pred_pairs.setdefault(old['id'],dict(split=old['split'],exact={},variants={key:{} for key in variants}))
            pair['exact'][state]=exact
            for key,z in variants.items():pair['variants'][key][state]=z
        write_csv(OUT/(case['name']+'-states.csv'),rows)
        groups=[]
        for split in ('test_offgrid','test_blocked'):
            ss=[r for r in rows if r['split']==split];decisions={}
            for variant in ('original','remove_port','remove_short','remove_boundaries','remove_interior'):
                pp=[]
                for item in pred_pairs.values():
                    if item['split']!=split:continue
                    actual=phase_metrics(item['exact'][0],item['exact'][1]);pred=phase_metrics(item['variants'][variant][0],item['variants'][variant][1])
                    pp.append(dict(exact_phase_valid=actual['phase_valid'],predicted_phase_valid=pred['phase_valid'],exact_separation=actual['separation_degrees'],predicted_separation=pred['separation_degrees'],exact_min_magnitude=actual['min_magnitude'],predicted_min_magnitude=pred['min_magnitude']))
                decisions[variant]=classification(pp,15,.8)
            high=[r for r in ss if r['complex_R_error']>1e-6]
            groups.append(dict(split=split,state_cases=len(ss),median_R_error=float(np.median([r['complex_R_error'] for r in ss])),
                median_boundary_magnitude_share=float(np.median([r['boundary_magnitude_share'] for r in high])),
                median_cancellation_ratio=float(np.median([r['cancellation_ratio'] for r in high])),
                median_boundary_signed_projection=float(np.median([r['port_signed_projection']+r['short_signed_projection'] for r in high])),
                median_interior_signed_projection=float(np.median([r['interior_signed_projection'] for r in high])),
                median_remove_boundaries_error=float(np.median([r['remove_boundaries_error'] for r in ss])),
                median_remove_interior_error=float(np.median([r['remove_interior_error'] for r in ss])),
                boundary_removal_reduces_error=int(sum(r['remove_boundaries_error']<r['complex_R_error'] for r in ss)),
                median_inverse_abs_D=float(np.median([r['inverse_abs_D'] for r in ss])),maximum_output_error_gain=max(r['error_gain'] for r in ss),decisions=decisions))
        summary=dict(model=case['name'],maximum_identity_disagreement=max_id,maximum_64_to_128_disagreement=max_quad,maximum_bound_violation=max_bound,regions=groups)
        summaries.append(summary)
        print(json.dumps(dict(model=case['name'],max_identity_disagreement=max_id,max_quadrature_difference=max_quad,blocked=groups[-1])),flush=True)
    result=dict(status='Historical signed diagnostic complete; no fitting',protocol_sha256=sha(OUT/'frozen-protocol.json'),seconds=time.perf_counter()-started,models=summaries,known_field_maximum_error=max(r['maximum_identity_error'] for r in known))
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(completed_models=len(summaries),seconds=result['seconds'])),flush=True)

if __name__=='__main__':main()
