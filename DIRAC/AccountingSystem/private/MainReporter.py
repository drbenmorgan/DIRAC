try:
  import hashlib
  md5 = hashlib
except:
  import md5
import re  
from DIRAC import S_OK, S_ERROR, gConfig
from DIRAC.ConfigurationSystem.Client.PathFinder import getServiceSection
from DIRAC.AccountingSystem.private.Policies import gPoliciesList
from DIRAC.AccountingSystem.private.Plotters.BaseReporter import BaseReporter as myBaseReporter
from DIRAC.AccountingSystem.private.ObjectLoader import loadObjects

class PlottersList:

  def __init__( self ):
    objectsLoaded = loadObjects( 'AccountingSystem/private/Plotters',
                                 re.compile( ".*[a-z1-9]Plotter\.py$" ),
                                 myBaseReporter )
    self.__plotters = {}
    for objName in objectsLoaded:
      self.__plotters[ objName[:-7] ] = objectsLoaded[ objName ]

  def getPlotterClass( self, typeName ):
    try:
      return self.__plotters[ typeName ]
    except KeyError:
      return None

class MainReporter:

  def __init__( self, db, setup ):
    self._db = db
    self.setup = setup
    self.csSection = getServiceSection( "Accounting/ReportGenerator", setup = setup )
    self.plotterList = PlottersList()

  def __calculateReportHash( self, reportRequest ):
    requestToHash = dict( reportRequest )
    granularity = gConfig.getValue( "%s/CacheTimeGranularity" % self.csSection, 300 )
    for key in ( 'startTime', 'endTime' ):
      epoch = requestToHash[ key ]
      requestToHash[ key ] = epoch - epoch % granularity
    md5Hash = md5.md5()
    md5Hash.update( repr( requestToHash ) )
    md5Hash.update( self.setup )
    return md5Hash.hexdigest()

  def generate( self, reportRequest, credDict ):
    typeName = reportRequest[ 'typeName' ]
    plotterClass = self.plotterList.getPlotterClass( typeName )
    if not plotterClass:
      return S_ERROR( "There's no reporter registered for type %s" % typeName )
    if typeName in gPoliciesList:
      retVal = gPoliciesList[ typeName ].checkRequest( reportRequest[ 'reportName' ],
                                                    credDict,
                                                    reportRequest[ 'condDict' ],
                                                    reportRequest[ 'grouping' ] )
      if not retVal[ 'OK' ]:
        return retVal
    reportRequest[ 'hash' ] = self.__calculateReportHash( reportRequest )
    plotter = plotterClass( self._db, self.setup, reportRequest[ 'extraArgs' ] )
    return plotter.generate( reportRequest )

  def list( self, typeName ):
    plotterClass = self.plotterList.getPlotterClass( typeName )
    if not plotterClass:
      return S_ERROR( "There's no plotter registered for type %s" % typeName )
    plotter = plotterClass( self._db, self.setup )
    return S_OK( plotter.plotsList() )