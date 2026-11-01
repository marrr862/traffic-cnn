import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1]/'app.py')
ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT/'data/video/vehicles.mp4'
HAS_RESULT = any((ROOT/'outputs').glob('**/summary.json'))

class AppTests(unittest.TestCase):
    def test_app_opens_without_exception(self):
        app=AppTest.from_file(APP)
        app.run(timeout=60)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.title[0].value,'Երթևեկության հոսքի վերլուծություն')

    @unittest.skipUnless(DEMO.exists() and HAS_RESULT, 'requires demo video (scripts/download_assets.py) and a processed result in outputs/')
    def test_points_manual_calibration_and_annotation_render(self):
        app=AppTest.from_file(APP).run(timeout=60)
        next(r for r in app.radio if r.label=='Ճանապարհային հարթության տրամաչափում').set_value('Ձեռքով (4 կետ)')
        app.run(timeout=60)
        self.assertEqual(len(app.exception),0)
        target=next(r for r in app.radio if r.label=='Նշվող կետ')
        self.assertIn('Տրամաչափում՝ Մոտ աջ',target.options)
        self.assertTrue(any(n.label=='A կետ՝ X' for n in app.number_input))
        self.assertTrue(any(n.label=='Լայնություն, մ' for n in app.number_input))
        next(n for n in app.number_input if n.label=='A կետ՝ Y').set_value(500)
        app.run(timeout=60)
        self.assertEqual(app.session_state['ay'],500)
        next(r for r in app.radio if r.label=='Նշագրման աղբյուր').set_value('Նշագրում հավելվածում')
        app.run(timeout=60)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any(b.label=='Ավելացնել նշագրման իրադարձություն' for b in app.button))

    def test_live_source_controls(self):
        app=AppTest.from_file(APP).run(timeout=60)
        next(r for r in app.radio if r.label=='Տեսանյութի աղբյուր').set_value('Ուղիղ հոսք (տեսախցիկ / URL)')
        app.run(timeout=60)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any(t.label=='Տեսախցիկի համար կամ հոսքի հասցե' for t in app.text_input))
        self.assertTrue(any(b.label=='Միանալ և վերցնել կադր' for b in app.button))
