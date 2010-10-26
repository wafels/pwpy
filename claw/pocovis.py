#! /usr/bin/env python

"""= pocovis.py - a skeleton task
& claw
: Unknown
+
 Script to load and visualize poco data
--
"""

import sys
#import mirtask
#from mirtask import uvdat, keys, util
import miriad
import numpy as n
import pylab as p
import scipy.optimize as opt
from threading import Thread
#from matplotlib.font_manager import fontManager, FontProperties
#font= FontProperties(size='x-small');


class poco:
    def __init__(self,file,nints=1000,nskip=0):
        # initialize
        self.nchan = 64
        self.chans = n.arange(6,58)
        self.nbl = 36
        initsize = nints*self.nbl   # number of integrations to read in a single chunk
        self.sfreq = 0.718  # freq for first channel in GHz
        self.sdf = 0.104/self.nchan   # dfreq per channel in GHz
        self.baseline_order = n.array([ 257, 258, 514, 261, 517, 1285, 262, 518, 1286, 1542, 259, 515, 773, 774, 771, 516, 1029, 1030, 772, 1028, 1287, 1543, 775, 1031, 1799, 1544, 776, 1032, 1800, 2056, 260, 263, 264, 519, 520, 1288])   # second iteration of bl nums
        self.autos = []
        self.noautos = []
        self.dmarr = n.arange(35,75,1)       # dm trial range in pc/cm3
#        self.tshift = 0.2     # not implemented yet
        self.nskip = nskip*self.nbl    # number of iterations to skip (for reading in different parts of buffer)
        nskip = self.nskip
        self.usedmmask = False    # algorithm for summing over dm track.  'dmmask' is data-shaped array with True/False values, else is 2xn array where track is.
        for a1 in range(1,9):             # loop to adjust delays
            for a2 in range(a1,9):
                self.blindex = n.where(self.baseline_order == a1*256 + a2)[0][0]
                if a1 == a2:
                    self.autos.append(self.blindex)
                else:
                    self.noautos.append(self.blindex)

# load data
#
# slick way, but hard to hack for interactive use
#        sys.argv.append('vis='+file)
#        keys.doUvdat ('dsl3', True)
#        opts = keys.process ()

# poor man's way
        vis = miriad.VisData(file)

        # initialize parameters
        nchan = self.nchan
        nbl = self.nbl
        i = 0
        da = n.zeros((initsize,nchan),dtype='complex64')
        fl = n.zeros((initsize,nchan),dtype='bool')
        ti = n.zeros((initsize),dtype='float64')

        # read data
        # You can pass traditional Miriad UV keywords to readLowlevel as keyword arguments
        for inp, preamble, data, flags, nread in vis.readLowlevel (False):
#        for inp, preamble, data, flags, nread in uvdat.readAll ():

            # Loop to skip some data and read shifted data into original data arrays
            if i < nskip:
                i = i+1
                continue 

            # Reduce these arrays to the correct size
            data = data[0:nread]
            flags = flags[0:nread]

    # Decode the preamble
    #        u, v, w = preamble[0:3]
            time = preamble[3]
    #        baseline = util.decodeBaseline (preamble[4])

    #    pol = uvdat.getPol ()
    
            if (i-nskip) < initsize:
                ti[i-nskip] = time
                da[i-nskip] = data
                fl[i-nskip] = flags
            else:
                break     # test to stop at initsize
#                da = n.concatenate((da,[data]))
#                ti = n.concatenate((ti,[time]))
#                fl = n.concatenate((fl,[flags]))
#                bl = n.concatenate((bl,[baseline]))
            if not (i % 10000):
                print 'Read integration ', str(i)
            i = i+1

        if i < initsize:
            print 'Array smaller than initialized array.  Trimming.'
            da = da[0:i-nskip]
            fl = fl[0:i-nskip]
            ti = ti[0:i-nskip]

        self.data = da.reshape((i-nskip)/nbl,nbl,nchan)
        self.flags = fl.reshape((i-nskip)/nbl,nbl,nchan)
        self.time = ti[::nbl]
        self.reltime = 24*3600*(self.time - self.time[0])      # relative time array in seconds
        print
        print 'Data read!'
        print 'Shape of Data, Flags, Time:'
        print self.data.shape, self.flags.shape, self.time.shape
        print 


    def prep(self):
        self.data = (self.data * self.flags)[:,self.noautos].mean(axis=1)
        self.data = self.data[:,self.chans] 
        print 'Data flagged, trimmed in channels, and averaged across baselines.'
        print 'New shape:'
        print self.data.shape


    def spec(self):
        noautos = self.noautos
        autos = self.autos
        chans = self.chans
        time = self.time
        data = self.data

