"""
Tests for the 3D-view feature (GUIPlotPanel.py).

Run headless (no `wx`): per tests/test_views.py, the pure logic of the wx-bound
methods is mirrored here in module-level helpers and asserted against. `matplotlib`
is available in CI, so the log-z range is validated against a real Normalize.

Mirrored source (pydatview/GUIPlotPanel.py):
  * onViewXY/YZ/XZ/onViewFree      (561-585) — camera presets
  * _apply_3d_plane                (526-560) — ortho/persp + axis visibility
  * set3DMode                      (1286-1303) — curve-type index clamp
  * captureViewData                (1384-1396) — 3D state keys
  * _GUI2Data / plot3D_type        (579-600, 1386) — plot3D_type normalisation
  * log-z colour range             (2917-2974)
"""
import json
import tempfile
import os
import unittest
import numpy as np
import matplotlib.colors as mcolors


# ---------------------------------------------------------------------------
# Helpers mirroring the 3D logic
# ---------------------------------------------------------------------------

def camera_preset(name):
    """Mirror of onViewXY/YZ/XZ/onViewFree -> (elev, azim, hide_axis)."""
    return {
        'XY':   (90, -90, 'z'),
        'YZ':   (0,    0, 'x'),
        'XZ':   (0,  -90, 'y'),
        'Free': (30, -60, None),
    }[name]


def proj_and_visibility(hide_axis):
    """Mirror of _apply_3d_plane: returns (proj_type, set_of_visible_axes)."""
    axes = ('x', 'y', 'z')
    if hide_axis:
        return 'ortho', {a for a in axes if a != hide_axis}
    return 'persp', set(axes)


def clamp_3d_sel(sel):
    """Mirror of set3DMode: cbCurveType has 2 entries (Scatter, Surf)."""
    return max(0, min(sel, 1))


def normalize_plot3d_type(val, view3D):
    """Mirror of captureViewData line 1386 + _GUI2Data clamp."""
    if not view3D:
        return 'Scatter'
    return val if val in ('Scatter', 'Surf') else 'Scatter'


def compute_z_range(z_arrays, logZ=False, autoscale=True, user_zmin=None, user_zmax=None):
    """Mirror of the log-z colour-range block (GUIPlotPanel.py:2917-2974)."""
    all_z_parts = []
    for z in z_arrays:
        z_vals = np.asarray(z, dtype=float)
        if logZ:
            with np.errstate(divide='ignore', invalid='ignore'):
                z_vals = np.log10(z_vals)
        all_z_parts.append(z_vals)
    all_z = np.concatenate(all_z_parts)
    finite_z = all_z[np.isfinite(all_z)]
    z_vmin = z_vmax = None
    if len(finite_z) > 0:
        z_vmin = float(np.min(finite_z))
        z_vmax = float(np.max(finite_z))
    if not autoscale:
        u_zmin, u_zmax = user_zmin, user_zmax
        if logZ:
            with np.errstate(divide='ignore', invalid='ignore'):
                if u_zmin is not None and u_zmin > 0:
                    u_zmin = float(np.log10(u_zmin))
                elif u_zmin is not None:
                    u_zmin = None
                if u_zmax is not None and u_zmax > 0:
                    u_zmax = float(np.log10(u_zmax))
                elif u_zmax is not None:
                    u_zmax = None
        if u_zmin is not None:
            z_vmin = u_zmin
        if u_zmax is not None:
            z_vmax = u_zmax
    if z_vmin is not None and z_vmax is not None:
        if z_vmin > z_vmax:
            z_vmin, z_vmax = z_vmax, z_vmin
        if z_vmin == z_vmax:
            eps = max(abs(z_vmin), 1.0) * 1e-6
            z_vmin -= eps
            z_vmax += eps
    return z_vmin, z_vmax


def capture_3d_data(view3D=True, curveType='Scatter', elev=30, azim=-60,
                    hide=None, logZ=False, flipZ=False):
    """Mirror of the 3D keys written by captureViewData (1384-1396)."""
    return {
        'view3D':      view3D,
        'plot3D_type': normalize_plot3d_type(curveType, view3D),
        'view3D_elev': elev,
        'view3D_azim': azim,
        'view3D_hide': hide,
        'logZ':        logZ,
        'flipZ':       flipZ,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCapture3DState(unittest.TestCase):
    def test_all_3d_keys_present(self):
        d = capture_3d_data()
        for k in ('view3D', 'plot3D_type', 'view3D_elev', 'view3D_azim',
                  'view3D_hide', 'logZ', 'flipZ'):
            self.assertIn(k, d)

    def test_json_round_trip(self):
        d = capture_3d_data(view3D=True, curveType='Surf', elev=12.5, azim=-45,
                            hide='z', logZ=True, flipZ=True)
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, 'v.pdvview')
            with open(p, 'w') as f:
                json.dump({'plotPanel': d}, f)
            with open(p) as f:
                loaded = json.load(f)['plotPanel']
        self.assertEqual(loaded['plot3D_type'], 'Surf')
        self.assertEqual(loaded['view3D_elev'], 12.5)
        self.assertEqual(loaded['view3D_hide'], 'z')
        self.assertTrue(loaded['logZ'])
        self.assertTrue(loaded['flipZ'])

    def test_plot3d_type_forced_scatter_when_not_3d(self):
        d = capture_3d_data(view3D=False, curveType='Surf')
        self.assertEqual(d['plot3D_type'], 'Scatter')


