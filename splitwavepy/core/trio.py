from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from . import core
from . import core3d
from .pair import Pair
from .window import Window

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

import copy

class Trio:
    """
    The Trio: work with 3-component data.
        
    Usage: Trio()     => create Trio of synthetic data
           Trio(data) => creates Trio from two traces stored as rows in numpy array data
           Trio(x,y,z) => creates Trio from two traces stored in numpy arrays x and y.
    
    Keyword Arguments:
        - delta = 1. (sample interval) [default] | float
        - units = 's' (for labelling) | string
        - geom = 'cart' (x,y,z) [default] | 'geo' (az,inc,r) | 'ray' (P,SH,SV) 
        - window = None (default) | Window object
        - angle
    
    Advanced Keyword Arguments (if in doubt don't use):
        - xyz = np.ones(3) | custom numpy array
        - rcvloc = None
        - srcloc = None
    """
    def __init__(self,*args,**kwargs):
        
        if ('delta' in kwargs):
            self.delta = kwargs['delta']
        else:
            self.delta = 1.
            
        if ('units' in kwargs):
            self.units = kwargs['units']
        else:
            self.units = 's'
        
        if ('window' in kwargs and isinstance(kwargs['window'],Window)):
            self.window = window
        else:
            self.window = None
        
        if len(args) == 0:
            if ('lag' in kwargs):
                # convert time shift to nsamples -- must be even
                nsamps = int(kwargs['lag']/self.delta)
                nsamps = nsamps if nsamps%2==0 else nsamps + 1
                kwargs['lag'] = nsamps                                      
            self.x, self.y, self.z = _synth(**kwargs)                  
        elif len(args) == 3:            
            self.x, self.y, self.z = args[0],args[1],args[2]    
        else: 
            raise Exception('Unexpected number of arguments')
                    
        # some sanity checks
        if self.x.ndim != 1:
            raise Exception('data must be one dimensional')
        if self.x.size%2 == 0:
            raise Exception('data must have odd number of samples')
        if (self.x.size != self.y.size) or (self.x.size != self.z.size):
            raise Exception('x and y and z must be the same length')
         
        # add geometry info
        if ('geom' in kwargs):
            self.geom = kwargs['geom']
        else:
            # if using 3-component data I'll guess the user wants cartesian coordinates.
            self.geom = 'cart'
            
        if ('srcloc' in kwargs):
            self.srcloc = kwargs['srcloc']
            
        if ('rcvloc' in kwargs):
            self.rcvloc = kwargs['rcvloc']
            
        # if ('xyz' in kwargs):
        #     self.xyz = kargs['xyz']
        # else:
        #     self.xyz = np.ones(3)
        
    # methods
    
    # set time from start
    def t(self):
        return np.arange(self.x.size) * self.delta
        
    def nsamps(self):
        return self.x.size

    def power(self):
        return self.x**2+self.y**2+self.z**2
        
    def centre(self):
        return int(self.x.size/2)
        
    def xyz(self):
        return np.vstack((self.x,self.y,self.z))

    def plot(self,window=None):
        """
        Plot trace data and particle motion
        """
        from matplotlib import gridspec
        fig = plt.figure(figsize=(12, 3))
        if window is None:
            gs = gridspec.GridSpec(1, 2, width_ratios=[3, 1])
            ax0 = plt.subplot(gs[0])
            ax0.plot(self.t(),self.x)
            ax0.plot(self.t(),self.y)
            ax0.plot(self.t(),self.z)
            # particle  motion
            lim = abs(self.xyz().max()) * 1.1
            # the polar axis:
            # ax_polar = plt.subplot(gs[1], polar=True, frameon=False)
            # ax_polar.set_rmax(lim)
            # ax_polar.patch.set_facecolor(111)
            # ax_polar.get_xaxis.set_visible(False)
            # ax_polar.grid(True)
            # the data
            ax1 = plt.subplot(gs[1])
            # ax1.patch.set_alpha(0)
            ax1.axis('equal')
            ax1.plot(self.y,self.x)
            ax1.set_xlim([-lim,lim])
            ax1.set_ylim([-lim,lim])
            ax1.axes.get_xaxis().set_visible(False)
            ax1.axes.get_yaxis().set_visible(False)
        else:
            gs = gridspec.GridSpec(1, 3, width_ratios=[3,1,1])
            ax0 = plt.subplot(gs[0])
            ax0.plot(self.t(),self.x)
            ax0.plot(self.t(),self.y)
            ax0.plot(self.t(),self.z)
            # the window limits
            nsamps = self.t().size
            wbeg = window.start(nsamps)*self.delta
            wend = window.end(nsamps)*self.delta
            ax0.axvline(wbeg,linewidth=2,color='r')
            ax0.axvline(wend,linewidth=2,color='r')
            # windowed data
            d2 = self.copy()
            d2.chop(window)
            ax1 = plt.subplot(gs[1])
            ax1.plot(d2.t()+wbeg,d2.x)
            ax1.plot(d2.t()+wbeg,d2.y)
            ax1.plot(d2.t()+wbeg,d2.z)
            # particle  motion
            lim = abs(d2.xyz().max()) * 1.1
            ax2 = plt.subplot(gs[2])
            ax2.axis('equal')
            ax2.plot(d2.y,d2.x)
            ax2.set_xlim([-lim,lim])
            ax2.set_ylim([-lim,lim])
            ax2.axes.get_xaxis().set_visible(False)
            ax2.axes.get_yaxis().set_visible(False)

        # show
        plt.show()
        
    def ppm(self,window=None):
        """Plot particle motion."""
        fig = plt.figure()                       
        ax = fig.gca(projection='3d')
        ax.plot(self.x,self.y,self.z)
        lim = abs(self.xyz().max()) * 1.1
        ax.axis('equal')
        ax.set_xlim([-lim,lim])
        ax.set_ylim([-lim,lim])
        ax.set_zlim([-lim,lim])
        plt.show()
        
        
    #
    # def split(self,degrees,tlag,copy=False):
    #     """
    #     Applies splitting operator (phi,dt) to Pair.
    #
    #     Rotates data so that trace1 is lined up with degrees (and trace2 90 degrees clockwise).
    #     Applies a relative time shift by the nearest even number of samples to tlag,
    #     trace1 is shifted tlag/2 forward in time, and trace2 tlag/2 backward in time.
    #     Then undoes the original rotation.
    #     """
    #     # convert time shift to nsamples -- must be even
    #     nsamps = int(tlag / self.delta)
    #     nsamps = nsamps if nsamps%2==0 else nsamps + 1
    #     # find appropriate rotation angle
    #     rangle = degrees - self.angle
    #     # apply splitting
    #     if copy == False:
    #         self.data = core.split(self.data,rangle,nsamps)
    #     else:
    #         dupe = self.copy()
    #         dupe.data = core.split(self.data,rangle,nsamps)
    #         return dupe
    #
    # def unsplit(self,degrees,tlag,copy=False):
    #     """
    #     Applies reverse splitting operator (phi,dt) to Pair.
    #
    #     Rotates data so that trace1 is lined up with degrees (and trace2 90 degrees clockwise).
    #     Applies a relative time shift by the nearest even number of samples to tlag,
    #     trace1 is shifted tlag/2 backward in time, and trace2 tlag/2 forward in time.
    #     Then undoes the original rotation.
    #     """
    #     # convert time shift to nsamples -- must be even
    #     nsamps = int(tlag / self.delta)
    #     nsamps = nsamps if nsamps%2==0 else nsamps + 1
    #     # find appropriate rotation angle
    #     rangle = degrees - self.angle
    #     if copy == False:
    #         self.data = core.unsplit(self.data,rangle,nsamps)
    #     else:
    #         dupe = self.copy()
    #         dupe.data = core.unsplit(self.data,rangle,nsamps)
    #         return dupe
    #
    # def rotateto(self,degrees,copy=False):
    #     """
    #     Rotate data so that trace1 lines up with *degrees*
    #     """
    #     # find appropriate rotation angle
    #     rangle = -degrees - self.angle
    #     if copy == False:
    #         self.data = core.rotate(self.data,rangle)
    #         self.angle = degrees
    #     else:
    #         dupe = self.copy()
    #         dupe.data = core.rotate(self.data,rangle)
    #         dupe.angle = degrees
    #         return dupe
    #
    # def lag(self,tlag,copy=False):
    #     """
    #     Relative shift trace1 and trace2 by tlag seconds
    #     """
    #     # convert time shift to nsamples -- must be even
    #     nsamps = int(tlag / self.delta)
    #     nsamps = nsamps if nsamps%2==0 else nsamps + 1
    #     if copy == False:
    #         self.data = core.lag(self.data,nsamps)
    #     else:
    #         dupe = self.copy()
    #         dupe.data = core.lag(self.data,nsamps)
    #         return dupe
     
    def chop(self,window,copy=False):
        """
        Chop data around window
        """
        self.x, self.y, self.z = core.chop(self.x,self.y,self.z,window=window)

        
    def genwindow(self,time_centre,time_width,tukey=None):
        """
        Return a window object about time_centre with time_width.
        """
        tcs = int(time_centre / self.delta)
        offset = tcs - self.centre()
        # convert time to nsamples -- must be odd
        width = int(time_width / self.delta)
        width = width if width%2==1 else width + 1        
        return Window(width,offset,tukey=tukey)
                
               
    def copy(self):
        return copy.copy(self)
        


def _synth(**kwargs):
    """return ricker wavelet synthetic data"""
    
    if ('pol' in kwargs):
        pol = kwargs['pol']
    else:
        pol = 0.
        
    if ('fast' in kwargs):
        fast = kwargs['fast']
    else:
        fast = 0.
        
    if ('lag' in kwargs):
        lag = kwargs['lag']
    else:
        lag = 0
        
    if ('noise' in kwargs):
        noise = kwargs['noise']
    else:
        noise = 0.03
        
    if ('nsamps' in kwargs):
        nsamps = kwargs['nsamps']
    else:
        nsamps = 501
        
    if ('width' in kwargs):
        width = kwargs['width']
    else:
        width = 16.
        
    if ('window' in kwargs):
        window = kwargs['window']
    else:
        window = Window(width*3)

    nsamps = int(nsamps)
    
    x = signal.ricker(nsamps, width) + core.noise(nsamps,noise,width/4)
    y = core.noise(nsamps,noise,width/4)
    z = core.noise(nsamps,noise,width/4)
    
    # rotate to polarisation
    x,y = core.rotate(x,y,-pol)
    
    # add any splitting -- this will reduce nsamps
    x,y = core.split(x,y,fast,lag)
    
    return x,y,z