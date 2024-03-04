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
import sys
import os
import errno
import logging
import analytics

from logging import handlers
from queryHandler.QueryHandler import PerfmonConnError
from queryHandler import SensorConfig
from __version__ import __version__
from messages import ERR, MSG
from bridgeLogger import configureLogging, getBridgeLogger
from confParser import getSettings
from metadata import MetadataHandler
from opentsdb import OpenTsdbApi
from prometheus import PrometheusExporter
from watcher import ConfigWatcher
from cherrypy import _cperror
from cherrypy.lib.cpstats import StatsPage

ENDPOINTS = {}


def processFormJSON(entity):
    ''' Used to generate JSON when the content
    is of type application/x-www-form-urlencoded. Added for grafana 3 support'''

    body = entity.fp.read()
    if len(body) > 0:
        cherrypy.serving.request.json = json.loads(body.decode('utf-8'))
    else:
        cherrypy.serving.request.json = json.loads('{}')


def load_endpoints(file_name):
    dirname, _ = os.path.split(os.path.abspath(__file__))
    conf_file = os.path.join(dirname, file_name)
    if os.path.isfile(conf_file):
        with open(conf_file) as f:
            d = json.load(f)
    api = file_name.split('_', 1)[0]
    ENDPOINTS[api] = d


def setup_cherrypy_logging(args):

    log = cherrypy.log

    # Remove the default FileHandlers if present.
    log.error_file = ""
    log.access_file = ""

    path = args.get('logPath')
    if not os.path.exists(path):
        os.makedirs(path)
    accesslog = os.path.join(path, 'cherrypy_access.log')
    errorlog = os.path.join(path, 'cherrypy_error.log')

    # Make a new RotatingFileHandler for the error log.
    handler = handlers.RotatingFileHandler(errorlog, 'a', 1000000, 10)
    handler.setLevel(logging.INFO)
    handler.setFormatter(cherrypy._cplogging.logfmt)
    log.error_log.addHandler(handler)

    # Make a new RotatingFileHandler for the access log.
    handler = handlers.RotatingFileHandler(accesslog, 'a', 1000000, 10)
    handler.setLevel(logging.INFO)
    handler.setFormatter(cherrypy._cplogging.logfmt)
    log.access_log.addHandler(handler)


def updateCherrypyConf(args):

    globalConfig = {'global': {'error_page.default': format_default_error_page,
                               'request.error_response': handle_error},
                    }

    cherrypy.config.update(globalConfig)

    dirname, _ = os.path.split(os.path.abspath(__file__))
    customconf = os.path.join(dirname, 'mycherrypy.conf')
    cherrypy.config.update(customconf)
    cherrypy.server.unsubscribe()


def bind_opentsdb_server(args):
    opentsdb_server = cherrypy._cpserver.Server()
    opentsdb_server.socket_port = args.get('port')
    opentsdb_server._socket_host = '0.0.0.0'
    if args.get('protocol') == "https":
        certPath = os.path.join(args.get('tlsKeyPath'), args.get('tlsCertFile'))
        keyPath = os.path.join(args.get('tlsKeyPath'), args.get('tlsKeyFile'))
        opentsdb_server.ssl_module = 'builtin'
        opentsdb_server.ssl_certificate = certPath
        opentsdb_server.ssl_private_key = keyPath
    opentsdb_server.statistics = analytics.cherrypy_internal_stats
    opentsdb_server.subscribe()


def bind_prometheus_server(args):
    prometheus_server = cherrypy._cpserver.Server()
    prometheus_server.socket_port = args.get('prometheus')
    prometheus_server._socket_host = '0.0.0.0'
    certPath = os.path.join(args.get('tlsKeyPath'), args.get('tlsCertFile'))
    keyPath = os.path.join(args.get('tlsKeyPath'), args.get('tlsKeyFile'))
    prometheus_server.ssl_module = 'builtin'
    prometheus_server.ssl_certificate = certPath
    prometheus_server.ssl_private_key = keyPath
    prometheus_server.statistics = analytics.cherrypy_internal_stats
    prometheus_server.subscribe()


def resolveAPIKeyValue(storedKey):
    keyValue = None
    if "/" in str(storedKey):
        with open(storedKey) as file:
            keyValue = file.read().rstrip()
        return keyValue
    else:
        return storedKey


def refresh_metadata(refresh_all=False):
    md = MetadataHandler()
    md.update(refresh_all)


def handle_error():
    response = cherrypy.response
    response.status = 500
    response.headers['Content-Type'] = 'application/json;charset=utf-8'
    response.headers["Content-Length"] = len(json.dumps(
        ['Sorry for Error!!! Please check the log']).encode("utf-8"))
    response.body = json.dumps(['Sorry for Error!!! Please check the log']).encode("utf-8")
    logger = getBridgeLogger()
    logger.error(MSG['UnexpecterError'].format(
        _cperror.format_exc()))


def format_default_error_page(status=404, message="Bad Request",
                              traceback=cherrypy.serving.request.show_tracebacks,
                              version='1.0'
                              ):
    template = {}
    template['error'] = status
    template['reason'] = message
    logger = getBridgeLogger()
    if traceback:
        logger.error(
            MSG['UnexpecterError'].format(_cperror.format_exc()))
    else:
        logger.details(f"HTTPError: {status} {message}")
    response = cherrypy.serving.response
    response.headers['Content-Type'] = 'application/json;charset=utf-8'
    response.headers["Content-Length"] = len(
        json.dumps(template).encode("utf-8"))
    return json.dumps(template).encode("utf-8")


