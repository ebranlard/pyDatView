import unittest
import numpy as np
#from pydatview.Tables import Table
import os
import matplotlib.pyplot as plt


from pydatview.plotdata import PlotData

class TestPlotData(unittest.TestCase):

    def test_FFT(self):
        # --- Test plotdata conversion to FFT
        # Ampltidue and frequency of a sin function should be retrieved
        dt = 0.1
        f0 = 1  ; 
        A  = 5  ; 
        t=np.arange(0,10,dt);
        y=A*np.sin(2*np.pi*f0*t)

        PD=PlotData(t,y)
        PD.toFFT(yType='Amplitude', avgMethod='None', bDetrend=False)
        f = PD.x
        Y = PD.y
        i=np.argmax(Y)
        self.assertAlmostEqual(Y[i],A)
        self.assertAlmostEqual(f[i],f0)

    def test_MinMax(self):
        # Test Min Max scaling (between 0 and 1)
        x = np.linspace(-2,2,100)
        y = x**3
        PD = PlotData(x,y)
        PD.toMinMax(xScale=True,yScale=True)
        self.assertAlmostEqual(np.min(PD.x),0.0)
        self.assertAlmostEqual(np.min(PD.y),0.0)
        self.assertAlmostEqual(np.max(PD.x),1.0)
        self.assertAlmostEqual(np.max(PD.y),1.0)

    def test_PDF(self):
        # --- Test the PDF conversion of plotdata
        # Check that the PDF of random normal noise is a Gaussian
        from pydatview.curve_fitting import model_fit
        mu=0
        sigma=1
        x = np.linspace(-1,1,15000)
        y = np.random.normal(mu,sigma,len(x))
        PD = PlotData(x,y)
        PD.toPDF()

        y_fit, pfit, fitter = model_fit('predef: gaussian', PD.x, PD.y)
        np.testing.assert_almost_equal(mu   ,fitter.model['coeffs']['mu']   , 1)
        np.testing.assert_almost_equal(sigma,fitter.model['coeffs']['sigma'], 1)
        #print(fitter)
        #plt.plot(PD.x,PD.y)
        #plt.plot(PD.x,fitter.model['fitted_function'](PD.x),'k--')
        #plt.show()

if __name__ == '__main__':
    unittest.main()
