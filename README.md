# pyDatView

A crossplatform GUI to display tabulated data from files or python pandas dataframes. Some of its features are: multiples plots, FFT plots, probability plots, export of figures...
The file formats supported, are: CSV files and other formats present in the [http://github.com/elmanuelito/weio/](weio) library.
Additional file formats can easily be added.

## Usage
The main script is executable and will open the GUI directly. A command line interface is provided, e.g.: 
```bash
pydatview -i file.csv
```
The python package can also be used directly from python/jupyter to display a dataframe or show the data in a file
```python
import pydatview 
pydatview.pydatview(dataframe=df)
# OR
pydatview.pydatview(filename='file.csv')
```

## Features
Main features:
- Plot of tabular data within a file
- Automatic detection of fileformat (based on [http://github.com/elmanuelito/weio/](weio) but possibility to add more formats)
- Reload of data (e.g. on file change)
- Display of statistics
- Export figure as pdf, png, eps, svg

Kind of plots:
- Scatter plots or line plots
- Multiple plots using sub-figures or a different colors
- Probability density function (PDF) plot
- Fast Fourier Transform (FFT) plot

Plot options:
- Logarithmic scales on x and y axis
- Scaling of data between 0 and 1 using min and max
- Synchronization of the x-axis of the sub-figures while zooming


## Requirements
The script is compatible python 2.7 and python 3.
The script relies on the following python packages: `numpy` `matplotlib`, `pandas`, `wxpython`, `click`

If you have pip installed on your system, you can install them by typing in a terminal: 
```bash
pip install numpy matplotlib pandas wxpython click 
```

If you have trouble installing wxPython, check their [https://wiki.wxpython.org/](wiki page)

## Download 
From the github page, click on the "Clone or download" button, and you may chose to download as Zip.
Alternatively, from a command line:

```bash
git clone https://github.com/elmanuelito/pyDatView
cd pyDatView
```

### Installation
The python packages mentioned in the Requirements section need to be installed.
To run the script standalone, no further installation steps are required, simply run:
```bash
python pyDatView
```

If you want to install the package to use it within python, run the following:
```bash
python pyDatView
```

### System-wide installation



### Adding more file formats
File formats can be added by implementing a subclass of `weio/File.py`, for instance `weio/VTKFile.py`. Existing examples are found in the folder `weio`.
Once implemented the fileformat needs to be registered in `weio/__init__.py` by adding an import line at the beginning of this script and adding a line in the function `fileFormats()` of the form `formats.append(FileFormat(VTKFile))`






