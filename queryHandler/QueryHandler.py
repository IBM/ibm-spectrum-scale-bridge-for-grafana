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

import socket
import json
import sys

import errno

from queryHandler import Query

class QueryHandler:
    '''
    Interface class to access ZIMon data
    '''
    
    # Column types
    PTHRU = 0   # single value
    RATIO = 1   # ratio value
    
    # Data types (only those used explicitly)
    DOUBLE = 20 # DT_FLOAT_32
    
    def __init__(self,server,port=9084,logger=None):
        '''
        Constructor requires name (or IP address) of the server and the port number (default: 9084)
        '''
        self.sock = None
        self.lineBuf = []
        self.columnInfos = []   # dict: 'column'= column number, 'keys'=keys for columns, 'name'=name of column
                                #       'type'=value type
        self.columnOps  = []    # dict:  
        self.leftover = ''
        self.queryDone = False
         
        self.server = server
        self.port = port
        self.logger = logger
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as msg:
            raise Exception(None,'Failed to create socket. Error code: {0}, error message: {1}'.format(str(msg[0]),msg[1]))
        
        try:
            remote_ip = socket.gethostbyname(server)
        except socket.gaierror:
            raise Exception(None,'Hostname {0} could not be resolved.'.format(server))
        
        try:
            self.sock.connect((remote_ip,port))
        except socket.error as e:
            raise Exception(None,'Unable to connect to {0} on port {1}, error number: {2}, error code: {3}'
                            .format(remote_ip, port, e.errno,errno.errorcode.get(e.errno)))
        
        self.sock.settimeout(60) # set socket timeout (60 seconds)
    
    def __exit__(self, arg_type, value, traceback):
        if self.sock != 0:
            self.sock.close()

    def __del__(self):
        if self.sock != None:
            self.sock.close()
            self.sock = None
    
    def __validSocket(self):
        '''Internal method that will try to connect to the server/port
        if the connection is broken (self.sock = None) '''
        if self.sock == None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except socket.error:
                if self.sock:
                    self.sock.close()
                    self.sock = None
                return False
            try:
                remote_ip = socket.gethostbyname(self.server)
            except socket.gaierror:
                if self.sock:
                    self.sock.close()
                    self.sock = None
                return False
        
            try:
                self.sock.connect((remote_ip,self.port))
            except socket.error:
                if self.sock:
                    self.sock.close()
                    self.sock = None
                return False
            
            
            self.sock.settimeout(60) # set socket timeout (60 seconds)
        
        return True
    
    def runQuery(self,query):
        '''
        runQuery: executes the given query based on the arguments.
        query: a query class instance
        '''
        # only one query can be active at a time; we do not queue
        if len(self.lineBuf) > 0:
            if self.logger:
                self.logger.info('QueryHandler: runQuery lineBuf not empty, terminating previous query')
            else:
                print('runQuery lineBuf not empty, terminating previous query')
            self.terminateCurrentQuery()
            self.queryDone = False
        else:
            self.queryDone = False
       
        # first get the metadata
        queryString = 'get -j '
        # metrics or keys
        if query.getUseMetrics():
            queryString += 'metrics '
            rmetrics = query.getRatioMetrics()
            if len(rmetrics) > 0:
                queryString += rmetrics
                if len(query.getMetrics()) > 0:
                    queryString += ','        
            queryString += query.getMetrics()
        else:
            queryString += 'key ' + query.getMetrics()
        
        # filters
        if len(query.getFilters()) > 0:
            queryString += ' from '+ query.getFilters()
        # groupBy
        if len(query.getGroupByMetrics()) > 0:
            queryString += ' group_by '+ query.getGroupByMetrics()
        # time spec
        queryString += ' now '
        #bucket size
        queryString += query.getBucketSize()+'\n'
            
        #if self.sock != 0:
        if (self.__validSocket()):
            try:
                if sys.version < '3':
                    self.sock.sendall(queryString)
                else:
                    self.sock.sendall(bytes(queryString,'UTF-8'))
            except socket.error as e:
                if self.logger:
                    self.logger.error('QueryHandler: Socket connection failed, errno: {0}'.format(e.errno))
                else:
                    print('Socket connection failed, errno: {0}'.format(e.errno))
                self.sock = None
                return -1
            
            msg = ''
            while True:
                chunk = ''
                try:
                    if sys.version < '3':
                        chunk = self.sock.recv(8192)
                    else:
                        chunk = self.sock.recv(8192).decode('UTF-8')
                except socket.timeout:  # no response with the set time
                    if self.logger:
                        self.logger.error('QueryHandler: Socket timed out, received no response (metadata request)')
                    else:
                        print('Socket timed out, received no response (metadata request)')
                    self.sock.close()   # close and force re-init
                    self.sock = None
                    return -1
                
                if chunk == '':
                    if self.logger:
                        self.logger.error('QueryHandler: Socket connection broken, received no data')
                    else:
                        print('Socket connection broken, received no data')
                    self.sock.close()
                    self.sock = None
                    return -1
                
                msg = msg + chunk
                if chunk.endswith('.\n'):
                    break
            lines = msg.split('\n')
            if lines[0].startswith('Error'):
                if self.logger:
                    self.logger.error('QueryHandler: query returned no data: {0}'.format(lines[0]))
                else:
                    print('query returned no data: {0}'.format(lines[0]))
                return -1

            try:
                jsonmsg = json.loads(lines[0])
            except ValueError as e:
                if self.logger:
                    self.logger.error('QueryHandler: query response not valid json: {0}'.format(lines[0][:20]))
                else:
                    print('query response not valid json: {0}'.format(lines[0][:20]))
                return -1

            self.columnInfos = []
            d = {}
            d['name'] = 'timestamp'
            d['type'] = 4   # DT_UINT_64
            d['keys'] = []
            d['column'] = 0
            self.columnInfos.append(d)
            colNum = 1
            legendItems = jsonmsg['legend']
            for item in legendItems:
                d = {}
                d['column'] = colNum
                colNum += 1
                d['keys'] = item['keys']
                d['name'] = item['caption']
                d['type'] = item['type']
                self.columnInfos.append(d)
            
            # Create columnOps which determines how the received data will be sent out
            # based on the types of columns (e.g., rates)
            self.columnOps = []
            ratioPairs = int(query.getRatioMetricsCount() / 2);
            idx = 0; 
            start = 0;
            while idx < len(self.columnInfos):
                if idx == 0: # timestamp
                    d = {}
                    d['op'] = QueryHandler.PTHRU
                    d['m1Col'] = 0
                    d['m2Col'] = -1
                    self.columnOps.append(d)
                    idx   += 1
                    start += 1

                elif ratioPairs > 0:
                    while ratioPairs > 0:
                        ratioCol1Name = query.getRatioMetric(query.getRatioMetricsCount() - (2*ratioPairs));
                        if ratioCol1Name == '':
                            if self.logger:
                                self.logger.error('QueryHandler: runQuery: Query.getRatioMetric (col1) returned no column name')
                            else:
                                print('runQuery: Query.getRatioMetric (col1) returned no column name')
                            return -1;
                        
                        # look for columns (col1s) that are the same, in order
                        tmpIdx = idx
                        while idx < len(self.columnInfos) and ratioCol1Name == self.columnInfos[idx].get('name'):
                            idx += 1
                        
                        if idx == tmpIdx:
                            if self.logger:
                                self.logger.error('QueryHandler: runQuery: could not find col1 metric {0} quitting'.format(ratioCol1Name))
                            else:
                                print('runQuery: could not find col1 metric {0} quitting'.format(ratioCol1Name))
                            return -1;
                            
                        
                        # There should be equal number of col1s and col2s
                        # idx points to the start of "column 2"; check how many column2 elements are available
                        # in comparison to column 1 elements discovered so far ( = idx-start)
                        ratioCol2Name = query.getRatioMetric(query.getRatioMetricsCount() - (2*ratioPairs) +1);
                        if ratioCol2Name == '':
                            if self.logger:
                                self.logger.error('QueryHandler: runQuery: Query.getRatioMetric (col2) returned no column name')
                            else:
                                print('runQuery: Query.getRatioMetric (col2) returned no column name')
                            return -1;
                        
                        start2 = idx;
                        count = 0;
                        while start2 < len(self.columnInfos) and start2 < idx+(idx-start):#len(self.columnInfos):
                            if ratioCol2Name == self.columnInfos[start2].get('name'):
                                count  +=1
                                start2 += 1
                            else:
                                break;
                        
                        if count != (idx-start):
                            if self.logger:
                                self.logger.error('QueryHandler: runQuery: Ratio processing: Found unmatching col1 and col2 pairs: {0} and {1}'
                                                  .format(ratioCol1Name, ratioCol2Name))
                            else:
                                print('runQuery: Ratio processing: Found unmatching col1 and col2 pairs: {0} and {1}'
                                                  .format(ratioCol1Name, ratioCol2Name));
                            return -1
                
                        # Add operation with the corresponding actual col numbers
                        for i in range(0,idx-start):
                            d = {}
                            d['op'] = QueryHandler.RATIO
                            d['m1Col'] = start+i
                            d['m2Col'] = idx+i
                            self.columnOps.append(d)
                        
                        start = start + (idx-start)*2;
                        idx = start;
                        ratioPairs -= 1

                else:
                    d = {}
                    d['op'] = QueryHandler.PTHRU
                    d['m1Col'] = idx
                    d['m2Col'] = -1
                    self.columnOps.append(d)                   
                    idx += 1
             
            # now get the real data
            queryString = 'get -'
            # type of response
            if (query.getUseJSON()):
                queryString += 'j'
            else:    # default, csv response
                queryString += 'c'
            # add 'include data from disk' if specified
            if (query.getIncludeDiskData()):
                queryString += 'a'
                
            # metrics or keys
            if query.getUseMetrics():
                queryString += ' metrics '
                rmetrics = query.getRatioMetrics()
                if len(rmetrics) > 0:
                    queryString += rmetrics
                    if len(query.getMetrics()) > 0:
                        queryString += ','          
                queryString += query.getMetrics()
            else:
                queryString += ' key ' + query.getMetrics()
            # filters
            if len(query.getFilters()) > 0:
                queryString += ' from '+ query.getFilters()
            # groupBy
            if len(query.getGroupByMetrics()) > 0:
                queryString += ' group_by '+ query.getGroupByMetrics()
            # time spec
            queryString += ' ' +  query.getTimeSpec()
            #bucket size
            queryString += ' ' + query.getBucketSize()+'\n'
            
            try:
                if sys.version < '3':
                    self.sock.sendall(queryString)
                else:
                    self.sock.sendall(bytes(queryString,'UTF-8'))
            except socket.error as e:
                if self.logger:
                    self.logger.error('QueryHandler: Socket connection failed, errno: {0}'.format(e.errno))
                else:
                    print('Socket connection failed, errno: {0}'.format(e.errno))
                self.sock = None
                return -1
    
            chunk = ''
            try:
                if sys.version < '3':
                    chunk = self.sock.recv(8192)
                else:
                    chunk = self.sock.recv(8192).decode('UTF-8')
            except socket.timeout:  # no response with the set time
                if self.logger:
                    self.logger.error('QueryHandler: Socket timed out, received no data (data)')
                else:
                    print('Socket timed out, received no data (data)')
                if len(self.lineBuf)>0:
                    del self.lineBuf[0:len(self.lineBuf)]
                if len(self.columnInfos)>0:
                    del self.columnInfos[0:len(self.columnInfos)]
                self.sock.close()   # close and force re-init
                self.sock = None
                return -1
            
            if chunk == '':
                if self.logger:
                    self.logger.error('QueryHandler: Socket connection broken, received no data')
                else:
                    print('Socket connection broken, received no data')
                self.sock.close()
                self.sock = None
                return -1
            
            msg = self.leftover + chunk
    
            rc = msg.rfind('\n')
            if rc < 0:  # could not find \n
                self.leftover = msg
            else:
                if rc == 0: # \n is the first element
                    self.leftover = msg[1:].lstrip().rstrip()
                else:
                    lines = msg[:rc].split('\n')
                    for line in lines:
                        if (len(line) == 0) | (line.lstrip().rstrip() == '.') | ('Timestamp' in line): continue
                        self.lineBuf.append(line)
                                    
                        if chunk.endswith('\n'):
                            # ends with linefeed
                            self.leftover = ''
                        else:
                            self.leftover = chunk[chunk.rfind('\n'):]
            
                        if chunk.endswith('.\n'):
                            self.queryDone = True            
       
            return 0
        else:
            return -1

    def terminateCurrentQuery(self):
        '''
        Used to terminate an existing query which has not been completely consumed
        Called from runQuery
        '''
        while(self.hasNext()):
            self.getRowData()
        if len(self.lineBuf)>0:
            del self.lineBuf[0:len(self.lineBuf)]
        if len(self.columnInfos)>0:
            del self.columnInfos[0:len(self.columnInfos)]
        if len(self.columnOps)>0:
            del self.columnOps[0:len(self.columnOps)]
                           
    def getCSVLine(self):
        '''
        Return a row of response as a comma separated CSV string
        '''
        if len(self.lineBuf) > 0:
            return self.lineBuf.pop(0)
        else:
            return ''
    
    def num(self,strNum):
        '''
        Converts input value strNum to an int or float
        '''
        try:
            return int(strNum)
        except ValueError:
            try:
                return float(strNum)
            except ValueError:
                if self.logger:
                    self.logger.warn('QueryHandler: method num called with a non numerical argument: {0}'.format(strNum))
                else:
                    print('Method QueryHandler::num called with a non numerical argument: {0}'.format(strNum))
                return None
    
    def getRowData(self):
        '''
        Returns the latest row read for query as a list of int or float values
        '''
        results = []
        timestamp = 0
        if len(self.lineBuf) > 0:
            line = self.lineBuf.pop(0).lstrip().rstrip()
            
            # handle the case where a line may contain non-characters (header data)
            Done = False
            while not Done:
                try:
                    int(line[:2])
                    Done = True
                except ValueError:
                    if len(self.lineBuf) == 0:
                        return timestamp,results
                    else:
                        line = self.lineBuf.pop(0).lstrip().rstrip()                
            
            vals = line.split(',')
            timestamp = int(vals.pop(0))
            
            for i in range(1,len(self.columnOps)):
                if self.columnOps[i].get('op') == QueryHandler.PTHRU:
                    val = vals[self.columnOps[i].get('m1Col')-1]
                    if val != 'null' or len(val) == 0:
                        results.append(self.num(val))
                    else:
                        results.append('null')
                else:       # RATIO
                    numVal = vals[self.columnOps[i].get('m1Col')-1]   # numerator (string)
                    denVal = vals[self.columnOps[i].get('m2Col')-1]   # denominator (string)
                    if numVal == 'null' or denVal == 'null':
                        results.append('null')
                        continue
                    elif len(numVal) == 0 or len(denVal) == 0:
                        if self.logger:
                            self.logger.warn('QueryHandler: getRowData: numerator or denominator string is empty!')
                        else:
                            print('getRowData: numerator or denominator string is empty!')
                        results.append('null')
                        continue
                    else:
                        numerator   = self.num(numVal)
                        denominator = self.num(denVal)
                        #Computing ratios:
                        # 1. if the numerator or the denomintor is null, the ratio is null.
                        # 2. if the denominator = 0, then
                        #      2.a if the nominator = 0, then the ratio is 0.0
                        #      2.b otherwise the value is null
                        # 3. if both the numerator and denominator are > 0, then the value is the ratio
                        if (numerator != None) and (denominator != None):
                            if (float(denominator) != 0.0):     # denominator is not zero, numerator is a value
                                results.append(float(numerator)/float(denominator))
                            elif float(numerator) == 0.0:       # denominator is zero, so is the numerator
                                results.append(float(0))
                            else:
                                results.append('null')
                        else:
                            results.append('null')
        
        return timestamp,results
            
    def hasNext(self): 
        '''
        Read additional response lines into buffer. Marks end of query if detected
        '''      
        if len(self.lineBuf) > 0:   # there is data to read
            return True
        else:
            if self.queryDone:  # is the query complete?
                return False

            while len(self.lineBuf) == 0:
                chunk = ''
                try:
                    if sys.version < '3':
                        chunk = self.sock.recv(8192)
                    else:
                        chunk = self.sock.recv(8192).decode('UTF-8')
                except socket.timeout:  # no response with the set time
                    if self.logger:
                        self.logger.error('QueryHandler: (hasNext) Socket timed out, received no data')
                    else:
                        print('(hasNext) Socket timed out, received no data')
                    return False
                
                if chunk == '':
                    if self.logger:
                        self.logger.error('QueryHandler: (hasNext) Socket connection broken, received no data')
                    else:
                        print('(hasNext) Socket connection broken, received no data')
                    return False
                
                if chunk == '\n.\n':            # end of response (full)
                    if len(self.leftover) > 0:  # if there is data in leftover, move it to linebuf
                        self.lineBuf.append(self.leftover)
                    self.queryDone = True       # mark query complete
                    self.leftover = ''
                    if len(self.lineBuf) > 0:
                        return True;            # there is data to process
                    else:
                        return False;
                    
                if chunk == '.\n':              # end of response (partial, include '.'
                    self.queryDone = True       # query complete, self.leftover must be empty
                    self.leftover = ''
                    return False;               # there is no data to process
                
                if chunk == '\n':               # possible 'end of query'
                    if (self.leftover == '.'):  # if self.leftover is '.'. this is the end of query
                        self.queryDone = True
                        self.leftover = ''
                        return False
                    #else: if there is data in self.leftover, this is handled below

                msg = self.leftover + chunk

                rc = msg.rfind('\n')
                if rc < 0:
                    self.leftover = msg
                    continue
                else:
                    if rc == 0:
                        self.leftover = msg[1:].lstrip().rstrip()
                        continue
                    else:
                        lines = msg[:rc].split('\n')
                        for line in lines:
                            if (len(line) == 0) | (line.lstrip().rstrip() == '.') | ('Timestamp' in line): continue
                            self.lineBuf.append(line)
            
                        if chunk.endswith('\n'):
                            # ends with linefeed
                            self.leftover = ''
                        else:
                            self.leftover = chunk[chunk.rfind('\n')+1:] # +1 to remove the found '\n'
            
                        if chunk.endswith('.\n'):
                            self.queryDone = True
                            break   # if query is done, nothing more to read
                       
            if len(self.lineBuf) > 0:
                return True
            else:
                return False
            
    def getJSONResponse(self):
        '''
        Returns a JSON string as a response
        '''
        response = ''
        while(self.hasNext()):
            response += self.lineBuf.pop(0).lstrip().rstrip()
       
        return response   
    
    def getTopology(self,ignoreMetrics=False):
        '''
        Returns complete topology as a single JSON string
        ignoreAttrs can be used to skip the (leaf) metrics
        '''
        queryString = 'topo'
        if ignoreMetrics:
            queryString += ' -a'
        queryString += '\n'
        
        if self.sock != 0:
            try:
                if sys.version < '3':
                    self.sock.sendall(queryString)
                else:
                    self.sock.sendall(bytes(queryString,'UTF-8'))
            except socket.error as e:
                if self.logger:
                    self.logger.error('QueryHandler: (getTopology) Socket connection failed, errno: {0}'.format(e.errno))
                else:
                    print('(getTopology) Socket connection failed, errno: {0}'.format(e.errno))
                return None
        
            msg = ''
            while True:
                chunk = ''
                if sys.version < '3':
                    chunk = self.sock.recv(4096)
                else:
                    chunk = self.sock.recv(4096).decode('UTF-8')
                if chunk == '':
                    if self.logger:
                        self.logger.error('QueryHandler: (getTopology) Socket connection broken, received no data')
                    else:
                        print('(getTopology) Socket connection broken, received no data')
                    return -1
                msg = msg + chunk
                if chunk.endswith('.\n'):
                    break
            
            lines = msg.split('\n')
            if lines[0].startswith('Error'):
                if self.logger:
                    self.logger.error('QueryHandler: topology query returned no data: {0}'.format(lines[0]))
                else:
                    print('topology query returned no data: {0}'.format(lines[0]))
                return None
    
            return lines[0]
        else:
            if self.logger:
                self.logger.error('QueryHandler: invalid socket (getTopology)')
            else:
                print('invalid socket (getTopology)')
            return None

    def getNumberOfColumns(self):
        '''
        Number of columnInfos in the response
        '''
        return len(self.columnOps);

    def getColumnName(self,index):
        '''
        The name of column(index)
        '''
        if index < len(self.columnOps) and index >= 0:
            colOpData = self.columnOps[index]
            if colOpData.get('op') == QueryHandler.PTHRU:
                return self.columnInfos[colOpData.get('m1Col')].get('name')
            elif colOpData.get('op') == QueryHandler.RATIO:
                name = self.columnInfos[colOpData.get('m1Col')].get('name')
                name += '/' + self.columnInfos[colOpData.get('m2Col')].get('name')
                return name
            else:
                return 'Unknown';
        else:
            return '';
        
        
    def getColumnType(self,index):
        '''
        Type of column(index)
        '''       
        if index < len(self.columnOps) and index >= 0:
            colOpData = self.columnOps[index]
            if colOpData.get('op') == QueryHandler.PTHRU:
                return self.columnInfos[colOpData.get('m1Col')].get('type')
            elif colOpData.get('op') == QueryHandler.RATIO:
                return QueryHandler.DOUBLE
            else:
                return 0
        else:
            return 0;
    
    def getColumnKeys(self,index):
        '''
        Returns the keys associated with the column at the given index.
        If the column is not a "ratio" operation, then the list will contain
        a single list of keys.
        If the column represents the results of a ratio operation, the list
        will contain two lists, a set of keys for the numerator, and a set of
        keys for the denominator.
        '''
        response = []
        if index < len(self.columnInfos) and index >= 0:
            colOpData = self.columnOps[index]
            response.append(self.columnInfos[colOpData.get('m1Col')].get('keys'))
            if colOpData.get('op') == QueryHandler.RATIO:
                response.append(self.columnInfos[colOpData.get('m2Col')].get('keys'))
        
        return response
        
        
