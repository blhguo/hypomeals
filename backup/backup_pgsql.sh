#!/bin/bash

if [[ -z "$DB_HOSTNAME" ]]; then
    HOSTNAME="db"
else
    HOSTNAME="$DB_HOSTNAME"
fi

if [[ -z "$DB_PORT" ]]; then
    PORT="22"
else
    PORT="$DB_PORT"
fi

function send_email {
    if [[ -e "/credentials.json" ]]; then
       echo "Found credentials"
       API_KEY=$(cat /credentials.json | jq -r .email.api_key)
       if [[ -z $API_KEY ]]; then
           echo "No API key was found. Aborting."
           return 1
       else
           echo "Found API key: *********"
       fi
       curl -s --user "api:$API_KEY" https://api.mailgun.net/v3/mail.mortonmo.com/messages -F from="Morton Mo <ym84@duke.edu>" -F to="moyehan@gmail.com" -F subject="$1" -F text="$2"
       return 0
    fi
    echo "Credentials not found. Aborting."
    return 1
}

echo "Backup up database $HOSTNAME:$PORT"
start=$SECONDS
ssh -i /backup.key "root@$HOSTNAME" -p "$PORT" -o StrictHostKeyChecking=no -C pg_dumpall -U postgres > ./backup.sql

if [[ $? -ne 0 ]]; then
    echo "Backup failed... Sending email"
    send_email "HypoMeals Backup Failed" "Backup failed at $(date). Please check ASAP."
    exit 1
fi

chmod 400 ./backup.sql
end=$SECONDS
echo "Backup completed in $((end - start)) seconds"
send_email "HypoMeals Backup Succeeded" "Backup succeeded at $(date)."
