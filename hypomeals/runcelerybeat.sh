#!/usr/bin/env bash

echo "Starting celery scheduler"

rm -f /code/celerybeat.pid
celery -A HypoMeals beat -l info -f /code/logs/celery.log --scheduler django_celery_beat.schedulers:DatabaseScheduler