'''
/* IBM_PROLOG_BEGIN_TAG                                                   */
/* This is an automatically generated prolog.                             */
/*                                                                        */
/* zimonGrafanaIntf.py                                                    */
/*                                                                        */
/* Licensed Materials - Property of IBM                                   */
/*                                                                        */
/* Restricted Materials of IBM                                            */
/*                                                                        */
/* (C) COPYRIGHT International Business Machines Corp. 2017               */
/* All Rights Reserved                                                    */
/*                                                                        */
/* US Government Users Restricted Rights - Use, duplication or            */
/* disclosure restricted by GSA ADP Schedule Contract with IBM Corp.      */
/*                                                                        */
/* IBM_PROLOG_END_TAG                                                     */
Created on Apr 4, 2017

@author: hwassman
'''

import cherrypy
import json
import re
import argparse
import logging.handlers
import sys


try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from queryHandler.Query import Query
from queryHandler.QueryHandler import QueryHandler2 as QueryHandler
from queryHandler.Topo import Topo
from collections import defaultdict
import time


# global variable to store and use topo data module wide
__TOPO__ = None
__TIMER__ = time.clock if sys.platform == 'win32' else time.time



class MetadataHandler():

    def __init__(self):
        self.qh = None
        self.logger = None
        self.server = '127.0.0.1'
        self.port = 9084

    def init(self, logger, server, port=9084):
        self.qh = None
        self.logger = logger
        self.server = server
        self.port = port

        return self.initializeTables()



    def initializeTables(self):
        '''Read the topology from ZIMon and (re-)construct
        the tables for metrics, keys, key elements (tag keys)
        and key values (tag values)'''
        
        if not self.qh: 
            try:
                self.qh = QueryHandler(self.server, self.port, self.logger)
            except Exception as e:
                self.logger.error('mdHandler: Could not initialize the QueryHandler Reason: %s' % e)
                return -1
            
        try: 
            global __TOPO__
            global __TIMER__
            tstart = __TIMER__()
            __TOPO__ = Topo(self.qh)
            tend = __TIMER__()
            foundItems = len(__TOPO__.topo)
            sensors = __TOPO__.topo['metricsMap'].keys()
            self.logger.info("Successfully retrieved MetaData for %s parent components totally, and the following sensors:\n %s" % (foundItems-1,", ".join(sensors)))
            self.logger.debug("Received metadata for the following parent components: %s" % ", ".join(__TOPO__.topo.keys()))
            self.logger.debug("Metadata retireval took %s seconds" % (tend-tstart))
            print("Successfully retrieved MetaData for sensors:\n\n %s \n" % "\t".join(sensors))
        except Exception as e:
                self.logger.error('mdHandler: Could not initializeTables Reason: %s' % e)
                return -2
        
        return 0



