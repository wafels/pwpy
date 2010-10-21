#! /usr/bin/env python

"""= varcat -- Print values of UV variables.
& pkgw
: Tools
+
 This task scans through UV data and prints out the values of
 user-specified UV variables as they change. Use it to investigate the
 low-level properties of your UV data.

 There two groups of variables: the variables of interest, and
 "context" variables. A line is printed only when one of the
 variables of interest changes. When a line is printed, both
 the context variables and the variables of interest are shown. The
 variable values are shown in a column format.

 A variable of interest is said to have "changed" when a new entry for
 the variable appears in the UV data stream (according to the routine
 UVVARUPD). The new entry for the variable may have the same value as
 the previous entry, however.
 
 Array-valued variables are not well-handled at the moment.
 
< vis
 Multiple input datasets are supported by VARCAT.

@ vars
 A comma-separated list of variable names. A line containing the values
 of these variables is printed every time one of the variables
 changes. No default, and must be specified. 

@ context
 A comma-separated list of variable names. Whenever a line is printed,
 the values of these variables are printed as well. However, changes
 in the values of these variables do not trigger the printing of a
 line. Defaults to "time".

@ format
 A comma-separated list of formatting styles for the variables of
 interest. Each formatting style is associated with the corresponding
 variable named in the "vars" keyword. The formatting styles are:

 'default'    Python's string representation of the variable's
              value is used.
 'time'       The variable is treated as Julian date and
              formatted as a date and time.
 'baseline'   The variable is treated as a baseline number and
              is formatted as ANT1-ANT2.
 'pol'        The variable is treated as a FITS-encoded polarization
              number and is formatted as the string representation of
              that polarization: XX, RL, etc.
 'precise'    The values is printed out as a floating-point number
              with 18 decimal places of precision.
 '' (blank)   The most appropriate formatting style for the variable is
              used. For the UV variable "time", this is "time"; for
              "baseline", it is "baseline"; for "pol", it is "pol";
              for all others, it is "default".

 If there are fewer formats specified than variables, the extra
 variables use the "most-appropriate" style. It is an error to
 specify more formats than variables. Defaults to an empty list, i.e.,
 all variables use the most-appropriate style.

@ cformat
 Analogous to "format", but applied to the context variables. Defaults
 to an empty list, i.e. all context variables use the most-appropriate
 style.

< select

< stokes

< line

@ width
 The width of each output column, in characters. Default is 20.

@ options
 Multiple options can be specified, separated by commas, and
 minimum-match is used.

 'nocal'   Do not apply antenna gain corrections.

 'nopol'   Do not apply polarization leakage corrections.

 'nopass'  Do not apply bandpass shape corrections.

--
"""

import sys
import mirtask
from mirtask import uvdat, keys
from mirtask.util import die

ks = keys.KeySpec ()
ks.mkeyword ('vars', 'a', 64)
ks.mkeyword ('context', 'a', 64)
ks.mkeyword ('format', 'a', 64)
ks.mkeyword ('cformat', 'a', 64)
ks.keyword ('width', 'i', 20)
ks.uvdat ('dsl3', True)
opts = ks.process ()

if len (opts.vars) == 0:
    die ('no variables to print out were specified')

if len (opts.context) == 0:
    opts.context = ['time']

if len (opts.format) > len (opts.vars):
    die ('more formatting commands were specified than there are variables to print')
else:
    while len (opts.format) < len (opts.vars):
        opts.format.append ('')

if len (opts.cformat) > len (opts.context):
    die ('more context formatting commands were specified than there are'
         ' context variables to print')
else:
    while len (opts.cformat) < len (opts.context):
        opts.cformat.append ('')

# Formatting utilities

def fBaseline (val):
    return '%d-%d' % (mirtask.util.decodeBaseline (val))

formatters = {
    'time': mirtask.util.jdToFull,
    'baseline': fBaseline,
    'pol': mirtask.util.polarizationName,
    'precise': lambda v: '%.18e' % (v, ),
    'default': str
    }

autoFormat = {
    'time': 'time',
    'baseline': 'baseline',
    'pol': 'pol'
    }

# Header row

s = ''
for v in opts.context + opts.vars:
    s += v.ljust (opts.width)
print s

# Print the variables!

curFile = None

for dIn, p, d, f in uvdat.read ():
    if dIn is not curFile:
        uvt = dIn.makeVarTracker ()
        uvt.track (*opts.vars)

        vinfo = []
        
        for v, fname in zip (opts.context + opts.vars, opts.cformat + opts.format):
            tup = dIn.probeVar (v)

            if tup is None:
                die ('no such variable "%s" in dataset %s!', v, dIn.name)

            vtype = tup[0]
            vlen = tup[1]

            # How should we format this variable into a string?

            if fname == '':
                if v in autoFormat: fname = autoFormat[v]
                else: fname = 'default'
                
            formatter = formatters[fname]

            # How do we obtain the value of this var when it's updated?
            
            if vtype == 'a': get = lambda: dIn.getVarString (v)
            elif vtype == 'r': get = lambda: dIn.getVarFloat (v, vlen)
            elif vtype == 'i': get = lambda: dIn.getVarInt (v, vlen)
            elif vtype == 'd': get = lambda: dIn.getVarDouble (v, vlen)
            elif vtype == 'c': get = lambda: dIn.getVarComplex (v, vlen)
            else:
                die ('unhandled or ungettable variable type "%s" for "%s" in '
                     'dataset %s!', vtype, v, dIn.name)

            # Ok, we have all the info we need. For some reason I need to stuff
            # vlen into the tuple, otherwise old values seem to get thrown away or
            # something. Maybe a single instance of vlen is getting captured and
            # reused each time unless we stuff it in a tuple to force a new variable
            # to be used?
            
            vinfo.append ((v, vlen, get, formatter))
            
        curFile = dIn

    if not uvt.updated (): continue

    s = ''

    for (v, vlen, get, formatter) in vinfo:
        #print v, get, formatter, vtype, vlen
        if vlen == 1:
            f = formatter (get ())
        else:
            f = formatter (get ()[1])

        if len (f) < opts.width:
            s += f.ljust (opts.width)
        else:
            s += '%s... ' % (f[0:16])

    print s
