# pylint: disable-msg=protected-access

import csv
import logging
import time
from collections import defaultdict

from cachetools import TTLCache
from django.core.exceptions import ValidationError
from django.db import transaction

from meals import utils
from meals.exceptions import (
    CollisionOccurredException,
)
from meals.importers import IMPORTERS
from .models import Sku, FormulaIngredient, ProductLine, Ingredient

logger = logging.getLogger(__name__)


FILE_TYPES = {
    "skus": Sku,
    "ingredients": Ingredient,
    "product_lines": ProductLine,
    "formulas": FormulaIngredient,
}
MODEL_TO_FILE_TYPES = {v: k for k, v in FILE_TYPES.items()}
HEADERS = {
    "skus": "SKU#,Name,Case UPC,Unit UPC,Unit size,"
    "Count per case,Product Line Name,Comment",
    "ingredients": "Ingr#,Name,Vendor Info,Size,Cost,Comment",
    "product_lines": "Name",
    "formulas": "SKU#,Ingr#,Quantity",
}
TOPOLOGICAL_ORDER = ["product_lines", "ingredients", "skus", "formulas"]
# A self expiring cache for 30 minutes
TRANSACTION_CACHE = TTLCache(maxsize=10, ttl=1800)


def _get_reader(stream, file_type):
    header_format = HEADERS[file_type]
    lines = stream.read().decode("UTF-8").splitlines()
    if lines[0] == header_format:
        return csv.DictReader(lines)
    logger.error(f"File {stream.name} of type {file_type} does not have a valid header")
    raise RuntimeError("Header format mismatch")


@transaction.atomic
@utils.log_exceptions(logger=logger)
def process_csv_files(files, session_key):
    inserted = defaultdict(lambda: 0)
    for file_type in TOPOLOGICAL_ORDER:
        if file_type in files:
            stream = files[file_type]
            if not stream:
                continue
            importer = IMPORTERS[file_type]()
            logger.info("Processing %s: %s", file_type, stream)
            try:
                reader = _get_reader(stream, file_type)
            except Exception:
                raise ValidationError(
                    "Cannot parse file %(filename)s.", params={"filename": stream.name}
                )
            instances, collisions = importer.do_import(reader, filename=stream.name)
            inserted[file_type] = len(instances)
            if collisions:
                if session_key not in TRANSACTION_CACHE:
                    TRANSACTION_CACHE[session_key] = {}
                TRANSACTION_CACHE[session_key][stream.name] = (instances, collisions)
                raise CollisionOccurredException

    return inserted


@transaction.atomic
def _force_save(tx):
    start = time.time()
    inserted = defaultdict(lambda: 0)
    updated = defaultdict(lambda: 0)
    for instances, collisions in tx.values():
        for instance in instances:
            instance.save()
            file_type = MODEL_TO_FILE_TYPES[instance._meta.model]
            inserted[file_type] += 1
        for collision in collisions:
            old, new = collision.old_record, collision.new_record
            old.delete()
            new.save()
            file_type = MODEL_TO_FILE_TYPES[old._meta.model]
            updated[file_type] += 1
    end = time.time()
    logger.info(
        "Inserted %d, updated %d records in %6.3f seconds",
        sum(inserted.values()),
        sum(updated.values()),
        end - start,
    )
    return inserted, updated


def force_save(session_key, force=False):
    result = {}, {}
    if session_key in TRANSACTION_CACHE:
        logger.info("Found ongoing transaction.")
        if force:
            logger.info("Loading from transaction cache. session_key=%s", session_key)
            cached_transaction = TRANSACTION_CACHE[session_key]
            logger.info("Successfully loaded transaction")
            result = _force_save(cached_transaction)
        del TRANSACTION_CACHE[session_key]
        logger.info("Deleted transaction with key=%s", session_key)
    return result


def has_ongoing_transaction(session_key):
    return session_key in TRANSACTION_CACHE


def get_transaction(session_key):
    return TRANSACTION_CACHE[session_key]


def clear_transaction(session_key):
    if session_key in TRANSACTION_CACHE:
        del TRANSACTION_CACHE[session_key]
