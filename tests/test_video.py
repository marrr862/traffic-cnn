"""Run manually after smoke training: verifies video I/O, not vehicle accuracy."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
import sys
import csv
import hashlib

WEIGHTS = next((p for p in [Path('runs/experiments/vehicle-finetune-full/weights/best.pt'),Path('runs/train/smoke/weights/best.pt')] if p.exists()),None)

class VideoSmokeTest(unittest.TestCase):
    @unittest.skipUnless(WEIGHTS is not None, 'requires locally trained weights')
    def test_video_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'blank.mp4'
            writer = cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),10,(320,240))
            self.assertTrue(writer.isOpened())
            for _ in range(5):
                writer.write(np.zeros((240,320,3),dtype=np.uint8))
            writer.release()
            subprocess.run([sys.executable,'-m','traffic_cnn.cli','analyze','--video',str(source),
                            '--weights',str(WEIGHTS),'--output',str(root/'out')],check=True)
            result = json.loads((root/'out'/'summary.json').read_text())
            self.assertEqual(result['frames'],5)
            self.assertAlmostEqual(result['duration_seconds'],0.5)
            self.assertEqual(result['source_sha256'],hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(result['crossings'],0)
            self.assertEqual(result['direction_labels']['negative_to_positive'],'Դեպի կադրի ստորին եզր')
            self.assertEqual(result['mean_visible_tracked_vehicles'],0)
            with (root/'out'/'flow_windows.csv').open() as f:
                windows = list(csv.DictReader(f))
            self.assertEqual(len(windows),1)
            self.assertEqual(float(windows[0]['duration_seconds']),.5)
            self.assertEqual(int(windows[0]['crossings']),0)
            self.assertEqual(json.loads((root/'out'/'progress.json').read_text())['status'],'complete')
            with (root/'out'/'frame_stats.csv').open() as f:
                statistics = list(csv.DictReader(f))
            self.assertEqual(len(statistics),5)
            self.assertEqual(float(statistics[-1]['time_seconds']),.4)
            self.assertTrue((root/'out'/'tracks_summary.csv').exists())
            cap = cv2.VideoCapture(str(root/'out'/'annotated.mp4'))
            self.assertTrue(cap.read()[0])
            cap.release()
            self.assertTrue((root/'out'/'crossings.csv').exists())
            self.assertTrue((root/'out'/'tracks.csv').exists())
