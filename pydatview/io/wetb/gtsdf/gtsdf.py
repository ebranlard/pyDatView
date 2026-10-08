import os
import numpy as np
import numpy.ma as ma
import xarray as xr
import glob
import warnings

# import tqdm
import inspect

from pydatview.io.wetb.gtsdf.unix_time import from_unix
try:
    import h5py
except ImportError as e:
    print('[FAIL] h5py package not available. HAWC2 HDF5 format will fail. Do `pip install h5py` to use it.')
    raise e
    h5py = None

block_name_fmt = "block%04d"

# from wetb.wetb.utils.postprocs import statistics
def statistics(time, data, info,
               statistics=['min', 'mean', 'max', 'std']) -> xr.DataArray:
    """
    Calculate statistics from different sensors.

    Parameters
    ----------
    time : array (Ntimesteps)
        Array containing the simulation time from start to end of writting output
    data : array (Ntimesteps x Nsensors)
        Array containing the time series of all sensors
    info : dict
        Dictionary that must contain the following entries:\n
            attribute_names: list of sensor names\n
            attribute_units: list of sensor units\n
            attribute_descriptions: list of sensor descriptions
    statistics : list (Nstatistics), optional
        List containing the different types of statistics to calculate for each sensor.
        The default is ['min', 'mean', 'max', 'std'].

    Returns
    -------
    xarray.DataArray (Nsensors x Nstatistics)
        DataArray containing statistics for all sensors.\n
        Dims: sensor_name, statistic\n
        Coords: sensor_name, statistic, sensor_unit, sensor_description

    """
    def get_stat(stat):
        if hasattr(np, stat):
            return getattr(np, stat)(data, 0)
    data = np.array([get_stat(stat) for stat in statistics]).T
    dims = ['sensor_name', 'statistic']
    coords = {'statistic': statistics,
              'sensor_name': info['attribute_names'],
              'sensor_unit': ('sensor_name', info['attribute_units']),
              'sensor_description': ('sensor_name', info['attribute_descriptions'])}
    return xr.DataArray(data=data, dims=dims, coords=coords)



def load(filename, dtype=None):
    """Load a 'General Time Series Data Format'-hdf5 datafile

    Parameters
    ----------
    filename : str or h5py.File
        filename or open file object

    dtype: data type, optional
        type of returned data array, e.g. float16, float32 or float64.
        If None(default) the type of the returned data depends on the type of the file data

    Returns
    -------
    time : ndarray(dtype=float64), shape (no_observations,)
        time
    data : ndarray(dtype=dtype), shape (no_observations, no_attributes)
        data
    info : dict
        info containing:
            - type: "General Time Series Data Format"
            - name: name of dataset or filename if not present in file
            - no_attributes: Number of attributes
            - no_blocks: Number of datablocks
            - [description]: description of dataset or "" if not present in file
            - [attribute_names]: list of attribute names
            - [attribute_units]: list of attribute units
            - [attribute_descriptions]: list of attribute descriptions

    See Also
    --------
    gtsdf, save


    Examples
    --------
    >>> import gtsdf
    >>> data = np.arange(6).reshape(3,2)
    >>> gtsdf.save('test.hdf5', data)
    >>> time, data, info = gtsdf.load('test.hdf5')
    >>> print time
    [ 0.  1.  2.]
    >>> print data
    [[ 0.  1.]
     [ 2.  3.]
     [ 4.  5.]]
    >>> print info
    {'no_blocks': 1, 'type': 'General time series data format', 'name': 'test', 'no_attributes': 2, 'description': ''}
    >>> gtsdf.save('test.hdf5', data, name='MyDataset',
                                      description='MyDatasetDescription',
                                      attribute_names=['Att1', 'Att2'],
                                      attribute_units=['m', "m/s"],
                                      attribute_descriptions=['Att1Desc', 'Att2Desc'],
                                      time = np.array([0,1,4]),
                                      time_start = 10,
                                      time_step=2,
                                      dtype=np.float64)
    >>> time, data, info = gtsdf.load('test.hdf5')
    >>> print time
    [ 10.  12.  18.]
    >>> print data
    [[ 0.  1.]
     [ 2.  3.]
     [ 4.  5.]]
    >>> print info
    {'attribute_names': array(['Att1', 'Att2'], dtype='|S4'),
     'attribute_units': array(['m', 'm/s'], dtype='|S3'),
     'attribute_descriptions': array(['Att1Desc', 'Att2Desc'], dtype='|S8'),
     'name': 'MyDataset',
     'no_attributes': 2,
     'no_blocks': 1,
     'type': 'General time series data format',
     'description': 'MyDatasetDescription'}
    """
    f = _open_h5py_file(filename)
    try:
        info = _load_info(f)
        time, data = _load_timedata(f, dtype)
        return time, data, info
    finally:
        try:
            f.close()
        except BaseException:
            pass


