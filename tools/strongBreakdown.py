#!/usr/bin/env python
import os
import sys
import yaml
import ROOT as r
import numpy as np
from math import sqrt
from collections import OrderedDict
from scipy.optimize import root, fsolve

xsec = yaml.safe_load(open('tools/STXSCrossSections.yml'))['CrossSections']
poiNames = yaml.safe_load(open('tools/stxsNames.yml'))

usemu = ('mu' in sys.argv[2::])

# ---------------------------------------------------------------
def ordered_load(stream, Loader=yaml.SafeLoader, object_pairs_hook=OrderedDict):
  class OrderedLoader(Loader):
    pass
  def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return object_pairs_hook(loader.construct_pairs(node))
  OrderedLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping)
  return yaml.load(stream, OrderedLoader)


# Get User Arguments
# ---------------------------------------------------------------
if (len(sys.argv) <= 1):
  print '%s Config' % sys.argv[0]; sys.exit()

#config = yaml.safe_load(open(sys.argv[1]))
config = ordered_load(open(sys.argv[1]))
options = config['Options']

npts = options['NPoints']
ModelName = options['ModelName']
pois = config['ParametersOfInterest']

table = []

results = { p: {}  for p in pois }
for POIName in pois:
  POITitle = config['ParametersOfInterest'][POIName][2]

  print ''
  print POIName

  tgs = {}
  for error in ['TOTAL','THEO','STAT']:
    # Get points
    # ---------------------------------------------------------------
    minNLL, muhat, pts = -999, 1.0, []

    tc = r.TChain('nllscan')
    dirPATH = 'output/%s/%s/%s' % (ModelName,POIName,error)
    for i in xrange(npts): tc.AddFile( os.path.join(dirPATH,'result_%d.root'%i) )

    for ievt in xrange(npts):
      tc.GetEntry(ievt)
      poiVal = getattr(tc,POIName)
      if (ievt==0):
        minNLL = tc.nll
        muhat = poiVal
      if tc.status:
        print 'WARNING : FIT FAILED @ %s = %f. Skipping Point.' % (POIName, poiVal), error
        continue
      pts.append( (poiVal, 2*(tc.nll-minNLL)) )

    pts.sort( key=lambda tup: tup[0] )
    xmin = min(pts,key=lambda x:x[0])[0]
    xmax = max(pts,key=lambda x:x[0])[0]

    xmin = config['ParametersOfInterest'][POIName][0]
    xmax = config['ParametersOfInterest'][POIName][1]

    # Fill TGraphs
    # ---------------------------------------------------------------
    tgs[error] = r.TGraph()
    tg = tgs[error]
    for i in xrange(len(pts)):
      tg.SetPoint( i, pts[i][0], pts[i][1] )

    # Get spline and find 1 sigma and 2 sigma intercepts
    # ---------------------------------------------------------------
    width = (xmax-xmin)
    sp = r.TSpline3('s',tg)
    x0  = root(lambda x : sp.Eval(x), x0=muhat).x[0]
    x1p = root(lambda x: np.abs(1 - sp.Eval(x)), x0=(xmax - 0.2*width)).x[0]
    x1m = root(lambda x: np.abs(1 - sp.Eval(x)), x0=(xmin + 0.2*width)).x[0]
    err = [ abs(x0-x1p), -abs(x0-x1m) ]

    print '%10s - %.2f   %.2f   %.2f  (%.2f, %.2f)' % (error, x0, x1p, x1m, (xmax - 0.1*width), (xmin + 0.1*width))

    #print error
    #print ' %20s = %.2f +/- (%+.2f, %+.2f)' % ( POIName, x0, err[0], err[1] )
    results[POIName][error] = ( x0, err[0], err[1] )

  # Plot debugging
  # -----------------------------------------
  #if ('qq2Hqq_pTjet1_gt200' in POIName):
  #  tgs['STAT'].SetLineColor( r.kRed )
  #  tgs['TOTAL'].Draw('AC')
  #  tgs['STAT'].Draw('C SAME')
  #  raw_input('done?')

print ''
print ''

## Print output
template  = '%s &= %.2f\ ^{%+.2f}_{%+.2f}\ fb'
template += ' = %.2f\ ^{%+.2f}_{%+.2f}\,\mathrm{(stat.)}'
template += '\ ^{%+.2f}_{%+.2f}\,\mathrm{(exp.)}'
template += '\ ^{%+.2f}_{%+.2f}\,\mathrm{(theory)}\ fb\\\\'
if usemu: template = template.replace('\ fb','')

for POIName in pois:
  x0,  totHI,  totLO = results[POIName]['TOTAL']
  x0,  sthHI,  sthLO = results[POIName]['THEO']
  _,  statHI, statLO = results[POIName]['STAT']

  status = ''
  if (abs(sthHI) > abs(totHI) or abs(sthLO) > abs(totLO) or abs(statHI) > abs(sthHI) or abs(statLO) > abs(sthLO)):
    status = '***'

  expHI =  sqrt( abs( totHI**2 - sthHI**2 ) )
  expLO = -sqrt( abs( totLO**2 - sthLO**2 ) )

  theoHI =  sqrt( abs( sthHI**2 - statHI**2 ) )
  theoLO = -sqrt( abs( sthLO**2 - statLO**2 ) )

  POIName = POIName.replace('mu_','')

  #x0 = 1
  if (POIName in xsec) and not usemu:
    xsecSM = xsec[POIName]
    x0     *= xsecSM
    totHI  *= xsecSM
    totLO  *= xsecSM
    expHI  *= xsecSM
    expLO  *= xsecSM
    theoHI *= xsecSM
    theoLO *= xsecSM
    statHI *= xsecSM
    statLO *= xsecSM

  name = poiNames[POIName]
  print template % ( name, x0, totHI, totLO, x0, statHI, statLO, expHI, expLO, theoHI, theoLO), status


#print ''
#print 'Latex Formatted: \n'
#for line in table: print line
#print ''

