import unittest
from traffic_cnn.calibration import Calibration, SpeedEstimator
from traffic_cnn.counting import LineCounter
from traffic_cnn.traffic_state import fundamental_check, plausibility_issues, vehicle_groups

QUAD = [[1252, 787], [2298, 803], [5039, 2159], [-550, 2159]]


class PlausibilityTests(unittest.TestCase):
    def test_realistic_highway_passes(self):
        check = fundamental_check(1500, 11, 120)
        self.assertEqual(plausibility_issues(120, 0, 0.0, 1500/4, check), [])

    def test_time_lapse_flow_detected_without_speeds(self):
        # Second demo video: about 38000 veh/h on three lanes, a single speed sample.
        issues = plausibility_issues(None, 0, 0.0, 38000/3, fundamental_check(38000, 39, 60))
        self.assertIn('flow_above_lane_capacity', issues)
        self.assertIn('flow_density_speed_mismatch', issues)

    def test_speed_reasons(self):
        self.assertEqual(plausibility_issues(170), ['median_speed_above_160'])
        self.assertEqual(plausibility_issues(None, 20, 0.5), ['speeds_above_250'])
        self.assertEqual(plausibility_issues(None, 5, 0.5), [])

    def test_no_flow_is_not_a_mismatch(self):
        self.assertEqual(plausibility_issues(None, 0, 0.0, 0, fundamental_check(0, 10, 50)), [])


class VehicleGroupTests(unittest.TestCase):
    def test_truck_and_bus_are_heavy(self):
        groups, share = vehicle_groups({'car': 6, 'van': 2, 'truck': 1, 'bus': 1})
        self.assertEqual(groups, {'light': 8, 'heavy': 2, 'motorcycle': 0})
        self.assertAlmostEqual(share, 0.2)

    def test_truck_bus_swap_keeps_groups(self):
        self.assertEqual(vehicle_groups({'car': 8, 'truck': 2}), vehicle_groups({'car': 8, 'bus': 2}))

    def test_empty_and_unknown_classes(self):
        self.assertEqual(vehicle_groups({})[1], None)
        groups, share = vehicle_groups({'tractor': 1, 'car': 1})
        self.assertEqual(groups['other'], 1)
        self.assertEqual(share, 0)


class BoundedStateTests(unittest.TestCase):
    def test_line_counter_forgets_stale_tracks(self):
        c = LineCounter((0, 50), (100, 50))
        c.update(1, (20, 40), 0)
        c.update(2, (30, 40), 90)
        c.forget(100)
        self.assertEqual(set(c.previous), {2})
        self.assertEqual(c.update(2, (30, 60), 101), 'negative_to_positive')

    def test_speed_estimator_forgets_but_keeps_track_median(self):
        speed = SpeedEstimator(Calibration.from_rectangle(QUAD, 25, 250, lanes=4), 25)
        for frame in range(30):
            speed.update(1, (1775, 1000 + 10*frame), frame)
        median = speed.track_speed(1)
        self.assertIsNotNone(median)
        speed.forget(10.0)
        self.assertNotIn(1, speed.points)
        self.assertIsNone(speed.current(1))
        self.assertEqual(speed.track_speed(1), median)


if __name__ == '__main__':
    unittest.main()


class RawSpeedTests(unittest.TestCase):
    def test_raw_median_includes_rejected(self):
        speed = SpeedEstimator(Calibration.from_rectangle(QUAD, 25, 250, lanes=4), 25, max_kmh=1)
        for frame in range(30):
            speed.update(1, (1775, 1000 + 10*frame), frame)
        self.assertIsNone(speed.track_speed(1))
        self.assertGreater(speed.raw_median(), 1)
        self.assertEqual(speed.rejected_share(), 1.0)


class SegmentShareTests(unittest.TestCase):
    def test_line_inside_and_outside_zone(self):
        c = Calibration.from_rectangle([[599, 710], [908, 710], [848, 1017], [167, 1017]], 10.8, 120, lanes=3)
        self.assertEqual(c.segment_share([380, 860, 890, 860]) > 0.9, True)
        self.assertEqual(c.segment_share([0, 648, 1919, 648]), 0)
        self.assertTrue(0 < c.segment_share([0, 860, 1919, 860]) < 0.5)
