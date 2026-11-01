"""Moving a project must preserve source identity and nested UI results."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.rebase_paths import main


class PortabilityTests(unittest.TestCase):
    def test_nested_results_and_idempotent_rebase(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root/'reports').mkdir()
            nested = root/'outputs/ui-example/results'
            nested.mkdir(parents=True)
            old = Path('/old/project')
            training = dict(data=str(old/'configs/data.yaml'),best_weights=str(old/'runs/experiments/full/weights/best.pt'),training_directory=str(old/'runs/experiments/full'))
            (root/'reports/vehicle-full.json').write_text(json.dumps(training))
            (root/'reports/recommended-model.json').write_text(json.dumps(dict(name='vehicle-full',weights=training['best_weights'])))
            summary = dict(weights=training['best_weights'],source_video=str(old/'outputs/ui-example/input.mp4'),source_sha256='a'*64,line=[0,10,100,10])
            path = nested/'summary.json'
            path.write_text(json.dumps(summary))
            main(root)
            first = json.loads(path.read_text())
            self.assertEqual(first['source_video'],str(root/'outputs/ui-example/input.mp4'))
            self.assertEqual(first['weights'],str(root/'runs/experiments/full/weights/best.pt'))
            self.assertEqual(first['source_sha256'],summary['source_sha256'])
            self.assertEqual(json.loads((root/'reports/recommended-model.json').read_text())['weights'],first['weights'])
            main(root)
            self.assertEqual(json.loads(path.read_text()),first)
            self.assertEqual(json.loads((root/'reports/vehicle-full.json').read_text())['original_project_root'],str(old))
