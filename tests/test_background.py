"""
Tests for the Background-image feature (GUIPlotPanel.py).

Run headless (no `wx`): following tests/test_views.py, the pure logic of the
wx-bound methods is mirrored here in module-level helpers and asserted against.

Mirrored source (pydatview/GUIPlotPanel.py):
  * _setBgImage / onClearBgImage   (1654-1718) — state reset
  * onPasteBgImage                 (1688-1706) — uint8 -> float [0,1] normalisation
  * _compute_bg_screen_lock        (1719-1795) — Moving -> Fixed crop/extent math
  * _full_extent_from_state        (1797-1830) — Fixed -> Moving full-extent math
"""
import unittest
import numpy as np


# ---------------------------------------------------------------------------
# Helpers mirroring the background-image logic
# ---------------------------------------------------------------------------

def bg_default_state():
    """Mirror of the field reset done by _setBgImage / onClearBgImage."""
    return {
        'bg_glued':         False,   # False = Fixed (pinned to plot rect)
        'bg_extent':        None,    # data coords, set in Moving mode
        'bg_display_image': None,    # cropped image for Fixed mode
        'bg_axes_extent':   None,    # axes-fraction extent for Fixed artist
        'bg_crop_box':      None,    # fraction [0,1] of original image
    }


def normalize_pasted(uint8_arr):
    """Mirror of onPasteBgImage: bytes -> float64 in [0,1]."""
    return uint8_arr.astype(np.float64) / 255.0


def compute_screen_lock(img_shape, bg_extent, viewport, parent_crop_box=None):
    """Mirror of _compute_bg_screen_lock for the glued/artist-present case.

    bg_extent = [bx0, bx1, by0, by1] : current image extent in data coords.
    viewport  = [vx0, vx1, vy0, vy1] : current axis limits (any order).
    Returns (crop_box, axes_extent) or None if the image is not visible.
    """
    vx0, vx1 = sorted(viewport[:2])
    vy0, vy1 = sorted(viewport[2:])
    bx0, bx1, by0, by1 = bg_extent
    if bx0 > bx1:
        bx0, bx1 = bx1, bx0
    if by0 > by1:
        by0, by1 = by1, by0

    ix0, ix1 = max(bx0, vx0), min(bx1, vx1)
    iy0, iy1 = max(by0, vy0), min(by1, vy1)
    if ix1 <= ix0 or iy1 <= iy0:
        return None

    col_lf = (ix0 - bx0) / (bx1 - bx0)
    col_rf = (ix1 - bx0) / (bx1 - bx0)
    # origin='upper': row 0 is at by1 (top), row h is at by0 (bottom)
    row_tf = (by1 - iy1) / (by1 - by0)
    row_bf = (by1 - iy0) / (by1 - by0)

    h, w = img_shape[:2]
    col0 = max(0, min(w, int(round(col_lf * w))))
    col1 = max(0, min(w, int(round(col_rf * w))))
    row0 = max(0, min(h, int(round(row_tf * h))))
    row1 = max(0, min(h, int(round(row_bf * h))))
    if col1 <= col0 or row1 <= row0:
        return None

    afx0 = (ix0 - vx0) / (vx1 - vx0)
    afx1 = (ix1 - vx0) / (vx1 - vx0)
    afy0 = (iy0 - vy0) / (vy1 - vy0)
    afy1 = (iy1 - vy0) / (vy1 - vy0)

    pa, pb, pc, pd = parent_crop_box if parent_crop_box is not None else [0.0, 1.0, 0.0, 1.0]
    crop_box = [pa + col_lf * (pb - pa),
                pa + col_rf * (pb - pa),
                pc + row_tf * (pd - pc),
                pc + row_bf * (pd - pc)]
    return crop_box, [afx0, afx1, afy0, afy1]


def full_extent_from_state(viewport, axes_extent, crop_box):
    """Mirror of _full_extent_from_state. Returns [Dx0, Dx1, Dy0, Dy1]."""
    vx0, vx1 = sorted(viewport[:2])
    vy0, vy1 = sorted(viewport[2:])
    afx0, afx1, afy0, afy1 = axes_extent if axes_extent is not None else [0.0, 1.0, 0.0, 1.0]
    dx0 = vx0 + afx0 * (vx1 - vx0)
    dx1 = vx0 + afx1 * (vx1 - vx0)
    dy0 = vy0 + afy0 * (vy1 - vy0)
    dy1 = vy0 + afy1 * (vy1 - vy0)
    a, b, c, d = crop_box if crop_box is not None else [0.0, 1.0, 0.0, 1.0]
    if (b - a) <= 0 or (d - c) <= 0:
        return [vx0, vx1, vy0, vy1]
    full_w = (dx1 - dx0) / (b - a)
    full_h = (dy1 - dy0) / (d - c)
    Dx0 = dx0 - a * full_w
    Dx1 = Dx0 + full_w
    # origin='upper': fraction c (top) maps to data y = dy1
    Dy1 = dy1 + c * full_h
    Dy0 = Dy1 - full_h
    return [Dx0, Dx1, Dy0, Dy1]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPasteNormalisation(unittest.TestCase):
    def test_uint8_to_float_range(self):
        arr = np.array([[0, 128, 255]], dtype=np.uint8)
        out = normalize_pasted(arr)
        self.assertEqual(out.dtype, np.float64)
        self.assertAlmostEqual(out[0, 0], 0.0)
        self.assertAlmostEqual(out[0, 2], 1.0)
        self.assertTrue((out >= 0).all() and (out <= 1).all())

    def test_shape_preserved(self):
        arr = np.zeros((4, 7, 3), dtype=np.uint8)
        self.assertEqual(normalize_pasted(arr).shape, (4, 7, 3))


