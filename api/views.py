from django.shortcuts import render
from django.http import JsonResponse

import os
import cassiopeia as cass
from cassiopeia.core import CurrentMatch
import datetime

cass.apply_settings({
  "global": {
    "default_region": None
  },

  "pipeline": {
    "Cache": {
    },

    "DDragon": {},

    "RiotAPI": {
      "api_key": "RIOT_API_KEY"
    }
  },

  "logging": {
    "print_calls": True,
    "print_riot_api_key": False,
    "default": "WARNING",
    "core": "WARNING"
  }
})
cass.set_riot_api_key(os.environ["RIOT_API_KEY"])
cass.set_default_region("NA")

def test(request):
    return JsonResponse([{
        "id": "1",
        "username": "samsepi0l"
      }, {
        "id": "2",
        "username": "D0loresH4ze"
      }], safe=False)

def get_match_timeline(request):
    #region = request.GET['region']
    #match_id = request.GET['match_id']

    s = cass.get_summoner(name="Kalturi")
    match = cass.get_match(id=33206532)
    

    return JsonResponse({"name":s.name})
