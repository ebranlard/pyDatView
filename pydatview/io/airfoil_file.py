import os
import pandas as pd
import numpy as np
from .csv_file import CSVFile, find_non_numeric_header_lines
from .plot3d_file import read_plot3d, write_plot3d
try:
    from .file import File, WrongFormatError, BrokenFormatError, EmptyFileError
except:
    File = dict
    EmptyFileError    = type('EmptyFileError', (Exception,),{})
    WrongFormatError  = type('WrongFormatError', (Exception,),{})
    BrokenFormatError = type('BrokenFormatError', (Exception,),{})

FORMAT_TO_EXT = {
    'csv': 'csv',
    'plot3d': 'fmt',
    'fmt': 'fmt',
    'xyz': 'xyz',
    'xy': 'xy',
    'g': 'g',
    'pointwise': 'pwise',
    'geo': 'geo',
}
EXT_TO_FORMAT = {
    'csv': 'csv',
    'txt': 'csv',
    'dat': 'csv',
    'fmt': 'plot3d',
    'xyz': 'plot3d',
    'xy': 'plot3d',
    'g': 'plot3d',
    'pwise': 'pointwise',
    'pw':    'pointwise',
    'geo': 'geo',
}
# --------------------------------------------------------------------------------{
# --- WEIO class
# --------------------------------------------------------------------------------}
class AirfoilShapeFile(File):
    """ 
    Read/write an airfoil shape (formatted, ASCII). The object behaves as a dictionary.

    Note: the class does not make any manipulation of the data

    Main methods
    ------------
    - read, write, toDataFrame, keys

    Examplesy
    --------
        f = AirfoilShapeFile('file.fmt')
        print(f.keys())
        print(f.toDataFrame().columns)  
    """

    @staticmethod
    def defaultExtensions():
        """ List of file extensions expected for this fileformat"""
        return ['.csv', '.dat', '.fmt', '.txt']

    @staticmethod
    def formatName():
        return 'Airfoil shape file'

    @staticmethod
    def priority(): return 60 # Priority in weio.read fileformat list between 0=high and 100:low

    def __init__(self, filename=None, **kwargs):
        """ Class constructor. If a `filename` is given, the file is read. """
        self.filename = filename
        self.data = None
        self.format = None
        if filename:
            self.read(**kwargs)

    def read(self, filename=None, verbose=False, format=None):
        """ Reads the file self.filename, or `filename` if provided """
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2, 'File not found:', self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:', self.filename)
        
        x, y, d = read_airfoil(self.filename, format=format, verbose=verbose)
        if 'format' in d:
            self.format = d['format']

        # Store
        self.data = pd.DataFrame({'x': x, 'y': y})
        for k,v in d.items():
            self[k] = v

    def write(self, filename=None, format=None, **kwargs):
        """ Rewrite object to file, or write object to `filename` if provided """
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        if format is None: 
            format = self.format # NOTE: not inferring from extension, change of behavior
        for k,v in self.items():
            if k not in kwargs and k not in ['x', 'y', 'format']:
                kwargs[k] = v


        write_airfoil(self.data['x'].values, self.data['y'].values, filename, format=format, **kwargs)

    def toDataFrame(self):
        """ Returns one DataFrame (single block) or a dict of DataFrames (multi-block) """
        return self.data

    def __repr__(self):
        s = '<{} object>:\n'.format(type(self).__name__)
        s += '|Main attributes:\n'
        s += '| - filename: {}\n'.format(self.filename)
        s += '| - format  : {}\n'.format(self.format)
        if self.data is not None:
            x = self.data['x'].values
            y = self.data['y'].values
            s += '| - data: shape:{}\n'.format(self.data.shape)
            s += '|      x: len:{} type:{} values:[{}, {}, ...,{}]\n'.format(len(x), x.dtype, x[0], x[1], x[-1] )
            s += '|      y: len:{} type:{} values:[{}, {}, ...,{}]\n'.format(len(y), y.dtype, y[0], y[1], y[-1] )
        s += '|Main keys from original input file:\n'
        for k,v in self.items():
            s += '| - {}: {}\n'.format(k, v)
        s += '|Main methods:\n'
        s += '| - read, write, toDataFrame, keys'
        return s

    def toString(self):
        """ """
        s = ''
        return s




