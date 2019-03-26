FROM postgres:11

RUN mkdir -p /var/lib/postgresql/certs
RUN chown -R postgres /var/lib/postgresql/certs

# Backups
RUN apt-get update && apt-get install -y -qq openssh-server

COPY run-sshd.sh /run-sshd.sh
RUN chmod +x /run-sshd.sh

# SSH and Rsync for backup
RUN mkdir -p /var/run/sshd
ADD authorized_keys /root/.ssh/authorized_keys

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENTRYPOINT ["/run-sshd.sh"]

CMD ["postgres", "-c", "ssl=on", "-c", "ssl_cert_file=/var/lib/postgresql/certs/server.crt", "-c", "ssl_key_file=/var/lib/postgresql/certs/server.key"]
