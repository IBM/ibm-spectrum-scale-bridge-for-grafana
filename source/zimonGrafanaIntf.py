'''
##############################################################################
# Copyright 2019 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################

Created on Apr 4, 2017

@author: HWASSMAN
'''

import cherrypy
import json
import re
import argparse
import logging.handlers
import sys
import socket
import os

from queryHandler.Query import Query
from queryHandler.QueryHandler import QueryHandler2 as QueryHandler
from queryHandler.Topo import Topo
from queryHandler import SensorConfig
from collections import defaultdict
from timeit import default_timer as timer


ERR = {400: 'Bad Request',
       404: 'Not Found',
       500: 'Internal Server Error. Please check logs for more details.'}

MSG = {'IntError': 'Server internal error occurred. Reason: {}',
       'sysStart': 'Initial cherryPy server engine start have been invoked. Python version: {}, cherryPy version: {}.',
       'MissingParm': 'Missing mandatory parameters, quitting',
       'KeyPathError': 'KeyPath directory not found, quitting',
       'CertError': 'Missing certificates in tht specified keyPath directory, quitting',
       'CollectorErr': 'Failed to initialize connection to pmcollector, quitting',
       'MetaError': 'Metadata could not be retrieved. Check log file for more details, quitting',
       'MetaSuccess': 'Successfully retrieved MetaData',
       'QueryError': 'Query request could not be proceed. Reason: {}',
       'SearchErr': 'Search for {} did cause exception: {}',
       'LookupErr': 'Lookup for metric {} did not return any results',
       'FilterByErr': 'No component entry found for the specified \'filterby\' attribute',
       'GroupByErr': 'In the current setup the group aggregation \'groupby\' is not possible.',
       'MetricErr': 'Metric {0} cannot be found. Please check if the corresponding sensor is configured',
       'InconsistentParams': 'Received parameters {} inconsistent with request parameters {}',
       'SensorDisabled': 'Sensor for metric {} is disabled',
       'NoData': 'Empty results received',  # Please check the pmcollector is properly configured and running.
       'BucketsizeChange': 'Based on requested downsample value: {} the bucketsize will be set: {}',
       'BucketsizeToPeriod': 'Bucketsize will be set to sensors period: {}',
       'ReceivedQuery': 'Received query request for query:{}, start:{}, end:{}',
       'RunQuery': 'Execute zimon query: {}',
       'AttrNotValid': 'Invalid attribute:{}',
       'AllowedAttrValues': 'For attribute {} applicable values:{}',
       'ReceivAttrValues': 'Received {}:{}',
       'TimerInfo': 'Processing {} took {} seconds',
       'Query2port': 'For better bridge performance multithreaded port {} will be used',
       'CollectorConnInfo': 'Connection to the collector server established successfully'
       }


class MetadataHandler():

    def __init__(self, logger, server, port=9084):
        self.__qh = None
        self.__sensorsConf = None
        self.__metaData = None
        self.logger = logger
        self.server = server
        self.port = port

        self.__initializeTables()

    @property
    def qh(self):
        if not self.__qh:
            self.__qh = QueryHandler(self.server, self.port, self.logger)
        return self.__qh

    @property
    def SensorsConfig(self):
        if not self.__sensorsConf or len(self.__sensorsConf) == 0:
            self.__sensorsConf = SensorConfig.readSensorsConfigFromMMSDRFS(self.logger)
        return self.__sensorsConf

    @property
    def metaData(self):
        return self.__metaData

    def __initializeTables(self):
        '''Read the topology from ZIMon and (re-)construct
        the tables for metrics, keys, key elements (tag keys)
        and key values (tag values)'''

        self.__qh = QueryHandler(self.server, self.port, self.logger)
        self.__sensorsConf = SensorConfig.readSensorsConfigFromMMSDRFS(self.logger)
        tstart = timer()
        self.__metaData = Topo(self.qh.getTopology())
        tend = timer()
        if not (self.metaData and self.metaData.topo):
            raise ValueError(MSG['NoData'])
        foundItems = len(self.metaData.allParents) - 1
        sensors = self.metaData.sensorsSpec.keys()
        self.logger.info(MSG['MetaSuccess'])
        self.logger.info(MSG['ReceivAttrValues'].format('parents totally', foundItems))
        self.logger.debug(MSG['ReceivAttrValues'].format('parents', ", ".join(self.metaData.allParents)))
        self.logger.info(MSG['ReceivAttrValues'].format('sensors', ", ".join(sensors)))
        self.logger.info(MSG['TimerInfo'].format('Metadata', str(tend - tstart)))

    def update(self):
        '''Read the topology from ZIMon and update
        the tables for metrics, keys, key elements (tag keys)
        and key values (tag values)'''

        tstart = timer()
        self.__metaData = Topo(self.qh.getTopology())
        tend = timer()
        if not (self.metaData and self.metaData.topo):
            self.logger.error(MSG['NoData'])  # Please check the pmcollector is properly configured and running.
            raise cherrypy.HTTPError(404, MSG[404])
        self.logger.info(MSG['MetaSuccess'])
        self.logger.debug(MSG['ReceivAttrValues'].format('parents', ", ".join(self.metaData.allParents)))
        self.logger.debug(MSG['TimerInfo'].format('Metadata', str(tend - tstart)))
        return({'msg': MSG['MetaSuccess']})


