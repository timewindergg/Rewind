from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict

import os
import cassiopeia as cass
from cassiopeia.core import CurrentMatch
import datetime
import time
import json

from .aggregator.tasks import aggregate_users, aggregate_user_match, aggregate_global_stats
from .models import ProfileStats, ChampionItems, UserChampionStats, Matches
from . import items as Items
from . import consts as Consts

import pdb

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

@require_http_methods(["GET"])
def get_version(request):
    response = {}

    try:
        response['version'] = cass.get_version()
    except:
        return HttpResponse(status=500)
        
    return JsonResponse(response)

@csrf_exempt
@require_http_methods(["POST"])
def update_summoner(request):
    summoner_name = request.POST['summoner_name']
    region = request.POST['region']

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        summoner, created = ProfileStats.objects.get_or_create(user_id=s.id, region=s.region.value)
        if created or summoner.last_updated < time.time() - Consts.SECONDS_BETWEEN_UPDATES:
            summoner.last_updated = round(time.time())
            aggregate_users.delay(s.id, s.region.value, 100)
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

    try:
        summoner = ProfileStats.objects.get(name=summoner_name, region=region)
    except:
        return HttpResponse(status=404)

    response = model_to_dict(summoner)

    return JsonResponse(response)


@require_http_methods(["GET"])
def get_match_history(request):
    summoner_id = int(request.GET['summoner_id'])
    region = request.GET['region']
    offset = int(request.GET['offset'])
    size = int(request.GET['size'])
    
    try:
        matches = Matches.objects.filter(user_id=summoner_id, region=region).order_by('-timestamp')[offset:size]
    except:
        return HttpResponse(status=404)

    response = list(matches.values())

    return JsonResponse(response, safe=False)


@require_http_methods(["GET"])
def get_user_champion_stats(request):
    summoner_name = request.GET['summoner_name']
    region = request.GET['region']

    try:
        profile = ProfileStats.objects.get(name=summoner_name, region=region)
    except:
        return HttpResponse(status=404)

    champ_stats = UserChampionStats.objects.filter(user_id=profile.user_id, region=region)
    response = list(champ_stats.values())

    return JsonResponse(response, safe=False)

@require_http_methods(["GET"])
def get_current_match(request):
    summoner_name = request.GET['summoner_name']
    region = request.GET['region']

    s = cass.get_summoner(name=summoner_name, region=region)
    if not s.exists:
        return HttpResponse(status=404)

    try:
        m = cass.get_current_match(summoner=s, region=region)
    except:
        return HttpResponse(status=404)

    response = {}

    red_team = []
    blue_team = []
    for participant in m.participants:
        p = {}
        p['id'] = participant.summoner.id
        p['champion_id'] = participant.champion.id
        p['name'] = participant.summoner.name
        p['summoner_spell0'] = participant.summoner_spell_d.id
        p['summoner_spell1'] = participant.summoner_spell_f.id
        runes = []
        for rune in participant.runes:
            runes.append(rune.id)
        p['runes'] = runes
        if participant.side.value == 100:
            blue_team.append(p)
        elif participant.side.value == 200:
            red_team.append(p)

    response['red_team'] = red_team
    response['blue_team'] = blue_team

    return JsonResponse(response)

@require_http_methods(["GET"])
def get_current_match_details(request):
    summoner_name = request.GET['summoner_name']
    region = request.GET['region']
    champion_id = int(request.GET['champion_id'])

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        matchlist = cass.get_match_history(summoner=s, region=region, champions=[champion_id], begin_index=0, end_index=20)
    else:
        return HttpResponse(status=404)

    response = {}

    # summoner stats for past 20 matches on a champion
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
    match_history = []

    for match in matchlist:
        for participant in match.participants:
            if participant.summoner.id == s.id and hasattr(participant, "timeline"):
                user = participant
                break

        stats["kills"] += user.stats.kills
        stats["deaths"] += user.stats.deaths
        stats["assists"] += user.stats.assists
        stats["totalCs"] += user.stats.total_minions_killed

        if user.stats.win:
            stats["wins"] += 1
            match_history.append(1)
        else:
            stats["losses"] += 1
            match_history.append(0)

    build = {}

    # get recommended build
    try:
        items = ChampionItems.objects.raw('SELECT * FROM api_championitems ci INNER JOIN api_items i ON ci.item_id = i.item_id WHERE ci.champ_id = %s ORDER BY ci.occurence DESC' % champion_id)
        boots = [item.item_id for item in items if item.item_type == Consts.ITEM_BOOTS]
        all_items = [item.item_id for item in items if item.item_type == Consts.ITEM_CORE]
        core = all_items[:3]
        situational = all_items[3:8]
    except:
        boots = []
        core = []
        situational = []
    
    build['boots'] = boots
    build['core'] = core
    build['situational'] = situational

    response['stats'] = stats
    response['build'] = build

    return JsonResponse(response)

@require_http_methods(["GET"])
def get_match_timeline(request):
    region = request.GET['region']
    match_id = int(request.GET['match_id'])

    match = cass.get_match(id=match_id, region=region)
    timeline = match.timeline
    frames = timeline.frames
    tl = json.loads(timeline.to_json())

    return JsonResponse(tl)
