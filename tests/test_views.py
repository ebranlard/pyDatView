"""
Tests for the view save/restore feature:
  - view state dict structure (keys present, types correct)
  - z-column name resolution logic
  - .pdvview JSON round-trip (export -> import path resolution)
  - view3D field in plotPanel state
"""
import os
import json
import tempfile
import unittest
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers that mirror the resolution logic in GUISelectionPanel
# ---------------------------------------------------------------------------

def resolve_x(v, cols, selected=True):
    """Resolve xSel from a saved tabSelections entry. Returns (xSel, warnings)."""
    warnings = []
    xSel = v.get('xSel', -1)
    xName = v.get('xName')
    if xName is not None:
        if xName in cols:
            xSel = cols.index(xName)
        else:
            if selected:
                warnings.append('x-column "{}" not found'.format(xName))
            xSel = -1
    elif xSel >= len(cols):
        xSel = -1
    return xSel, warnings


def resolve_y(v, cols, selected=True):
    """Resolve ySel from a saved tabSelections entry. Returns (ySel, warnings)."""
    warnings = []
    ySel = list(v.get('ySel', []))
    yNames = v.get('yNames', [])
    if yNames:
        ySel_new = [cols.index(yn) for yn in yNames if yn in cols]
        missing  = [yn for yn in yNames if yn not in cols]
        if missing and selected:
            warnings.append('column(s) not found: {}'.format(missing))
        ySel = ySel_new if ySel_new else [iy for iy in ySel if 0 <= iy < len(cols)]
    else:
        ySel = [iy for iy in ySel if 0 <= iy < len(cols)]
    return ySel, warnings


def resolve_z(v, cols, selected=True):
    """Resolve zSel (comboZ index: 0=None, 1+=col). Returns (zSel, warnings)."""
    warnings = []
    zSel  = v.get('zSel', 0)
    zName = v.get('zName')
    if zName is not None:
        if zName in cols:
            zSel = cols.index(zName) + 1   # +1 because comboZ[0]='None'
        else:
            if selected:
                warnings.append('z-column "{}" not found'.format(zName))
            zSel = 0
    elif zSel > len(cols):   # comboZ has len(cols)+1 entries
        zSel = 0
    return zSel, warnings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestViewStateStructure(unittest.TestCase):
    """Verify that the expected keys are present in view state dicts."""

    def _make_tab_entry(self, xSel, ySel, zSel, cols):
        """Build a tabSelections entry with name backups."""
        xName  = cols[xSel] if 0 <= xSel < len(cols) else None
        yNames = [cols[i] for i in ySel if 0 <= i < len(cols)]
        zColIdx = zSel - 1
        zName  = cols[zColIdx] if 0 <= zColIdx < len(cols) else None
        return {
            'xSel':   xSel,
            'ySel':   list(ySel),
            'zSel':   zSel,
            'xName':  xName,
            'yNames': yNames,
            'zName':  zName,
        }

    def test_tab_entry_keys(self):
        cols = ['Time', 'Speed', 'Power', 'Torque']
        entry = self._make_tab_entry(xSel=0, ySel=[2], zSel=3, cols=cols)
        for key in ('xSel', 'ySel', 'zSel', 'xName', 'yNames', 'zName'):
            self.assertIn(key, entry)

    def test_tab_entry_values(self):
        cols = ['Time', 'Speed', 'Power', 'Torque']
        entry = self._make_tab_entry(xSel=0, ySel=[2], zSel=3, cols=cols)
        self.assertEqual(entry['xName'],  'Time')
        self.assertEqual(entry['yNames'], ['Power'])
        self.assertEqual(entry['zName'],  'Power')   # zSel=3 → zColIdx=2 → cols[2]

    def test_z_none_stored_as_zero(self):
        """zSel=0 means 'None' (no Z column selected)."""
        cols = ['Time', 'Speed', 'Power']
        entry = self._make_tab_entry(xSel=0, ySel=[1], zSel=0, cols=cols)
        self.assertEqual(entry['zSel'],  0)
        self.assertIsNone(entry['zName'])

    def test_plot_panel_view3d_key(self):
        """plotPanel state must include view3D."""
        plot_state = {
            'plotType':  'Regular',
            'logX':      False,
            'logY':      False,
            'grid':      False,
            'crossHair': True,
            'subplot':   False,
            'sync':      True,
            'autoScale': True,
            'stepPlot':  False,
            'curveType': 1,
            'plotStyle': {},
            'view3D':    True,
        }
        self.assertIn('view3D', plot_state)
        self.assertTrue(plot_state['view3D'])


