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

from collections import namedtuple, defaultdict
from contextlib import closing
import inspect
from itertools import chain
import json
import operator
import socket
import sys
import time
import select

from .PerfmonRESTclient import perfHTTPrequestHelper, createRequestDataObj, getAuthHandler
try:
    import SysmonLogger
except Exception:
    pass

class PerfmonConnError(Exception):
    pass


EMPTY = json.loads('{"header" : {"bcount" : 0, "bsize" : 0, "t_start" : 0, "t_end" : 0 }, "legend" : [], "rows" : [], "rangeData": [] }')

HeaderData = namedtuple('HeaderData', 'bcount, bsize, t_start, t_end')
'''structure for header data           int,   int,   long,   long '''


class Row(namedtuple('_Row', 'tstamp, values, nsamples')):
    '''structure for a row of data long, [numbers], [numbers]'''
    __slots__ = ()

    @property
    def time_str(self):
        return time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(self.tstamp))

    def is_empty(self):
        return sum(self.nsamples) == 0
        # return len(self.values) == self.values.count(None)


class ColumnInfo(namedtuple('_ColumnInfo', 'name, semType, keys, column')):
    '''header data for each column          string, int, [KEY], int '''
    __slots__ = ()

    @property
    def key_str(self):
        '''string which includes all keys'''
        return ', '.join(str(key) for key in self.keys if key)

    @property
    def identifiers(self):
        ''' get all identifiers from all Keys'''
        ident = set(key.identifier for key in self.flat_keys if key.identifier)
        if len(ident) == 1:
            return ident.pop()
        return tuple(ident)

    @property
    def parents(self):
        ''' get parent(s) of this column'''
        parent = set(key.parent for key in self.flat_keys if key.parent)
        if len(parent) == 1:
            return parent.pop()
        return tuple(parent)

    @property
    def flat_keys(self):
        '''for computed columns we have multiple lists of keys, flatten it to a simple list'''
        if len(self.keys) > 1 or isinstance(self.keys[0], list):
            flat_keys = list(chain.from_iterable(self.keys))
            if not isinstance(flat_keys[0], Key):
                flat_keys = self.keys
        else:
            flat_keys = self.keys
        return flat_keys

    def __hash__(self):
        return hash((self.name, self.key_str))

    def __eq__(self, other):
        return (self.name, self.key_str) == (other.name, other.key_str)

    def __ne__(self, other):
        return not(self == other)


class Key(namedtuple('_Key', 'parent, sensor, identifier, metric, domains')):
    '''data structure of a Key string, string, tuple of strings (can be empty), string, tuple of domains
    describing parent (node or cluster), sensor and metric for the data
    as well as the identifier if the metric applies to multiple items.
    Also joined are the aggregation domains of that key which describe the effective bucket size'''
    __slots__ = ()

    @classmethod
    def _from_string(cls, key, domains):
        '''Split a string like node.localnet.com|Network|eth0|netdev_bytes_s to its consisting parts'''
        items = key.split('|')
        return Key(items[0], items[1], tuple(items[2:-1]), items[-1], domains)

    def __str__(self):
        return '|'.join([self.parent, self.sensor, '|'.join(self.identifier), self.metric]).replace('||', '|')

    def shortKey_str(self):
        return '|'.join([self.parent, self.sensor, '|'.join(self.identifier)])

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash((self.parent, self.sensor, self.identifier, self.metric))

    def __eq__(self, other):
        return (self.parent, self.sensor, self.identifier, self.metric) == (other.parent, other.sensor, other.identifier, other.metric)

    def __ne__(self, other):
        return not(self == other)


class Domain(namedtuple('_domain', 'domainID, start, end, bucketSize')):
    '''data structure of a domain,     int,   int,    int,  int'''
    __slots__ = ()

    @property
    def start_str(self):
        return time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(self.start))

    @property
    def end_str(self):
        return time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(self.end))


DEFAULT_DOMAIN = Domain(99, 0, 6666666666, 666)