#reorganize into dimensions of integration, baseline, channel
        print 'Plotting spectrgram.'
        abs = n.abs(data[:,chans])

        p.figure(1)
        day0 = int(time[0])
        ax = p.imshow(abs, aspect='auto', interpolation='nearest')
#    ax = p.imshow(abs, aspect='auto', extent=(0,max(chans),max(time-day0),min(time-day0)))
#    p.axis([-0.5,len(chans)+0.5,100,0])
        p.colorbar(ax)


    def dmmask(self, dm = 0., t0 = 0., show=0,):
        """Takes dispersion measure in pc/cm3 and time offset from first integration in seconds.
        Returns a mask to be multiplied by the data array.
        Not typically used now, since dmtrack is faster.
        """

        reltime = self.reltime
        if self.data.shape[1] == len(self.chans):
            chans = self.chans
        else:
            chans = n.arange(nchan)

        # initialize mask (false=0)
        mask = n.zeros((self.data.shape[0],self.data.shape[1]),dtype=bool)   # could get clever here.  use integer code to stack dm masks in unique way
        freq = self.sfreq + chans * self.sdf             # freq array in GHz

        # given freq, dm, dfreq, calculate pulse time and duration
        pulset = 4.2e-3 * dm * freq**(-2) + t0  # time in seconds
        pulsedt = 8.3e-6 * dm * (1000*self.sdf) * freq**(-3)   # dtime in seconds

        for ch in range(mask.shape[1]):
            ontime = n.where(((pulset[ch] + pulsedt[ch]/2.) >= reltime) & ((pulset[ch] - pulsedt[ch]/2.) <= reltime))
#            print ontime
            mask[ontime, ch] = True

        if show:
            ax = p.imshow(mask, aspect='auto', interpolation='nearest')
            p.axis([-0.5,len(chans)+0.5,max(reltime),min(reltime)])
            p.colorbar(ax)

        return mask


    def dmtrack(self, dm = 0., t0 = 0., show=0):
        """Takes dispersion measure in pc/cm3 and time offset from first integration in seconds.
        Returns an array of (time, channel) to select from the data array.
        Faster than dmmask.
        """

        reltime = self.reltime
        if self.data.shape[1] == len(self.chans):  # related to preparing of data?
            chans = self.chans
        else:
            chans = n.arange(self.nchan)
        nchan = len(chans)

        freq = self.sfreq + chans * self.sdf             # freq array in GHz

        # given freq, dm, dfreq, calculate pulse time and duration
        pulset = 4.2e-3 * dm * freq**(-2) + t0  # time in seconds
        pulsedt = 8.3e-6 * dm * (1000*self.sdf) * freq**(-3)   # dtime in seconds

        timebin = []
        chanbin = []
        for ch in range(nchan):
            ontime = n.where(((pulset[ch] + pulsedt[ch]/2.) >= reltime) & ((pulset[ch] - pulsedt[ch]/2.) <= reltime))
#            print ontime[0], ch
            timebin = n.concatenate((timebin, ontime[0]))
            chanbin = n.concatenate((chanbin, (ch * n.ones(len(ontime[0]), dtype=int))))

        track = (list(timebin), list(chanbin))
#        print 'timebin, chanbin:  ', timebin, chanbin

        if show:
            p.plot(track[1], track[0])

        return track


    def dedisperse(self):
        """Integrates over data*dmmask or data at dmtrack for each pair of elements in dmarr, time.
        Not threaded.  Uses dmmask or dmthread directly.
        """

        dmarr = self.dmarr
        reltime = self.reltime
        minintersect = len(self.chans)

        dmt0arr = n.zeros((len(dmarr),len(reltime)), dtype='float64')
#        accummask = n.zeros(self.data.shape, dtype='bool')
        if self.data.shape[1] == len(self.chans):
            chans = self.chans
        else:
            chans = n.arange(self.nchan)

        for i in range(len(dmarr)):
            for j in range(len(reltime)):
                if self.usedmmask:    # slower by factor of 2 than dmtracks
                    dmmask = self.dmmask(dm=dmarr[i], t0=reltime[j])
                    if dmmask.sum() >= minintersect:               # ignore tiny, noise-dominated tracks
                        dmt0arr[i,j] = n.mean(n.abs (self.data * dmmask)[n.where(dmmask == True)])
#                   accummask = accummask + dmmask
                else:
                    dmtrack = self.dmtrack(dm=dmarr[i], t0=reltime[j])
                    if len(dmtrack[0]) >= minintersect:               # ignore tiny, noise-dominated tracks
                        dmt0arr[i,j] = n.mean(n.abs (self.data[dmtrack[0],dmtrack[1]]))
            print 'dedispersed for ', dmarr[i]

        self.dmt0arr = dmt0arr

