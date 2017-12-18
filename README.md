Timewinder Rewind

TODO:
- Batch async api calls
- URL sethod specification refactor
- Include timeline stats in aggregations (Results in 2x API calls and processing time, check performance scalability)

Setup:
1. Create a new virtual env (virtualenv, anaconda) with python3.6
2. `pip install -r requirements.txt`
3. `pip install git+https://github.com/meraki-analytics/cassiopeia.git`
	*install directly from git to get the latest changes. Cassiopeia doesnt often release to pip
4. Write `export RIOT_API_KEY=<key>` to .bash_profile 

DB setup:
1. Install postgres 10 with `brew install postgresql`. Read postgres docs for instructions on how to start it up.
2. in postgres shell, 
```
	CREATE DATABASE timewinder;
	CREATE USER timewinder_admin WITH PASSWORD 'twnumba1';
	GRANT ALL PRIVILEGES ON DATABASE timewinder TO timewinder_admin;
```
3. Run `./manage.py migrate` to apply migrations

Must setup rabbitMQ if you want data aggregations to run:
1. `brew install rabbitMQ`
3. Start the rabbitMQ server! `rabbitmq-server -detached`
4. Start a worker! `celery -A rewind worker -l info`

Done!

`./manage.py runserver` 

test on http://localhost:8000/get_match_timeline/?region=NA&match_id=2650476106



