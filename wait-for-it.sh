#!/bin/bash
set -e

host="$1"
shift
cmd="$@"

>&2 echo "Waiting for postgres..."
>&2 echo "Host: $host"
>&2 echo "Postgres User: $POSTGRES_USER"
>&2 echo "Postgres Password: $POSTGRES_PASSWORD"
>&2 echo "Postgres DB: $POSTGRES_DB"

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 2
done

>&2 echo "Postgres is up - executing command"
exec $cmd
