Timewinder Rewind

TODO:
- URL method specification refactor
- Include timeline stats in aggregations (Results in 2x API calls and processing time, check performance scalability)

Setup:
1. Create a new virtual env (virtualenv, anaconda) with python3.6
2. `pip install -r requirements.txt`
3. `pip install git+https://github.com/meraki-analytics/cassiopeia.git`
	*install directly from git to get the latest changes. Cassiopeia doesnt often release to pip
4. Write `export RIOT_API_KEY=<key>` to .bash_profile 

DB setup:
1. Install postgres 10 with `brew install postgresql`. Read postgres docs for instructions on how to start it up. You may(really) want to alias the commands for starting up and shutting down the psql server.
2. in postgres shell, 
```
	CREATE DATABASE timewinder;
	CREATE USER timewinder_admin WITH PASSWORD 'twnumba1';
	GRANT ALL PRIVILEGES ON DATABASE timewinder TO timewinder_admin;
```
3. Run `./manage.py migrate` to apply migrations

RabbitMQ setup:
1. `brew install rabbitMQ`
2. Start the rabbitMQ server! `sudo rabbitmq-server`
3. Start a worker! `celery -A rewind worker -l warning`

Import static data:
1. start django shell: `./manage.py shell`
2. in django shell:
```
    import api.items
    api.items.update_items()
```

Done!

`./manage.py runserver` 

test on http://localhost:8000/get_match_timeline/?region=NA&match_id=2650476106