class GetHandler(object):
    exposed = True
        
    def __init__(self):
        pass
     
    def init(self, logger, mdHandler, server, port=9084):
        self.logger = logger
        self.mdHandler = mdHandler
        self.server = server
        self.port = port                 



    @cherrypy.tools.json_out()
    def GET(self, **params):
        '''Handle partial URLs such as /api/suggest?q=cpu_&type=metrics 
        where type is one of metrics, tagk or tagv 
        or
        Handle /api/search/lookup/m=cpu_idle{node=*}
        where m is the metric and optional term { tagk = tagv } qualifies the lookup.
        For more details please check openTSDB API (version 2.2 and higher) documentation for
        /api/lookup 
        /api/search/lookup 
        '''
        
        resp = []
        
        global __TOPO__
        if __TOPO__ is None:
            rc = self.mdHandler.initializeTables()
            if rc != 0:
                raise cherrypy.HTTPError(500, 'Failed to update metadata, please check log file for more details.')

        
        if 'suggest' in cherrypy.request.script_name:  
            if params.get('q'):  # /api/suggest
                searchStr = params['q'].strip()
                # if '*' and tagv, then it denotes a grouping key value: do not process
                if not(searchStr == '*' and params['type'] == 'tagv'):
                    # Since grafana sends the candidate string quickly, one character at a time, it
                    # is likely that the reg exp compilation will fail.
                    try:
                        regex = re.compile("^" + searchStr + ".*")
                    except re.error:
                        self.logger.debug("ERROR: Search for %s did cause exception: %s" %(searchStr, str(re.error)))
                        regex = None  # failed to compile, return empty response
                    if regex:
                        try: 
                            if params['type'] == 'metrics':
                                resp = sorted([m.group(0) for item in __TOPO__.getAllSupportedMetrics() for m in [regex.search(item)] if m])
                            elif params['type'] == 'tagk':
                                resp = sorted([m.group(0) for item in __TOPO__.getAllSupportedTagNames() for m in [regex.search(item)] if m])
                            elif params['type'] == 'tagv':
                                resp = sorted([m.group(0) for item in __TOPO__.getAllSupportedTagValues() for m in [regex.search(item)] if m])
                        except Exception as e:
                            self.logger.error('Server internal error occurred. Reason: %s' % str(e))
                            raise cherrypy.HTTPError(500, 'Internal Server Error. Please check logs for more details.')
                    
        elif 'lookup' in cherrypy.request.script_name:
            if params.get('m'):  # /api/search/lookup
                filterBy = None
                queryTags = []
                resultTags = []


                try: 
                    params_list = re.split(r'\{(.*)\}', params['m'].strip())
                    searchMetric = params_list[0]
                    if searchMetric and str(searchMetric).strip() not in __TOPO__.getAllSupportedMetrics():
                        self.logger.debug("ERROR: Lookup for metric  %s didn't return any results." % searchMetric)
                    else:
                        if len(params_list) > 1:
                            attr = params_list[1]
                            filterBy = dict(x.split('=') for x in attr.split(','))
                        identifiersMap =__TOPO__.getIdentifiersMapForQueryAttr('metric', searchMetric, filterBy)
                    
                        if identifiersMap:
                            for identifiers in identifiersMap:
                                d = defaultdict(dict)
                                for key in identifiers.keys():
                                    d['tags'][key]= identifiers[key]
                                    if d not in resultTags:
                                        resultTags.append(d)

                    if filterBy:
                        for key, value in filterBy.items():
                            tmp = {'key' : key, 'value' : value}
                            queryTags.append(tmp)
                        
                except Exception as e:
                    self.logger.error('Server internal error occurred. Reason: %s' % str(e))
                    raise cherrypy.HTTPError(500, 'Internal Server Error. Please check logs for more details.')

                resp = {}
                resp['type'] = "LOOKUP"
                resp['metric'] = searchMetric
                resp['tags'] = queryTags
                resp['results'] = resultTags

        elif 'update' in cherrypy.request.script_name:
            rc = self.mdHandler.initializeTables()
            resp = {}
            if rc == 0:
                resp['msg'] = 'metadata successfully updated.'
            else:
                resp['msg'] = 'failed to update metadata, please check log.'
            resp['rc'] = rc
            
        elif 'aggregators' in cherrypy.request.script_name:
            resp = [ "noop", "sum", "avg", "max", "min", "rate"]

        elif 'config/filters' in cherrypy.request.script_name:
            supportedFilters = {}
            filterDesc = {}
            filterDesc['description'] = '''Accepts an exact value or a regular expressions and matches against  
            values for the given tag. The value can be omitted if the filter is used to specify groupBy on the tag only.'''
            filterDesc['examples'] = '''node=pm_filter(machine1), node=pm_filter(machine[1-6]), node=pm_filter(m1|m2),
            node=pm_filter(mac.*), node=pm_filter((?!^z).*)'''
            supportedFilters['pm_filter'] = filterDesc
            resp = supportedFilters
        
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        return resp        
    
    
    
