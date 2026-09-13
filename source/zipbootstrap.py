'''
##############################################################################
# Copyright 2025 IBM Corp.
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

Zip bootstrap for the IBM Storage Scale bridge for Grafana.

On bare-metal GPFS nodes cherrypy may not be installed system-wide but is
bundled in /usr/lpp/mmfs/lib/python_external_libs.zip.  Importing this
module before any third-party import ensures the zip is on sys.path when
needed, without requiring any change to the environment outside the process.

This module intentionally contains only stdlib imports so it can be safely
imported even when no third-party packages are available yet.
'''

import os
import sys

_EXT_LIBS_ZIP = '/usr/lpp/mmfs/lib/python_external_libs.zip'

try:
    import cherrypy as _cherrypy   # already available — nothing to do
    del _cherrypy
except ImportError:
    if os.path.isfile(_EXT_LIBS_ZIP) and _EXT_LIBS_ZIP not in sys.path:
        sys.path.insert(0, _EXT_LIBS_ZIP)
