import unittest
import numpy as np
from traffic_cnn.calibration import Calibration, SpeedEstimator, homography, point_in_polygon, speed_statistics
from traffic_cnn.traffic_state import density, level_of_service, fundamental_check
from traffic_cnn.flow import flow_windows

QUAD = [[1252, 787], [2298, 803], [5039, 2159], [-550, 2159]]


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.c = Calibration.from_rectangle(QUAD, 25, 250, lanes=4)

    def test_corners_map_to_rectangle(self):
        world = self.c.to_world(QUAD)
        np.testing.assert_allclose(world, [[0, 0], [25, 0], [25, 250], [0, 250]], atol=1e-6)

    def test_round_trip(self):
        points = np.array([[1800, 1000], [2000, 1500], [700, 2000]])
        np.testing.assert_allclose(self.c.to_image(self.c.to_world(points)), points, atol=1e-6)

    def test_degenerate_points_rejected(self):
        with self.assertRaises(ValueError):
            homography([[0, 0], [1, 1], [2, 2], [3, 3]], [[0, 0], [1, 0], [1, 1], [0, 1]])
        with self.assertRaises(ValueError):
            Calibration.from_rectangle(QUAD, 0, 250)

    def test_polygon(self):
        self.assertTrue(point_in_polygon((5, 5), [[0, 0], [10, 0], [10, 10], [0, 10]]))
        self.assertFalse(point_in_polygon((15, 5), [[0, 0], [10, 0], [10, 10], [0, 10]]))

    def test_known_speed_recovered_with_jitter(self):
        rng = np.random.default_rng(0)
        estimator = SpeedEstimator(self.c, 25)
        for frame in range(50):  # 25 m/s = 90 km/h along the road
            image = self.c.to_image([[8, 40 + 25 * frame / 25]])[0] + rng.normal(0, 2, 2)
            value = estimator.update(1, image, frame)
        self.assertAlmostEqual(value, 90, delta=4)
        self.assertAlmostEqual(estimator.track_speed(1), 90, delta=4)

    def test_no_speed_before_min_span_and_outside_zone(self):
        estimator = SpeedEstimator(self.c, 25)
        self.assertIsNone(estimator.update(1, self.c.to_image([[5, 50]])[0], 0))
        self.assertIsNone(estimator.update(2, (10, 10), 0))

    def test_implausible_speeds_are_counted(self):
        estimator = SpeedEstimator(self.c, 25)
        for frame in range(40):  # 120 m/s = 432 km/h, e.g. an accelerated video
            estimator.update(1, self.c.to_image([[8, 5 + 120 * frame / 25]])[0], frame)
        self.assertIsNone(estimator.track_speed(1))
        self.assertGreater(estimator.rejected, 10)
        self.assertEqual(estimator.rejected_share(), 1.0)

    def test_stationary_vehicle_zero_speed(self):
        estimator = SpeedEstimator(self.c, 25)
        point = self.c.to_image([[5, 100]])[0]
        for frame in range(30):
            value = estimator.update(1, point, frame)
        self.assertAlmostEqual(value, 0, places=6)


class TrafficStateTests(unittest.TestCase):
    def test_density_and_los(self):
        k, k_lane = density(10, 250, 4)
        self.assertEqual((k, k_lane), (40, 10))
        self.assertEqual(level_of_service(k_lane), 'B')
        self.assertEqual(level_of_service(5), 'A')
        self.assertEqual(level_of_service(40), 'F')
        self.assertIsNone(level_of_service(None))

    def test_speed_statistics(self):
        stats = speed_statistics([60, 120, None])
        self.assertEqual(stats['time_mean_kmh'], 90)
        self.assertAlmostEqual(stats['space_mean_kmh'], 80)

    def test_fundamental(self):
        check = fundamental_check(2000, 20, 100)
        self.assertEqual(check['density_times_speed'], 2000)
        self.assertEqual(check['relative_difference'], 0)

    def test_windows_with_speed_and_density(self):
        frames = [dict(frame=n, visible_tracked_vehicles=1, density_per_km=4.0) for n in range(20)]
        events = [dict(frame=1, direction='negative_to_positive', speed_kmh='60'),
                  dict(frame=2, direction='negative_to_positive', speed_kmh=120.0),
                  dict(frame=15, direction='positive_to_negative', speed_kmh='')]
        windows = flow_windows(events, frames, 2, 5)
        self.assertEqual(windows[0]['mean_speed_kmh'], 90)
        self.assertAlmostEqual(windows[0]['space_mean_speed_kmh'], 80)
        self.assertIsNone(windows[1]['mean_speed_kmh'])
        self.assertEqual(windows[1]['mean_density_per_km'], 4)


if __name__ == '__main__':
    unittest.main()