# --------------------------------------------------------------------------------{
# --- Main wrappers
# --------------------------------------------------------------------------------}
def read_airfoil(filename, format=None, verbose=False, **kwargs):
    """ Read airfoil coordinates from a filename"""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"File {filename} does not exist.") 
    if format is None:
        ext = os.path.splitext(filename)[1].lower().strip('.')
        format = EXT_TO_FORMAT[ext]
    format = format.lower()
    if verbose:
        print(f"Reading airfoil from {filename} with format {format}")

    if format in ['csv','tab']:
        x, y, d = read_airfoil_csv_like(filename)
    elif format in ['plot3d','fmt','g','xyz','xy','x']:
        x, y, d = read_airfoil_plot3d(filename)
    elif format in ['pointwise', 'pw','pwise']:
        x, y, d = read_airfoil_pointwise(filename, plot=False)
    else:
        raise  NotImplementedError(f"File type {ext} is not supported.")

    
    if not np.issubdtype(x.dtype, np.floating) or not np.issubdtype(y.dtype, np.floating):
        print('First values of x:',x[0:5], x.dtype)
        print('First values of y:',y[0:5], y.dtype)
        raise ValueError("Ffile must contain floating point numbers in both columns. Maybe the header was not detected correctly?")

    return x, y, d

def write_airfoil(x, y, filename, format=None, **kwargs):
    """ Write airfoil coordinates to a file"""
    if format is None:
        ext = os.path.splitext(filename)[1].lower().strip('.')
        format = EXT_TO_FORMAT[ext]
    format = format.lower()
    if format in ['csv','tab']:
        write_airfoil_csv(x, y, filename)
    elif format in ['plot3d','fmt','g','xyz','xy','x']:
        write_airfoil_plot3d(x, y, filename, **kwargs)
    elif format in ['pointwise', 'pw','pwise']:
        write_airfoil_pointwise(x, y, filename)
    elif format == 'geo':
        write_airfoil_geo(x, y, filename, **kwargs)
    elif format == 'openfast':
        write_airfoil_openfast(x, y, filename, **kwargs)
    else:
        raise NotImplementedError(f"Format {format} is not supported.")

# --------------------------------------------------------------------------------}
# --- OpenFAST airfoil shape
# --------------------------------------------------------------------------------{
def read_airfoil_openfast(filename):
    """
    Reads a FAST-format airfoil file (with NumCoords and comments).
    Returns a dict with keys: 'x', 'y', 'AirfoilRefPoint', 'NumCoords'.
    """
    d = {}
    d['format'] = 'openfast'

    with open(filename, 'r', encoding='utf-8', errors='surrogateescape') as f:
        lines = f.readlines()

    # Find the line with NumCoords (first non-comment, with an int at start)
    numcoords = None
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith('!') or s.startswith('#'): continue
        try:
            numcoords = int(s.split()[0])
            idx_numcoords = i
            break
        except Exception:
            continue
    if numcoords is None:
        raise BrokenFormatError("Could not find NumCoords in file.")

    d['NumCoords'] = numcoords

    # Find the reference point (first non-comment, non-empty line after NumCoords)
    idx_ref = None
    comments1 =[]
    for j in range(idx_numcoords+1, len(lines)):
        s = lines[j].strip()
        if s.startswith('!') or s.startswith('#'): 
            comments1.append(s)
            continue
        try:
            vals = [float(x) for x in s.replace(',', ' ').split()]
            if len(vals) == 2:
                d['AirfoilRefPoint'] = np.array(vals)
                idx_ref = j
                break
        except Exception():
            continue
    if idx_ref is None:
        raise BrokenFormatError("Could not find airfoil reference point.")

    # Find the start of the coordinates (first non-comment, non-empty line after ref)
    coords = []
    d['comments'] =[]
    for k in range(idx_ref+1, len(lines)):
        s = lines[k].strip()
        if s.startswith('!') or s.startswith('#'): 
            d['comments'].append(s)
            continue
        #try:
        vals = [float(x) for x in s.replace(',', ' ').split()]
        if len(vals) == 2:
            coords.append(vals)
            if len(coords) >= numcoords:
                break
        else:
            raise BrokenFormatError('More than two values in line, expected only x and y coordinates.')
        # except Exception:
        #     continue

    coords = np.array(coords)
    if coords.shape[0] != numcoords-1: # Note: +1 for the reference point..
        raise BrokenFormatError(f"Expected {numcoords} coordinates, got {coords.shape[0]}.")

    x = coords[:,0]
    y = coords[:,1]
    return x, y, d

