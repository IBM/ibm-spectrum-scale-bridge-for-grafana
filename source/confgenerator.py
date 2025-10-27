'''
##############################################################################
# Copyright 2023 IBM Corp.
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

Created on Mai 30, 2024

@author: HWASSMAN
'''

import cherrypy
import json
import socket
import os
try:
    # Optional dependency
    import yaml
except ImportError as e:
    yaml = e
from messages import MSG, ERR


class PrometheusConfigGenerator(object):
    exposed = True

    def __init__(self, logger, mdHandler, config_attr, endpoints):
        if isinstance(yaml, ImportError):
            raise yaml
        self.logger = logger
        self.__md = mdHandler
        self.endpoints = endpoints
        self.attr = config_attr

    @property
    def md(self):
        return self.__md

    @property
    def qh(self):
        return self.__md.qh

    @property
    def TOPO(self):
        return self.__md.metaData

    @staticmethod
    def host_ip():
        hostname = socket.getfqdn()
        local_ip = socket.gethostbyname_ex(hostname)[2][0]
        return local_ip

    def generate_config(self):
        scrape_configs = []
        global_config = {"scrape_interval": "15s",
                         "evaluation_interval": "15s",
                         "query_log_file": "/var/log/prometheus/query.log"}
        alerting_config = {"alertmanagers": [{"static_configs": [{"targets": None}]}]}
        for endpoint, sensor in self.endpoints.items():
            period = self.md.getSensorPeriod(sensor)
            if period > 0:
                scrape_job = {}
                scrape_job["job_name"] = sensor
                scrape_job["scrape_interval"] = f"{period}s"
                scrape_job["honor_timestamps"] = True
                scrape_job["metrics_path"] = endpoint
                scrape_job["scheme"] = self.attr.get('protocol')
                if self.attr.get('protocol') == "https":
                    if not (
                        self.attr.get('tlsKeyPath')
                        and self.attr.get('tlsCertFile')
                        and self.attr.get('tlsKeyFile')
                            ):
                        self.logger.error(MSG['MissingSSLCert'])
                        return MSG['MissingSSLCert']
                    certPath = os.path.join(self.attr.get('tlsKeyPath'),
                                            self.attr.get('tlsCertFile'))
                    keyPath = os.path.join(self.attr.get('tlsKeyPath'),
                                           self.attr.get('tlsKeyFile'))
                    tls = {"cert_file": certPath,
                           "key_file": keyPath,
                           "insecure_skip_verify": True}
                    scrape_job["tls_config"] = tls
                if self.attr.get('enabled', False):
                    if not (
                        self.attr.get('username', False)
                        and self.attr.get('password', False)
                            ):
                        self.logger.error(MSG['MissingParm'])
                        return MSG['MissingParm']
                    basic_auth = {"username": self.attr.get('username')}
                    if os.path.isfile(self.attr.get('password')):
                        pw = {"password_file": self.attr.get('password')}
                    else:
                        pw = {"password": self.attr.get('password')}
                    basic_auth.update(pw)
                    scrape_job["basic_auth"] = basic_auth
                targets = {"targets": [f"{self.host_ip()}:{self.attr.get('prometheus')}"]}
                scrape_job["static_configs"] = [targets]
                scrape_configs.append(scrape_job)
        prometheus_job = {}
        prometheus_job["job_name"] = "prometheus"
        prometheus_job["static_configs"] = [{"targets": ["localhost:9090"]}]
        scrape_configs.insert(0, prometheus_job)
        resp = {"global": global_config,
                "alerting": alerting_config,
                "rule_files": None,
                "scrape_configs": scrape_configs}
        yaml_string = yaml.dump(resp)
        return yaml_string

    def GET(self, **params):
        '''Handle partial URLs such as /metrics_cpu
           TODO: add more explanation
        '''
        resp = []

        self.logger.trace(f"Request headers:{str(cherrypy.request.headers)}")
        conn = cherrypy.request.headers.get('Host').split(':')
        if len(conn) == 2 and int(conn[1]) != int(self.attr.get('prometheus')):
            self.logger.error(MSG['EndpointNotSupportedForPort'].
                              format(cherrypy.request.script_name, str(conn[1])))
            raise cherrypy.HTTPError(400, ERR[400])

        # generate prometheus.yml
        if '/prometheus.yml' == cherrypy.request.script_name:
            print(params)
            resp = self.generate_config()
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            return resp

        else:
            self.logger.error(MSG['EndpointNotSupported'].format(cherrypy.request.script_name))
            raise cherrypy.HTTPError(400, ERR[400])

        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Content-Type'] = 'application/json'
        resp = json.dumps(resp)
        return resp

    def OPTIONS(self):
        # print('options_post')
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, NEW, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Accept'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800
