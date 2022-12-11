
from catboost import CatBoostRegressor
import os
import json
import glob
import pandas as pd

def to_float(val, stars):
    if val == stars:
        return 1.0
    return 0.0

data = []

for file in glob.glob("clanwars/*.json"):
    with open(file, "r") as f:
        c = json.loads(f.read())
        data += c
                 
print(f"Read {len(data)} data points")
df = pd.DataFrame(data)
df_encoded = df.drop(labels=["attackerTag", "defenderTag", "order", "duration", "destructionPercentage", "attacker_warPreference", "defender_warPreference"], axis=1)
cat_features = ['attacker_league', 'defender_league']

models = []

split_i = int(df_encoded.shape[0] * 0.7)
train = df_encoded.iloc[:split_i]
test = df_encoded.iloc[split_i:]
train_data = train.drop(labels=['stars'], axis=1)
train_labels = train['stars']
test_data = test.drop(labels=['stars'], axis=1)
test_labels = test['stars']

for stars in [0, 1, 2, 3]:
    print(f"fitting {stars}")
    train_labels_mod = train_labels.apply(lambda val: to_float(val, stars))
    test_labels_mod = test_labels.apply(lambda val: to_float(val, stars))
    model = CatBoostRegressor(iterations=100000)
    model_name = f"stars_regression_{stars}.cbm"
    if not os.path.exists(model_name):
        model.fit(train_data, train_labels_mod, cat_features=cat_features, eval_set=(test_data, test_labels_mod), early_stopping_rounds=10, verbose=True)
        model.save_model(model_name)
    else:
        model.load_model(model_name)
    models.append(model)



with open("columns.json", "w") as f:
    f.write(json.dumps([column for column in train_data.columns]))


matches = 0

for i in range(test_data.shape[0]):
    denum = 0
    num = 0
    for star in [0, 1, 2, 3]:
        pred = models[star].predict(test_data.iloc[i])
        denum += pred
        if int(star) == int(test_labels.iloc[i]):
            num += pred
print(f"OOS accuracy {num / denum}")
