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
from messages import MSG
import configparser
import getpass


def checkFileExists(path, filename):
    for root, dirs, files in os.walk(path):
        if filename in files:
            return True
    return False


def checkTLSsettings(args):
    if args.get('port') == 8443 and (not args.get('tlsKeyPath') or not args.get('tlsKeyFile') or not args.get('tlsCertFile')):
        return False, MSG['MissingParm']
    elif args.get('port') == 8443 and not os.path.exists(args.get('tlsKeyPath')):
        return False, MSG['KeyPathError']
    elif args.get('port') == 8443:
        if (not checkFileExists(args.get('tlsKeyPath'), args.get('tlsCertFile'))) or (not checkFileExists(args.get('tlsKeyPath'), args.get('tlsKeyFile'))):
            return False, MSG['CertError']
    return True, ''

def checkAPIsettings(args):
    if not args.get('apiKeyName') or not args.get('apiKeyValue'):
        return False, MSG['MissingParm']
    return True, ''


def getSettings(argv):
    settings = {}
    msg = ''
    defaults = ConfigManager().defaults
    args, msg = parse_cmd_args(argv)
    if args and defaults:
        settings = merge_defaults_and_args(defaults, args)
    elif args:
        settings = args
    else:
        return None, msg
    # check API key settings
    valid, msg = checkAPIsettings(settings)
    if not valid:
        return None, msg
    # check TLS settings
    valid, msg = checkTLSsettings(settings)
    if not valid:
        return None, msg
    return settings, ''


def merge_defaults_and_args(defaults, args):
    '''merge default config parameters with input parameters from the command line'''
    brConfig = {}
    brConfig = dict(defaults)
    args = vars(args)
    brConfig.update({k: v for k, v in args.items() if v is not None and not (v == str(None))})
    return brConfig


class Singleton(type):
    _inst = {}

    def __call__(clazz, *args, **kwargs):
        if clazz not in clazz._inst:
            clazz._inst[clazz] = super(Singleton, clazz).__call__(*args, **kwargs)
        return clazz._inst[clazz]


class ConfigManager(object, metaclass=Singleton):
    ''' A singleton class managing the application configuration defaults '''

    def __init__(self):
        self.__sectOptions = {}
        self.__defaults = {}
        self.configFiles = ['config.ini']

    @property
    def options(self):
        if not self.__sectOptions:
            self.__sectOptions = self.reload()
        return self.__sectOptions

    @property
    def defaults(self):
        if not self.__defaults:
            self.__defaults = self.parse_defaults()
        return self.__defaults

    def reload(self):
        options = {}
        self.__sectOptions = {}
        if self.configFiles:
            for config in self.configFiles:
                options.update(self.readConfigFile(config))
        return options

    def readConfigFile(self, fileName):
        '''parse config file and store values in a dict {section:{ key: value}}'''
        options = {}
        dirname, filename = os.path.split(os.path.abspath(__file__))
        conf_file = os.path.join(dirname, fileName)
        if os.path.isfile(conf_file):
            try:
                config = configparser.ConfigParser()
                config.optionxform = str
                config.read(conf_file)
                for sect in config.sections():
                    options[sect] = {}
                    for name, value in config.items(sect):
                        if value.isdigit():
                            value = int(value)
                        options[sect][name] = value
            except Exception as e:
                print(f"cannot read config file {fileName} Exception {e}")
        else:
            print(f"cannot find config file {fileName} in {dirname}")
        return options

    def parse_defaults(self):
        '''parse all sections parameters to a simple key:value dict'''
        defaults = {}
        for sect_name, sect_values in self.options.items():
            for name, value in sect_values.items():
                defaults[name] = value
        return defaults


class Password(argparse.Action):
    defaults = ConfigManager().defaults

    def __call__(self, parser, namespace, values, option_string):
        if values is None and self.defaults.get('apiKeyValue', None) == None:
            print('no valid apiKeyValue found in the config.ini')
            values = getpass.getpass()

        setattr(namespace, self.dest, values)


def parse_cmd_args(argv):
    '''parse input parameters'''

    parser = argparse.ArgumentParser('python zimonGrafanaIntf.py')
    parser.add_argument('-s', '--server', action="store", default=None,
                        help='Host name or ip address of the ZIMon collector (Default from config.ini: 127.0.0.1)')
    parser.add_argument('-P', '--serverPort', action="store", type=int, choices=[9980, 9981], default=None,
                        help='ZIMon collector port number (Default from config.ini: 9980)')
    parser.add_argument('-l', '--logPath', action="store", default=None, help='location path of the log file (Default from config.ini: \'/var/log/ibm_bridge_for_grafana\')')
    parser.add_argument('-f', '--logFile', action="store", default=None, help='Name of the log file (Default from config.ini: zserver.log')
    parser.add_argument('-c', '--logLevel', action="store", type=int, default=None,
                        help='log level. Available levels: 10 (DEBUG), 15 (MOREINFO), 20 (INFO), 30 (WARN), 40 (ERROR) (Default from config.ini: 15)')
    parser.add_argument('-p', '--port', action="store", type=int, choices=[4242, 8443], default=None, help='port number listening on for HTTP(S) connections (Default from config.ini: 4242)')
    parser.add_argument('-t', '--tlsKeyPath', action="store", default=None, help='Directory path of tls privkey.pem and cert.pem file location (Required only for HTTPS port 8443)')
    parser.add_argument('-k', '--tlsKeyFile', action="store", default=None, help='Name of TLS key file, f.e.: privkey.pem (Required only for HTTPS port 8443)')
    parser.add_argument('-m', '--tlsCertFile', action="store", default=None, help='Name of TLS certificate file, f.e.: cert.pem (Required only for HTTPS port 8443)')
    parser.add_argument('-n', '--apiKeyName',  action="store", default=None, help='Name of api key file (Default from config.ini: \'scale_grafana\')')
    parser.add_argument('-v', '--apiKeyValue',  action=Password, nargs='?', dest='apiKeyValue', default=None, help='Enter your apiKey value:')

    args = parser.parse_args(argv)
    return args, ''
