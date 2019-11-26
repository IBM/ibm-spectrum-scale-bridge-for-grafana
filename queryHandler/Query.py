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

class Query(object):
    '''
    classdocs
    '''

    # OPERATION TYPES
    # No operation (metric only)
    NOP = 0;
    # sum operation
    SUM = 1;
    # avg operation
    AVG = 2;
    # max operation
    MAX = 3;
    # min operation
    MIN = 4;
    # rate operation
    RATE = 5;

    def __init__(self):
        '''
        Constructor
        '''
        self.useMetrics     = True           # use "metrics" or "key" (True or False)
        self.includeDiskData = False         # disk or archived data (False or True)
        self.useJSON        = False          # receive response as a JSON string (if set to True)
        self.metricsOrKeys  = []             # list of string metrics or keys
        self.filters        = []             # list of filters
        self.groupByMetrics = []             # list of groupBy metrics
        self.ratioMetrics   = []             # list of ratio metrics
        self.timeRep        = ''             # string time representation
        self.bucket_size    = 1              # bucket size
        
    def setUseMetrics(self,useMetricsValue):
        '''
        If set to "true", then the metrics are specified using
        the (short) name only, e.g., "cpu_idle". Otherwise, the
        metrics are specified using the key representation, 
        e.g., machine1|CPU|cpu_idle
        Default: metric type
        '''
        self.useMetrics = useMetricsValue
    
    def getUseMetrics(self):
        '''
        Helper function
        '''
        return self.useMetrics
    
    def setIncludeDiskData(self, includeDiskDataValue):
        '''
        If set to "true", then the queryM will also use archived data
        from the disk. This allows more fine grain data to be available, but
        as it reads data from disk, it is slower. By default, includeDiskData
        is set to false (disabled).
        '''   
        self.includeDiskData = includeDiskDataValue
   
    def getIncludeDiskData(self):
        '''
        Helper function
        '''
        return self.includeDiskData
    
    def setUseJSON(self, useJSONValue):
        '''
        Response to the query will be returned as a JSON string
        '''
        self.useJSON = useJSONValue
        
    def getUseJSON(self):
        '''
        Helper function
        '''
        return self.useJSON
    
    def addMetric(self,metric):
        '''
        Add string metric name to the queryM
        '''
        self.metricsOrKeys.append(metric)

    def addMetricOp(self, op, metric):
        '''
        Add metric operation to the queryM, e.g., "sum(cpu_idle)" using the input
        metric name and operation type
        '''
        metricOp = ''
        
        if op == self.NOP:
            metricOp = metric
        elif op == self.SUM:
            metricOp = 'sum('+metric+')'
        elif op == self.AVG:
            metricOp = 'avg('+metric+')'
        elif op == self.MAX:
            metricOp = 'max('+metric+')'
        elif op == self.MIN:
            metricOp = 'min('+metric+')'
        elif op == self.RATE:
            metricOp = 'rate('+metric+')'
            
        self.metricsOrKeys.append(metricOp)

    def getMetrics(self):
        '''
        Helper function
        '''
        response=''
        count = len(self.metricsOrKeys)
        for m in self.metricsOrKeys:
            response += m
            if (count-1 > 0): 
                response += ', '
            count -= 1
        
        return response
    
    def addKey(self, key):
        '''
        Add string metric key to the queryM
        '''
        self.metricsOrKeys.append(key)

    def getKeys(self):
        '''
        Helper function
        '''
        return self.getMetrics()
    
    def addRatio(self,op,metric1,metric2):
        '''
        Add a ratio with two metrics, each using the op, e.g., metrics x and y and SUM operator, with 
        sum(x)/sum(y) as the desired output. Supported operation types: Query.NOP, Query.SUM, and Query.AVG.
        '''
        metricOp1 = ''
        metricOp2 = ''

        if op == self.NOP:
            metricOp1 = metric1
            metricOp2 = metric2
        elif op == self.SUM:
            metricOp1 = 'sum('+metric1+')'
            metricOp2 = 'sum('+metric2+')'
        elif op == self.AVG:
            metricOp1 = 'avg('+metric1+')'
            metricOp2 = 'avg('+metric2+')'
        else:
            print('Operation {} not valid for ratios, addRatio failed'.format(op))
        
        if len(metricOp1) > 0 and len(metricOp2) > 0:
            self.ratioMetrics.append(metricOp1)
            self.ratioMetrics.append(metricOp2)
        
    def getRatioMetrics(self):
        '''
        Return comma separated ratio metrics
        '''
        return ','.join(self.ratioMetrics)
    
    def getRatioMetric(self,idx):
        '''
        Return ratioMetric at the given index
        '''
        if idx < len(self.ratioMetrics):
            return self.ratioMetrics[idx]
        else:
            return ''
        
    def getRatioMetricsCount(self):
        '''
        Return the number of ratio metrics defined
        '''
        return len(self.ratioMetrics)       
    
    def addFilter(self,metric, value):
        '''
        Add a filter of the form "metric=value" where
        the metric is an identifier key element and
        value is a constant or a regular expression       
        '''
        if self.useMetrics == False:    # this query uses keys, not metrics
            raise(Exception("Query::addFilter: cannot specify filter when using metric keys"));
        else:
            self.filters.append(metric+"="+value);
    
    def getFilters(self):
        '''
        Helper function
        '''
        response = '';
        count = len(self.filters);
        for f in self.filters:
            response += f
            if (count-1 > 0): 
                response += ', '
            count -= 1
        
        return response
    
    def addGroupByMetric(self,groupByMetric):
        '''
        Add a metric to be used in grouping multi-metric (operation)
        columns
        '''                                 
        self.groupByMetrics.append(groupByMetric);

    
    def getGroupByMetrics(self):
        '''
        Helper function
        '''
        response = '';
        count = len(self.groupByMetrics);
        for g in self.groupByMetrics:
            response += g
            if (count-1 > 0): 
                response += ', '
            count -= 1
        
        return response

    def set_timeBounds(self,tstart,tend):
        '''
        Specify time bounds (start and end)
        Note: an empty "" argument implies tstart or tend has no value
        '''
        if (len(tstart) != 0):
            self.timeRep += "tstart " + tstart;
        if (len(tend) != 0):
            self.timeRep += " tend " + tend;
  
    def set_timeLastNBuckets(self,num_buckets):
        '''
        Number of most recent buckets to include in the response
        to the query
        '''
        self.timeRep = "last " + str(num_buckets);

    def set_timeDuration(self,seconds):
        '''
        Most recent duration in seconds to cover in the response
        to the query
        '''
        self.timeRep = "duration " + str(seconds);

    def set_timeNow(self):
        '''
        Sets the query to return the current value ("now")
        '''
        self.timeRep = ' now';   

    def getTimeSpec(self):
        '''
        Helper function
        '''
        return self.timeRep;
    
    def setBucketSize(self,bucket_size):
        '''
        Number of seconds that constitute a bucket
        '''
        self.bucket_size = bucket_size;
    
    def getBucketSize(self):
        '''
        Helper function
        '''
        return 'bucket_size ' + str(self.bucket_size);
       
