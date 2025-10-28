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
import base64
import binascii
import os
from messages import MSG
from metaclasses import Singleton
import configparser
import getpass


def checkFileExists(path, filename):
    for root, dirs, files in os.walk(path):
        if filename in files:
            return True
    return False


def checkTLSsettings(args):
    if args.get('protocol') == "https" and (not args.get('tlsKeyPath') or not
                                            args.get('tlsKeyFile') or not
                                            args.get('tlsCertFile')
                                            ):
        return False, MSG['MissingParm']
    elif args.get('protocol') == "https" and not os.path.exists(args.get('tlsKeyPath')):
        return False, MSG['KeyPathError']
    elif args.get('protocol') == "https":
        if (not checkFileExists(
            args.get('tlsKeyPath'), args.get('tlsCertFile'))
            ) or (not checkFileExists(
                args.get('tlsKeyPath'), args.get('tlsKeyFile'))):
            return False, MSG['MissingFileFromPathError']
    return True, ''


def checkBasicAuthsettings(args):
    if args.get('enabled') and (not args.get('username') or not
                                args.get('password')
                                ):
        return False, MSG['MissingParm']
    elif args.get('enabled') and ("/" in str(args.get('password')) and not
                                  os.path.isfile(args.get('password'))
                                  ):
        return False, MSG['PathNotFound'].format("basic auth settings")
    elif args.get('enabled') and "/" not in str(args.get('password')):
        try:
            base64.b64decode(args.get('password'), validate=True)
        except binascii.Error:
            return False, MSG['WrongFormat'].format("basic auth password")
    return True, ''


def checkApplicationPort(args):
    if not args.get('port', None) and not args.get('prometheus', None):
        return False, MSG['MissingPortParam']
    return True, ''


def checkAPIsettings(args):
    if not args.get('apiKeyName') or not args.get('apiKeyValue'):
        return False, MSG['MissingParm']
    elif "/" in str(args.get('apiKeyValue')) and not os.path.isfile(args.get('apiKeyValue')):
        return False, MSG['PathNotFound'].format("api key settings")
    return True, ''


def checkCAsettings(args):
    if args.get('caCertPath') and args['caCertPath'] != False and not (os.path.exists(args['caCertPath'])):
        return False, MSG['FileNotFound'].format("mandatory for CA validation")
    return True, ''


def checkForInvalidsettings(args):
    if all(args.values()):
        return True, ''
    else:
        for key, value in args.items():
            if value is None or value == '':
                return False, MSG['InvalidConfigParm'].format(key)
        return True, ''


def getSettings(argv):
    settings = {}
    args, msg = parse_cmd_args(argv)
    customFile = vars(args).get('configFile', None)
    defaults = ConfigManager(customFile).defaults
    if args and defaults:
        settings = merge_defaults_and_args(defaults, args)
    elif args:
        settings = vars(args)
    else:
        return None, msg
    valid, msg = checkForInvalidsettings(settings)
    if not valid:
        return None, msg
    # check application port
    valid, msg = checkApplicationPort(settings)
    if not valid:
        return None, msg
    # check API key settings
    valid, msg = checkAPIsettings(settings)
    if not valid:
        return None, msg
    # check basic auth settings
    valid, msg = checkBasicAuthsettings(settings)
    if not valid:
        return None, msg
    # check TLS settings
    valid, msg = checkTLSsettings(settings)
    if not valid:
        return None, msg
    # check ca certificate settings
    valid, msg = checkCAsettings(settings)
    if not valid:
        return None, msg
    return settings, ''


def merge_defaults_and_args(defaults, args):
    '''merge default config parameters with input parameters from the command line'''
    brConfig = dict(defaults)
    args = vars(args)
    brConfig.update({k: v for k, v in args.items() if v is not None and not (v == str(None))})
    for k, v in brConfig.items():
        if v == "no" or v == "False":
            brConfig[k] = False
        elif v == "yes" or v == "True":
            brConfig[k] = True
        elif isinstance(v, str) and v.isdigit():
            brConfig[k] = int(v)
    return brConfig


