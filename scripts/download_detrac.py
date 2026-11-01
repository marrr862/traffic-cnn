"""Fetch a fixed test-sequence prefix from the author's ZIP using HTTP ranges."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile
import time

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://drive.usercontent.google.com/download?id=1fQC6CEWOeL9pnJ4ZdD7U2gromcnWDRgm&export=download&confirm=t'
ANNOTATIONS = 'https://drive.usercontent.google.com/download?id=1zc8KZWUa3Cw0DbcFqTCMBmUZzbfuhGKr&export=download&confirm=t'

class RemoteZip(io.RawIOBase):
    def __init__(self, url):
        self.url, self.position = url, 0
        for attempt in range(5):
            response = urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=-22','Cache-Control':'no-cache'}),timeout=60)
            if response.status == 206: break
            payload = response.read(8192).decode('utf-8',errors='replace')
            response.close()
            if 'Quota exceeded' in payload: raise RuntimeError('Author Google Drive archive quota exceeded; retry later, not a dataset file')
            time.sleep(2)
        else: raise ValueError('Server must support byte ranges')
        self.size = int(response.headers['Content-Range'].split('/')[-1])
        response.close()
        self.cache = None
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position+offset if whence == 1 else self.size+offset
        return self.position
    def read(self, count=-1):
        count = self.size-self.position if count < 0 else min(count,self.size-self.position)
        if count <= 0: return b''
        start, stop = self.position, self.position+count
        if self.cache is None or not self.cache[0] <= start or stop > self.cache[0]+len(self.cache[1]):
            end = min(self.size,max(stop,start+8*1024*1024))-1
            for attempt in range(5):
                request = urllib.request.Request(self.url,headers={'Range':f'bytes={start}-{end}','Cache-Control':'no-cache'})
                with urllib.request.urlopen(request,timeout=60) as response:
                    if response.status == 206 and response.headers.get('Content-Range','').startswith(f'bytes {start}-'):
                        self.cache = (start,response.read())
                        break
                    if 'Quota exceeded' in response.read(8192).decode('utf-8',errors='replace'): raise RuntimeError('Author Google Drive archive quota exceeded; retry later')
                time.sleep(2)
            else: raise ValueError(f'Incorrect byte-range response for {start}-{end}')
        offset = start-self.cache[0]
        result = self.cache[1][offset:offset+count]
        if len(result) != count: raise IOError('Truncated range')
        self.position = stop
        return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sequence',default='MVI_39031')
    parser.add_argument('--frames',type=int,default=300)
    args = parser.parse_args()
    if args.frames < 1 or not args.sequence.startswith('MVI_') or not args.sequence[4:].isdigit():
        parser.error('Invalid sequence or frame count')
    destination = ROOT/'data/ua-detrac'/args.sequence
    destination.mkdir(parents=True,exist_ok=True)
    annotation_zip = ROOT/'data/ua-detrac/archives/test-annotations.zip'
    annotation_zip.parent.mkdir(parents=True,exist_ok=True)
    if not annotation_zip.exists():
        urllib.request.urlretrieve(ANNOTATIONS,annotation_zip)
    with zipfile.ZipFile(annotation_zip) as archive:
        xml = archive.read(f'DETRAC-Test-Annotations-XML/{args.sequence}.xml')
    (destination/'annotations.xml').write_bytes(xml)
    with zipfile.ZipFile(RemoteZip(URL)) as archive:
        prefix = f'DETRAC-Images/{args.sequence}/'
        entries = sorted(n for n in archive.namelist() if n.startswith(prefix) and n.lower().endswith('.jpg'))[:args.frames]
        if len(entries) != args.frames: raise ValueError('Insufficient sequence frames')
        manifest = {}
        for index,name in enumerate(entries):
            target = destination/Path(name).name
            if not target.exists():
                payload = archive.read(name)  # zipfile also verifies CRC.
                target.with_suffix('.tmp').write_bytes(payload)
                target.with_suffix('.tmp').replace(target)
            manifest[target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
            if (index+1)%50 == 0: print(f'{args.sequence}: {index+1}/{len(entries)}',flush=True)
    report = dict(sequence=args.sequence,frames=len(entries),selection='Fixed first frames of first alphabetic test sequence; chosen before inference',image_source=URL,annotation_source=ANNOTATIONS,author_page='https://sites.google.com/view/daweidu/projects/ua-detrac',xml_sha256=hashlib.sha256(xml).hexdigest(),images=manifest)
    (destination/'manifest.json').write_text(json.dumps(report,indent=2))
    print(destination,flush=True)

if __name__ == '__main__': main()
