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

Created on Apr 17, 2026

@author: HWASSMAN
'''

import cherrypy
import json
from processinfo import collect_process_info


class HealthCheck:
    """Liveness probe. With ?details=true also returns process/container resource usage."""
    exposed = True

    def GET(self, details='false'):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        if details.lower() == 'true':
            response = {'status': 'ok'}
            response.update(collect_process_info())
            return json.dumps(response).encode('utf-8')
        return b'{"status": "ok"}'
