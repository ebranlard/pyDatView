import os
import re
import pandas as pd

try:
    from .file import File, WrongFormatError
except:
    File=dict
    WrongFormatError  = type('WrongFormatError', (Exception,),{})
    EmptyFileError    = type('EmptyFileError', (Exception,),{})

class CSVFile(File):
    """ 
    Read/write a CSV file. 

    Main methods
    ------------
      read, write, toDataFrame

    Examples
    --------

        # Read a csv file and convert it to a pandas dataframe
        f = CSVFile('test.csv')
        df = f.toDataFrame()

    """

    @staticmethod
    def defaultExtensions():
        return ['.csv','.txt']

    @staticmethod
    def formatName():
        return 'CSV file'

    def __init__(self, filename=None, sep=None, colNames=None, commentChar=None, commentLines=None,\
                       colNamesLine=None, detectColumnNames=True, header=None, doRead=True, streaming=False, **kwargs):
        # Initialize CSV-specific attributes
        colNames     = [] if colNames is None else colNames
        commentLines = [] if commentLines is None else commentLines
        self.sep          = sep
        self.skipRows     = []
        self.colNames     = colNames
        self.commentChar  = commentChar
        self.commentLines = commentLines
        self.colNamesLine = colNamesLine
        self.detectColumnNames = detectColumnNames
        if header is None:
            self.header=[]
        else:
            if not hasattr(header, '__len__'):
                self.header=[header]
            else:
                self.header=header
        self.nHeader=0
        if (len(self.commentLines)>0) and (self.commentChar is not None):
            raise Exception('Provide either `commentChar` or `commentLines` for CSV file types')
        if (len(self.colNames)>0) and (self.colNamesLine is not None):
            raise Exception('Provide either `colNames` or `colNamesLine` for CSV file types')

        # Call parent __init__ - handles streaming, filename, etc.
        File.__init__(self, filename=None, streaming=streaming)

        # Handle filename after parent init
        if filename:
            if streaming:
                # Don't read immediately in streaming mode - wait for context manager
                self.filename = filename
            else:
                self.read(filename, doRead=doRead, **kwargs)

    def __enter__(self):
        """Context manager entry - CSV needs special handling for detect()."""
        self._in_context = True
        if self.filename:
            # In streaming mode: detect headers, open file but don't read data
            # In normal mode: read everything
            if self.streaming:
                self.read(doRead=False)  # Run detect() only
                self._read()  # Open file handle and skip to data
            else:
                self.read(doRead=True)
        return self

    # Inherit __exit__ and _enforce_context_if_needed from parent File class

    def read(self, filename=None, doRead=True, streaming=None, **kwargs):
        if filename:
            self.filename = filename
        if streaming is not None:
            self.streaming = streaming
        if not self.filename:
            raise Exception('No filename provided')
        if not os.path.isfile(self.filename):
            raise OSError(2,'File not found:',self.filename)
        if os.stat(self.filename).st_size == 0:
            raise EmptyFileError('File is empty:',self.filename)

        self._enforce_context_if_needed()

        # Calling children function
        self.detect()
        if doRead:
            self._read(**kwargs)

    def detect(self):
        COMMENT_CHAR=['#','!',';']
        # --- Detecting encoding
        # NOTE: done by parent class method
        
        # --- Subfunctions
        def readFirstLines(nLines):
            lines=[]
            with open(self.filename, 'r', encoding=self.encoding, errors="surrogateescape") as fid:
                for i, line in enumerate(fid):
                    lines.append(line.strip())
                    if i==nLines:
                        break
            return lines

        def readline(iLine):
            with open(self.filename,'r',encoding=self.encoding) as f:
                for i, line in enumerate(f):
                    if i==iLine:
                        return line.strip()
                    elif i>iLine:
                        break
        def split(s):
            if s is None:
                return []
            if self.sep==r'\s+':
                return s.strip().split()
            else:
                return [c.strip() for c in s.strip().split(self.sep)]
        def strIsFloat(s):
            try:
                float(s)
                return True
            except:
                return False
        # --- Safety
        if self.sep=='' or self.sep==' ':
            self.sep=r'\s+'

        iStartLine=0
        
        # --- Exclude some files from the CSV reader ---
        line=readline(iStartLine)
        words=line.split()
        if len(words)>1:
            try:
                int(words[0])
                word0int = True
            except:
                word0int = False
            if word0int and words[1].isalpha():
                raise WrongFormatError('Input File {}: '.format(self.filename) + 'is not likely a CSV file' )
                
        # --- Headers (i.e. comments)
        # TODO: read few headers lines instead of multiple read below..

        self.header = []
        if len(self.commentLines)>0:
            # We read the lines
            with open(self.filename,'r',encoding=self.encoding) as f:
                for i in range(max(self.commentLines)+1):
                    l = f.readline()
                    if i in self.commentLines:
                        self.header.append(l.strip())
        elif self.commentChar is not None:
            # we detect the comments lines that start with comment char
            with open(self.filename,'r',encoding=self.encoding) as f:
                n=0
                while n<100:
                    l = f.readline().strip()
                    if (not l) or (l+'_dummy')[0] != self.commentChar[0]:
                        break
                    self.header.append(l.strip())
                    n+=1
            self.commentLines=list(range(len(self.header)))
        else:
            # We still believe that some characters are comments
            line=readline(iStartLine)
            line=str(line).strip()
            if len(line)>0 and line[0] in COMMENT_CHAR:
                self.commentChar=line[0]
                # Nasty copy paste from above
                with open(self.filename,'r',encoding=self.encoding) as f:
                    n=0
                    while n<100:
                        l = f.readline().strip()
                        if (not l) or (l+'_dummy')[0] != self.commentChar[0]:
                            break
                        self.header.append(l.strip())
                        n+=1

        iStartLine = len(self.header)

        # --- File separator 
        if self.sep is None:
            # Detecting separator by reading first lines of the file
            try:
                with open(self.filename,'r',encoding=self.encoding) as f:
                    dummy=[next(f).strip() for x in range(iStartLine)]
                    head=[next(f).strip() for x in range(2)]
                # comma, semi columns or tab
                if head[1].find(',')>0:
                    self.sep=','
                elif head[1].find(';')>0:
                    self.sep=';'
                elif head[1].find('\t')>0:
                    self.sep='\t'
                else:
                    self.sep=r'\s+'
            except:
                # most likely an empty file
                pass

        # --- ColumnNames
        if self.colNamesLine is not None:
            if self.colNamesLine<0:
                # The column names are hidden somwhere in the header 
                line=readline(iStartLine+self.colNamesLine).strip()
                # Removing comment if present (should be present..)
                if self.commentChar is not None:
                    if line.find(self.commentChar)==0:
                        line=line[len(self.commentChar):].strip()
                self.colNames = split(line)
            else:
                line=readline(self.colNamesLine)
                self.colNames=split(line)
                iStartLine = max(iStartLine,self.colNamesLine+1)
        elif len(self.colNames)>0:
            pass
        elif not self.detectColumnNames:
            pass
        else:
            # Looking at first line of data, if mainly floats -> it's not the column names
            colNames = split(readline(iStartLine))
            nFloat = sum([strIsFloat(s) for s in colNames])
            if nFloat ==0 or (len(colNames)>2 and nFloat <= len(colNames)/2):
                # We assume that the line contains the column names
                self.colNames=colNames
                self.colNamesLine = iStartLine
                iStartLine = iStartLine+1
                #  --- Now, maybe the user has put some units below
                first_line = readline(iStartLine)
                #print('>>> first line',first_line)
                first_cols = split(first_line)
                nFloat = sum([strIsFloat(s) for s in first_cols])
                nPa    = first_line.count('(')+first_line.count('[')
                #if nFloat == 0 or nPa>len(self.colNames)/2:
                if nPa>len(self.colNames)/2:
                    # that's definitely some units
                    if len(first_cols)==len(self.colNames):
                        self.colNames=[c.strip()+'_'+u.strip() for c,u in zip(self.colNames, first_cols)]
                    iStartLine = iStartLine+1
            elif len(self.header)>0:
                # Maybe the columns names are in the header
                if self.sep is not None:
                    first_line = readline(iStartLine)
                    first_cols = split(first_line)
                    #print('CommentChar:',self.commentChar)
                    #print('First line:',first_line)
                    #print('First col :',first_cols)
                    for l in self.header:
                        if self.commentChar is not None:
                            if len(self.commentChar)>0:
                                l=l[len(self.commentChar):]
                        cols=split(l)
                        nFloat = sum([strIsFloat(s) for s in cols])
                        if len(cols)==len(first_cols) and nFloat <= len(colNames)-1:
                            self.colNames = cols
                            break
        # --- Reading data
        skiprows = list(range(iStartLine))
        if (self.colNamesLine is not None):
            skiprows.append(self.colNamesLine)
        if (self.commentLines is not None) and len(self.commentLines)>0:
            skiprows = skiprows + self.commentLines
        self.skiprows =list(sorted(set(skiprows)))
        if self.sep is not None:
            if self.sep=='\t':
                self.sep=r'\s+'
        #print(skiprows)

    def _read(self):
        """Read CSV data. In streaming mode, file handle is kept open."""
        try:
            if self.streaming:
                # Streaming mode: keep file open
                self._fid = open(self.filename, 'r', encoding=self.encoding)
                # Skip to data start
                for _ in range(max(self.skiprows) + 1 if self.skiprows else 0):
                    self._fid.readline()
                # Data is not loaded yet
                self.data = None
            else:
                # Normal mode: read entire file
                with open(self.filename,'r',encoding=self.encoding) as f:
                    self.data = pd.read_csv(f,sep=self.sep,skiprows=self.skiprows,header=None,comment=self.commentChar)

                if (len(self.colNames)==0) or (len(self.colNames)!=len(self.data.columns)):
                    self.colNames=['C{}'.format(i) for i in range(len(self.data.columns))]
                self.data.columns = self.colNames
                self.data.rename(columns=lambda x: x.strip(),inplace=True)
        except pd.errors.ParserError as e:
            raise WrongFormatError('CSV File {}: '.format(self.filename)+e.args[0])

    def _readAll(self):
        """Read all remaining CSV data in streaming mode."""
        if self._fid is None:
            raise RuntimeError("No open file handle")

        try:
            # Read remaining data from current position
            self.data = pd.read_csv(self._fid, sep=self.sep, header=None, comment=self.commentChar)

            if (len(self.colNames)==0) or (len(self.colNames)!=len(self.data.columns)):
                self.colNames=['C{}'.format(i) for i in range(len(self.data.columns))]
            self.data.columns = self.colNames
            self.data.rename(columns=lambda x: x.strip(), inplace=True)
        except pd.errors.ParserError as e:
            raise WrongFormatError('CSV File {}: '.format(self.filename)+e.args[0])

    def _readChunk(self, nlines=None, **kwargs):
        """Read a chunk of CSV data (nlines rows)."""
        if self._fid is None:
            raise RuntimeError("No open file handle")

        if nlines is None:
            nlines = 1000  # Default chunk size

        try:
            chunk = pd.read_csv(self._fid, sep=self.sep, header=None, comment=self.commentChar, nrows=nlines)

            if len(chunk) == 0:
                return None  # End of file

            if (len(self.colNames)==0) or (len(self.colNames)!=len(chunk.columns)):
                self.colNames=['C{}'.format(i) for i in range(len(chunk.columns))]
            chunk.columns = self.colNames
            chunk.rename(columns=lambda x: x.strip(), inplace=True)

            return chunk
        except pd.errors.EmptyDataError:
            # End of file reached
            return None
        except pd.errors.ParserError as e:
            raise WrongFormatError('CSV File {}: '.format(self.filename)+e.args[0])


    def read_slow_stop_at_first_empty_lines(self, skiprows=None, sep=None, numeric_only=True, colNames=None):
        """
        HACKY function
        Reads a CSV file line by line, stopping at the first empty line.
        This is a slower method but can be useful for large files or when you want to avoid loading the entire file into memory.
        """
        if skiprows is None:
            skiprows = self.skipRows + self.commentLines 
        if sep is None:
            sep = self.sep if self.sep is not None else ','
        if colNames is None:
            colNames = self.colNames

        def smart_split(line, sep):
            """Splits a line using a separator, which can be a regex (e.g. '\\s+') or a normal string."""
            if sep == r'\s+':
                return re.split(r'\s+', line.strip())
            else:
                return [c.strip() for c in line.strip().split(sep)]
        data = []
        with open(self.filename, 'r', encoding=self.encoding) as f:
            for i, line in enumerate(f):
                if i in skiprows:
                    continue
                line = line.strip()
                if not line:
                    break
                cols = smart_split(line, sep)
                if len(colNames)>0 and len(cols) != len(self.colNames):
                    raise Exception("Error: Wrong number of columns on line {}.".format(i))
                data.append(cols)
        if len(colNames)>0:
            self.data= pd.DataFrame(data, columns=self.colNames)
        else:
            self.data= pd.DataFrame(data)
            self.colNames=['C{}'.format(i) for i in range(len(self.data.columns))]
        self.data.columns = self.colNames;

        if numeric_only:
            self.data = self.data.apply(pd.to_numeric, errors='coerce')
        #self.data.dropna(inplace=True)

    def _write(self):
        # --- Safety
        if self.sep==r'\s+' or self.sep=='':
            self.sep='\t'
        # Write
        if len(self.header)>0:
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.header)+'\n')
            with open(self.filename, 'a', encoding='utf-8') as f:
                try:
                    self.data.to_csv(f,   sep=self.sep,     index=False,header=False, line_terminator='\n')
                except TypeError:
                    print('[WARN] CSVFile: Pandas failed, likely encoding error. Attempting a quick and dirty fix.')
                    s=''
                    vals=self.data.values
                    for l in vals:
                        sLine=(self.sep).join([str(v) for v in l])
                        s+=sLine+'\n'
                    f.write(s)
        else:
            self.data.to_csv(self.filename,sep=self.sep,index=False)

    def __repr__(self):
        s = '<CSVFile: {}>\n'.format(self.filename)
        s += '| - sep         =`{}`\n'.format(self.sep)
        s += '| - commentChar =`{}`\n'.format(self.commentChar)
        s += '| - colNamesLine= {}\n'.format(self.colNamesLine)
        s += '| - encoding    = {}\n'.format(self.encoding)
        s += '| - commentLines= {}\n'.format(self.commentLines)
        s += '| - skipRows    = {}\n'.format(self.skipRows)
        s += '| - colNames    = {}\n'.format(self.colNames)
        if len(self.header)>0:
            s += '| - header:\n'+ '\n'.join(self.header)+'\n'
        if len(self.data)>0:
            s += '| - size: {}x{}'.format(len(self.data),len(self.data.columns))
        return s

    def toDataFrame(self):
        return self.data

    def to2DFields(self, **kwargs):
        import xarray as xr
        if len(kwargs.keys())>0:
            print('[WARN] CSVFile: to2DFields: ignored keys: ',kwargs.keys())
        if len(self.data)==0:
            return None
        M = self.data.values
        if self.data.columns[0].lower()=='index':
            M = M[:,1:]
        s1 = 'rows'
        s2 = 'columns'
        ds = xr.Dataset(coords={s1: range(M.shape[0]), s2: range(M.shape[1])})
        ds['data'] = ([s1, s2], M)
        return ds

    # --------------------------------------------------------------------------------
    # --- Properties NOTE: copy pasted from file.py to make this file standalone..
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


def find_non_numeric_header_lines(filename):
    """
    Reads a file line by line and returns a list of indices for lines that are headers,
    i.e., lines that contain anything other than numbers, commas, tabs, spaces, or scientific notation.
    Stops at the first line that is purely numeric (with allowed delimiters).
    """
    header_indices = []
    header_lines = []
    numeric_line_pattern = re.compile(r'^[\s,]*([+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?[\s,]*)+$')
    with open(filename, 'r', errors="surrogateescape") as f:
        for idx, line in enumerate(f):
            s = line.strip()
            if not s: continue
            if numeric_line_pattern.fullmatch(s):
                break
            header_lines.append(s)
            header_indices.append(idx)
    return header_indices, header_lines

if __name__ == '__main__':
    f = CSVFile('C:/Work/Courses/440/project_solution/data/CFD_u.dat')
    print(f)
    ds = f.to2DFields()
    print(ds)

