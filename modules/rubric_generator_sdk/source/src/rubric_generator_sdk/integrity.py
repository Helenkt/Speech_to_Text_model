import hashlib
import json
from pathlib import Path


def verify_runtime():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'runtime_manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Installed SDK file changed: '+name+'. Reinstall the release; do not edit hashes.')
    canonical=json.dumps(manifest['files'],sort_keys=True,separators=(',',':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
