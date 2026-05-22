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
import cherrypy
import analytics
import threading
from threading import Lock
from typing import Callable, TypeVar
from functools import wraps
from messages import MSG
from profiler import Profiler

T = TypeVar('T')


def get_request_host() -> str:
    """
    Extract host (without port) from cherrypy request headers.
    Returns:
        Host string without port, or 'unknown' if not available
    """
    try:
        host_header = cherrypy.request.headers.get('Host', '')
        host = host_header.split(':')[0] if host_header else 'unknown'
        return host
    except Exception:
        return 'unknown'


def get_runtime_statistics(enabled: bool = False) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """ Conditionally executes the passed through function f with profiling."""

    def outer(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            profiler = Profiler()
            result = profiler.run(f, *args, **kwargs)
            return result
        return wrapper

    def no_outer(f: Callable[..., T]) -> Callable[..., T]:
        return f
    return outer if enabled else no_outer


@get_runtime_statistics(enabled=analytics.runtime_profiling)
def execution_time() -> Callable[[Callable[..., T]], Callable[..., T]]:
    """ Logs the name of the given function f with  passed parameter values
        and the time it takes to execute it.
    """
    def outer(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self = args[0]

            # self.logger.trace(MSG['StartMethod'].format(f.__name__, ', '.join(filter(None, [args_str, kwargs_str]))))
            t1 = time.perf_counter(), time.process_time()
            result = f(*args, **kwargs)
            t2 = time.perf_counter(), time.process_time()
            duration = t2[0] - t1[0]
            cpu_time = t2[1] - t1[1]
            # keep as alternative following line
            # wrapper._execution_duration = duration

            # Check if httpMetrics is enabled via analytics module
            if analytics.http_metrics_enabled and hasattr(self, 'internal_metrics'):
                try:
                    import threading
                    current = threading.current_thread()
                    # Use the class name as prefix
                    class_name = self.__class__.__name__
                    metric_name = f"{class_name}_{f.__name__}"
                    self.internal_metrics[current.ident][metric_name] = self.internal_metrics[current.ident].get(metric_name, 0) + duration
                    # metric_count = f"{metric_name}_count"
                    # self.internal_metrics[current.ident][metric_count] = self.internal_metrics[current.ident].get(metric_count, 0) + 1
                except Exception as e:
                    self.logger.error(MSG['InternalExecutionMetricsCacheFailed'].format(e))
            elif not analytics.http_metrics_enabled:
                args_str = ', '.join(map(str, args[1:])) if len(args) > 1 else ''
                kwargs_str = ', '.join(f'{k}={v}' for k, v in kwargs.items()) if len(kwargs) > 0 else ''
                self.logger.debug(MSG['RunMethod'].format(f.__name__, ', '.join(filter(None, [args_str, kwargs_str]))))
                self.logger.debug(MSG['TimerInfo'].format(f.__name__, duration, cpu_time))
            else:
                self.logger.trace(f'{f.__name__} does not have internal metrics')
            return result
        return wrapper
    return outer


@get_runtime_statistics(enabled=analytics.runtime_profiling)
def cond_execution_time(detail_level: int = 1) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """ Wrapper method that measures execution time of wrapped methods.
    This decorator conditionally logs the name of the given function with
    passed parameter values and the time it takes to execute it, based on
    the analytics.inspect_special detail level setting.
    The wrapper only executes timing measurements if the global
    analytics.inspect_special setting is greater than or equal to the
    specified detail_level. This allows fine-grained control over which
    methods are profiled based on the desired level of detail.
    Args:
        detail_level: Required detail level (1-5). The wrapper only measures
                     execution time if analytics.inspect_special >= detail_level.
                     Level 1 = basic profiling, Level 5 = most detailed profiling.
     Returns:
        A decorator that wraps the function with execution time measurement,
        or returns the original function unchanged if detail level is insufficient.
    Example:
        @cond_execution_time(detail_level=3)
        def my_method(self):
            # This will only be timed if analytics.inspect_special >= 3
            pass
    """
    # Check analytics settings at decoration time
    should_measure = analytics.inspect_special >= detail_level

    def outer(f: Callable[..., T]) -> Callable[..., T]:
        # Pre-compute metric name prefix for detail_levels 2-4 (optimization)
        if detail_level == 4:
            metric_prefix = "perfmon_"
        elif detail_level == 3:
            metric_prefix = "qh_"
        elif detail_level == 2:
            metric_prefix = "collector_"
        else:
            metric_prefix = None

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self = args[0]
            if hasattr(self, 'logger'):
                logger = self.logger
            else:
                from bridgeLogger import getBridgeLogger
                logger = getBridgeLogger()

            # logger.trace(MSG['StartMethod'].format(f.__name__, ', '.join(filter(None, [args_str, kwargs_str]))))
            t1 = time.perf_counter(), time.process_time()
            result = f(*args, **kwargs)
            t2 = time.perf_counter(), time.process_time()
            duration = t2[0] - t1[0]
            cpu_time = t2[1] - t1[1]
            # wrapper._execution_duration = duration  # type: ignore

            # Check if httpMetrics is enabled via analytics module
            if analytics.http_metrics_enabled and hasattr(self, 'internal_metrics'):
                try:
                    current = threading.current_thread()
                    # Determine metric name using pre-computed prefix
                    if metric_prefix:
                        metric_name = f"{metric_prefix}{f.__name__}"
                    elif detail_level == 1:
                        # Use the class name as prefix
                        metric_name = f"{self.__class__.__name__}_{f.__name__}"
                    else:
                        metric_name = f.__name__
                    self.internal_metrics[current.ident][metric_name] = self.internal_metrics[current.ident].get(metric_name, 0) + duration
                    # metric_count = f"{metric_name}_count"
                    # self.internal_metrics[current.ident][metric_count] = self.internal_metrics[current.ident].get(metric_count, 0) + 1
                except Exception as e:
                    logger.error(MSG['InternalExecutionMetricsCacheFailed'].format(e))
            elif not analytics.http_metrics_enabled:
                args_str = ', '.join(map(str, args[1:])) if len(args) > 1 else ''
                kwargs_str = ', '.join(f'{k}={v}' for k, v in kwargs.items()) if len(kwargs) > 0 else ''
                logger.debug(MSG['RunMethod'].format(f.__name__, ', '.join(filter(None, [args_str, kwargs_str]))))
                logger.debug(MSG['TimerInfo'].format(f.__name__, duration, cpu_time))
            else:
                logger.trace(f'{f.__name__} does not have internal metrics')
            return result
        return wrapper

    def no_outer(f: Callable[..., T]) -> Callable[..., T]:
        return f
    return outer if should_measure else no_outer


def synchronized(lock: Lock):
    """Decorator which takes a Lock and runs the function under that Lock"""
    def funcWrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                ret = func(*args, **kwargs)
            return ret
        return wrapper
    return funcWrapper


def classattributes(default_attr: dict, more_allowed_attr: list):
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
    return {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'n': 2628000, 'y': 31536000}.get(timeunit, -1)
