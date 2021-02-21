'''
##############################################################################
# Copyright 2021 IBM Corp.
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

Created on Feb 15, 2021

@author: HWASSMAN
'''

import argparse
import os
import logging.handlers
from messages import MSG
import configparser


def findKeyFile(path):
    for name in ["privkey.pem", "tls.key"]:
        for root, dirs, files in os.walk(path):
            if name in files:
                return name
    return None


def findCertFile(path):
    for name in ["cert.pem", "tls.crt"]:
        for root, dirs, files in os.walk(path):
            if name in files:
                return name
    return None


def parse_defaults_from_config_file(fileName='config.ini'):
    defaults = {}
    dirname, filename = os.path.split(os.path.abspath(__file__))
    conf_file = os.path.join(dirname, fileName)
    if os.path.isfile(conf_file):
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(conf_file)
        for sect in config.sections():
            for name, value in config.items(sect):
                defaults[name] = value
    return defaults


def parse_cmd_args(argv):
    '''parse input parameters'''

    parser = argparse.ArgumentParser('python zimonGrafanaIntf.py')
    parser.add_argument('-s', '--server', action="store", default='localhost',
                        help='Host name or ip address of the ZIMon collector (Default: 127.0.0.1) \
                        NOTE: Per default ZIMon does not accept queries from remote machines. \
                        To run the bridge from outside of the ZIMon collector, you need to modify ZIMon queryinterface settings (\'ZIMonCollector.cfg\')')
    parser.add_argument('-P', '--serverPort', action="store", type=int, default=9084, help='ZIMon collector port number (Default: 9084)')
    parser.add_argument('-l', '--logFile', action="store", default="./logs/zserver.log", help='location of the log file (Default: ./logs/zserver.log')
    parser.add_argument('-c', '--logLevel', action="store", type=int, default=logging.INFO, help='log level 10 (DEBUG), 20 (INFO), 30 (WARN), 40 (ERROR) (Default: 20)')
    parser.add_argument('-p', '--port', action="store", type=int, choices=[4242, 8443], default=4242, help='port number listening on for HTTP(S) connections (Default: 4242)')
    parser.add_argument('-t', '--tlsKeyPath', action="store", help='Directory path of tls privkey.pem and cert.pem file location (Required only for HTTPS port 8443)')

    args = parser.parse_args(argv)

    if args.port == 8443 and not args.tlsKeyPath:
        return None, MSG['MissingParm']
    elif args.port == 8443 and not os.path.exists(args.tlsKeyPath):
        return None, MSG['KeyPathError']
    elif args.port == 8443:
        certFile = findCertFile(args.tlsKeyPath)
        keyFile = findKeyFile(args.tlsKeyPath)
        if (not certFile) or (not keyFile):
            return None, MSG['CertError']

    return args, ''
