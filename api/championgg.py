import time
import cassiopeia as cass
from cassiopeia import Champion

from pprint import pprint
from urllib.request import urlopen
import json
import os

from api.models import ChampionStats, ChampionMatchups

KEY = os.environ['CHAMPIONGG_API_KEY']

def update_champions():
    # fetch all champions
    champions = cass.get_champions('NA')
    total_champions = len(champions)

    then = time.time()

    for i, champion in enumerate(champions):
        print("Updating %d of %d..." % (i+1, total_champions), end='')

        champion_url = "http://api.champion.gg/v2/champions/%d?champData=hashes,matchups&api_key=%s" % (champion.id, KEY)
        response = urlopen(champion_url)
        dictionary = json.load(response)

        for role in dictionary:
            champ_id = role['_id']['championId']
            champion_role = role['_id']['role']

            champion_stat, created = ChampionStats.objects.get_or_create(champ_id=champ_id, role=champion_role)

            if ('skillorderhash' in role['hashes']):
                champion_stat.skill_orders = json.dumps(role['hashes']['skillorderhash']['highestCount'])
            if ('finalitemshashfixed' in role['hashes']):
                champion_stat.items = json.dumps(role['hashes']['finalitemshashfixed']['highestCount'])
            if ('summonershash' in role['hashes']):
                champion_stat.summoners = json.dumps(role['hashes']['summonershash']['highestCount'])
            if ('runehash' in role['hashes']):
                champion_stat.runes = json.dumps(role['hashes']['runehash']['highestCount'])

            champion_stat.save()

            for matchup in role['matchups'][champion_role]:
                champion_match_up, created = ChampionMatchups.objects.get_or_create(champ_id=champ_id, role=champion_role, enemy_champ_id=matchup['champ2_id'])
                champion_match_up.win_rate = matchup['champ1']['winrate']
                champion_match_up.kills = matchup['champ1']['kills']
                champion_match_up.deaths = matchup['champ1']['deaths']
                champion_match_up.assists = matchup['champ1']['assists']
                champion_match_up.save()

            if champion_role == 'DUO_CARRY' or champion_role == 'DUO_SUPPORT':
                for matchup in role['matchups']['ADCSUPPORT']:
                    champion_match_up, created = ChampionMatchups.objects.get_or_create(champ_id=champ_id, role=champion_role, enemy_champ_id=matchup['champ2_id'])
                    champion_match_up.win_rate = matchup['champ1']['winrate']
                    champion_match_up.kills = matchup['champ1']['kills']
                    champion_match_up.deaths = matchup['champ1']['deaths']
                    champion_match_up.assists = matchup['champ1']['assists']
                    champion_match_up.save()

        print(" done")
        
        now = time.time()
        if now - then < 0.2:
            time.sleep(now - then)

    print("Update complete!")
