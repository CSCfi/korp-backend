
"""
korpplugins.logger

Simple logging plugin for the Korp backend

The plugin contains functions for the plugin mount points in korp.py. The
plugin uses Python's standard logging module.

Configuration variables for the plugin are specified in
korpplugins.logger.config.

Note that the plugin currently handles concurrent logging from multiple worker
processes (such as when running the Korp backend with Gunicorn) only by writing
their log entries to separate files, so the configuration variable
LOG_FILENAME_FORMAT should contain a placeholder for the process id ({pid}).
The separate files can be concatenated later manually.
"""


import logging
import os
import os.path
import time

import korpplugins
from . import config as pluginconf


class LevelLoggerAdapter(logging.LoggerAdapter):

    """
    A LoggerAdapter subclass with its own log level

    This class keeps its own log level, so different LevelLoggerAdapters
    for the same Logger may have different log levels. (In contrast,
    LoggerAdapter.setlevel delegates to Logger.setLevel, so calling it
    sets the level for all LoggerAdapters of the Logger instance, which
    is not desired here.)
    """

    def __init__(self, logger, extra, level=None):
        super().__init__(logger, extra)
        self._level = logger.getEffectiveLevel() if level is None else level

    def setLevel(self, level):
        self._level = level

    def getEffectiveLevel(self):
        return self._level

    def log(self, level, msg, *args, **kwargs):
        # LoggerAdapter.log calls logger.log, which re-checks isEnabledFor
        # based on the info in logger, so we need to redefine it to use
        # self._level here. The following is a combination of Logger.log and
        # LoggerAdapter.log, but calling self.isEnabledFor (of LoggerAdapter),
        # which in turn calls self.getEffectiveLevel (of this class).
        if not isinstance(level, int):
            if logging.raiseExceptions:
                raise TypeError("level must be an integer")
            else:
                return
        if self.isEnabledFor(level):
            msg, kwargs = self.process(msg, kwargs)
            self._log(level, msg, args, **kwargs)