def main(argv):
    # parse input arguments
    args, msg = getSettings(argv)
    if not args:
        print(msg)
        return

    registered_apps = []

    # prepare the logger
    logger = configureLogging(args.get('logPath'), args.get('logFile', None),
                              args.get('logLevel'))

    # prepare cherrypy logging configuration
    setup_cherrypy_logging(args)

    # prepare cherrypy server configuration
    updateCherrypyConf(args)

    # prepare metadata
    try:
        logger.info("%s", MSG['BridgeVersionInfo'].format(__version__))
        logger.details('zimonGrafanaItf invoked with parameters:\n %s',
                       "\n".join("{}={}".format(k, v)
                                 for k, v in args.items() if not
                                 k == 'apiKeyValue'))
        mdHandler = MetadataHandler(logger=logger, server=args.get('server'),
                                    port=args.get('serverPort'),
                                    apiKeyName=args.get('apiKeyName'),
                                    apiKeyValue=resolveAPIKeyValue(args.get('apiKeyValue')),
                                    caCertPath=args.get('caCertPath'),
                                    includeDiskData=args.get('includeDiskData'),
                                    sleepTime=args.get('retryDelay', None)
                                    )
    except (AttributeError, TypeError, ValueError) as e:
        # logger.details('%s', MSG['IntError'].format(str(e)))
        print('%s', MSG['IntError'].format(str(e)))
        logger.error(MSG['MetaError'])
        return
    except IOError as e:
        if e.errno == errno.ENOENT:
            # file does not exist'
            logger.error(f'Error reading file, Reason: {e}')
        elif e.errno == errno.EACCES:
            # file cannot be read
            logger.error(f'Error accessing file, Reason: {e}')
        return
    except (PerfmonConnError, Exception) as e:
        logger.error('%s', MSG['CollectorErr'].format(str(e)))
        return
    except (OSError) as e:
        logger.details('%s', MSG['IntError'].format(str(e)))
        logger.error("ZiMon sensor configuration file not found")
        return

    if args.get('port', None):
        bind_opentsdb_server(args)
        api = OpenTsdbApi(logger, mdHandler, args.get('port'))

        cherrypy.tree.mount(api, '/api/query',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                              'request.body.processors': {'application/x-www-form-urlencoded': processFormJSON}
                              }
                             }
                            )
        # query for metric name (openTSDB: zimon extension returns keys as well)
        cherrypy.tree.mount(api, '/api/suggest',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        # query for tag name and value, given a metric (openTSDB)
        cherrypy.tree.mount(api, '/api/search/lookup',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        # query to force update of metadata (zimon feature)
        cherrypy.tree.mount(api, '/api/update',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        # query for list configured zimon sensors
        cherrypy.tree.mount(api, '/sensorsconfig',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        # query for list of aggregators (openTSDB)
        cherrypy.tree.mount(api, '/api/aggregators',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        # query for list of filters (openTSDB)
        cherrypy.tree.mount(api, '/api/config/filters',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        registered_apps.append("OpenTSDB Api listening on Grafana queries")

    if args.get('prometheus', None):
        bind_prometheus_server(args)
        load_endpoints('prometheus_endpoints.json')
        exporter = PrometheusExporter(logger,
                                      mdHandler,
                                      args.get('prometheus'),
                                      args.get('rawCounters', False))
        exporter.endpoints.update(ENDPOINTS.get('prometheus',
                                                {}))

        # query to force update of metadata (zimon feature)
        cherrypy.tree.mount(exporter, '/update',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        # query for list configured zimon sensors
        cherrypy.tree.mount(exporter, '/sensorsconfig',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        # query for all metrics (PrometheusExporter)
        cherrypy.tree.mount(exporter, '/metrics',
                            {'/':
                             {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                             }
                            )
        if len(exporter.endpoints) > 0:
            for endpoint in exporter.endpoints.keys():
                cherrypy.tree.mount(exporter, endpoint,
                                    {'/':
                                     {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
                                     }
                                    )
        registered_apps.append("Prometheus Exporter Api listening on Prometheus requests")
        cherrypy.tree.mount(StatsPage(), '/cherrypy_internal_stats')

    logger.info("%s", MSG['sysStart'].format(sys.version, cherrypy.__version__))

    try:
        files_to_watch = SensorConfig.get_config_paths()
        watcher = ConfigWatcher(files_to_watch, refresh_metadata, refresh_all=True)
        cherrypy.engine.subscribe('start', watcher.start_watch)
        cherrypy.engine.subscribe('stop', watcher.stop_watch)
        cherrypy.engine.start()
        cherrypy.engine.log('test')
        logger.info("%s", MSG['ConnApplications'].format(",\n ".join(registered_apps)))
        logger.info("server started")
        with open("/proc/{}/stat".format(os.getpid())) as f:
            data = f.read()
        foreground_pid_of_group = data.rsplit(" ", 45)[1]
        is_in_foreground = str(os.getpid()) == foreground_pid_of_group
        logger.debug("Server PID: {}. Process started in the foreground: {}".
                     format(os.getpid(), is_in_foreground))
        cherrypy.engine.block()
    except TypeError as e:
        logger.error("Server request could not be proceed. Reason: {}".format(e))
        raise cherrypy.HTTPError(500, ERR[500])
    except OSError as e:
        logger.error("STOPPING: Server request could not be proceed. \
        Reason: {}".format(e))
        cherrypy.engine.stop()
        cherrypy.engine.exit()

    api = exporter = None

    logger.warning("server stopped")


if __name__ == '__main__':
    main(sys.argv[1:])
