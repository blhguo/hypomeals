from collections import defaultdict
from datetime import datetime, time

from django.template.loader import render_to_string
from django_extensions.management.jobs import DailyJob
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.defaultfilters import striptags


EMAILS = {
    "Brandon": "idkwain@gmail.com",
    "Xingyu": "dukexingyuchen@gmail.com",
    "Morton": "moyehan@gmail.com",
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
            msg = EmailMultiAlternatives(
                "ECE458 Project Task Reminder",
                striptags(email_html),
                settings.EMAIL_FROM_ADDR,
                [email],
            )
            msg.attach_alternative(email_html, "text/html")
            msg.send()
