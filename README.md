[![Build Status](https://travis-ci.org/ebranlard/pyDatView.svg?branch=master)](https://travis-ci.org/ebranlard/pyDatView)
<a href="https://www.buymeacoffee.com/hTpOQGl" rel="nofollow"><img alt="Donate just a small amount, buy me a coffee!" src="https://warehouse-camo.cmh1.psfhosted.org/1c939ba1227996b87bb03cf029c14821eab9ad91/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f446f6e6174652d4275792532306d6525323061253230636f666665652d79656c6c6f77677265656e2e737667"></a>



# pyDatView

A crossplatform GUI to display tabulated data from files or python pandas dataframes. It's compatible Windows, Linux and MacOS, python 2 and python 3. Some of its features are: multiples plots, FFT plots, probability plots, export of figures...
The file formats supported, are: CSV files and other formats present in the [weio](http://github.com/ebranlard/weio/) library.
Additional file formats can easily be added.

![Scatter](/../screenshots/screenshots/PlotScatter.png)

## QuickStart
For **Windows** users, an installer executable is available [here](https://github.com/ebranlard/pyDatView/releases) (look for the latest pyDatView\*.exe)

**Linux** and **MacOS** users can use the command lines below. **Linux** users may need to install the package python-wxgtk\* (e.g. `python-gtk3.0`) from their distribution. **MacOS** users can use a `brew`, `anaconda` or `virtualenv` version of python and pip, but the final version of python that calls the script needs to have access to the screen (see [details for MacOS](#macos-installation)). The main commands for **Linux** and **MacOS** users are:
```bash
git clone --recurse-submodules https://github.com/ebranlard/pyDatView
cd pyDatView
python -m pip install --user -r requirements.txt
make     # executes: 'python pyDatView.py' (on linux) or './pythonmac pyDatView.py' (on Mac)
```
More information about the download, requirements and installation is provided [further down this page](#installation)


## Usage
The main script is executable and will open the GUI directly. A command line interface is provided, e.g.: 
```bash
pyDatView file.csv
```
The python package can also be used directly from python/jupyter to display a dataframe or show the data in a file
```python
import pydatview 
pydatview.show(dataframe=df)
# OR
pydatview.show(filename='file.csv')
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



## Installation

### Windows installation
For Windows users, installer executables are available [here](https://github.com/ebranlard/pyDatView/releases) (look for the latest pyDatView\*.exe)

### Linux installation
The script is compatible python 2.7 and python 3 and relies on the following python packages: `numpy` `matplotlib`, `pandas`, `wxpython`.
To download the code and install the dependencies (with pip) run the following:
```bash
git clone --recurse-submodules https://github.com/ebranlard/pyDatView
cd pyDatView
python -m pip install --user -r requirements.txt
```
If the installation of `wxpython` fails, you may need to install the package python-wxgtk\* (e.g. `python-gtk3.0`) from your distribution. For Debian/Ubuntu systems, try:
`sudo apt-get install python-wxgtk3.0`.
For further troubleshooting you can check the [wxPython wiki page](https://wiki.wxpython.org/).

If the requirements are successfully installed you can run pyDatView by typing:
```bash
python pyDatView.py
```
To easily access it later, you can add an alias to your `.bashrc` or install the pydatview module:
```bash
echo "alias pydat='python `pwd`/pyDatview.py'" >> ~/.bashrc
# or
python setup.py install
```


## MacOS installation
The installation works with python2 and python3, with `brew` (with or without a `virtualenv`) or `anaconda`.
First, download the source code:
```bash
git clone --recurse-submodules https://github.com/ebranlard/pyDatView
cd pyDatView
```
Before installing the requirements, you need to be aware of the two following issues with MacOS:
- If you are using the native version of python, there is an incompatibility between the native version of `matplotlib` on MacOS and the version of `wxpython`. The solution is to use `virtualenv`, `brew` or `anaconda`.
- To use a GUI app, you need a python program that has access to the screen. These special python programs are in different locations. For the system-python, it's usually in `/System`, the `brew` versions are usually in `/usr/local/Cellar`, and the `anaconda` versions are usually called `python.app`.
The script `pythonmac` provided in this repository attempt to find the correct python program depending if you are in a virtual environment, in a conda environment, a system-python or a python from brew or conda. 

Different solutions are provided below depending on your preferred way of working.

### Brew-python version (outside of a virtualenv)
If you have `brew` installed, and you installed python with `brew install python`, then the easiest is to use your `python3` version:
```
python3 -m pip install --user -r requirements.txt
python3 pyDatView.py
```

### Brew-python version (inside a virtualenv)
If you are inside a virtualenv, with python 2 or 3, use:
```
pip install -r requirements.txt
./pythonmac pyDatView.py
```
If the `pythonmac` commands fails, contact the developer, and in the meantime try to replace it with something like:
```
$(brew --prefix)/Cellar/python/XXXXX/Frameworks/python.framework/Versions/XXXX/bin/pythonXXX
```
where the result from `brew --prefix` is usually `/usr/loca/` and the `XXX` above corresponds to the version of python you are using in your virtual environment.


### Anaconda-python version (outside a virtualenv)
The installation of anaconda sometimes replaces the system python with the anaconda version of python. You can see that by typing `which python`. Use the following:
```
python -m pip install --user -r requirements.txt
./pythonmac pyDatView.py
```
If the `pythonmac` commands fails, contact the developer, and in the meantime try to replace it with a path similar to
```bash
/anaconda3/bin/python.app
```
where `/anaconda3/bin/` is the path that would be returned by the command `which conda`. Note the `.app` at the end. If you don't have `python.app`, try installing it with `conda install -c anaconda python.app`


### Easy access
To easily access the program later, you can add an alias to your `.bashrc` or install the pydatview module:
```bash
echo "alias pydat='python `pwd`/pyDatview.py'" >> ~/.bashrc
# or
python setup.py install
```





## Adding more file formats
File formats can be added by implementing a subclass of `weio/File.py`, for instance `weio/VTKFile.py`. Existing examples are found in the folder `weio`.
Once implemented the fileformat needs to be registered in `weio/__init__.py` by adding an import line at the beginning of this script and adding a line in the function `fileFormats()` of the form `formats.append(FileFormat(VTKFile))`



## Contributing
Any contributions to this project are welcome! If you find this project useful, you can also buy me a coffee (donate a small amount) with the link below:


<a href="https://www.buymeacoffee.com/hTpOQGl" rel="nofollow"><img alt="Donate just a small amount, buy me a coffee!" src="https://warehouse-camo.cmh1.psfhosted.org/1c939ba1227996b87bb03cf029c14821eab9ad91/68747470733a2f2f696d672e736869656c64732e696f2f62616467652f446f6e6174652d4275792532306d6525323061253230636f666665652d79656c6c6f77677265656e2e737667"></a>



