
import requests
import os
import urllib.parse
import random
import string
import time
import datetime
import json

header = {"Authorization": f"Bearer {os.getenv('CLASH_OF_CLANS_KEY')}"}
url = "https://api.clashofclans.com/v1"

def get_war_log(clan_tag):
    response = requests.get(f"https://api.clashofclans.com/v1/clans/%23{clan_tag.replace('#', '')}/currentwar", headers=header)
    if 'reason' in response.json().keys():
        if response.json()['reason'] == 'accessDenied':
            print("Access Denied")
            return '', []
    if 'state' in response.json().keys():
        if response.json()['state'] == 'notInWar':
            print("Not in war")
            return '', []
        if response.json()['state'] == 'preparation':
            print("In preparation")
            return '', []
    attacks = []
    for member in response.json()['clan']['members']:
        if 'attacks' not in member.keys():
            continue
        for attack in member['attacks']:
            attacker_info = get_player_info(attack['attackerTag'])
            for key in attacker_info.keys():
                new_key = f"attacker_{key}"
                attack[new_key] = attacker_info[key]
            defender_info = get_player_info(attack['defenderTag'])
            for key in defender_info.keys():
                new_key = f"defender_{key}"
                attack[new_key] = defender_info[key]
            attacks.append(attack)
    for member in response.json()['opponent']['members']:
        if 'attacks' not in member.keys():
            continue
        for attack in member['attacks']:
            attacker_info = get_player_info(attack['attackerTag'])
            for key in attacker_info.keys():
                new_key = f"attacker_{key}"
                attack[new_key] = attacker_info[key]
            defender_info = get_player_info(attack['defenderTag'])
            for key in defender_info.keys():
                new_key = f"defender_{key}"
                attack[new_key] = defender_info[key]
            attacks.append(attack)
    attacks = sorted(attacks, key = lambda x: x.get('order'))
    clan_tags = '_'.join(sorted([response.json()['clan']['tag'], response.json()['opponent']['tag']])).replace('#', '')
    war_tag = response.json()['startTime'] + '_' + clan_tags
    return war_tag, attacks


def get_player_info(player_tag):
    response = requests.get(f"https://api.clashofclans.com/v1/players/%23{player_tag.replace('#', '')}", headers=header)
    player_info = dict()
    for key in ["townHallLevel", "expLevel", "trophies", "bestTrophies", "warStars", "attackWins", "defenseWins", "builderHallLevel", "versusTrophies", "bestVersusTrophies", "versusBattleWins", "warPreference", "donations", "donationsReceived", "clanCapitalContributions"]: 
        player_info[key] = response.json()[key]
    if "league" in response.json().keys():
        player_info["league"] = response.json()["league"]["name"]
    else:
        player_info["league"] = "none"
    for troop in response.json()['troops']:
        key = f"troop_{troop['name'].replace(' ', '_')}_level"
        player_info[key] = troop['level']
    for hero in response.json()['heroes']:
        key = f"hero_{hero['name'].replace(' ', '_')}_level"
        player_info[key] = hero['level']
    for spell in response.json()['spells']:
        key = f"spell_{spell['name'].replace(' ', '_')}_level"
        player_info[key] = spell['level']
    return player_info


def get_random_string(length):
    letters = string.printable
    result_str = ''.join(random.choice(letters) for i in range(length))
    return urllib.parse.quote(result_str)


if __name__ == '__main__':
    while True:
        random_string = get_random_string(3)
        print(f"new search string {random_string}")
        clans_response = requests.get(f"{url}/clans?name={random_string}&minMembers=20", headers=header)
        print(f"found {len(clans_response.json()['items'])} clans")
        for clan in clans_response.json()['items']:
            try:
                print(f"Parsing clan {clan['name']}")
                if not clan['isWarLogPublic']:
                    print(f"Clan war log is not public")
                    continue
                war_tag, attacks = get_war_log(clan['tag'])
                if len(attacks) == 0:
                    continue
                print(f"{datetime.datetime.now()} - {war_tag} / {len(attacks)}")
                with open(f"clanwars/{war_tag}.json", "w") as f:
                    f.write(json.dumps(attacks))
            except Exception as e:
                print(e)
            time.sleep(5)
