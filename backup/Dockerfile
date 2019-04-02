FROM debian:stretch

RUN apt-get update && apt-get install -y -qq rsnapshot jq curl cron
ADD rsnapshot.conf /etc/rsnapshot.conf

ADD backup_pgsql.sh /scripts/backup_pgsql.sh
ADD crontab /etc/cron.d/rsnapshot
ADD conninfo.json /conninfo.json
ADD run_as_cron /scripts/run_as_cron
ADD cron_env /cron_env

RUN chmod +x /scripts/backup_pgsql.sh
RUN chmod +x /scripts/run_as_cron
RUN crontab /etc/cron.d/rsnapshot
RUN chmod 644 /etc/cron.d/rsnapshot
RUN touch /var/log/cron.log

ENTRYPOINT ["cron", "-f"]
