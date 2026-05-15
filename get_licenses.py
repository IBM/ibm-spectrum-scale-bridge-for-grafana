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

Created on Mai 15, 2026

@author: HWASSMAN
'''

from importlib.metadata import distributions

pkgs = []
for d in distributions():
    m = d.metadata
    name = m['Name']
    version = m['Version']

    lic = m['License']
    
    if not lic or str(lic).upper() in ['NONE', 'UNKNOWN', 'UNBEKANNT', '']:
        lic = m['License-Expression']
        
    if not lic or str(lic).upper() in ['NONE', 'UNKNOWN', 'UNBEKANNT', '']:
        classifiers = m.get_all('Classifier') or []
        lic_list = [c.split(' :: ')[-1] for c in classifiers if c.startswith('License')]
        if lic_list:
            lic = ', '.join(lic_list)
        else:
            lic = 'Nicht hinterlegt'

    # Add package name, version, license separated by tabulator
    pkgs.append(f"{name}\t{version}\t{lic}")

result = sorted(list(set(pkgs)), key=str.lower)

with open('/licenses/packages_licenses.tsv', 'w') as f:
    f.write('\n'.join(result) + '\n')
