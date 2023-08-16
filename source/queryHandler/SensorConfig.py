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


import os
import re
try:
    import SysmonLogger
except Exception:
    pass

mmsdrfsFile = '/var/mmfs/gen/mmsdrfs'
zimonFile = '/opt/IBM/zimon'
collectorsFile = '/opt/IBM/zimon/ZIMonCollector.cfg'


def readSensorsConfigFromMMSDRFS(logger=None):
    '''
    :return: list of dictionaries with sensorsName as key and the values of the sensors in the mmsdrfs
    '''
    if not logger:
        logger = SysmonLogger.getLogger(__name__)

    if not os.path.isfile(mmsdrfsFile):
        logger.debug("MMSDRFS file not found (%s), continue with trying to read pmsensors configuration from ZIMonSensors.cfg ", mmsdrfsFile)
        return readSensorsConfig(logger)

    data = ""
    logger.debug("readSensorsConfigFromMMSDRFS attempt to read %s", mmsdrfsFile)
    try:
        with open(mmsdrfsFile) as f:
            data = data.join([line.split(":")[4] for line in f if "PERFMONCFG" in line])
    except (Exception, IOError) as error:
        logger.details("failed trying read %s with reason: %s", mmsdrfsFile, error)
        return []

    # parse config file in a list of dictionaries format
    return parseSensorsConfig(data, logger)


def readSensorsConfig(logger=None, customFile=None):
    '''
    :return: list of dictionaries with sensorsName as key and the values of the sensors in the ZimonSensors.cfg
    '''
    if not logger:
        logger = SysmonLogger.getLogger(__name__)

    global zimonFile
    if customFile:
        zimonFile = rf"{customFile}"

    sensorConfigFiles = []
    parsedSensors = []

    if os.path.isfile(zimonFile):
        sensorConfigFiles.append(zimonFile)
    elif os.path.isdir(zimonFile):
        for root, dirs, files in os.walk(zimonFile):
            for file in files:
                if file.endswith(".cfg"):
                    sensorConfigFiles.append(os.path.join(root, file))
    else:
        logger.details("ZiMon sensor configuration file not found (%s) ", zimonFile)
        print("ZiMon sensor configuration file not found")
        raise OSError(2, 'No such file or directory', zimonFile)

    data = ""
    logger.debug("readSensorsConfig attempt to read %s", zimonFile)
    for file in sensorConfigFiles:
        try:
            with open(file) as myfile:
                data = myfile.read().replace('\n', '')
        except (Exception, IOError) as error:
            logger.details("failed trying read %s with reason: %s", zimonFile, error)
            continue
        # parse config file in a list of dictionaries format
        parsedSensors.extend(parseSensorsConfig(data, logger))
    return parsedSensors


def parseSensorsConfig(sensorsConfig, logger):
    """ Returns a list of dicts, describing definitions of sensors """
    logger.debug("invoke parseSensorsConfig")
    try:
        sensors = []
        sensorsStr = ""
        if sensorsConfig.find("smbstat") != -1:
            sensorsStr = sensorsConfig[sensorsConfig.find("sensors"):sensorsConfig.find("smbstat")]
        else:
            end = None
            sensorsStr = sensorsConfig[sensorsConfig.find("sensors"):end]
        sensorsList = re.findall('(?P<sensor>{.*?})(?:,|$)', sensorsStr)
        for sensorString in sensorsList:
            sensorAttr = re.findall(r'(?P<name>\w+) = (?P<value>\"\S*\"|\d+)', sensorString)
            d = {}
            for attr in sensorAttr:
                d[attr[0]] = attr[1]
            sensors.append(d)
        return sensors
    except (Exception, IOError) as error:
        logger.details("failed parsing sensors config content with reason: %s", error)
        return []


def getCollectorPorts(logger=None):
    '''
    :return: list of configured query ports found in the ZIMonCollector.cfg
    '''
    if not logger:
        logger = SysmonLogger.getLogger(__name__)

    if not os.path.isfile(collectorsFile):
        raise IOError("ZiMon collector configuration file not found on the localhost")

    queryport = None
    query2port = None

    logger.debug("getCollectorsPorts attempt to read %s", collectorsFile)
    try:
        with open(collectorsFile) as myFile:
            for line in myFile:
                line = line.rstrip()  # remove '\n' at end of line
                if 'queryport' in line:
                    queryport = re.search(r'"(?P<queryport>\d+?)"', line).group('queryport')
                elif 'query2port = ""' in line:
                    query2port = '9094'
                elif 'query2port' in line:
                    query2port = re.search(r'"(?P<query2port>\d+?)"', line).group('query2port')

                if queryport and query2port:
                    return [queryport, query2port]

    except (Exception, IOError) as error:
        logger.error("failed trying read %s with reason: %s", collectorsFile, error)
        return []
    logger.debug("found collector ports: %s", str([queryport, query2port]))
    return [queryport, query2port]
