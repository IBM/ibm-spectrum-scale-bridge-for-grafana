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

Created on Jan 2026

@author: HWASSMAN
'''

import cherrypy
import json
import configparser
import logging
import os
import re

from messages import MSG
from bridgeLogger import getBridgeLogger
import confParser


# ---------------------------------------------------------------------------
# Key classification
# ---------------------------------------------------------------------------

# Keys safe to change at runtime (no server socket / file-handle impact)
WRITABLE_KEYS = frozenset({
    "rawCounters",
    "logLevel",
    "includeDiskData",
    "retryDelay",
})

# Subset of WRITABLE_KEYS that require an explicit runtime side-effect beyond
# updating self._config (e.g. syncing the logging framework's handler levels).
SIDE_EFFECT_KEYS = frozenset({
    "logLevel",
})

# Keys that exist in the config but require a bridge restart to take effect
RESTART_REQUIRED_KEYS = frozenset({
    "prometheus",
    "port",
    "protocol",
    "server",
    "serverPort",
    "opentsdbBindIp",
    "promBindIp",
    "tlsKeyPath",
    "tlsKeyFile",
    "tlsCertFile",
    "caCertPath",
    "logPath",
    "logFile",
    "cpAccessLog",
    "cpAccessLogBackups",
})

# Keys that must never be returned or accepted over the API (secrets)
HIDDEN_KEYS = frozenset({
    "password",
    "apiKeyValue",
    "configFile",
})

# Regex that matches a commented-out INI assignment, e.g.:
#   # port = 4242
#   # tlsKeyPath = /etc/bridge_ssl/certs
#
# Two guards prevent false positives from INI example/doc lines:
#
#   1. Key length cap {0,19}: the longest real config key is 18 chars
#      (cpAccessLogBackups).  Long tokens such as the base64 example line
#         #   TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg==
#      are rejected because the 30-char token exceeds the cap, so the
#      trailing "==" is never reached.
#
#   2. Non-empty value (\s*\S after =): a bare "# key =" line with nothing
#      after the equals sign is not a real assignment and is ignored.
_COMMENTED_KEY_RE = re.compile(r'^\s*#\s*([A-Za-z][A-Za-z0-9_]{0,19})\s*=\s*\S')


def _parse_commented_keys(ini_files):
    """Return {key: section} for every commented-out key=value line found
    across *ini_files* (an ordered list of file paths).

    Files are scanned in order with plain assignment (last file wins), so
    the custom override file takes precedence over the template — matching
    the behaviour of ``configparser.read()`` for live keys.
    """
    commented = {}
    for path in ini_files:
        current_section = None
        try:
            with open(path, encoding='utf-8') as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped.startswith('[') and stripped.endswith(']'):
                        current_section = stripped[1:-1]
                        continue
                    if current_section is None:
                        continue
                    m = _COMMENTED_KEY_RE.match(line)
                    if m:
                        commented[m.group(1)] = current_section
        except OSError:
            pass
    return commented


def _build_section_maps(config_manager, brFullConfig=None):
    """Build key-section lookup dicts by reading the INI files directly.

    Reads every section and key from the template config.ini (always present)
    and, if available, the effective custom override file.  The result is two
    plain dicts:

        key_to_section  : { "rawCounters": "prometheues_exporter_plugin", ... }
        section_to_keys : { "prometheues_exporter_plugin": ["prometheus",
                                                             "promBindIp",
                                                             "rawCounters"], ... }

    Because configparser only sees uncommented lines, keys that are defined in
    comments are covered via two additional sources, tried in order:
      1. The custom override file — the user may have uncommented them there
         (already handled by configparser above).
      2. ``_parse_commented_keys`` — scans all INI files for commented-out
         assignments; custom file wins over template (last-file-wins).
    """
    key_to_section = {}

    files_to_read = [config_manager.templateFile]
    effective_custom = config_manager.customFile or (
        config_manager.DEFAULT_CUSTOM_CONFIG
        if os.path.isfile(config_manager.DEFAULT_CUSTOM_CONFIG)
        else None
    )
    if effective_custom and effective_custom != config_manager.templateFile:
        files_to_read.append(effective_custom)

    cfg = configparser.ConfigParser()
    cfg.optionxform = str          # preserve key-name casing
    cfg.read(files_to_read)        # later files override earlier ones

    for section in cfg.sections():
        for key in cfg.options(section):
            # Template wins: only record the first section that owns a key.
            key_to_section.setdefault(key, section)

    # Fill gaps for keys that were commented-out in any of the INI files.
    # setdefault: live keys (already in key_to_section) are never overridden.
    for key, section in _parse_commented_keys(files_to_read).items():
        key_to_section.setdefault(key, section)

    # Every key in brFullConfig must already be covered by the two passes above
    # (CLI args only override existing schema keys, never introduce new ones).
    # Any key that is still unmapped here signals a bug — log a warning.
    if brFullConfig:
        unmapped = [k for k in brFullConfig if k not in key_to_section]
        if unmapped:
            getBridgeLogger().warning(
                "Config keys not found in any INI section (template unreadable "
                "or unknown CLI flag): %s", unmapped)

    section_to_keys = {}
    for key, section in key_to_section.items():
        section_to_keys.setdefault(section, []).append(key)

    return key_to_section, section_to_keys


class ConfigApi(object):
    """REST handler for reading and updating runtime bridge configuration.

    Mounted at /config on the same CherryPy server as all other endpoints;
    inherits the global Basic Auth protection automatically.

    Flat (key-level) endpoints
    --------------------------
    GET   /config             return nested {section: {key: value}} for all
                              non-secret settings; commented-out keys appear
                              as "disabled"
    GET   /config?key=K       return a single setting (flat {key: value})
    PATCH /config             batch update (writable keys only); JSON body
    PUT   /config?key=K       single key update; JSON body {"value": V}

    Section-level endpoints
    -----------------------
    GET   /config/sections          list available INI section names
    GET   /config/section/<name>    all non-secret keys in that section,
                                    disabled keys shown as "disabled"
    PATCH /config/section/<name>    update writable keys in that section

    Initialisation endpoint
    -----------------------
    POST  /config/init        create the custom config file so that subsequent
                              write calls can persist changes across restarts

    Validation endpoint
    -------------------
    GET   /config/validate    validate the current live configuration
    POST  /config/validate    dry-run: validate the live config merged with the
                              supplied JSON body — nothing is applied or written
    """

    exposed = True

    def __init__(self, logger, brFullConfig, config_manager):
        """
        Parameters
        ----------
        logger         : bridge logger instance
        brFullConfig       : live flat settings dict shared with all plugins
        config_manager : ConfigManager singleton (provides customFile path)
        """
        self.logger = logger
        self._config = brFullConfig
        self._cm = config_manager

        self._key_to_section, self._section_to_keys = _build_section_maps(
            config_manager, self._config)

        # Sub-handler mounted at /config/section and /config/sections
        self.section = _SectionApi(logger, config_manager,
                                   self._visible, self._nested_view,
                                   self._apply_update,
                                   self._section_to_keys)
        self.sections = _SectionListApi(logger, self._section_to_keys)
        self.init = _InitApi(logger, config_manager)
        self.validate = _ValidateApi(logger, self._config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _visible(self):
        """Return a flat copy of the live config with secret keys removed."""
        return {k: v for k, v in self._config.items() if k not in HIDDEN_KEYS}

    def _nested_view(self, section_name=None):
        """Return config as a nested dict  { section: { key: value } }.

        Keys known to the INI structure but absent from the live config
        (i.e. commented-out in the INI and never set via CLI or custom file)
        are included with the sentinel value ``"disabled"``.
        Secret keys (HIDDEN_KEYS) are always omitted entirely.

        When *section_name* is given, only that section's dict is returned.
        """
        visible = self._visible()
        # Determine which sections to include
        sections = ([section_name] if section_name else
                    sorted(self._section_to_keys.keys()))
        result = {}
        for sect in sections:
            sect_dict = {}
            for key in self._section_to_keys.get(sect, []):
                if key in HIDDEN_KEYS:
                    continue
                sect_dict[key] = visible.get(key, "disabled")
            result[sect] = sect_dict
        return result

    def _persist(self, updates):
        """Write *updates* back to the effective custom config file.

        Returns ``True`` when written successfully, a message string explaining
        why persistence was skipped, or ``False`` on an I/O error.
        """
        target = (self._cm.customFile
                  or (self._cm.DEFAULT_CUSTOM_CONFIG
                      if os.path.isfile(self._cm.DEFAULT_CUSTOM_CONFIG)
                      else None))
        if not target:
            self.logger.warning(MSG['ConfigApiNoTarget'])
            return MSG['ConfigApiNoTarget']
        if os.path.abspath(target) == os.path.abspath(self._cm.templateFile):
            self.logger.warning(MSG['ConfigApiTemplateWriteBlocked'])
            return MSG['ConfigApiTemplateWriteBlocked']

        # Use the template as the authoritative section source — it is never
        # written to and cannot be tainted by prior misplacements.
        template_sections = _parse_commented_keys([self._cm.templateFile])

        cfg = configparser.ConfigParser()
        cfg.optionxform = str          # preserve key-name casing
        cfg.read(target)               # no-op when file does not yet exist

        for key, value in updates.items():
            # Evict from every section first — heals any prior misplacement.
            for s in cfg.sections():
                cfg.remove_option(s, key)
            if value is not None:
                # Template-derived section wins; fall back to runtime map for
                # keys that are live (not commented) in the template.
                section = (template_sections.get(key)
                           or self._key_to_section.get(key))
                if section:
                    if not cfg.has_section(section):
                        cfg.add_section(section)
                    cfg.set(section, key, str(value))

        try:
            with open(target, "w") as fh:
                cfg.write(fh)
            self.logger.info(MSG['ConfigApiPersisted'].format(target))
            return True
        except OSError as exc:
            self.logger.error(MSG['ConfigApiPersistError'].format(str(exc)))
            return False

    def _apply_update(self, body):
        """Validate and apply a {key: value} dict.

        ``RESTART_REQUIRED_KEYS`` are not applied to the live config but are
        still persisted to the config file so the change takes effect after the
        next bridge restart.  Passing ``null`` / ``None`` as the value removes
        the key from the file entirely (disables the feature).

        Returns (updated, rejected, restart_required, persisted).
          updated         — keys applied to the live process immediately
          rejected        — keys refused entirely (hidden / unknown / read-only)
          restart_required — keys accepted and persisted but needing a restart
          persisted       — True / False / explanatory string
        """
        updated = {}
        rejected = {}
        restart_required = {}
        restart_pending = {}

        for key, value in body.items():
            if key in HIDDEN_KEYS:
                rejected[key] = "forbidden: secret key"
            elif key in RESTART_REQUIRED_KEYS:
                restart_required[key] = MSG['ConfigApiRestartRequired']
                restart_pending[key] = value
            elif key not in self._config:
                rejected[key] = "unknown key"
            elif key not in WRITABLE_KEYS:
                rejected[key] = "read-only key"
            else:
                self._config[key] = value
                updated[key] = value
                if key in SIDE_EFFECT_KEYS:
                    self._apply_side_effects(key, value)
                self.logger.details(MSG['ConfigApiUpdated'].format(key, value))

        # Persist both live updates and restart-pending changes.
        to_persist = {**updated, **restart_pending}
        persisted = self._persist(to_persist) if to_persist else False
        return updated, rejected, restart_required, persisted

    def _apply_side_effects(self, key, value):
        """Apply the runtime side-effect for *key* (a member of SIDE_EFFECT_KEYS).

        Called only after the key has been validated, written to self._config,
        and confirmed to be in SIDE_EFFECT_KEYS.
        """
        if key == "logLevel":
            try:
                level = logging._checkLevel(value)
            except (ValueError, TypeError):
                self.logger.warning(
                    f"logLevel value {value!r} not recognised by logging; "
                    "handler levels not updated")
                return
            bridge_logger = getBridgeLogger()
            for handler in bridge_logger.handlers:
                handler.setLevel(level)
            self.logger.info(
                f"logLevel updated to {level} ({logging.getLevelName(level)})")

    @staticmethod
    def _json_response(data):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps(data).encode('utf-8')

    @staticmethod
    def _read_body():
        try:
            return json.loads(cherrypy.request.body.read().decode('utf-8'))
        except (ValueError, AttributeError) as exc:
            raise cherrypy.HTTPError(400, f"Invalid JSON body: {exc}")

    # ------------------------------------------------------------------
    # HTTP handlers (flat / key-level)
    # ------------------------------------------------------------------

    def GET(self, key=None, **params):
        """Return current configuration.

        Without query parameters: returns nested {section: {key: value}};
        commented-out keys appear as "disabled".
        With ?key=K: returns a flat {key: value} for that single key.
        """
        self.logger.trace(f"GET /config key={key!r}")
        if key is not None:
            visible = self._visible()
            if key not in visible:
                raise cherrypy.HTTPError(404, f"Unknown or hidden config key: {key!r}")
            return self._json_response({key: visible[key]})
        return self._json_response(self._nested_view())

    def PATCH(self, **params):
        """Batch-update one or more writable config keys.

        Request body (JSON): { "rawCounters": false, "logLevel": 20 }
        """
        body = self._read_body()
        if not isinstance(body, dict):
            raise cherrypy.HTTPError(400, "Request body must be a JSON object")
        updated, rejected, restart_required, persisted = self._apply_update(body)
        return self._json_response({"updated": updated,
                                    "restart_required": restart_required,
                                    "rejected": rejected,
                                    "persisted": persisted})

    def PUT(self, key=None, **params):
        """Update a single writable config key.

        URL:  PUT /config?key=rawCounters
        Body: { "value": false }
        """
        if not key:
            raise cherrypy.HTTPError(400, "Query parameter 'key' is required")
        body = self._read_body()
        if "value" not in body:
            raise cherrypy.HTTPError(400, "JSON body must contain a 'value' field")
        updated, rejected, restart_required, persisted = self._apply_update({key: body["value"]})
        return self._json_response({"updated": updated,
                                    "restart_required": restart_required,
                                    "rejected": rejected,
                                    "persisted": persisted})

    def OPTIONS(self, **params):
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, PATCH, PUT, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800


# ---------------------------------------------------------------------------
# Sub-handlers for section-level access
# ---------------------------------------------------------------------------

class _SectionListApi(object):
    """Handles GET /config/sections — lists available INI section names."""

    exposed = True

    def __init__(self, logger, section_to_keys):
        self.logger = logger
        self._section_to_keys = section_to_keys

    def GET(self, **params):
        self.logger.trace("GET /config/sections")
        sections = sorted(self._section_to_keys.keys())
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({"sections": sections}).encode('utf-8')

    def OPTIONS(self, **params):
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800


class _SectionApi(object):
    """Handles /config/section/<name> — GET and PATCH at section granularity."""

    exposed = True

    def __init__(self, logger, config_manager, visible_fn,
                 nested_view_fn, apply_fn, section_to_keys):
        self.logger = logger
        self._cm = config_manager
        self._visible = visible_fn          # bound method from ConfigApi
        self._nested_view = nested_view_fn  # bound method from ConfigApi
        self._apply_update = apply_fn       # bound method from ConfigApi
        self._section_to_keys = section_to_keys

    def _section_view(self, section_name):
        """Return key/value pairs for *section_name*.

        Commented-out keys (absent from the live config) appear as
        ``"disabled"``; secret keys are always omitted.
        """
        if section_name not in self._section_to_keys:
            raise cherrypy.HTTPError(404, f"Unknown section: {section_name!r}. "
                                     f"Available: {sorted(self._section_to_keys)}")
        nested = self._nested_view(section_name)
        return nested.get(section_name, {})

    def GET(self, section_name=None, **params):
        """Return all non-secret settings belonging to *section_name*.

        URL: GET /config/section/prometheues_exporter_plugin
        """
        self.logger.trace(f"GET /config/section/{section_name!r}")
        data = self._section_view(section_name)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps(data).encode('utf-8')

    def PATCH(self, section_name=None, **params):
        """Update writable keys within *section_name*.

        URL:  PATCH /config/section/prometheues_exporter_plugin
        Body: { "rawCounters": false }

        Keys in the body that do not belong to the specified section are
        rejected immediately, before any update is applied.
        """
        self.logger.trace(f"PATCH /config/section/{section_name!r}")
        # Validate section name first
        if section_name not in self._section_to_keys:
            raise cherrypy.HTTPError(404, f"Unknown section: {section_name!r}. "
                                     f"Available: {sorted(self._section_to_keys)}")

        try:
            body = json.loads(cherrypy.request.body.read().decode('utf-8'))
        except (ValueError, AttributeError) as exc:
            raise cherrypy.HTTPError(400, f"Invalid JSON body: {exc}")

        if not isinstance(body, dict):
            raise cherrypy.HTTPError(400, "Request body must be a JSON object")

        section_keys = set(self._section_to_keys[section_name])
        wrong_section = {k: f"key does not belong to section '{section_name}'"
                         for k in body if k not in section_keys}
        valid_body = {k: v for k, v in body.items() if k in section_keys}

        updated, rejected, restart_required, persisted = self._apply_update(valid_body)
        rejected.update(wrong_section)

        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps({"section": section_name,
                           "updated": updated,
                           "restart_required": restart_required,
                           "rejected": rejected,
                           "persisted": persisted}).encode('utf-8')

    def OPTIONS(self, **params):
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, PATCH, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800


class _InitApi(object):
    """Handles POST /config/init — creates the custom config file.

    When the bridge is running without a custom config file, write calls
    succeed in-memory but are not persisted across restarts.  This endpoint
    creates the default custom config file
    (``/etc/grafanabridge/config.ini``) so subsequent write calls have a
    target to persist to — no restart required.
    """

    exposed = True

    def __init__(self, logger, config_manager):
        self.logger = logger
        self._cm = config_manager

    def POST(self, **params):
        """Create the custom config file if it does not already exist.

        URL: POST /config/init
        Body (optional JSON): { "path": "/my/custom/config.ini" }

        Path resolution:
          1. "path" key in the request body — caller chooses the location
          2. Default RPM location (/etc/grafanabridge/config.ini)

        Note: if the bridge was started with -F, that file already exists by
        definition (startup validates it), so this endpoint is only meaningful
        when no custom file is present at all.

        Returns:
            {"created": true,  "path": "<path>"}  — file was created
            {"created": false, "path": "<path>",
             "reason": "already exists"}           — file already present
            {"created": false, "reason": "..."}    — could not be created
        """
        self.logger.trace("POST /config/init")

        # Resolve target: body "path" wins, otherwise use the default location.
        body = {}
        raw = cherrypy.request.body.read()
        if raw:
            try:
                body = json.loads(raw.decode('utf-8'))
            except (ValueError, AttributeError) as exc:
                raise cherrypy.HTTPError(400, f"Invalid JSON body: {exc}")
            if not isinstance(body, dict):
                raise cherrypy.HTTPError(400, "Request body must be a JSON object")

        target = body.get('path') or self._cm.DEFAULT_CUSTOM_CONFIG

        if os.path.isfile(target):
            self.logger.info(MSG['ConfigApiInitAlreadyExists'].format(target))
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps({"created": False,
                               "path": target,
                               "reason": "already exists"}).encode('utf-8')
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            open(target, 'w').close()
            self.logger.info(MSG['ConfigApiInitCreated'].format(target))
        except OSError as exc:
            self.logger.error(MSG['ConfigApiInitError'].format(str(exc)))
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps({"created": False,
                               "reason": str(exc)}).encode('utf-8')

        cherrypy.response.status = 201
        cherrypy.response.headers['Content-Type'] = 'application/json'
        response = {"created": True, "path": target}
        if target != self._cm.DEFAULT_CUSTOM_CONFIG:
            response["note"] = MSG['ConfigApiInitRestartRequired'].format(target)
        return json.dumps(response).encode('utf-8')

    def OPTIONS(self, **params):
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800


# ---------------------------------------------------------------------------
# Validation sub-handler
# ---------------------------------------------------------------------------

def _run_validators(candidate):
    """Run all startup-time check functions against *candidate* config dict.

    Returns a list of error message strings (empty list means valid).
    The order matches the check sequence in confParser.getSettings().
    """
    errors = []
    for fn in (
        confParser.checkApplicationPort,
        confParser.checkAPIsettings,
        confParser.checkBasicAuthsettings,
        confParser.checkTLSsettings,
        confParser.checkCAsettings,
    ):
        ok, msg = fn(candidate)
        if not ok:
            errors.append(msg)
    return errors


class _ValidateApi(object):
    """Handles GET/POST /config/validate.

    GET  /config/validate
        Validates the current live configuration against the same rules that
        are checked at bridge startup.  Returns {"valid": true} or
        {"valid": false, "errors": [...]}.

    POST /config/validate   body: {"key": value, ...}
        Performs a dry-run: merges the supplied key/value pairs into a copy of
        the live configuration and validates the result.  Nothing is applied or
        written to disk.  Returns the same structure as GET, plus a
        "candidate" field showing the merged values that were checked (secrets
        omitted).
    """

    exposed = True

    def __init__(self, logger, config):
        self.logger = logger
        self._config = config

    def GET(self, **params):
        self.logger.trace("GET /config/validate")
        errors = _run_validators(self._config)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        if errors:
            return json.dumps({"valid": False, "errors": errors}).encode('utf-8')
        return json.dumps({"valid": True}).encode('utf-8')

    def POST(self, **params):
        """Dry-run validation: merge the request body into a copy of the live
        config and validate — nothing is applied or persisted."""
        self.logger.trace("POST /config/validate")
        raw = cherrypy.request.body.read()
        if raw:
            try:
                body = json.loads(raw.decode('utf-8'))
            except (ValueError, AttributeError) as exc:
                raise cherrypy.HTTPError(400, f"Invalid JSON body: {exc}")
            if not isinstance(body, dict):
                raise cherrypy.HTTPError(400, "Request body must be a JSON object")
        else:
            body = {}

        # Build candidate: start from a copy of the live config, overlay body.
        candidate = dict(self._config)
        candidate.update(body)

        errors = _run_validators(candidate)

        # Build a safe view of the candidate (secrets stripped).
        safe_candidate = {k: v for k, v in candidate.items()
                          if k not in HIDDEN_KEYS}

        cherrypy.response.headers['Content-Type'] = 'application/json'
        if errors:
            return json.dumps({"valid": False, "errors": errors,
                               "candidate": safe_candidate}).encode('utf-8')
        return json.dumps({"valid": True,
                           "candidate": safe_candidate}).encode('utf-8')

    def OPTIONS(self, **params):
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800
