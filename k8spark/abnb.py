import logging
import re
import time
from functools import lru_cache
from os.path import exists
from typing import List, Dict
import matplotlib.pyplot as plt  # Data visualisation libraries
import pandas as pd
import pyspark
import pyspark.sql.functions as F
import wget
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import RFormula
from pyspark.ml.regression import LinearRegression, GeneralizedLinearRegression, DecisionTreeRegressor
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator, CrossValidatorModel
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import regexp_extract
from k8spark.spark_utils import get_spark
from k8spark import logger

__name__ = "abnb"
__await_keyboard__ = True
__plot_graphs__ = True

# Increase if you have very large dataset and you have sufficient cluster memory for more exectuors.
dataset_partitions = 30

# http://insideairbnb.com/get-the-data.html
data_url = "https://data.insideairbnb.com/united-states/ca/san-francisco/2024-09-04/data/listings.csv.gz"
data_file = "listings.csv.gz"


def main():
    logger.info("Start of airbnb")
    single_pipeline_multiple_regressions()
    logger.info("End of airbnb")
    if __await_keyboard__:
        logger.info("Keeping program alive. You'll need to kill the process/pod.")
        await_keyboard()

def await_keyboard():
    while True:
        time.sleep(1)

def single_pipeline_multiple_regressions(params: Dict = None, folds=2, metric='r2', limit=None):
    """
    :param params: Regression parameters (for all regression types) unless customized
    :param folds: Folds for CrossValidator
    :param metric: Metric for CrossValidator
    :param limit: If not None, then limit of data set (for testing)
    :return: best model
    """
    logger.debug("Reading data")
    df = create_dataset()
    train_data, test_data = df.randomSplit([0.7, 0.3], 24)  # proportions [], seed for random
    # Regression formula
    rformula = create_rformula(df)
    # Pipeline basic to be shared across model fitting and testing
    pipeline = Pipeline(stages=[])  # Must initialize with empty list!
    # base pipeline (the processing here should be reused across pipelines)
    basePipeline = [rformula]
    # list of individual parameter grids
    final_param_grid = []
    # Add each model with their parameters using helper function
    regressions = [LinearRegression, GeneralizedLinearRegression, DecisionTreeRegressor]
    # regressions = [LinearRegression]  # Use one model for testing
    if params:
        regression_params = [params] * len(regressions)
    else:
        # Custom params here, in same sequence as models: https://spark.apache.org/docs/3.1.1/api/python/reference/pyspark.ml.html
        regression_params = [{'elasticNetParam': [0.5, 1.0]}, {'regParam': [0.5, 1.0]}, {'minInfoGain': [0.01, 0.3]}]
        # regression_params = [{}, {}, {}]  # Use empty params for testing
    for regression_type, params in zip(regressions, regression_params):
        logger.info(f"Creating sub-pipeline {regression_type} with params {params}")
        regression, param_grid = create_regression(regression_type, params)
        # Set the stages for the above (single) Pipeline object (in variable pipeline)
        # pipeline.stages are a parameter to the parameter grid (https://bryancutler.github.io/cv-pipelines/)
        param_grid.baseOn({pipeline.stages: basePipeline + [regression]})
        final_param_grid += param_grid.build()
    cv = CrossValidator() \
        .setEstimator(pipeline) \
        .setEvaluator(RegressionEvaluator().setMetricName(metric)) \
        .setEstimatorParamMaps(final_param_grid) \
        .setNumFolds(folds)
    logger.info("Fitting all parameteirzed models to data (which takes some time).")
    if limit:
        cv_models = cv.fit(train_data.limit(limit))
    else:
        cv_models = cv.fit(train_data)
    logger.info(f"Models metrics are: {cv_models.avgMetrics}")
    logger.debug(f"Best model: {cv_models.bestModel}")
    best_model = cv_models.bestModel
    # Odd error: java.util.NoSuchElementException: Failed to find a default value for link
    try:
        logger.info(f"Best pipeline stages are: {cv_models.bestModel.stages}")
    except:
        pass
    if limit:
        model_summary(best_model, test_data.limit(limit))
    else:
        model_summary(best_model, test_data)
    metrics, model_names = model_metrics(cv_models, final_param_grid)
    logger.info(f"Models, from worst to best: {model_names}")
    logger.info(f"Model metrics: {metrics}")
    if __plot_graphs__:
        logger.info("Plotting all models")
        plot_models(cv_models, final_param_grid, metric)
    return best_model


