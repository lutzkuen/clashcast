
import json
from flask import Flask, render_template, request, session, send_file, url_for
from catboost import CatBoostRegressor
import requests
import urllib
import os
from PIL import Image, ImageFont, ImageDraw 

models = []
for star in [0, 1, 2, 3]:
    models.append(CatBoostRegressor().load_model(f"stars_regression_{star}.cbm"))

with open("columns.json", "r") as f:
    columns = json.loads(f.read())

class CoCForecaster:
    def __init__(self, models, api_key, sorted_columns):
        self.api_key = api_key
        self.models = models
        self.player_infos = dict()
        self.header = {"Authorization": f"Bearer {api_key}"}
        self.sorted_columns = sorted_columns

    def get_clan_name_suggestions(self, search_term):
        parts = urllib.parse.unquote(search_term).split("/")
        clan_part = parts[0].strip()
        clans_response = requests.get(f"{os.getenv('CLASH_OF_CLANS_ENDPOINT')}/clans?name={urllib.parse.quote(clan_part)}&limit=5", headers=self.header)
        suggestions = []
        for clan in clans_response.json()["items"]:
            clan_info = requests.get(f"{os.getenv('CLASH_OF_CLANS_ENDPOINT')}/clans/{urllib.parse.quote(clan['tag'])}", headers=self.header)
            for member in clan_info.json()["memberList"]:
                if len(parts) >= 3:
                    clan_rank = parts[2].strip()
                    if member["clanRank"] == clan_rank:
                        suggestions.append(f"{clan['name']} / {member['name']} / {member['clanRank']}")
                elif len(parts) >= 2:
                    member_name = parts[1].strip()
                    if member_name.lower() in member["name"].lower():
                        suggestions.append(f"{clan['name']} / {member['name']} / {member['clanRank']}")
                else:
                    suggestions.append(f"{clan['name']} / {member['name']} / {member['clanRank']}")
                if len(suggestions) >= 20:
                    return suggestions
        return suggestions

    def get_clan_tag(self, clan_name):
        clans_response = requests.get(f"{os.getenv('CLASH_OF_CLANS_ENDPOINT')}/clans?name={clan_name}&limit=1", headers=self.header)
        if len(clans_response.json()["items"]) == 0:
            return None
        return clans_response.json()["items"][0]["tag"]

    def get_clan_members(self, clan_tag):
        clan_response = requests.get(f"{os.getenv('CLASH_OF_CLANS_ENDPOINT')}/clans/{clan_tag}", headers=self.header)
        return clan_response.json()["memberList"]
        
    def get_player_info(self, player_tag):
        if player_tag in self.player_infos.keys():
            return self.player_infos[player_tag]
        response = requests.get(f"{os.getenv('CLASH_OF_CLANS_ENDPOINT')}/players/{player_tag}", headers=self.header)
        player_info = dict()
        for key in ["townHallLevel", "expLevel", "trophies", "bestTrophies", "warStars", "attackWins", "defenseWins", "builderHallLevel", "versusTrophies", "bestVersusTrophies", "versusBattleWins", "warPreference", "donations", "donationsReceived", "clanCapitalContributions"]: 
            player_info[key] = response.json().get(key, 0)
        if "league" in response.json().keys():
            player_info["league"] = response.json()["league"]["name"]
        else:
            player_info["league"] = "none"
        if "troops" in response.json().keys():
            for troop in response.json().get('troops'):
                key = f"troop_{troop['name'].replace(' ', '_')}_level"
                player_info[key] = troop['level']
        else:
            print(f"Did not find troops for {player_tag}")
        if "heroes" in response.json().keys():
            for hero in response.json().get('heroes'):
                key = f"hero_{hero['name'].replace(' ', '_')}_level"
                player_info[key] = hero['level']
        else:
            print(f"Did not find heroes for {player_tag}")            
        if "spells" in response.json().keys():
            for spell in response.json().get('spells'):
                key = f"spell_{spell['name'].replace(' ', '_')}_level"
                player_info[key] = spell['level']
        print(f"Did not find spells for {player_tag}")
        self.player_infos[player_tag] = player_info
        return player_info
        
    def get_star_probability(self, attacker_tag, defender_tag):
        attacker_info = self.get_player_info(attacker_tag)
        defender_info = self.get_player_info(defender_tag)
        row = []
        for column in self.sorted_columns:
            if column.startswith("attacker_"):
                key = column.replace("attacker_", "")
                row.append(attacker_info.get(key))
            if column.startswith("defender_"):
                key = column.replace("defender_", "")
                row.append(defender_info.get(key))
        stars = [self.models[0].predict([row]), self.models[1].predict([row]), self.models[2].predict([row]), self.models[3].predict([row])]
        # remove negative probabilities
        for i in range(len(stars)):
            if stars[i][0] < 0:
                stars[i][0] = 0
        # normalize the vector to sum to 1
        ss = 0
        for i in range(4):
            ss += stars[i][0]
        for i in range(4):
            stars[i][0] = stars[i][0] / ss
        expectation = round(stars[1][0] + 2*stars[2][0] + 3*stars[3][0],2)
        return [round(100*stars[0][0]), round(100*stars[1][0]), round(100*stars[2][0]), round(100*stars[3][0]), expectation]
    
forecaster = CoCForecaster(models, os.getenv('CLASH_OF_CLANS_KEY'), columns)

app = Flask(__name__)


@app.route("/")
def index():
    """
    Print welcome screen

    :return:
    """
    return render_template(
        "index.html",
    )

@app.route("/clan/search", methods=["GET"])
def search_clan():
    search_term = request.args.get("q")
    return forecaster.get_clan_name_suggestions(urllib.parse.quote(search_term))


@app.route("/", methods=["POST"])
def multiplayer():
    attacker_tag = request.form.get("attacker")
    defender_clan = request.form.get("defender_clan")
    defender_clan, defender_name, defender_clan_rank = [part.strip() for part in defender_clan.split("/")]
    defender_clan_tag = urllib.parse.quote(forecaster.get_clan_tag(defender_clan))
    members = forecaster.get_clan_members(defender_clan_tag)
    font = ImageFont.truetype("font/Roboto-Black.ttf", 16)
    is_found = False
    for clan_member in members:
        if clan_member["clanRank"] == defender_clan_rank or clan_member["name"] == defender_name:
            is_found = True
            break
    if is_found:
        defender_tag = clan_member["tag"]
        propabilities = forecaster.get_star_probability(urllib.parse.quote(attacker_tag), urllib.parse.quote(defender_tag))
        default_image = Image.open("static/assets/3_stars_big_icon.png")
        image_edit = ImageDraw.Draw(default_image)
        for i in [1, 2, 3]:
            ypos = 65
            if i == 2:
                ypos = 55
            image_edit.text((37+(i-1)*98, ypos), str(propabilities[i])+" %", (0, 0, 0), font=font)
        image_name = f"{attacker_tag.replace('#', '')}_{defender_tag.replace('#', '')}.png"
        default_image.save(f"static/assets/{image_name}")
        return render_template(
            "index.html",
            image_url=image_name,
        )
    else:
        return render_template(
            "index.html",
            not_found=True,
        )
    

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
