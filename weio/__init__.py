from .File import *
from .FileFormats import *
# User defined formats
from .Fast import *
from .CSV import *

def fileFormats():
    formats = []
    formats.append(FileFormat(FastFile))
    formats.append(FileFormat(FastOutASCIIFile))
    formats.append(FileFormat(CSVFile))
    return formats


def detectFormat(filename):
    formats=fileFormats()

    ext = os.path.splitext(filename.lower())[1]
    with open(filename) as f:
        head=[next(f).strip() for x in range(2)]

    detected = False

    i = 0 
    while not detected and i<len(formats):
        myformat = formats[i]
        if ext in myformat.extensions:
            if myformat.isValid(filename):
                detected=True
                #print('File detected as :',myformat)
                return myformat

        i += 1

    if not detected:
        raise Exception('The file was not detected by detectFormat():'+filename)

def read(filename,fileformat=None):
    if fileformat is None:
        fileformat = detectFormat(filename)
    # Reading the file with the appropriate class
    return fileformat.constructor(filename)
