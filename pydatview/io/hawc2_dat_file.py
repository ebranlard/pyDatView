import numpy as np
import pandas as pd
import os 

from .file import File, WrongFormatError, FileNotFoundError
from .wetb.hawc2.Hawc2io import ReadHawc2


class HAWC2DatFile(File):

    @staticmethod
    def defaultExtensions():
        return ['.dat','.sel']

    @staticmethod
    def formatName():
        return 'HAWC2 dat file'

    def __init__(self, filename=None, streaming=False, **kwargs):
        self.info={}
        self.data=None if streaming else np.array([])
        self.bHawc=False
        self._res_file = None  # Store ReadHawc2 object for streaming

        # Call parent __init__ - handles streaming, filename, _in_context, _fid
        File.__init__(self, filename=filename, streaming=streaming, **kwargs)

    def _read(self, streaming=False, **kwargs):
        try:
            res_file  = ReadHawc2(self.filename)

            # Store metadata (always loaded)
            self.info['attribute_names'] = res_file.ChInfo[0]
            self.info['attribute_units'] = res_file.ChInfo[1]
            self.info['attribute_descr'] = res_file.ChInfo[2]
            self.info['NrSc'] = res_file.NrSc
            self.info['NrCh'] = res_file.NrCh
            self.info['Time'] = res_file.Time
            self.info['Freq'] = res_file.Freq
            self.info['FileFormat'] = res_file.FileFormat

            if res_file.FileFormat=='BHAWC_ASCII':
                self.bHawc=True

            if streaming:
                # Streaming mode: store ReadHawc2 object, don't load data yet
                self._res_file = res_file
                self.data = None
            else:
                # Normal mode: load all data immediately
                self.data = res_file.ReadAll()

        except FileNotFoundError:
            raise
        except Exception as e:
            raise WrongFormatError('HAWC2 dat File {}: '.format(self.filename)+e.args[0])

    def _readAll(self):
        """Read all data in streaming mode."""
        if self._res_file is None:
            raise RuntimeError("No ReadHawc2 object available (not in streaming mode)")

        # Read all channels
        self.data = self._res_file.ReadAll()

    def _readChunk(self, **kwargs):
        """Read chunk of data - not implemented for HAWC2 files."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support readChunk()")

    #def _write(self):
        #self.data.to_csv(self.filename,sep=self.false,index=False)

    def _toDataFrame(self):
        import re

        # Simplify output names
        names=self.info['attribute_names']
        for i,desc in enumerate(self.info['attribute_descr']):
            elem = re.findall(r'E-nr:\s*(\d+)', desc)
            zrel = re.findall(r'Z-rel:\s*(\d+.\d+)', desc)
            node = re.findall(r'nodenr:\s*(\d+)', desc)
            mbdy = re.findall(r'Mbdy:([-a-zA-Z0-9_.]*) ', desc)
            s    = re.findall(r's=\s*(\d+.\d+)\[m\]', desc)
            sS   = re.findall(r's/S=\s*(\d+.\d+)', desc)

            pref=''
            names[i] = names[i].replace(' ','')
            names[i] = names[i].replace('coo:global','g').strip()
            names[i] = names[i].replace('Statepos','').strip()
            names[i] = names[i].replace('axisangle','rot_').strip()

            if len(mbdy)==1:
                names[i] = names[i].replace('coo:'+mbdy[0],'b').strip()
                pref += mbdy[0]

            if len(zrel)==1 and len(elem)==1:
                ielem=int(elem[0])
                fzrel=float(zrel[0])
                if fzrel==0:
                    pref+= 'N'+str(ielem)
                elif fzrel==1:
                    pref+='N'+str(ielem+1)
                else:
                    pref+='N'+str(ielem+fzrel)
            if len(s)==1 and len(sS)==1:
                pref+='r'+str(sS[0])

            if len(node)==1:
                pref+='N'+node[0]
            names[i]=pref+names[i]

        if self.info['attribute_units'] is not None:
            units = [u.replace('(','').replace(')','').replace('[','').replace(']','') for u in self.info['attribute_units']]

            cols=[n+'_['+u+']' for n,u in zip(names,units)]
        else:
            cols=names

        return pd.DataFrame(data=self.data,columns=cols)
#
    def _write(self):
        filename=self.filename
        ext = os.path.splitext(filename)[-1].lower()
        if ext=='.dat':
            datfilename=filename
        elif ext=='.sel':
            datfilename=filename.replace(ext,'.dat')
        else:
            datfilename=filename+'.dat'
        selfilename=datfilename[:-4]+'.sel'
        nScans    = self.data.shape[0]
        nChannels = self.data.shape[1]
        SimTime   = self.data[-1,0] #-self.data[0,0]
        # --- dat file
        np.savetxt(datfilename, self.data, fmt='%16.8e')
        # --- Sel file
        with open(selfilename, 'w') as f:
            if self.bHawc:
                f.write('BHawC channel reference file (sel):\n')
                f.write('+===================== (Name) =================== (Time stamp) ========= (Path) ==========================================================+\n')
                f.write('Original BHAWC file    : NA.dat                    2001.01.01  00:00:00  C:\\\n')
                f.write('Channel reference file : NA.sel                    2001.01.01  00:00:00  C:\\\n')
                f.write('Result file            : NA.dat                    2001.01.01  00:00:00  C:\\\n')
                f.write('+=========================================================================================================================================+\n')
                f.write('Scans             \tChannels                      \tTime [sec]                \tCoordinate convention: Siemens\n')
                f.write('{:19s}\t{:25s}\t{:25s}\n\n'.format(str(nScans),str(nChannels),'{:.3f}'.format(SimTime)))
                f.write('{:19s}\t{:25s}\t{:25s}\t{:25s}\n'.format('Channel','Variable descriptions','Labels','Units'))
                for chan,(label,descr,unit) in enumerate(zip(self.info['attribute_names'],self.info['attribute_descr'],self.info['attribute_units'])):
                    unit=unit.replace('(','').replace(')','').replace('[','').replace(']','')
                    f.write('{:19s}\t{:25s}\t{:25s}\t{:25s}\n'.format(str(chan+1),descr[0:26],label[0:26],'['+unit+']'))
            else:

                f.write('________________________________________________________________________________________________________________________\n')
                f.write('  Version ID : NA\n')
                f.write('                                                            Time : 00:00:00\n')
                f.write('                                                            Date : 01:01.2001\n')
                f.write('________________________________________________________________________________________________________________________\n')
                f.write('  Result file : {:s}\n'.format(os.path.basename(datfilename)))
                f.write('________________________________________________________________________________________________________________________\n')
                f.write('   Scans    Channels    Time [sec]      Format\n')
                f.write('{:12s}{:12s}{:16s}{:s}\n'.format(str(nScans),str(nChannels),'{:.3f}'.format(SimTime),'ASCII'))
                f.write('\n')
                f.write('{:12s}{:31s}{:11s}{:s}'.format('Channel','Name','Unit','Variable Description\n'))
                f.write('\n')
                for chan,(label,descr,unit) in enumerate(zip(self.info['attribute_names'],self.info['attribute_descr'],self.info['attribute_units'])):
                    unit=unit.replace('(','').replace(')','').replace('[','').replace(']','')
                    f.write('{:12s}{:31s}{:11s}{:s}\n'.format(str(chan+1),label[0:30],unit,descr))
                f.write('________________________________________________________________________________________________________________________\n');

class BHAWCDatFile(HAWC2DatFile):
    def __init__(self, filename=None, **kwargs):
        super(HAWC2DatFile, self).__init__(filename=filename,**kwargs)
        self.bHawc=False