class QueryResult:
    '''Wrapper for the data returned by a Zimon query'''

    def __init__(self, query, res_json):
        self.query = query
        self.json = res_json

        self.header = self.__parseHeader()
        self.columnInfos = self.__parseLegend()
        self.rows = self.__parseRows()

        self.index_cache = {}  # (metric, id) -> row value index
        self.ids = self._findIdentifiers()

        if self.query and len(self.query.measurements) > 0:
            self._add_calculated_colunm_headers()

            calc = Calculator()
            for row in self.rows:
                self._add_calculated_row_data(calc, row)

    def __parseHeader(self):
        item = self.json['header']
        return HeaderData(**item)

    def __parseLegend(self):
        legendItems = self.json['legend']
        columnInfos = []

        domains_by_key = defaultdict(list)
        if "rangedata" in self.json:
            for item in self.json["rangeData"]:
                dkey = item.get('key')
                for domain in item.get('domains'):
                    domains_by_key[dkey].append(Domain(**domain))
                if len(domains_by_key[dkey]) == 0:
                    domains_by_key[dkey].append(DEFAULT_DOMAIN)

        for count, item in enumerate(legendItems):
            keys = item['keys']
            parsedKeys = tuple(Key._from_string(key, tuple(domains_by_key.get(key, [DEFAULT_DOMAIN]))) for key in keys)
            col_info = ColumnInfo(item['caption'], item['semType'], parsedKeys, count)
            columnInfos.append(col_info)
        return columnInfos

    def __parseRows(self):
        return [Row(**item) for item in self.json['rows']]

    def _findIdentifiers(self):
        ids = []  # not a set or dict because order matters
        for ci in self.columnInfos:
            p = set(key.parent for key in ci.keys)
            if len(p) == 1:
                parents = p.pop()
            else:
                parents = tuple(p)

            id_item = (parents, ci.identifiers)
            if id_item not in ids:
                ids.append(id_item)
        return ids

    def _add_calculated_colunm_headers(self):
        '''for each measurement create a result column for each ID '''
        for q_name, prg in self.query.measurements.items():
            for parent, myid in self.ids:
                key_aq = []
                for step in prg:
                    if step not in Calculator.OPS and not is_number(step):
                        metric = step
                        idx = self._index_by_metric_id(metric, parent, myid)
                        if idx != -1:
                            # key_aq.append([key for key in self.columnInfos[idx].keys if key])
                            key_aq.extend(key for key in self.columnInfos[idx].keys if key)
                nextidx = max(ci.column for ci in self.columnInfos) + 1
                self.columnInfos.append(ColumnInfo(q_name, 15, (tuple(key_aq)), nextidx))

    def _add_calculated_row_data(self, calc, row):
        '''for each measurement calculate result column for each ID for the given row'''
        for parent, myid in self.ids:
            for q_name, prg in self.query.measurements.items():
                calc.clear()
                for step in prg:
                    if step in Calculator.OPS:
                        calc.op(step)
                    elif is_number(step):
                        calc.push(float(step))
                    else:
                        idx = self._index_by_metric_id(step, parent, myid)
                        if idx != -1:
                            value = row.values[idx]
                            if value is None:
                                calc.clear()
                                calc.push(None)
                                break
                            calc.push(value)
                        else:
                            raise ValueError('prg step not identified %s', step)
                res = calc.pop()
                row.values.append(res)

    def __getitem__(self, index):
        return self.rows[index]

    def _index_by_metric_id(self, metric, parent, identifier):
        '''get index to columInfo / values for a given metric and identifier'''
        idx = self.index_cache.get((metric, parent, identifier), -1)
        if idx != -1:
            return idx

        for ci in self.columnInfos:
            # check for k.name too? handle parent?
            if ci.keys[0].metric == metric and ci.identifiers == identifier and ci.parents == parent:
                self.index_cache[(metric, parent, identifier)] = ci.column
                return ci.column
        return -1

    def drop_base_metrics(self):
        '''remove all headers and data columns which were used to compute a measurement'''
        columns = sorted(self.index_cache.values(), reverse=True)
        for col_idx in columns:
            del self.columnInfos[col_idx]
            for row in self.rows:
                del row.values[col_idx]

        renumberedColumns = []
        for idx, col in enumerate(self.columnInfos):
            renumberedColumns.append(ColumnInfo(col.name, col.semType, col.keys, idx))
        self.columnInfos = renumberedColumns

        return self

    def remove_rows_with_no_data(self):
        self.rows = [r for r in self.rows if not r.is_empty()]

    def reduce(self):
        # self.remove_rows_with_no_data()
        values = [self.latest(col) for col in self.columnInfos]
        ts = self.rows[-1].tstamp if len(self.rows) > 0 else int(time.time())
        return Row(ts, values, [1] * len(values))

    def check_rows_have_no_data(self):
        return True if(len([r for r in self.rows if not r.is_empty()]) == 0) else False

    def latest(self, column):
        ''' get last non null value of a column'''
        return self.__colstat(column, lambda x: next(iter(x)), reverse=True)

    def min(self, column):
        ''' get minimum value of a column'''
        return self.__colstat(column, min)

    def downsampleResults(self, interval, aggregator='avg'):
        ''' Performs downsampling of QueryResult.rows with specified aggregation method and interval'''
        try:
            func = __builtins__[aggregator]
            return self.__downsample(func, interval)
        except Exception:
            return self.__downsample(self.dAVG, interval)

    def max(self, column):
        ''' get maximum value of a column'''
        return self.__colstat(column, max)

    def sum(self, column):
        ''' get sum of values of a column'''
        return self.__colstat(column, sum)

    def avg(self, column):
        ''' get average value of column'''
        s = self.sum(column)
        l = self.__colstat(column, len)
        return s / (1.0 * l)

    def dAVG(self, valList):
        ''' get average value of values'''
        s = sum(valList)
        l = len(valList)
        if l == 0:
            return None
        return int(round(s / l))

    def __colstat(self, column, fn, reverse=False):
        if isinstance(column, ColumnInfo):
            idx = column.column
        else:
            idx = column
        if reverse:
            data = (row.values[idx] for row in reversed(self.rows))
        else:
            data = (row.values[idx] for row in self.rows)
        try:
            return fn(list(filter(lambda x: x is not None, data)))
        except Exception:
            return None

    def __downsample(self, fn, interval, column='all'):

        aggrRows = []

        for i in range(0, len(self.rows), interval):
            rows_chunk = self.rows[i:i + interval]
            chunk_values = [row.values for row in rows_chunk]
            aggr_values = [None] * len(self.columnInfos)
            # iterate through each column of the time interval data chunk
            for idx, column_values in enumerate(zip(*chunk_values)):
                try:
                    if len(column_values) == column_values.count(None):
                        aggr_value = None
                    else:
                        aggr_value = fn(list(filter(lambda x: x is not None, column_values)))
                except Exception:
                    aggr_value = None
                aggr_values[idx] = aggr_value

            tIdx = (i + len(chunk_values)) - 1
            aggrRows.append({"tstamp": self.rows[tIdx].tstamp, "values": aggr_values, "nsamples": len(rows_chunk)})

        return [Row(**item) for item in aggrRows]


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass


