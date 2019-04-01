Timewinder Rewind

TODO:
- Include timeline stats in aggregations (Results in 2x API calls and processing time, check performance scalability)

Available on `https://timewinder-rewind.herokuapp.com/`

Setup:
1. Create a new conda virtual env with python3.6
2. `pip install -r requirements.txt`
3. `pip install git+https://github.com/meraki-analytics/cassiopeia.git`
	*install directly from git to get the latest changes. Cassiopeia doesnt often release to pip*
4. Write `export RIOT_API_KEY=<key>` to .bash_profile 

DB setup:
1. Install postgres 10 with `brew install postgresql`. Read postgres docs for instructions on how to start it up. You may(really) want to alias the commands for starting up and shutting down the psql server.
2. in postgres shell, 
```
	CREATE DATABASE timewinder;
```
3. Run `./manage.py migrate` to apply migrations

Redis celery setup:
1. `brew install redis`
2. Write the following to .bash_profile:
	- `export REDIS_URL="redis://localhost:6379/0"`
	- `export MAX_CONNECTIONS=20`
	- `export BROKER_POOL_LIMIT=10` 
3. Start the redis server! `redis-server /usr/local/etc/redis.conf`
~~4. Start a worker! `celery -A rewind worker -l warning`~~

Import static data:
1. start django shell: `./manage.py shell`
2. in django shell:
```
    import api.items
    api.items.update_items()
```

Done!

To run:
1. install heroku-cli https://devcenter.heroku.com/articles/heroku-cli
2. Run `heroku local -p 8000`. Default port is 5000 
Heroku will automatically run a celery worker as specified in the Procfile.

Test on http://localhost:8000/get_match_timeline/?region=NA&match_id=2650476106

Deployment:
screen -S server ./server.sh
screen -S celery ./celery.sh