def _open_h5py_file(filename):
    if isinstance(filename, h5py.File):
        f = filename
        filename = f.filename
    else:
        assert os.path.isfile(filename), "File, %s, does not exists" % filename
        f = h5py.File(filename, 'r')
    return f


def decode(v):
    if isinstance(v, bytes):
        return v.decode('latin1')
    elif hasattr(v, 'len'):
        return [decode(v_) for v_ in v]
    return v


def _load_info(f):

    info = {k: decode(v) for k, v in f.attrs.items()}
    check_type(f)
    if 'name' not in info:
        info['name'] = os.path.splitext(os.path.basename(f.filename))[0]
    if 'attribute_names' in f:
        info['attribute_names'] = [v.decode('latin1') for v in f['attribute_names']]
    if 'attribute_units' in f:
        info['attribute_units'] = [v.decode('latin1') for v in f['attribute_units']]
    if 'attribute_descriptions' in f:
        info['attribute_descriptions'] = [v.decode('latin1') for v in f['attribute_descriptions']]
    try:
        info['dtype'] = f[block_name_fmt % 0]['data'].dtype
    except BaseException:
        pass
    return info


def _load_timedata(f, dtype):
    no_blocks = f.attrs['no_blocks']
    if (block_name_fmt % 0) not in f:
        raise ValueError("HDF5 file must contain a group named '%s'" % (block_name_fmt % 0))
    block0 = f[block_name_fmt % 0]
    if 'data' not in block0:
        raise ValueError("group %s must contain a dataset called 'data'" % (block_name_fmt % 0))
    _, no_attributes = block0['data'].shape

    if dtype is None:
        file_dtype = f[block_name_fmt % 0]['data'].dtype
        if "float" in str(file_dtype):
            dtype = file_dtype
        elif file_dtype in [np.int8, np.uint8, np.int16, np.uint16]:
            dtype = np.float32
        else:
            dtype = np.float64
    time = []
    data = []
    for i in range(no_blocks):

        try:
            block = f[block_name_fmt % i]
        except Error:
            continue
        no_observations, no_attributes = block['data'].shape
        block_time = (block.get('time', np.arange(no_observations))[:]).astype(np.float64)
        if 'time_step' in block.attrs:
            block_time *= block.attrs['time_step']
        if 'time_start' in block.attrs:
            block_time += block.attrs['time_start']
        time.extend(block_time)

        block_data = block['data'][:].astype(dtype)
        if "int" in str(block['data'].dtype):
            block_data[block_data == np.iinfo(block['data'].dtype).max] = np.nan

        if 'gains' in block:
            block_data *= block['gains'][:]
        if 'offsets' in block:
            block_data += block['offsets'][:]
        data.append(block_data)

    if no_blocks > 0:
        data = np.vstack(data)
    return np.array(time).astype(np.float64), np.array(data).astype(dtype)