class GetHandler(object):
    exposed = True

    def __init__(self, logger, mdHandler):
        self.logger = logger
        self.__md = mdHandler

    @property
    def md(self):
        return self.__md

    @property
    def qh(self):
        return self.__md.qh

    @property
    def TOPO(self):
        return self.__md.metaData

    def __getSuggest(self, params):
        resp = []

        if params.get('q'):
            searchStr = params['q'].strip()
            # if '*' and tagv, then it denotes a grouping key value: do not process
            if not(searchStr == '*' and params['type'] == 'tagv'):
                # Since grafana sends the candidate string quickly, one character at a time, it
                # is likely that the reg exp compilation will fail.
                try:
                    regex = re.compile("^" + searchStr + ".*")
                except re.error:
                    self.logger.debug(MSG['SearchErr'].format(searchStr, str(re.error)))
                    regex = None  # failed to compile, return empty response
                if regex:
                    try:
                        if params['type'] == 'metrics':
                            resp = sorted([m.group(0) for item in self.TOPO.getAllEnabledMetricsNames for m in [regex.search(item)] if m])
                        elif params['type'] == 'tagk':
                            resp = sorted([m.group(0) for item in self.TOPO.getAllAvailableTagNames for m in [regex.search(item)] if m])
                        elif params['type'] == 'tagv':
                            resp = sorted([m.group(0) for item in self.TOPO.getAllAvailableTagValues for m in [regex.search(item)] if m])
                    except Exception as e:
                        self.logger.exception(MSG['IntError'].format(str(e)))
                        raise cherrypy.HTTPError(500, ERR[500])
        return resp

    def __getLookup(self, params):

        if params.get('m'):
            try:
                params_list = re.split(r'\{(.*)\}', params['m'].strip())
                searchMetric = params_list[0]
                if searchMetric and str(searchMetric).strip() not in self.TOPO.getAllEnabledMetricsNames:
                    self.logger.debug(MSG['LookupErr'].format(searchMetric))
                    return {}
                else:
                    filterBy = None
                    if len(params_list) > 1:
                        attr = params_list[1]
                        filterBy = dict(x.split('=') for x in attr.split(','))
                    identifiersMap = self.TOPO.getIdentifiersMapForQueryAttr('metric', searchMetric, filterBy)
                    res = LookupResultObj(searchMetric)
                    res.parseResultTags(identifiersMap)
                    res.parseRequestTags(filterBy)
                    resp = res.__dict__

            except Exception as e:
                self.logger.exception(MSG['IntError'].format(str(e)))
                raise cherrypy.HTTPError(500, MSG[500])

        return resp

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

        # /api/suggest
        if 'suggest' in cherrypy.request.script_name:
            resp = self.__getSuggest(params)

        # /api/search/lookup
        elif 'lookup' in cherrypy.request.script_name:
            resp = self.__getLookup(params)

        # /api/update
        elif 'update' in cherrypy.request.script_name:
            resp = self.md.update()

        elif 'aggregators' in cherrypy.request.script_name:
            resp = ["noop", "sum", "avg", "max", "min", "rate"]

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

    def __init__(self, logger, mdHandler):
        self.logger = logger
        self.__md = mdHandler

    @property
    def qh(self):
        return self.__md.qh

    @property
    def sensorsConf(self):
        return self.__md.SensorsConfig

    @property
    def TOPO(self):
        return self.__md.metaData

    def _getTimeMultiplier(self, timeunit):
        '''Translate OpenTSDB time units, ignoring ms (milliseconds)'''
        return {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'n': 2628000,
            'y': 31536000,
            }.get(timeunit, -1)

    def _retrieveData(self, query, dsOp=None, dsInterval=None):
        '''Executes zimon query and returns results'''

        self.logger.info(MSG['RunQuery'].format(query))
        tstart = timer()
        res = self.qh.runQuery(query)
        tend = timer()
        self.logger.info(MSG['TimerInfo'].format('runQuery: \"' + str(query) + '\"', str(tend - tstart)))
        if res is None:
            return
        self.logger.info("res.rows length: {}".format(len(res.rows)))
        rows = res.rows
        if dsOp and dsInterval and len(res.rows) > 1:
            rows = res.downsampleResults(dsInterval, dsOp)
        columnValues = defaultdict(dict)
        for row in rows:
            for value, columnInfo in zip(row.values, res.columnInfos):
                columnValues[columnInfo][row.tstamp] = value
        return columnValues

    def _validateQueryFilters(self, metricName, query):
        notValid = False

        # check filterBy settings
        if query.filters:
            filterBy = dict(x.split('=') for x in query.filters)
            identifiersMap = self.TOPO.getIdentifiersMapForQueryAttr('metric', metricName, filterBy)

            if not identifiersMap:
                self.logger.error(MSG['FilterByErr'])
                return (notValid, MSG['AttrNotValid'].format('filter'))

        # check groupBy settings
        if query.groupby:
            filter_keys = self.TOPO.getAllFilterKeysForMetric(metricName)
            if not filter_keys:
                self.logger.error(MSG['GroupByErr'])
                return (notValid, MSG['AttrNotValid'].format('filter'))
            groupKeys = query.groupby
            if not all(key in filter_keys for key in groupKeys):
                self.logger.error(MSG['AttrNotValid'].format('groupBy'))
                self.logger.error(MSG['ReceivAttrValues'].format('groupBy', ", ".join(filter_keys)))
                return (notValid, MSG['AttrNotValid'].format('filter'))

        return (True, '')

    def _createZimonQuery(self, q, start, end):
        '''Creates zimon query string '''
        query = Query()
        query.normalize_rates = False
        bucketSize = 1  # default
        inMetric = q.get('metric')
        if inMetric not in self.TOPO.getAllEnabledMetricsNames:
            self.logger.error(MSG['MetricErr'].format(inMetric))
            raise cherrypy.HTTPError(404, MSG['MetricErr'].format(inMetric))
        else:
            self.logger.info(MSG['ReceivedQuery'].format(str(q), str(start), str(end)))

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

            except ValueError as e:
                self.logger.error(MSG['QueryError'].format(str(e)))
                raise cherrypy.HTTPError(400, MSG['QueryError'].format(str(e)))

        # set time bounds
        if end:
            query.setTime(str(int(int(start) / 1000)), str(int(int(end) / 1000)))
        else:
            query.setTime(str(int(int(start) / 1000)), '')

        # set bucket size
        bucketSize = self._getSensorPeriod(inMetric)
        if bucketSize < 1:
            self.logger.error(MSG['SensorDisabled'].format(inMetric))
            raise cherrypy.HTTPError(400, MSG['SensorDisabled'].format(inMetric))

        dsOp = dsBucketSize = dsInterval = None
        if q.get('downsample'):
            dsOp = self._get_downsmplOp(q.get('downsample'))
            dsBucketSize = self._calc_bucketSize(q.get('downsample'))
            if not dsOp and dsBucketSize > bucketSize:
                bucketSize = dsBucketSize
                self.logger.info(MSG['BucketsizeChange'].format(q.get('downsample'), bucketSize))
            elif dsBucketSize <= bucketSize:
                dsOp = dsInterval = None
            else:
                dsInterval = int(dsBucketSize / bucketSize)
        else:
            self.logger.info(MSG['BucketsizeToPeriod'].format(bucketSize))

        query.setBucketSize(bucketSize)

        return query, dsOp, dsInterval

    def _formatQueryResponse(self, inputQuery, results, showQuery=False, globalAnnotations=False):

        resList = []

        for columnInfo, dps in results.items():
            if columnInfo.name.find(inputQuery.get('metric')) == -1:
                self.logger.error(MSG['InconsistentParams'].format(columnInfo.name, inputQuery.get('metric')))
                raise cherrypy.HTTPError(500, MSG[500])

            filtersMap = self.TOPO.getAllFilterMapsForMetric(columnInfo.keys[0].metric)
            res = QueryResultObj(inputQuery, dps, showQuery, globalAnnotations)
            res.parseTags(self.logger, filtersMap, columnInfo)
            cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            resList.append(res.__dict__)

        return resList

    def _calc_bucketSize(self, downsample):
        bucketSize = 1  # default
        bstr = downsample

        if '-' in bstr:
            x = re.split('(\d+)', bstr[:bstr.find('-')])
            if len(x) == 3:  # if not 3, then split failed
                if x[1]:  # there is a time value
                    if x[1].isdigit():
                        timeMultiplier = -1
                        if x[2]:  # there is a unit
                            timeMultiplier = self._getTimeMultiplier(x[2])
                            if timeMultiplier == -1:
                                bucketSize = int(x[1])
                            else:
                                bucketSize = int(x[1]) * timeMultiplier
                        else:  # no units
                            bucketSize = int(x[1])
        return bucketSize

    def _get_downsmplOp(self, downsample):
        bstr = downsample
        if '-' in bstr:
            x = bstr.split('-')
            if x[1] in ['avg', 'sum', 'max', 'min']:
                return x[1]
        return None

    def _getSensorPeriod(self, metric):
        bucketSize = 0
        sensor = self.TOPO.getSensorForMetric(metric)
        if not sensor:
            self.logger.error(MSG['MetricErr'].format(metric))
            raise cherrypy.HTTPError(404, MSG['MetricErr'].format(metric))
        elif sensor in ('GPFSPoolCap', 'GPFSInodeCap'):
            sensor = 'GPFSDiskCap'
        elif sensor in ('GPFSNSDFS', 'GPFSNSDPool'):
            sensor = 'GPFSNSDDisk'

        for sensorAttr in self.sensorsConf:
            if sensorAttr['name'] == str('\"%s\"' % sensor):
                bucketSize = int(sensorAttr['period'])
        return bucketSize

    @cherrypy.config(**{'tools.json_in.force': False})
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        ''' Process POST. tools.json_in.force is set to False for
        compatability between versions of grafana < 3 and version 3.'''

        # read query request parameters
        jreq = cherrypy.request.json

        _resp = []

        if jreq.get('queries') is None:
            self.logger.error(MSG['QueryError'].format('empty'))
            raise cherrypy.HTTPError(400, MSG[400])

        # A request query can include more than one sub query and any mixture of the two types
        # For more details please check openTSDB API (version 2.2 and higher) documentation for
        # /api/query
        for i, q in enumerate(jreq.get('queries')):

            q['index'] = i
            query, dsOp, dsInterval = self._createZimonQuery(q, jreq.get('start'), jreq.get('end'))
            if self.logger.level == logging.DEBUG:
                (valid, msg) = self._validateQueryFilters(q.get('metric'), query)
                if not valid:
                    raise cherrypy.HTTPError(400, msg)
            columnValues = self._retrieveData(query, dsOp, dsInterval)
            if columnValues is None:
                self.logger.debug(MSG['NoData'])
                if len(jreq.get('queries')) == 1:
                    raise cherrypy.HTTPError(404, ERR[404])
                else:
                    continue

            res = self._formatQueryResponse(q, columnValues, jreq.get('showQuery'), jreq.get('globalAnnotations'))
            cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            _resp.extend(res)

        return _resp

    def OPTIONS(self):
        # print('options_post')
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, NEW, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Accept'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800