# From chapter 12 of Rioux
def sanitize_column_name(name):
    """Drops unwanted characters from the column name.
    We replace spaces, dashes and slashes with underscore,
    and only keep alphanumeric characters."""
    answer = name
    for i, j in ((" ", "_"), ("-", "_"), ("/", "_"), ("&", "and")):
        answer = answer.replace(i, j)
    return "".join(
        [
            char
            for char in answer
            if char.isalpha() or char.isdigit() or char == "_"
        ]
    )


def create_dataset(url=data_url, file=data_file):
    """
    Prepare the given data for analysis.
    :return: one `DataFrame` with all the data.
    """
    if not exists(file):
        wget.download(url)
    # Note that spark.read.csv can read .gz (compressed) files.
    # Pandas can also read .gz (compressed) files.
    # pandas is a better csv reader than spark and this is a small dataset
    pdf = pd.read_csv('listings.csv.gz', converters={i: str for i in range(100)})
    logger.info(f"Read data: {pdf.shape}.")
    # From pandas to DataFrame
    spark = get_spark(name="air_bnb")
    spark.sparkContext.setLogLevel("WARN")
    df = spark.createDataFrame(pdf)
    # Use Rioux function to clean names
    df = df.toDF(*[sanitize_column_name(name) for name in df.columns])
    # Cast columns for their type
    # Get just number for price and percentages
    df = df.withColumn('price', regexp_extract(F.col('price'), '\$?(\d*\.?\d*)', 1))
    df = df.withColumn('host_response_rate', regexp_extract(F.col('host_response_rate'), '(\d*\.?\d*)%', 1))
    df = df.withColumn('host_acceptance_rate', regexp_extract(F.col('host_acceptance_rate'), '(\d*\.?\d*)%', 1))
    df = df.withColumn('bathrooms_text', regexp_extract(F.col('bathrooms_text'), '(\d*\.?\d*) .*', 1))
    # Now cast (all numbers as double, even integers)
    # WARNING: Various errors can occur because of null values or empty string values.
    number_columns = ['bathrooms_text',
                      'host_id', 'host_response_rate', 'host_acceptance_rate',
                      'host_listings_count', 'host_total_listings_count',
                      'accommodates', 'bathrooms', 'bedrooms',
                      'beds', 'price', 'minimum_nights', 'maximum_nights', 'minimum_minimum_nights',
                      'maximum_minimum_nights',
                      'minimum_maximum_nights', 'maximum_maximum_nights', 'minimum_nights_avg_ntm',
                      'maximum_nights_avg_ntm',
                      'has_availability', 'availability_30', 'availability_60', 'availability_90', 'availability_365',
                      'number_of_reviews',
                      'number_of_reviews_ltm', 'number_of_reviews_l30d',
                      'review_scores_rating',
                      'review_scores_accuracy', 'review_scores_cleanliness', 'review_scores_checkin',
                      'review_scores_communication',
                      'review_scores_location', 'review_scores_value', 'instant_bookable',
                      'calculated_host_listings_count',
                      'calculated_host_listings_count_entire_homes', 'calculated_host_listings_count_private_rooms',
                      'calculated_host_listings_count_shared_rooms', 'reviews_per_month'
                      ]
    for column in number_columns:
        df = df.withColumn(column, df[column].cast('double'))
    # select columns for regression
    # WARNING: boolean columns cause OutOfMemoryError (for unknown reason)
    df = df.select('price', 'accommodates', 'bedrooms', 'number_of_reviews',
                   'reviews_per_month', 'review_scores_rating', 'number_of_reviews_l30d', 'number_of_reviews_ltm',
                   'beds', 'availability_30', 'availability_60', 'availability_90', 'availability_365',
                   'bathrooms_text', 'minimum_nights', 'maximum_nights')
    # clean data (a bit)
    df = df.where('price > 0 AND price<900000000 AND bedrooms > 0')
    df = df.dropna()
    df = df.repartition(dataset_partitions)
    logger.debug("Data partitions ={}".format(df.rdd.getNumPartitions()))
    return df


def create_rformula(df: DataFrame, formula: str = None) -> RFormula:
    """
    :param df: `DataFrame` used to created formula, if none provided
    :param formula: RFormula (optional)
    :return: RFormula object.
    """
    logger.debug(f"Analysis columns: {df.columns}")
    if not formula:
        columns = df.columns
        # Not using Price (label) or address in features
        columns.remove('price')
        formula = "{} ~ {}".format("price", " + ".join(columns))
    logger.info("Formula : {}".format(formula))
    rformula = RFormula(formula=formula)
    return rformula