def write_airfoil_openfast(x, y, filename, AirfoilRefPoint=None, comments=None, NumCoords=None):
    """
    Writes airfoil coordinates to a FAST/OpenFAST airfoil shape file.
    - x, y: arrays of coordinates
    - filename: output file path
    - AirfoilRefPoint: (optional) 2-element array for the reference point, defaults to [0.25, 0.0]
    - comments: (optional) list of comment lines to write at the top of the file
    - NumCoords : neglected
    """
    if AirfoilRefPoint is None:
        AirfoilRefPoint = [0.25, 0.0]
        print('[WARN] No AirfoilRefPoint provided, using default [0.25, 0.0].')

    NumCoords = len(x) + 1

    if comments is None:
        comments = [
            "! coordinates of the airfoil shape",
            "!  x/c        y/c",
        ]
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"{NumCoords:<6d}   NumCoords         ! The number of coordinates in the airfoil shape file (including an extra coordinate for airfoil reference).  Set to zero if coordinates not included.\n")
        f.write("! ......... x-y coordinates are next if NumCoords > 0 .............\n")
        f.write("! x-y coordinate of airfoil reference\n")
        f.write("!  x/c        y/c\n")
        f.write(f"{AirfoilRefPoint[0]:.8f}\t{AirfoilRefPoint[1]:.8f}\n")
        for c in comments:
            f.write(f"{c}\n")
        for xi, yi in zip(x, y):
            f.write(f"{xi:.6f}\t{yi:.6f}\n")

# --------------------------------------------------------------------------------}
# --- CSV 
# --------------------------------------------------------------------------------{
def has_two_ints_on_second_line_and_third_empty(filename):
    """
    See for instance e850.dat

    Returns True if the second line of the file contains exactly two floats that can be coerced to integers,
    and the third line is empty (only whitespace or newline).
    """
    with open(filename, 'r', encoding='utf-8', errors='surrogateescape') as f:
        lines = []
        for _ in range(3):
            line = f.readline()
            if not line: break
            lines.append(line.rstrip('\n\r'))

    if len(lines) < 3: return False

    # Check second line
    parts = lines[1].strip().replace(',', ' ').split()
    if len(parts) != 2: return False
    try:
        floats = [float(p) for p in parts]
        ints   = [int(f) for f in floats]
        if not all(abs(f-i)<1e-8 for f,i in zip(floats,ints)):
            return False
    except Exception:
        return False

    # Check third line is empty
    if lines[2].strip() != '':
        return False

    return True

def is_OpenFAST_airfoil_shape(filename):
    """ Detect if the file is in OpenFAST airfoil shape format """
    with open(filename, 'r', encoding='utf-8', errors='surrogateescape') as f:
        lines = []
        for _ in range(2):
            line = f.readline()
            # check if line contains "NumCoords"
            if "numcoords" in line.lower():
                return True
            if not line: break
    return False


def read_airfoil_csv_like(filename):

    # --- Detect OpenFAST airfoil shape format
    if is_OpenFAST_airfoil_shape(filename):
        return read_airfoil_openfast(filename)

    # --- Find non-numeric header lines
    header_indices, header_lines = find_non_numeric_header_lines(filename)

    # We expect mostly 0 or one line of header. If more than one header line is found, it's best if lines start with a '#'
    if len(header_indices)> 1:
        print("[INFO] Found more than one header line in file ", filename)
    #    # count lines that do not start with "#"
    #    not_comment_lines = [line for line in header_lines if not line.startswith('#')]
    #    nNotComment = len(not_comment_lines)
    #    print("[INFO] Found non-comment header lines:", not_comment_lines)
    #    #if nNotComment > 0:
    #    #    raise Exception("Error: More than one header line found in the file. Please ensure the file has a single header line, no header lines at all, or that all header lines start with `#`.")


    if has_two_ints_on_second_line_and_third_empty(filename):
        raise BrokenFormatError('File format with separate Upper and Lower surfaces not yet supported, file {}.'.format(filename))

    #print('>>>> commentLines:', header_indices, 'header_lines:', header_lines)
    #csv = CSVFile(filename=filename, commentLines=header_indices, detectColumnNames=False, colNames=['x', 'y'], doRead=False)
    csv = CSVFile(filename=filename, commentLines=header_indices, doRead=False) #, detectColumnNames=False, colNames=['x', 'y'], doRead=False)
    try:
        csv._read()
    except WrongFormatError as e:
        print("[FAIL] {}".format(str(e).strip()))
        print("       > Trying to read the file with a slower method...")
        #print(csv)
        csv.read_slow_stop_at_first_empty_lines(numeric_only=True)

    df = csv.toDataFrame()
    #import pandas as pd
    #df = pd.read_csv(filename)
    #print(df)
    if df.shape[1] == 2:
        x = df.iloc[:, 0].values
        y = df.iloc[:, 1].values
    else:
        raise ValueError("CSV file must have exactly two columns for x and y coordinates.")
    # Check if numpy array are all floats, otherwise( e.g. if they are objects) raise an exception
    if not np.issubdtype(x.dtype, np.floating) or not np.issubdtype(y.dtype, np.floating):
        if x[-1] == 'ZZ':
            print('[WARN] File {} Last value of x is "ZZ", removing it and converting to float.'.format(filename))
            x=x[:-1].astype(float)
            y=y[:-1]
        else:
            print(csv)
            print('First values of x:',x[0:5], x.dtype)
            print('First values of y:',y[0:5], y.dtype)
            raise ValueError("CSV file must contain floating point numbers in both columns. Maybe the header was not detected correctly?")
    d={}
    d['format'] = 'csv'
    return x, y, d

