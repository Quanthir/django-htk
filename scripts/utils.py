# Python Standard Library Imports
import datetime
import inspect
import logging
import time
import traceback
import sys

# Third Party (PyPI) Imports
import MySQLdb
import rollbar

# HTK Imports
from htk.constants.time import *
from htk.utils.db import (
    attempt_mysql_reconnect,
    close_connection,
    ensure_mysql_connection_usable,
)


# isort: off


def job_runner(f):
    """Accepts any callable function and runs it

    Catches any exceptions and logs to Rollbar
    """
    result = None
    try:
        ensure_mysql_connection_usable()
        result = f()
    except MySQLdb.OperationalError as e:
        extra_data = {
            'caught_exception': True,
            'attempt_reconnect': True,
        }
        rollbar.report_exc_info(extra_data=extra_data)
        attempt_mysql_reconnect()
    except Exception:
        rollbar.report_exc_info()
        slog(traceback.format_exc(), level='error')
    finally:
        close_connection()
    return result


def background_script_wrapper(
    workhorse=lambda: None,
    completion_message='Workhorse iteration completed.',
    daemon_mode=True,
    sleep_duration_seconds=TIMEOUT_1_HOUR,
):
    from django.conf import settings

    while True:
        job_runner(workhorse)

        if settings.TEST:
            # just make sure that it runs
            break

        if not daemon_mode:
            # just run once, don't keep looping
            break

        slog('DONE. %s Sleeping...' % completion_message)
        time.sleep(sleep_duration_seconds)


def slog(m, level='info'):
    logger = logging.getLogger(__name__)
    logger_fns = {
        'debug': logger.debug,
        'info': logger.info,
        'warning': logger.warn,
        'error': logger.error,
        'critical': logger.critical,
    }
    logger_fn = logger_fns.get(level, logger.info)

    previous_call = inspect.stack()[1]
    previous_fn = previous_call[0].f_code.co_name
    previous_file = previous_call[1]
    extra = {
        'file': previous_file,
        'func': previous_fn,
    }
    logger_fn(m, extra=extra)


def progress_bar(current_count, total_count):
    completed = int(round((float(current_count) / float(total_count)) * 100))
    remaining = 100 - completed
    ending = "\n" if total_count == current_count else "\r"
    print(
        'Progress: {} of {} ({}%) [{}{}]'.format(
            current_count,
            total_count,
            completed,
            '#' * completed,
            '-' * remaining,
        ),
        end=ending,
    )
    sys.stdout.flush()