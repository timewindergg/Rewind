from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

import os
import cassiopeia as cass
from cassiopeia.core import CurrentMatch
import datetime
import time
import json

from .aggregator.tasks import aggregate_users, aggregate_user_match, aggregate_global_stats
from .models import ProfileStats

cass.set_riot_api_key(os.environ["RIOT_API_KEY"])
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

@csrf_exempt
@require_http_methods(["POST"])
def update_summoner(request):
    summoner_name = request.POST['summoner_name']
    region = request.POST['region']

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        summoner, created = ProfileStats.objects.get_or_create(user_id=s.id, region=s.region.value)
        if created or summoner.last_updated < time.time() - 15*60:
            summoner.last_updated = round(time.time())
            aggregate_users.delay(s.id, s.region.value)
        summoner.name = s.name
        summoner.region = s.region.value
        summoner.icon = s.profile_icon.id
        summoner.level = s.level
        summoner.save()

        #update leagues, deprecated..
        #l = cass.get_leagues(summoner=s, region=region)

    else:
        return HttpResponse(status=404)

    return HttpResponse(status=200)

@require_http_methods(["GET"])
def get_summoner(request):
    summoner_name = request.GET['summoner_name']
    region = request.GET['region']

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        summoner = ProfileStats.objects.get(name=summoner_name, region=region)
    else:
        return HttpResponse(status=404)

    return JsonResponse(summoner)

@require_http_methods(["GET"])
def get_match_history(request):
    summoner_id = request.GET['summoner_id']
    region = request.GET['region']
    offset = request.GET['offset']
    size = request.GET['size']

    matches = Matches.objects.get(user_id=summoner_id, region=region).order_by('-timestamp')[offset:size]

    return JsonResponse(matches)


@require_http_methods(["GET"])
def get_user_champion_stats(request):
    summoner_name = request.GET['summoner_name']
    region = request.GET['region']

    try:
        profile = ProfileStats.objects.get(name=summoner_name, region=region)
        champ_stats = UserChampionStats.objects.get(user_id=profile.user_id, region=region)
    except:
        return JsonResponse(status=404)

    return JsonResponse(champ_stats)

@require_http_methods(["GET"])
def get_current_match(request):
    summoner_name = request.GET['summoner_name']
    region = request.GET['region']

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        m = cass.get_current_match(s, region)
    else:
        return HttpResponse(status=404)

    response = {}

    red_team = []
    blue_team = []
    for participant in m.red_team:
        championWinRate = ""
        totalCs = 


    return JsonResponse(m)

@require_http_methods(["GET"])
def get_current_match_details(request):
    summoner_name = request.GET['summoner_name']
    region = request.GET['region']
    champion_id = request.GET['champion_id']

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        matchlist = cass.get_match_history(summoner=s, region=region, champion=[champion_id], start_index=0, end_index=20)
    else
        return HttpResponse(status=404)

    stats = {
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "totalCs": 0,
        "totalCs10": 0,
        "totalCs20": 0,
        "totalCs30": 0,
        "wins": 0,
        "losses": 0
    }
    for match in matchlist:
        for participant in match.participants:
        if participant.summoner.id == summoner.id:
            user = participant
            break

        stats["kills"] += user.stats.kills
        stats["deaths"] += user.stats.deaths
        stats["assists"] += user.stats.assists
        stats["totalCs"] += user.stats.total_minions_killed

        if user.stats.win:
            stats["wins"] += 1
        else:
            stats["losses"] += 1

        

    return JsonResponse(json.dumps(stats))

@require_http_methods(["GET"])
def get_match_timeline(request):
    region = request.GET['region']
    match_id = int(request.GET['match_id'])

    match = cass.get_match(id=match_id, region=region)
    timeline = match.timeline
    frames = timeline.frames
    tl = json.loads(timeline.to_json())

    return JsonResponse(tl)
