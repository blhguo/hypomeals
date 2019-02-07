#!/bin/bash
echo "Waiting for database system to be up"
sleep 5

while [ "1"=="1" ]
do
    gunicorn -b="0:8000" --forwarded-allow-ips="*" HypoMeals.wsgi
    sleep 1
done
