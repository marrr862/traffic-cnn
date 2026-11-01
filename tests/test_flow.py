import unittest
from traffic_cnn.flow import flow_windows


class FlowTests(unittest.TestCase):
    def test_boundaries_empty_window_and_short_tail(self):
        frames = [dict(frame=n, visible_tracked_vehicles=n%3) for n in range(25)]
        events = [dict(frame=n, direction=d) for n,d in [(0,'negative_to_positive'),(20,'positive_to_negative'),(24,'negative_to_positive')]]
        windows = flow_windows(events, frames, 2, 5)
        self.assertEqual([w['crossings'] for w in windows], [1,0,2])
        self.assertEqual([w['frame_count'] for w in windows], [10,10,5])
        self.assertEqual(windows[-1]['duration_seconds'], 2.5)
        self.assertEqual(windows[-1]['event_rate_per_hour'], 2880)
        self.assertEqual(windows[-1]['positive_to_negative'], 1)
        self.assertAlmostEqual(windows[0]['mean_visible_tracked_vehicles'], .9)
        self.assertEqual(windows[0]['peak_visible_tracked_vehicles'], 2)

    def test_invalid_parameters_and_outside_event(self):
        frames = [dict(frame=0,visible_tracked_vehicles=0)]
        for fps, interval in [(0,5),(float('nan'),5),(2,0),(2,float('inf'))]:
            with self.assertRaises(ValueError):
                flow_windows([],frames,fps,interval)
        with self.assertRaises(ValueError):
            flow_windows([dict(frame=1,direction='negative_to_positive')],frames,2)
        with self.assertRaises(ValueError):
            flow_windows([],[],2)