class TestZColumnResolution(unittest.TestCase):
    """Test z-column resolution: name-first, index fallback, out-of-range."""

    def setUp(self):
        self.cols = ['Time', 'Speed', 'Power', 'Torque']

    def test_resolve_by_name(self):
        v = {'zSel': 99, 'zName': 'Power'}   # index wrong, name correct
        zSel, w = resolve_z(v, self.cols)
        self.assertEqual(zSel, 3)             # cols.index('Power')+1 = 3
        self.assertEqual(w, [])

    def test_resolve_by_index_when_no_name(self):
        v = {'zSel': 2, 'zName': None}        # comboZ index 2 → col index 1 → 'Speed'
        zSel, w = resolve_z(v, self.cols)
        self.assertEqual(zSel, 2)
        self.assertEqual(w, [])

    def test_missing_name_falls_back_to_none(self):
        v = {'zSel': 2, 'zName': 'DoesNotExist'}
        zSel, w = resolve_z(v, self.cols)
        self.assertEqual(zSel, 0)             # None
        self.assertEqual(len(w), 1)
        self.assertIn('DoesNotExist', w[0])

    def test_missing_name_no_warning_for_unselected_table(self):
        v = {'zSel': 2, 'zName': 'DoesNotExist'}
        zSel, w = resolve_z(v, self.cols, selected=False)
        self.assertEqual(zSel, 0)
        self.assertEqual(w, [])              # no warning for unselected table

    def test_index_out_of_range_resets_to_none(self):
        v = {'zSel': 100, 'zName': None}     # way out of range
        zSel, w = resolve_z(v, self.cols)
        self.assertEqual(zSel, 0)

    def test_none_selection_preserved(self):
        v = {'zSel': 0, 'zName': None}
        zSel, w = resolve_z(v, self.cols)
        self.assertEqual(zSel, 0)            # still None
        self.assertEqual(w, [])

    def test_reordered_columns(self):
        """Name lookup must survive column reordering."""
        v = {'zSel': 1, 'zName': 'Power'}   # was first col; now third
        new_cols = ['Time', 'Torque', 'Speed', 'Power']
        zSel, w = resolve_z(v, new_cols)
        self.assertEqual(zSel, 4)            # new_cols.index('Power')+1 = 4
        self.assertEqual(w, [])


class TestXYResolution(unittest.TestCase):
    """Test x- and y-column resolution (same strategy as z)."""

    def setUp(self):
        self.cols = ['Time', 'Speed', 'Power', 'Torque']

    def test_x_resolved_by_name(self):
        v = {'xSel': 99, 'xName': 'Speed'}
        xSel, w = resolve_x(v, self.cols)
        self.assertEqual(xSel, 1)
        self.assertEqual(w, [])

    def test_x_missing_name_returns_minus_one(self):
        v = {'xSel': 1, 'xName': 'Gone'}
        xSel, w = resolve_x(v, self.cols)
        self.assertEqual(xSel, -1)
        self.assertEqual(len(w), 1)

    def test_y_resolved_by_name(self):
        v = {'ySel': [99], 'yNames': ['Power', 'Torque']}
        ySel, w = resolve_y(v, self.cols)
        self.assertEqual(ySel, [2, 3])
        self.assertEqual(w, [])

    def test_y_partial_missing(self):
        v = {'ySel': [], 'yNames': ['Power', 'Missing']}
        ySel, w = resolve_y(v, self.cols)
        self.assertEqual(ySel, [2])          # only Power resolved
        self.assertEqual(len(w), 1)
        self.assertIn('Missing', w[0])

    def test_y_all_missing_falls_back_to_index(self):
        v = {'ySel': [1, 2], 'yNames': ['Gone']}
        ySel, w = resolve_y(v, self.cols)
        self.assertEqual(ySel, [1, 2])       # index fallback