def save(filename, data, **kwargs):
    """Save a 'General Time Series Data Format'-hdf5 datafile

    Additional datablocks can be appended later using gtsdf.append_block

    Parameters
    ----------
    filename : str
    data : array_like, shape (no_observations, no_attributes)
    name : str, optional
        Name of dataset
    description : str, optional
        Description of dataset
    attribute_names : array_like, shape (no_attributes,), optional
        Names of attributes
    attribute_units : array_like, shape (no_attributes,), optinoal
        Units of attributes
    attribute_descriptions : array_like, shape(no_attributes,), optional
        Descriptions of attributes
    time : array_like, shape (no_observations, ), optional
        Time, default is [0..no_observations-1]
    time_start : int or float, optional
        Time offset (e.g. start time in seconds since 1/1/1970), default is 0, see notes
    time_step : int or float, optional
        Time scale factor (e.g. 1/sample frequency), default is 1, see notes
    dtype : data-type, optional
        Data type of saved data array, default uint16.\n
        Recommended choices:

        - uint16: Data is compressed into 2 byte integers using a gain and offset factor for each attribute
        - float64: Data is stored with high precision using 8 byte floats

    Notes
    -----
    Time can be specified by either

    - time (one value for each observation). Required inhomogeneous time distributions
    - time_start and/or time_step (one or two values), Recommended for homogeneous time distributions
    - time and time_start and/or time_step (one value for each observation + one or two values)

    When reading the file, the returned time-array is calculated as time * time_step + time_start

    See Also
    --------
    gtsdf, append_block, load


    Examples
    --------
    >>> import gtsdf
    >>> data = np.arange(12).reshape(6,2)
    >>> gtsdf.save('test.hdf5', data)
    >>> gtsdf.save('test.hdf5', data, name='MyDataset',
                                      description='MyDatasetDescription',
                                      attribute_names=['Att1', 'Att2'],
                                      attribute_units=['m', "m/s"],
                                      attribute_descriptions=['Att1Desc', 'Att2Desc'],
                                      time = np.array([0,1,2,6,7,8]),
                                      time_start = 10,
                                      time_step=2,
                                      dtype=np.float64)
    """
    if not filename.lower().endswith('.hdf5'):
        filename += ".hdf5"
    # exist_ok does not exist in Python27
    if not os.path.exists(os.path.dirname(os.path.abspath(filename))):
        os.makedirs(os.path.dirname(os.path.abspath(filename)))  # , exist_ok=True)
    _save_info(filename, data.shape, **kwargs)
    append_block(filename, data, **kwargs)


def _save_info(filename, data_shape, **kwargs):

    f = h5py.File(filename, "w")
    try:
        f.attrs["type"] = "General time series data format"
        no_observations, no_attributes = data_shape

        if 'name' in kwargs:
            f.attrs['name'] = kwargs['name']
        if 'description' in kwargs:
            f.attrs['description'] = kwargs['description']
        f.attrs['no_attributes'] = no_attributes
        if 'attribute_names' in kwargs:
            if no_attributes:
                assert len(kwargs['attribute_names']) == no_attributes, "len(attribute_names)=%d but data shape is %s" % (
                    len(kwargs['attribute_names']), data_shape)
            f.create_dataset("attribute_names", data=np.array([v.encode('utf-8') for v in kwargs['attribute_names']]))
        if 'attribute_units' in kwargs:
            if no_attributes:
                assert(len(kwargs['attribute_units']) == no_attributes)
            f.create_dataset("attribute_units", data=np.array([v.encode('utf-8') for v in kwargs['attribute_units']]))
        if 'attribute_descriptions' in kwargs:
            if no_attributes:
                assert(len(kwargs['attribute_descriptions']) == no_attributes)
            f.create_dataset("attribute_descriptions", data=np.array(
                [v.encode('utf-8') for v in kwargs['attribute_descriptions']]))
        f.attrs['no_blocks'] = 0
    except Exception:
        raise
    finally:
        f.close()


