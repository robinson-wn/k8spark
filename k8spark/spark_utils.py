import pyspark
from pyspark.sql import SparkSession
from functools import lru_cache
from k8spark import logger

__name__ = "k8spark"

@lru_cache(maxsize=None)
def get_spark(name=__name__) -> SparkSession:
    return SparkSession.builder.appName(name).getOrCreate()