class ConfigManager(object, metaclass=Singleton):
    ''' A singleton class managing the application configuration defaults '''

    def __init__(self, custom_config_file=None):
        self.__defaults = {}
        self.customFile = custom_config_file
        self.templateFile = self.get_template_path()

    @property
    def defaults(self):
        if not self.__defaults:
            self.__defaults = self.parse_defaults()
        return self.__defaults

    def readConfigFile(self, fileName):
        '''parse config file and store values in a dict {section:{ key: value}}'''
        options = {}
        if os.path.isfile(fileName):
            try:
                config = configparser.ConfigParser()
                config.optionxform = str
                config.read(fileName)
                for sect in config.sections():
                    options[sect] = {}
                    for name, value in config.items(sect):
                        if value.isdigit():
                            value = int(value)
                        options[sect][name] = value
            except Exception as e:
                print(f"Error: Cannot read config file {fileName} Exception {e}")
        else:
            print(f"Error: Cannot find config file {fileName}")
        return options

    def get_template_path(self):
        '''parse config.ini to a simple key:value dict'''
        dirname, _ = os.path.split(os.path.abspath(__file__))
        return os.path.join(dirname, 'config.ini')

    def parse_file(self, file):
        '''parse file to a simple key:value dict'''
        settings = {}
        section_names = set()
        sections = self.readConfigFile(file)
        if sections:
            section_names = set(sections.keys())
            for _, sect_values in sections.items():
                for name, value in sect_values.items():
                    settings[name] = value
        return section_names, settings

    def parse_defaults(self):
        """Retuns a dictionary of parameter names and values parsed from config file

        If no custom config file provided the values will be parsed from template
        file (.config.ini)
        """

        default_sections, defaults = self.parse_file(self.templateFile)
        if not self.customFile or self.customFile == self.templateFile:
            return defaults

        custom_sections, customs = self.parse_file(self.customFile)
        sect = default_sections.intersection(custom_sections)
        if not sect:
            return defaults

        defaults.update(customs)
        return defaults


class Password(argparse.Action):
    # defaults = ConfigManager().defaults

    def __call__(self, parser, namespace, values, option_string):
        if values is None:
            if self.dest == 'password':
                print('Enter your basic auth password')
            else:
                print('Enter your apiKey value')
            values = getpass.getpass()

        setattr(namespace, self.dest, values)


def parse_cmd_args(argv):
    '''parse input parameters'''

    parser = argparse.ArgumentParser('python zimonGrafanaIntf.py')
    parser.add_argument('-s', '--server', action="store", default=None,
                        help='Host name or ip address of the ZIMon collector (Default from config.ini: 127.0.0.1)')
    parser.add_argument('-P', '--serverPort', action="store", type=int, choices=[9980, 9981], default=None,
                        help='ZIMon collector port number (Default from config.ini: 9980)')
    parser.add_argument('-l', '--logPath', action="store", default=None,
                        help='location path of the log file (Default from config.ini: \'/var/log/ibm_bridge_for_grafana\')')
    parser.add_argument('-f', '--logFile', action="store", default=None,
                        help='Name of the log file (Default from config.ini: zserver.log). If no log file name specified \
    all traces will be printed out directly on the command line')
    parser.add_argument('-F', '--configFile', action="store", default=None,
                        help='Absolute path to the custom config file that should be used instead of the default config.ini file (optional)')
    parser.add_argument('-c', '--logLevel', action="store", type=int, default=None,
                        help='log level. Available levels: 10 (DEBUG), 15 (MOREINFO), 20 (INFO), 30 (WARN), 40 (ERROR) (Default from config.ini: 15)')
    parser.add_argument('-e', '--prometheus', action="store", default=None,
                        help='port number listening on Prometheus HTTPS connections (Default from config.ini: 9250, if enabled)')
    parser.add_argument('-p', '--port', action="store", default=None,
                        help='port number listening on OpenTSDB API HTTP(S) connections (Default from config.ini: 4242, if enabled)')
    parser.add_argument('-r', '--protocol', action="store", choices=["http", "https"], default=None,
                        help='Connection protocol HTTP/HTTPS (Default from config.ini: "http")')
    parser.add_argument('-b', '--enabled', action="store", choices=["True", "False"], default=None,
                        help='Controls if HTTP/S basic authentication should be enabled or not (Default from config.ini: "True")')
    parser.add_argument('-u', '--username', action="store", default=None,
                        help='HTTP/S basic authentication user name(Default from config.ini: \'scale_admin\')')
    parser.add_argument('-a', '--password', action=Password, nargs='?', dest='password', default=None,
                        help='Enter your HTTP/S basic authentication password:')
    parser.add_argument('-t', '--tlsKeyPath', action="store", default=None,
                        help='Directory path of tls privkey.pem and cert.pem file location (Required only for HTTPS ports 8443/9250)')
    parser.add_argument('-k', '--tlsKeyFile', action="store", default=None,
                        help='Name of TLS key file, f.e.: privkey.pem (Required only for HTTPS ports 8443/9250)')
    parser.add_argument('-m', '--tlsCertFile', action="store", default=None,
                        help='Name of TLS certificate file, f.e.: cert.pem (Required only for HTTPS ports 8443/9250)')
    parser.add_argument('-n', '--apiKeyName', action="store", default=None,
                        help='Name of api key file (Default from config.ini: \'scale_grafana\')')
    parser.add_argument('-v', '--apiKeyValue', action=Password, nargs='?', dest='apiKeyValue', default=None,
                        help='Enter your apiKey value:')
    parser.add_argument('-d', '--includeDiskData', action="store", choices=["yes", "no"], default=None,
                        help='Use or not the historical data from disk (Default from config.ini: "no")')
    parser.add_argument('-w', '--rawCounters', action="store", choices=["True", "False"], default=None,
                        help='Controls if original sensor counters should be exposed by PrometheusExporter (Default from config.ini: "True")')

    args = parser.parse_args(argv)
    return args, ''
