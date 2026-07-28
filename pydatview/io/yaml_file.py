"""
Input/output class for YAML files, with special logic for wind turbine and polar data.
"""
import numpy as np
import pandas as pd
import os
import yaml

try:
    from .file import File, WrongFormatError, BrokenFormatError, EmptyFileError
except:
    File = dict
    EmptyFileError    = type('EmptyFileError', (Exception,),{})
    WrongFormatError  = type('WrongFormatError', (Exception,),{})
    BrokenFormatError = type('BrokenFormatError', (Exception,),{})

class YAMLFile(File):
    """
    Read/write a YAML file. The object behaves as a dictionary.

    Main methods
    ------------
    - read, write, toDataFrame, keys

    Examples
    --------
        f = YAMLFile('file.yaml')
        print(f.keys())
        dfs = f.toDataFrame()
        print(dfs)
    """

    @staticmethod
    def defaultExtensions():
        return ['.yaml', '.yml']

    @staticmethod
    def formatName():
        return 'YAML file'

    @staticmethod
    def priority(): return 60

    def __init__(self, filename=None, **kwargs):
        self.filename = filename
        if filename:
            self.read(**kwargs)

    def read(self, filename=None, **kwargs):
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2, 'File not found:', self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:', self.filename)
        
        with open(self.filename, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        self.clear()
        self.update(data) # We are a dictionary-like object

    def write(self, filename=None):
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        
        with open(self.filename, 'w', encoding='utf-8') as f:
            yaml.dump(dict(self), f, default_flow_style=False)



    def toDataFrame(self):
        """
        Loops through all keys in the YAML file, detects 1D and 2D arrays,
        and combines all 1D arrays with the same length into a DataFrame.
        Column names are made unique using the minimal chain of keys necessary.
        The DataFrame key is based on the common parent of the arrays being combined.
        Returns a dictionary of DataFrames.
        """
        import collections

        def is_1d_array(val):
            return isinstance(val, (list, np.ndarray)) and all(isinstance(x, (int, float)) for x in val)

        def is_2d_array(val):
            return (
                isinstance(val, (list, np.ndarray))
                and len(val) > 0
                and isinstance(val[0], (list, np.ndarray))
                and all(isinstance(row, (list, np.ndarray)) for row in val)
            )

        # Recursively walk the dict, collecting arrays and their key chains
        arrays_1d = []
        arrays_2d = []

        def walk(d, chain=None):
            if chain is None:
                chain = []
            if isinstance(d, dict):
                for k, v in d.items():
                    walk(v, chain + [k])
            elif is_1d_array(d):
                arrays_1d.append((tuple(chain), d))
            elif is_2d_array(d):
                arrays_2d.append((tuple(chain), d))

        walk(self)

        # Group 1D arrays by their length
        length_map = collections.defaultdict(list)
        for chain, arr in arrays_1d:
            length_map[len(arr)].append((chain, arr))

        dfs = {}
        parent_counter = collections.defaultdict(int)
        for arrlen, arrlist in length_map.items():
            if arrlen == 0 or len(arrlist) < 2:
                continue  # skip empty or single columns

            # Find minimal unique suffix for each chain (for column names)
            all_chains = [chain for chain, arr in arrlist]
            min_suffixes = {}
            for i, chain in enumerate(all_chains):
                for n in range(1, len(chain)+1):
                    suffix = chain[-n:]
                    if sum([other[-n:] == suffix for other in all_chains]) == 1:
                        min_suffixes[chain] = suffix
                        break
                else:
                    min_suffixes[chain] = chain  # fallback

            # Find common parent for all chains
            def common_prefix(chains):
                if not chains:
                    return ()
                min_len = min(len(c) for c in chains)
                prefix = []
                for i in range(min_len):
                    vals = set(c[i] for c in chains)
                    if len(vals) == 1:
                        prefix.append(chains[0][i])
                    else:
                        break
                return tuple(prefix)
            parent = common_prefix(all_chains)
            parent_str = "_".join(str(k) for k in parent) if parent else "root"
            parent_counter[parent_str] += 1
            key = parent_str
            if parent_counter[parent_str] > 1:
                key = f"{parent_str}_{parent_counter[parent_str]}"

            # Build DataFrame dict
            df_dict = {}
            for chain, arr in arrlist:
                colname = "_".join(str(k) for k in min_suffixes[chain])
                df_dict[colname] = arr
            if df_dict:
                # --- Special logic for "_grid" columns ---
                grid_cols = [c for c in df_dict if c.endswith("_grid")]
                if grid_cols and len(grid_cols) > 1:
                    # Check if all grid columns have the same content
                    first_grid = df_dict[grid_cols[0]]
                    if all(np.array_equal(df_dict[c], first_grid) for c in grid_cols[1:]):
                        # Remove all grid columns
                        for c in grid_cols:
                            df_dict.pop(c)
                        # Insert 'grid' as first column
                        df_dict = {'grid': first_grid, **df_dict}
                # --- Remove "_values" suffix from columns ---
                new_df_dict = {}
                for c in df_dict:
                    if c.endswith("_values"):
                        new_c = c[:-7]
                    else:
                        new_c = c
                    new_df_dict[new_c] = df_dict[c]
                df_dict = new_df_dict
                dfs[key] = pd.DataFrame(df_dict)

        # Add 2D arrays as their own DataFrames
        for chain, arr in arrays_2d:
            ncols = len(arr[0])
            colnames = []
            for i in range(ncols):
                colname = "_".join(str(k) for k in chain + (f"col{i+1}",))
                colnames.append(colname)
            df = pd.DataFrame(arr, columns=colnames)
            key = "_".join(str(k) for k in chain) + "_2d"
            dfs[key] = df

        if not dfs:
            return None
        return dfs

    def __repr__(self):
        s = '<{} object>:\n'.format(type(self).__name__)
        s += '|Main attributes:\n'
        s += '| - filename: {}\n'.format(self.filename)
        s += '|Main keys:\n'
        for k in self.keys():
            s += '| - {}\n'.format(k)
        s += '|Main methods:\n'
        s += '| - read, write, toDataFrame, keys'
        return s

    def toString(self):
        return yaml.dump(dict(self), default_flow_style=False)