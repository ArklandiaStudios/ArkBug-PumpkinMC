#!/usr/bin/env python3
"""Apply this release's exact patch set to its clean, pinned Pumpkin base."""
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parent.parent


def prepare(source):
    source = source.resolve()
    release = json.loads((ROOT / 'release.json').read_text())
    catalog = json.loads((ROOT / 'fixes.json').read_text())
    head = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if head != release['pumpkin_base_commit']:
        raise ValueError('Checkout the exact Pumpkin base commit from release.json first')
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain']):
        raise ValueError('Use a clean, separate Pumpkin checkout')
    fixes = {fix['issue']: fix for fix in catalog['fixes']}
    patches = list(dict.fromkeys(ROOT / fixes[issue]['patch']
                                  for issue in release['applied_fixes']))
    package = source / 'crates/pumpkin/Cargo.toml'
    content = package.read_text()
    updated, count = re.subn(
        r'(?m)^version(?:\.workspace)?\s*=.*$',
        f'version = "{release["pumpkin_version"]}"', content, count=1)
    if count != 1:
        raise ValueError('Cannot find the Pumpkin package version')
    lock_path = source / 'Cargo.lock'
    lock = lock_path.read_text()
    locked = next(item['version'] for item in tomllib.loads(lock)['package']
                  if item['name'] == 'pumpkin')
    before = f'name = "pumpkin"\nversion = "{locked}"'
    after = f'name = "pumpkin"\nversion = "{release["pumpkin_version"]}"'
    if lock.count(before) != 1:
        raise ValueError('Cannot identify the Pumpkin lockfile entry')
    # Check overlapping patches in order without touching the checkout first.
    with tempfile.TemporaryDirectory(prefix='arkbug-release-index-') as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / 'index'))
        subprocess.run(['git', '-C', str(source), 'read-tree', 'HEAD'], env=env, check=True)
        for patch in patches:
            subprocess.run(['git', '-C', str(source), 'apply', '--cached', str(patch)],
                           env=env, check=True)
    for patch in patches:
        subprocess.run(['git', '-C', str(source), 'apply', str(patch)], check=True)
    package.write_text(updated)
    lock_path.write_text(lock.replace(before, after, 1))
    metadata = {'server_version': release['pumpkin_version'],
                'base_commit': head, 'applied_fixes': release['applied_fixes'],
                'upstream_included': {}}
    (source / 'arkbug-build.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'engine': metadata['server_version'],
                      'fixes': len(metadata['applied_fixes']), 'patches': len(patches)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    prepare(parser.parse_args().source)
