web: newrelic-admin run-program bin/start-pgbouncer-stunnel gunicorn rewind.wsgi -k gevent --worker-connections 3000 --log-file -
worker: newrelic-admin run-program celery -A rewind worker -l warning --concurrency=5 --max-memory-per-child=200000 --max-tasks-per-child=1000
