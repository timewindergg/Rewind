from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.db import transaction
from django.db.models import Sum, Q

import os
import cassiopeia as cass
from cassiopeia.core import CurrentMatch
import datetime
import time
import json
from functools import reduce

from .aggregator.tasks import aggregate_users, aggregate_user_match, aggregate_global_stats
from .models import ProfileStats, ChampionItems, UserChampionStats, Matches, MatchLawn, UserLeagues, UserChampionMasteries, UserChampionVersusStats, UserChampionItems, UserChampionRunes, UserChampionSummoners
from . import items as Items
from . import consts as Consts

import logging
log = logging.getLogger(__name__)

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
      "api_key": os.environ["RIOT_API_KEY"]
    },
  },

  "logging": {
    "print_calls": True,
    "print_riot_api_key": False,
    "default": "WARNING",
    "core": "WARNING"
  }
})

#
# HELPER FUNCTIONS
#
def normalize_region(region):
    try:
        return region.upper()
    except:
        return region

def get_champion_id(name):
    return int(Consts.CHAMPION_IDS[name.lower()])

#
# STATIC DATA
#
@require_http_methods(["GET"])
def get_static_data(request):
    region = normalize_region(request.GET['region'])

    response = {}
    try:
        response['version'] = cass.get_version(region=region)
        
        items_response = {}
        items = cass.get_items(region=region)
        for item in items:
            item_response = {}
            item_response['name'] = item.name
            item_response['totalGold'] = item.gold.total
            item_response['sellGold'] = item.gold.sell
            item_response['description'] = item.description
            item_response['plaintext'] = item.plaintext
            items_response[str(item.id)] = item_response
        response['items'] = items_response
        
    except Exception as e:
        log.warn("failed to get static data", stack_info=True)
        log.warn(e)
        return HttpResponse(status=500)
        
    return JsonResponse(response)

#
# UPDATE SUMMONER
#
def update_summoner_helper(s, region):
    update = False

    with transaction.atomic():
        summoner, created = ProfileStats.objects.select_for_update().get_or_create(user_id=s.id, region=region)
        if created or summoner.last_updated < time.time() - Consts.SECONDS_BETWEEN_UPDATES:
            update = True
            summoner.last_updated = round(time.time())
            summoner.name = s.name
            summoner.icon = s.profile_icon.id
            summoner.level = s.level
            summoner.save()

            leagues = cass.get_league_positions(summoner=s, region=region)
            for league in leagues:
                user_league, created = UserLeagues.objects.select_for_update().get_or_create(user_id=s.id, region=region, queue=league.queue.value)
                user_league.tier = league.tier.value
                user_league.division = league.division.value
                user_league.points = league.league_points
                user_league.save()

            cmasteries = cass.get_champion_masteries(summoner=s, region=region)
            for cmastery in cmasteries:
                user_champion, created = UserChampionMasteries.objects.select_for_update().get_or_create(user_id=s.id, region=region, champ_id=cmastery.champion.id)
                user_champion.level = cmastery.level
                user_champion.total_points = cmastery.points
                user_champion.points_since_last = cmastery.points_since_last_level
                user_champion.points_to_next = cmastery.points_until_next_level
                user_champion.chest_granted = cmastery.chest_granted
                user_champion.save()
                
        transaction.on_commit(lambda: aggregate_users.delay(summoner.user_id, region, 500))


@csrf_exempt
@require_http_methods(["POST"])
def update_summoner(request):
    summoner_name = request.POST['summoner_name']
    region = normalize_region(request.POST['region'])

    s = cass.get_summoner(name=summoner_name, region=region)
    if s.exists:
        update_summoner_helper(s, region)
    else:
        return HttpResponse(status=404)

    return HttpResponse(status=200)

#
# GET SUMMONER
#
@require_http_methods(["GET"])
def get_summoner(request):
    summoner_name = request.GET['summoner_name']
    region = normalize_region(request.GET['region'])

    s = cass.get_summoner(name=summoner_name, region=region)
    if not s.exists:
        return HttpResponse('Summoner does not exist', status=404)

    update_summoner_helper(s, region)

    try:
        summoner = ProfileStats.objects.get(user_id=s.id, region=region)
    except:
        log.warn("ProfileStats not found after update in get_summoner")
        return HttpResponse("Error retrieving profile stats", status=500)

    try:
        cmasteries = UserChampionMasteries.objects.filter(user_id=s.id, region=region).order_by('-total_points')[:3]
    except:
        log.warn("UserChampionMasteries not found after update in get_summoner")
        return HttpResponse("Error retrieving champion masteries", status=500)

    try:
        userLeagues = UserLeagues.objects.filter(user_id=s.id, region=region)
    except:
        log.warn("ProfileStats not found after update in get_summoner")
        return HttpResponse("Error retrieving leagues", status=500)

    try:
        lawn = MatchLawn.objects.filter(user_id=s.id, region=region).order_by('-date')[:90]
    except:
        log.warn("Lawn not found after update in get_summoner")
        return HttpResponse("Error retrieving matchlawn", status=500)

    try:
        champ_stats = UserChampionStats.objects.filter(user_id=s.id, region=region)
    except:
        log.warn("Champ stats not found after update in get_summoner")
        return HttpResponse(status=500)

    response = model_to_dict(summoner)
    response['championMasteries'] = list(cmasteries.values())
    response['leagues'] = list(userLeagues.values())
    response['lawn'] = list(lawn.values())
    response['championStats'] = list(champ_stats.values())

    return JsonResponse(response)

