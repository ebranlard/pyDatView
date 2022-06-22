""" 
Input/output class for the ROSCO performance (Cp,Ct,Cq) fileformat 
"""
import numpy as np
import pandas as pd
import os

try:
    from .file import File, WrongFormatError, BrokenFormatError
except:
    EmptyFileError    = type('EmptyFileError', (Exception,),{})
    WrongFormatError  = type('WrongFormatError', (Exception,),{})
    BrokenFormatError = type('BrokenFormatError', (Exception,),{})
    File=dict

class ROSCOPerformanceFile(File):
    """ 
    Read/write a ROSCO performance file. The object behaves as a dictionary.
    
    Main methods
    ------------
    - read, write, toDataFrame, keys
    
    Examples
    --------
        f = ROSCOPerformanceFile('Cp_Ct_Cq.txt')
        print(f.keys())
        print(f.toDataFrame().columns)  
    
    """

    @staticmethod
    def defaultExtensions():
        """ List of file extensions expected for this fileformat"""
        return ['.txt']

    @staticmethod
    def formatName():
        """ Short string (~100 char) identifying the file format"""
        return 'ROSCO Performance file'

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
        # --- Example: 
        pitch, TSR, WS, Cp, Ct, Cq = load_from_txt(self.filename)
        self['pitch'] = pitch
        self['TSR']   = TSR
        self['WS']    = WS
        self['CP']    = Cp
        self['CT']    = Ct
        self['CQ']    = Cq

    def _write(self):
        """ Writes to self.filename"""
        # --- Example:
        write_rotor_performance(self.filename, self['pitch'], self['TSR'], self['CP'],self['CT'], self['CQ'], self['WS'], TurbineName='')

    def toDataFrame(self):
        """ Returns object into dictionary of DataFrames"""
        dfs={}
        columns = ['TSR_[-]']+['Pitch_{:.2f}_[deg]'.format(p) for p in self['pitch']]
        dfs['CP'] = pd.DataFrame(np.column_stack((self['TSR'], self['CP'])), columns=columns)
        dfs['CT'] = pd.DataFrame(np.column_stack((self['TSR'], self['CT'])), columns=columns)
        dfs['CQ'] = pd.DataFrame(np.column_stack((self['TSR'], self['CQ'])), columns=columns)
        return dfs

    # --- Optional functions
    def __repr__(self):
        """ String that is written to screen when the user calls `print()` on the object. 
        Provide short and relevant information to save time for the user. 
        """
        s='<{} object>:\n'.format(type(self).__name__)
        s+='|Main attributes:\n'
        s+='| - filename: {}\n'.format(self.filename)
        # --- Example printing some relevant information for user
        s+='|Main keys:\n'
        s+='| - pitch: {}\n'.format(self['pitch'])
        s+='| - TSR:   {}\n'.format(self['TSR'])
        s+='| - WS:    {}\n'.format(self['WS'])
        s+='| - CP,CT,CQ : shape {}\n'.format(self['CP'].shape)
        s+='|Main methods:\n'
        s+='| - read, write, toDataFrame, keys'
        return s
    



def load_from_txt(txt_filename):
    '''
    Taken from ROSCO_toolbox/utitities.py by Nikhar Abbas
        https://github.com/NREL/ROSCO
        Apache 2.0 License

    Load rotor performance data from a *.txt file. 
    Parameters:
    -----------
        txt_filename: str
                        Filename of the text containing the Cp, Ct, and Cq data. This should be in the format printed by the write_rotorperformance function
    '''

    pitch = None
    TSR   = None
    WS    = None

    with open(txt_filename) as pfile:
        for iline, line in enumerate(pfile):
            # Read Blade Pitch Angles (degrees)
            if 'Pitch angle' in line:
                pitch = np.array([float(x) for x in pfile.readline().strip().split()])

            # Read Tip Speed Ratios (rad)
            elif 'TSR' in line:
                TSR = np.array([float(x) for x in pfile.readline().strip().split()])

            #Read WS
            elif 'Wind speed' in line:
                WS = np.array([float(x) for x in pfile.readline().strip().split()])
            
            # Read Power Coefficients
            elif 'Power' in line:
                pfile.readline()
                Cp = np.empty((len(TSR),len(pitch)))
                for tsr_i in range(len(TSR)):
                    Cp[tsr_i] = np.array([float(x) for x in pfile.readline().strip().split()])
            
            # Read Thrust Coefficients
            elif 'Thrust' in line:
                pfile.readline()
                Ct = np.empty((len(TSR),len(pitch)))
                for tsr_i in range(len(TSR)):
                    Ct[tsr_i] = np.array([float(x) for x in pfile.readline().strip().split()])

            # Read Torque Coefficients
            elif 'Torque' in line:
                pfile.readline()
                Cq = np.empty((len(TSR),len(pitch)))
                for tsr_i in range(len(TSR)):
                    Cq[tsr_i] = np.array([float(x) for x in pfile.readline().strip().split()])

            if pitch is None and iline>10:
                raise WrongFormatError('This does not appear to be a ROSCO performance file, Pitch vector not found')

        return pitch, TSR, WS, Cp, Ct, Cq


def write_rotor_performance(txt_filename, pitch, TSR, CP, CT, CQ, WS=None, TurbineName=''):
    '''
    Taken from ROSCO_toolbox/utitities.py by Nikhar Abbas
        https://github.com/NREL/ROSCO
        Apache 2.0 License

    Write text file containing rotor performance data
    Parameters:
    ------------
        txt_filename: str, optional
                        Desired output filename to print rotor performance data. Default is Cp_Ct_Cq.txt
    '''
    file = open(txt_filename,'w')
    # Headerlines
    file.write('# ----- Rotor performance tables for the {} wind turbine ----- \n'.format(TurbineName))
    file.write('# ------------ Written on {} using the ROSCO toolbox ------------ \n\n'.format(now.strftime('%b-%d-%y')))

    # Pitch angles, TSR, and wind speed
    file.write('# Pitch angle vector, {} entries - x axis (matrix columns) (deg)\n'.format(len(pitch)))
    for i in range(len(pitch)):
        file.write('{:0.4}   '.format(pitch[i]))
    file.write('\n# TSR vector, {} entries - y axis (matrix rows) (-)\n'.format(len(TSR)))
    for i in range(len(TSR)):
        file.write('{:0.4}    '.format(TSR[i]))
    if WS is not None:
        file.write('\n# Wind speed vector - z axis (m/s)\n')
        for i in range(len(WS)):
            file.write('{:0.4}    '.format(WS[i]))
        file.write('\n')
    
    # Cp
    file.write('\n# Power coefficient\n\n')
    for i in range(len(TSR)):
        for j in range(len(pitch)):
            file.write('{0:.6f}   '.format(CP[i,j]))
        file.write('\n')
    file.write('\n')
    
    # Ct
    file.write('\n#  Thrust coefficient\n\n')
    for i in range(len(TSR)):
        for j in range(len(pitch)):
            file.write('{0:.6f}   '.format(CT[i,j]))
        file.write('\n')
    file.write('\n')
    
    # Cq
    file.write('\n# Torque coefficient\n\n')
    for i in range(len(TSR)):
        for j in range(len(pitch)):
            file.write('{0:.6f}   '.format(CQ[i,j]))
        file.write('\n')
    file.write('\n')
    file.close()




if __name__ == '__main__':
    f = ROSCOPerformanceFile('./tests/example_files/RoscoPerformance_CpCtCq.txt')
    print(f)
    dfs = f.toDataFrame()
    print(dfs['CP'])

