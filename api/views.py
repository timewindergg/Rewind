from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

import os
import cassiopeia as cass
from cassiopeia.core import CurrentMatch
import datetime
import json

cass.set_riot_api_key(os.environ["RIOT_API_KEY"])
print(cass.__dict__)
cass.apply_settings({
  "global": {
    "default_region": None
  },

  "pipeline": {
    "Cache": {
      "expirations": {
          "ChampionStatusData": datetime.timedelta(hours=6),
          "ChampionStatusListData": datetime.timedelta(hours=6),
          "Realms": datetime.timedelta(hours=6),
          "Versions": datetime.timedelta(hours=6),
          "Champion": datetime.timedelta(days=20),
          "Rune": datetime.timedelta(days=20),
          "Item": datetime.timedelta(days=20),
          "SummonerSpell": datetime.timedelta(days=20),
          "Map": datetime.timedelta(days=20),
          "ProfileIcon": datetime.timedelta(days=20),
          "Locales": datetime.timedelta(days=20),
          "LanguageStrings": datetime.timedelta(days=20),
          "SummonerSpells": datetime.timedelta(days=20),
          "Items": datetime.timedelta(days=20),
          "Champions": datetime.timedelta(days=20),
          "Runes": datetime.timedelta(days=20),
          "Maps": datetime.timedelta(days=20),
          "ProfileIcons": datetime.timedelta(days=20),
          "ChampionMastery": datetime.timedelta(days=7),
          "ChampionMasteries": datetime.timedelta(days=7),
          "LeagueEntries": datetime.timedelta(hours=6),
          "League": datetime.timedelta(hours=6),
          "ChallengerLeague": datetime.timedelta(hours=6),
          "MasterLeague": datetime.timedelta(hours=6),
          "Match": datetime.timedelta(days=3),
          "Timeline": datetime.timedelta(days=1),
          "Summoner": datetime.timedelta(days=1),
          "ShardStatus": datetime.timedelta(hours=1),
          "CurrentMatch": -1,
          "FeaturedMatches": -1
      }
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

@require_http_methods(["POST"])
def update_summoner(request):
    pass

@require_http_methods(["GET"])
def get_summoner(request):
    pass

@require_http_methods(["GET"])
def get_match_history(request):
    pass

@require_http_methods(["GET"])
def get_user_champion_stats(request):
    pass

@require_http_methods(["GET"])
def get_current_match(request):
    pass

@require_http_methods(["GET"])
def get_match_timeline(request):
    region = request.GET['region']
    match_id = int(request.GET['match_id'])

    match = cass.get_match(id=match_id, region=region)
    timeline = match.timeline
    frames = match.timeline.frames

    #remove duplicate data from cass
    tl = json.loads(timeline.to_json())
    frames = tl['frames']
    for item in frames:
        participant_frame = item['_participant_frames']['1']
        item['participant_frame'] = participant_frame
        del item['_participant_frames']

    return JsonResponse(tl)
