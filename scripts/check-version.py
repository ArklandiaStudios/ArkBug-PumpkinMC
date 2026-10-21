#!/usr/bin/env python3
"""Startup companion: check the actual binary without making game ticks wait."""
from pathlib import Path
import argparse, time
from compatibility import ROOT, GitHub, decisions, identify, read_catalog, write_json

def check(binary, output, api=None):
    catalog = read_catalog()
    build = identify(binary, catalog)
    report = {'schema': 1, 'checked_at': int(time.time()), 'server_version': None,
              'applied_fixes': [], 'github_status': 'unknown_build', 'upstream_included': {}}
    if build is None:
        write_json(output, report)
        print('[ArkBug] Binaire inconnu : aucun correctif ArkBug déclaré actif.', flush=True)
        return report
    report.update(build)
    report['github_status'] = 'checking'
    # Display depends on compiled patches, never on availability of GitHub.
    write_json(output, report)
    try:
        api = api or GitHub(catalog['repository'], ROOT / 'github-cache')
        proofs = decisions(api, catalog, build['base_commit'])
        report['upstream_included'] = {key: proof for key, proof in proofs.items() if proof}
        report['github_status'] = 'verified'
        # A compiled patch cannot be undone by hiding its chat line. Normal
        # prepared builds already exclude these patches before compilation.
        report['rebuild_required'] = [issue for issue in build['applied_fixes'] if proofs.get(str(issue))]
    except Exception as error:
        report['github_status'] = 'unavailable'
        report['github_error'] = type(error).__name__
    report['checked_at'] = int(time.time())
    write_json(output, report)
    print(f"[ArkBug] Version {build['server_version']} ; GitHub : {report['github_status']}.", flush=True)
    if report.get('rebuild_required'):
        print('[ArkBug] Reconstruction nécessaire pour retirer un correctif déjà compilé.', flush=True)
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    check(arguments.binary, arguments.output)