class KorpLogger(korpplugins.KorpFunctionPlugin):

    """Class containing plugin functions for various mount points"""

    # The class attribute _loggers contains loggers (actually,
    # LevelLogAdapters) for all the requests being handled by the current
    # process. Different LevelLogAdapters are needed so that the request id can
    # be recorded in the log messages, tying the different log messages for a
    # request, and so that the log level can be adjusted if the request
    # contains "debug=true".
    _loggers = dict()

    def __init__(self):
        """Initialize logging; called only once per process"""
        super().__init__()
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(pluginconf.LOG_LEVEL)
        tm = time.localtime()
        logfile = (os.path.join(pluginconf.LOG_BASEDIR,
                                pluginconf.LOG_FILENAME_FORMAT)
                   .format(year=tm.tm_year, mon=tm.tm_mon, mday=tm.tm_mday,
                           hour=tm.tm_hour, min=tm.tm_min, sec=tm.tm_sec,
                           pid=os.getpid()))
        logdir = os.path.split(logfile)[0]
        os.makedirs(logdir, exist_ok=True)
        handler = logging.FileHandler(logfile)
        handler.setFormatter(logging.Formatter(pluginconf.LOG_FORMAT))
        self._logger.addHandler(handler)

    # Helper methods

    def _init_logging(self, request, args):
        """Initialize logging; called once per request (in enter_handler)"""
        request_id = KorpLogger._get_request_id(request)
        loglevel = (logging.DEBUG if (pluginconf.LOG_ENABLE_DEBUG_PARAM
                                      and "debug" in args)
                    else pluginconf.LOG_LEVEL)
        logger = LevelLoggerAdapter(
            self._logger, {"request": request_id}, loglevel)
        self._loggers[request_id] = logger
        return logger

    def _log(self, log_fn, category, item, value):
        """Log item in category with value using function log_fn

        Do not log if pluginconf.LOG_CATEGORIES is not None and it
        does not contain category, or if pluginconf.LOG_EXCLUDE_ITEMS
        contains item.
        """
        # TODO: Make the log message format configurable
        if (KorpLogger._log_category(category)
                and item not in pluginconf.LOG_EXCLUDE_ITEMS):
            log_fn(item + ": %s", value)

    @staticmethod
    def _get_request_id(request):
        """Return request id (actual request object, not proxy)"""
        return id(request)

    @staticmethod
    def _get_logger(request):
        """Return the logger for request (actual request object, not proxy)"""
        return KorpLogger._loggers[KorpLogger._get_request_id(request)]

    @staticmethod
    def _log_category(category):
        """Return True if logging category"""
        return (pluginconf.LOG_CATEGORIES is None
                or category in pluginconf.LOG_CATEGORIES)

    # Actual plugin methods (functions)

    def enter_handler(self, args, starttime, request):
        """Initialize logging at entering Korp and log basic information"""
        logger = self._init_logging(request, args)
        env = request.environ
        self._log(logger.info, "userinfo", "IP", request.remote_addr)
        self._log(logger.info, "userinfo", "User-agent", request.user_agent)
        self._log(logger.info, "referrer", "Referrer", request.referrer)
        # request.script_root is empty; how to get the name of the
        # script? Or is it at all relevant here?
        # self._log(logger.info, "params", "Script", request.script_root)
        self._log(logger.info, "params", "Loginfo", args.get("loginfo", ""))
        cmd = request.path.strip("/")
        if not cmd:
            cmd = "info"
        # Would it be better to call this "Endpoint"?
        self._log(logger.info, "params", "Command", cmd)
        self._log(logger.info, "params", "Params", args)
        # Log user information (Shibboleth authentication only). How could we
        # make this depend on using a Shibboleth plugin?
        if KorpLogger._log_category("auth"):
            remote_user = request.remote_user
            if remote_user:
                auth_domain = remote_user.partition("@")[2]
                auth_user = md5.new(remote_user).hexdigest()
            else:
                auth_domain = auth_user = None
            self._log(logger.info, "auth", "Auth-domain", auth_domain)
            self._log(logger.info, "auth", "Auth-user", auth_user)
        self._log(logger.debug, "env", "Env", env)
        # self._log(logger.debug, "env", "App",
        #           repr(korpplugins.app_globals.app.__dict__))

    def exit_handler(self, endtime, elapsed_time, request):
        """Log information at exiting Korp"""
        logger = KorpLogger._get_logger(request)
        self._log(logger.info, "load", "CPU-load",
                  " ".join(str(val) for val in os.getloadavg()))
        # FIXME: The CPU times probably make little sense, as the WSGI server
        # handles multiple requests in a single process
        self._log(logger.info, "times", "CPU-times",
                  " ".join(str(val) for val in os.times()[:4]))
        self._log(logger.info, "times", "Elapsed", elapsed_time)
        del self._loggers[KorpLogger._get_request_id(request)]

    def filter_result(self, result, request):
        """Debug log the result (request response)

        Note that the possible filter_result functions of plugins
        loaded before this one have been applied to the result.
        """
        # TODO: Truncate the value if too long
        logger = KorpLogger._get_logger(request)
        self._log(logger.debug, "debug", "Result", result)

    def filter_cqp_input(self, cqp, request):
        """Debug log CQP input cqp"""
        logger = KorpLogger._get_logger(request)
        self._log(logger.debug, "debug", "CQP", cqp)

    def filter_sql(self, sql, request):
        """Debug log SQL statements sql"""
        logger = KorpLogger._get_logger(request)
        self._log(logger.debug, "debug", "SQL", sql)

    def log(self, levelname, category, item, value, request):
        """Log with the given level, category, item and value

        levelname should be one of "debug", "info", "warning", "error"
        and "critical", corresponding to the methods in
        logging.Logger.

        This general logging method can be called from other plugins
        via korpplugins.KorpFunctionPlugin.call("log", ...) whenever
        they wish to log something.
        """
        logger = KorpLogger._get_logger(request)
        self._log(getattr(logger, levelname, logger.info),
                  category, item, value)
