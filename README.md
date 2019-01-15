[![Build Status](https://travis-ci.org/ebranlard/pyDatView.svg?branch=master)](https://travis-ci.org/ebranlard/pyDatView)

# pyDatView

A crossplatform GUI to display tabulated data from files or python pandas dataframes. Some of its features are: multiples plots, FFT plots, probability plots, export of figures...
The file formats supported, are: CSV files and other formats present in the [weio](http://github.com/ebranlard/weio/) library.
Additional file formats can easily be added.

![Scatter](/../screenshots/screenshots/PlotScatter.png)

## QuickStart
For windows users, an installer executable is available here:
 - https://github.com/ebranlard/pyDatView/releases

For command line users:
```bash
git clone --recurse-submodules https://github.com/ebranlard/pyDatView
cd pyDatView
pip install -r requirements.txt
python pyDatView.py
```
Then you can simply add an alias to your bashrc or install the pydatview module
```bash
echo "alias pydat='python `pwd`/pyDatview.py'" >> ~/.bashrc
#python setup.py install
```



More information about the download, installation and requirements is provided further down this page.


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
- Automatic detection of fileformat (based on [weio](http://github.com/ebranlard/weio/) but possibility to add more formats)
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


## Download, installation and requirements
For windows users, an installer executable is available here (look for pyDatView\*.exe):
 - https://github.com/ebranlard/pyDatView/releases


For command line users, the script is compatible python 2.7 and python 3 and relies on the following python packages: `numpy` `matplotlib`, `pandas`, `xarray`, `wxpython`.
The script can be donwloaded as follows:
```bash
git clone --recurse-submodules https://github.com/ebranlard/pyDatView
```
If you have pip installed on your system, you can install the dependencies 
```bash
pip install -r requirements.txt
```
If you have trouble installing wxPython, check their [https://wiki.wxpython.org/](wiki page)

To run the script standalone, no further installation steps are required, simply run:
```bash
python pyDatView.py
```
If you want to install the package to use it within python, run the following:
```bash
python setup.py install
```


## System-wide installation
For windows users the installer should register the program and it should be accessible in the startmenu.

Linux/Mac:
Make the file `pyDatView.py` executable and add it to your system path



## Adding more file formats
File formats can be added by implementing a subclass of `weio/File.py`, for instance `weio/VTKFile.py`. Existing examples are found in the folder `weio`.
Once implemented the fileformat needs to be registered in `weio/__init__.py` by adding an import line at the beginning of this script and adding a line in the function `fileFormats()` of the form `formats.append(FileFormat(VTKFile))`






