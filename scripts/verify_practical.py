"""Verify and exercise the practical bundle in a fresh temporary location."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify(archive_path, run_tests=True):
    archive_path = Path(archive_path).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read('traffic-cnn/BUNDLE_MANIFEST.json'))
        for name, expected in manifest.items():
            member = Path(name)
            if member.is_absolute() or '..' in member.parts:
                raise ValueError(f'Unsafe manifest path: {name}')
            digest = hashlib.sha256()
            size = 0
            with archive.open('traffic-cnn/'+name) as source:
                for chunk in iter(lambda:source.read(1024*1024),b''):
                    digest.update(chunk)
                    size += len(chunk)
            if size != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                raise ValueError(f'Bundle checksum mismatch: {name}')
        if run_tests:
            with tempfile.TemporaryDirectory(prefix='traffic-practical-') as directory:
                # Extract only verified members, never arbitrary ZIP entries.
                for name in manifest:
                    archive.extract('traffic-cnn/'+name,directory)
                project = Path(directory)/'traffic-cnn'
                for command in [[sys.executable,'scripts/rebase_paths.py'],[sys.executable,'-m','unittest','discover','-s','tests','-v']]:
                    subprocess.run(command,cwd=project,check=True)
    result = dict(archive=str(archive_path),verified_files=len(manifest),bytes=archive_path.stat().st_size,relocated_tests=run_tests)
    print(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',nargs='?',default=str(ROOT/'deliverables/traffic-cnn-practical.zip'))
    parser.add_argument('--checksums-only',action='store_true')
    args = parser.parse_args()
    verify(args.archive,not args.checksums_only)
