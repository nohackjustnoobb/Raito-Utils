import json
import os
from constant import *


print(
    "Get your credentials from this website: https://my.surfshark.com/vpn/manual-setup/main/openvpn"
)
username = input("Username: ")
password = input("Password: ")

number = input("Number of proxies (10): ") or 10
ip = input("IP address (localhost): ") or "localhost"


config = {
    "testLinks": [],
    "proxies": [],
}


os.makedirs("./output/docker-compose", exist_ok=True)

for i in range(number):
    country = tuple(COUNTRIES.keys())[0]

    override = input(f"Country ({country}): ")
    cities = COUNTRIES.get(override)
    if cities is not None:
        country = override
    else:
        print(f"Can't find the input country. Falling back to {country}.")

    cities = COUNTRIES[country]
    city = cities.pop()

    if len(cities) == 0:
        del COUNTRIES[country]

    yml = f"""version: "3"

services:
    surfshark:
        image: ilteoood/docker-surfshark
        container_name: surfshark-{i}
        environment:
            - SURFSHARK_USER={username}
            - SURFSHARK_PASSWORD={password}
            - SURFSHARK_COUNTRY={country}
            - SURFSHARK_CITY={city}
            - LAN_NETWORK=10.0.0.0/16
        cap_add:
            - NET_ADMIN
        devices:
            - /dev/net/tun
        ports:
            - {1080 + i}:1080
        restart: unless-stopped
"""

    os.makedirs(f"./output/docker-compose/surfshark-{i}", exist_ok=True)
    with open(f"./output/docker-compose/surfshark-{i}/docker-compose.yml", "w") as file:
        file.write(yml)

    config["proxies"].append(
        {
            "address": f"socks5://{ip}:{1080+i}",
            "restartCMD": f"docker restart surfshark-{i}",
        }
    )

with open("./output/config.json", "w") as json_file:
    json.dump(config, json_file, indent=4, ensure_ascii=False)

start = input("Start (N): ")

if start.lower() == "y":
    import start
