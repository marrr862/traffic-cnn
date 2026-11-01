import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from PIL import Image
import scripts.prepare_visdrone as preparation

class DatasetTests(unittest.TestCase):
    def image(self,color):
        buf=io.BytesIO()
        Image.new('RGB',(100,80),color).save(buf,format='JPEG')
        return buf.getvalue()
    def test_conversion_and_duplicate_exclusion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'data/archives').mkdir(parents=True)
            (root/'configs').mkdir()
            (root/'reports').mkdir()
            for split,color in [('test-dev','red'),('val','green'),('train','blue')]:
                prefix=f'VisDrone2019-DET-{split}'
                with zipfile.ZipFile(root/f'data/archives/{prefix}.zip','w') as archive:
                    archive.writestr(f'{prefix}/images/000001_1.jpg',self.image(color))
                    archive.writestr(f'{prefix}/annotations/000001_1.txt',
                                     '-5,10,25,20,1,4,0,0\n0,0,10,10,0,4,0,0\n0,0,10,10,1,1,0,0\n20,20,20,20,1,9,0,0')
                    if split=='train':
                        archive.writestr(f'{prefix}/images/000002_2.jpg',self.image('red'))
                        archive.writestr(f'{prefix}/annotations/000002_2.txt','0,0,10,10,1,4,0,0')
            original=preparation.ROOT
            try:
                preparation.ROOT=root
                preparation.prepare(pilot_size=1)
            finally:
                preparation.ROOT=original
            report=json.loads((root/'reports/dataset.json').read_text())
            self.assertEqual(report['splits']['train']['images'],1)
            self.assertEqual(len(report['duplicates_excluded']),1)
            self.assertEqual(report['splits']['test']['boxes_by_class'],{'car':1,'bus':1})
            rows=(root/'data/visdrone-vehicles/labels/test/000001_1.txt').read_text().splitlines()
            self.assertEqual(rows[0],'0 0.10000000 0.25000000 0.20000000 0.25000000')
            self.assertEqual(report['pilot']['images'],1)
