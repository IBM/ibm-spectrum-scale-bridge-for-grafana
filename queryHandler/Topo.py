'''
/* IBM_PROLOG_BEGIN_TAG                                                   */
/* This is an automatically generated prolog.                             */
/*                                                                        */
/* queryHandler/Topo.py                                                   */
/*                                                                        */
/* Licensed Materials - Property of IBM                                   */
/*                                                                        */
/* Restricted Materials of IBM                                            */
/*                                                                        */
/* (C) COPYRIGHT International Business Machines Corp. 2017               */
/* All Rights Reserved                                                    */
/*                                                                        */
/* US Government Users Restricted Rights - Use, duplication or            */
/* disclosure restricted by GSA ADP Schedule Contract with IBM Corp.      */
/*                                                                        */
/* IBM_PROLOG_END_TAG                                                     */
Created on Apr 4, 2017

@author: hwassman
'''


import json
import logging
import sys
import six



class Topo(object):
    '''
     ZIMon Metadata topology parser class
    '''

    def __init__(self,queryHandler):
        
        self.logger = queryHandler.logger
        self.qh = queryHandler
        self.topo = self._processTopo()



    def cleanJSONStr(self, inString):
        '''Remove control, single backslash, quote characters
        from unprocessed JSON string'''
        charSet = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '
        return(''.join(str(a) for a in filter(charSet.__contains__, inString)).replace('\\', '\\\\').replace('"', '\"'))



    def _processTopo(self):
        '''
        returns a tree representation of the performance metadata topology
        based on the metrics, sensors and keys, used by the ZIMon collector
        '''

        out = self.qh.getTopology()
        if out is None:
            self.logger.error("QueryHandler: getTopology returns no data. Please check the pmcollector is properly configured and running")
            raise Exception("Metadata topology for performance monitoring could not be retrieved")

        if sys.version < '3':
            out = out.decode('utf-8', 'ignore')
        metadata = json.loads(out, strict=False)

        if not metadata:
            self.logger.error("QueryHandler: _processTopo could not load json")
            raise Exception("Metadata topology for performance monitoring could not be retrieved")

        return self._processMetadata(metadata)



    def _processMetadata(self, metadata):
        '''
        For each component of the highest level (cluster or cluster_node) splits metadata in
        sub components, filters and metrics related info maps
        '''

        comp_tree = {}

        # metrics dictionary, per sensor for all elements in the metadata
        metrics = {}

        for metaStr in metadata:
            # sub components dictionary of the highest level component (cluster or
            # cluster_node)
            components = {}
            # filters dictionary, per sensor, per (cluster or cluster_node) component
            filters = {}
            # name of the  (cluster or cluster_node) component
            label = metaStr.get('fieldLabel')

            if label in comp_tree.keys():
                components = comp_tree[label]['componentsMap']
                filters = comp_tree[label]['filtersMap']

            (components, metrics, filters, metaKeys) = self._parse_topoJSONStr(
                metaStr, components, metrics, filters)
            for metaKey in metaKeys:
                (components, metrics, filters, metaKeys1) = self._parse_topoJSONStr(
                    metaKey, components, metrics, filters)
                for metaKey1 in metaKeys1:
                    (components, metrics, filters, metaKeys2) = self._parse_topoJSONStr(
                        metaKey1, components, metrics, filters)
                    for metaKey2 in metaKeys2:
                        (components, metrics, filters, metaKeys3) = self._parse_topoJSONStr(
                            metaKey2, components, metrics, filters)
                        for metaKey3 in metaKeys3:
                            (components, metrics, filters, metaKeys4) = self._parse_topoJSONStr(
                                metaKey3, components, metrics, filters)
                            for metaKey4 in metaKeys4:
                                (components, metrics, filters, metaKeys5) = self._parse_topoJSONStr(
                                    metaKey4, components, metrics, filters)

            tree_entry = {}
            tree_entry['componentsMap'] = components
            tree_entry['filtersMap'] = filters

            comp_tree[label] = tree_entry

        comp_tree['metricsMap'] = metrics
        return comp_tree



    def _parse_topoJSONStr(self, metaStr, components, metrics, filters):
        '''
        This function parses the 'node' or 'attribute' object found in the given JSON string (metaStr) in
        the componets or metrics dictionary. Also the used metric filters (per sensor) will be stored
        in the filters dictionary. If the string contains sub-tree keys, they will be returned as metaKeys
        for the next parse iteration.
        '''

        metaKeys = []
        # check if entity is a component
        if metaStr['type'] == 'node':
            field_value = metaStr['fieldLabel']
            field_name = metaStr['fieldName']
            components.setdefault(field_name, [])
            if field_value not in components[field_name]:
                components[field_name].append(field_value)
        # check if entity is a metric
        elif metaStr['type'] == 'attribute':
            partKey = metaStr['partialKey'].split('|')
            field_name = metaStr['fieldName']
            metrics.setdefault(partKey[1], [])
            if field_name not in metrics[partKey[1]]:
                metrics[partKey[1]].append(field_name)
            # check if metric allows  filter keys
            if len(partKey) >= 2:
                tags = {}
                sensor = partKey.pop(1)
                filters.setdefault(sensor, [])
                for filter in partKey:
                    for compLabel in components.keys():
                        if filter in components[compLabel]:
                            tags[compLabel] = filter
                if tags not in filters[sensor]:
                    filters[sensor].append(tags)

        # check if metaStr includes next level metaStr
        if metaStr.get('keys') is not None and len(metaStr['keys']) > 0:
            metaKeys = metaStr['keys']
        return (components, metrics, filters, metaKeys)



    def getAllSupportedMetrics(self):
        metricslist = []
        sensorslist = self.topo['metricsMap']
        for sensor, metrics in sensorslist.items():
            metricslist.extend(metrics)
        return set(metricslist)



    def getSensorForMetric(self, searchMetric):
        for sensor, metrics in self.topo['metricsMap'].items():
            if searchMetric in metrics:
                return sensor
        return None



    def getAllSupportedTagNames(self):
        tagklist = []
        for entryName, entryValues in self.topo.items():
            if not entryName == 'metricsMap':
                tagklist.extend(entryValues['componentsMap'].keys())
        return list(set(tagklist))



    def getAllSupportedTagValues(self):
        tagvlist = []
        for entryName, entryValues in self.topo.items():
            if not entryName == 'metricsMap':
                for key, values in entryValues['componentsMap'].items():
                    if not key == 'sensor':
                        tagvlist.extend(values)
        return list(set(tagvlist))



    def getAllValuesForTagName(self, searchTag):
        tagvlist = []
        for entryName, entryValues in self.topo.items():
            if not entryName == 'metricsMap':
                for key, values in entryValues['componentsMap'].items():
                    if key == searchTag:
                        tagvlist.extend(values)
        return list(set(tagvlist))



    def getAllKeysForTagValue(self, searchValue):
        tagklist = []
        for entryName, entryValues in self.topo.items():
            if not entryName == 'metricsMap':
                for key, values in entryValues['componentsMap'].items():
                    if searchValue in values:
                        tagklist.extend(key)
        return list(set(tagklist))



    def getAllFilterMapsForSensor(self, searchSensor):
        '''
        This function returns a list of filters maps found for the specified sensor name (searchSensor)
        based on metadata topology returned from zimon "topo".
        '''
        filtersMaps = []
        for entryName, entryValues in self.topo.items():
            if entryName == 'metricsMap' or searchSensor not in entryValues['filtersMap'].keys():
                continue
            filtersMaps.extend(entryValues['filtersMap'][searchSensor])
        return filtersMaps



    def getAllFilterMapsForMetric(self, searchMetric):
        searchSensor = None
        for sensor, metrics in self.topo['metricsMap'].items():
            if searchMetric in metrics:
                searchSensor = sensor
                break
        if searchSensor:
            return self.getAllFilterMapsForSensor(searchSensor)
        return []



    def getAllFilterKeysForMetric(self, searchMetric):
        searchSensor = None
        keys = []
        for sensor, metrics in self.topo['metricsMap'].items():
            if searchMetric in metrics:
                searchSensor = sensor
                break
        if searchSensor:
            filtersMap = self.getAllFilterMapsForSensor(searchSensor)
            for a in filtersMap:
                keys.extend(a.keys())

        if len(keys) > 1:
            return list(set(keys))
        return keys



    def getSensorsForMeasurementMetrics(self, searchMetrics):
        if not searchMetrics:
            raise Exception("TOPO ERROR: No metrics provided" )
        sensorsList = []
        for metric in searchMetrics:
            if (metric.find("(")>=0):
                metric = metric[metric.find("(")+1:-1]
            sensorsList.append(self.getSensorForMetric(metric))
        if len(sensorsList)> 1:
            return list(set(sensorsList))
        return sensorsList



    def getAllFilterKeysForMeasurementMetrics(self, metrics):
        filterKeys = []

        sensors = self.getSensorsForMeasurementMetrics(metrics)
        for sensor in sensors:
            filtersMap = self.getAllFilterMapsForSensor(sensor)
            for a in filtersMap:
                if filterKeys and set(filterKeys) != set(a.keys()):
                    self.logger.error("TOPO WARN: query metrics have differend filter keys")
                filterKeys.extend(a.keys())

        if len(filterKeys) > 1:
            return list(set(filterKeys))
        return filterKeys
        



    def getIdentifiersMapForQueryAttr(self, type, metricsStr, filterBy):
        if type == 'metric':
            filtersMap = self.getAllFilterMapsForMetric(metricsStr)
        elif type == 'measurement':
            sensors = self.getSensorsForMeasurementMetrics(metricsStr.split())
            for sensor in sensors:
                filtersMap = self.getAllFilterMapsForSensor(sensor)
        else:
            raise Exception("TOPO ERROR: The query type %s not supported" % type)

        if not filterBy or len(filterBy) == 0:
            return filtersMap

        if len(filterBy) > 0:
            groupFilter = {}
            conditionalFilter = {}
            singleFilter = {}

            for key, value in filterBy.items():
                if str(key).find('*') != -1:
                    foundKeys = self.getAllKeysForTagValue(value)
                    for foundKey in foundKeys:
                        singleFilter[foundKey] = value
                elif str(value).find('*') != -1:
                    groupFilter[key] = self.getAllValuesForTagName(key)
                elif str(value).find('|') != -1:
                    conditionalFilter[key] = value.split('|')
                else:
                    singleFilter[key] = value

            if singleFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] == v) for k, v in six.iteritems(singleFilter)):
                        filtersMap.remove(filtersDict)
            if conditionalFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] in v) for k, v in six.iteritems(conditionalFilter)):
                        filtersMap.remove(filtersDict)
            if groupFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] in v) for k, v in six.iteritems(groupFilter)):
                        filtersMap.remove(filtersDict)
           

        return filtersMap
