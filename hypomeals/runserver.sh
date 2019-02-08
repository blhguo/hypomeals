#!/bin/bash
echo "Waiting for database system to be up"
sleep 3

while [ "1"=="1" ]
do
    gunicorn -b="0:8000" --workers=1 --forwarded-allow-ips="*" HypoMeals.wsgi
    sleep 1
done
