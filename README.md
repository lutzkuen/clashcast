# Clashcast

This repository contains python scripts to fetch Clash of Clans Battle result data and train Catboost models on it.

## Setup

Set the environment variables:

CLASH_OF_CLANS_KEY: Your clash of clans API key
CLASH_OF_CLANS_ENDPOINT: In most cases this is simply https://api.clashofclans.com/v1, unless supercell upgrades the API or you decide to run a custom proxy or such

install the requirements in the app folder

    python3 -m venv venv
    source venv/bin/activate
    pip install -r app/requirements.txt

## Gathering data

To gather data run 

    python get_data.py

this will slowly populate the clanwars folder with json files describing the outcome of some wars.

## Training the models

Run

    python parse_and_train.py

this will run for a bit depending on much data you gathered and create the cbm files.

## Running the prediction app

Move your previously trained models to the app folder

    cp *.cbm app/

Run the app

    cd app && python main.py

This will run a flask app which you can access at localhost:8080. When you enter your player Tag and manage to find your opponent with the clan name / player name / player rank combination the app will create a little image depicting your probability receiving a given amount of stars.
![](demo.png)