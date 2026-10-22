# The core's processes, for hosts that read a Procfile (Cabotage among
# them): the release step, then the minimum formation of web plus one
# worker that serves every queue with the scheduler embedded. The two
# optional processes below are for larger instances. Heroku reads
# heroku.yml instead; the two must agree, and a test checks they do.
release: python manage.py createcachetable && python manage.py migrate
web: gunicorn -c config/gunicorn.conf.py portal.wsgi:application --log-file -
worker: sh bin/worker
worker-media: celery -A portal worker -Q media --concurrency 1 --loglevel=info
worker-beat: celery -A portal beat --loglevel=info
