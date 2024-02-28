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


from collections import defaultdict
from typing import Set, List, Dict, DefaultDict

# dict.iteritems() deprecated in python 3
iterval = lambda d: (getattr(d, 'itervalues', None) or d.values)()


class Topo(object):
    '''
     ZIMon Metadata topology parser class
    '''

    def __init__(self, jsonStr=None):
        self.topo = jsonStr
        self.__metricsDef = defaultdict(dict)   # metrics dictionary, per sensor for all elements in the metadata
        self.__metricsType = defaultdict(dict)   # metrics types dictionary
        self.__levels = defaultdict(dict)       # component level priority dictionary, per sensor
        self.__ids = {}                                # fieldIds dictionary
        self.__groupKeys = {}
        self.__compTree = {}
        if self.topo:
            self._processMetadata(self.topo)

    def _processMetadata(self, metadata):
        '''
        For each component of the highest level (cluster or cluster_node) splits metadata in
        sub components, filters and metrics related info maps
        '''

        for metaStr in metadata:

            # sub components dictionary of the highest level component (cluster or cluster_node)
            _components = defaultdict(set)
            # filters dictionary, per sensor, per (cluster or cluster_node) component
            _filters = defaultdict(list)
            # name of the  (cluster or cluster_node) component
            label = metaStr.get('fieldLabel')

            if label in self.__compTree.keys():
                _components = self.__compTree[label]['componentsMap']
                _filters = self.__compTree[label]['filtersMap']

            self._parse_topoJSONStr(self.__metricsDef, self.__metricsType, self.__levels, self.__ids, self.__groupKeys, _components, _filters, metaStr)
            tree_entry = {}
            tree_entry['componentsMap'] = _components
            tree_entry['filtersMap'] = _filters

            # comp_tree[label] = tree_entry
            self.__compTree[label] = tree_entry

    def _parse_topoJSONStr(self, metrics, metricsType, levels, ids, groupKeys, components, filters, metaStr):
        '''
        This function parses the 'node' or 'attribute' object found in the given JSON string (metaStr) in
        the componets or metrics dictionary. Also the used metric filters (per sensor) will be stored
        in the filters dictionary. If the string contains sub-tree keys, they will be returned as metaKeys
        for the next parse iteration.
        '''

        field_value = metaStr['fieldLabel']
        field_name = metaStr['fieldName']
        field_type = metaStr['fieldSemantics']

        # check if entity is a component
        if metaStr['type'] == 'node':
            if field_value not in components[field_name]:
                components[field_name].add(field_value)
            # check if metaStr includes next level metaStr
            if 'keys' in metaStr and len(metaStr['keys']) > 0:
                for metaKey in metaStr['keys']:
                    self._parse_topoJSONStr(metrics, metricsType, levels, ids, groupKeys, components, filters, metaKey)

        # check if entity is a metric
        elif metaStr['type'] == 'attribute':

            field_id = metaStr['fieldID']
            groupKey = metaStr['partialKey']
            partKey = groupKey.split('|')
            sensor = partKey.pop(1)

            if field_name not in iterval(metrics[sensor]):
                metrics[sensor][field_id] = field_name
                metricsType[field_name] = field_type

            if groupKey not in groupKeys:
                # parse sensor relevant data f.e. groupKey, filters, levels
                groupKeys[groupKey] = len(groupKeys) + 1
                tags = {}
                levTree = {}
                for i, compValue in enumerate(partKey):
                    for compLabel in components:
                        if compValue in components[compLabel]:
                            levTree[i + 1] = compLabel
                            tags[compLabel] = compValue
                # if tags not in filters[sensor]:
                # not needed as groupkeys check will allow this to be reached only once
                filters[sensor].append(tags)
                if sensor not in levels:
                    levels[sensor] = levTree

            # parse key id
            key = f"{groupKey}|{field_name}"
            ids[key] = f"{groupKeys[groupKey]}:{field_id}"

    @property
    def allFiltersMaps(self) -> DefaultDict[str, List[Dict[str, str]]]:
        '''
        Returns a list of all filters maps returned from zimon meta data.
        Each filters map is a list of component name, component value tuples
        representing a single entity have been monitored by zimon
        '''
        filtersMaps = defaultdict(list)
        for entryName in self.__compTree.keys():
            for sensor, values in self.__compTree[entryName]['filtersMap'].items():
                filtersMaps[sensor].extend(values)
        return filtersMaps

    @property
    def allAvailableComponents(self) -> DefaultDict[str, Set[str]]:
        '''
        Returns a list of dictionaries.
        Each dictionary contains of a componet name and all found values for this
        component(tag) in the meta data returned by zimon
        '''
        components = defaultdict(set)
        for entryName in self.__compTree.keys():
            for name, values in self.__compTree[entryName]['componentsMap'].items():
                components[name].update(values)
        return components

    @property
    def allParents(self) -> List[str]:
        return list(self.__compTree.keys())

    @property
    def allIDs(self) -> Dict[str, str]:
        return self.__ids

    @property
    def groupKeys(self):
        return self.__groupKeys

    @property
    def sensorsLevels(self):
        return self.__levels

    @property
    def sensorsSpec(self):
        ''' Returns the specification of all defined sensors as dictionary of dictionaries
        sensor dictionary consists of for the sensor supported filter tags and metric_ids'''
        sensorsDicts = {}
        for sensor in self.__metricsDef.keys():
            sensorsDicts[sensor] = list(self.__levels[sensor].values()) + list(self.__metricsDef[sensor].values())
        return sensorsDicts

    @property
    def metricsSpec(self):
        ''' Returns all defined metrics as dictionary of (metric_name : metric_id) items '''
        return self.__metricsDef

    @property
    def metricsType(self):
        ''' Returns a dictionary of (metric_name : metric_type) items '''
        return self.__metricsType

    @property
    def getAllEnabledMetricsNames(self):
        ''' Returns list of all found metrics names'''
        metricslist = []
        for sensor_metrics in self.__metricsDef.values():
            metricslist.extend(list(sensor_metrics.values()))
        return list(set(metricslist))

    @property
    def getAllAvailableTagNames(self):
        return list(self.allAvailableComponents.keys())

    @property
    def getAllAvailableTagValues(self):
        tagvlist = []
        for key, values in self.allAvailableComponents.items():
            if not key == 'sensor':
                tagvlist.extend(values)
        return list(set(tagvlist))

    def getSensorForMetric(self, searchMetric):
        if (searchMetric.find("(") >= 0):
            searchMetric = searchMetric[searchMetric.find("(") + 1:-1]
        for sensor, metrics in self.__metricsDef.items():
            if searchMetric in set(metrics.values()):
                return sensor
        return None

    def getSensorMetricNames(self, searchSensor: str) -> list:
        metrics = self.__metricsDef.get(searchSensor, None)
        if metrics:
            return metrics.values()
        return []

    def getSensorsForMeasurementMetrics(self, searchMetrics):
        sensorsList = []
        for metric in searchMetrics:
            if (metric.find("(") >= 0):
                metric = metric[metric.find("(") + 1:-1]
            sensorsList.append(self.getSensorForMetric(metric))
        if len(sensorsList) > 1:
            return list(set(sensorsList))
        return sensorsList

    def getAllValuesForTagName(self, searchTag: str) -> Set[str]:
        return self.allAvailableComponents.get(searchTag, set())

    def getAllKeysForTagValue(self, searchValue: str) -> List[str]:
        tagklist = set()
        for key, values in self.allAvailableComponents.items():
            if searchValue in values:
                tagklist.add(key)
        return list(tagklist)

    def getAllFilterMapsForSensor(self, searchSensor):
        '''
        This function returns a list of filters maps found for the specified sensor name (searchSensor)
        based on metadata topology returned from zimon "topo".
        '''
        filtersMaps = []
        if searchSensor in set(self.allFiltersMaps.keys()):
            filtersMaps.extend(self.allFiltersMaps[searchSensor])
        return filtersMaps

    def getAllFilterMapsForMetric(self, searchMetric):
        searchSensor = self.getSensorForMetric(searchMetric)
        if searchSensor:
            return self.getAllFilterMapsForSensor(searchSensor)
        return []

    def getAllFilterMapsForMeasurementMetrics(self, searchMetrics):
        filtersMaps = []
        sensors = self.getSensorsForMeasurementMetrics(searchMetrics)
        for sensor in sensors:
            if sensor:
                filtersMaps = self.getAllFilterMapsForSensor(sensor)
        return filtersMaps

    def getKeyGranularitylistForMetric(self, searchMetric):
        searchSensor = self.getSensorForMetric(searchMetric)
        if not searchSensor:
            return None
        for sensor, levels in self.__levels.items():
            if searchSensor == sensor:
                return levels
        return None

    def getAllFilterKeysForMetric(self, searchMetric):
        keys = []
        filtersMap = self.getAllFilterMapsForMetric(searchMetric)
        for a in filtersMap:
            keys.extend(list(a.keys()))
        if len(keys) > 1:
            return list(set(keys))
        return keys

    def getAllFilterKeysForSensor(self, searchSensor):
        filter_keys = set()
        filtersMap = self.getAllFilterMapsForSensor(searchSensor)
        for filter in filtersMap:
            filter_keys.update(filter.keys())
        return list(filter_keys)

    def getAllFilterKeysForMeasurementsMetrics(self, searchMetrics):
        filterKeys = []
        filtersMap = self.getAllFilterMapsForMeasurementMetrics(searchMetrics)
        for a in filtersMap:
            filterKeys.extend(list(a.keys()))
        if len(filterKeys) > 1:
            return list(set(filterKeys))
        return filterKeys

    def getFiltersOnlyWithGPFSTypeMounts(self, listGPFSmounts):
        '''returns self.allFiltersMaps, but for DiskFree sensor
           filters includes only gpfs type mounts'''
        onlyGPFS = []
        filtersMaps = self.allFiltersMaps
        if listGPFSmounts and 'DiskFree' in filtersMaps:
            diskFree_filters = filtersMaps['DiskFree']
            for filtersDict in diskFree_filters:
                if filtersDict['mountPoint'] in listGPFSmounts:
                    onlyGPFS.append(filtersDict)
            filtersMaps['DiskFree'] = onlyGPFS
        return filtersMaps

    def getIdentifiersMapForQueryAttr(self, type_, metricsStr, filterBy):
        if type_ == 'metric':
            filtersMap = self.getAllFilterMapsForMetric(metricsStr)
        elif type_ == 'measurement':
            filtersMap = self.getAllFilterMapsForMeasurementMetrics(metricsStr.split(","))
        else:
            raise Exception("TOPO ERROR: The query type %s not supported" % type_)

        if not filtersMap or not filterBy or len(filterBy) == 0:
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

            iteritems = lambda d: (getattr(d, 'iteritems', None) or d.items)()
            if singleFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] == v) for k, v in iteritems(singleFilter)):
                        filtersMap.remove(filtersDict)
            if conditionalFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] in v) for k, v in iteritems(conditionalFilter)):
                        filtersMap.remove(filtersDict)
            if groupFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] in v) for k, v in iteritems(groupFilter)):
                        filtersMap.remove(filtersDict)

        return filtersMap

    def calculateQueryPriority(self, metric, filterBy):

        priority = -1

        if (metric.find("(") >= 0):
            metric = metric[metric.find("(") + 1:-1]
        levels = self.getKeyGranularitylistForMetric(metric)
        if not levels:
            return priority
        max_level = len(levels) + 1
        if not filterBy or len(filterBy) == 0:
            priority = max_level
            return priority

        if len(filterBy) > max_level:
            return priority

        filterKeys = list(filterBy.keys())
        if '*' in filterBy.values():
            for key, value in filterBy.iteritems():
                if value == '*':
                    filterKeys.remove(key)

        foundLevels = [0]
        for level, tag in levels.items():
            for filterKey in filterKeys:
                if filterKey == tag:
                    foundLevels.append(level)

        # for node-wide metrics use the filter count ranking the priority
        if 'node' in levels[1]:
            filter_level = (len(foundLevels) - 1)
        # for cluster-wide metrics use the filter order ranking the priority
        else:
            filter_level = max(foundLevels)

        priority = max_level - filter_level
        return priority
