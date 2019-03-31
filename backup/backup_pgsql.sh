#!/bin/bash

if [[ -e "/conninfo.json" ]]; then
    # Read from conninfo.json if the file exists
    HOSTNAME=$(/bin/cat /conninfo.json | /usr/bin/jq -r .hostname)
    PORT=$(/bin/cat /conninfo.json | /usr/bin/jq -r .port)
else
    # Otherwise get hostname/port from environment variable
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
fi

function send_email {
    if [[ -e "/credentials.json" ]]; then
       /bin/echo "Found credentials"
       API_KEY=$(/bin/cat /credentials.json | /usr/bin/jq -r .email.api_key)
       if [[ -z $API_KEY ]]; then
           /bin/echo "No API key was found. Aborting."
           return 1
       fi
       /bin/echo "Found API key: *********"
       /usr/bin/curl -s --user "api:$API_KEY" https://api.mailgun.net/v3/mail.mortonmo.com/messages -F from="Morton Mo <ym84@duke.edu>" -F to="moyehan@gmail.com" -F subject="$1" -F text="$2"
       return 0
    fi
    /bin/echo "Credentials not found. Aborting."
    return 1
}

/bin/echo "Backup up database $HOSTNAME:$PORT"
start=$SECONDS
/usr/bin/ssh -i /backup.key "root@$HOSTNAME" -p "$PORT" -o StrictHostKeyChecking=no -C pg_dumpall -U postgres > ./backup.sql

if [[ $? -ne 0 ]]; then
    /bin/echo "Backup failed... Sending email"
    send_email "HypoMeals Backup Failed" "Backup failed at $(date). Please check ASAP."
    exit 1
fi

chmod 400 ./backup.sql
end=$SECONDS
/bin/echo "Backup completed in $((end - start)) seconds"
send_email "HypoMeals Backup Succeeded" "Backup succeeded at $(date)."