if __name__ == '__main__':
    # Create query with metrics
    queryM = Query()
    queryM.setUseMetrics(True)
    queryM.addMetric('cpu_idle')
    queryM.addMetricOp(Query.AVG,'netdev_bytes_r')
    print(queryM.getMetrics())
    # Create query with keys
    queryK = Query()
    queryK.setUseMetrics(False)
    queryK.addKey('host1|CPU|cpu_idle')
    queryK.addKey('host2|Network|eth0|netdev_packets_s')
    print(queryK.getKeys())
    # filter (metric)
    queryM.addFilter('node','host3')
    queryM.addFilter('netdev_name','eth[01]')
    print(queryM.getFilters())
    # filter (key): should not work
    try:
        queryK.addFilter('node','host3')
    except Exception as e:
        print('Caught exception: {0}'.format(e))
    # groupByMetrics
    queryM.addGroupByMetric('netdev_name')
    print(queryM.getGroupByMetrics())
    # time specification
    queryM.set_timeBounds("2014-03-24 09:00:00", "2014-03-30 09:00:00");
    print(queryM.getTimeSpec());
    queryK.set_timeLastNBuckets(100);
    print(queryK.getTimeSpec());
    # bucket_size
    queryM.setBucketSize(60);
    print(queryM.getBucketSize());
         
    print('Done')
    