import unittest
import numpy as np
from scripts.expand_training import augment


class ExpansionTests(unittest.TestCase):
    def test_horizontal_flip_corrects_only_x_and_preserves_box(self):
        image = np.zeros((40,80,3),dtype=np.uint8)
        image[:,:20] = 100
        transformed,rows = augment(image,['3 0.2 0.7 0.1 0.15'],43)
        self.assertEqual(transformed.shape,image.shape)
        values = rows[0].split()
        self.assertEqual(values[0],'3')
        self.assertAlmostEqual(float(values[1]),.8)
        self.assertEqual(values[2:],['0.7','0.1','0.15'])
        self.assertGreater(transformed[:,-20:].mean(),transformed[:,:20].mean())
        self.assertEqual(augment(image,[],43)[1],[])