def create_regression(regression_type: pyspark.ml.regression, params: Dict) -> List:
    """
    Convenience function to create a regression object and associated ParamGrid.
    :param regression_type: A pyspark regression type.
    :param params: Parameters for the regression in dictionary format. For example, {'regParam': [0.0, 0.5, 1.0]}
    :return: the regression object and its associated ParamGrid
    """
    # Regression object of the type provided
    r = regression_type()

    # Add the parameters to the ParamGridBuilder
    # Uses a dictionary to do something like this:
    # paramGrid = ParamGridBuilder() \
    #     .addGrid(r.regParam, [0.5, 1.0]) \
    #     .build()
    paramGrid = ParamGridBuilder()
    if params:
        for k, v in params.items():
            param = [p for p in r.params if p.name == k]
            if param:
                paramGrid.addGrid(param[0], v)
            else:
                logger.warning("Unknown parameter {} for {}.".format(k, regression_type))
    return r, paramGrid


def model_summary(pipeline_model: PipelineModel, test_df: DataFrame):
    # Regression is last model in pipeline
    lrm = pipeline_model.stages[-1]
    try:
        logger.info("coefficients: {}".format(lrm.coefficients))
        logger.info("intercept: {}".format(lrm.intercept))
    except Exception as e:
        logger.warning("Model {} does not provide coefficients.".format(model_name(lrm)))
    # Graph predictions vs actual
    lm_fitted = pipeline_model.transform(test_df)
    labeledPredictions = lm_fitted.select("label", "prediction")
    # Here, get pairs where there is both a label and prediction
    # collect gets the data from the data grid and places the results in a list (label, prediction)
    # zip(* ) converts the tuple list into two lists
    y_test, predictions = zip(*labeledPredictions.collect())
    if __plot_graphs__:
        plt.xlabel('actuals')
        plt.ylabel('predictions')
        plt.title("{} actual vs predicted".format(model_name(lrm)))
        plt.scatter(y_test, predictions)
        plt.savefig("model_summary.png")
        # plt.show()

def model_name(model):
    return model.uid.split('_')[0]


def paramGrid_model_name(model):
    params = [v for v in model.values() if type(v) is not list]
    name = [v[-1] for v in model.values() if type(v) is list][0]
    name = re.match(r'([a-zA-Z]*)', str(name)).groups()[0]
    return "{}{}".format(name, params)


def model_metrics(cv_models: CrossValidatorModel, paramGrid: List):
    # Resulting metric and model description
    # get the measure from the CrossValidator, cvModel.avgMetrics
    # get the model name & params from the paramGrid
    # put them together here:
    measures = zip(cv_models.avgMetrics, [paramGrid_model_name(m) for m in paramGrid])
    metrics, model_names = zip(*measures)
    return metrics, model_names


def plot_models(cv_models: CrossValidatorModel, paramGrid: List, metric='r2'):
    metrics, model_names = model_metrics(cv_models, paramGrid)
    # Plot the model metrics
    plt.clf()  # clear figure
    fig = plt.figure(figsize=(5, 5))
    plt.style.use('fivethirtyeight')
    axis = fig.add_axes([0.1, 0.3, 0.8, 0.6])
    plt.bar(range(len(model_names)), metrics)
    # plot the model name & param as X labels
    plt.xticks(range(len(model_names)), model_names, rotation=70, fontsize=6)
    plt.yticks(fontsize=8)
    plt.ylabel(f"{metric}", fontsize=8)
    plt.title('Model evaluations')
    plt.savefig("model_plots.png")
    # plt.show()


# Methods to check for various emtpy values
def emply_column_count(df):
    df.select([F.count(F.when(F.isnan(c) | F.col(c).isNull() | F.col(c) == "", c)).alias(c) for c in df.columns])


def nan_column_count(df):
    df.select([F.count(F.when(F.isnan(df[c]), c)).alias(c) for c in df.columns]).show()


def null_column_count(df):
    df.select([F.count(F.when(df[c].isNull(), c)).alias(c) for c in df.columns]).show()


# When done, exec into pod to see results
# kubectl exec -it pods/abnb-driver -- bash
# Copy results out with:
# kubectl cp abnb-driver:model_plots.png model_plots.png
# kubectl cp abnb-driver:model_summary.png model_summary.png
# Run main program when file loaded into Python
# main()
