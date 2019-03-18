from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
from requests import HTTPError, Timeout

from celery import shared_task
from meals.models import Sku
from meals.sales import SalesException, query_sku_sales

logger = get_task_logger(__name__)


@shared_task(
    rate_limit="5/s",
    autoretry_for=(ConnectionError, HTTPError, Timeout, SalesException),
    retry_kwargs={"max_retries": settings.SALES_REQUEST_MAX_RETRIES},
    retry_backoff=True,
)
def get_sku_sales_for_year(sku_number: int, year: int) -> int:
    logger.info("Getting sales data for SKU #%d year %d", sku_number, year)
    result = query_sku_sales(sku_number, year, logger)
    logger.info("Saved %d results for SKU #%d year %d", result, sku_number, year)
    return result


@shared_task
def refresh_sales_for_current_year() -> int:
    now = timezone.now()
    num_processed = 0
    for number in Sku.objects.values_list("number", flat=True).distinct():
        logger.info("Refreshing sales for SKU #%d", number)
        get_sku_sales_for_year.apply_async(args=(number, now.year))
        num_processed += 1
    logger.info("Scheduled %d SKUs for refresh", num_processed)
    return num_processed
