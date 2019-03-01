import csv
from collections import defaultdict
from datetime import datetime, time

from django.template.loader import render_to_string
from django_extensions.management.jobs import DailyJob
from django.core.mail import send_mail
from django.conf import settings


EMAILS = {
    # "Brandon": "brandon.guo@duke.edu",
    # "Xingyu": "xc77@duke.edu",
    "Morton": "ym84@duke.edu",
}


class LineIterator:
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


class Job(DailyJob):
    help = "Sends a reminder on pending tasks every day."

    def _get_values(self):
        self.file = settings.GOOGLE_SHEETS_CLIENT.open(
            settings.GOOGLE_SHEET_SPREADSHEET_NAME
        ).sheet1
        return LineIterator(self.file.get_all_values())

    def execute(self):
        reader = self._get_values()
        assigned_to = defaultdict(list)
        for row in reader:
            if row["#"]:
                row["Deadline"] = datetime.strptime(row["Deadline"], "%m/%d/%Y")
                row["Deadline"] = datetime.combine(row["Deadline"], time(17, 0))
                assigned_to[row["Assigned to"]].append(row)

        for person, email in EMAILS.items():
            email_html = render_to_string(
                template_name="meals/email/task_reminder.html",
                context={
                    "name": person,
                    "spreadsheet_id": self.file.spreadsheet.id,
                    "u4g_tasks": assigned_to["U4G"],
                    "assigned_to": assigned_to[person],
                },
            )
            send_mail(
                "ECE458 Project Task Reminder",
                message="Please view HTML message",
                from_email="ym84@duke.edu",
                recipient_list=[email],
                fail_silently=False,
                html_message=email_html,
            )
