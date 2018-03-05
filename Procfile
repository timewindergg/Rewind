web: newrelic-admin run-program gunicorn rewind.wsgi --log-file -
worker: newrelic-admin run-program celery -A rewind worker -l warning --concurrency=4