def write_airfoil_csv(x, y, filename):
    df = pd.DataFrame({'x': x, 'y': y})
    df.to_csv(filename, index=False)

# --------------------------------------------------------------------------------}
# --- Plot3D
# --------------------------------------------------------------------------------{
def read_airfoil_plot3d(filename):
    coords, dims = read_plot3d(filename, singleblock=True)
    x = coords[:, 0]
    y = coords[:, 1]
    # Make sure we keep only the first slice in z-direction
    nx = dims[0]
    x = x[:nx]
    y = y[:nx]
    d = {}
    d['format'] = 'plot3d'
    return x, y, d

# --------------------------------------------------------------------------------}
# --- Pointwise
# --------------------------------------------------------------------------------{
def read_airfoil_pointwise(filename, plot=False, verbose=False):
    # TODO this is horrible code, needs to be refactored
    lower = []
    upper = []
    TE = []
    d= {}
    d['format'] = 'pointwise'

    with open(filename, 'r') as file:
        # Read the entire content of the file
        lines = file.readlines()

        current_section = 'lower'  # Starting with the lower section
        idx = 0  # Line index

        while idx < len(lines):
            line = lines[idx].strip()

            if line.isdigit():  # When the line is a number (point count)
                num_points = int(line)  # Get the number of points in the section
                idx += 1  # Move to the next line containing the coordinates

                # Read the next `num_points` lines and store x, y, z coordinates
                for _ in range(num_points):
                    if idx < len(lines):
                        x, y, z = map(float, lines[idx].strip().split())  # Parse x, y, z values
                        if current_section == 'lower':
                            lower.append((x, y, z))  # Append to the lower section
                        elif current_section == 'upper':
                            upper.append((x, y, z))  # Append to the upper section
                        elif current_section == 'TE':
                            TE.append((x, y, z))  # Append to the TE section
                        idx += 1  # Move to the next line containing coordinates

                # Switch sections after processing each part
                if current_section == 'lower':
                    current_section = 'upper'
                elif current_section == 'upper':
                    current_section = 'TE'
            
            else:
                idx += 1  # Skip lines that are not point counts or coordinates
    TE    = np.asarray(TE)[:,:2]# Keep only x and y coordinates
    lower = np.asarray(lower)[:,:2] 
    upper = np.asarray(upper)[:,:2]

    from nalulib.curves import contour_is_clockwise
    coords1 = np.vstack((lower[:-1], upper[:-1], TE))
    assert contour_is_clockwise(coords1), "Pointwise format is expected to be clockwise."
    assert np.allclose(coords1[0, :], coords1[-1, :], rtol=1e-10, atol=1e-12), "First and last points must be the same in Pointwise format."

    # NOTE: Pointwise is assumed to be clockwise
    TE = TE[::-1]  # Reverse the order of TE points to match the convention
    lower = lower[::-1]  # Reverse the order of lower surface points        
    upper = upper[::-1]  # Reverse the order of upper surface points

    # NOTE: coords are anticlockwise with first and last point being the same
    coords = np.vstack((upper[:-1], lower[:-1], TE))
    assert np.allclose(coords[0, :], coords[-1, :], rtol=1e-10, atol=1e-12), "First and last points must be the same in Pointwise format."

    if plot:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 5))
        plt.plot(coords[:,0], coords[:,1], '.-', label='Airfoil Shape', color='black')
        plt.plot(lower[:,0], lower[:,1], label='Lower Surface', color='blue')
        plt.plot(upper[:,0], upper[:,1], label='Upper Surface', color='red')
        plt.plot(TE[:,0], TE[:,1], label='Trailing Edge', color='green') 
        plt.title('Airfoil Shape with Upper and Lower Surfaces')
        plt.xlabel('x')
        plt.ylabel('y')
        plt.axis('equal')
        plt.legend()
        plt.grid(True)
        plt.show()

    return coords[:,0], coords[:,1], d 

