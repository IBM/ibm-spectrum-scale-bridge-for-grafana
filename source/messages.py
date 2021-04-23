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


ERR = {400: 'Bad Request',
       404: 'Not Found',
       500: 'Internal Server Error. Please check logs for more details.'}

MSG = {'IntError': 'Server internal error occurred. Reason: {}',
       'sysStart': 'Initial cherryPy server engine start have been invoked. Python version: {}, cherryPy version: {}.',
       'MissingParm': 'Missing mandatory parameters, quitting',
       'KeyPathError': 'KeyPath directory not found, quitting',
       'CertError': 'Missing certificates in tht specified keyPath directory, quitting',
       'CollectorErr': 'Failed to initialize connection to pmcollector: {}, quitting',
       'MetaError': 'Metadata could not be retrieved. Check log file for more details, quitting',
       'MetaSuccess': 'Successfully retrieved MetaData',
       'QueryError': 'Query request could not be proceed. Reason: {}',
       'SearchErr': 'Search for {} did cause exception: {}',
       'LookupErr': 'Lookup for metric {} did not return any results',
       'FilterByErr': 'No component entry found for the specified \'filterby\' attribute',
       'GroupByErr': 'In the current setup the group aggregation \'groupby\' is not possible.',
       'MetricErr': 'Metric {0} cannot be found. Please check if the corresponding sensor is configured',
       'InconsistentParams': 'Received parameters {} inconsistent with request parameters {}',
       'SensorDisabled': 'Sensor for metric {} is disabled',
       'NoData': 'Empty results received',  # Please check the pmcollector is properly configured and running.
       'BucketsizeChange': 'Based on requested downsample value: {} the bucketsize will be set: {}',
       'BucketsizeToPeriod': 'Bucketsize will be set to sensors period: {}',
       'ReceivedQuery': 'Received query request for query:{}, start:{}, end:{}',
       'RunQuery': 'Execute zimon query: {}',
       'AttrNotValid': 'Invalid attribute:{}',
       'AllowedAttrValues': 'For attribute {} applicable values:{}',
       'ReceivAttrValues': 'Received {}:{}',
       'TimerInfo': 'Processing {} took {} seconds',
       'Query2port': 'For better bridge performance multithreaded port {} will be used',
       'CollectorConnInfo': 'Connection to the collector server established successfully',
       'BridgeVersionInfo': ' *** IBM Spectrum Scale bridge for Grafana - Version: {} ***',
       'FileNotFound': 'The file {} not found.'
       }