class PostHandler(object):
    exposed = True
    
    def init(self, logger, mdHandler, server, port=9084):
        self.logger = logger
        self.mdHandler = mdHandler
        self.server = server
        self.port = port



    def getTimeMultiplier(self, timeunit):
        '''Translate OpenTSDB time units, ignoring ms (milliseconds)'''
        return {
            's' : 1,
            'm' : 60,
            'h' : 3600,
            'd' : 86400,
            'w' : 604800,
            'n' : 2628000,
            'y' : 31536000,
            }.get(timeunit, -1)



    def retrieveData(self, zimonQuery, qh):
        
        self.logger.info('execute query: %s', str(zimonQuery))
        res = qh.runQuery(zimonQuery)
        
        if res == None:
            return

        columnValues = defaultdict(dict)
        for row in res.rows:
            for value, columnInfo in zip(row.values, res.columnInfos):
                columnValues[columnInfo][row.tstamp] = value
        return columnValues



    def validateQueryFilters(self, metricName, query):
        notValid = False
        msg = "Filter validation fails.It might affect query results. Please check logs for more information"

        # check filterBy settings
        if query.filters:
            filterBy = dict(x.split('=') for x in query.filters)
            identifiersMap = __TOPO__.getIdentifiersMapForQueryAttr('metric', metricName, filterBy)
            if not identifiersMap:
                self.logger.error("ERROR: No component entry found for the specified \'filterby\' attribute")
                return (notValid, msg)

        # check groupBy settings
        if query.groupby:
            filter_keys = __TOPO__.getAllFilterKeysForMetric(metricName)
            if not filter_keys:
                self.logger.error("ERROR: In the current setup the group aggregation \'groupby\' is not possible. ")
                return (notValid, msg)
            groupKeys = query.groupby.split(',')
            if not all(key in filter_keys for key in groupKeys):
                self.logger.error("ERROR: The specified \'groupby\' attribute is invalid.\n\
The following group keys applicable for the selected metric(measurement): \n\
" + str(", ".join(filter_keys)))
                return (notValid, msg)
        
        return (True, '')



    def createZimonQuery(self, q, start, end):
        query = Query()
        query.normalize_rates = False
        #aggregation = 'nop'
        bucketSize = 1  # default
        
        inMetric = q.get('metric')
        if not inMetric in __TOPO__.getAllSupportedMetrics():
            self.logger.error('Metric %s not found. Please check if the corresponding sensor is configured' % inMetric)
            raise cherrypy.HTTPError(404, 'Metric {0} cannot be found'.format(inMetric))
        else:
            #self.logger.info("Received query request for 'metric': %s, 'start': %s, 'end': %s " % (inMetric, str(start), str(end)))
            self.logger.info("Received query request for 'query': %s, 'start': %s, 'end': %s " % (str(q), str(start), str(end)))

        # add tagName or metric using the same method. There is no 'NOOP' option in openTSDB            
        query.addMetric(inMetric, q.get('aggregator'))
        
        if q.get('filters'):
            try:
                for f in q.get('filters'):
                    tagk = f.get('tagk')
                    if tagk:
                        if f.get('groupBy'):
                            query.addGroupByMetric(tagk)
                        if f.get('filter'):
                            query.addFilter(tagk, f.get('filter'))
                        
            except  ValueError as e:
                self.logger.error('ERROR: Parsing filers parameters from the request query. Reason: %s', str(e))
                raise cherrypy.HTTPError(400, 'Query request could not be proceed. Reason: %s', str(e))

        # set time bounds
        if end:
            query.setTime(str(int(int(start) / 1000)),
                                     str(int(int(end) / 1000)))
        else:
            query.setTime(str(int(int(start) / 1000)), '')
            
        # set bucket size
        if q.get('downsample'):
            bucketSize = self.calc_bucketSize(q.get('downsample'))
            self.logger.info('Based on requested downsample value: %s the bucketsize will be set: %s' %(str(q.get('downsample')), str(bucketSize)))
        query.setBucketSize(bucketSize)
        
        return query



    def formatQueryResponse(self, inputQuery, results, showQuery=False, globalAnnotations=False):
        
        resList = []
        

        for columnInfo, dps in results.items():
            if columnInfo.name.find(inputQuery.get('metric')) == -1:
                    self.logger.error('Inconsistent metric name. Received results for metric name: %s. Requested data for metric: %s' % (str(columnInfo.name), str(inputQuery.get('metric'))) )
                    raise cherrypy.HTTPError(404, 'Inconsistent reuest and response data. Please check log messages for more information')
                
            res = dict.fromkeys(['metric','tags','aggregatedTags','dps'])
            res['metric'] = inputQuery.get('metric')
            res['dps'] = dps
            res['tags']= {}
            res['aggregatedTags']= []
            
            if len(columnInfo.keys) > 1:
                res['aggregatedTags'] = __TOPO__.getAllFilterKeysForMetric(inputQuery.get('metric'))
            
            elif len(columnInfo.keys) == 1:
                ident = [columnInfo.parents]
                ident.extend(columnInfo.identifiers)
                self.logger.debug('Single ts identifiers: %s' % str(', '.join(ident)))
                filtersMap =__TOPO__.getAllFilterMapsForMetric(columnInfo.name)
                for filtersDict in filtersMap:
                    if all((value in filtersDict.values()) for value in ident):
                        self.logger.debug('Keys found for identifiers in filtersMap: %s' % str(', '.join(filtersDict.keys())))
                        res['tags'] = filtersDict
                
            if showQuery:
                self.logger.debug('showQuery enabled')
                res['query']= inputQuery
                
            if globalAnnotations:
                self.logger.debug('globalAnnotations enabled')
                res['globalAnnotations'] = []
            
            cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            resList.append(res)

        return resList



    def calc_bucketSize(self, downsample):
        bucketSize = 1  # default
        bstr = downsample
        if '-' in bstr:
            x = re.split('(\d+)', bstr[:bstr.find('-')])
            if len(x) == 3:  # if not 3, then split failed
                if x[1]:  # there is a time value
                    if x[1].isdigit():
                        timeMultiplier = -1
                        if x[2]:  # there is a unit
                            timeMultiplier = self.getTimeMultiplier(x[2])
                            if timeMultiplier == -1:
                                bucketSize = int(x[1])
                            else:
                                bucketSize = int(x[1]) * timeMultiplier
                        else:  # no units
                            bucketSize = int(x[1])
                            
        return bucketSize



    @cherrypy.config(**{'tools.json_in.force' : False})
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        ''' Process POST. tools.json_in.force is set to False for 
        compatability between versions of grafana < 3 and version 3.'''

        # read query request parameters
        jreq = cherrypy.request.json

        qh = self.mdHandler.qh
        resp = []
        
        if jreq.get('queries') == None:
            self.logger.error('Empty query received, returning an error response')
            raise cherrypy.HTTPError(400, 'Empty query received') 

        # A request query can include more than one sub query and any mixture of the two types
        # For more details please check openTSDB API (version 2.2 and higher) documentation for
        # /api/query
        for q in jreq.get('queries'):
            if qh == None:
                try:
                    qh = QueryHandler(self.server, self.port, self.logger)
                except Exception as e:
                    self.logger.error('Could not initialize the QueryHandler, PostHandler::POST failed (errno: {}, errmsg: {})'.format(e.args[0], e.args[1]))
                    return []
                
            global __TOPO__
            if __TOPO__ is None:
                rc = self.mdHandler.initializeTables()
                if rc != 0:
                    raise cherrypy.HTTPError(500, 'Failed to update metadata, please check log file for more details.')

            query = self.createZimonQuery( q, jreq.get('start'), jreq.get('end'))
            if self.logger.level == logging.DEBUG:
                (valid, msg) = self.validateQueryFilters(q.get('metric'), query)
                if not valid:
                    raise cherrypy.HTTPError(404, msg)
            columnValues = self.retrieveData(query, qh)
            if columnValues == None:
                self.logger.debug('Error: query returning empty results')
                if len(jreq.get('queries')) == 1:
                    raise cherrypy.HTTPError(404, 'No data available for the requested query')
                else:
                    continue;
                
            res = self.formatQueryResponse(q, columnValues, jreq.get('showQuery'), jreq.get('globalAnnotations'))
            resp.extend(res)

        qh = None     
        return resp        



    def OPTIONS(self):
        # print('options_post')
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Accept'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800



