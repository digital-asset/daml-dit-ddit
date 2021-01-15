import logging
import time


def setup_default_logging(**overrides):
    logging.Formatter.converter = time.gmtime

    defaults = {
        'level': logging.INFO,
        'format': '%(asctime)s [%(levelname)s] (%(name)s) %(message)s',
        'datefmt': '%Y-%m-%dT%H:%M:%S%z'
    }

    config = {**defaults, **overrides}

    logging.basicConfig(**config)


LOG = logging.getLogger('ddit')

def is_verbose():
    return logging.root.level <= logging.DEBUG
