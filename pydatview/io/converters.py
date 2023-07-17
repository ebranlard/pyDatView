import os


# --------------------------------------------------------------------------------
# --- Writing pandas DataFrame to different formats
# --------------------------------------------------------------------------------
# The

def writeFileDataFrames(fileObject, writer, extension='.conv', filename=None, **kwargs):
    """ 
    From a fileObejct, extract dataframes and write them to disk.

    - fileObject: object inheriting from weio.File with at least
                   - the attributes .filename
                   - the method     .toDataFrame()
    - writer: function with the interface:   writer ( dataframe, filename, **kwargs )
    """ 
    if filename is None:
        base, _ = os.path.splitext(fileObject.filename)
        filename = base + extension
    else:
        base, ext = os.path.splitext(filename)
        if len(ext)!=0:
            extension = ext
    if filename == fileObject.filename:
        raise Exception('Not overwritting {}. Specify a filename or an extension.'.format(filename))
        
    dfs = fileObject.toDataFrame()
    if isinstance(dfs, dict):
        for name,df in dfs.items():
            filename = base + name + extension
            if filename == fileObject.filename:
                raise Exception('Not overwritting {}. Specify a filename or an extension.'.format(filename))
            writeDataFrame(df=df, writer=writer, filename=filename, **kwargs)
    else:
        writeDataFrame(df=dfs, writer=writer, filename=filename, **kwargs)


def writeDataFrame(df, writer, filename, **kwargs):
    """ 
    Write a dataframe to disk based on a "writer" function. 
    - df: pandas dataframe
    - writer: function with the interface:   writer ( dataframe, filename, **kwargs )
    - filename: filename 
    """
    writer(df, filename, **kwargs)

# --- Low level writers
def dataFrameToCSV(df, filename, sep=',', index=False, **kwargs):
    base, ext = os.path.splitext(filename)
    if len(ext)==0:
        filename = base='.csv'
    df.to_csv(filename, sep=sep, index=index, **kwargs)

def dataFrameToOUTB(df, filename, **kwargs):
    from .fast_output_file import writeDataFrame as writeDataFrameToOUTB
    base, ext = os.path.splitext(filename)
    if len(ext)==0:
        filename = base='.outb'
    writeDataFrameToOUTB(df, filename, binary=True)

def dataFrameToParquet(df, filename, **kwargs):
    df.to_parquet(path=filename, **kwargs)

