import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
import cv2
import numpy as np
from traffic_cnn.sources import is_live, is_youtube, resolve, LatestFrameReader

WEIGHTS = next((p for p in Path('runs/experiments').glob('*/weights/best.pt')), None)


class FakeCapture:
    def __init__(self, n=20):
        self.n, self.i = n, 0
    def read(self):
        time.sleep(0.01)
        if self.i >= self.n:
            return False, None
        self.i += 1
        return True, np.full((48, 64, 3), self.i, np.uint8)
    def isOpened(self):
        return self.i < self.n


class SourceTests(unittest.TestCase):
    def test_classification(self):
        self.assertTrue(is_live('0'))
        self.assertTrue(is_live('rtsp://192.168.1.10/stream'))
        self.assertTrue(is_live('https://www.youtube.com/watch?v=abc'))
        self.assertFalse(is_live('data/video/vehicles.mp4'))
        self.assertTrue(is_youtube('https://youtu.be/abc'))
        self.assertEqual(resolve('2'), 2)
        self.assertEqual(resolve('rtsp://cam/1'), 'rtsp://cam/1')

    def test_latest_frame_reader_returns_new_frames(self):
        reader = LatestFrameReader(FakeCapture())
        ok, frame, stamp, seq = reader.read(0)
        self.assertTrue(ok)
        time.sleep(0.05)
        ok2, frame2, stamp2, seq2 = reader.read(seq)
        self.assertTrue(ok2)
        self.assertGreater(seq2, seq)
        self.assertGreaterEqual(stamp2, stamp)
        reader.stop()

    @unittest.skipUnless(WEIGHTS is not None, 'requires trained weights')
    def test_max_seconds_limits_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'clip.mp4'
            writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (320, 240))
            for _ in range(30):
                writer.write(np.zeros((240, 320, 3), np.uint8))
            writer.release()
            subprocess.run([sys.executable, '-m', 'traffic_cnn.cli', 'analyze', '--video', str(source), '--weights', str(WEIGHTS),
                            '--output', str(root/'out'), '--max-seconds', '1.0', '--device', 'cpu', '--imgsz', '320'], check=True)
            summary = json.loads((root/'out'/'summary.json').read_text())
            self.assertEqual(summary['frames'], 10)
            self.assertFalse(summary['live_source'])
            self.assertTrue((root/'out'/'preview.jpg').exists())


if __name__ == '__main__':
    unittest.main()
