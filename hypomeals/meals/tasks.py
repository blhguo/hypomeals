import os
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, time

from celery.exceptions import Retry
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.template.defaultfilters import striptags
from django.template.loader import render_to_string
from django.utils import timezone
from requests import HTTPError, Timeout

from HypoMeals.celery import app

from meals import utils
from meals.models import Sku
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
    logger.info("Saved %d results for SKU #%d year %d", result, sku_number, year)
    return result


@app.task
def refresh_sales_for_current_year() -> int:
    now = timezone.now()
    num_processed = 0
    for number in Sku.objects.values_list("number", flat=True).distinct():
        logger.info("Refreshing sales for SKU #%d", number)
        get_sku_sales_for_year.apply_async(args=(number, now.year))
        num_processed += 1
    logger.info("Scheduled %d SKUs for refresh", num_processed)
    return num_processed


@app.task
def notify_backup_success(
    start_time: datetime, end_time: datetime, path: str, total_bytes: int
) -> None:
    logger.info("Backup succeeded at %s. Sending email...", end_time.isoformat())
    email_html = render_to_string(
        template_name="meals/email/backup_success.html",
        context={
            "start_time": start_time,
            "end_time": end_time,
            "path": path,
            "total_bytes": total_bytes,
        },
    )
    msg = EmailMultiAlternatives(
        "HypoMeals Backup Success",
        striptags(email_html),
        settings.EMAIL_FROM_ADDR,
        [settings.BACKUP_NOTIFY_EMAIL],
    )
    msg.attach_alternative(email_html, "text/html")
    msg.send()
    logger.info("Email sent successfully.")


@app.task
def backup_all() -> bool:
    start_time = timezone.now()
    filename = f"backup-{start_time.strftime(settings.BACKUP_DATETIME_FORMAT)}.sql"
    path = os.path.join(settings.BACKUP_STORAGE_DIR, filename)
    command = [
        "ssh",
        "-i",
        settings.BACKUP_SSH_KEY,
        f"root@{settings.DATABASES['default']['HOST']}",
        "-o",
        "StrictHostKeyChecking=no",
        "-C",
        "pg_dumpall",
        "-U",
        "postgres",
    ]
    temp = tempfile.mktemp()
    with open(temp, "w") as backup_file:
        logger.info("Executing command %s", command)
        logger.info("Storing backup in temporary file %s", temp)
        proc = subprocess.Popen(command, stdout=backup_file)
        logger.info("Launched backup process as PID %d", proc.pid)
        try:
            exit_code = proc.wait(timeout=settings.BACKUP_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise Retry(
                message="Timeout expired when waiting for backup to "
                "complete. Retrying..."
            )
        if exit_code != 0:
            raise Retry(
                message=f"Command failed with exit code {exit_code}. Retrying..."
            )
    total_bytes = 0
    with open(temp, "r") as local, default_storage.open(path, "w") as remote:
        chunked_reader = utils.chunked_read(local, chunk_size=5120)
        for data in chunked_reader:
            remote.write(data)
            total_bytes += len(data)
        remote.flush()

    end_time = timezone.now()
    logger.info(
        "Backup completed at %s. %d bytes transferred",
        end_time.isoformat(),
        total_bytes,
    )
    notify_backup_success.apply(args=(start_time, end_time, path, total_bytes))
    return True


class TableLineIterator:
    def __init__(self, lines):
        self.lines = lines
        self.headers = lines[0]
        self.index = 0

    def __next__(self):
        self.index += 1
        if self.index >= len(self.lines):
            raise StopIteration
        return dict(zip(self.headers, self.lines[self.index]))

    def __iter__(self):
        return self


@app.task
def send_task_reminder(person: str, email: str) -> None:
    file = settings.GOOGLE_SHEETS_CLIENT.open(
        settings.GOOGLE_SHEET_SPREADSHEET_NAME
    ).sheet1
    reader = TableLineIterator(file.get_all_values())
    assigned_to = defaultdict(list)
    for row in reader:
        if row["#"]:
            row["Deadline"] = datetime.strptime(row["Deadline"], "%m/%d/%Y")
            row["Deadline"] = datetime.combine(row["Deadline"], time(17, 0))
            if row["Completed?"] != "TRUE":
                assigned_to[row["Assigned to"]].append(row)

    if not assigned_to["U4G"] and not assigned_to[person]:
        logger.info("%s has completed all tasks and no U4G tasks. Skipping...", person)
        return
    logger.info("Sending email to %s <%s>", person, email)

    email_html = render_to_string(
        template_name="meals/email/task_reminder.html",
        context={
            "name": person,
            "spreadsheet_id": file.spreadsheet.id,
            "u4g_tasks": assigned_to["U4G"],
            "assigned_to": assigned_to[person],
        },
    )
    msg = EmailMultiAlternatives(
        "ECE458 Project Task Reminder",
        striptags(email_html),
        settings.EMAIL_FROM_ADDR,
        [email],
    )
    msg.attach_alternative(email_html, "text/html")
    msg.send()
    logger.info("Sent %d bytes", len(email_html))
