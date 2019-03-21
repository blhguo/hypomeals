FROM postgres:11

RUN apt-get update && apt-get install -y -qq rsnapshot
ADD rsnapshot.conf /etc/rsnapshot.conf

ADD backup_pgsql.sh /backup_pgsql.sh
RUN chmod +x /backup_pgsql.sh

ENTRYPOINT ["rsnapshot" "alpha"]