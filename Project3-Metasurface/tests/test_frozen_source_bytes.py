"""Frozen scientific receipts must survive an ordinary Git checkout on every OS."""
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

class FrozenSourceBytes(unittest.TestCase):
    def test_gap_source_helper_and_initializer_match_frozen_receipts(self):
        plan=json.loads((ROOT/'outputs/gap-objective-diagnosis/frozen-protocol.json').read_text())
        self.assertEqual(sha(ROOT/'code/gap_objective_diagnosis.py'),plan['source_sha256'])
        self.assertEqual(sha(ROOT/'code/optimizer_control.py'),plan['budget_helper_sha256'])
        self.assertEqual(sha(ROOT/plan['starting_weights']['path']),plan['starting_weights']['sha256'])

    def test_optimizer_source_and_initializers_match_frozen_receipts(self):
        plan=json.loads((ROOT/'outputs/optimizer-continuation-control/frozen-protocol.json').read_text())
        self.assertEqual(sha(ROOT/'code/optimizer_control.py'),plan['source_sha256'])
        for record in plan['starting_weights'].values():self.assertEqual(sha(ROOT/record['path']),record['sha256'])

    def check_sources(self,study):
        folder=ROOT/'outputs'/study;plan=json.loads((folder/'frozen-protocol.json').read_text())
        redactions=json.loads((ROOT/'publication-redactions.json').read_text())['files']
        for name,expected in plan['source_hashes'].items():
            with self.subTest(study=study,source=name):
                actual=sha(ROOT/'code'/name)
                if actual==expected:continue
                revision=folder/'serialization-revision.json'
                if name=='run_residual_error_budget.py' and revision.exists():
                    known=json.loads(revision.read_text())
                    if expected==known['original_source_sha256'] and actual==known['revised_source_sha256']:continue
                matches=[r for r in redactions if r['path']=='code/'+name and r['original_sha256']==expected and r['published_sha256']==actual and r['numeric_code_unchanged']]
                self.assertEqual(len(matches),1,'Source byte mismatch is neither frozen nor a documented publication-only redaction.')

    def test_boundary_source_bytes_match_or_have_documented_redaction(self):self.check_sources('hard-boundary-control')
    def test_residual_source_bytes_match_or_have_documented_revision(self):self.check_sources('residual-error-budget')

if __name__=='__main__':unittest.main()