#
# MATCH HISTORY
#
@require_http_methods(["GET"])
def get_match_history(request):
    summoner_name = request.GET['summoner_name']
    region = normalize_region(request.GET['region'])
    offset = int(request.GET['offset'])
    size = int(request.GET['size'])

    summoner = cass.get_summoner(name=summoner_name, region=region)
    if not summoner.exists:
        return HttpResponse('Summoner does not exist', status=404)

    try:
        matches = Matches.objects.filter(user_id=summoner.id, region=region).order_by('-timestamp')[offset:size]
    except:
        return HttpResponse(status=404)

    response = list(matches.values())

    return JsonResponse(response, safe=False)

#
# USER CHAMPION STATS
#
def get_user_champion_stats(summoner_name, region, champion_id):
    summoner = cass.get_summoner(name=summoner_name, region=region)
    if not summoner.exists:
        return HttpResponse('Summoner does not exist', status=404)

    response = {}

    try:
        champ_stats = UserChampionStats.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id)
    except:
        log.warn("failed to get champ_stats", stack_info=True)
        return HttpResponse(status=500)

    try:
        champ_versus = UserChampionVersusStats.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id)
    except:
        log.warn("failed to get champ_versus", stack_info=True)
        return HttpResponse(status=500)

    try:
        championItems = {}
        items = UserChampionItems.objects.raw('SELECT * FROM api_userchampionitems ci INNER JOIN api_items i ON ci.item_id = i.item_id WHERE ci.champ_id = %s AND ci.season_id = 11 ORDER BY ci.occurence DESC' % champion_id)

        # top
        boots = [item.item_id for item in items if item.item_type == Consts.ITEM_BOOTS and item.lane == cass.data.Lane.top_lane.value]
        all_items = [item.item_id for item in items if item.item_type == Consts.ITEM_CORE and item.lane == cass.data.Lane.top_lane.value]
        itemset = {}
        itemset['items'] = all_items
        itemset['boots'] = boots
        championItems['top'] = itemset

        # jungle
        boots = [item.item_id for item in items if item.item_type == Consts.ITEM_BOOTS and item.lane == cass.data.Lane.jungle.value]
        all_items = [item.item_id for item in items if item.item_type == Consts.ITEM_CORE and item.lane == cass.data.Lane.jungle.value]
        itemset = {}
        itemset['items'] = all_items
        itemset['boots'] = boots
        championItems['jg'] = itemset

        # mid
        boots = [item.item_id for item in items if item.item_type == Consts.ITEM_BOOTS and item.lane == cass.data.Lane.mid_lane.value]
        all_items = [item.item_id for item in items if item.item_type == Consts.ITEM_CORE and item.lane == cass.data.Lane.mid_lane.value]
        itemset = {}
        itemset['items'] = all_items
        itemset['boots'] = boots
        championItems['mid'] = itemset

        # bot
        boots = [item.item_id for item in items if item.item_type == Consts.ITEM_BOOTS and item.lane == cass.data.Lane.bot_lane.value]
        all_items = [item.item_id for item in items if item.item_type == Consts.ITEM_CORE and item.lane == cass.data.Lane.bot_lane.value]
        itemset = {}
        itemset['items'] = all_items
        itemset['boots'] = boots
        championItems['bot'] = itemset
    except:
        log.warn("failed to get champ_items", stack_info=True)
        return HttpResponse(status=500)

    try:
        champ_runes = UserChampionRunes.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id).order_by('-occurence')
    except:
        log.warn("failed to get champ_runes", stack_info=True)
        return HttpResponse(status=500)

    try:
        champ_summs = UserChampionSummoners.objects.filter(user_id=summoner.id, region=region, champ_id=champion_id).order_by('-occurence')
    except:
        log.warn("failed to get champ_summs", stack_info=True)
        return HttpResponse(status=500)

    response['championStats'] = list(champ_stats.values())
    response['championMatchups'] = list(champ_versus.values())
    response['championItems'] = championItems
    response['championRunes'] = list(champ_runes.values())
    response['championSummoners'] = list(champ_summs.values())

    return JsonResponse(response)


@require_http_methods
def get_user_champion_stats_by_id(request):
    summoner_name = request.GET['summoner_name']
    region = normalize_region(request.GET['region'])
    champion_id = int(['champion_id'])

    return get_user_champion_stats(summoner_name, region, champion_id)


