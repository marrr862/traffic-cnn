import unittest
from traffic_cnn.counting import LineCounter

class CountingTests(unittest.TestCase):
    def counter(self):
        return LineCounter((0,50),(100,50))
    def test_crossing_once_with_dead_band(self):
        c = self.counter()
        self.assertIsNone(c.update(1,(20,40),0))
        self.assertIsNone(c.update(1,(20,51),1))
        self.assertEqual(c.update(1,(20,60),2),'negative_to_positive')
        self.assertIsNone(c.update(1,(20,40),3))
    def test_outside_segment(self):
        c = self.counter()
        c.update(1,(110,40),0)
        self.assertIsNone(c.update(1,(110,60),1))
    def test_stale(self):
        c = self.counter()
        c.update(1,(20,40),0)
        self.assertIsNone(c.update(1,(20,60),100))
    def test_reverse(self):
        c = self.counter()
        c.update(2,(20,60),0)
        self.assertEqual(c.update(2,(20,40),1),'positive_to_negative')
    def test_same_side(self):
        c = self.counter()
        self.assertIsNone(c.update(2,(20,60),0))
        self.assertIsNone(c.update(2,(20,65),1))
    def test_invalid(self):
        with self.assertRaises(ValueError):
            LineCounter((0,0),(0,0))

if __name__ == '__main__':
    unittest.main()


class StartCrossingTests(unittest.TestCase):
    """Tracks first seen just past the line (line y=50, box height 40)."""
    def counter(self):
        return LineCounter((0,50),(100,50))

    def test_track_starting_past_line_and_moving_away_is_counted(self):
        # First demo video: the first truck appears 9 px past the line at frame 0.
        c = self.counter()
        self.assertIsNone(c.update(1,(20,59),0,size=40))
        self.assertIsNone(c.update(1,(20,65),1,size=40))
        self.assertEqual(c.update(1,(20,70),2,size=40),'negative_to_positive')
        self.assertIsNone(c.update(1,(20,90),3,size=40))

    def test_track_starting_in_dead_band(self):
        c = self.counter()
        self.assertIsNone(c.update(1,(20,49),0,size=40))
        self.assertIsNone(c.update(1,(20,42),1,size=40))   # 8 px: not yet a quarter of the box height
        self.assertEqual(c.update(1,(20,35),2,size=40),'positive_to_negative')

    def test_far_or_stationary_start_is_not_counted(self):
        c = self.counter()
        c.update(1,(20,80),0,size=40)          # 30 px > half of the box height
        self.assertIsNone(c.update(1,(20,100),2,size=40))
        c.update(2,(40,58),0,size=40)          # stays at the line
        for frame in range(1,30):
            self.assertIsNone(c.update(2,(40,60),frame,size=40))

    def test_start_moving_toward_line_is_counted_once_by_normal_crossing(self):
        c = self.counter()
        c.update(1,(20,58),0,size=40)
        self.assertEqual(c.update(1,(20,40),2,size=40),'positive_to_negative')
        self.assertIsNone(c.update(1,(20,20),3,size=40))

    def test_new_id_of_counted_vehicle_is_not_counted_again(self):
        c = self.counter()
        c.update(1,(20,40),0,size=40)
        self.assertEqual(c.update(1,(20,56),1,size=40),'negative_to_positive')
        # The tracker loses ID 1 and gives the same vehicle ID 2 a few frames later.
        c.update(2,(22,62),4,size=40)
        self.assertIsNone(c.update(2,(22,80),5,size=40))

    def test_disabled_without_size_and_off_segment(self):
        c = self.counter()
        c.update(1,(20,59),0)
        self.assertIsNone(c.update(1,(20,80),2))
        c.update(2,(120,59),0,size=40)
        self.assertIsNone(c.update(2,(120,80),2,size=40))
