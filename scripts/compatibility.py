"""Identify installed builds and prove that an upstream fix belongs to their base.

Issue state and release dates are deliberately not used as evidence. A merge
must be an ancestor of the exact base commit; the memory fix requires all three
weak back-references, not a related fix to mob AI.
"""
from pathlib import Path
import base64, hashlib, json, re, time, urllib.error, urllib.request

ROOT = Path(__file__).resolve().parent.parent
MEMORY_FILES = [
    ('crates/pumpkin/src/net/java/mod.rs', r'player:\s*ArcSwap<\s*Weak<Player>\s*>'),
    ('crates/pumpkin/src/net/bedrock/mod.rs', r'player:\s*ArcSwap<\s*Weak<Player>\s*>'),
    ('crates/pumpkin-inventory/src/sync_handler.rs', r'player:\s*Mutex<Option<Weak<dyn InventoryPlayer>>>'),
]

def read_catalog():
    return json.loads((ROOT / 'fixes.json').read_text())

def identify(binary, catalog):
    with Path(binary).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return next((dict(build) for build in catalog['builds'] if build['sha256'] == digest), None)

class GitHub:
    def __init__(self, repository, cache):
        self.repository = repository
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)

    def get(self, path, immutable=False):
        filename = self.cache / (hashlib.sha256(path.encode()).hexdigest() + '.json')
        if filename.exists():
            cached = json.loads(filename.read_text())
            if immutable or time.time() - cached['at'] < 3600:
                return cached['value']
        url = f'https://api.github.com/repos/{self.repository}/{path}'
        request = urllib.request.Request(url, headers={
            'User-Agent': 'ArkBug-version-check', 'Accept': 'application/vnd.github+json',
        })
        with urllib.request.urlopen(request, timeout=4) as response:
            value = json.load(response)
        temporary = filename.with_suffix('.tmp')
        temporary.write_text(json.dumps({'at': time.time(), 'value': value}))
        temporary.replace(filename)
        return value

    def source(self, commit, path):
        data = self.get(f'contents/{path}?ref={commit}', immutable=True)
        if data.get('encoding') != 'base64':
            raise ValueError('GitHub did not return source content')
        return base64.b64decode(data['content']).decode()

def upstream_proof(api, fix, commit):
    """None means unproven, not that the upstream server is necessarily buggy."""
    for number in fix.get('pull_requests', []):
        pull = api.get(f'pulls/{number}')
        merged = pull.get('merge_commit_sha')
        if pull.get('merged') is not True or not re.fullmatch(r'[a-f0-9]{40}', merged or ''):
            continue
        comparison = api.get(f'compare/{merged}...{commit}', immutable=True)
        if comparison.get('status') in ('ahead', 'identical'):
            # An ancestor merge could subsequently have been reverted. Require
            # its Rust source files to still match the merged implementation.
            # Changed implementations need review instead of an optimistic skip.
            files = api.get(f'pulls/{number}/files?per_page=100')
            if not isinstance(files, list) or len(files) >= 100:
                continue
            paths = [entry['filename'] for entry in files if entry['filename'].endswith('.rs') and entry.get('status') != 'removed']
            if not paths:
                continue
            try:
                unchanged = all(api.source(merged, path) == api.source(commit, path) for path in paths)
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                unchanged = False
            if unchanged:
                return {'method': 'merged_ancestor', 'pull_request': number, 'commit': merged, 'verified_files': paths}
    if fix.get('source_checks'):
        checked = []
        for entry in fix['source_checks']:
            try:
                source = api.source(commit, entry['path'])
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    return None
                raise
            source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
            if not all(re.search(pattern, source, re.S) for pattern in entry['patterns']):
                return None
            checked.append(entry['path'])
        return {'method': 'source_checks', 'commit': commit, 'files': checked}
    if fix['issue'] == 4048:
        checked = []
        for path, pattern in MEMORY_FILES:
            try:
                source = api.source(commit, path).replace('std::sync::', '')
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    return None
                raise
            # Comments cannot serve as evidence of an actual field declaration.
            source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
            if not re.search(pattern, source):
                return None
            checked.append(path)
        return {'method': 'weak_back_references', 'commit': commit, 'files': checked}
    return None

def verify_base(api, commit):
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('An exact 40-character upstream commit is required')
    if api.get(f'commits/{commit}', immutable=True).get('sha') != commit:
        raise ValueError('The base commit was not verified on GitHub')

def decisions(api, catalog, commit):
    verify_base(api, commit)
    return {str(fix['issue']): upstream_proof(api, fix, commit) for fix in catalog['fixes']}

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)
