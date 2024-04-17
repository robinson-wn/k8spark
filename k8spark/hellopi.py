from operator import add
from random import random
from time import time

import numpy as np

from k8spark.spark_utils import get_spark
from k8spark import logger

__name__ = "hellopi"

MILLION = 1000000
n = MILLION * 100
partitions = 6
# 7 = 15.6s, 1 = 34s


def is_point_inside_unit_circle(_):
    x, y = random(), random()
    return 1 if x * x + y * y < 1 else 0


def calculate_pi():
    t_0 = time()
    # parallelize creates a spark Resilient Distributed Dataset (RDD)
    # its values are useless in this case
    # but allows us to distribute our calculation (inside function)
    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")
    count = spark.sparkContext.parallelize(range(0, n), partitions) \
        .map(is_point_inside_unit_circle).reduce(add)
    logger.info(f"{np.round(time() - t_0, 3)}, seconds elapsed for spark approach and n={n}")
    logger.info(f"Pi is roughly {(4.0 * count / n)}")


def main():
    logger.info("Hello World from PySpark")
    logger.info(f"Computing Pi with {n:,} points using {partitions} partitions")
    calculate_pi()