class TestPlot3DTypeNormalisation(unittest.TestCase):
    def test_valid_values_pass_through(self):
        self.assertEqual(normalize_plot3d_type('Scatter', True), 'Scatter')
        self.assertEqual(normalize_plot3d_type('Surf', True), 'Surf')

    def test_invalid_falls_back_to_scatter(self):
        self.assertEqual(normalize_plot3d_type('LS', True), 'Scatter')
        self.assertEqual(normalize_plot3d_type('', True), 'Scatter')


class TestCameraPresets(unittest.TestCase):
    def test_presets(self):
        self.assertEqual(camera_preset('XY'),   (90, -90, 'z'))
        self.assertEqual(camera_preset('YZ'),   (0,    0, 'x'))
        self.assertEqual(camera_preset('XZ'),   (0,  -90, 'y'))
        self.assertEqual(camera_preset('Free'), (30, -60, None))

    def test_plane_views_hide_their_normal_axis(self):
        for plane, normal in (('XY', 'z'), ('YZ', 'x'), ('XZ', 'y')):
            self.assertEqual(camera_preset(plane)[2], normal)


class TestProjectionVisibility(unittest.TestCase):
    def test_hidden_axis_uses_ortho_and_is_invisible(self):
        proj, visible = proj_and_visibility('z')
        self.assertEqual(proj, 'ortho')
        self.assertNotIn('z', visible)
        self.assertEqual(visible, {'x', 'y'})

    def test_free_view_uses_persp_all_visible(self):
        proj, visible = proj_and_visibility(None)
        self.assertEqual(proj, 'persp')
        self.assertEqual(visible, {'x', 'y', 'z'})


class TestCurveTypeClamp(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(clamp_3d_sel(-1), 0)
        self.assertEqual(clamp_3d_sel(0), 0)
        self.assertEqual(clamp_3d_sel(1), 1)
        self.assertEqual(clamp_3d_sel(5), 1)


class TestZRange(unittest.TestCase):
    def test_linear_range_is_data_minmax(self):
        vmin, vmax = compute_z_range([np.array([1.0, 5.0, 3.0])])
        self.assertAlmostEqual(vmin, 1.0)
        self.assertAlmostEqual(vmax, 5.0)

    def test_multiple_arrays_combined(self):
        vmin, vmax = compute_z_range([np.array([1.0, 2.0]), np.array([0.5, 9.0])])
        self.assertAlmostEqual(vmin, 0.5)
        self.assertAlmostEqual(vmax, 9.0)

    def test_logz_transforms_and_drops_nonpositive(self):
        # 0 and -1 -> non-finite after log10 and must be filtered out
        vmin, vmax = compute_z_range([np.array([-1.0, 0.0, 1.0, 100.0])], logZ=True)
        self.assertAlmostEqual(vmin, 0.0)    # log10(1)
        self.assertAlmostEqual(vmax, 2.0)    # log10(100)

    def test_user_limits_ignored_when_autoscale(self):
        vmin, vmax = compute_z_range([np.array([1.0, 5.0])], autoscale=True,
                                     user_zmin=100.0, user_zmax=200.0)
        self.assertAlmostEqual(vmin, 1.0)
        self.assertAlmostEqual(vmax, 5.0)

    def test_user_limits_applied_when_not_autoscale(self):
        vmin, vmax = compute_z_range([np.array([1.0, 5.0])], autoscale=False,
                                     user_zmin=2.0, user_zmax=4.0)
        self.assertAlmostEqual(vmin, 2.0)
        self.assertAlmostEqual(vmax, 4.0)

    def test_logz_user_limits_log_scaled_and_nonpositive_dropped(self):
        # user_zmin=-1 (invalid in log) dropped -> falls back to data; user_zmax=100 -> log10=2
        vmin, vmax = compute_z_range([np.array([1.0, 1000.0])], logZ=True,
                                     autoscale=False, user_zmin=-1.0, user_zmax=100.0)
        self.assertAlmostEqual(vmin, 0.0)    # data log10(1), user min dropped
        self.assertAlmostEqual(vmax, 2.0)    # log10(100)

    def test_inverted_user_limits_swapped(self):
        vmin, vmax = compute_z_range([np.array([1.0, 5.0])], autoscale=False,
                                     user_zmin=4.0, user_zmax=2.0)
        self.assertLess(vmin, vmax)
        self.assertAlmostEqual(vmin, 2.0)
        self.assertAlmostEqual(vmax, 4.0)

    def test_constant_data_padded(self):
        vmin, vmax = compute_z_range([np.array([3.0, 3.0, 3.0])])
        self.assertLess(vmin, vmax)          # epsilon padding avoids collapse
        # a Normalize built from the padded range is valid (no zero span)
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
        self.assertFalse(np.isnan(norm(3.0)))


if __name__ == '__main__':
    unittest.main()
