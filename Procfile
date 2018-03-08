web: newrelic-admin run-program bin/start-pgbouncer-stunnel gunicorn rewind.wsgi --log-file -
worker: newrelic-admin run-program celery -A rewind worker -l warning --concurrency=5 --max-memory-per-child=200 --max-tasks-per-child=1000