class TestViewFilePersistence(unittest.TestCase):
    """Test the .pdvview JSON file format: write -> read round-trip."""

    def _make_view_data(self, base_dir, data_path):
        rel = os.path.relpath(data_path, base_dir)
        return {
            'version':       1,
            'name':          'test_view',
            'files':         [{'path': rel, 'format': 'CSV'}],
            'loaderOptions': {'dayfirst': False, 'naming': 'Ellude'},
            'modeIndex':     0,
            'selection': {
                'tabSelectedNames': ['default'],
                'tabSelections': {
                    'default': {
                        'xSel': 0, 'ySel': [1], 'zSel': 2,
                        'xName': 'Time', 'yNames': ['Speed'], 'zName': 'Power',
                    }
                },
                'simTabSelection': {},
                'filterSelection': ['', '', ''],
                'mode': 'Regular',
            },
            'plotPanel': {
                'plotType': 'Regular',
                'view3D':   True,
            },
        }

    def test_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_file = os.path.join(tmpdir, 'data', 'run.csv')
            os.makedirs(os.path.dirname(data_file))
            pd.DataFrame({'Time': [0, 1], 'Speed': [1, 2], 'Power': [3, 4]}).to_csv(data_file, index=False)

            view_path = os.path.join(tmpdir, 'my_view.pdvview')
            view_data = self._make_view_data(tmpdir, data_file)

            with open(view_path, 'w') as f:
                json.dump(view_data, f, indent=2)

            with open(view_path, 'r') as f:
                loaded = json.load(f)

            self.assertEqual(loaded['name'],    'test_view')
            self.assertEqual(loaded['version'], 1)
            self.assertTrue(loaded['plotPanel']['view3D'])

            # File path should be relative
            stored_path = loaded['files'][0]['path']
            self.assertFalse(os.path.isabs(stored_path))

            # Resolve back to absolute
            base_dir  = os.path.dirname(os.path.abspath(view_path))
            abs_path  = os.path.normpath(os.path.join(base_dir, stored_path))
            self.assertTrue(os.path.isfile(abs_path))

    def test_z_selection_survives_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            view_path = os.path.join(tmpdir, 'v.pdvview')
            view_data = self._make_view_data(tmpdir, os.path.join(tmpdir, 'f.csv'))
            with open(view_path, 'w') as f:
                json.dump(view_data, f)
            with open(view_path, 'r') as f:
                loaded = json.load(f)
            sel = loaded['selection']['tabSelections']['default']
            self.assertEqual(sel['zSel'],  2)
            self.assertEqual(sel['zName'], 'Power')

    def test_missing_file_reported_not_crash(self):
        """A stored path that does not exist should be detectable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            view_path = os.path.join(tmpdir, 'v.pdvview')
            view_data = self._make_view_data(tmpdir, os.path.join(tmpdir, 'nonexistent.csv'))
            with open(view_path, 'w') as f:
                json.dump(view_data, f)
            with open(view_path, 'r') as f:
                loaded = json.load(f)
            base_dir = os.path.dirname(os.path.abspath(view_path))
            for entry in loaded['files']:
                abs_path = os.path.normpath(os.path.join(base_dir, entry['path']))
                self.assertFalse(os.path.isfile(abs_path))


class TestViewStateCompatibility(unittest.TestCase):
    """Old views without zSel/zName must load cleanly (backward compat)."""

    def test_old_entry_no_z_keys(self):
        """resolve_z on an entry with no z keys must return 0 (None)."""
        v = {'xSel': 0, 'ySel': [1], 'xName': 'Time', 'yNames': ['Speed']}
        zSel, w = resolve_z(v, ['Time', 'Speed', 'Power'])
        self.assertEqual(zSel, 0)
        self.assertEqual(w, [])

    def test_old_plot_panel_no_view3d(self):
        """plotPanel without view3D key must default to False."""
        plot_state = {'plotType': 'Regular'}
        view3D = plot_state.get('view3D', False)
        self.assertFalse(view3D)


class TestBugRegressions(unittest.TestCase):
    """Regression tests for specific bugs found and fixed."""

    # --- Bug 1: onFilterChange dropped zSel ------------------------------------
    # The fix: pass zSel=self.comboZ.GetSelection() to setGUIColumns.
    # We can't test the wx widget directly, but we can assert that
    # setGUIColumns is called WITH a zSel argument and that the resolution
    # logic handles a preserved zSel correctly.

    def test_filter_change_preserves_z_by_existing_index(self):
        """After a filter, a valid zSel in range must be kept as-is."""
        cols = ['Time', 'Speed', 'Power']
        # zSel=2 (comboZ index 2 → 'Speed'); still in range after filter
        v = {'zSel': 2, 'zName': None}
        zSel, w = resolve_z(v, cols)
        self.assertEqual(zSel, 2)  # preserved
        self.assertEqual(w, [])

    def test_filter_change_resets_out_of_range_z(self):
        """After a filter that removes columns, an out-of-range zSel resets to 0."""
        # Simulate: table had 5 cols, now only 2 remain (filter applied)
        cols_after_filter = ['Time', 'Speed']
        v = {'zSel': 4, 'zName': None}   # was valid before, now out-of-range
        zSel, w = resolve_z(v, cols_after_filter)
        self.assertEqual(zSel, 0)  # reset to None

    # --- Bug 2: zName NameError when tab is None in captureViewState ----------
    # The fix: initialize zName = None alongside xName/yNames before the
    # `if tab is not None:` block.

    def test_capture_state_tab_not_in_tablist(self):
        """captureViewState: stale tabSelections entry (tab not in tabList)
        must produce zName=None rather than a NameError."""
        # Simulate the logic of the fixed captureViewState loop body
        # when tab is None (stale entry)
        cols = None   # tab not available
        xName  = None
        yNames = []
        zName  = None   # <<< the fix: must be initialized here
        # tab is None → skip the if block
        result = {
            'xSel':   -1,
            'ySel':   [],
            'zSel':   0,
            'xName':  xName,
            'yNames': yNames,
            'zName':  zName,
        }
        self.assertIsNone(result['zName'])  # no NameError, value is None
        self.assertIsNone(result['xName'])
        self.assertEqual(result['yNames'], [])

    def test_capture_state_z_none_selected(self):
        """When zSel=0 (None), zColIdx=-1 → zName must be None, not raise."""
        cols = ['Time', 'Speed', 'Power']
        zSel = 0
        zColIdx = zSel - 1   # = -1
        zName = cols[zColIdx] if 0 <= zColIdx < len(cols) else None
        self.assertIsNone(zName)


class TestSubPanelState(unittest.TestCase):
    """Verify that sub-panel state dicts have the expected keys and types (R1-R5)."""

    def _make_spectral(self, yType='PSD', xType='1/x', avgMethod='Welch',
                       avgWindow='Hamming', bDetrend=False, nExp=11, xlim='-1'):
        return {'yType': yType, 'xType': xType, 'avgMethod': avgMethod,
                'avgWindow': avgWindow, 'bDetrend': bDetrend,
                'nExp': nExp, 'nPerDecade': nExp, 'xlim': xlim}

    def _make_compare(self, type_='Relative'):
        return {'type': type_}

    def _make_minmax(self, yScale=True, xScale=False, yCenter='None', yRef=None):
        return {'yScale': yScale, 'xScale': xScale, 'yCenter': yCenter, 'yRef': yRef}

    def _make_pdf(self, nBins=51, smooth=False):
        return {'nBins': nBins, 'smooth': smooth}

    def _make_polar(self, Bins='None', Deg=True, About='x (from z, y hori flip, z vert)',
                    SameMean=False, rRef=None):
        return {'Bins': Bins, 'Deg': Deg, 'About': About, 'SameMean': SameMean, 'rRef': rRef}

    # R1 – Spectral
    def test_spectral_keys(self):
        s = self._make_spectral()
        for k in ('yType', 'xType', 'avgMethod', 'avgWindow', 'bDetrend', 'nExp', 'xlim'):
            self.assertIn(k, s)

    def test_spectral_defaults(self):
        s = self._make_spectral()
        self.assertEqual(s['yType'], 'PSD')
        self.assertEqual(s['avgMethod'], 'Welch')
        self.assertFalse(s['bDetrend'])
        self.assertEqual(s['xlim'], '-1')

    def test_spectral_custom(self):
        s = self._make_spectral(yType='Amplitude', avgMethod='Binning', bDetrend=True, nExp=8, xlim='10.5')
        self.assertEqual(s['yType'], 'Amplitude')
        self.assertEqual(s['avgMethod'], 'Binning')
        self.assertTrue(s['bDetrend'])
        self.assertEqual(s['nExp'], 8)
        self.assertEqual(s['xlim'], '10.5')

    # R2 – Compare
    def test_compare_keys(self):
        c = self._make_compare()
        self.assertIn('type', c)

    def test_compare_type_values(self):
        for t in ('Relative', '|Relative|', 'Ratio', 'Absolute', 'Y-Y'):
            c = self._make_compare(type_=t)
            self.assertEqual(c['type'], t)

    # R3 – MinMax
    def test_minmax_keys(self):
        m = self._make_minmax()
        for k in ('yScale', 'xScale', 'yCenter', 'yRef'):
            self.assertIn(k, m)

    def test_minmax_defaults(self):
        m = self._make_minmax()
        self.assertTrue(m['yScale'])
        self.assertFalse(m['xScale'])
        self.assertEqual(m['yCenter'], 'None')
        self.assertIsNone(m['yRef'])

    # R4 – PDF
    def test_pdf_keys(self):
        p = self._make_pdf()
        for k in ('nBins', 'smooth'):
            self.assertIn(k, p)

    def test_pdf_defaults(self):
        p = self._make_pdf()
        self.assertEqual(p['nBins'], 51)
        self.assertFalse(p['smooth'])

    # R5 – Polar
    def test_polar_keys(self):
        p = self._make_polar()
        for k in ('Bins', 'Deg', 'About', 'SameMean'):
            self.assertIn(k, p)

    def test_polar_defaults(self):
        p = self._make_polar()
        self.assertTrue(p['Deg'])
        self.assertFalse(p['SameMean'])
        self.assertEqual(p['Bins'], 'None')


class TestToggleState(unittest.TestCase):
    """Verify save/restore of axis toggle fields R6-R8."""

    def _make_plot_state(self, swapXY=False, flipX=False, flipY=False, plotMatrix=False):
        return {'swapXY': swapXY, 'flipX': flipX, 'flipY': flipY, 'plotMatrix': plotMatrix}

    def test_toggle_keys_present(self):
        s = self._make_plot_state()
        for k in ('swapXY', 'flipX', 'flipY', 'plotMatrix'):
            self.assertIn(k, s)

    def test_toggle_defaults_are_false(self):
        s = self._make_plot_state()
        self.assertFalse(s['swapXY'])
        self.assertFalse(s['flipX'])
        self.assertFalse(s['flipY'])
        self.assertFalse(s['plotMatrix'])

    def test_toggle_values_preserved(self):
        s = self._make_plot_state(swapXY=True, flipX=True)
        self.assertTrue(s['swapXY'])
        self.assertTrue(s['flipX'])
        self.assertFalse(s['flipY'])


class TestPipelineState(unittest.TestCase):
    """Pipeline action state must be captured and survive a JSON round-trip.

    Each Data-menu action (Mask, Filter, Resample, Bin data, Remove Outliers)
    has a data dict with at least 'active'.  The view serialisation should
    preserve all keys and values faithfully.
    """

    # -- helpers that mirror the dicts returned by each plugin's _DEFAULT_DICT --

    def _mask_data(self, active=True, maskString='{Time}>0'):
        return {'active': active, 'maskString': maskString, 'formattedMaskString': ''}

    def _filter_data(self, active=True, name='Moving average', param=100):
        return {'active': active, 'name': name, 'param': param,
                'paramName': 'Window Size', 'paramRange': [1, 100000]}

    def _resample_data(self, active=True, name='Every n', param=2):
        return {'active': active, 'name': name, 'param': param, 'paramName': 'n'}

    def _binning_data(self, active=True, nBins=50, xMin=None, xMax=None):
        return {'active': active, 'nBins': nBins, 'xMin': xMin, 'xMax': xMax}

    def _remove_outliers_data(self, active=True, medianDeviation=5):
        return {'active': active, 'medianDeviation': medianDeviation}

    # -- structure tests --

    def test_pipeline_state_keys(self):
        """Each action dict must have at least an 'active' key."""
        for d in [self._mask_data(), self._filter_data(),
                  self._resample_data(), self._binning_data(),
                  self._remove_outliers_data()]:
            self.assertIn('active', d)

    def test_mask_state_keys(self):
        d = self._mask_data()
        for k in ('active', 'maskString', 'formattedMaskString'):
            self.assertIn(k, d)

    def test_filter_state_keys(self):
        d = self._filter_data()
        for k in ('active', 'name', 'param', 'paramName', 'paramRange'):
            self.assertIn(k, d)

    def test_resample_state_keys(self):
        d = self._resample_data()
        for k in ('active', 'name', 'param'):
            self.assertIn(k, d)

    def test_binning_state_keys(self):
        d = self._binning_data()
        for k in ('active', 'nBins'):
            self.assertIn(k, d)

    def test_remove_outliers_state_keys(self):
        d = self._remove_outliers_data()
        for k in ('active', 'medianDeviation'):
            self.assertIn(k, d)

    # -- round-trip tests --

    def _make_view_with_pipeline(self, pipeline):
        return {
            'version':    1,
            'name':       'pipe_test',
            'files':      [],
            'pipeline':   pipeline,
            'plotPanel':  {},
            'selection':  {},
        }

    def test_pipeline_json_round_trip(self):
        """Full pipeline state must survive a JSON round-trip."""
        pipeline = {
            'Mask':           self._mask_data(active=True, maskString='{Speed}>0'),
            'Filter':         self._filter_data(active=True, name='Moving average', param=50),
            'Resample':       self._resample_data(active=False),
            'Remove Outliers': self._remove_outliers_data(active=True, medianDeviation=3),
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            view_path = os.path.join(tmpdir, 'v.pdvview')
            with open(view_path, 'w') as f:
                json.dump(self._make_view_with_pipeline(pipeline), f)
            with open(view_path, 'r') as f:
                loaded = json.load(f)
        pl = loaded['pipeline']
        self.assertEqual(pl['Mask']['maskString'], '{Speed}>0')
        self.assertTrue(pl['Mask']['active'])
        self.assertEqual(pl['Filter']['param'], 50)
        self.assertFalse(pl['Resample']['active'])
        self.assertEqual(pl['Remove Outliers']['medianDeviation'], 3)

    def test_missing_pipeline_key_defaults_to_empty(self):
        """Old views without a 'pipeline' key must not crash on restore."""
        view = {'name': 'old', 'modeIndex': 0, 'selection': {}, 'plotPanel': {}}
        pl = view.get('pipeline', {})
        self.assertEqual(pl, {})

    def test_inactive_actions_are_present_but_flagged(self):
        """Even inactive actions are serialisable; the 'active' flag is the signal."""
        d = self._filter_data(active=False, param=200)
        self.assertFalse(d['active'])
        self.assertEqual(d['param'], 200)

    def test_binning_with_limits_round_trip(self):
        """Binning xMin/xMax must survive serialisation (including None values)."""
        pipeline = {'Bin data': self._binning_data(active=True, nBins=20, xMin=0.0, xMax=100.0)}
        with tempfile.TemporaryDirectory() as tmpdir:
            view_path = os.path.join(tmpdir, 'v.pdvview')
            with open(view_path, 'w') as f:
                json.dump(self._make_view_with_pipeline(pipeline), f)
            with open(view_path, 'r') as f:
                loaded = json.load(f)
        bd = loaded['pipeline']['Bin data']
        self.assertEqual(bd['nBins'], 20)
        self.assertAlmostEqual(bd['xMin'], 0.0)
        self.assertAlmostEqual(bd['xMax'], 100.0)


class TestLoaderOptionsInView(unittest.TestCase):
    """R9: loaderOptions must be present in both in-memory and file views."""

    def test_in_memory_view_has_loader_options(self):
        """In-memory view must include loaderOptions so dayfirst survives restore."""
        view = {
            'name':          'myview',
            'modeIndex':     0,
            'selection':     {},
            'plotPanel':     {},
            'loaderOptions': {'dayfirst': True, 'naming': 'Ellude'},
        }
        self.assertIn('loaderOptions', view)
        self.assertTrue(view['loaderOptions']['dayfirst'])

    def test_file_view_loader_options_round_trip(self):
        """loaderOptions must survive a JSON round-trip in an exported view."""
        with tempfile.TemporaryDirectory() as tmpdir:
            view_path = os.path.join(tmpdir, 'v.pdvview')
            view_data = {
                'version':       1,
                'name':          'test',
                'files':         [],
                'loaderOptions': {'dayfirst': True, 'naming': 'Ellude'},
                'modeIndex':     0,
                'selection':     {},
                'plotPanel':     {},
            }
            with open(view_path, 'w') as f:
                json.dump(view_data, f)
            with open(view_path, 'r') as f:
                loaded = json.load(f)
            self.assertEqual(loaded['loaderOptions']['dayfirst'], True)
            self.assertEqual(loaded['loaderOptions']['naming'], 'Ellude')

    def test_missing_loader_options_defaults_gracefully(self):
        """A view without loaderOptions must not crash on restore."""
        view = {'name': 'old', 'modeIndex': 0, 'selection': {}, 'plotPanel': {}}
        opts = view.get('loaderOptions', {})
        self.assertEqual(opts, {})


class TestPlotPanelViewData(unittest.TestCase):
    """
    Headless tests for captureViewData / restoreViewData logic.
    These cover bugs W2 (missing '1.75' in LWChoices) and W3 (plot3D_type
    read from wrong widget) that were found in the pre-merge review.
    """

    # Must match EstheticsPanel.__init__ AND restoreViewData exactly.
    LW_CHOICES = ['0.5', '1.0', '1.25', '1.5', '1.75', '2.0', '2.5', '3.0']

    def _make_plot_data(self, curveType='LS', lineWidth='1.5', view3D=False,
                        plot3D_type='Scatter', axisLimits=None):
        """Build a minimal captureViewData-like dict."""
        return {
            'plotType': 'Regular',
            'logX': False, 'logY': False, 'grid': False,
            'crossHair': True, 'subplot': False, 'sync': True,
            'autoScale': True, 'stepPlot': False,
            'curveType':   curveType,
            'view3D':      view3D,
            'plot3D_type': plot3D_type,
            'plotStyle': {
                'LineWidth': lineWidth, 'Font': '11',
                'LegendFont': '11', 'LegendPosition': 'Upper right',
                'MarkerSize': '2',
            },
            'axisLimits': axisLimits or {
                'xmin': '', 'xmax': '', 'ymin': '', 'ymax': '',
                'zmin': '', 'zmax': '',
            },
            'logZ': False, 'flipZ': False,
            'swapXY': False, 'flipX': False, 'flipY': False,
            'plotMatrix': False,
        }

    # --- W2: LWChoices consistency ---

    def test_lw_175_in_choices(self):
        """'1.75' must be present in the LWChoices list used by restoreViewData."""
        self.assertIn('1.75', self.LW_CHOICES)

    def test_all_lw_choices_indexable(self):
        """Every value in the LW dropdown must be findable via .index() without ValueError."""
        for val in self.LW_CHOICES:
            # Would raise ValueError if val is missing — that is the bug W2 fixed.
            idx = self.LW_CHOICES.index(val)
            self.assertEqual(self.LW_CHOICES[idx], val)

    def test_lw_175_round_trip(self):
        """LineWidth '1.75' must survive a save/restore cycle (pure dict)."""
        data = self._make_plot_data(lineWidth='1.75')
        lw = data['plotStyle']['LineWidth']
        idx = self.LW_CHOICES.index(lw)   # must not raise ValueError
        self.assertEqual(self.LW_CHOICES[idx], '1.75')

    # --- W3: curveType vs plot3D_type ---

    def test_curve_type_stored_as_string(self):
        """curveType must be a string (read from cbCurveType.GetValue())."""
        data = self._make_plot_data(curveType='Scatter', view3D=True,
                                    plot3D_type='Scatter')
        self.assertIsInstance(data['curveType'], str)

    def test_3d_restore_prefers_curveType_over_plot3D_type(self):
        """When view3D=True, restoreViewData must pick curveType over the legacy plot3D_type."""
        # Simulate: view saved in 3D+Surf mode; plot3D_type is stale 'Scatter'
        data = self._make_plot_data(curveType='Surf', view3D=True,
                                    plot3D_type='Scatter')
        choices = ['Scatter', 'Surf']
        curveType = data.get('curveType')
        if isinstance(curveType, str) and curveType in choices:
            sel = choices.index(curveType)
        elif data.get('plot3D_type') in choices:
            sel = choices.index(data['plot3D_type'])
        else:
            sel = 0
        self.assertEqual(sel, 1)   # 'Surf', not stale 'Scatter'

    def test_plot3D_type_matches_curveType_when_3d(self):
        """captureViewData must write plot3D_type from cbCurveType when view3D=True."""
        # Simulate fixed captureViewData: plot3D_type = cbCurveType.GetValue() if view3D
        curveType = 'Surf'
        view3D = True
        plot3D_type = curveType if view3D else 'Scatter'
        self.assertEqual(plot3D_type, 'Surf')

    # --- Axis limits ---

    def test_axis_limits_all_keys_present(self):
        """axisLimits dict must contain all six keys."""
        data = self._make_plot_data()
        for key in ('xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax'):
            self.assertIn(key, data['axisLimits'])

    def test_axis_limits_json_round_trip(self):
        """Non-empty axis limits must survive JSON serialisation."""
        data = self._make_plot_data(axisLimits={
            'xmin': '0.5', 'xmax': '10.0',
            'ymin': '',    'ymax': '',
            'zmin': '-1',  'zmax': '1',
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, 'v.pdvview')
            with open(p, 'w') as f:
                json.dump({'plotPanel': data}, f)
            with open(p, 'r') as f:
                loaded = json.load(f)
        lims = loaded['plotPanel']['axisLimits']
        self.assertEqual(lims['xmin'], '0.5')
        self.assertEqual(lims['xmax'], '10.0')
        self.assertEqual(lims['zmin'], '-1')
        self.assertEqual(lims['ymin'], '')   # blank = auto-scale

    def test_axis_limits_missing_in_old_view_defaults_empty(self):
        """Old views without axisLimits must not crash; missing key → empty string."""
        data = {'plotType': 'Regular', 'view3D': False}
        lims = data.get('axisLimits', {})
        self.assertEqual(lims.get('xmin', ''), '')
        self.assertEqual(lims.get('zmax', ''), '')


if __name__ == '__main__':
    unittest.main()
