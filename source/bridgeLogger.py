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

Created on Mar 15, 2021

@author: HWASSMAN
'''

import logging
import logging.handlers
import os

logging.TRACE = 5
logging.addLevelName(logging.TRACE, 'TRACE')

logging.MOREINFO = 15
logging.addLevelName(logging.MOREINFO, 'MOREINFO')


class MyLogger(logging.getLoggerClass()):

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.TRACE):
            self._log(logging.TRACE, msg, args, **kwargs)

    def details(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.MOREINFO):
            self._log(logging.MOREINFO, msg, args, **kwargs)


def configureLogging(logPath, logfile, loglevel=logging.INFO):

    try:
        loglevel = logging._checkLevel(loglevel)
    except (ValueError, TypeError):
        loglevel = logging.INFO

    logToFile = True if logfile else False

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(threadName)-55s - %(levelname)-8s - %(message)s')
    formatter1 = logging.Formatter('%(asctime)s - %(threadName)-40s - %(levelname)-8s - %(message)s', datefmt='%Y-%m-%d %H:%M')

    # prepare the logger
    logging.setLoggerClass(MyLogger)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.TRACE)

    # prepare stream handler
    strmhandler = logging.StreamHandler()
    strmhandler.setLevel(loglevel)
    strmhandler.setFormatter(formatter1)

    if logToFile:
        # create the log file path if needed
        if not os.path.exists(logPath):
            os.makedirs(logPath)
        logfile = os.path.join(logPath, logfile)

        rfhandler = logging.handlers.RotatingFileHandler(logfile, 'a', 1000000, 5)  # 5 x 1M files
        rfhandler.setLevel(loglevel)
        rfhandler.setFormatter(formatter)

        strmhandler.setLevel(logging.INFO)  # if we log to a file limit the console traces to INFO level

        logger.addHandler(rfhandler)

    logger.addHandler(strmhandler)

    logger.propagate = False  # prevent propagation to default (console) logger
    return logger


def getBridgeLogger():
    return logging.getLogger(__name__)
