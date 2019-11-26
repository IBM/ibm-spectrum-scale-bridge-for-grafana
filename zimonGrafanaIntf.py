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

Created on Jun 29, 2015
Updated on Aug 15, 2016

@author: fer
'''

import cherrypy

import json

import re

import argparse
import logging.handlers

import sys

import copy

from collections import OrderedDict

from queryHandler.Query import Query
from queryHandler.QueryHandler import QueryHandler

class MetadataHandler():

    def __init__(self):
        pass
    
    def init(self,logger,server,port=9084):
        '''Description of internal data sets:
        metrics:        list of (observed) metric names
        keys:           list of key instances
        metaKeys:       key components, i.e., metric-> list of key components
        tagKeys:        list of key component names that can be used as tags
        tagValues:      list of key values that can be used as tag values
        metricNodeMap:  metric name+|+tag -> available values for metric name, tag pair
        '''
        self.logger = logger
        self.server = server
        self.port   = port
          
        self.metrics = set()
        self.keys = []
        self.tagKeys = set()
        self.tagValues = set()
        self.metaKeys = {}
        self.metricNodeMap = {}
        
        return self.initializeTables()
    
    def cleanJSONStr(self,inString):
        '''Remove control, single backslash, quote characters
        from unprocessed JSON string'''
        charSet = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '
        return(''.join(str(a) for a in filter(charSet.__contains__,inString)).replace('\\','\\\\').replace('"','\"'))
    
    def initializeTables(self):
        '''Read the topology from ZIMon and (re-)construct
        the tables for metrics, keys, key elements (tag keys)
        and key values (tag values)'''
        
        qh = None
        try:
            qh = QueryHandler(self.server,self.port)           
        except Exception as e:
            self.logger.error('Could not initialize the QueryHandler, GetHandler::initializeTables failed (errno: {}, errmsg: {})'.format(e.args[0],e.args[1]))
            return -1

        topoJSONStr = qh.getTopology()
          
        if topoJSONStr != None:
            if sys.version < '3':
                self.metrics = set()
                self.keys = []
                self.tagKeys = set()
                self.tagValues = set()
                self.metaKeys = {}
                self.metricNodeMap = {}
            else:
                # reset tables
                self.metrics.clear()
                self.keys.clear()
                self.tagKeys.clear()
                self.tagValues.clear()
                self.metaKeys.clear()
                self.metricNodeMap.clear()
            
            # clean-up step - some keys may contain illegal chars
            topoJSONStr = self.cleanJSONStr(topoJSONStr) 
              
            topojson = json.loads(topoJSONStr)
              
            self.processTopo(topojson,[],[])
              
            for key in self.metaKeys.keys():
                self.logger.debug(key+":"+''.join(self.metaKeys.get(key)))
                
            #for key in self.metricNodeMap.keys():
            #    print("{}: {}".format(key,self.metricNodeMap[key]))
      
        #print('m: {} k: {} tk: {} tv: {}'.format(len(self.metrics),len(self.keys),len(self.tagKeys),len(self.tagValues)))
        return 0
    
    def processTopo(self,tjson,mKey,kVal):
        for node in tjson:
            if node['type'] == 'node':
                self.tagKeys.add(node['fieldName'])
                mKey.append(node['fieldName'])
                kVal.append(node['fieldLabel'])
                self.tagValues.add(node['fieldLabel'])
                self.processTopo(node['keys'],mKey,kVal)
                mKey.pop()
                kVal.pop()
            elif node['type'] == 'attribute':
                self.metrics.add(node['fieldName'])
                self.keys.append(node['partialKey']+'|'+node['fieldName'])
                if not node['fieldName'] in self.metaKeys:
                    if sys.version < '3':
                        new_list = mKey[:]
                        self.metaKeys[node['fieldName']] = new_list
                    else:
                        self.metaKeys[node['fieldName']] = mKey.copy()
                if len(mKey) != len(kVal):
                    print("mKey and kVal have different lengths!")
                for i in range(len(mKey)):
                    if mKey[i] == 'sensor':
                        continue;
                    mnmKey = node['fieldName']+'|'+mKey[i]
                    if not mnmKey in self.metricNodeMap:
                        temp = set()
                        temp.add(kVal[i])
                        self.metricNodeMap[mnmKey] = temp
                    else:
                        self.metricNodeMap[mnmKey].add(kVal[i])
                    
                    

class GetHandler(object):
    exposed = True
        
    def __init__(self):
        pass
     
    def init(self,logger,mdHandler,server,port=9084):
        self.logger = logger
        self.mdHandler = mdHandler
        self.server = server
        self.port   = port                 
 
    @cherrypy.tools.json_out()
    def GET(self,**params):
        '''Handle partial URLs such as /api/suggest?q=cpu_&type=metrics 
        where type is one of metrics, tagk or tagv: in terms of ZIMon, "metrics"
        is a metric name or key; "tagk" is a metric name and "tagv" is a value
        or
        Handle /api/search/lookup/m=cpu_idle{node=*}
        where m is the metric and optional term { tagk = tagv } qualifies the lookup.
        If { tagk = tagv } is not present, then key identifiers (metric names) are returned.
        If present (typically with tagv = '*', tagv values for given metric ('m') and 'tagk'
        are returned'''
        
        #print('get')
        #print('sn {} q {} t {} m {}'.format(cherrypy.request.script_name,params.get('q'),
        #                                    params.get('type'),params.get('m')))
   
        resp = []
        if 'suggest' in cherrypy.request.script_name:  
            if params.get('q'): # /api/suggest
                searchStr = params['q'].strip()
                # if '*' and tagv, then it denotes a grouping key value: do not process
                if not(searchStr == '*' and params['type'] == 'tagv'):
                    # Since grafana sends the candidate string quickly, one character at a time, it
                    # is likely that the reg exp compilation will fail.
                    try:
                        regex = re.compile("^"+searchStr+".*")
                    except re.error:
                        #print( re.error )
                        regex = None    # failed to compile, return empty response
        
                    if regex:
                        if params['type'] == 'metrics':
                            if searchStr.find('|') == -1:
                                # metric or key
                                resMetrics = [m.group(0) for item in self.mdHandler.metrics for m in [regex.search(item)] if m]
                                regex = re.compile("^"+searchStr.replace('|','\|')+".*")
                                resKeys = [m.group(0) for item in self.mdHandler.keys for m in [regex.search(item)] if m]
                        
                                resp = sorted(resMetrics+resKeys)
                            else:
                                regex = re.compile("^"+searchStr.replace('|','\|')+".*")
                                resp = sorted([m.group(0) for item in self.mdHandler.keys for m in [regex.search(item)] if m])
                        elif params['type'] == 'tagk':
                            resp = sorted([m.group(0) for item in self.mdHandler.tagKeys for m in [regex.search(item)] if m])
                        elif params['type'] == 'tagv':
                            resp = sorted([m.group(0) for item in self.mdHandler.tagValues for m in [regex.search(item)] if m])
        elif 'lookup' in cherrypy.request.script_name:
            if params.get('m'): # /api/search/lookup
    
                m = re.search('(?P<metric>\w+)(\{(?P<tagk>.*)=(?P<tagv>.*)\})?',params['m'].strip())
                metric  = (lambda x: x.strip() if x else None)(m.group('metric'))
                tagTerm = (lambda x: x.strip() if x else None)(m.group('tagk'))
                tagVal  = (lambda x: x.strip() if x else None)(m.group('tagv'))

                # below, results is either a list or None
                if tagTerm == None:
                    results = self.mdHandler.metaKeys.get(metric)
                else:
                    if tagTerm != '*':
                        searchTerm = metric.strip() + '|' + tagTerm
                        if searchTerm in self.mdHandler.metricNodeMap:
                            results = sorted(self.mdHandler.metricNodeMap[searchTerm])
                        else:
                            results = None
                    else:
                        self.logger.error('Not handled: metric = {} tagTerm = {} and tagVal = {}'.format(metric,tagTerm,tagVal))   
                        
                resp = {}
                resp['type']    = "LOOKUP"
                resp['metric']  = metric
                if tagTerm != None:
                    tmp = {}
                    tmp['key'] = tagTerm;
                    tmp['value'] = tagVal
                    tmp1 = []
                    tmp1.append(tmp)
                    resp['tags'] = tmp1
                else:
                    resp['tags'] = []
     
                finalResults = []
                if results != None:
                    for res in results:
                        if res == 'sensor':
                            continue
                        d1={}
                        if tagTerm != None:
                            d1[tagTerm] = res
                        else:
                            d1[res] = '*'
                        d2={}
                        d2['tags']=d1
                        finalResults.append(d2)
                resp['results'] = finalResults     
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
        cherrypy.response.headers['Access-Control-Allow-Origin']    = '*'
        return resp        
    
class PostHandler(object):
    exposed = True
    
    def init(self,logger,mdHandler,server,port=9084):
        self.logger = logger
        self.mdHandler = mdHandler
        self.server = server
        self.port   = port

    def translateAggregator(self,aggregator):
        '''Translate OpenTSDB aggregation to ZIMon'''
        res = Query.NOP # default
        if aggregator == 'noop':    # default, but do it again
            res = Query.NOP
        elif aggregator == 'sum':
            res = Query.SUM
        elif aggregator == 'avg':
            res = Query.AVG
        elif aggregator == 'max':
            res = Query.MAX
        elif aggregator == 'min':
            res = Query.MIN
        elif aggregator == 'rate':
            res = Query.RATE   
        return res
     
    def getTagValueFromKey(self,metricName,tagName,strKey):
        '''Return string value for the metricName from a key'''
        metaKey = self.mdHandler.metaKeys.get(metricName)
        if metaKey:
            if tagName in metaKey:
                idx = metaKey.index(tagName)
                keyParts = strKey.split('|')
                if idx <= len(keyParts):
                    return keyParts[idx]
         
        return None
    
    def getTagValueFromKeys(self,metricName,tagName,keyList):
        '''Return a list of string values for the metricName from 
        the list of keys'''
        # following is necessary if json was mangled so the "list" is a "string"
        if type(keyList) is str:
            temp = []
            temp.append(keyList)
            keyList = temp
        
        metaKey = self.mdHandler.metaKeys.get(metricName)
        if metaKey:
            if tagName in metaKey:
                idx = metaKey.index(tagName)
                valList = []
                for key in keyList:
                    keyParts = key.split('|')
                    if idx <= len(keyParts):
                        valList.append(keyParts[idx])
                if len(valList) > 0:
                    return ', '.join(set(valList))
         
        return None
 
    def getTimeMultiplier(self,timeunit):
        '''Translate OpenTSDB time units, ignoring ms (milliseconds)'''
        return {
            's' : 1,
            'm' : 60,
            'h' : 3600,
            'd' : 86400,
            'w' : 604800,
            'n' : 2628000,
            'y' : 31536000,
            }.get(timeunit,-1)

    @cherrypy.config(**{'tools.json_in.force' : False})
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def POST(self):
        ''' Process POST. tools.json_in.force is set to False for 
        compatability between versions of grafana < 3 and version 3.'''
        #print('post')

        # read json input        
        jreq = cherrypy.request.json
        #print('start: {} queries: {}'.format(jreq.get('start'),jreq.get('queries')))
        
        # start: start of time period
        # end:   end of time period
        # queries: set of queries, each containing:
        #    metric: metric to query, in our case, could also be a tagName
        #    aggregator: operation on values (grouping?) sum,avg,max,min new: { dev,zimsum,mimmin,mimmax }
        #    downsample: interpret as bucket_size, if not specified, use smallest bucket_size (?)
        #    tags: dictionary of name/val pairs, to be used with metric to precisely identify the data
        #        if the value of a tag is '*', then the tag is used as a grouping key
        #    rate: if true, counter difference should be reported, otherwise row values
        #    rateoptions: grafana supports { 'counter':true } as the only value, indicating monotonically increasing counter
        
        qh = None
        resp = []
        
        if jreq.get('queries') == None:
            self.logger.error('Empty query received, returning an error response')
            raise cherrypy.HTTPError(400, 'Empty query received')            

        for q in jreq.get('queries'):
            if qh == None:
                try:
                    qh = QueryHandler(self.server,self.port)           
                except Exception as e:
                    self.logger.error('Could not initialize the QueryHandler, PostHandler::POST failed (errno: {}, errmsg: {})'.format(e.args[0],e.args[1]))
                    return []

            query = Query()
            
            inMetric = q.get('metric')
            if not inMetric in self.mdHandler.metrics:
                regex = re.compile(inMetric.replace('|','\|'))
                result = [m.group(0) for item in self.mdHandler.keys for m in [regex.search(item)] if m]
                if len(result) > 0: # tagName
                    query.setUseMetrics(False)
                else:   # return an error since the "metric" is not a valid metric or key
                    self.logger.error('Invalid metric or key, returning an error response')
                    raise cherrypy.HTTPError(400, 'Metric or key {0} cannot be found'.format(inMetric))

            # else: metric

            if q.get('aggregator'):
                aggregation = self.translateAggregator(q.get('aggregator'))
            else:
                aggregation = Query.NOP

            # add tagName or metric using the same method. There is no 'NOOP' option in openTSDB            
            query.addMetricOp(aggregation,inMetric)
            
            tagDict = None
            groupByList = None
            if q.get('filters'):
                tagDict = {}
                groupByList = set()
                for f in q.get('filters'):
                    tagk = f.get('tagk')
                    if tagk:
                        if f.get('groupBy'):
                            groupByList.add(tagk)
                        if f.get('filter'):
                            if tagDict.get(tagk):
                                # tag already exists, will overwrite
                                self.logger.warn('Duplicate filter defined for {0}, will be overwritten'.format(tagk))
                            tagDict[f.get('tagk')] = f.get('filter')
                        else:
                            # there is no value, skip
                            pass
                    else:
                        # no tag, skip
                        pass
                            
                for groupByElem in groupByList:
                    query.addGroupByMetric(groupByElem)
            else:   # if not 'filters' (>= 2.2), try 'tags' (<= 2.1)
                tagDict = q.get('tags')

            if tagDict:
                tList = []  # contains the combination of tags
                for tagName in tagDict.keys():
                    if (tagDict.get(tagName) == '*'):   # grouping tagName
                        query.addGroupByMetric(tagName)
# Commented out code implements the openTSDB feature where the "|" indicates an "OR". This does not match
# the ZIMon use of "|" as the regular expression "OR", returning incorrect results.
#                     else:
#                         if '|' in tagDict.get(tagName): # REVISIT for ZIMon interpretation of the "|"
#                             # a tag with openTSDB "OR" option where each element of the value (separated by '|')
#                             # should create a time-series
#                             # Approach: since multiple tags with '|' can be specified, first collect and construct the
#                             # the possible combinations
#                             flist = tagDict.get(tagName).split('|')
#                             if len(tList) == 0:
#                                 for elem in flist:
#                                     d = {}
#                                     d[tagName] = elem
#                                     tList.append(d)
#                             else:
#                                 nList = []
#                                 for d in tList:
#                                     for elem in flist:
#                                         newd = d.copy()
#                                         newd[tagName] = elem
#                                         nList.append(newd)
#                                 tList = copy.deepcopy(nList)
                    else:
                        # straightforward tag with a value
                        if len(tList) == 0:
                            d = {}
                            d[tagName] = tagDict.get(tagName)
                            tList.append(d)
                        else:
                            nList = []
                            for d in tList:
                                newd = d.copy()
                                newd[tagName] = tagDict.get(tagName)
                                nList.append(newd)
                            tList = copy.deepcopy(nList)
                
                if len(tList) > 0:
                    fdict = tList[0]  # pick first for this query
                    for key in fdict:
                        query.addFilter(key, fdict.get(key))

                    for odict in tList[1:]:    # for others, create new queries
                        newq = copy.deepcopy(q)
                        newq['tags'] = odict
                        jreq['queries'].append(newq)

            # set time bounds
            if jreq.get('end'):
                query.set_timeBounds(str(int(int(jreq.get('start'))/1000)),
                                     str(int(int(jreq.get('end'))/1000)))
            else:
                query.set_timeBounds(str(int(int(jreq.get('start'))/1000)),'')

            # set bucket size
            bstr = q.get('downsample')
            bucketSize = 1 # default
            if bstr:
                if '-' in bstr:
                    x = re.split('(\d+)',bstr[:bstr.find('-')])
                    if len(x) == 3: # if not 3, then split failed
                        if x[1]: # there is a time value
                            if x[1].isdigit():
                                timeMultiplier = -1
                                if x[2]: # there is a unit
                                    timeMultiplier = self.getTimeMultiplier(x[2])
                                    if timeMultiplier == -1:
                                        bucketSize = int(x[1])
                                    else:
                                        bucketSize = int(x[1]) * timeMultiplier
                                else:   # no units
                                    bucketSize = int(x[1])
                                    
            query.setBucketSize(bucketSize)
            
            rc = qh.runQuery(query)
            if rc < 0:
                if len(jreq) == 1:
                    self.logger.error('Error sending query, returning empty response')
                    raise cherrypy.HTTPError(404, 'No data available, error sending query')
                else:
                    continue;
            
            # get results
            dpsList = []
            for i in range(0, qh.getNumberOfColumns()-1):
                dpsList.append(OrderedDict())
            
            while (qh.hasNext()):
                rowStr = qh.getCSVLine()    # read line as string
                vals = rowStr.split(',')
                timestamp = vals.pop(0)

                for i in range(0, qh.getNumberOfColumns()-1):
                    if not (vals[i] == 'null'):
                        dpsList[i][timestamp] = qh.num(vals[i])
            
            for idx,dps in zip(range(0,len(dpsList)),dpsList):
                msg = {}
                msg['metric'] = q.get('metric') # 'metric' key is used to label if no tags are defined
                msg['tags'] = {}
                if tagDict:
                    allKeys = qh.getColumnKeys(idx+1)
                    if aggregation == Query.NOP:    # if NOP, no operation or grouping is done, so use full key
                        if type(allKeys[0]) is str:
                            msg['metric'] = allKeys[0]
                        else:
                            msg['metric'] =  allKeys[0][0]
                        # leave the tag empty
                    elif aggregation == Query.RATE:
                        if type(allKeys[0]) is str:
                            msg['metric'] = q.get('aggregator')+'('+ allKeys[0] + ')'
                        else:
                            msg['metric'] = q.get('aggregator')+'('+ allKeys[0][0] +')'
                    else:
                        for tagName in tagDict.keys():                           
                            if (tagDict.get(tagName) != '*'):
                                msg['tags'][tagName] = tagDict.get(tagName)
# We can get all the values for a given tag from the keys, but this lengthens the displayed string in Grafana significantly.
# To enable this feature, comment out the line above, and uncomment those below.
#                                strVal = self.getTagValueFromKeys(q.get('metric'), tagName, qh.getColumnKeys(idx+1))
#                                if strVal:
#                                    if ',' in strVal:
#                                        msg['tags'][tagName] = tagDict.get(tagName)
#                                         msg['tags'][tagName] = '[' + strVal + ']'
#                                    else:
#                                        msg['tags'][tagName] = strVal
#                               else:
#                                    msg['tags'][tagName] = strVal
                            else: 
                                # if this is a grouping tag, given any column tagName, extract the value for that tag
                                if len(qh.getColumnKeys(idx+1)) > 0:
                                    msg['tags'][tagName] = self.getTagValueFromKeys(q.get('metric'), tagName, 
                                                                                    qh.getColumnKeys(idx+1)[0])
                                else:   # can only occur if the data source is sending bad keys
                                    msg['tags'][tagName] = 'unknown'
                        if groupByList:
                            for groupKeyElem in groupByList:
                                if not msg['tags'].get(groupKeyElem):   # do not enter again
                                    if len(qh.getColumnKeys(idx+1)) > 0:
                                        msg['tags'][groupKeyElem] = self.getTagValueFromKeys(q.get('metric'), groupKeyElem, 
                                                                                             qh.getColumnKeys(idx+1)[0])
                                    else:   # can only occur if the data source is sending bad keys
                                        msg['tags'][tagName] = 'unknown'
                else:       # if no tags were defined, try to name based on returned column meta data
                    allKeys = qh.getColumnKeys(idx+1)
                    if aggregation == Query.NOP:
                        if type(allKeys) is str:
                            msg['metric'] = allKeys[0]
                        else:
                            msg['metric'] = allKeys[0][0]
                    elif aggregation == Query.RATE:
                        if type(allKeys) is str:
                            msg['metric'] = q.get('aggregator')+'('+ allKeys[0] +')'
                        else:
                            msg['metric'] = q.get('aggregator')+'('+ allKeys[0][0] +')'
                    else:
                        if groupByList:
                            for groupKeyElem in groupByList:
                                if len(qh.getColumnKeys(idx+1)) > 0:
                                    msg['tags'][groupKeyElem] = self.getTagValueFromKeys(q.get('metric'), groupKeyElem, 
                                                                                         qh.getColumnKeys(idx+1)[0])
                                else:   # can only occur if the data source is sending bad keys
                                    msg['tags'][tagName] = 'unknown'
                        else:
                            msg['metric'] = q.get('aggregator')+'('+q.get('metric')+')'
                                     
                msg['aggregatedTags'] = []
                if not tagDict:
                    metaKey = self.mdHandler.metaKeys.get(msg['metric'])
                    if metaKey:
                        for keyp in metaKey:
                            msg['aggregatedTags'].append(keyp)
                msg['dps'] = dps
            
                cherrypy.response.headers['Access-Control-Allow-Origin']    = '*'
                resp.append(msg)
        
        qh = None     
        return resp        

    def OPTIONS(self):
        #print('options_post')
        
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods']   = 'GET, POST, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin']    = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers']   = 'Content-Type,Accept'
        cherrypy.response.headers['Access-Control-Max-Age']         = 604800
   
def processFormJSON(entity):
    ''' Used to generate JSON when the content
    is of type application/x-www-form-urlencoded. Added for grafana 3 support'''
    #print('processFormJSON')

    body = entity.fp.read()
    if len(body) > 0:
        cherrypy.serving.request.json = json.loads(body.decode('utf-8'))
    else:
        cherrypy.serving.request.json = json.loads('{}')

def main(argv):
    
    serverDefault = ''
    # parse input arguments
    parser = argparse.ArgumentParser('python zimonGrafanaIntf.py')
    parser.add_argument('-s',"-server", action="store",default=serverDefault,help='name or ip address of the ZIMon collector (Required)')
    parser.add_argument('-P','-serverPort',action="store",type=int,default=9084,help='ZIMon collector port number (Default: 9084)')
    parser.add_argument('-l','-logFile',action="store",default="./zserver.log",help='location of the log file (Default: ./zserver.log')
    parser.add_argument('-c','-logLevel',action="store",default=logging.INFO,help='log level 10 (DEBUG), 20 (INFO), 30 (WARN), 40 (ERROR) (Default: 20)')
    parser.add_argument('-p','-port',action="store",type=int,default=4242,help='port number to listen on (Default: 4242)');

    args = vars(parser.parse_args(argv))
    # prepare the logger
    logger = logging.getLogger('zimonGrafanaIntf')
    rfhandler = logging.handlers.RotatingFileHandler(args['l'], 'a', 1000000, 5)    # 5 x 1M files
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rfhandler.setFormatter(formatter)
    logger.addHandler(rfhandler)
    log_level = int(args['c'])
    if log_level in [10,20,30,40]:
        logger.setLevel(log_level)
    else:
        logger.setLevel(logging.INFO)
        logger.warn('Given log level is incorrect, will assume default (20: INFO)')
    logger.propagate = False        # prevent propagation to default (console) logger
    
    if args['s'] == serverDefault:
        logger.error('Server name not specified, quitting')
        print('Server name not specified, quitting')
        return

    mdHandler = MetadataHandler()
    if mdHandler.init(logger,args['s'],args['P']) != 0:
        print('Failed to initialize MetadataHandler, please check log file for reason')
        return

    globalConfig = {
                    'global' : {
                                'server.socket_host': '0.0.0.0',
                                'server.socket_port' : args['p'],
                                'server.socket_timeout' : 60,       # increase timeout to 60s
                                'tools.encode.on' : True,
                                'tools.encode.encoding' : 'utf-8'}}
    cherrypy.config.update(globalConfig)

    cherrypy.log.screen = None  # turn off logging to console

    ph = PostHandler()
    ph.init(logger, mdHandler,args['s'],args['P'])
    cherrypy.tree.mount(ph, '/api/query',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                          'request.body.processors' : { 'application/x-www-form-urlencoded': processFormJSON }
                           }
                         }
                        )
    
    gh = GetHandler()
    gh.init(logger, mdHandler, args['s'],args['P'])
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
    print("Your system is running python version: %s",sys.version)
    print("server starting")
    cherrypy.engine.start()
    cherrypy.engine.block()
    
    ph = None
    gh = None
    print("server stopped")

        
if __name__ == '__main__':
    main(sys.argv[1:])
    
    

    