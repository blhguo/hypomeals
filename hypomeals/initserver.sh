#!/bin/bash 
python3 manage.py makemigrations
python3 manage.py migrate
res="$?"
while [ "$res" != "0" ]
do
    sleep 3;
    python3 manage.py migrate
    python3 manage.py shell < init_script.py
    res="$?"
done
