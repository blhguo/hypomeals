FROM postgres:11

ADD vcm-4081.vm.duke.edu.pem /var/lib/postgresql/certs/server.crt
ADD vcm-4081.vm.duke.edu.key /var/lib/postgresql/certs/server.key

RUN chown -R postgres /var/lib/postgresql/certs
RUN chmod 400 /var/lib/postgresql/certs/server.key
RUN chmod 644 /var/lib/postgresql/certs/server.crt

CMD ["postgres", "-c", "ssl=on", "-c", "ssl_cert_file=/var/lib/postgresql/certs/server.crt", "-c", "ssl_key_file=/var/lib/postgresql/certs/server.key"]