def append_block(filename, data, **kwargs):
    """Append a data block and corresponding time data to already existing file

    Parameters
    ----------
    filename : str
    data : array_like, shape (no_observations, no_attributes)
    time : array_like, shape (no_observations, ), optional
        Time, default is [0..no_observations-1]
    time_start : int or float, optional
        Time offset (e.g. start time in seconds since 1/1/1970), default is 0, see notes
    time_step : int or float, optional
        Time scale factor (e.g. 1/sample frequency), default is 1, see notes
    dtype : data-type, optional
        Data type of saved data array, default uint16.\n
        Recommended choices:

        - uint16: Data is compressed into 2 byte integers using a gain and offset factor for each attribute
        - float64: Data is stored with high precision using 8 byte floats

    Notes
    -----
    Time can be specified by either

    - time (one value for each observation). Required inhomogeneous time distributions
    - time_start and/or time_step (one or two values), Recommended for homogeneous time distributions
    - time and time_start and/or time_step (one value for each observation + one or two values)

    When reading the file, the returned time-array is calculated as time * time_step + time_start

    See Also
    --------
    gtsdf, save


    Examples
    --------
    >>> import gtsdf
    >>> data = np.arange(12).reshape(6,2)
    >>> gtsdf.save('test.hdf5', data)
    >>> gtsdf.append_block('test.hdf5', data+6)
    >>> time, data, info = gtsdf.load('test.hdf5')
    >>> print time
    [ 0.  1.  2.  3.  4.  5.]
    >>> print data
    [[  0.   1.]
     [  2.   3.]
     [  4.   5.]
     [  6.   7.]
     [  8.   9.]
     [ 10.  11.]]
    >>> print info
    {'no_blocks': 2, 'type': 'General time series data format', 'name': 'test', 'no_attributes': 2}
    """

    try:
        f = h5py.File(filename, "a")
        check_type(f)
        no_observations, no_attributes = data.shape
        assert(no_attributes == f.attrs['no_attributes'])
        blocknr = f.attrs['no_blocks']
        if blocknr == 0:
            dtype = kwargs.get('dtype', np.uint16)
        else:
            dtype = f[block_name_fmt % 0]['data'].dtype
            if dtype == np.uint16:
                if no_observations < 12:  # size with float32<1.2*size with uint16
                    dtype = np.float32

        block = f.create_group(block_name_fmt % blocknr)
        if 'time' in kwargs:
            assert(len(kwargs['time']) == no_observations)
            block.create_dataset('time', data=kwargs['time'])
        if 'time_step' in kwargs:
            time_step = kwargs['time_step']
            block.attrs['time_step'] = np.float64(time_step)
        if 'time_start' in kwargs:
            block.attrs['time_start'] = np.float64(kwargs['time_start'])

        pct_res = np.array([1])
        if "int" in str(dtype):
            if np.any(np.isinf(data)):
                f.close()
                raise ValueError(
                    "Int compression does not support 'inf'\nConsider removing outliers or use float datatype")
            nan = np.isnan(data)
            non_nan_data = ma.masked_array(data, nan)
            offsets = np.min(non_nan_data, 0)
            try:
                data = np.copy(data).astype(np.float64)
            except MemoryError:
                data = np.copy(data)
            data -= offsets
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # ignore warning caused by abs(nan) and np.nanmax(nan)
                pct_res = (np.percentile(data[~np.isnan(data)], 75, 0) - np.percentile(data[~np.isnan(data)],
                                                                                       25, 0)) / np.nanmax(np.abs(data), 0)  # percent of resolution for middle half of data
            gains = np.max(non_nan_data - offsets, 0).astype(np.float64) / \
                (np.iinfo(dtype).max - 1)  # -1 to save value for NaN
            not0 = np.where(gains != 0)
            data[:, not0] /= gains[not0]

            data = data.astype(dtype)
            data[nan] = np.iinfo(dtype).max

            block.create_dataset('gains', data=gains)
            block.create_dataset('offsets', data=offsets)

        block.create_dataset("data", data=data.astype(dtype))
        f.attrs['no_blocks'] = blocknr + 1
        f.close()

        if "int" in str(dtype):
            int_res = (np.iinfo(dtype).max - np.iinfo(dtype).min)
            with np.errstate(invalid='ignore'):
                if min(pct_res[pct_res > 0]) * int_res < 256:
                    raise Warning("Less than 256 values are used to represent 50%% of the values in column(s): %s\nConsider removing outliers or use float datatype" % np.where(
                        pct_res[pct_res > 0] * int_res < 256)[0])

    except Exception:
        try:
            f.close()
        except BaseException:
            pass
        raise