def write_airfoil_pointwise(x, y, output_file):
    # === Load airfoil data ===
    x_orig, y_orig = x, y

    # === Find leading edge index (minimum x)
    le_index = np.argmin(x_orig)

    # === convert to .txt file format for Pointwise
    
    # === 1. Split into upper and lower surfaces
    x_orig_upper, y_orig_upper = x_orig[:le_index+1], y_orig[:le_index+1]
    x_orig_lower, y_orig_lower = x_orig[le_index:], y_orig[le_index:]

    # === 2. Sort both surfaces to save as .dat file without interpolation
    x_orig_lower_sorted, y_orig_lower_sorted = x_orig_lower[::-1], y_orig_lower[::-1]
    x_orig_upper_sorted, y_orig_upper_sorted =  x_orig_upper[::-1], y_orig_upper[::-1]

    
    # === 3. Save original data in .dat format ===
    with open(output_file, 'w') as f:
        # Write lower surface
        f.write(f"{len(x_orig_lower_sorted)}\n")
        for x, y in zip(x_orig_lower_sorted, y_orig_lower_sorted):
            f.write(f"{x:.6f} {y:.6f} 0.000000\n")

        # Write upper surface
        f.write(f"{len(x_orig_upper_sorted)}\n")
        for x, y in zip(x_orig_upper_sorted, y_orig_upper_sorted):
            f.write(f"{x:.6f} {y:.6f} 0.000000\n")

        # Write TE surface
        f.write(f"{3}\n")
        f.write(f"{x_orig_upper_sorted[-1]:.6f} {y_orig_upper_sorted[-1]:.6f} 0.000000\n")
        f.write(f"{((x_orig_upper_sorted[-1]+x_orig_lower_sorted[0])/2):.6f} {((y_orig_lower_sorted[0]+y_orig_upper_sorted[-1])/2):.6f} 0.000000\n")
        f.write(f"{x_orig_lower_sorted[0]:.6f} {y_orig_lower_sorted[0]:.6f} 0.000000\n")


# --------------------------------------------------------------------------------}
# --- gmesh 
# --------------------------------------------------------------------------------{
def write_airfoil_geo(x, y, output_file, lc=1.0):
    with open(output_file, 'w') as f_out:
        f_out.write("// Gmsh .geo file generated from 2D airfoil .txt\n\n")
        zz=0
        point_ids = np.arange(len(x), dtype=int) + 1  # Point IDs start from 1 in Gmsh
        for i, (xx, yy)in enumerate(zip(x, y)):
            f_out.write(f"Point({point_ids[i]}) = {{{xx}, {yy}, {zz}, {lc}}};\n")

        # Connect all points in a closed loop
        f_out.write("\n// Single Line connecting all points in a loop\n")
        line_str = ", ".join(str(pid) for pid in point_ids + [point_ids[0]])
        f_out.write(f"Line(1) = {{{line_str}}};\n")


def write_airfoil_plot3d(x, y, filename, thick=False):
    """ Write airfoil coordinates to a Plot3D file"""
    if thick:
        # We duplicate the x y coordiantes and have z=0 and z=1
        coords = np.column_stack((x, y, np.zeros_like(x)))
        coords = np.concatenate((coords, coords + np.array([0, 0, 1])))
        dims = (len(x), 2, 1)  # Two slices in the z-direction
    else:
        coords = np.column_stack((x, y, np.zeros_like(x)))  # Assuming z=0 for 2D airfoil
        dims = (len(x), 1, 1)  # Assuming a single slice in the z-direction
    write_plot3d(filename, coords, dims)


if __name__ == '__main__':
    shp = AirfoilShapeFile(os.path.join(os.path.dirname(__file__), '../../data/airfoils/tests/FAST_naca64618.txt'))
    print(shp)
    shp.write('test_openfast.txt')
    shp = AirfoilShapeFile('test_openfast.txt')
    print(shp)