class LookupResultObj():

    def __init__(self, metric):
        self.type = "LOOKUP"
        self.metric = metric
        self.tags = []
        self.results = []

    def parseRequestTags(self, filtersDict):
        if filtersDict:
            for key, value in filtersDict.items():
                tmp = {'key': key, 'value': value}
                self.tags.append(tmp)

    def parseResultTags(self, identifiersMap):
        if identifiersMap:
            for identifiers in identifiersMap:
                d = defaultdict(dict)
                for key in identifiers.keys():
                    d['tags'][key] = identifiers[key]
                    if d not in self.results:
                        self.results.append(d)


class QueryResultObj():

    def __init__(self, inputQuery, dps, showQuery=False, globalAnnotations=False):
        self.metric = inputQuery.get('metric')
        self.dps = dps
        if showQuery:
            self.query = inputQuery
        if globalAnnotations:
            self.globalAnnotations = []
        self.tags = defaultdict(list)
        self.aggregatedTags = []

    def parseTags(self, logger, filtersMap, columnInfo):
        tagsDict = defaultdict(list)
        for key in columnInfo.keys:
            ident = [key.parent]
            ident.extend(key.identifier)
            logger.debug(MSG['ReceivAttrValues'].format('Single ts identifiers', ', '.join(ident)))
            for filtersDict in filtersMap:
                if all((value in filtersDict.values()) for value in ident):
                    logger.debug(MSG['ReceivAttrValues'].format('filtersKeys', ', '.join(filtersDict.keys())))
                    if len(columnInfo.keys) == 1:
                        self.tags = filtersDict
                    else:
                        for _key, _value in filtersDict.items():
                            tagsDict[_key].append(_value)

        for _key, _values in tagsDict.items():
            if len(set(_values)) > 1:
                self.aggregatedTags.append(_key)
            else:
                self.tags[_key] = _values[0]


