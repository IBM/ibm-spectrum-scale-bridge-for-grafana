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

Created on Jan 28, 2021

@author: HWASSMAN
'''

# catch import failure on AIX since we will not be shipping our third-party libraries on AIX
try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass



DEFAULT_HEADERS = {
            "Accept": "application/json",
            "Content-type": "application/json"
        }


def getAuthHandler(keyName, keyValue):
    if not isinstance(keyName, bytes):
        keyName = bytes(keyName, 'utf-8')
    if not isinstance(keyValue, bytes):
        keyValue = bytes(keyValue, 'utf-8')
    return requests.auth.HTTPBasicAuth(keyName,keyValue)


def createRequestDataObj(logger, method, endpoint, host, port, auth, headers=None, files=None, json=None, params=None, data=None, cookies=None, hooks=None):
    '''This method is used to prepare an instance of the class: <requests.Request>, which will be sent to the server. '''

    if method.upper() not in ['GET', 'DELETE']:
        logger.error('createRequestDataObj __ request METHOD {} not allowed'.format(method))
        return None
    if not host or not port or not endpoint or not auth:
        logger.error('createRequestDataObj __ missing mandatory parameters')
        return None
    url = f'https://{host}:{port}/sysmon/v1/{endpoint}'
    # Create the Request.
    req = requests.Request(method=method.upper(),
        url=url,
        headers=headers or DEFAULT_HEADERS,
        files=files,
        data=data or {},
        json=json,
        params=params or {},
        auth=auth,
        cookies=cookies,
        hooks=hooks,
        )
    logger.debug('createRequestDataObj __ created request')
    return req


class perfHTTPrequestHelper(object):
    """
    REST communication handler / dispatcher for the QueryHandler
    1. does send a prepared Request object to a server
    2. waits until  the server response, finally forwards a result to the QueryHandler
    """

    def __init__(self, logger, reqdata=None, session=None):
        self.session = session or requests.Session() 
        self.requestData = reqdata
        self.logger = logger

    def doRequest(self):
        if self.requestData and isinstance(self.requestData, requests.Request):
            _prepRequest = self.session.prepare_request(self.requestData)
            try:
                res = self.session.send(_prepRequest)
                return res
            except requests.exceptions.ConnectionError:
                res = requests.Response()
                res.status_code = 503
                res.reason = "Connection refused from server"
                res.content = None
                return res
            except requests.exceptions.RequestException as e:
                self.logger.debug('doRequest __ RequestException. Request data: {}, Response data: {}'.format(e.request, e.response))
                res = requests.Response()
                res.status_code = 404
                res.reason = "The request could not be processed from server"
                res.content = None
                return res
        else:
            raise TypeError('doRequest __ Error: request data wrong format')
