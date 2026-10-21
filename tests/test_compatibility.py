import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import compatibility as compatibility

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

checker = module('checker', 'scripts/check-version.py')
preparer = module('preparer', 'scripts/prepare-engine.py')
BASE = 'a' * 40
MERGE = 'b' * 40

class FakeGitHub:
    def __init__(self, merged=True, comparison='ahead', memory=True):
        self.merged, self.comparison, self.memory = merged, comparison, memory
    def get(self, path, immutable=False):
        if path.endswith('/files?per_page=100'):
            return [{'filename':'src/fix.rs','status':'modified'}]
        if path.startswith('commits/'):
            return {'sha': path.removeprefix('commits/')}
        if path.startswith('pulls/'):
            return {'merged': self.merged and not path.endswith('/2'), 'state': 'closed', 'merge_commit_sha': MERGE}
        if path.startswith('compare/'):
            return {'status': self.comparison}
        raise AssertionError(path)
    def source(self, commit, path):
        if not self.memory:
            return 'player: ArcSwap<Option<Arc<Player>>>'
        return 'player: Mutex<Option<Weak<dyn InventoryPlayer>>>' if 'sync_handler' in path else 'player: ArcSwap<Weak<Player>>'

class CompatibilityTests(unittest.TestCase):
    def test_new_gameplay_fixes_require_all_source_checks(self):
        source=ROOT/('pumpkin' if (ROOT/'pumpkin').exists() else 'engine-src')
        for issue in [3516,4089,3972,4123,3847,3918,3933,3969,4063,4090,3989,3065,3716,3698,3730,2016,4045,3902,3571,3510,3367,3511,3512]:
            fix=next(fix for fix in compatibility.read_catalog()['fixes'] if fix['issue']==issue)
            api=FakeGitHub(merged=False)
            api.source=lambda commit,path:(source/path).read_text()
            self.assertIsNotNone(compatibility.upstream_proof(api,fix,BASE),issue)
            missing=fix['source_checks'][-1]['path']
            api.source=lambda commit,path:'' if path==missing else (source/path).read_text()
            self.assertIsNone(compatibility.upstream_proof(api,fix,BASE),issue)
    def test_closed_unmerged_pr_does_not_disable(self):
        self.assertIsNone(compatibility.upstream_proof(FakeGitHub(merged=False), {'issue':3844,'pull_requests':[1]}, BASE))
    def test_newer_merge_does_not_disable_old_server(self):
        self.assertIsNone(compatibility.upstream_proof(FakeGitHub(comparison='behind'), {'issue':3844,'pull_requests':[1]}, BASE))
    def test_divergent_branch_does_not_disable(self):
        self.assertIsNone(compatibility.upstream_proof(FakeGitHub(comparison='diverged'), {'issue':3844,'pull_requests':[1]}, BASE))
    def test_ancestor_merge_is_proven(self):
        proof = compatibility.upstream_proof(FakeGitHub(), {'issue':3844,'pull_requests':[1]}, BASE)
        self.assertEqual(proof['commit'], MERGE)
    def test_reverted_or_changed_merged_code_is_not_assumed_fixed(self):
        api = FakeGitHub()
        api.source = lambda commit,path: 'fixed' if commit==MERGE else 'old implementation'
        self.assertIsNone(compatibility.upstream_proof(api, {'issue':3844,'pull_requests':[1]}, BASE))
    def test_memory_requires_weak_references_in_all_three_places(self):
        self.assertIsNotNone(compatibility.upstream_proof(FakeGitHub(), {'issue':4048}, BASE))
        self.assertIsNone(compatibility.upstream_proof(FakeGitHub(memory=False), {'issue':4048}, BASE))
        api = FakeGitHub()
        original = api.source
        api.source = lambda commit,path: 'player: Mutex<Option<Arc<dyn InventoryPlayer>>>' if 'sync_handler' in path else original(commit,path)
        self.assertIsNone(compatibility.upstream_proof(api, {'issue':4048}, BASE))
    def test_unknown_binary_cannot_inherit_known_version_fixes(self):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary) / 'pumpkin'
            binary.write_bytes(b'different binary')
            self.assertIsNone(compatibility.identify(binary, compatibility.read_catalog()))
    def test_github_outage_preserves_confirmed_compiled_fixes(self):
        with tempfile.TemporaryDirectory() as temporary:
            build = {'server_version':'test','base_commit':BASE,'applied_fixes':[3844]}
            api = FakeGitHub()
            api.get = lambda *args,**kwargs: (_ for _ in ()).throw(ConnectionError())
            with patch.object(checker, 'identify', return_value=build):
                result = checker.check(Path(temporary)/'pumpkin',Path(temporary)/'status.json',api)
            self.assertEqual(result['applied_fixes'], [3844])
            self.assertEqual(result['github_status'], 'unavailable')
    def test_binary_with_compiled_duplicate_requires_real_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            build = {'server_version':'test','base_commit':BASE,'applied_fixes':[3844]}
            with patch.object(checker,'identify',return_value=build), patch.object(checker,'decisions',return_value={'3844':{'method':'merged_ancestor'}}):
                result = checker.check('unused',Path(temporary)/'status.json',FakeGitHub())
            self.assertEqual(result['applied_fixes'], [3844])
            self.assertEqual(result['rebuild_required'], [3844])
    def test_preparation_omits_integrated_patches_and_applies_only_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            subprocess.run(['git','init','-q',str(source)],check=True)
            (source/'crates/pumpkin').mkdir(parents=True)
            (source/'Cargo.toml').write_text('[workspace.package]\nversion="0.2.0+26.3"\n')
            (source/'crates/pumpkin/Cargo.toml').write_text('[package]\nname="pumpkin"\nversion.workspace=true\n')
            for issue in [3844,3759,4048]:
                (source/f'fix{issue}').write_text('upstream\n' if issue != 3759 else 'missing\n')
            subprocess.run(['git','-C',str(source),'add','.'],check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=ArkBug Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
            fix = root/'missing.patch'
            fix.write_text('diff --git a/fix3759 b/fix3759\n--- a/fix3759\n+++ b/fix3759\n@@ -1 +1 @@\n-missing\n+fixed\n')
            catalog = {'repository':'Pumpkin-MC/Pumpkin','fixes':[
                {'issue':3844,'pull_requests':[1],'patch':str(root/'must-not-read-3844.patch')},
                {'issue':3759,'pull_requests':[2],'patch':str(fix)},
                {'issue':4048,'pull_requests':[],'patch':str(root/'must-not-read-4048.patch')},
            ]}
            with patch.object(preparer,'read_catalog',return_value=catalog):
                result = preparer.prepare(source,FakeGitHub())
            self.assertEqual(result['applied_fixes'],[3759])
            self.assertEqual(set(result['upstream_included']),{'3844','4048'})
            self.assertEqual((source/'fix3759').read_text(),'fixed\n')
            self.assertEqual((source/'fix3844').read_text(),'upstream\n')
            self.assertNotIn('.p3844',result['server_version'])
            self.assertIn('.p3759',result['server_version'])

    def test_shared_correction_applied_once_for_two_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'source';source.mkdir()
            subprocess.run(['git','init','-q',str(source)],check=True)
            (source/'crates/pumpkin').mkdir(parents=True)
            (source/'Cargo.toml').write_text('[workspace.package]\nversion="0.2.0"\n')
            (source/'crates/pumpkin/Cargo.toml').write_text('[package]\nversion.workspace=true\n')
            (source/'shared').write_text('old\n')
            subprocess.run(['git','-C',str(source),'add','.'],check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
            correction=Path(temporary)/'shared.patch'
            correction.write_text('diff --git a/shared b/shared\n--- a/shared\n+++ b/shared\n@@ -1 +1 @@\n-old\n+fixed\n')
            catalog={'repository':'Pumpkin-MC/Pumpkin','fixes':[{'issue':i,'patch':str(correction)} for i in [2016,4045]]}
            with patch.object(preparer,'read_catalog',return_value=catalog), patch.object(preparer,'decisions',return_value={'2016':None,'4045':None}):
                result=preparer.prepare(source,FakeGitHub())
            self.assertEqual(result['applied_fixes'],[2016,4045])
            self.assertEqual((source/'shared').read_text(),'fixed\n')

    def ordered_patch_fixture(self, broken=False):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source';source.mkdir()
            subprocess.run(['git','init','-q',str(source)],check=True)
            (source/'crates/pumpkin').mkdir(parents=True)
            (source/'Cargo.toml').write_text('[workspace.package]\nversion="0.2.0"\n')
            (source/'crates/pumpkin/Cargo.toml').write_text('[package]\nversion.workspace=true\n')
            (source/'shared').write_text('original\n')
            subprocess.run(['git','-C',str(source),'add','.'],check=True)
            subprocess.run(['git','-C',str(source),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
            catalog={'repository':'Pumpkin-MC/Pumpkin','fixes':[]}
            for issue,old,new in [(1,'original','first'),(2,'invalid' if broken else 'first','second')]:
                patch_file=root/f'{issue}.patch'
                patch_file.write_text(f'diff --git a/shared b/shared\n--- a/shared\n+++ b/shared\n@@ -1 +1 @@\n-{old}\n+{new}\n')
                catalog['fixes'].append({'issue':issue,'patch':str(patch_file)})
            with patch.object(preparer,'read_catalog',return_value=catalog):
                if broken:
                    with self.assertRaises(subprocess.CalledProcessError):preparer.prepare(source,FakeGitHub())
                    self.assertEqual((source/'shared').read_text(),'original\n')
                    self.assertEqual(subprocess.check_output(['git','-C',str(source),'status','--porcelain']),b'')
                else:
                    result=preparer.prepare(source,FakeGitHub())
                    self.assertEqual(result['applied_fixes'],[1,2])
                    self.assertEqual((source/'shared').read_text(),'second\n')
    def test_overlapping_patches_apply_in_order(self):
        self.ordered_patch_fixture()
    def test_later_incompatible_patch_leaves_worktree_untouched(self):
        self.ordered_patch_fixture(broken=True)

if __name__ == '__main__':
    unittest.main()
