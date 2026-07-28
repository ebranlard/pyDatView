""" 
Input/output class for the Plot3D file format (formatted, ASCII)
"""
import numpy as np
import pandas as pd
import os

try:
    from .file import File, WrongFormatError, BrokenFormatError, EmptyFileError
except:
    File = dict
    EmptyFileError    = type('EmptyFileError', (Exception,),{})
    WrongFormatError  = type('WrongFormatError', (Exception,),{})
    BrokenFormatError = type('BrokenFormatError', (Exception,),{})

class Plot3DFile(File):
    """ 
    Read/write a Plot3D file (formatted, ASCII). The object behaves as a dictionary.

    Main methods
    ------------
    - read, write, toDataFrame, keys

    Examples
    --------
        f = Plot3DFile('file.fmt')
        print(f.keys())
        print(f.toDataFrame().columns)  
    """

    @staticmethod
    def defaultExtensions():
        """ List of file extensions expected for this fileformat"""
        return ['.g', '.x', '.y', '.xy', '.xyz', '.fmt']

    @staticmethod
    def formatName():
        return 'Plot3D formatted ASCII file'

    @staticmethod
    def priority(): return 60 # Priority in weio.read fileformat list between 0=high and 100:low

    def __init__(self, filename=None, **kwargs):
        """ Class constructor. If a `filename` is given, the file is read. """
        self.filename = filename
        if filename:
            self.read(**kwargs)

    def read(self, filename=None, verbose=False, method='numpy'):
        """ Reads the file self.filename, or `filename` if provided """
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2, 'File not found:', self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:', self.filename)

        coords_list, dims = read_plot3d(self.filename, verbose=verbose, method=method, singleblock=False)
        self['coords'] = coords_list
        self['dims'] = dims

    def write(self, filename=None):
        """ Rewrite object to file, or write object to `filename` if provided """
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')

        write_plot3d(self.filename, self['coords'], self['dims'], singleblock=False)

    def toDataFrame(self):
        """ Returns one DataFrame (single block) or a dict of DataFrames (multi-block) """
        coords_list = self.get('coords', None)
        if coords_list is None:
            raise Exception("No coordinates loaded.")
        if len(coords_list) == 1:
            coords = coords_list[0]
            df = pd.DataFrame(coords, columns=['x', 'y', 'z'])
            return df
        else:
            dfs={}
            for i, coords in enumerate(coords_list):
                df = pd.DataFrame(coords, columns=['x', 'y', 'z'])
                dfs[f'block_{i}'] = df
            return dfs

    def __repr__(self):
        s = '<{} object>:\n'.format(type(self).__name__)
        s += '|Main attributes:\n'
        s += '| - filename: {}\n'.format(self.filename)
        if 'dims' in self:
            for i, dims in enumerate(self['dims']):
                s += '| - dims[{}]: shape {}\n'.format(i, dims)
        if 'coords' in self:
            for i, coords in enumerate(self['coords']):
                s += '| - coords[{}]: shape {}\n'.format(i, coords.shape)
        s += '|Main methods:\n'
        s += '| - read, write, toDataFrame, keys'
        return s

    def toString(self):
        """ """
        s = ''
        return s

    def plot(self, ax=None, **kwargs):
        """
        Plots the x, y coordinates as a scatter plot.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Existing matplotlib axes to plot on. If None, a new figure and axes are created.
        **kwargs : dict
            Additional keyword arguments passed to plt.scatter.
        """
        import matplotlib.pyplot as plt
        dfs = self.toDataFrame()
        if isinstance(dfs, dict):
            for key, df in dfs.items():
                if ax is None:
                    fig, ax = plt.subplots()
                ax.scatter(df['x'], df['y'], label=key, **kwargs)
            ax.legend()
        else:
            df = dfs
            if ax is None:
                fig, ax = plt.subplots()
            ax.scatter(df['x'], df['y'], **kwargs)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_title('Plot3D x-y Scatter')
        ax.axis('equal')
        ax.grid(True)
        return ax




