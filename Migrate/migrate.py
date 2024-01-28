import json
import requests


# load the config
with open("config.json", "r") as file:
    config = json.load(file)


# obtain token
fromToken = requests.post(
    config["fromEndpoint"]["token"],
    json={
        "email": config["fromEmail"],
        "password": config["fromPassword"],
    },
).json()["token"]
fromToken = f"{config['fromEndpoint']['authScheme']} {fromToken}"


toToken = requests.post(
    config["toEndpoint"]["token"],
    json={
        "email": config["toEmail"],
        "password": config["toPassword"],
    },
).json()["token"]
toToken = f"{config['toEndpoint']['authScheme']} {toToken}"


# migrate collections
fromCollection = requests.get(
    config["fromEndpoint"]["collection"], headers={"Authorization": fromToken}
).json()
requests.post(
    config["toEndpoint"]["collection"],
    json=fromCollection,
    headers={"Authorization": toToken},
)


# migrate history
fromHistory = []
page = 1
while True:
    resp = requests.get(
        config["fromEndpoint"]["history"],
        params={"page": page},
        headers={"Authorization": fromToken},
    )
    fromHistory.extend(resp.json())

    page += 1
    if resp.headers["Is-Next"] == "0":
        break
requests.post(
    config["toEndpoint"]["history"],
    json=fromHistory,
    headers={"Authorization": toToken},
)
