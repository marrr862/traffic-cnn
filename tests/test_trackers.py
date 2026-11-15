import unittest
from traffic_cnn.cli import TRACKERS, tracker_settings


class TrackerSettingsTests(unittest.TestCase):
    def test_same_thresholds_for_every_tracker(self):
        for name in TRACKERS:
            settings = tracker_settings(name, 0.3, 0.1)
            self.assertEqual(settings['tracker_type'], name.removesuffix('-reid'))
            self.assertEqual((settings['track_high_thresh'], settings['new_track_thresh'], settings['track_low_thresh'], settings['track_buffer']), (0.3, 0.3, 0.1, 30))
            self.assertIn(settings.get('gmc_method', 'none'), ('none',))  # fixed cameras: no motion compensation

    def test_appearance_only_where_requested(self):
        self.assertFalse(tracker_settings('botsort', 0.3, 0.1)['with_reid'])
        self.assertTrue(tracker_settings('botsort-reid', 0.3, 0.1)['with_reid'])
        self.assertTrue(tracker_settings('deepocsort', 0.3, 0.1)['with_reid'])

    def test_unknown_tracker(self):
        with self.assertRaises(ValueError):
            tracker_settings('sort', 0.3, 0.1)


if __name__ == '__main__':
    unittest.main()
