""" 
Input/output class for the fileformat supported by GNU Plot
"""
import numpy as np
import pandas as pd
import os


try:
    from .file import File, WrongFormatError, BrokenFormatError
except:
    File=dict
    EmptyFileError    = type('EmptyFileError', (Exception,),{})
    WrongFormatError  = type('WrongFormatError', (Exception,),{})
    BrokenFormatError = type('BrokenFormatError', (Exception,),{})

class GNUPlotFile(File):
    """ 
    Read/write a GnuPlot file. The object behaves as a dictionary.
    
    Main methods
    ------------
    - read, write, toDataFrame, keys
    
    Examples
    --------
        f = GNUPlotFile('file.xxx')
        print(f.keys())
        print(f.toDataFrame().columns)  
    
    """

    @staticmethod
    def defaultExtensions():
        """ List of file extensions expected for this fileformat"""
        return ['.dat']

    @staticmethod
    def formatName():
        """ Short string (~100 char) identifying the file format"""
        return 'GNUPlot file'

    @staticmethod
    def priority(): return 60 # Priority in weio.read fileformat list between 0=high and 100:low

    def __init__(self, filename=None, **kwargs):
        """ Class constructor. If a `filename` is given, the file is read. """
        self.filename = filename
        if filename:
            self.read(**kwargs)

    def read(self, filename=None, **kwargs):
        """ Reads the file self.filename, or `filename` if provided """
        
        # --- Standard tests and exceptions (generic code)
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2,'File not found:',self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:',self.filename)
        # --- Calling (children) function to read
        self._read(**kwargs)

    def write(self, filename=None):
        """ Rewrite object to file, or write object to `filename` if provided """
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        # Calling (children) function to write
        self._write()

    def _read(self):
        """ Reads self.filename and stores data into self. Self is (or behaves like) a dictionary"""
        # NOTE: for ascii files only
        with open(self.filename, 'r') as fid:
            data = []
            column_names = None
            headers = []
            current_dataset = []

            for line in fid:
                line = line.strip()
                # header
                if line.startswith('#'):
                    headers.append(line[1:].strip())
                    continue
                if not line:
                    # a new line triggers GNUPlot to "lift the pen"
                    if current_dataset:
                        data.append(np.array(current_dataset))
                        current_dataset = []
                    continue
                current_dataset.append(np.array(line.split()).astype(float))

            if current_dataset:
                data.append(np.array(current_dataset))

        # Try to detect column names from header
        same_columns, same_rows, n_cols, n_rows = check_same_shape(data)
        if same_columns:
            column_names = find_string_with_n_splits(headers, n_cols)

        self['data'] = data
        self['headers'] = headers
        self['column_names']= column_names

    def plot(self):
        import matplotlib.pyplot as plt
        data, column_names = self['data'], self['column_names']

        if not data:
            print("No data found in the file.")
            return

        shapes = [dataset.shape for dataset in data]
        if len(set(shapes)) != 1:
            print("Datasets have different shapes.")
            return

        data = data[0]  # Assuming all datasets have the same shape, take the first one
        x = data[:, 0]
        y = data[:, 1]
        z_columns = data[:, 2:]

        xu = np.unique(x)
        yu = np.unique(y)

        if len(xu) * len(yu) != len(x):
            print("The data does not form a proper grid.")
            return

        X, Y = np.meshgrid(xu, yu)

        for i, z_column in enumerate(z_columns.T):
            Z = z_column.reshape(len(yu), len(xu))
            plt.figure()
            cp = plt.contourf(X, Y, Z)
            plt.colorbar(cp)
            plt.title(f'Plot for column {i + 3}' + (f' ({column_names[i + 2]})' if column_names else ''))
            plt.xlabel('X')
            plt.ylabel('Y')
            plt.show()


    def _write(self):
        """ Writes to self.filename"""
        # --- Example:
        #with open(self.filename,'w') as f:
        #    f.write(self.toString)
        raise NotImplementedError()


    # --------------------------------------------------------------------------------
    # --- Convenient properties 
    # --------------------------------------------------------------------------------
    @property
    def common_shape(self):
        same_columns, same_rows, n_cols, n_rows = check_same_shape(self['data'])
        if same_columns and same_rows:
            return n_rows, n_cols
        else:
            return None

    @property
    def is_meshgrid(self):
        b1 = self.common_shape
        b2 = check_first_column_same(self['data'])
        b3 = check_second_column_unique(self['data'])
        return b1 is not None and b2 is not None and b3 is not None

    @property
    def x_values(self):
        if len(self['data'])==1:
            x= self['data'][:,0]
        else:
            x = check_first_column_same(self['data'])
            if x is None:
                # TODO, potential concat but this will make the check above unclear
                pass
        return x

    @property
    def y_values(self):
        if len(self['data'])==1:
            y= self['data'][:,1]
        else:
            y = check_second_column_unique(self['data'])
            if y is None:
                # TODO, potential concat but this will make the check above unclear
                pass
        return y

    def toDataFrame(self):
        """ Returns object into one DataFrame, or a dictionary of DataFrames"""
        data = self['data']
        shape = self.common_shape
        x = self.x_values
        y = self.y_values
        colNames=self['column_names']
        if self['column_names'] is None:
            colNames = default_colnames(self['data'][0].shape[1])

        # --- Only one data set
        if len(data)==1:
            M = self['data'][0]
            return pd.DataFrame(data=M, columns=colNames)

        # --- Mesh grid dataset
        if self.is_meshgrid:
            # We concatenate..
            M = np.vstack(self['data'])
            return pd.DataFrame(data=M, columns=colNames)

        # --- A bunch a different lines 
        dfs={}
        same_columns, same_rows, n_cols, n_rows = check_same_shape(self['data'])
        for i in range(len(self['data'])):
            if same_columns:
                cols = colNames 
            else:
                colNames = default_colnames(self['data'][i].shape[1])
            dfs['set'+str(i)] = pd.DataFrame(data=self['data'][i], columns=cols)
        return dfs
    
    def to2DFields(self, **kwargs):
        import xarray as xr
        is_meshgrid = self.is_meshgrid
        shape = self.common_shape
        x = self.x_values
        y = self.y_values
        colNames=self['column_names']
        if self['column_names'] is None:
            colNames = default_colnames(self['data'][0].shape[1])

        if not self.is_meshgrid:
            return None
         

        if len(kwargs.keys())>0:
            print('[WARN] GNUPlotFile: to2DFields: ignored keys: ',kwargs.keys())

        ds = xr.Dataset()
        ds = xr.Dataset(coords={colNames[0]: x, colNames[1]: y})
        data = np.array(self['data'])
        #X, Y = np.meshgrid(x,y)
        for i,c in enumerate(colNames[2:]):
            ds[c] = ((colNames[0],colNames[1]), np.squeeze(data[:,:,i+2]).T)
        return ds

    # --- Optional functions
    def __repr__(self):
        """ String that is written to screen when the user calls `print()` on the object. 
        Provide short and relevant information to save time for the user. 
        """
        def axisvec_to_string(v, s=''):
            if v is None:
                return 'None'
            else:
                deltas = np.diff(v)
                if len(v)==0:
                    return '[], n:0'
                elif len(v)==1:
                    return '[{}], n:1'.format(v[0])
                elif len(v)==2:
                    return '[{}, {}], n:2'.format(v[0], v[1])
                else: # len(np.unique(deltas))==1:
                    # TODO improve me
                    return '[{} ... {}],  d{}:{}, n:{}'.format(v[0], v[-1], s, v[1]-v[0], len(v))
                #else:
                #    return '[{} {} ... {}],  d{}:{}, n:{}'.format(v[0], v[1], v[-1], s, v[-1]-v[-2], len(v))

        s='<{} object>:\n'.format(type(self).__name__)
        s+='|Main attributes:\n'
        s+='| - filename: {}\n'.format(self.filename)

        common_shape = self.common_shape
        s+='| * common_shape: {}\n'.format(common_shape)
        s+='| * is_meshgrid: {}\n'.format(self.is_meshgrid)
        s+='| * x_values: {}\n'.format(axisvec_to_string(self.x_values, 'x'))
        s+='| * y_values: {}\n'.format(axisvec_to_string(self.y_values, 'y'))
        s+='|Main keys:\n'
        if common_shape:
            s+='| - data : length {}, shape {}\n'.format(len(self['data']), common_shape)
        else:
            s+='| - data : length {}, shapes {}\n'.format(len(self['data']), [x.shape for x in self['data']])
        s+='| - headers : {}\n'.format(self['headers'])
        s+='| - column_names : {}\n'.format(self['column_names'])
        s+='|Main methods:\n'
        s+='| - read, write, toDataFrame, to2DFields, keys'
        return s
    
    def toString(self):
        """ """
        s=''
        return s

