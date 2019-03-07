from typing import Dict

from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from django.conf import settings
from requests import HTTPError, Timeout

from HypoMeals.celery import app
from meals.sales import SalesException, query_sku_sales

logger = get_task_logger(__name__)


@app.task(
    rate_limit="5/s",
    autoretry_for=(ConnectionError, HTTPError, Timeout, SalesException),
    retry_kwargs={"max_retries": settings.SALES_REQUEST_MAX_RETRIES},
    retry_backoff=True,
)
def get_sku_sales_for_year(sku_number: int, year: int) -> int:
    logger.info("Getting sales data for SKU #%d year %d", sku_number, year)
    result = query_sku_sales(sku_number, year, logger)
    logger.info("Saved %d results for SKU %d year %d", result, sku_number, year)
    return result


def get_sku_sales(sku_number: int) -> Dict[int, AsyncResult]:
    """
    Schedules to retrieve all sales record from the sales system, in a sequential
    manner, for the years 1999 to 2019. Note that due to requirements, this cannot
    be parallelized.

    Note: if Sales data already exists for a SKU and a particular year, they will be
    deleted.
    :param sku_number: the sku to retrieve sales records
    :return: a dict mapping from year number an `AsyncResult` instance which, upon a
        `.get()` call, returns the number of records retrieved.
    """
    results: Dict[int, AsyncResult] = {}

    for year in range(1999, 2020):
        result = get_sku_sales_for_year.apply_async(
            (sku_number, year), countdown=settings.SALES_TIMEOUT
        )
        results[year] = result

    return results
