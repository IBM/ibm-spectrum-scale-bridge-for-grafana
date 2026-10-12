'''
##############################################################################
# Copyright 2026 IBM Corp.
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

Created on Apr 17, 2026

@author: HWASSMAN
'''

import os

try:
    import psutil as _psutil
    _psutil_available = True
except ImportError:
    _psutil_available = False


def _read_file(path, default=None):
    """Read a single-line file, return stripped string or default on any error."""
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def _proc_rss_mb(pid):
    """Read VmRSS from /proc/<pid>/status. Returns float MB or None."""
    try:
        with open(f'/proc/{pid}/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    kb = int(line.split()[1])
                    return round(kb / 1024, 1)
    except OSError:
        pass
    return None


def _proc_threads(pid):
    """Read Threads from /proc/<pid>/status. Returns int or None."""
    try:
        with open(f'/proc/{pid}/status') as f:
            for line in f:
                if line.startswith('Threads:'):
                    return int(line.split()[1])
    except OSError:
        pass
    return None


def _cgroup_memory():
    """
    Read container memory limit and current usage from cgroups v2.
    Returns dict with limit_mb / used_mb, or empty dict if not in a container.
    """
    result = {}
    raw_limit = _read_file('/sys/fs/cgroup/memory.max')
    if raw_limit and raw_limit != 'max':
        result['limit_mb'] = round(int(raw_limit) / (1024 * 1024), 1)
    raw_used = _read_file('/sys/fs/cgroup/memory.current')
    if raw_used:
        result['used_mb'] = round(int(raw_used) / (1024 * 1024), 1)
    return result


def _cgroup_cpu():
    """
    Read container CPU quota from cgroups v2 cpu.max.
    Format is '<quota> <period>' or 'max <period>' (no limit).
    Returns dict with quota_cores, or empty dict if not in a container.
    """
    raw = _read_file('/sys/fs/cgroup/cpu.max')
    if not raw:
        return {}
    parts = raw.split()
    if len(parts) == 2 and parts[0] != 'max':
        try:
            quota_cores = round(int(parts[0]) / int(parts[1]), 2)
            return {'quota_cores': quota_cores, 'raw': raw}
        except (ValueError, ZeroDivisionError):
            pass
    return {'raw': raw}


def collect_process_info():
    """
    Collect process-level and container-level resource usage.
    Always uses /proc and /sys/fs/cgroup (Linux).
    Augments with psutil fields when psutil is installed.
    """
    pid = os.getpid()
    info = {'pid': pid}

    # --- memory ---
    memory = {}
    rss = _proc_rss_mb(pid)
    if rss is not None:
        memory['rss_mb'] = rss
    memory.update(_cgroup_memory())
    if memory:
        info['memory'] = memory

    # --- cpu / threads ---
    cpu = {}
    threads = _proc_threads(pid)
    if threads is not None:
        cpu['threads'] = threads
    cpu.update(_cgroup_cpu())
    if cpu:
        info['cpu'] = cpu

    # --- psutil (optional) ---
    if _psutil_available:
        try:
            proc = _psutil.Process(pid)
            psutil_info = {
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'memory_percent': round(proc.memory_percent(), 2),
            }
            try:
                psutil_info['open_fds'] = proc.num_fds()
            except AttributeError:
                pass  # Windows
            info['psutil'] = psutil_info
        except Exception:
            pass

    return info