def processFormJSON(entity):
    ''' Used to generate JSON when the content
    is of type application/x-www-form-urlencoded. Added for grafana 3 support'''

    body = entity.fp.read()
    if len(body) > 0:
        cherrypy.serving.request.json = json.loads(body.decode('utf-8'))
    else:
        cherrypy.serving.request.json = json.loads('{}')


def configureLogging(logfile, loglevel):
    # create the logfile path if needed
    path, folder = os.path.split(logfile)
    if not os.path.exists(path):
        os.makedirs(path)

    # prepare the logger
    logger = logging.getLogger('zimonGrafanaIntf')
    rfhandler = logging.handlers.RotatingFileHandler(logfile, 'a', 1000000, 5)  # 5 x 1M files
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rfhandler.setFormatter(formatter)
    logger.addHandler(rfhandler)
    try:
        logger.setLevel(loglevel)
    except (ValueError, TypeError):
        logger.setLevel(logging.INFO)
    logger.propagate = False  # prevent propagation to default (console) logger
    return logger


def validateCollectorConf(args, logger):

    if not (args.server == 'localhost') and not (args.server == '127.0.0.1'):
        try:
            s = socket.socket()
            s.connect((args.server, args.serverPort))
            print(MSG['CollectorConnInfo'])
        finally:
            s.close()
    else:
        # get queryport
        foundPorts = SensorConfig.getCollectorPorts(logger)
        if foundPorts and str(args.serverPort) not in foundPorts:
            raise Exception("Invalid serverPort specified. Try with: %s" % str(foundPorts))
        elif foundPorts[1] and not (args.serverPort == int(foundPorts[1])):
            args.serverPort = int(foundPorts[1])
            logger.info(MSG['Query2port'].format(args.serverPort))


