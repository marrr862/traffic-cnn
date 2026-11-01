import unittest
from scripts.evaluate_detrac import crossing_reference, in_ignore, iou

class DetracTests(unittest.TestCase):
    def test_published_id_crossing_and_original_class(self):
        def target(bottom): return dict(id=4,box=[400,bottom-20,440,bottom],kind='others')
        events=crossing_reference([(0,[target(310)]),(1,[target(324)]),(2,[target(338)]),(3,[target(310)])])
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['class'],'others')
        self.assertEqual(events[0]['frame_interval'],[0,2])
        self.assertEqual(events[0]['direction'],'negative_to_positive')
    def test_gap_and_segment_exclude_false_crossings(self):
        targets=[dict(id=1,box=[100,300,120,310],kind='car')]
        later=[dict(id=1,box=[100,320,120,340],kind='car')]
        self.assertEqual(crossing_reference([(0,targets),(31,later)]),[])
        self.assertEqual(crossing_reference([(0,[dict(id=1,box=[1000,300,1020,310],kind='car')]),(1,[dict(id=1,box=[1000,320,1020,340],kind='car')])]),[])
    def test_ignore_center_and_iou(self):
        self.assertTrue(in_ignore([0,0,20,20],[[5,5,10,10]]))
        self.assertFalse(in_ignore([0,0,4,4],[[5,5,10,10]]))
        self.assertAlmostEqual(iou([0,0,10,10],[[0,0,10,10]])[0],1)
