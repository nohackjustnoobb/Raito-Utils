import json

# check the config
with open("config.json", "r") as file:
    config = json.load(file)


mode = config.get("mode", "all")
if mode == "update":
    import mode.update
else:
    import mode.all
