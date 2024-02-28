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

Created on Feb 4, 2017

@author: NSCHULD
'''
#


def isString(val):
    return isinstance(val, str)


class Query(object):
    '''
    Updated Version of a Zimon Query Interface for metric queries only
    Allows construction most queries with the  Ctor. Also adds a fluent API for other cases
    '''

    # OPERATION TYPES
    NOP = 0  # No operation (metric only)
    SUM = 1  # sum operation
    AVG = 2   # avg operation
    MAX = 3  # max operation
    MIN = 4   # min operation
    RATE = 5  # rate operation
    OPERATIONS = {
        NOP: "{0}", SUM: "sum({0})", AVG: "avg({0})", MAX: "max({0})", MIN: "min({0})", RATE: "rate({0})"}
    OPS_STR = {'nop': NOP, 'noop': NOP, 'sum': SUM, 'avg': AVG, 'max': MAX, 'min': MIN, 'rate': RATE}

    FIELDS = set(["gpfs_cluster_name", "gpfs_disk_name", "gpfs_diskpool_name",
                  "gpfs_disk_usage_name", "gpfs_fset_name", "gpfs_fs_name",
                  "mountPoint", "netdev_name", 'diskdev_name', "node", "db_name",
                  "operation", "protocol", "waiters_time_threshold", "export",
                  "nodegroup", "account", "filesystem", "tct_csap", "tct_operation", "cloud_nodeclass"])

    DISK_CAP_METRICS = set(["gpfs_disk_disksize", "gpfs_disk_free_fullkb", "gpfs_disk_free_fragkb",
                            "gpfs_pool_disksize", "gpfs_pool_free_fragkb", "gpfs_pool_free_fullkb",
                            "gpfs_fs_inode_used", "gpfs_fs_inode_free", "gpfs_fs_inode_alloc", "gpfs_fs_inode_max"])

    def __init__(self, metrics=None, bucketsize=1, filters=None, groupby=None, includeDiskData=False):
        '''
        Constructor, filters and groupby must be preformmated
        '''
        self.includeDiskData = includeDiskData     # disk or archived data (False or True)
        self.bucket_size = bucketsize              # bucket size

        self.metrics = []             # list of string metrics
        self.filters = []             # list of filters
        self.groupby = []             # list of groupBy metrics

        if metrics is not None:
            if (isString(metrics)):
                self.metrics = metrics.split(',')
            elif iter(metrics) is not iter(metrics):
                self.metrics = metrics
            else:
                raise ValueError("metrics are not in the right format")

        if filters is not None:
            if (isString(filters)):
                self.filters = filters.split(',')
            elif iter(filters) is not iter(filters):
                self.filters = filters
            else:
                raise ValueError("filters are not in the right format")

        if groupby is not None:
            if (isString(groupby)):
                self.groupby = groupby.split(',')
            elif iter(groupby) is not iter(groupby):
                self.groupby = groupby
            else:
                raise ValueError("groupby are not in the right format")

        self.timeRep = ' now'         # string time representation
        self.measurements = {}
        self.normalize_rates = True
        self.rawData = False
        self.key = None
        self.sensor = None

    def addMetric(self, metric, op=None):
        '''
        Add metric operation to the query, e.g., "sum(cpu_idle)" using the input
        metric name and operation type
        '''
        if isString(op):
            op = Query.OPS_STR.get(op.lower(), Query.NOP)

        metricop = Query.OPERATIONS.get(op, '{0}').format(metric)
        self.metrics.append(metricop)
        return self

    def addKey(self, key):
        self.key = key

    def addMetricsGroup(self, sensor):
        self.sensor = sensor

    def addGroupByMetric(self, groupByMetric):
        '''Add a metric to be used in grouping multi-metric (operation) columns'''
        if groupByMetric not in self.FIELDS:
            raise ValueError("unknown groupby type %s" % groupByMetric)
        self.groupby.append(groupByMetric)
        return self

    def addFilter(self, field, value):
        '''Add a filter of the form "field=value" where
        the field is an identifier key element and
        value is a constant or a regular expression'''
        if field not in self.FIELDS:
            raise ValueError("unknown filter type %s" % field)
        newFilter = field + "=" + value
        if newFilter not in self.filters:
            self.filters.append(newFilter)
        return self

    def setBucketSize(self, bucketsize):
        self.bucket_size = bucketsize
        return self

    def setTime(self, tstart='', tend='', num_buckets=0, duration=0):
        '''
        Specify time bounds
        '''
        self.timeRep = 'now'  # default

        if tstart:
            self.timeRep = "tstart " + tstart
        if tend:
            if not tstart:
                self.timeRep = ''
            self.timeRep += " tend " + tend
        if num_buckets:
            self.timeRep = "last " + str(num_buckets)
        if duration:
            self.timeRep = "duration " + str(duration)
        return self

    def addComputation(self, name, prg):
        '''add a named, derived column to the resultset
        :param name: name used for the colum in the reultset
        :param prg: comma delimited list of steps to take,
        step can be metric name, operation or number (UPN notation)

        '''
        self.measurements[name] = prg.split(',')
        return self

    def addRatio(self, metric1, metric2, op=NOP):
        '''
        Add ratio computation
        '''
        metricop1 = Query.OPERATIONS.get(op, '{0}').format(metric1)
        metricop2 = Query.OPERATIONS.get(op, '{0}').format(metric2)
        if metricop1 not in self.metrics:
            self.metrics.append(metricop1)
        if metricop2 not in self.metrics:
            self.metrics.append(metricop2)
        self.addComputation(metricop1 + '/' + metricop2, metric1 + ',' + metric2 + ',/')
        return self

    def addMeasurement(self, meassure):
        '''
        Add a pre-defined measurement
        '''
        self.metrics.extend(meassure.metrics)
        self.groupby.extend(meassure.groupby)
        self.filters.extend(meassure.filters)
        self.measurements.update(meassure.measurements)
        return self

    def __str__(self):
        # dd = '-a' if self.includeDiskData else ''
        # Workaround for RTC Defect 280368: Zimon capacity query does not return all results (seen on CNSA)
        dd = ''
        if self.includeDiskData:
            dd = '-a'
        if self.metrics:
            for metric in self.metrics:
                if any(map(metric.__contains__, self.DISK_CAP_METRICS)):
                    dd = '-ar'
                    break
        elif (self.sensor and self.sensor in ("GPFSDiskCap",
                                              "GPFSPoolCap",
                                              "GPFSInodeCap")
              ):
            dd = '-ar'

        if self.rawData:
            raw = '-z'
        else:
            raw = ''

        if self.sensor is not None:
            queryString = 'get -j {0} {1} group {2} bucket_size {3} {4}'.format(
                dd, raw, self.sensor, self.bucket_size, self.timeRep)
        elif self.key is not None:
            queryString = 'get -j {0} {1} {2} bucket_size {3} {4}'.format(
                dd, raw, self.key, self.bucket_size, self.timeRep)
        else:
            queryString = 'get -j {0} {1} metrics {2} bucket_size {3} {4}'.format(
                dd, raw, ','.join(self.metrics), self.bucket_size, self.timeRep)

        if self.filters:
            queryString += ' from ' + ",".join(self.filters)

        if self.groupby:
            queryString += ' group_by ' + ','.join(self.groupby)
        queryString += '\n'
        return queryString


class Measurement(Query):
    '''Just a marker class'''

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
