import cassiopeia as cass
from flask import Flask, jsonify, request
import os

API_KEY = os.environ['RIOT_API_KEY']
REGION = "NA"

app = Flask(__name__)
cass.set_riot_api_key(API_KEY)  # This overrides the value set in your configuration/settings.
cass.set_default_region(REGION)

@app.route("/", methods=['GET'])
def hello():
    summoner = cass.get_summoner(name="xxCode")

    return jsonify({'name':summoner.name,
                    'level':summoner.level})

@app.route("/api/<region>/<summoner>")
def getSummoner(region, summoner):
    pass
