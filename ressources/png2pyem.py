from wx.tools import img2py
import sys
import os

library='../pydatview/icons.py'

for i,arg in enumerate(sys.argv[1:]):
    png  = arg
    name = os.path.splitext(os.path.basename(png))[0]

    img2py.img2py(image_file=png, python_file=library, imgName=name, icon=True, append=i>0)