if __name__ == '__main__':
    # ZIMon server 
    server = 'lettere'
    # Create a query handler 'object'
    try:
        qh = QueryHandler(server,9084)
    except Exception as e:
        print('Could not initialize the QueryHandler, quitting (errno: {0}, errmsg: {1})'.format(e.args[0],e.args[1]))
        sys.exit(0)
    # query using metrics
    query = Query()
    query.setUseMetrics(True)
    query.addMetric('cpu_idle')
    query.addMetric('netdev_bytes_s')
    query.addMetric('mem_active')
    # filter (metric)
    query.addFilter('node',server)
    query.addFilter('netdev_name','eth[01]')
    # time spec
    query.set_timeLastNBuckets(10)
    # bucket_size
    query.setBucketSize(60);
    # run query
    rc = qh.runQuery(query)
    if rc < 0:
        print('Error sending query 1, quitting')
        sys.exit(0)
    # print the columnInfos that are received (first is timestamp, the others corresponds to the metrics / keys
    i = 0
    while (i < qh.getNumberOfColumns()):
        print(qh.getColumnName(i)+' : '+str(qh.getColumnKeys(i))+' : '+str(qh.getlColumnType(i)))
        i += 1
    # display the incoming data using getRowData which returns values as string,ints or floats
    count = 1
    while (qh.hasNext()):
        timestamp,values = qh.getRowData()
        result = ''
        col = 0
        for val in values:
            result += str(val)
            if col < len(values)-1:
                result += ','
            col += 1
        print(str(count)+': '+str(timestamp)+': '+ result)
        count += 1
    
    print('--------')
    # query using keys
    query = Query()
    query.setUseMetrics(False)
    query.addKey('.*|CPU|cpu_idle')
    query.addKey(server+'|Network|eth[01]|netdev_bytes_r')
    query.set_timeLastNBuckets(10)
    query.setBucketSize(60)

    rc = qh.runQuery(query)
    if rc < 0:
        print('Error sending query 2, quitting')
        sys.exit(0)

    # print the columnInfos that are received (first is timestamp, the others corresponds to the metrics / keys
    i = 0
    while (i < qh.getNumberOfColumns()):
        print(qh.getColumnName(i)+' : '+str(qh.getColumnKeys(i))+' : '+str(qh.getlColumnType(i)))
        i += 1
  
    # read received values as rows of CSV strings (comma separated)    
    while (qh.hasNext()):
        print(qh.getCSVLine())
    
    print('Done.')