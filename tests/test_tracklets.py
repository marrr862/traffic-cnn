import unittest
from traffic_cnn.tracklets import Tracklets


class TrackletTests(unittest.TestCase):
    def test_lost_id_preserves_vehicle_and_class(self):
        t = Tracklets()
        t.update([(1,[0,0,20,20],2,.9)],0)
        t.update([(1,[2,0,22,20],2,.9)],1)
        result = t.update([(8,[6,0,26,20],3,.6)],3)
        self.assertEqual(result[0][:2],(1,8))
        self.assertEqual(result[0][3],2)

    def test_simultaneous_vehicles_not_merged(self):
        t = Tracklets()
        t.update([(1,[0,0,20,20],0,.9)],0)
        result = t.update([(1,[0,0,20,20],0,.9),(2,[1,0,21,20],0,.9)],1)
        self.assertEqual([r[0] for r in result],[1,2])

    def test_ambiguous_candidates_not_merged(self):
        t = Tracklets()
        t.update([(1,[0,0,20,20],0,.9),(2,[1,0,21,20],0,.9)],0)
        self.assertEqual(t.update([(3,[0,0,20,20],0,.9)],1)[0][0],3)

    def test_competing_new_ids_not_merged(self):
        t = Tracklets()
        t.update([(1,[0,0,20,20],0,.9)],0)
        self.assertEqual([r[0] for r in t.update([(2,[0,0,20,20],0,.9),(3,[1,0,21,20],0,.9)],1)],[2,3])

    def test_stale_id_not_reused(self):
        t = Tracklets(max_gap=3)
        t.update([(1,[0,0,20,20],0,.9)],0)
        self.assertEqual(t.update([(2,[0,0,20,20],0,.9)],4)[0][0],2)

    def test_reappearing_original_track_splits_simultaneous_alias(self):
        t = Tracklets()
        t.update([(1,[0,0,20,20],0,.9)],0)
        self.assertEqual(t.update([(8,[0,0,20,20],0,.9)],1)[0][0],1)
        results = t.update([(1,[0,0,20,20],0,.9),(8,[1,0,21,20],0,.9)],2)
        self.assertEqual([r[0] for r in results],[1,8])
