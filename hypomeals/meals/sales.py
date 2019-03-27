import operator
from decimal import Decimal
from logging import Logger
from typing import List, Sequence, Iterator, Dict

import requests
from django.conf import settings
from django.db import transaction
from lxml import etree
from lxml.html import Element

from meals.models import Customer, Sku, Sale


class SalesException(Exception):
    pass


class HtmlTableIterator:
    def __init__(self, table: Element, headers: Sequence[str] = None) -> None:
        self.current_row = 0
        self.rows = table.findall("tr")
        self.num_rows = len(self.rows)
        self.headers = []
        if headers:
            self.headers = headers
            return

        thead = table.find("thead")
        if thead is not None:
            first_row = thead[0]
        else:
            first_row = self.rows[0]
            self.rows = self.rows[1:]  # first row will be taken as header
            self.current_row = 0
            self.num_rows -= 1

        for td in first_row:
            header = td.text.strip()
            self.headers.append(header)

    def process_cell(self, cell):
        return cell.strip()

    def process_row(self, row):
        return map(
            self.process_cell, map(operator.attrgetter("text"), row.findall("td"))
        )

    def __next__(self) -> Dict[str, str]:
        if self.current_row >= self.num_rows:
            raise StopIteration
        row = self.process_row(self.rows[self.current_row])
        self.current_row += 1
        return dict(zip(self.headers, row))

    def __iter__(self) -> Iterator[Dict[str, str]]:
        return self


def query_sku_sales(sku_number: int, year: int, logger: Logger = None) -> int:
    """
    Queries the Hypothetical Meals legacy sales interface and caches results.
    :param sku_number: a SKU number to query
    :param year: the year to query. Must be in range [1999, 2019]
    :param logger: a logger to use. If None, nothing will be logged
    :return: number of sales records retrieved / saved
    """
    sku = Sku.objects.filter(pk=sku_number)
    if not sku.exists():
        # This really should not happen, but better safe than sorry
        raise SalesException("SKU number does not exist in database.")
    sku = sku[0]
    params = {"sku": sku_number, "year": year}
    url = settings.SALES_INTERFACE_URL
    connect_timeout = settings.SALES_REQUEST_CONNECT_TIMEOUT
    read_timeout = settings.SALES_REQUEST_READ_TIMEOUT
    resp = requests.get(url, params=params, timeout=(connect_timeout, read_timeout))
    resp.raise_for_status()

    if logger:
        logger.debug("Raw HTML: %s", resp.text)
    tree = etree.HTML(resp.text)
    table = tree.find("body/table")
    if table is None:
        raise SalesException("Unable to find a table in sales records.")
    sales_records: List[Sale] = []
    for row in HtmlTableIterator(table):
        customer = Customer.objects.get_or_create(
            id=int(row["cust#"]), defaults={"name": row["cust_name"]}
        )[0]
        year = int(row["year"])
        week = int(row["week"])
        sales = Decimal(row["sales"])
        price = Decimal(row["price/case"])
        sales_records.append(
            Sale(
                sku=sku,
                year=year,
                week=week,
                customer=customer,
                sales=sales,
                price=price,
            )
        )
    with transaction.atomic():
        Sale.objects.filter(sku=sku, year=year).delete()
        Sale.objects.bulk_create(sales_records)
    return len(sales_records)
