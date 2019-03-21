FROM postgres:11

ADD vcm-4081.vm.duke.edu.pem /var/lib/postgresql/certs/server.crt
ADD vcm-4081.vm.duke.edu.key /var/lib/postgresql/certs/server.key

RUN chown -R postgres /var/lib/postgresql/certs
RUN chmod 400 /var/lib/postgresql/certs/server.key
RUN chmod 644 /var/lib/postgresql/certs/server.crt

# Backups
RUN apt-get update && apt-get install -y -qq rsnapshot cron openssh-server
ADD rsnapshot.conf /etc/rsnapshot.conf

ADD backup_pgsql.sh /backup_pgsql.sh
RUN chmod +x /backup_pgsql.sh

# SSH and Rsync for backup
RUN mkdir -p /var/run/sshd
ADD authorized_keys /root/.ssh/authorized_keys

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd


CMD ["postgres", "-c", "ssl=on", "-c", "ssl_cert_file=/var/lib/postgresql/certs/server.crt", "-c", "ssl_key_file=/var/lib/postgresql/certs/server.key"]
