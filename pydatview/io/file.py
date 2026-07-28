import os
from collections import OrderedDict

class WrongFormatError(Exception):
    pass

class EmptyFileError(Exception):
    pass

class BrokenFormatError(Exception):
    pass

class BrokenReaderError(Exception):
    pass

class OptionalImportError(Exception):
    pass

try: #Python3
    FileNotFoundError=FileNotFoundError
except NameError: # Python2
    FileNotFoundError = IOError

class File(OrderedDict):
    def __init__(self, filename=None, streaming=False, **kwargs):
        OrderedDict.__init__(self)
        self.filename = filename
        self.streaming = streaming      # If True, read headers only, keep file open
        self.data = None                # Data storage (varies by format)
        self._in_context = False        # True only if in 'with' block
        self._fid = None                # File handle when streaming
        if filename is not None and not streaming:
            # Only read immediately in normal mode; streaming mode waits for __enter__
            self.read(streaming=streaming, **kwargs)

    def __enter__(self):
        """Context manager entry."""
        self._in_context = True
        if self.filename:
            self.read(streaming=self.streaming)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit - close file handle if open."""
        if self._fid is not None:
            self._fid.close()
            self._fid = None
        self._in_context = False
        # Optional: free data on exit if not streaming (saves memory)
        if not self.streaming and self.data is not None:
            self.data = None
        return False  # Propagate exceptions

    def _enforce_context_if_needed(self):
        """Raise if streaming and not in context manager."""
        # Check if streaming attribute exists (some old file formats may not have it)
        if hasattr(self, 'streaming') and self.streaming and not self._in_context:
            raise RuntimeError(
                "streaming=True requires using a context manager ('with' statement) "
                "to ensure the file is closed. Use: `with File(...) as reader:`"
            )

    def read(self, filename=None, streaming=None, **kwargs):
        if filename is not None:
            self.filename = filename
        if streaming is not None:
            self.streaming = streaming
        # Initialize streaming attribute if it doesn't exist (for old file formats)
        if not hasattr(self, 'streaming'):
            self.streaming = False
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2, 'File not found:', self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:', self.filename)

        self._enforce_context_if_needed()

        # Calling children function
        # Check if child class _read() accepts streaming parameter
        import inspect
        sig = inspect.signature(self._read)
        if 'streaming' in sig.parameters:
            # New-style _read() with streaming support
            self._read(streaming=self.streaming, **kwargs)
        else:
            # Old-style _read() without streaming support
            self._read(**kwargs)
        return self

    def write(self, filename=None, **kwargs):
        if filename:
            self.filename = filename
        if not self.filename:
            raise Exception('No filename provided')
        # Calling children function
        self._write(**kwargs)

    def readAll(self):
        """Read remaining data after streaming header (to be implemented by children)."""
        if not self.streaming:
            raise RuntimeError("readAll() only valid in streaming mode")
        if not self._in_context:
            raise RuntimeError("readAll() requires context manager")
        self._readAll()

    def readChunk(self, **kwargs):
        """Read chunk of data (to be implemented by children)."""
        if not self.streaming:
            raise RuntimeError("readChunk() only valid in streaming mode")
        if not self._in_context:
            raise RuntimeError("readChunk() requires context manager")
        return self._readChunk(**kwargs)

    def toDataFrame(self):
        return self._toDataFrame()

    # --------------------------------------------------------------------------------
    # --- Properties
    # --------------------------------------------------------------------------------
    @property
    def size(self):
        return os.path.getsize(self.filename)

    @property
    def encoding(self):	
        import codecs
        import chardet 
        """  Detects encoding"""
        try:
            byts = min(32, self.size)
        except TypeError:
            return None
        with open(self.filename, 'rb') as f:
            raw = f.read(byts)
        if raw.startswith(codecs.BOM_UTF8):
            return 'utf-8-sig'
        else:
            result = chardet.detect(raw)
            return result['encoding']


    # --------------------------------------------------------------------------------}
    # --- Conversions
    # --------------------------------------------------------------------------------{
    def toCSV(self, filename=None, extension='.csv', **kwargs):
        """ By default, writes dataframes to CSV
        Keywords arguments are the same as pandas DataFrame to_csv:
          - sep: separator
          - index: write index or not
          - etc.
        """
        from .converters import writeFileDataFrames 
        from .converters import dataFrameToCSV
        writeFileDataFrames(self, dataFrameToCSV, filename=filename, extension=extension, **kwargs)

    def toOUTB(self, filename=None, extension='.outb', **kwargs):
        """ write to OUTB"""
        from .converters import writeFileDataFrames 
        from .converters import dataFrameToOUTB
        writeFileDataFrames(self, dataFrameToOUTB, filename=filename, extension=extension, **kwargs)


    def toParquet(self, filename=None, extension='.parquet', **kwargs):
        """ write to OUTB"""
        from .converters import writeFileDataFrames 
        from .converters import dataFrameToParquet
        writeFileDataFrames(self, dataFrameToParquet, filename=filename, extension=extension, **kwargs)

    
    # --------------------------------------------------------------------------------
    # --- Sub class methods
    # --------------------------------------------------------------------------------
    def _read(self, streaming=False, **kwargs):
        raise NotImplementedError("Method must be implemented in the subclass")

    def _write(self):
        raise NotImplementedError("Method must be implemented in the subclass")

    def _toDataFrame(self):
        raise NotImplementedError("Method must be implemented in the subclass")

    def _readAll(self):
        """Override in child classes for streaming support."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support readAll()")

    def _readChunk(self, **kwargs):
        """Override in child classes for streaming support."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support readChunk()")

    def _fromDataFrame(self):
        raise NotImplementedError("Method must be implemented in the subclass")

    def _fromDictionary(self):
        raise NotImplementedError("Method must be implemented in the subclass")

    def _fromFile(self):
        raise NotImplementedError("Method must be implemented in the subclass")

    # --------------------------------------------------------------------------------
    # --- Static methods
    # --------------------------------------------------------------------------------
    @staticmethod
    def defaultExtension():
        raise NotImplementedError("Method must be implemented in the subclass")

    @staticmethod
    def formatName():
        raise NotImplementedError("Method must be implemented in the subclass")

    def test_write_read(self,bDelete=False):
        """ Test that we can write and then read what we wrote
        NOTE: this does not check that what we read is the same..
        """
        # --- First, test write function (assuming read)
        try:
            f,ext=os.path.splitext(self.filename)
            filename_out = f+'_TMP'+ext
            self.write(filename_out)
        except Exception as e:
            raise Exception('Error writing what we read\n'+e.args[0])
        # --- Second,  re-read what we wrote
        try:
            self.read(filename_out)
        except Exception as e:
            raise Exception('Error reading what we wrote\n'+e.args[0])
        if bDelete:
            os.remove(filename_out)
        return filename_out

    def test_ascii(self,bCompareWritesOnly=False,bDelete=True):
        # compare ourselves (assuming read has occured) with what we write

        f,ext=os.path.splitext(self.filename)
        # --- Perform a simple write/read test
        filename_out=self.test_write_read()

        # --- Perform ascii comparison (and delete if success)
        if bCompareWritesOnly:
            f1 = filename_out
            f2 = f+'_TMP2'+ext
            self.write(f2)
        else:
            f1 = f+ext
            f2 = filename_out
        bStat=ascii_comp(f1,f2,bDelete=bDelete)

        if bStat:
            if bCompareWritesOnly and bDelete:
                os.remove(f1)
        else:
            raise Exception('The ascii content of {} and {} are different'.format(f1,f2))

# --------------------------------------------------------------------------------}
# --- Helper functions
# --------------------------------------------------------------------------------{
def isBinary(filename):
    with open(filename, 'r') as f:
        try:
            # first try to read as string
            l = f.readline()
            # then look for weird characters
            for c in l:
                code = ord(c)
                if code<10 or (code>14 and code<31):
                    return True
            return False
        except UnicodeDecodeError:
            return True


def numberOfLines(filename, method=1):

    if method==1:
        return sum(1 for i in open(filename, 'rb'))

    elif method==2:
        def blocks(files, size=65536):
            while True:
                b = files.read(size)
                if not b: break
                yield b
        with open(filename, "r",encoding="utf-8",errors='ignore') as f:
            return sum(bl.count("\n") for bl in blocks(f))
    else:
        raise NotImplementedError()

def ascii_comp(file1,file2,bDelete=False):
    """ Compares two ascii files line by line.
    Comparison is done ignoring multiple white spaces for now"""
    # --- Read original as ascii
    with open(file1, 'r') as f1:
        lines1 = f1.read().splitlines();
        lines1 = '|'.join([l.replace('\t',' ').strip() for l in lines1])
        lines1 = ' '.join(lines1.split())
    # --- Read second file as ascii
    with open(file2, 'r') as f2:
        lines2 = f2.read().splitlines();
        lines2 = '|'.join([l.replace('\t',' ').strip() for l in lines2])
        lines2 = ' '.join(lines2.split())

    if lines1 == lines2:
        if bDelete:
            os.remove(file2)
        return True
    else:
        return False
