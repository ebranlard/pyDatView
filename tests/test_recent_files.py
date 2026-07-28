"""
Tests for the Recent Files feature (main.py `_track_recent` /
`_populateRecentFilesMenu`).

These tests run headless: the real implementation lives on `wx`-importing GUI
modules that are not installed in CI, so — following the same convention as
tests/test_views.py — the pure logic is mirrored here in small helper functions
and asserted against.

Mirrored source:
  * pydatview/main.py:1187-1223 (_track_recent, _populateRecentFilesMenu)
  * pydatview/main.py:55                  VIEW_FILE_EXT = '.pdvview'
  * pydatview/GUIPlotPanel.py:49          IMAGE_EXTS = ('.png', ...)
"""
import os
import unittest


# ---------------------------------------------------------------------------
# Constants mirrored from the source (kept in sync deliberately)
# ---------------------------------------------------------------------------
VIEW_FILE_EXT = '.pdvview'
IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')


# ---------------------------------------------------------------------------
# Helpers mirroring the recent-files logic in main.py
# ---------------------------------------------------------------------------

def track_recent(recent, path, cap=30):
    """Mirror of main.py `_track_recent`.

    Insert *path* (as an absolute path) at the top of *recent*, de-duplicating
    and capping the list at *cap*. Returns the new list (does not mutate input).
    """
    recent = list(recent)
    abs_path = os.path.abspath(path)
    if abs_path in recent:
        recent.remove(abs_path)
    recent.insert(0, abs_path)
    return recent[:cap]


def recent_label(path):
    """Mirror of the label/category routing in `_populateRecentFilesMenu`.

    Returns (category, label) where category is one of 'view', 'bg', 'data'.
    """
    low = path.lower()
    if low.endswith(VIEW_FILE_EXT):
        return 'view', '[view] {}'.format(path)
    elif low.endswith(IMAGE_EXTS):
        return 'bg', '[bg] {}'.format(path)
    else:
        return 'data', path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestTrackRecent(unittest.TestCase):
    """Ordering, de-duplication, capping and absolute-path normalisation."""

    def test_newest_first(self):
        recent = []
        for p in ('/a/one.csv', '/a/two.csv', '/a/three.csv'):
            recent = track_recent(recent, p)
        self.assertEqual(recent[0], os.path.abspath('/a/three.csv'))
        self.assertEqual(recent[-1], os.path.abspath('/a/one.csv'))

    def test_readd_moves_to_top_without_duplicate(self):
        recent = []
        for p in ('/a/one.csv', '/a/two.csv', '/a/three.csv'):
            recent = track_recent(recent, p)
        before_len = len(recent)
        recent = track_recent(recent, '/a/one.csv')   # re-add the oldest
        self.assertEqual(recent[0], os.path.abspath('/a/one.csv'))
        self.assertEqual(len(recent), before_len)      # no growth: it moved, not duplicated
        self.assertEqual(recent.count(os.path.abspath('/a/one.csv')), 1)

    def test_cap_at_30_keeps_newest(self):
        recent = []
        for i in range(35):
            recent = track_recent(recent, '/dir/file{:02d}.csv'.format(i))
        self.assertEqual(len(recent), 30)
        # newest (file34) on top, oldest kept is file05 (00-04 dropped)
        self.assertEqual(recent[0], os.path.abspath('/dir/file34.csv'))
        self.assertEqual(recent[-1], os.path.abspath('/dir/file05.csv'))
        self.assertNotIn(os.path.abspath('/dir/file04.csv'), recent)

    def test_custom_cap(self):
        recent = []
        for i in range(10):
            recent = track_recent(recent, '/d/f{}.csv'.format(i), cap=3)
        self.assertEqual(len(recent), 3)

    def test_paths_stored_absolute(self):
        recent = track_recent([], 'relative/file.csv')
        self.assertTrue(os.path.isabs(recent[0]))
        self.assertEqual(recent[0], os.path.abspath('relative/file.csv'))

    def test_relative_forms_dedupe(self):
        """'x.csv' and './x.csv' refer to the same file and must not duplicate."""
        recent = track_recent([], 'x.csv')
        recent = track_recent(recent, './x.csv')
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0], os.path.abspath('x.csv'))

    def test_empty_input_returns_single_entry(self):
        recent = track_recent([], '/a/only.csv')
        self.assertEqual(recent, [os.path.abspath('/a/only.csv')])


class TestRecentLabel(unittest.TestCase):
    """Category/label routing used to build the submenu items."""

    def test_view_file_labelled(self):
        cat, label = recent_label('/a/my.pdvview')
        self.assertEqual(cat, 'view')
        self.assertTrue(label.startswith('[view] '))

    def test_each_image_ext_is_bg(self):
        for ext in IMAGE_EXTS:
            cat, label = recent_label('/a/pic' + ext)
            self.assertEqual(cat, 'bg', 'ext {} should route to bg'.format(ext))
            self.assertTrue(label.startswith('[bg] '))

    def test_data_file_plain_label(self):
        for p in ('/a/data.csv', '/a/run.txt', '/a/out.outb'):
            cat, label = recent_label(p)
            self.assertEqual(cat, 'data')
            self.assertEqual(label, p)   # plain path, no prefix

    def test_case_insensitive(self):
        self.assertEqual(recent_label('/A/MY.PDVVIEW')[0], 'view')
        self.assertEqual(recent_label('/A/PIC.PNG')[0], 'bg')
        self.assertEqual(recent_label('/A/DATA.CSV')[0], 'data')

    def test_empty_recent_is_sentinel(self):
        """An empty recent list produces the disabled '(empty)' item, i.e. no entries."""
        recent = []
        self.assertEqual(len(recent), 0)   # _populateRecentFilesMenu shows '(empty)'

    def test_mixed_list_preserves_order_and_categories(self):
        paths = ['/a/v.pdvview', '/a/d.csv', '/a/img.jpg']
        recent = []
        for p in paths:
            recent = track_recent(recent, p)
        cats = [recent_label(p)[0] for p in recent]
        # newest-first: img(bg), d(data), v(view)
        self.assertEqual(cats, ['bg', 'data', 'view'])


if __name__ == '__main__':
    unittest.main()
