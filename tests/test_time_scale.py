import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from traffic_cnn.motion import MotionMeter

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = ROOT/'runs/experiments/vehicle-finetune-full/weights/best.pt'
VIDEO = ROOT/'data/video/vehicles.mp4'


class MotionMeterTests(unittest.TestCase):
    def test_median_step_in_box_heights(self):
        m = MotionMeter()
        for frame in range(5):
            m.update(1, (0, 10*frame), 100, frame)   # 0.1 box heights per frame
            m.update(2, (50, 50), 100, frame)        # parked, ignored
        s = m.summary(25, 25/4)
        self.assertEqual(s['samples'], 4)
        self.assertAlmostEqual(s['median_box_heights_per_frame'], 0.1)
        self.assertAlmostEqual(s['per_video_second'], 2.5)
        self.assertAlmostEqual(s['per_real_second'], 0.625)

    def test_gaps_are_not_steps(self):
        m = MotionMeter()
        m.update(1, (0, 0), 100, 0)
        m.update(1, (0, 50), 100, 3)
        self.assertEqual(m.summary(25, 25)['samples'], 0)
        m.forget(10)
        self.assertEqual(m.last, {})


@unittest.skipUnless(WEIGHTS.exists() and VIDEO.exists(), 'requires local weights and demo video')
class TimeScaleTests(unittest.TestCase):
    def run_cli(self, root, name, seconds, *extra):
        out = Path(root)/name
        subprocess.run([sys.executable, '-m', 'traffic_cnn.cli', 'analyze', '--video', str(VIDEO), '--weights', str(WEIGHTS),
                        '--output', str(out), '--line', '0', '1296', '3839', '1296', '--max-seconds', str(seconds),
                        '--calibration', str(ROOT/'configs/calibration-vehicles.json'), *extra],
                       check=True, capture_output=True, cwd=ROOT)
        return json.loads((out/'summary.json').read_text())

    def test_time_scale_converts_to_real_time(self):
        with tempfile.TemporaryDirectory() as root:
            # --max-seconds is real time: both runs process the same 75 frames.
            normal = self.run_cli(root, 'normal', 3)
            scaled = self.run_cli(root, 'scaled', 12, '--time-scale', '4')
        self.assertEqual(normal['frames'], 75)
        self.assertEqual(scaled['frames'], 75)
        self.assertAlmostEqual(scaled['time_fps'], normal['source_fps']/4)
        self.assertAlmostEqual(scaled['duration_seconds'], 4*normal['duration_seconds'])
        self.assertEqual(scaled['crossings'], normal['crossings'])
        self.assertAlmostEqual(scaled['flow_vehicles_per_hour']*4, normal['flow_vehicles_per_hour'])
        self.assertAlmostEqual(scaled['density']['mean_density_per_km'], normal['density']['mean_density_per_km'])
        self.assertAlmostEqual(scaled['motion']['median_box_heights_per_frame'], normal['motion']['median_box_heights_per_frame'])
        # The speed window is in real seconds, so it spans fewer frames: the ratio is close to, not exactly, 4.
        ratio = normal['speed']['all_tracks']['median_kmh']/scaled['speed']['all_tracks']['median_kmh']
        self.assertAlmostEqual(ratio, 4, delta=0.6)


if __name__ == '__main__':
    unittest.main()
