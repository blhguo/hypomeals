#!/usr/bin/env bash

echo "Starting celery"

celery -A HypoMeals worker -l info -f /code/logs/celery.log