FROM debian:stretch

RUN apt-get update && apt-get install -y -qq rsnapshot jq curl cron
ADD rsnapshot.conf /etc/rsnapshot.conf

ADD backup_pgsql.sh /scripts/backup_pgsql.sh
ADD crontab /etc/cron.d/rsnapshot

RUN chmod +x /scripts/backup_pgsql.sh
RUN crontab /etc/cron.d/rsnapshot
RUN chmod 644 /etc/cron.d/rsnapshot
RUN touch /var/log/cron.log

ENTRYPOINT ["cron", "-f"]
