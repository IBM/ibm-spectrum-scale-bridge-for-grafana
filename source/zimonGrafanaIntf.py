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
import logging.handlers
import sys
import os
import errno

from queryHandler.QueryHandler import PerfmonConnError
from queryHandler import SensorConfig
from __version__ import __version__
from messages import ERR, MSG
from bridgeLogger import configureLogging, getBridgeLogger
from confParser import getSettings
from metadata import MetadataHandler
from opentsdb import OpenTsdbApi
from watcher import ConfigWatcher
from cherrypy import _cperror


def processFormJSON(entity):
    ''' Used to generate JSON when the content
    is of type application/x-www-form-urlencoded. Added for grafana 3 support'''

    body = entity.fp.read()
    if len(body) > 0:
        cherrypy.serving.request.json = json.loads(body.decode('utf-8'))
    else:
        cherrypy.serving.request.json = json.loads('{}')


def updateCherrypyConf(args):

    path = args.get('logPath')
    if not os.path.exists(path):
        os.makedirs(path)
    accesslog = os.path.join(path, 'cherrypy_access.log')
    errorlog = os.path.join(path, 'cherrypy_error.log')

    globalConfig = {'global': {'server.socket_port': args.get('port'),
                               'log.access_file': accesslog,
                               'log.error_file': errorlog,
                               # default error response
                               'error_page.default': format_default_error_page,
                               # unexpected errors
                               'request.error_response': handle_error},
                    }

    cherrypy.config.update(globalConfig)

    dirname, filename = os.path.split(os.path.abspath(__file__))
    customconf = os.path.join(dirname, 'mycherrypy.conf')
    cherrypy.config.update(customconf)


def updateCherrypySslConf(args):
    certPath = os.path.join(args.get('tlsKeyPath'), args.get('tlsCertFile'))
    keyPath = os.path.join(args.get('tlsKeyPath'), args.get('tlsKeyFile'))
    sslConfig = {'global': {'server.ssl_module': 'builtin',
                            'server.ssl_certificate': certPath,
                            'server.ssl_private_key': keyPath}}
    cherrypy.config.update(sslConfig)


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
                              traceback=cherrypy.serving.request.show_tracebacks
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

    # prepare the logger
    logger = configureLogging(args.get('logPath'), args.get('logFile', None),
                              args.get('logLevel'))

    # prepare cherrypy server configuration
    updateCherrypyConf(args)
    if args.get('protocol') == "https":
        updateCherrypySslConf(args)

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

    api = OpenTsdbApi(logger, mdHandler)
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

    try:
        files_to_watch = SensorConfig.get_config_paths()
        watcher = ConfigWatcher(files_to_watch, refresh_metadata, refresh_all=True)
        cherrypy.engine.subscribe('start', watcher.start_watch)
        cherrypy.engine.subscribe('stop', watcher.stop_watch)
        cherrypy.engine.start()
        cherrypy.engine.log('test')
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

    api = None

    logger.warning("server stopped")


if __name__ == '__main__':
    main(sys.argv[1:])
