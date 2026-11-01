import unittest
from traffic_cnn.counting import DuplicateGuard, overlap_ratio

TRUCK = (100, 100, 300, 200)
CAB = (100, 110, 160, 200)


class DuplicateGuardTests(unittest.TestCase):
    def test_overlap_ratio(self):
        self.assertEqual(overlap_ratio(TRUCK, CAB), 1.0)
        self.assertEqual(overlap_ratio((0, 0, 10, 10), (20, 20, 30, 30)), 0.0)
        self.assertAlmostEqual(overlap_ratio((0, 0, 10, 10), (5, 0, 15, 10)), 0.5)

    def test_second_id_of_same_vehicle_is_rejected(self):
        g = DuplicateGuard()
        self.assertIsNone(g.duplicate_of(1, TRUCK, 'negative_to_positive', 10, {1: TRUCK, 2: CAB}))
        self.assertEqual(g.duplicate_of(2, CAB, 'negative_to_positive', 12, {1: TRUCK, 2: CAB}), 1)

    def test_following_vehicle_in_same_lane_is_counted(self):
        # First demo video: tracks 2 and 10 cross 10 frames and 20 px apart, yet are two cars.
        g = DuplicateGuard()
        self.assertIsNone(g.duplicate_of(2, (1480, 1240, 1570, 1300), 'negative_to_positive', 8, {2: (1480, 1240, 1570, 1300)}))
        boxes = {2: (1490, 1400, 1580, 1460), 10: (1500, 1240, 1590, 1300)}
        self.assertIsNone(g.duplicate_of(10, boxes[10], 'negative_to_positive', 18, boxes))

    def test_requires_same_direction_and_visibility(self):
        g = DuplicateGuard()
        g.duplicate_of(1, TRUCK, 'negative_to_positive', 10, {1: TRUCK})
        self.assertIsNone(g.duplicate_of(2, CAB, 'positive_to_negative', 11, {1: TRUCK, 2: CAB}))
        self.assertIsNone(g.duplicate_of(3, CAB, 'negative_to_positive', 12, {3: CAB}))

    def test_window_and_forget(self):
        g = DuplicateGuard(window=5)
        g.duplicate_of(1, TRUCK, 'negative_to_positive', 0, {1: TRUCK})
        self.assertIsNone(g.duplicate_of(2, CAB, 'negative_to_positive', 6, {1: TRUCK, 2: CAB}))
        g.forget(20)
        self.assertEqual(g.crossed, {})


if __name__ == '__main__':
    unittest.main()
