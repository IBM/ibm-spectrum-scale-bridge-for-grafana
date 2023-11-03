'''
##############################################################################
# Copyright 2023 IBM Corp.
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

Created on Oct 25, 2023

@author: HWASSMAN
'''

import time
import copy
from typing import Callable, TypeVar, Any
from functools import wraps
from messages import MSG

T = TypeVar('T')


def execution_time(skip_attribute: bool = False) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """ Logs the name of the given function f with  passed parameter values
        and the time it takes to execute it.
    """
    def outer(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self = args[0]
            args_str = ', '.join(map(str, args[1:])) if len(args) > 1 else ''
            kwargs_str = ', '.join(f'{k}={v}' for k, v in kwargs.items()) if len(kwargs) > 0 else ''
            self.logger.trace(MSG['StartMethod'].format(f.__name__, ', '.join(filter(None, [args_str, kwargs_str]))))
            t = time.time()
            result = f(*args, **kwargs)
            duration = time.time() - t
            if not skip_attribute:
                wrapper._execution_duration = duration  # type: ignore
            self.logger.debug(MSG['RunMethod'].format(f.__name__, ', '.join(filter(None, [args_str, kwargs_str]))))
            self.logger.debug(MSG['TimerInfo'].format(f.__name__, duration))
            return result
        return wrapper
    return outer


def classattributes(default_attr, more_allowed_attr):
    """ class __init__decorator
        Parses kwargs attributes, for optional arguments uses default values,
        if not provided with kwargs
        Usage:
            1st arg is a dict of attributes with default values
            2nd arg is a list of additional allowed attributes which may be instantiated or not
    """
    def class_decorator(cls):
        def new_init(self, **kwargs):
            allowed_attr = list(default_attr.keys()) + more_allowed_attr
            default_attr_to_update = copy.deepcopy(default_attr)
            default_attr_to_update.update(kwargs)
            self.__dict__.update((k, v) for k, v in default_attr_to_update.items() if k in allowed_attr)
        cls.__init__ = new_init
        return cls
    return class_decorator


def getTimeMultiplier(timeunit):
    """ Translate OpenTSDB time units, ignoring ms (milliseconds) """
    return {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'n': 2628000,
            'y': 31536000, }.get(timeunit, -1)