def load_pandas(filename, dtype=None):
    import pandas as pd
    time, data, info = load(filename, dtype)
    df = pd.DataFrame()
    df["Time"] = time
    df["Date"] = [from_unix(t) for t in time]
    for n, d in zip(info['attribute_names'], data.T):
        df[n] = d
    return df


def check_type(f):
    if 'type' not in f.attrs or \
            (f.attrs['type'].lower() != "general time series data format" and f.attrs['type'].lower() != b"general time series data format"):
        raise ValueError("HDF5 file must contain a 'type'-attribute with the value 'General time series data format'")
    if 'no_blocks' not in f.attrs:
        raise ValueError("HDF5 file must contain an attribute named 'no_blocks'")

    
def get_postproc(postproc_function, file_h5py, file, time_data_info=None, **kwargs) -> xr.DataArray:
    """
    Call a given postproc function with its postproc-specific and file-specific parameters, and return a DataArray from its output if any.

    Parameters
    ----------
    postproc_function : function
        Function that executes a given postproc
    file_h5py : h5py.File object
        h5py.File object in append mode from hdf5 file
    file : str
        Absolute path to hdf5 file
    time_data_info : tuple, optional
        Tuple containing the arrays time, data and the dictionary info. If passed, it is not necessary
        to load them from the hdf5 file. The default is None.
    **kwargs : dict, optional
        Dictionary containing the postproc-specific parameters that postproc_function takes.

    Returns
    -------
    postproc_output : xarray.DataArray
        DataArray from postproc_function output if any, otherwise None. Its name will be
        the same as the postproc_function

    """
    print(f"Calculating {postproc_function.__name__} for '{file}'")
    if time_data_info is None:
        time_data_info = load(file)
    time, data, info = time_data_info
    postproc_function_args = inspect.signature(postproc_function).parameters.keys()
    file_args = {}
    for item in ['file_h5py', 'file', 'time', 'data', 'info']:
        if item in postproc_function_args:
            file_args[item] = locals()[item]
    postproc_output = postproc_function(**file_args, **kwargs)
    if postproc_output is None:
        return
    if isinstance(postproc_output, np.ndarray) or isinstance(postproc_output, list):
        postproc_output = xr.DataArray(postproc_output)
    postproc_output.name = postproc_function.__name__
    return postproc_output


def write_postproc(file, postproc_output) -> None:
    """
    Write a postproc DataArray to hdf5 file.\n
    A block called the same as the DataArray is created under the block 'postproc'.
    A dataset called 'data' is created under the previous block for the DataArray data
    with its dims in the attribute "dims", and also a dataset for each DataArray coordinate
    with its dimension in the attribute "dim".

    Parameters
    ----------
    file : h5py.File object
        h5py.File object in append mode from hdf5 file
    postproc_output : xarray.DataArray
        DataArray whose name, data, dims and coords are written into hdf5 file.

    Returns
    -------
    None

    """
    if postproc_output is None:
        return
    print(f"Writing {postproc_output.name} to '{file.filename}'")
    if 'postproc' not in file:
        file.create_group('postproc')
    if postproc_output.name in file['postproc']:
        del file['postproc'][postproc_output.name]
    file['postproc'].create_group(postproc_output.name)
    file['postproc'][postproc_output.name].create_dataset(name='data', data=postproc_output.astype(float))
    file['postproc'][postproc_output.name]['data'].attrs['dims'] = [d.encode('utf-8') for d in postproc_output.dims]
    for coord in postproc_output.coords:
        if np.issubdtype(postproc_output.coords[coord].dtype, np.str_):
            file['postproc'][postproc_output.name].create_dataset(name=coord, data=np.array([v.encode('utf-8') for v in postproc_output.coords[coord].values]))
        else:
            file['postproc'][postproc_output.name].create_dataset(name=coord, data=postproc_output.coords[coord].astype(float))
        file['postproc'][postproc_output.name][coord].attrs['dim'] = postproc_output.coords[coord].dims[0].encode('utf-8')


