'''
/* IBM_PROLOG_BEGIN_TAG                                                   */
/* This is an automatically generated prolog.                             */
/*                                                                        */
/* queryHandler/QueryHandler.py                                           */
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
Created on Feb 4, 2017

@author: nschuld
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
            parent = parent.pop()
        return parent

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

    def is_counter(self):
        '''column has counter type values in keys'''
        return self.semType != 1

    def probably_stale(self):
        ''' checks whether at least on key has data in the current domain, if not object might be gone'''
        for key in self.flat_keys:
            for domain in key.domains:
                if domain.domainID == 1:
                    return False
        return True

    def bucket_sizes(self, row_time):
        '''get a set of bucket sizes for the keys in this column'''
        buckets = set()
        for key in self.flat_keys:
            for domain in key.domains:
                if domain.start <= row_time <= domain.end:
                    buckets.add(domain.bucketSize)
        if not buckets:  # no domain found for the time given
            buckets.add(1)
        return buckets

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
        return '|'.join([self.parent, self.sensor, '|'.join(self.identifier), self.metric])

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

        if self.query:
            if self.query.normalize_rates:
                self._normalize_rates()

            if len(self.query.measurements) > 0:
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
        for item in self.json["rangeData"]:
            dkey = item.get('key')
            for domain in item.get('domains'):
                domains_by_key[dkey].append(Domain(**domain))

        for count, item in enumerate(legendItems):
            keys = item['keys']
            parsedKeys = tuple(Key._from_string(key, tuple(domains_by_key.get(key)))
                               for key in keys)
            col_info = ColumnInfo(item['caption'], item['semType'], parsedKeys, count)
            columnInfos.append(col_info)
        return columnInfos

    def __parseRows(self):
        return [Row(**item) for item in self.json['rows']]

    def _findIdentifiers(self):
        ids = []  # not a set or dict because order matters
        for ci in self.columnInfos:
            p = set(key.parent for key in ci.keys)
            parents = ",".join(p)

            id_item = (parents, ci.identifiers)
            if id_item not in ids:
                ids.append(id_item)
        return ids

    def _normalize_rates(self):
        '''for all counter columns normalize data to "per second" '''
        for column in self.columnInfos:
            if column.is_counter():
                for row in self.rows:
                    val = row.values[column.column]
                    if val:
                        buckets = column.bucket_sizes(row.tstamp)
                        if len(buckets) > 1 and len(column.keys) == 1:
                            samples = row.nsamples[column.column]
                            for bs in buckets:
                                if samples * bs == self.header.bsize:
                                    buckets = set([bs])
                                    break
                        buckets.add(self.header.bsize)
                        d = max(buckets)
                        row.values[column.column] = val / d

    def _add_calculated_colunm_headers(self):
        '''for each measurement create a result column for each ID '''
        for q_name, prg in self.query.measurements.items():
            for parent, myid in self.ids:
                key_aq = []
                for step in prg:
                    if step not in Calculator.OPS and not is_number(step):
                        metric = step
                        idx = self._index_by_metric_id(metric, myid)
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
                        idx = self._index_by_metric_id(step, myid)
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

    def _index_by_metric_id(self, metric, identifier):
        '''get index to columInfo / values for a given metric and identifier'''
        idx = self.index_cache.get((metric, identifier), -1)
        if idx != -1:
            return idx

        for ci in self.columnInfos:
            # check for k.name too? handle parent?
            if ci.keys[0].metric == metric and ci.identifiers == identifier:
                self.index_cache[(metric, identifier)] = ci.column
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

    def has_multiple_domains(self):
        '''check whether result has data from different aggregation domains'''
        start = self.rows[0].tstamp
        end = self.rows[-1].tstamp

        min_domain = 9999
        max_domain = 0

        for column in self.columnInfos:
            min_domain = min(min_domain, min(column.bucket_sizes(start)))
            max_domain = max(max_domain, max(column.bucket_sizes(end)))

        return min_domain != max_domain

    def latest(self, column):
        ''' get last non null value of a column'''
        return self.__colstat(column, lambda x: next(iter(x)), reverse=True)

    def min(self, column):
        ''' get minimum value of a column'''
        return self.__colstat(column, min)

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
            return fn(list(filter(None, data)))  # list is needed for py 3
        except Exception:
            return None


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

    OPS = {"+": operator.add, "-": operator.sub, '*': operator.mul, '/': div}

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

    def __init__(self, server, port=9084, logger=None):
        '''
        Constructor requires name (or IP address) of the server and the port number (default: 9084)
        '''
        self.server = server
        self.remote_ip = socket.gethostbyname(server)
        self.port = port
        self.logger = logger 

    def __do_query(self, data):
        '''handle communication which collector node'''
        if data is None or len(data) == 0:
            return None
        
        timer = time.clock if sys.platform == 'win32' else time.time
        
        chunks = []
        msg = ''
        endstr = '.\n'
        if sys.version >= '3':
            msg = b''
            endstr = b'.\n'
            
        try:
            with closing(socket.socket(socket.AF_INET,socket.SOCK_STREAM)) as sock:
                sock.settimeout(60)
                sock.connect((self.remote_ip, self.port))
                if sys.version >= '3':
                    data = bytes(data, 'UTF-8')
                sock.sendall(data)

                while True:
                    tstart = timer()
                    r, _, _ = select.select([sock], [], [])
                    if r:
                        chunk = sock.recv(4096)
                        if chunk == '':
                            raise IOError('QueryHandler: Socket connection broken, received no data')
                        chunks.append(chunk)
                        if chunk.endswith(endstr):
                            tend1 = timer()
                            count = len(chunks)
                            msg = msg.join(chunks)
                            if sys.version >= '3':
                                msg = msg.decode('UTF-8')
                            lmsg = len(msg)
                            tend2 = timer()
                            self.logger.debug("__do_query completed. Received %s chunks of totally %s data within % s seconds. \
Total time spent for string reading and decoding %s seconds" %(count,lmsg,(tend1 - tstart),(tend2-tstart)))
                            break
        except socket.timeout as e:
            print('socket timeout')
            self.logger.error(e)
        except Exception as e:
            self.logger.error(e)
            return None
        res = msg.split('\n')[0]
        if res.startswith('Error'):
            if self.logger:
                self.logger.debug('QueryHandler: query returned no data: {0}'.format(res))
            return None
        return res

    def getTopology(self, ignoreMetrics=False):
        '''
        Returns complete topology as a single JSON string
        ignoreAttrs can be used to skip the (leaf) metrics
        '''
        queryString = 'topo \n'
        if ignoreMetrics:
            queryString = 'topo -a \n'

        return self.__do_query(queryString)

    def runQuery(self, query):
        '''
        runQuery: executes the given query based on the arguments.
        :param query: a query class instance
        '''
        res = self.__do_query(str(query))

        if res is None:
            if self.logger:
                self.logger.error('QueryHandler: query response has no data results')
            return None
        try:
            result = json.loads(res)
            return QueryResult(query, result)
        except Exception as e:
            self.logger.error(
                'QueryHandler: query response not valid json: {0} {1}'.format(res[:20], e))
        try:
            res = res.decode('utf-8', 'ignore')
            result = json.loads(res, strict=False)
            return QueryResult(query, result)
        except Exception as e:
            self.logger.error(
                'QueryHandler: query response not valid json: {0} {1}'.format(res[:20], e))

    @staticmethod
    def getQueryHandler():
        server = '127.0.0.1'
        port = 9084

        return QueryHandler2(server, port)
