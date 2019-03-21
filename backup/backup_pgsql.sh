#!/bin/bash

PASSWORD=Hyp0Mea1sR0cks! pg_dumpall -f ./backup.sql --dbname='host=192.168.16.3 port=5432 connect_timeout=10 user=postgres'
chmod 400 ./backsup.sql