# pyDatView — Agent Guide

## What is pyDatView and When to Use It

pyDatView is a cross-platform GUI tool for loading, visualising, and analysing
**tabulated time-series and general tabular data**.  Use it when:

- A user wants to **inspect or plot data files** quickly without writing code
  (CSV, Excel, OpenFAST output, NetCDF, mat, HDF5, Parquet, …)
- A user asks to **compare signals** across multiple files or tables
- A user needs **spectral analysis** (FFT / PSD) or **probability density**
  plots without bespoke code
- A user wants to **apply pipeline operations** (filter, resample, bin,
  remove outliers) and immediately see the result
- A user asks to create a **reusable view** that can be shared with colleagues
  or re-opened later on different data
- A user needs to **export a clean Python script** that reproduces a plot for
  a report or publication
- A user is doing **wind-energy / OpenFAST post-processing** (specialised
  channel renaming, nodal averaging, etc.)

Do **not** use pyDatView as a replacement for general-purpose data processing
scripts, database queries, or machine-learning pipelines.

---

## Installation

```bash
# Clone and install dependencies
git clone https://github.com/ebranlard/pyDatView
cd pyDatView
pip install -r requirements.txt

# Launch
python pyDatView.py              # empty window
python pyDatView.py file.csv     # open one or more files directly
```

**macOS:** replace `python` with `pythonw`.
**Windows:** a self-contained installer (`pyDatView*.exe`) is available from
the GitHub releases page.

---

## Launching from Python

```python
import pydatview

# Open by filename
pydatview.show('results.csv')
pydatview.show(['run1.out', 'run2.out'])

# Pass DataFrames directly
pydatview.show(df)
pydatview.show([df1, df2], names=['Baseline', 'Modified'])

# Mix DataFrames and files
pydatview.show(dataframes=[df], filenames=['ref.csv'])
```

`show()` blocks until the window is closed and returns nothing.

---

## Supported File Formats (40+)

| Category | Extensions / Formats |
|---|---|
| Generic tabular | `.csv`, `.txt`, `.xls`, `.xlsx`, `.parquet`, `.pkl` |
| Scientific | `.nc` (NetCDF), `.mat` (MATLAB), `.tdms`, `.vtu` / `.pvtu` (VTK) |
| OpenFAST / FAST | `.out`, `.outb`, `.fst`, `.dat`, linearisation files, summary files |
| Wind files | `.bts` (TurbSim), Bladed, HAWCStab2, HAWC2 |
| Other | Tecplot `.dat`, GNUPlot, Plot3D, Cactus, RAAW MAT, FLEX, BModes |
| Config | `.yaml` / `.yml` |

Format is detected automatically from the file extension.  Use the **Format**
dropdown in the toolbar to force a specific reader.

---

## GUI Layout

```
┌─ Menu Bar ─────────────────────────────────────────────────────┐
├─ Toolbar  [Mode] [Format] [Live Plot ☑] [Views dropdown]───────┤
├─ Selection Panel (left) ─────────────────┬─ Plot Canvas (right)┤
│  ┌─ Table list ──────────────────────┐   │  (matplotlib)       │
│  ├─ Column Panel 1 ─────────────────┤   │                     │
│  │  X-axis  [dropdown]              │   ├─ Plot controls ─────┤
│  │  Z/Color [dropdown]              │   │  type · PDF · FFT   │
│  │  Filter  [regex]                 │   │  MinMax · Polar     │
│  │  Column list (multi-select)      │   │  Colormap · Aesthet.│
│  ├─ Column Panel 2 (compare mode) ──┤   ├─ Info / Stats ──────┤
│  └─ Column Panel 3 (3-table mode) ──┘   │  mean·std·min·max   │
├─ Pipeline bar (bottom) ─────────────────┴─────────────────────┤
└────────────────────────────────────────────────────────────────┘
```

Panels can be resized by dragging the sashes.  Each panel remembers its last
width independently.

---

## File and Table Operations

