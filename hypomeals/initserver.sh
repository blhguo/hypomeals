#!/bin/bash

function init {
    python3 manage.py makemigrations --no-input
    if [ "$?" != "0" ]; then
        return 1
    fi
    python3 manage.py migrate --no-input
    if [ "$?" != "0" ]; then
        return 1
    fi
    python3 manage.py shell < init_script.py
    if [ "$?" != "0" ]; then
        return 1
    fi
    python3 manage.py collectstatic --no-input
    return "$?"
}

res="1"
while [ "$res" != "0" ]
do
    sleep 3;
    init;
    res="$?"
done