def findKeyFile(path):
    for name in ["privkey.pem", "tls.key"]:
        for root, dirs, files in os.walk(path):
            if name in files:
                return name
    return None


def findCertFile(path):
    for name in ["cert.pem", "tls.crt"]:
        for root, dirs, files in os.walk(path):
            if name in files:
                return name
    return None


def updateCherrypyConf(args):

    path, folder = os.path.split(args.logFile)
    if not os.path.exists(path):
        os.makedirs(path)
    accesslog = os.path.join(path, 'cherrypy_access.log')
    errorlog = os.path.join(path, 'cherrypy_error.log')

    globalConfig = {'global': {'server.socket_host': '0.0.0.0',
                               'server.socket_port': args.port,
                               'server.socket_timeout': 60,  # increase timeout to 60s
                               'request.show_tracebacks': False,
                               'log.screen': False,  # turn off logging to console
                               'log.access_file': accesslog,
                               'log.error_file': errorlog,
                               'tools.encode.on': True,
                               'tools.encode.encoding': 'utf-8'}}
    cherrypy.config.update(globalConfig)


def updateCherrypySslConf(args, certFile, keyFile):
    certPath = os.path.join(args.keyPath, certFile)
    keyPath = os.path.join(args.keyPath, keyFile)
    sslConfig = {'global': {'server.ssl_module': 'builtin',
                            'server.ssl_certificate': certPath,
                            'server.ssl_private_key': keyPath}}
    cherrypy.config.update(sslConfig)