class TestStateReset(unittest.TestCase):
    def test_default_state_is_fixed_mode(self):
        st = bg_default_state()
        self.assertFalse(st['bg_glued'])            # Fixed is the default
        self.assertIsNone(st['bg_extent'])
        self.assertIsNone(st['bg_display_image'])
        self.assertIsNone(st['bg_axes_extent'])
        self.assertIsNone(st['bg_crop_box'])

    def test_clear_returns_to_default(self):
        # Simulate a populated state then a clear()
        st = {'bg_glued': True, 'bg_extent': [0, 1, 0, 1],
              'bg_display_image': object(), 'bg_axes_extent': [0, 1, 0, 1],
              'bg_crop_box': [0.1, 0.9, 0.1, 0.9]}
        st = bg_default_state()
        self.assertEqual(st, bg_default_state())


class TestScreenLock(unittest.TestCase):
    """_compute_bg_screen_lock: Moving (data coords) -> Fixed (axes fraction)."""

    def test_image_fully_inside_viewport_fills_axes(self):
        # bg covers data [0,10]x[0,10]; we zoom into the central [2,8] box.
        res = compute_screen_lock((100, 100), [0, 10, 0, 10], [2, 8, 2, 8])
        self.assertIsNotNone(res)
        crop, ae = res
        # the visible portion fills the whole zoomed view
        np.testing.assert_allclose(ae, [0.0, 1.0, 0.0, 1.0])
        # crop box: x 0.2..0.8 ; y (origin upper) top=(10-8)/10=0.2, bottom=(10-2)/10=0.8
        np.testing.assert_allclose(crop, [0.2, 0.8, 0.2, 0.8])

    def test_partial_overlap_clips(self):
        # image spans x[0,10]; viewport x[5,20] -> only right half of image visible
        res = compute_screen_lock((100, 100), [0, 10, 0, 10], [5, 20, 0, 10])
        self.assertIsNotNone(res)
        crop, ae = res
        # x crop from 0.5 to 1.0
        self.assertAlmostEqual(crop[0], 0.5)
        self.assertAlmostEqual(crop[1], 1.0)
        # image occupies axes-fraction 0 .. (10-5)/(20-5)=1/3 of the view
        self.assertAlmostEqual(ae[0], 0.0)
        self.assertAlmostEqual(ae[1], 1.0 / 3.0)

    def test_no_overlap_returns_none(self):
        res = compute_screen_lock((100, 100), [0, 10, 0, 10], [20, 30, 0, 10])
        self.assertIsNone(res)

    def test_inverted_limits_normalised(self):
        ordered = compute_screen_lock((100, 100), [0, 10, 0, 10], [2, 8, 2, 8])
        flipped = compute_screen_lock((100, 100), [0, 10, 0, 10], [8, 2, 8, 2])
        self.assertIsNotNone(flipped)
        np.testing.assert_allclose(flipped[0], ordered[0])
        np.testing.assert_allclose(flipped[1], ordered[1])

    def test_parent_crop_box_composition(self):
        # already cropped to x[0.2,0.8]; further zoom selects middle half again
        parent = [0.2, 0.8, 0.2, 0.8]
        res = compute_screen_lock((100, 100), [0, 10, 0, 10], [2, 8, 2, 8],
                                  parent_crop_box=parent)
        crop, _ = res
        # col_lf=0.2 -> 0.2 + 0.2*(0.8-0.2)=0.32 ; col_rf=0.8 -> 0.2+0.8*0.6=0.68
        np.testing.assert_allclose(crop, [0.32, 0.68, 0.32, 0.68])


class TestFullExtentRoundTrip(unittest.TestCase):
    """Fixed <-> Moving transforms must be inverses of one another."""

    def test_full_extent_recovers_original(self):
        full_extent = [-3.0, 7.0, 1.0, 11.0]   # original image extent (data coords)
        viewport    = [0.0, 4.0, 3.0, 9.0]      # zoomed-in view, inside the image
        # Moving -> Fixed
        crop, ae = compute_screen_lock((200, 200), full_extent, viewport)
        # Fixed -> Moving must rebuild the original full extent
        recovered = full_extent_from_state(viewport, ae, crop)
        np.testing.assert_allclose(recovered, full_extent, atol=1e-9)

    def test_degenerate_crop_box_returns_viewport(self):
        viewport = [0.0, 4.0, 0.0, 4.0]
        out = full_extent_from_state(viewport, [0, 1, 0, 1], [0.5, 0.5, 0.0, 1.0])
        np.testing.assert_allclose(out, [0.0, 4.0, 0.0, 4.0])


if __name__ == '__main__':
    unittest.main()
