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
       'MissingPortParam': 'Missing applications port configuration, quitting',
       'MissingSSLCert': 'Missing ssl configuration, quitting',
       'KeyPathError': 'KeyPath directory not found, quitting',
       'MissingFileFromPathError': 'Missing certificates in the specified keyPath directory, quitting',
       'CollectorErr': 'Failed to initialize connection to pmcollector: {}, quitting',
       'MetaError': 'Metadata could not be retrieved. Check log file for more details, quitting',
       'MetaSuccess': 'Successfully retrieved MetaData',
       'RequestMetaUpdate': 'MetaData update requested',
       'ElapsedTimeSinceLastUpdate': 'Elapsed time:{} since last MetaData update',
       'QueryError': 'Query request could not be proceed. Reason: {}',
       'SearchErr': 'Search for {} did cause exception: {}',
       'LookupErr': 'Lookup for metric {} did not return any results',
       'FilterByErr': 'No component entry found for the specified \'filterby\' attribute',
       'GroupByErr': 'In the current setup the group aggregation \'groupby\' is not possible.',
       'MetricErr': 'Metric {0} cannot be found. Please check if the corresponding sensor is configured',
       'InconsistentParams': 'Received parameters {} inconsistent with request parameters {}',
       'InvalidConfigParm': 'Configuration Parameter "{}" has not allowed value, quitting',
       'SensorDisabled': 'Sensor for metric {} is disabled',
       'SensorForceRawData': 'Sensor {} includes metrics type counter, which need to be collected as raw data',
       'EndpointNotSupported': 'Endpoint {} you try to access is not supported',
       'EndpointNotSupportedForPort': 'Endpoint {} is not supported for port {}',
       'NoData': 'Empty results received',  # Please check the pmcollector is properly configured and running.
       'NoSensorConfigData': 'No sensor configuration data parsed',
       'NoDataStartNextAttempt': 'No Metadata results received from the pmcollector. Start retry attempt {} in 60s (MAX_ATTEMPTS_COUNT:{})',
       'BucketsizeChange': 'Based on requested downsample value: {} the bucketsize will be set: {}',
       'BucketsizeToPeriod': 'Bucketsize will be set to sensors period: {}',
       'DownsampleAggregation': 'Perform downsample aggregation: {} for metric: {}',
       'ReceivedQuery': 'Received query request for query:{}, start:{}, end:{}',
       'AttrNotValid': 'Invalid attribute:{}',
       'AllowedAttrValues': 'For attribute {} applicable values:{}',
       'ReceivAttrValues': 'Received {}:{}',
       'StartMethod': 'Starting method: {} with args: {}.',
       'RunMethod': 'Executed method: {} with args: {}.',
       'TimerInfo': 'Processing {} took real time: {:.6f} seconds, cpu time: {:.6f} seconds.',
       'Query2port': 'For better bridge performance multithreaded port {} will be used',
       'CollectorConnInfo': 'Connection to the collector server established successfully',
       'BridgeVersionInfo': ' *** IBM Storage Scale bridge for Grafana - Version: {} ***',
       'FileNotFound': 'The file {} not found.',
       'FileChanged': 'The file {} has been changed.',
       'FileAddedToWatch': 'The file {} added to watching files.',
       'StartWatchingFiles': 'Start watching file changes in the path {}.',
       'StopWatchingFiles': 'Stop watching file changes in the path {}.',
       'StartMonitoringTopoChanges': 'Start monitoring if a Metadata refresh needed.',
       'StopMonitoringTopoChanges': 'Stop monitoring Metadata refresh requests.',
       'PathNoCfgFiles': 'The path does not contain any configuration files.',
       'NewKeyDetected': 'Detected not known single ts identifiers {}.',
       'NewKeyAlreadyReported': 'Single ts identifiers {} already reported as not known.',
       'UnexpecterError': 'Unexpected error: {}',
       'DataWrongFormat': 'Content could not be parsed: {}',
       'StartCustomThread': 'Started custom thread {}',
       'StopCustomThread': 'Stopped custom thread {}',
       'MetricInResults': 'Metric {} is in Collector.metrcs',
       'MetricNotInResults': 'Metric {} is not in Collector.metrcs',
       'ConnApplications': 'Registered applications: \n {}',
       'WrongFormat': 'The {} specified in wrong format.',
       'AuthValidationError': 'Basic auth data not valid'
       }