### Opening files
- **File → Open** (Ctrl+O): replace current data with new file(s)
- **File → Add file** (Ctrl+A): add file(s) to current session
- **Drag-and-drop** onto the window; hold Ctrl while dropping to *add* rather
  than *replace*
- **File → Recent Files** submenu: last 30 opened/exported paths, newest first;
  `.pdvview` view files open directly as views

### Table context menu (right-click on table list)
- Rename, Delete, Reload from disk, Merge tables
- Export to CSV / Parquet / `.outb`

### Multi-table selection
Select multiple tables with Ctrl+click or Shift+click.  Use the **Mode**
dropdown to control column matching:

| Mode | Behaviour |
|---|---|
| Auto | pyDatView picks the best strategy |
| Same columns | Only columns present in all tables |
| Similar columns | Fuzzy name matching |
| 2 tables | Fixed two-table comparison layout |
| 3 tables | Fixed three-table layout |

---

## Column / Signal Selection

- **X-axis dropdown**: choose the independent variable (time, index, etc.)
- **Y-axis list**: multi-select with Click / Ctrl+Click / Shift+Click
- **Z/Color dropdown**: optional third variable — activates coloured scatter
  or 3-D view (see below)
- **Filter box**: live regex filter on column names; if exactly one match
  remains it is auto-selected

### Formula columns (right-click column list → "Add column from formula")
```
{Speed} * 0.5 * {Density} * {Area}   # arithmetic
np.sqrt({Fx}**2 + {Fy}**2)           # numpy functions
```
Predefined shortcuts: unit conversions, derivatives, correlations,
normalisations.

---

## Plot Types

Select via the radio buttons in the Plot Type panel on the right:

| Type | Description |
|---|---|
| **Regular** | Line or scatter plot (default) |
| **FFT** | Power spectral density (Welch or raw), frequency × PSD, amplitude |
| **PDF** | Histogram / probability density function |
| **MinMax** | Data normalised to [0, 1]; useful for shape comparison |
| **Compare** | Subplots side-by-side |
| **Polar** | Polar coordinates (beta) |

### Curve style (curve-type combo box)
- **2-D (no Z)**: Plain line, Least-Squares fit, Markers only, Mix
- **2-D + Z colour**: Scatter, Scatter+Line (thin grey connecting line with
  coloured scatter on top)
- **3-D view**: Scatter, Surface

### Subplot layout
- **Over plot**: all Y signals on one axes
- **Subplot**: one axes per signal, stacked vertically with shared X zoom
- **Comparison**: side-by-side subplots across tables

---

## Z / Color Variable and 3-D View

1. Select a column in the **Z/Color** dropdown (Column Panel 1, below X-axis)
2. The plot automatically switches to coloured scatter
3. A **colormap** selector and **colorbar** toggle appear below the canvas
4. Check **3D view** in the Color panel to render a true 3-D scatter or surface
5. 3-D interaction:
   - View preset buttons: XY plane / YZ plane / XZ plane / free perspective
   - Rotate: left-drag; Pan: Ctrl+left-drag; Zoom: scroll wheel
   - **Rotate button** in toolbar: toggle rotation mode

---

## Pipeline Actions

The pipeline bar at the bottom chains data-transformation steps that
**reapply automatically on every plot redraw** (including after file reload).

Available actions (via the "+" button or Plugins menu):

| Action | Effect |
|---|---|
| Mask | Zero-out or remove selected time ranges |
| Remove Outliers | Statistical outlier rejection |
| Filter | Low-pass, moving average, or custom FIR/IIR |
| Resample | Change sampling rate |
| Bin data | Aggregate into bins (useful for scatter data) |
| Standardise units (SI / WE) | Automatic unit conversion |
| OpenFAST: Nodal Average | Average radial / nodal data |
| OpenFAST: Rename channels | v2.3 / v3.4 channel-name migration |

---

## Measurements and Statistics

- **Left/Right cursors**: click on the canvas to place measurement markers;
  the info panel shows Δx and Δy
