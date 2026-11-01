import unittest

import numpy as np

from traffic_cnn.tiling import merge, tile_windows


class TilingTest(unittest.TestCase):
    def test_windows_cover_frame_with_overlap(self):
        windows = tile_windows(1360, 765, 640, 0.2)
        covered = np.zeros((765, 1360), bool)
        for x1, y1, x2, y2 in windows:
            self.assertLessEqual(x2, 1360)
            self.assertLessEqual(y2, 765)
            covered[y1:y2, x1:x2] = True
        self.assertTrue(covered.all())
        self.assertEqual(tile_windows(500, 400, 640), [(0, 0, 500, 400)])

    def test_merge_removes_duplicate_and_clipped_boxes(self):
        boxes = np.array([[100, 100, 140, 120], [101, 100, 141, 121], [100, 100, 118, 120], [300, 300, 340, 320]], np.float32)
        scores = np.array([0.9, 0.8, 0.7, 0.6], np.float32)
        classes = np.array([0, 1, 0, 2])
        kept, kept_scores, kept_classes = merge(boxes, scores, classes, iou=0.5, ios=0.8)
        self.assertEqual(len(kept), 2)
        self.assertEqual(kept_classes.tolist(), [0, 2])
        kept, _, _ = merge(boxes, scores, classes, iou=0.5, ios=0.8, agnostic=False)
        self.assertEqual(len(kept), 3)  # class-wise: the van duplicate survives


if __name__ == '__main__':
    unittest.main()
