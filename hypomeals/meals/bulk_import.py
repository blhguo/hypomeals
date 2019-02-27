# pylint: disable-msg=protected-access

import csv
import logging
import time
from collections import defaultdict

from cachetools import TTLCache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.fields.related import RelatedField

from meals import utils
from meals.exceptions import CollisionOccurredException, UserFacingException
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
TOPOLOGICAL_ORDER = ["product_lines", "ingredients", "skus", "formulas"]
# A self expiring cache for 30 minutes
TRANSACTION_CACHE = TTLCache(maxsize=10, ttl=1800)


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
            lines = stream.read().decode("UTF-8").splitlines()
            instances, collisions = importer.do_import(lines, filename=stream.name)
            inserted[file_type] = len(instances)
            if collisions:
                if session_key not in TRANSACTION_CACHE:
                    TRANSACTION_CACHE[session_key] = {}
                TRANSACTION_CACHE[session_key][stream.name] = (instances, collisions)
                raise CollisionOccurredException

    return inserted


def _save_instance(instance):
    """
    Saves an instance with ForeignKey objects that are potentially not committed to
    DB.
    :param instance: an instance to save
    """
    for field in instance._meta.fields:
        if isinstance(field, RelatedField):
            fk = getattr(instance, field.name)
            fk.save()
            setattr(instance, field.name, fk)
            logger.info("Saved fk %s (#%d) %s", field.name, fk.pk, str(fk))
    instance.save()


@transaction.atomic
def _force_save(tx):
    start = time.time()
    inserted = defaultdict(lambda: 0)
    updated = defaultdict(lambda: 0)
    for instances, collisions in tx.values():
        for instance in instances:
            _save_instance(instance)
            file_type = MODEL_TO_FILE_TYPES[instance._meta.model]
            inserted[file_type] += 1
        for collision in collisions:
            old, new = collision.old_record, collision.new_record
            old.delete()
            _save_instance(new)
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