def div(a, b):  # defined anew because of py 2/3 difference
    try:
        return float(a) / float(b)
    except:
        return 0


class Calculator(object):
    '''simple UPN calculator'''

    OPS = {"+": operator.add, "-": operator.sub, '*': operator.mul, '/': div,
           ">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}

    def __init__(self):
        self.stack = []

    def push(self, arg):
        self.stack.append(arg)
        return self

    def peek(self):
        return self.stack[0]

    def pop(self):
        return self.stack.pop()

    def clear(self):
        del self.stack[:]

    def op(self, operation):
        if (operation in Calculator.OPS):
            operation = Calculator.OPS[operation]

        if (inspect.isbuiltin(operation)):
            if operation.__name__ in ('neg', 'pos', 'abs', 'not_', 'inv'):
                ary = 1
            else:
                ary = 2
        else:
            ary = len(inspect.getargspec(operation)[0])

        if ary == 1:
            a = self.stack.pop()
            c = operation(a)
            self.push(c)
        elif ary == 2:
            a = self.stack.pop()
            b = self.stack.pop()
            c = operation(b, a)
            self.push(c)
        else:
            raise ValueError('unknown operator')
        return self


class QueryHandler2:
    '''
    Interface class to access ZIMon data
    '''

    def __init__(self, server, port, logger, apiKeyName, apiKeyValue):
        '''
        Constructor requires name (or IP address) of the server and the port number (default: 9084)
        '''
        self.__keyName = apiKeyName
        self.__keyValue = apiKeyValue
        self.server = server
        self.remote_ip = socket.gethostbyname(server)
        self.port = port
        self.logger = logger

    @property
    def apiKeyData(self):
        return self.__keyName, self.__keyValue

    def getTopology(self, ignoreMetrics=False):
        '''
        Returns complete topology as a single JSON string
        ignoreAttrs can be used to skip the (leaf) metrics
        '''
        params = None
        if ignoreMetrics:
            params = {'query': '-a'}
        res = self.__do_RESTCall('perfmon/topo', 'GET', params)

        if res is None:
            self.logger.error("QueryHandler: getTopology returns no data.")
            return
        try:
            result = json.loads(res, strict=False)
            return result
        except Exception as e:
            self.logger.error(
                'QueryHandler: getTopology response not valid json: {0} {1}'.format(res[:20], e))

    def getAvailableMetrics(self):
        '''
        Returns output from topo -m
        '''
        params = {'query': '-m'}
        return self.__do_RESTCall('perfmon/topo', 'GET', params)

    def deleteKeyFromTopology(self, keyStr, precheck=True):
        '''
        Executes the delete command for the given key
        Returns result dictionary
        '''
        # delete pre-check option
        check = '-n' if precheck == True else ''
        deleteString = f'delete {check} key {keyStr} \n'

        params = {'query': deleteString}
        response = self.__do_RESTCall('perfmon/delete', 'DELETE', params)

        if response is None:
            self.logger.debug('QueryHandler: deleteKeysFromTopology response has no data results')
            return None
        try:
            result = json.loads(response, strict=False)
            return result
        except Exception as e:
            self.logger.error(
                'QueryHandler: deleteKeysFromTopology response not valid json: {0} {1}'.format(response[:20], e))

    def runQuery(self, query):
        '''
        runQuery: executes the given query based on the arguments.
        :param query: a query class instance
        '''
        params = {'query': str(query)}
        self.logger.debug('QueryHandler: REST call perfmon/data invoked with following params: {0}'.format(params))
        res = self.__do_RESTCall('perfmon/data', 'GET', params)

        if res is None:
            self.logger.error('QueryHandler: query response has no data results')
            return None
        try:
            result = json.loads(res, strict=False)
            return QueryResult(query, result)
        except Exception as e:
            self.logger.error(
                'QueryHandler: query response not valid json: {0} {1}'.format(res[:20], e))

    def __do_RESTCall(self, endpoint, requestType='GET', params=None):
        '''
        Forward query request to the HTTPRequest client interface
        '''

        self.logger.debug("__do_RESTcall invoke __ params: {} {} {}".format(endpoint, requestType, str(params)))

        try:
            _auth = getAuthHandler(*self.apiKeyData)
            _reqData = createRequestDataObj(self.logger, requestType, endpoint, self.server, self.port, auth=_auth, params=params)
            _request = perfHTTPrequestHelper(self.logger, reqdata=_reqData)
            _request.session.verify = False
            _response = _request.doRequest()

            if _response.status_code == 200:
                return _response.content.decode('utf-8', "strict")
            elif _response.status_code == 401:
                self.logger.debug('Request headers:{}'.format(_response.request.headers))
                self.logger.debug('Request url:{}'.format(_response.request.url))
                msg = "Perfmon RESTcall error __ Server responded: {} {}".format(_response.status_code, _response.reason)
                self.logger.details(msg)
                raise PerfmonConnError("{} {}".format(_response.status_code, _response.reason))
            else:
                msg = "Perfmon RESTcall error __ Server responded: {} {}".format(_response.status_code, _response.reason)
                self.logger.warning(msg)
                if _response.content:
                    contentMsg = _response.content.decode('utf-8', "strict")
                    self.logger.details(f'Response content:{contentMsg}')
                return None
        except TypeError as e:
            self.logger.exception(e)
            # return ("", str(e), 500)  # Internal Server Error
            return None
