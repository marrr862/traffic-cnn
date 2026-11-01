"""Download the three publicly documented VisDrone archives with retries."""
import hashlib
import json
import urllib.request
from pathlib import Path
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://github.com/ultralytics/assets/releases/download/v0.0.0/'


def main():
    directory = ROOT/'data/archives'
    directory.mkdir(parents=True,exist_ok=True)
    reference = json.loads((ROOT/'reports/dataset.json').read_text()) if (ROOT/'reports/dataset.json').exists() else {}
    for split in ['train','val','test-dev']:
        name = f'VisDrone2019-DET-{split}.zip'
        path = directory/name
        expected = reference.get('archive_sha256',{}).get(split)
        if not path.exists():
            temporary = path.with_suffix('.download')
            for attempt in range(3):
                try:
                    print(f'Downloading {name}',flush=True)
                    urllib.request.urlretrieve(BASE+name,temporary)
                    with zipfile.ZipFile(temporary) as archive:
                        bad = archive.testzip()
                        if bad:
                            raise ValueError(f'Corrupt ZIP member {bad}')
                    temporary.replace(path)
                    break
                except Exception:
                    temporary.unlink(missing_ok=True)
                    if attempt == 2:
                        raise
                    time.sleep(2)
        checksum = hashlib.sha256()
        with path.open('rb') as archive_handle:
            for block in iter(lambda:archive_handle.read(1024*1024),b''):
                checksum.update(block)
        digest = checksum.hexdigest()
        if expected and digest != expected:
            raise ValueError(f'SHA-256 mismatch: {path}; retain file for inspection')
        print(f'{name}: {digest}',flush=True)


if __name__ == '__main__':
    main()
