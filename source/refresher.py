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

Created on Dec 9, 2024

@author: HWASSMAN
'''

import cherrypy
import time
from bridgeLogger import getBridgeLogger
from utils import synchronized
from metaclasses import Singleton
from metadata import MetadataHandler
from messages import MSG
from threading import Thread, Lock

LOCK = Lock()


class TopoRefreshManager(object, metaclass=Singleton):
    running = False
    thread = None
    refresh_delay_secs = 30

    def __init__(self, call_func_on_change=None, *args, **kwargs):
        self._cached_stamp = {}
        self.logger = getBridgeLogger()
        self.update_required = False
        self.new_keys = set()
        self.call_func_on_change = call_func_on_change
        self.args = args
        self.kwargs = kwargs

    def start_monitor(self):
        """ Function to start monitor in a thread"""
        self.running = True
        if not self.thread:
            self.thread = Thread(name='TopoRefreshManager', target=self.monitor)
            self.thread.start()
            cherrypy.engine.log('Started custom thread %r.' % self.thread.name)
            self.logger.debug(MSG['StartMonitoringTopoChanges'])

    @synchronized(LOCK)
    def update_local_cache(self, key):
        """ Function to cache unknown key locally"""
        cache_size = len(self.new_keys)
        self.new_keys = self.new_keys.union(key)
        updated_size = len(self.new_keys)
        if updated_size > cache_size:
            self.logger.trace(MSG['NewKeyDetected'].format('|'.join(key)))
            self.update_required = True
        else:
            self.logger.trace(MSG['NewKeyAlreadyReported'].format('|'.join(key)))

    @synchronized(LOCK)
    def clear_local_cache(self):
        """ Function to clear local cache after topo refresh"""
        self.new_keys.clear()
        self.update_required = False

    def monitor(self):
        """ Function to keep watching in a loop """
        while self.running:
            try:
                time.sleep(self.refresh_delay_secs)
                if self.update_required:
                    md = MetadataHandler()
                    elapsed_time = time.time() - md.getUpdateTime
                    self.logger.trace(MSG['ElapsedTimeSinceLastUpdate'].format(elapsed_time))
                    if elapsed_time > 300 or self.new_keys > 100:
                        self.logger.info(MSG['RequestMetaUpdate'])
                        if self.call_func_on_change is not None:
                            self.call_func_on_change(*self.args, **self.kwargs)
                            self.clear_local_cache()
            except KeyboardInterrupt:
                self.logger.details(MSG['StopMonitoringTopoChanges'])
                break
            except Exception as e:
                self.logger.warning(
                    MSG['UnexpecterError'].format(type(e).__name__))
                pass

    def stop_monitor(self):
        """ Function to break monitoring """
        try:
            self.running = False
            if self.thread:
                self.thread.join()
                cherrypy.engine.log('Stopped custom thread %r.' % self.thread.name)
                self.thread = None
        except KeyboardInterrupt:
            print(f"Recived KeyboardInterrupt during stopping the thread {self.thread.name}")
