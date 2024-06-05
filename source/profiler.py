'''
##############################################################################
# Copyright 2024 IBM Corp.
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

Created on May 15, 2024

@author: HWASSMAN
'''

import cherrypy
import io
import os
from cProfile import Profile
try:
    # Optional dependency
    from pstats import SortKey
except ImportError as e:
    SortKey = e
from pstats import Stats
from metaclasses import Singleton


class Profiler(metaclass=Singleton):
    exposed = True

    def __init__(self, path=None):
        if isinstance(SortKey, ImportError):
            raise SortKey
        if not path:
            path = os.path.join(os.path.dirname(__file__), 'profile')
        self.path = path
        if not os.path.exists(path):
            os.makedirs(path)

    def run(self, func, *args, **kwargs):
        """Dump profile data into self.path."""
        with Profile() as profile:
            filename = f"profiling_{func.__name__}.prof"
            result = func(*args, **kwargs)
            (
                Stats(profile)
                .strip_dirs()
                .sort_stats(SortKey.CALLS)
                .dump_stats(os.path.join(self.path, filename))
            )
        return result

    def statfiles(self):
        """ Returns a list of available profiling files"""
        return [f for f in os.listdir(self.path)
                if f.startswith('profiling_') and f.endswith('.prof')]

    def stats(self, filename, sortby='cumulative'):
        """ Returns output of print_stats() for the given profiling file"""
        sio = io.StringIO()
        s = Stats(os.path.join(self.path, filename), stream=sio)
        s.strip_dirs()
        s.sort_stats(sortby)
        s.print_stats()
        response = sio.getvalue().splitlines()
        sio.close()
        return response

    def GET(self, **params):
        """ Forward GET REST HTTP/s API incoming requests to Profiler
            available endpoints:
                            /profiling
        """
        resp = []
        # /profiling
        if '/profiling' == cherrypy.request.script_name:
            del cherrypy.response.headers['Content-Type']
            outp = []
            runs = self.statfiles()
            for name in runs:
                outp.extend(self.stats(filename=name))
            resp = '\n'.join(outp) + '\n'
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return resp