def processFormJSON(entity):
    ''' Used to generate JSON when the content
    is of type application/x-www-form-urlencoded. Added for grafana 3 support'''
    # print('processFormJSON')

    body = entity.fp.read()
    if len(body) > 0:
        cherrypy.serving.request.json = json.loads(body.decode('utf-8'))
    else:
        cherrypy.serving.request.json = json.loads('{}')



def configureLogging(args):
    # prepare the logger
    logger = logging.getLogger('zimonGrafanaIntf')
    rfhandler = logging.handlers.RotatingFileHandler(args['l'], 'a', 1000000, 5)  # 5 x 1M files
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rfhandler.setFormatter(formatter)
    logger.addHandler(rfhandler)
    log_level = int(args['c'])
    if log_level in [10, 20, 30, 40]:
        logger.setLevel(log_level)
    else:
        logger.setLevel(logging.INFO)
        logger.warn('Given log level is incorrect, will assume default (20: INFO)')
    logger.propagate = False  # prevent propagation to default (console) logger
    
    return logger
    
    
    
def updateCherrypyConf(args):
    
    globalConfig = {
                    'global' : {
                                'server.socket_host': '0.0.0.0',
                                'server.socket_port' : args['p'],
                                'server.socket_timeout' : 60,  # increase timeout to 60s
                                'request.show_tracebacks' : False,
                                'log.screen' : False,  # turn off logging to console 
                                'log.access_file': "cherrypy_access.log",
                                'log.error_file': "cherrypy_error.log",
                                'tools.encode.on' : True,
                                'tools.encode.encoding' : 'utf-8'}}
    cherrypy.config.update(globalConfig)

    if args['p'] == 8443:
        sslConfig = {
                    'global' : {
                                'server.ssl_module' : 'builtin',
                                'server.ssl_certificate' : args['k']+"/cert.pem",
                                'server.ssl_private_key' : args['k']+"/privkey.pem" }}
        cherrypy.config.update(sslConfig)
        
        
    