# --------------------------------------------------------------------------------}
# --- Low level functions 
# --------------------------------------------------------------------------------{
def read_plot3d(filename, verbose=False, method='numpy', singleblock=False):
    """
    Reads a simple multi-block Plot3D file (formatted, ASCII).
    Returns:
        coords_list: list of (n_points, 3) arrays, one per block
        dims: (n_blocks, 3) list of (ni, nj, nk)
    """
    coords_list = []
    if method == 'numpy':
        dims = np.loadtxt(filename, skiprows=1, max_rows=1, dtype=int)
        coords = np.loadtxt(filename, skiprows=2)
        coords = coords.reshape((3, dims[0]*dims[1]*dims[2])).transpose()
        dims = [dims]
        coords_list = [coords]
    else:
        with open(filename, "r") as f:
            nblocks = int(f.readline())
            dims = []
            for _ in range(nblocks):
                dims.append(tuple(int(x) for x in f.readline().split()))
            for block in range(nblocks):
                ni, nj, nk = dims[block]
                npts = ni * nj * nk
                block_coords = np.zeros((npts, 3))
                for idim in range(3):
                    for k in range(nk):
                        for j in range(nj):
                            for i in range(ni):
                                idx = i + j * ni + k * ni * nj
                                val = float(f.readline())
                                block_coords[idx, idim] = val
                coords_list.append(block_coords)
    if singleblock and len(coords_list) == 1:
        return coords_list[0], dims[0]
    if verbose:
        for i, arr in enumerate(coords_list):
            print(f"Block {i}: shape {arr.shape}, dims {dims[i]}")
            x_min, x_max = arr[:, 0].min(), arr[:, 0].max()
            y_min, y_max = arr[:, 1].min(), arr[:, 1].max()
            z_min, z_max = arr[:, 2].min(), arr[:, 2].max()
            print(f"  x range: [{x_min:.6f}, {x_max:.6f}]")
            print(f"  y range: [{y_min:.6f}, {y_max:.6f}]")
            print(f"  z range: [{z_min:.6f}, {z_max:.6f}]")
    return coords_list, dims

def write_plot3d(filename, coords_list, dims, singleblock=False):
    """
    Writes a simple multi-block Plot3D file (formatted, ASCII).
    Args:
        filename: Output file name
        coords_list: list of (n_points, 3) arrays, one per block
        dims: (n_blocks, 3) list of (ni, nj, nk) or a single (ni, nj, nk)
        singleblock: If True, write as single block (no nblocks header)
    """
    if singleblock:
        coords_list = [coords_list]  # Ensure coords_list is a list with one block
        dims = [dims]  # Ensure dims is a list with one block
    # Ensure coords_list is a list
    if not isinstance(coords_list, list):
        coords_list = [coords_list]
    with open(filename, "w") as f:
        nblocks = len(coords_list)
        f.write(f"{nblocks}\n")

        if nblocks == 1:
            ni, nj, nk = dims if isinstance(dims, (list, tuple)) and len(dims) == 3 else dims[0]
            f.write(f"{ni} {nj} {nk}\n")
            coords = coords_list[0]
            for idim in range(3):
                for idx in range(coords.shape[0]):
                    f.write(f"{coords[idx, idim]}\n")
        else:
            for block, (coords, (ni, nj, nk)) in enumerate(zip(coords_list, dims)):
                f.write(f"{ni} {nj} {nk}\n")
                for idim in range(3):
                    for idx in range(coords.shape[0]):
                        f.write(f"{coords[idx, idim]}\n")
                    #for k in range(nk):
                    #    for j in range(nj):
                    #        for i in range(ni):
                    #            idx = i + j * ni + k * ni * nj
                    #            f.write(f"{coords[idx, idim]}\n")


if __name__ == '__main__':  
    import matplotlib.pyplot as plt
    p3d = Plot3DFile('C:/Work/cfd/nalulib/examples/airfoils/naca0012_blunt.fmt')
    print(p3d)
    p3d.plot()
    p3d.write('C:/Work/cfd/nalulib/examples/airfoils/_naca0012_blunt_out.fmt')
    plt.show()