#        ax = p.imshow(accummask, aspect='auto')
#        p.axis([-0.5,len(chans)+0.5,max(time),min(time)])


    def plotdmt0(self, sig=5., save=0):
        """calculates rms noise in dmt0 space, then plots circles for each significant point
        save=1 means plot to file.
        """
        dmarr = self.dmarr
        arr = self.dmt0arr
        reltime = self.reltime
        tbuffer = 7  # number of extra iterations to trim from edge of dmt0 plot

        # Trim data down to where dmt0 array is nonzero
        arreq0 = n.where(arr == 0)
        trimt = arreq0[1].min()
        arr = arr[:,:trimt - tbuffer]
        reltime = reltime[:trimt - tbuffer]
        print 'dmt0arr/time trimmed to new shape:  ',n.shape(arr), n.shape(reltime)

        # single iteration of sigma clip to find mean and std, skipping zeros
        mean = arr.mean()
        std = arr.std()
        print 'initial mean, std:  ', mean, std
        cliparr = n.where((arr < mean + 5*std) & (arr > mean - 5*std))
        mean = arr[cliparr].mean()
        std = arr[cliparr].std()
        print 'final mean, sig, std:  ', mean, sig, std

        # Recast arr as significance array
        arr = (arr - mean)/std

        # Detect peaks
        peaks = n.where(arr > sig)   # this is probably biased
        print 'peaks:  ', peaks

        p.clf()
        ax = p.imshow(arr, aspect='auto', origin='lower', interpolation='nearest', extent=(min(reltime),max(reltime),min(dmarr),max(dmarr)))
        p.colorbar()

        if peaks:
            for i in range(len(peaks[1])):
                ax = p.imshow(arr, aspect='auto', origin='lower', interpolation='nearest', extent=(min(reltime),max(reltime),min(dmarr),max(dmarr)))
                p.axis((min(reltime),max(reltime),min(dmarr),max(dmarr)))
                p.plot([reltime[peaks[1][i]]], [dmarr[peaks[0][i]]], 'o', markersize=2*arr[peaks[0][i],peaks[1][i]], markerfacecolor='white', markeredgecolor='blue', alpha=0.5)

        p.xlabel('Time (s)')
        p.ylabel('DM (pc/cm3)')
        p.title('Signal to Noise Ratio of Dedispersed Pulse')
        if save:
            p.savefig('plot_dmt0_%s.png' % (str(self.nskip)))


    def dedisperse2(self):
        """Integrates over data*dmmask or data at dmtrack for each pair of elements in dmarr, time.
        Uses threading.  SLOWER than serial.
        """

        dmarr = self.dmarr
        reltime = self.reltime

        self.dmt0arr = n.zeros((len(dmarr),len(reltime)), dtype='float64')
#        accummask = n.zeros(self.data.shape, dtype='bool')
        if self.data.shape[1] == len(self.chans):
            chans = self.chans
        else:
            chans = n.arange(self.nchan)

        threadlist = []
        for i in range(len(dmarr)):
            for j in range(len(reltime)):
                proc = worker(self, i, j)
                threadlist.append(proc)
                proc.start()
            print 'submitted for dm= ', dmarr[i]
        for proc in threadlist:
            proc.join()


#class worker(Thread):
#    
#    def __init__(self, pv, i, j):
#        Thread.__init__(self)
#        self.pv = pv
#        self.i = i
#        self.j = j
#
#    def run(self):
#        """Threadable unit for dedisperse2.
#        """
#
#        if self.pv.usedmmask:    # slower by factor of 2 than dmtracks
#            dmmask = self.pv.dmmask(dm=self.pv.dmarr[self.i], t0=self.pv.reltime[self.j])
#            if dmmask.sum() >= 5:               # ignore tiny, noise-dominated tracks
#                self.pv.dmt0arr[self.i,self.j] = n.mean(n.abs (self.pv.data * dmmask)[n.where(dmmask == True)])
#        else:
#            dmtrack = self.pv.dmtrack(dm=self.pv.dmarr[self.i], t0=self.pv.reltime[self.j])
#            if len(dmtrack[0]) >= 5:               # ignore tiny, noise-dominated tracks
#                self.pv.dmt0arr[self.i,self.j] = n.mean(n.abs (self.pv.data[dmtrack[0],dmtrack[1]]))


if __name__ == '__main__':
    # default stuff
    print 'Greetings, human.'
    print ''
    nints = 10000
    
    for nskip in range(nints*0.3,nints*10,nints*0.6):
        pv = poco('poco-crab0.mir', nints=nints, nskip=nskip)
        pv.prep()
        pv.dedisperse()
        pv.plotdmt0(save=1)

