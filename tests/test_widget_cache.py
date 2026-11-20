from datetime import date
import importlib.util
from pathlib import Path
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('daily_cache', ROOT / 'kodi/addons/plugin.video.smarted/daily_cache.py')
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)


class WidgetCacheTest(unittest.TestCase):
    def test_same_day_and_midnight(self):
        with tempfile.TemporaryDirectory() as path:
            calls = []
            def fetch():
                calls.append(1)
                return ['real-' + str(len(calls))]
            ok = lambda value: isinstance(value, list) and len(value) == 1
            a = date(2026, 11, 10)
            self.assertEqual(cache.cached(path, 'recent-movies', fetch, ok, a), ['real-1'])
            self.assertEqual(cache.cached(path, 'recent-movies', fetch, ok, a), ['real-1'])
            self.assertEqual(cache.cached(path, 'recent-movies', fetch, ok, date(2026,11,11)), ['real-2'])
            self.assertEqual(len(calls), 2)

    def test_failure_is_not_cached_and_corruption_recovers(self):
        with tempfile.TemporaryDirectory() as path:
            count = []
            def fail(): count.append(1); return []
            ok = lambda value: isinstance(value, list) and bool(value)
            self.assertEqual(cache.cached(path, 'recent-series', fail, ok), [])
            self.assertEqual(cache.cached(path, 'recent-series', fail, ok), [])
            self.assertEqual(len(count), 2)
            (Path(path) / 'recent-series.json').write_text('{bad')
            self.assertEqual(cache.cached(path, 'recent-series', lambda: ['real'], ok), ['real'])

    def test_simultaneous_widgets_share_one_fetch(self):
        with tempfile.TemporaryDirectory() as path:
            calls, values = [], []
            def fetch(): calls.append(1); time.sleep(.1); return ['real']
            def run(): values.append(cache.cached(path, 'recent-movies', fetch, lambda x: bool(x)))
            threads = [threading.Thread(target=run) for _ in range(4)]
            for t in threads: t.start()
            for t in threads: t.join()
            self.assertEqual(len(calls), 1)
            self.assertEqual(values, [['real']] * 4)

    def test_unwritable_cache_does_not_block_content(self):
        with tempfile.TemporaryDirectory() as path:
            file = Path(path) / 'not-directory'
            file.write_text('x')
            self.assertEqual(cache.cached(str(file), 'recent-movies', lambda: ['real'], lambda x: True), ['real'])

    def test_thirty_item_widget_keys_and_path_traversal_guard(self):
        with tempfile.TemporaryDirectory() as path:
            movies = [{'id': idx} for idx in range(30)]
            series = ([{'id': idx} for idx in range(30)], [])
            self.assertEqual(
                cache.cached(path, 'recent-movies-30', lambda: movies, lambda v: len(v) == 30),
                movies,
            )
            self.assertEqual(
                cache.cached(path, 'recent-series-30', lambda: series, lambda v: len(v[0]) == 30),
                series,
            )
            for bad in ('../evil', 'carrossel-../evil', 'other-widget'):
                with self.assertRaises(ValueError):
                    cache.cached(path, bad, lambda: ['x'], lambda v: True)


if __name__ == '__main__': unittest.main()
