'''
##############################################################################
# Copyright 2024 IBM Corp.
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

Created on Feb 09, 2024

@author: HWASSMAN
'''

global inspect
inspect = False

global inspect_special
inspect_special = False

global urllib3_debug
urllib3_debug = 0

# measure requests Time-To-First-Byte (TTFB)
global requests_elapsed_time
requests_elapsed_time = False