def add_postproc(file, config={statistics: {'statistics': ['min', 'mean', 'max', 'std']}}) -> list:
    """
    Call get_postproc and write_postproc for each postproc in config.

    Parameters
    ----------
    file : str
        Absolute path to hdf5 file
    config : dict, optional
        Dictionary containing postprocs. Its keys are functions and its values are dicts for their postproc-specific parameters.\n
        Example:\n
        {statistics: {'statistics': ['min', 'mean', 'max', 'std']},\n
        extreme_loads: {'sensors_info': [('Tower base shear force', 0, 1), ('Blade 1 '.' bending moment', 9, 10)]}}\n
        The default is {statistics: {'statistics': ['min', 'mean', 'max', 'std']}}.

    Returns
    -------
    postproc_output_list : list of DataArrays
        List of DataArrays output by each postproc function

    """
    time_data_info = load(file)
    f = h5py.File(file, "a")
    postproc_output_list = []
    for postproc, kwargs in config.items():
        postproc_output = get_postproc(postproc_function=postproc, file_h5py=f, file=file, time_data_info=time_data_info, **kwargs)
        write_postproc(file=f, postproc_output=postproc_output)
        if postproc_output is not None:
            postproc_output_list.append(postproc_output)
    f.close()
    return postproc_output_list
    

def load_postproc(filename, 
                  config={statistics: {'statistics': ['min', 'mean', 'max', 'std']}},
                  force_recompute=False) -> list:
    """
    Read data from hdf5 file for each postproc in config and return a list of DataArrays. If any postproc in config is missing in the hdf5 file
    it will compute it and write it as well. This can be also be done to rewrite postprocs in config that already are in the hdf5 file
    by passing force_recompute=True.

    Parameters
    ----------
    filename : str
        Absolute path to hdf5 file
    config : dict, optional
        Dictionary containing postprocs. Its keys are functions and its values are dicts for their postproc-specific parameters.\n
        Example:\n
        {statistics: {'statistics': ['min', 'mean', 'max', 'std']},\n
        extreme_loads: {'sensors_info': [('Tower base shear force', 0, 1), ('Blade 1 '.' bending moment', 9, 10)]}}\n
        The default is {statistics: {'statistics': ['min', 'mean', 'max', 'std']}}.
    force_recompute : bool, optional
        Whether all postprocs in config should be calculated and written to hdf5 file (True) or only the ones that
        are missing (False). The default is False.

    Returns
    -------
    data_arrays: list of DataArrays
       List of DataArrays from each block under 'postproc' in hdf5 file that also is in config

    """
    if force_recompute:
        postproc_output_list = add_postproc(filename, config)
        return postproc_output_list
    f = _open_h5py_file(filename)
    if 'postproc' not in f:
        f.close()
        postproc_output_list = add_postproc(filename, config)
        return postproc_output_list
    # Check which postprocs in config are missing in the hdf5 file
    config_missing = {}
    for postproc, args in config.items():
        if postproc.__name__ not in f['postproc']:
            config_missing[postproc] = args
    # Add missing postprocs in config to hdf5 file, if there are any
    if config_missing != {}:
        f.close()
        add_postproc(filename, config_missing)
        f = _open_h5py_file(filename)
    # Return list of DataArrays for all postprocs in config
    data_arrays = []
    for postproc in config.keys():
        try:
            data_arrays.append(xr.DataArray(name=postproc.__name__,
                                            data=f['postproc'][postproc.__name__]['data'],
                                            dims=f['postproc'][postproc.__name__]['data'].attrs['dims'],
                                            coords={coord: ([v.decode('latin1') for v in f['postproc'][postproc.__name__][coord]]
                                                                if np.issubdtype(f['postproc'][postproc.__name__][coord].dtype, bytes)
                                                                else 
                                                            f['postproc'][postproc.__name__][coord])
                                                                    if coord in f['postproc'][postproc.__name__]['data'].attrs['dims']
                                                                    else 
                                                            ((f['postproc'][postproc.__name__][coord].attrs['dim'], [v.decode('latin1') for v in f['postproc'][postproc.__name__][coord]])
                                                                if np.issubdtype(f['postproc'][postproc.__name__][coord].dtype, bytes)
                                                                else 
                                                            (f['postproc'][postproc.__name__][coord].attrs['dim'], f['postproc'][postproc.__name__][coord]))
                                                                        for coord in f['postproc'][postproc.__name__] if coord != 'data'}))
        except:
            continue
    f.close()
    return data_arrays


