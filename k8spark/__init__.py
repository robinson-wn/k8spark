import logging

__version__ = "0.1.0"
__name__ = "k8spark"

# https://www.toptal.com/python/in-depth-python-logging
logging.basicConfig(format='%(asctime)s %(levelname)s {}: %(message)s'.format(__name__),
                    datefmt='%y/%m/%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.getLogger('py4j.clientserver').setLevel(logging.WARN)