@require_http_methods(["GET"])
def get_user_champion_stats_by_name(request):
    summoner_name = request.GET['summoner_name']
    region = normalize_region(request.GET['region'])
    champion_id = get_champion_id(request.GET['champion_name'])

    return get_user_champion_stats(summoner_name, region, champion_id)

#
# CURRENT MATCH
#
@require_http_methods(["GET"])
def get_current_match(request):
    summoner_name = request.GET['summoner_name']
    region = normalize_region(request.GET['region'])

    s = cass.get_summoner(name=summoner_name, region=region)
    if not s.exists:
        return HttpResponse(status=404)

    try:
        m = cass.get_current_match(summoner=s, region=region)
    except:
        return HttpResponse(status=404)

    response = {}
    winrates = {}

    blue_team_champs = [p.champion.id for p in m.teams[0].participants] 
    red_team_champs = [p.champion.id for p in m.teams[1].participants]

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
            cvs = UserChampionVersusStats.objects.filter(Q(champ_id=participant.champion.id) & reduce(lambda x, y: x | y, [Q(enemy_champ_id=champ) for champ in red_team_champs])).values('enemy_champ_id').annotate(Sum('wins'), Sum('losses'), Sum('total_games'))
        elif participant.side.value == 200:
            red_team.append(p)
            cvs = UserChampionVersusStats.objects.filter(Q(champ_id=participant.champion.id) & reduce(lambda x, y: x | y, [Q(enemy_champ_id=champ) for champ in blue_team_champs])).values('enemy_champ_id').annotate(Sum('wins'), Sum('losses'), Sum('total_games'))

        winrate = {}
        for c in cvs:
            winrate[c['enemy_champ_id']] = c
        winrates[str(participant.champion.id)] = winrate    
        
    blue_bans = [v.id for k, v in m.teams[0].bans.items()]
    red_bans = [v.id for k, v in m.teams[1].bans.items()]

    queue = {}
    queue['id'] = m.queue.id
    queue['value'] = m.queue.value

    response['red_team'] = red_team
    response['blue_team'] = blue_team
    response['red_bans'] = red_bans
    response['blue_bans'] = blue_bans
    response['creation'] = round(m.creation.timestamp())
    response['queue'] = queue
    response['winrates'] = winrates

    return JsonResponse(response)

#
# CURRENT_MATCH_DETAILS
#
def get_current_match_details(summoner_name, region, champion_id):
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
        "cs10": 0,
        "cs20": 0,
        "cs30": 0,
        "gold10": 0,
        "gold20": 0,
        "gold30": 0,
        "wins": 0,
        "losses": 0
    }
    match_history = []

    games10 = 0
    games20 = 0
    games30 = 0
    cs10 = 0
    cs20 = 0
    cs30 = 0
    gold10 = 0
    gold20 = 0
    gold30 = 0
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

        try:
            cs10 += match.timeline.frames[10].participant_frames[user.id].creep_score
            gold10 += match.timeline.frames[10].participant_frames[user.id].gold_earned
            games10 += 1

            cs20 += match.timeline.frames[20].participant_frames[user.id].creep_score
            gold20 += match.timeline.frames[20].participant_frames[user.id].gold_earned
            games20 += 1

            cs30 += match.timeline.frames[30].participant_frames[user.id].creep_score
            gold30 += match.timeline.frames[30].participant_frames[user.id].gold_earned
            games30 += 1
        except:
            pass

    try:
        stats["cs10"] = round(cs10 / games10, 2)
        stats["cs20"] = round(cs20 / games20, 2)
        stats["cs30"] = round(cs30 / games30, 2)
        stats["gold10"] = round(gold10 / games10, 2)
        stats["gold20"] = round(gold20 / games20, 2)
        stats["gold30"] = round(gold30 / games30, 2)
    except:
        # divide by 0
        pass

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

    return response


@require_http_methods(["POST"])
def get_current_match_details_by_batch(request):
    summoners = request.POST['summoners']
    region = normalize_region(request.POST['region'])

    response = {}

    for s in summoners:
        cid = int(s.champion_id)
        name = s.summoner_name
        response[name] = get_current_match_details(name, region, cid)

    return JsonResponse(response)


@require_http_methods(["GET"])
def get_current_match_details_by_id(request):
    summoner_name = request.GET['summoner_name']
    region = normalize_region(request.GET['region'])
    champion_id = int(request.GET['champion_id'])

    response = get_current_match_details(summoner_name, region, champion_id)

    return JsonResponse(response)

#
# MATCH TIMELINE
#
@require_http_methods(["GET"])
def get_match_timeline(request):
    region = normalize_region(request.GET['region'])
    match_id = int(request.GET['match_id'])

    match = cass.get_match(id=match_id, region=region).load()
    timeline = match.timeline.load()

    response = {}
    response['timeline'] = json.loads(timeline.to_json())
    response['match'] = json.loads(match.to_json())
    
    return JsonResponse(response)
