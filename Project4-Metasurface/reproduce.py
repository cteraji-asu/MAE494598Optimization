"""One-command reproduction in a new directory; never overwrite retained results."""
from pathlib import Path
import argparse, shutil, subprocess, sys, json
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent

def prepare(destination):
    destination=destination.resolve()
    if destination.exists():raise SystemExit('Destination already exists. Choose a new directory.')
    if destination==ROOT or ROOT in destination.parents or destination in ROOT.parents:
        raise SystemExit('Destination must be outside the canonical Project4 directory and its parents.')
    destination.mkdir(parents=True)
    target=destination/ROOT.name;target.mkdir()
    for folder in ['code','tests','site']:
        shutil.copytree(ROOT/folder,target/folder,ignore=shutil.ignore_patterns('__pycache__','qa'))
    for name in ['index.md','two-pinn-findings.md','smooth-pinn-findings.md','RUBRIC-CROSSWALK.md','README.md','requirements.txt','reproduce.py']:
        if (ROOT/name).exists():shutil.copy2(ROOT/name,target/name)
    (target/'review').mkdir()
    for name in ['surrogate-bonus-audit-2026-11-16.md','rubric-audit-2026-11-16.md']:
        if (ROOT/'review'/name).exists():shutil.copy2(ROOT/'review'/name,target/'review'/name)
    assets=target/'assets';assets.mkdir()
    for pattern in ['*-protocol.json','*-freeze-receipt.json']:
        for path in (ROOT/'assets').glob(pattern):shutil.copy2(path,assets/path.name)
    prior=ROOT.parent/'Project3-Metasurface'
    shutil.copytree(prior/'code',destination/'Project3-Metasurface'/'code',ignore=shutil.ignore_patterns('__pycache__'))
    for path in (prior/'outputs').rglob('frozen-protocol.json'):
        dest=destination/'Project3-Metasurface'/path.relative_to(prior);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    return target

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,default=ROOT.parent.parent/('reproduce-project4-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    p.add_argument('--core-python',default=sys.executable)
    p.add_argument('--pinn-python',default=sys.executable)
    p.add_argument('--prepare-only',action='store_true')
    args=p.parse_args();target=prepare(args.destination)
    commands=[
        [args.core_python,str(target/'code/run_design.py')],
        [args.core_python,str(target/'code/verify_gradient_sweep.py'),'--output',str(target/'review/gradient-sweep-final-2026-11-16.json')],
        [args.pinn_python,str(target/'code/two_pinn_study.py')],
        [args.pinn_python,str(target/'code/two_pinn_audit.py')],
    ]
    if (target/'code/smooth_pinn_study.py').exists():commands.append([args.pinn_python,str(target/'code/smooth_pinn_study.py')])
    if (target/'code/smooth_pinn_audit.py').exists():commands.append([args.pinn_python,str(target/'code/smooth_pinn_audit.py')])
    commands.extend([
        [args.core_python,'-m','unittest','discover','-s',str(target/'tests'),'-p','test_wave_fem.py','-v'],
        [args.pinn_python,'-m','unittest','discover','-s',str(target/'tests'),'-p','test_two_pinn.py','-v'],
    ])
    if (target/'tests/test_smooth_pinn.py').exists():commands.append([args.pinn_python,'-m','unittest','discover','-s',str(target/'tests'),'-p','test_smooth_pinn.py','-v'])
    commands.extend([
        [args.pinn_python,str(target/'code/export_saved_surrogate_gradients.py'),'--output',str(target/'review/saved-surrogate-gradients-2026-11-16.json')],
        [args.core_python,str(target/'code/restricted_fe_bridge.py'),'--output',str(target/'review/restricted-fe-bridge-2026-11-16.json')],
        [args.core_python,str(target/'code/compare_saved_surrogate_fe.py'),'--model',str(target/'review/saved-surrogate-gradients-2026-11-16.json'),'--fe',str(target/'review/restricted-fe-bridge-2026-11-16.json'),'--output',str(target/'review/surrogate-fe-comparison-2026-11-16.json')],
    ])
    # 23 Nov supplemental runs: extra ladder rungs, gradient/cost/KKT checks and post hoc
    # sensitivity studies on the unchanged solver; saved surrogates inside SLSQP.
    commands.extend([
        [args.core_python,str(target/'code/rubric_studies.py')],
        [args.pinn_python,str(target/'code/surrogate_optimizer_loop.py')],
        [args.core_python,'-m','unittest','discover','-s',str(target/'tests'),'-p','test_rubric_evidence.py','-v'],
    ])
    commands.extend([[args.core_python,str(target/'code/build_report.py')],[args.core_python,str(target/'code/audit_artifacts.py')]])
    node=shutil.which('node')
    if node:commands.append([node,str(target/'tests/test_viewer_ledger.cjs')])
    plan={'destination':str(target),'commands':commands,'note':'Retained canonical outputs are untouched. Fixed protocol files are copied before training. Timing and timestamps will differ.'}
    (target/'REPRODUCTION-PLAN.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(json.dumps(plan,indent=2),flush=True)
    if args.prepare_only:return
    for command in commands:
        print('\nRUN '+subprocess.list2cmdline(command),flush=True)
        subprocess.run(command,cwd=target.parent,check=True)
    print('\nComplete. Open '+str(target/'preview.html')+' through a local HTTP server.',flush=True)

if __name__=='__main__':main()
