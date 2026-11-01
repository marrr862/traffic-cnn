import unittest
from traffic_cnn.geometry import validate_line,direction_labels
from traffic_cnn.counting import LineCounter


class GeometryTests(unittest.TestCase):
    def test_finite_segment_and_direction_for_vertical_and_reversed_lines(self):
        c=LineCounter((50,0),(50,100))
        c.update(1,(60,50),0)
        self.assertEqual(c.update(1,(40,50),1),'negative_to_positive')
        self.assertEqual(direction_labels([50,0,50,100])['negative_to_positive'],'Դեպի կադրի ձախ եզր')
        self.assertEqual(direction_labels([100,50,0,50])['negative_to_positive'],'Դեպի կադրի վերին եզր')
        self.assertIn('A→B',direction_labels([0,0,100,100])['negative_to_positive'])

    def test_nan_and_invalid_endpoints_are_rejected(self):
        for line in [[0,0,0,0],[0,0,100,50],[0,0,float('nan'),50],[-1,0,99,50],[0,0,99]]:
            with self.assertRaises(ValueError):
                validate_line(line,100,100)
        with self.assertRaises(ValueError):
            LineCounter((0,float('nan')),(100,50))
        self.assertEqual(validate_line([0,0,99,99],100,100),[0,0,99,99])
