"""Download the trained models (GitHub release) and the two Roboflow demo videos into their expected paths."""
import argparse
import hashlib
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'https://github.com/marrr862/traffic-cnn/releases/download/v1.0/'
VIDEOS = 'https://media.roboflow.com/supervision/video-examples/'
MODELS = {
    'vehicle-road-yolov8s': '32288ed57a169467f4f205064dd5c1f32b24e176a4f6bc4c5104fed870a59d5f',
    'vehicle-road-combined': 'b0e8c74a91134b85523983c5dba322d0d5fd88e8f176684e2b4e639899a73055',
    'vehicle-hires-960': 'b7003b2a7f4541df9286b38b0f83099351b8bd0f24d812e5ff6bc8fdd9ba9894',
}
DEMOS = {
    'vehicles.mp4': 'ac81100d9310bd4e9c02bc0b13b6492781d009742ced347766b2601be3c44ad4',
    'vehicles-2.mp4': 'f1fb78b80c67f9185c91f7ce280e42e2c923810646172b7cf2fe90ea998e0062',
}


def sha256(path):
    checksum = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):
            checksum.update(block)
    return checksum.hexdigest()


def fetch(url,path,expected):
    if path.exists() and sha256(path) == expected:
        print(f'{path.relative_to(ROOT)}: already present',flush=True)
        return
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix('.download')
    for attempt in range(3):
        try:
            print(f'Downloading {url}',flush=True)
            urllib.request.urlretrieve(url,temporary)
            if sha256(temporary) != expected:
                raise ValueError(f'SHA-256 mismatch: {url}')
            temporary.replace(path)
            print(f'{path.relative_to(ROOT)}: {expected}',flush=True)
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-only',action='store_true')
    parser.add_argument('--videos-only',action='store_true')
    args = parser.parse_args()
    if not args.videos_only:
        for name,expected in MODELS.items():
            fetch(RELEASE+f'{name}.pt',ROOT/'runs/experiments'/name/'weights/best.pt',expected)
    if not args.models_only:
        for name,expected in DEMOS.items():
            fetch(VIDEOS+name,ROOT/'data/video'/name,expected)


if __name__ == '__main__':
    main()
