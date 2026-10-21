"""Prepare an isolated reproduction workspace. Does not execute training.

Canonical outputs remain untouched. Commands run inside the new workspace so
analysis uses the same outputs that its training/evaluation commands produce.
"""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
STUDIES={'primary':'switched-surrogate','optimizer':'optimizer-continuation-control','boundary':'hard-boundary-control','residual':'residual-error-budget','gap':'gap-objective-diagnosis'}
COMMANDS={
 'primary':['python code/switched_surrogate.py','python code/summarize_switched_surrogate.py','python code/plot_switched_surrogate.py'],
 'optimizer':['python code/optimizer_control.py'],
 'boundary':['python code/hard_boundary_control.py','python code/evaluate_hard_boundary.py'],
 'residual':['python code/run_residual_error_budget.py'],
 'gap':['python code/gap_objective_diagnosis.py'],
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--study',choices=STUDIES,required=True);p.add_argument('--destination',type=Path,required=True);args=p.parse_args()
    dest=args.destination.resolve();assert not dest.exists(),'Choose a new, nonexistent destination; no overwrite or deletion is performed.'
    assert dest!=ROOT and not ROOT.is_relative_to(dest) and not dest.is_relative_to(ROOT),'Destination must be outside the canonical project and must not contain it.'
    target=STUDIES[args.study];dest.mkdir(parents=True)
    shutil.copytree(ROOT/'code',dest/'code',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ('tests','requirements.txt','requirements-science.txt'):
        source=ROOT/name
        if source.is_dir():shutil.copytree(source,dest/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        elif source.exists():shutil.copy2(source,dest/name)
    for source in (ROOT/'outputs').iterdir():
        if source.name==target:continue
        if source.is_dir():shutil.copytree(source,dest/'outputs'/source.name)
        else:
            (dest/'outputs').mkdir(exist_ok=True);shutil.copy2(source,dest/'outputs'/source.name)
    output=dest/'outputs'/target;output.mkdir(parents=True,exist_ok=True)
    # Keep exact geometry/criteria, but omit completed weights and result files.
    for name in ('frozen-protocol.json','serialization-revision.json','split-amendment.json'):
        if (ROOT/'outputs'/target/name).exists():shutil.copy2(ROOT/'outputs'/target/name,output/name)
    publication=ROOT/'publication-redactions.json';changes=[]
    if args.study in ('residual','boundary') and publication.exists():
        frozen=output/'frozen-protocol.json';plan=json.loads(frozen.read_text());redactions=json.loads(publication.read_text())['files']
        for filename,expected in list(plan['source_hashes'].items()):
            actual=sha(dest/'code'/filename)
            if actual==expected:continue
            revision=output/'serialization-revision.json'
            if filename=='run_residual_error_budget.py' and revision.exists():
                known=json.loads(revision.read_text())
                if expected==known['original_source_sha256'] and actual==known['revised_source_sha256']:continue
            entry=next((r for r in redactions if r['path']=='code/'+filename and r['original_sha256']==expected and r['published_sha256']==actual),None)
            assert entry and entry['numeric_code_unchanged'],'Unexplained source difference; stop rather than bypass source verification.'
            changes.append(entry);plan['source_hashes'][filename]=actual
        if changes:
            shutil.copy2(frozen,output/'frozen-protocol.original.json');plan['reproduction_only_publication_redactions']=changes;frozen.write_text(json.dumps(plan,indent=2))
    receipt=dict(study=args.study,canonical_project_untouched=True,source_protocol_sha256=sha(ROOT/'outputs'/target/'frozen-protocol.json'),prepared_protocol_sha256=sha(output/'frozen-protocol.json'),publication_redactions=changes,working_directory=str(dest),commands=COMMANDS[args.study],training_executed=False)
    (dest/'REPRODUCTION-PLAN.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
