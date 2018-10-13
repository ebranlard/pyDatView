# pyDatView

A crossplatform GUI to display tabulated data from files or python pandas dataframes. Some of its features are: multiples plots, FFT plots, probability plots, export of figures...
The file formats supported, are: CSV files and other formats present in the [weio](http://github.com/elmanuelito/weio/) library.
Additional file formats can easily be added.

## Usage
The main script is executable and will open the GUI directly. A command line interface is provided, e.g.: 
```bash
pyDatView file.csv
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
- Automatic detection of fileformat (based on [weio](http://github.com/elmanuelito/weio/) but possibility to add more formats)
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

## Screenshots

Scatter plot (by selecting `Scatter`) and several plots on the same figure:

![Scatter](/../screenshots/screenshots/PlotScatter.png)

<!--![OverPlot](/../screenshots/screenshots/OverPlot.png) -->

Fast Fourier Transform of the signals (by selecting `FFT`) and displaying several plots using subfigures (by selecting `Subplot`). 

![SubPlotFFT](/../screenshots/screenshots/SubPlotFFT.png)

Probability density function:

![PlotPDF](/../screenshots/screenshots/PlotPDF.png)

Scaling all plots between 0 and 1 (by selecting `MinMax`)

![PlotMinMax](/../screenshots/screenshots/PlotMinMax.png)


## Requirements
The script is compatible python 2.7 and python 3.
The script relies on the following python packages: `numpy` `matplotlib`, `pandas`, `wxpython`, `click`

If you have pip installed on your system, you can install them by typing in a terminal: 
```bash
pip install numpy matplotlib pandas wxpython click 
```
or type `make dep` from the main directory.

If you have trouble installing wxPython, check their (wiki page)[https://wiki.wxpython.org/]

## Download 
From a command line:
```bash
git clone --recurse-submodules https://github.com/elmanuelito/pyDatView
cd pyDatView
```
If you don't have git installed, you can download the pyDatView and weio repositories with the links below:
(http://github.com/elmanuelito/weio/zipball/master/)
(http://github.com/elmanuelito/pyDatView/zipball/master/)
Then, place the content of the weio zip archive into the folder weio of the pyDatView directory.


### Installation
The python packages mentioned in the Requirements section need to be installed.
To run the script standalone, no further installation steps are required, simply run:
```bash
python pyDatView.py
```

If you want to install the package to use it within python, run the following:
```bash
python setup.py install
```
or type `make install` from the main directory.

### System-wide installation
Windows:
The repository has a file `pyDatView.cmd`. If python is in your system path, double clicking on this file should open the application. Drag and dropping a file to this script will open the file. 
To make the program accessible, you can create a shortcut to the file `pyDatView.cmd` and add it to your QuickLaunch toolbar if you have one.


Linux/Mac:
Make the file `pyDatView.py` executable and add it to your system path



### Adding more file formats
File formats can be added by implementing a subclass of `weio/File.py`, for instance `weio/VTKFile.py`. Existing examples are found in the folder `weio`.
Once implemented the fileformat needs to be registered in `weio/__init__.py` by adding an import line at the beginning of this script and adding a line in the function `fileFormats()` of the form `formats.append(FileFormat(VTKFile))`