- **Info panel** (bottom right): mean, std, min, max, count for each selected
  signal; updated live
- Copy statistics to clipboard via right-click in the info panel

---

## Views — Save and Restore Complete Sessions

A **view** captures: selected tables, X/Y/Z columns, applied formulas, plot
type and settings, pipeline state, and panel sash widths.

### Named views (in-session)
- **Views → Save current view…** (Ctrl+S): type a name, saved in memory
- **Views selector** (toolbar dropdown): instantly restore any saved view
- Saved views survive file reloads within the same session

### Portable view files (`.pdvview`)
- **Views → Export view to file…**: saves a JSON file containing all settings
  *and relative paths to the source data files*
- **Views → Import view from file…**: restores the full session
- Share a `.pdvview` file with colleagues; as long as data files are at the
  same relative location the view reopens identically
- Opening a `.pdvview` via File → Open or Recent Files also restores it
- `.pdvview` files are also tracked in the Recent Files list

---

## Export

| Export target | How |
|---|---|
| Figure (PNG, PDF, SVG, EPS) | Save button in plot toolbar |
| Table data (CSV, Parquet, `.outb`) | Right-click table → Export, or File → Export table |
| Python script | File → Export script |
| View file (`.pdvview`) | Views → Export view to file |

### Python script export
Generates a standalone script that reproduces the current plot.  Options:
- Library flavour: `pydatview`, `welib`, `openfast_toolbox`
- DataFrames as dict, list, or enumeration
- Verbosity level for comments

The generated script is a starting point; a header note flags what may need
manual adjustment.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+O | Open file(s) |
| Ctrl+A | Add file(s) |
| Ctrl+R | Reload current files |
| Ctrl+S | Save current view |
| Ctrl+F | Focus column filter |

---

## Plot Aesthetics

Accessible via the **Aesthetics** panel (right side):
- Font size (6–18 pt)
- Line width (0.5–3.0)
- Marker size (0.5–8)
- Legend position (11 options including "None")
- Legend font size

Changes apply immediately to the canvas.

---

## Configuration and Persistence

Settings are stored in a JSON file in the platform's app-data directory
(e.g. `~/.pydatview_rc` on Linux).  Persisted state includes:

- Window size
- Font sizes
- Recent files list (30 entries)
- Named views
- Pipeline state
- Plot panel settings
- Loader options (e.g. date format `dayfirst`)

**Reset to defaults**: Help → Reset options (deletes the config file and
closes the application; reopen to start fresh).

---

## Programmatic / Scripting Notes

When helping a user write code that uses pyDatView:

```python
# Minimal example
import pandas as pd
import pydatview

df = pd.read_csv('data.csv')
pydatview.show(df, names=['My Data'])

# Multiple runs comparison
import glob
files = sorted(glob.glob('results_*.out'))
pydatview.show(filenames=files)
```

The `show()` call launches a blocking `wx.App` main loop.  It cannot be used
inside another `wx.App` or inside a Jupyter cell without special handling
(use `pydatview.showApp()` in a subprocess, or call from a standalone script).

Pipeline actions and view states can be scripted via internal APIs
(`MainFrame.addAction`, `captureViewState`, `restoreViewState`) but these are
internal and subject to change; prefer the GUI for interactive use.

---

## Quick Reference — Common Tasks

| Task | Steps in GUI |
|---|---|
| Open and plot a CSV | Ctrl+O → select file → pick X/Y columns |
| Compare two runs | Ctrl+O → select both files → Ctrl-click both in table list |
| FFT of a signal | Select signal → click **FFT** radio button |
| Add a derived channel | Right-click column list → Add formula |
| Filter noisy signal | Pipeline "+" → Filter → set cutoff |
| Save reusable session | Ctrl+S → type name; or Views → Export view to file |
| Export plot for report | Save button (floppy icon) in plot toolbar → PNG/PDF |
| Generate Python script | File → Export script |
| 3-D scatter | Select Z/Color column → check "3D view" |
