import tempfile
import unittest
from pathlib import Path
from PIL import Image
import yaml
from scripts.audit_dataset import audit

class DatasetAuditTests(unittest.TestCase):
    def corpus(self,root):
        for i,split in enumerate(['train','val','test']):
            (root/'images'/split).mkdir(parents=True);(root/'labels'/split).mkdir(parents=True)
            Image.new('RGB',(20,20),(i*70,0,0)).save(root/'images'/split/'a.png')
            (root/'labels'/split/'a.txt').write_text('0 0.5 0.5 0.5 0.5\n')
        config=root/'data.yaml';config.write_text(yaml.safe_dump(dict(path=str(root),train='images/train',val='images/val',test='images/test',names={0:'car'})))
        return config
    def test_counts_and_corrupt_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=self.corpus(root)
            self.assertEqual(audit(config)['splits']['train']['boxes_by_class'],{'car':1})
            (root/'labels/train/a.txt').write_text('0 0.1 0.5 0.5 0.5\n')
            with self.assertRaisesRegex(ValueError,'Invalid class/box'):audit(config)
    def test_cross_split_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=self.corpus(root)
            (root/'images/test/a.png').write_bytes((root/'images/train/a.png').read_bytes())
            with self.assertRaisesRegex(ValueError,'Cross-split duplicate'):audit(config)