def main(argv):

    # parse input arguments
    parser = argparse.ArgumentParser('python zimonGrafanaIntf.py')
    parser.add_argument('-s', '--server', action="store", default='localhost',
                        help='Host name or ip address of the ZIMon collector (Default: 127.0.0.1) \
                        NOTE: Per default ZIMon does not accept queries from remote machines. \
                        To run the bridge from outside of the ZIMon collector, you need to modify ZIMon queryinterface settings (\'ZIMonCollector.cfg\')')
    parser.add_argument('-P', '--serverPort', action="store", type=int, default=9084, help='ZIMon collector port number (Default: 9084)')
    parser.add_argument('-l', '--logFile', action="store", default="./logs/zserver.log", help='location of the log file (Default: ./logs/zserver.log')
    parser.add_argument('-c', '--logLevel', action="store", type=int, default=logging.INFO, help='log level 10 (DEBUG), 20 (INFO), 30 (WARN), 40 (ERROR) (Default: 20)')
    parser.add_argument('-p', '--port', action="store", type=int, default=4242, help='port number to listen on (Default: 4242)')
    parser.add_argument('-k', '--keyPath', action="store", help='Directory path of privkey.pem and cert.pem file location(Required only for HTTPS port 8443)')

    args = parser.parse_args(argv)

    if args.port == 8443 and not args.keyPath:
        print(MSG['MissingParm'])
        return
    elif args.port == 8443 and not os.path.exists(args.keyPath):
        print(MSG['KeyPathError'])
        return
    elif args.port == 8443:
        certFile = findCertFile(args.keyPath)
        keyFile = findKeyFile(args.keyPath)
        if (not certFile) or (not keyFile):
            print(MSG['CertError'])
            return

    # prepare the logger
    logger = configureLogging(args.logFile, args.logLevel)
    logger.info('zimonGrafanaItf invoked with parameters:%s', str(args))

    # prepare cherrypy server configuration
    updateCherrypyConf(args)
    if args.port == 8443:
        updateCherrypySslConf(args, certFile, keyFile)

    # prepare metadata
    try:
        validateCollectorConf(args, logger)
        mdHandler = MetadataHandler(logger, args.server, args.serverPort)
        print(MSG['MetaSuccess'])
        print(MSG['ReceivAttrValues'].format('sensors', "\n\n" + "\t".join(mdHandler.metaData.sensorsSpec.keys())))
    except (AttributeError, ValueError, TypeError) as e:
        logger.exception('%s', MSG['IntError'].format(str(e)))
        print(MSG['MetaError'])
        return
    except (Exception, IOError) as e:
        logger.exception('%s', MSG['IntError'].format(str(e)))
        print(MSG['CollectorErr'])
        return
    except (OSError) as e:
        logger.exception('%s', MSG['IntError'].format(str(e)))
        print("ZiMon sensor configuration file not found")
        return

    ph = PostHandler(logger, mdHandler)
    cherrypy.tree.mount(ph, '/api/query',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                          'request.body.processors': {'application/x-www-form-urlencoded': processFormJSON}
                          }
                         }
                        )

    gh = GetHandler(logger, mdHandler)
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

    print(MSG['sysStart'].format(sys.version, cherrypy.__version__))
    logger.info("%s", MSG['sysStart'].format(sys.version, cherrypy.__version__))

    try:
        cherrypy.engine.start()
        print("server started")
        cherrypy.engine.block()
    except TypeError:
        print("Server request could not be proceed. Reason:")
        raise cherrypy.HTTPError(500, ERR[500])
    except IOError:
        print("STOPPING: Server request could not be proceed. Reason:")
        cherrypy.engine.stop()
        cherrypy.engine.exit()

    ph = None
    gh = None

    print("server stopped")


if __name__ == '__main__':
    main(sys.argv[1:])
