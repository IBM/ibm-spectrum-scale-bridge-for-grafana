'''
##############################################################################
# Copyright 2026 IBM Corp.
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

Created on Feb 15, 2026

@author: HWASSMAN
'''

import cherrypy
import json
from collections import defaultdict
from messages import MSG, ERR


class RestHelpGenerator(object):
    exposed = True

    def __init__(self, logger):
        self.logger = logger

    def generate_endpoints_list(self):
        ep = defaultdict(list)
        outp = ''
        for value in cherrypy.tree.apps.values():
            name = value.root.__class__.__name__
            endp = value.script_name
            ep[name].append(endp)
        for key, values in ep.items():
            outp += key + '\n\t' + '\n\t'.join(values) + '\n\n'
        return outp

    def GET(self, **params):
        '''Handle partial URLs such as /metrics_cpu
           TODO: add more explanation
        '''
        resp = []

        self.logger.trace(f"Request headers:{str(cherrypy.request.headers)}")

        # generate prometheus.yml
        if '/endpoints' == cherrypy.request.script_name:
            print(params)
            resp = self.generate_endpoints_list()
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
