#!/usr/bin/env python3
"""Prepare a clean upstream worktree, omitting fixes proven present on GitHub.

No update, build, restart or running-binary mutation happens implicitly. Refuse
an incompatible patch rather than rewriting unfamiliar upstream code.
"""
from pathlib import Path
import argparse, json, os, re, subprocess, tempfile, tomllib
from compatibility import ROOT, GitHub, decisions, identify, read_catalog, write_json

def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()

def prepare(source, api=None):
    source = Path(source).resolve()
    if git(source, 'status', '--porcelain'):
        raise RuntimeError('A clean, separate upstream worktree is required')
    commit = git(source, 'rev-parse', 'HEAD')
    catalog = read_catalog()
    api = api or GitHub(catalog['repository'], ROOT / 'github-cache')
    proofs = decisions(api, catalog, commit)  # Failure leaves sources untouched.
    selected = [fix for fix in catalog['fixes'] if not proofs[str(fix['issue'])]]
    # Multiple reports may share one upstream correction. Apply it once.
    patches = list(dict.fromkeys(str(ROOT / fix['patch']) for fix in selected))
    if patches:
        # Later fixes can modify the same lines as an earlier fix. Validate
        # their ordered result in a private index before touching the worktree.
        with tempfile.TemporaryDirectory(prefix='arkbug-patches-') as temporary:
            environment = dict(os.environ, GIT_INDEX_FILE=str(Path(temporary)/'index'))
            subprocess.run(['git','-C',str(source),'read-tree','HEAD'],env=environment,check=True)
            for patch in patches:
                subprocess.run(['git','-C',str(source),'apply','--cached',patch],env=environment,check=True)
        for patch in patches:
            subprocess.run(['git','-C',str(source),'apply',patch],check=True)
    package = source / 'crates/pumpkin/Cargo.toml'
    workspace = tomllib.loads((source / 'Cargo.toml').read_text())
    metadata = tomllib.loads(package.read_text())['package']
    base_version = metadata['version'] if isinstance(metadata['version'], str) else workspace['workspace']['package']['version']
    ids = [fix['issue'] for fix in selected]
    suffix = f'arkbug.{commit}' + ''.join(f'.p{issue}' for issue in ids)
    version = base_version + ('.' if '+' in base_version else '+') + suffix
    content, replacements = re.subn(r'(?m)^version(?:\.workspace)?\s*=.*$', f'version = "{version}"', package.read_text(), count=1)
    if replacements != 1:
        raise RuntimeError('Cannot identify the Pumpkin package version')
    package.write_text(content)
    manifest = {'server_version': version, 'base_commit': commit, 'applied_fixes': ids,
                'upstream_included': {key: proof for key, proof in proofs.items() if proof}}
    write_json(source / 'arkbug-build.json', manifest)
    return manifest

def register(source, binary):
    manifest = json.loads((Path(source) / 'arkbug-build.json').read_text())
    catalog = read_catalog()
    import hashlib
    with Path(binary).open('rb') as stream:
        manifest['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    catalog['builds'] = [build for build in catalog['builds'] if build['sha256'] != manifest['sha256']]
    catalog['builds'].append(manifest)
    write_json(ROOT / 'fixes.json', catalog)
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--register-binary', type=Path)
    args = parser.parse_args()
    result = register(args.source, args.register_binary) if args.register_binary else prepare(args.source)
    print(json.dumps(result, indent=2))
