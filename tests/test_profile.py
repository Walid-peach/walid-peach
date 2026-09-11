import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('profile_renderer', ROOT / 'scripts/profile.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'data/profile.json').read_text())

    def test_valid_svg_and_reduced_motion(self):
        for mobile, panel in [(m, p) for m in (True, False) for p in ('intro', 'projects', 'activity')]:
            svg = p.render(self.data, mobile, panel=panel)
            root = ET.fromstring(svg)
            self.assertIn('prefers-reduced-motion', svg)
            for a in root.iter('{http://www.w3.org/2000/svg}animate'):
                values = a.attrib['values'].split(';')
                times = list(map(float, a.attrib['keyTimes'].split(';')))
                self.assertEqual(len(values), len(times))
                self.assertEqual(times[0], 0)
                self.assertEqual(times[-1], 1)
                self.assertEqual(times, sorted(times))

    def test_ball_stays_inside_playfield_and_hits_only_active_bricks(self):
        bricks = [{'x': c * 15, 'y': r * 15, 'size': 11, 'count': (c+r) % 2}
                  for c in range(40) for r in range(7)]
        frames, hits, pw, py = p.simulate(bricks, 600, 250)
        self.assertTrue(hits)
        for x, y, paddle in frames:
            self.assertTrue(0 <= x <= 600 and 0 <= y <= 250)
            self.assertTrue(0 <= paddle <= 600 - pw)
        self.assertTrue(all(bricks[i]['count'] > 0 for i in hits))

    def test_language_accounting_includes_other(self):
        parts = p.language_parts({'Jupyter Notebook': 1000, 'Python': 20, 'TypeScript': 30, 'HTML': 10, 'CSS': 5, 'Go': 2})
        self.assertEqual(sum(v for _, v in parts), 67)
        self.assertNotIn('Jupyter Notebook', dict(parts))
        self.assertEqual(parts[-1], ('Other', 7))

    def test_streak_handles_today_grace_gaps_and_future_days(self):
        data = {'updated': '2026-09-09', 'weeks': [{'contributionDays': [
            {'date': '2026-09-06', 'contributionCount': 0},
            {'date': '2026-09-07', 'contributionCount': 3},
            {'date': '2026-09-08', 'contributionCount': 1},
            {'date': '2026-09-09', 'contributionCount': 0},
            {'date': '2026-09-10', 'contributionCount': 9}]}]}
        self.assertEqual(p.current_streak(data), 2)
        days = data['weeks'][0]['contributionDays']
        days[3]['contributionCount'] = 1
        self.assertEqual(p.current_streak(data), 3)
        days[2]['contributionCount'] = 0
        self.assertEqual(p.current_streak(data), 1)
        days[3]['contributionCount'] = 0
        self.assertEqual(p.current_streak(data), 0)
        del days[2]
        self.assertEqual(p.current_streak(data), 0)

    def test_empty_activity_and_languages_are_supported(self):
        self.data['languages'] = {}
        for w in self.data['weeks']:
            for d in w['contributionDays']:
                d['contributionCount'] = 0
        ET.fromstring(p.render(self.data))


if __name__ == '__main__':
    unittest.main()