# --------------------------------------------------------------------------------}
# --- Some hlper functions 
# --------------------------------------------------------------------------------{
def check_same_shape(arrays):
    if not arrays:
        return False, False
    num_columns = arrays[0].shape[1]
    num_rows = arrays[0].shape[0]
    same_columns = all(array.shape[1] == num_columns for array in arrays)
    same_rows = all(array.shape[0] == num_rows for array in arrays)
    return same_columns, same_rows, num_columns, num_rows

def check_first_column_same(arrays):
    if not arrays:
        return None
    first_column = arrays[0][:, 0]
    for array in arrays[1:]:
        if not np.array_equal(array[:, 0], first_column):
            return None
    return first_column

def check_second_column_unique(arrays):
    if not arrays:
        return None
    unique_values = []
    for array in arrays:
        second_column = array[:, 1]
        unique_value = np.unique(second_column)
        if len(unique_value) != 1:
            return None
        unique_values.append(unique_value[0])
    return np.array(unique_values)

def find_string_with_n_splits(strings, n):
    for string in strings:
        splits = string.split()
        if len(splits) == n:
            return splits
    return None

def default_colnames(n):
    colNames=['C{}'.format(i) for i in range(n)]
    colNames[0] = 'x'
    colNames[1] = 'y'
    return colNames

if __name__ == '__main__':
    from welib.essentials import *
    plt = GNUPlotFile('diff.000000.dat')
    print(plt)
    df =plt.toDataFrame()
    print(df)
    ds = plt.to2DFields()
    print(ds)
