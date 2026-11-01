import unittest
from scripts.evaluate_counting import match_events
from traffic_cnn.evaluation import evaluate_run

class EventMatchingTests(unittest.TestCase):
    def ref(self,frame,cls='car'):
        return {'frame_interval':[frame,frame],'direction':'negative_to_positive','class':cls}
    def event(self,frame,cls='car'):
        return {'frame':str(frame),'direction':'negative_to_positive','vehicle_class':cls}
    def test_equal_totals_can_hide_compensating_errors(self):
        result=match_events([self.ref(10),self.ref(50)],[self.event(10),self.event(80)],tolerance=0)
        self.assertEqual(result['matched_events'],1)
        self.assertEqual(len(result['unmatched_reference_events']),1)
        self.assertEqual(len(result['unmatched_predicted_events']),1)
    def test_duplicate_events_match_only_once(self):
        result=match_events([self.ref(10)],[self.event(10),self.event(11)])
        self.assertEqual(result['matched_events'],1)
        self.assertEqual(len(result['unmatched_predicted_events']),1)
    def test_class_error_is_separate_from_counting(self):
        result=match_events([self.ref(10)],[self.event(10,'truck')])
        self.assertEqual(result['matched_events'],1)
        self.assertEqual(len(result['matched_class_disagreements']),1)
    def test_direction_must_match(self):
        event=self.event(10);event['direction']='positive_to_negative'
        self.assertEqual(match_events([self.ref(10)],[event])['matched_events'],0)
    def test_empty_events(self):
        self.assertEqual(match_events([],[])['matched_events'],0)
        self.assertEqual(len(match_events([self.ref(10)],[])['unmatched_reference_events']),1)
    def test_evaluation_requires_same_source_line_and_fps(self):
        summary=dict(source_sha256='a'*64,line=[0,50,100,50],source_fps=25,frames=100,crossings=1,processing_fps=10)
        reference=dict(source_sha256='a'*64,line=summary['line'],fps=25,events=[self.ref(10),self.ref(50)])
        result=evaluate_run(summary,reference,[self.event(10)])
        self.assertEqual(result['event_precision'],1)
        self.assertEqual(result['event_recall'],.5)
        self.assertAlmostEqual(result['event_f1'],2/3)
        for overrides in [dict(source_sha256='b'*64),dict(line=[0,40,100,40]),dict(fps=30),dict(events=[self.ref(101)]),dict(events=[None])]:
            with self.assertRaises(ValueError):
                evaluate_run(summary,{**reference,**overrides},[self.event(10)])
        with self.assertRaises(ValueError):
            evaluate_run(summary,reference,[])
        with self.assertRaises(ValueError):
            match_events([],[],tolerance=-1)