def main(argv):
    
    serverDefault = ''
    # parse input arguments
    parser = argparse.ArgumentParser('python zimonGrafanaIntf.py')
    parser.add_argument('-s', "-server", action="store", default=serverDefault, help='name or ip address of the ZIMon collector (Required)')
    parser.add_argument('-P', '-serverPort', action="store", type=int, default=9084, help='ZIMon collector port number (Default: 9084)')
    parser.add_argument('-l', '-logFile', action="store", default="./zserver.log", help='location of the log file (Default: ./zserver.log')
    parser.add_argument('-c', '-logLevel', action="store", default=logging.INFO, help='log level 10 (DEBUG), 20 (INFO), 30 (WARN), 40 (ERROR) (Default: 20)')
    parser.add_argument('-p', '-port', action="store", type=int, default=4242, help='port number to listen on (Default: 4242)')
    parser.add_argument('-k', '-keyPath', action="store", help='Directory path of privkey.pem and cert.pem file location(Required only for HTTPS port 8443)');

    args = vars(parser.parse_args(argv))
    
    # prepare the logger
    logger = configureLogging(args)
    
    #check pmcollector ip
    if args['s'] == serverDefault:
        logger.error('Server name not specified, quitting')
        print('Server name not specified, quitting')
        return
    
    # prepare metadata
    mdHandler = MetadataHandler()
    if mdHandler.init(logger, args['s'], args['P']) != 0:
        print('Failed to initialize MetadataHandler, please check log file for reason')
        return
    
    if args['p'] == 8443 and not args['k']:
            print('Missing mandatory parameters, quitting')
            return
    #prepare cherrypy server configuration
    updateCherrypyConf(args)

    ph = PostHandler()
    ph.init(logger, mdHandler, args['s'], args['P'])
    cherrypy.tree.mount(ph, '/api/query',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                          'request.body.processors' : { 'application/x-www-form-urlencoded': processFormJSON }
                           }
                         }
                        )
    
    gh = GetHandler()
    gh.init(logger, mdHandler, args['s'], args['P'])
    # query for metric name (openTSDB: zimon extension returns keys as well)
    cherrypy.tree.mount(gh, '/api/suggest',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                         }
                        )
    # query for tag name and value, given a metric (openTSDB)
    cherrypy.tree.mount(gh, '/api/search/lookup',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                         }
                        )
    # query to force update of metadata (zimon feature)
    cherrypy.tree.mount(gh, '/api/update',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                         }
                        )
    # query for list of aggregators (openTSDB)
    cherrypy.tree.mount(gh, '/api/aggregators',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                         }
                        )

    # query for list of filters (openTSDB)
    cherrypy.tree.mount(gh, '/api/config/filters',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                         }
                        )
    
    
    print("Your system is running python version: %s and cherryPy version: %s" % ( sys.version, cherrypy.__version__))
    logger.info("START:Initial cherryPy server engine start have been invoked. Python version: %s, cherryPy version: %s." % ( sys.version, cherrypy.__version__))
    
    try:
        cherrypy.engine.start()
        print("server started")
        cherrypy.engine.block()
    except (ImportError, IOError, KeyboardInterrupt, Exception):
        #msg = "server stopping, please check logs for more details"
        #logger.error("STOPPING: Server request could not be proceed. Reason: %s" % e)
        cherrypy.engine.stop()
        cherrypy.engine.exit()


        
    
    ph = None
    gh = None

    print("server stopped")

        
if __name__ == '__main__':
    main(sys.argv[1:])
    
    

    