def collect_postproc(folder, recursive=True,
                     config={statistics: {'statistics': ['min', 'mean', 'max', 'std']}},
                     force_recompute=False) -> list:
    """
    Call load_postproc for all hdf5 files in folder and collect into a single dataArray for each postproc in config.
    
    Parameters
    ----------
    folder : str
        Absolute path to folder containing hdf5 files
    recursive : bool, optional
        Whether to include hdf5 files in subfolders (True) or not (False). The default is True.
    config : dict, optional
        Dictionary containing postprocs. Its keys are functions and its values are dicts for their postproc-specific parameters.\n
        Example:\n
        {statistics: {'statistics': ['min', 'mean', 'max', 'std']},\n
        extreme_loads: {'sensors_info': [('Tower base shear force', 0, 1), ('Blade 1 '.' bending moment', 9, 10)]}}\n
        The default is {statistics: {'statistics': ['min', 'mean', 'max', 'std']}}.
    force_recompute : bool, optional
        Whether all postprocs in config should be calculated and written to hdf5 file (True) or only the ones that
        are missing (False). The default is False.

    Returns
    -------
    data_arrays: list of DataArrays
        List of DataArrays from each block under 'postproc' in hdf5 file that also is in config. Each DataArray has
        an extra dimension 'filename' since DataArrays from all files have been collected into a single one

    """
    if recursive:
        p = os.path.join('.', folder, '**', '*.hdf5')
    else:
        p = os.path.join('.', folder, '*.hdf5')
    fn_lst = sorted(glob.glob(p, recursive=recursive))
    if not fn_lst:
        raise Exception(f"No *.hdf5 files found in {os.path.abspath(os.path.join('.', folder))}")
    postproc_output_list_all_files = [load_postproc(fn, config=config, force_recompute=force_recompute) for fn in tqdm.tqdm(fn_lst)]
    data_arrays = []
    for i in range(len(postproc_output_list_all_files[0])):
        name = postproc_output_list_all_files[0][i].name
        data = np.array([f[i] for f in postproc_output_list_all_files])
        dims = ('filename',) + postproc_output_list_all_files[0][i].dims
        coords = postproc_output_list_all_files[0][i].coords
        data_arrays.append(xr.DataArray(name=name, data=data, dims=dims, coords=coords))
        data_arrays[-1].coords['filename'] = [os.path.relpath(fn, '.') for fn in fn_lst]
    return data_arrays                   
    

def compress2postproc(file, config={statistics: {'statistics': ['min', 'mean', 'max', 'std']}}) -> None:
    """
    Compress hdf5 file into only the postproc data, removing all time series.

    Parameters
    ----------
    file : str
        Absolute path to hdf5 file
    config : dict, optional
        Dictionary containing postprocs. Its keys are functions and its values are dicts for their postproc-specific parameters.\n
        Example:\n
        {statistics: {'statistics': ['min', 'mean', 'max', 'std']},\n
        extreme_loads: {'sensors_info': [('Tower base shear force', 0, 1), ('Blade 1 '.' bending moment', 9, 10)]}}\n
        The default is {statistics: {'statistics': ['min', 'mean', 'max', 'std']}}.

    Returns
    -------
    None

    """
    time_data_info = load(file)
    time, data, info = time_data_info
    _save_info(file, data.shape, **info)
    f = h5py.File(file, "a")
    for postproc, kwargs in config.items():
        postproc_output = get_postproc(postproc_function=postproc, file_h5py=f, file=file, time_data_info=time_data_info, **kwargs)
        write_postproc(file=f, postproc_output=postproc_output)
    f.close()
      
