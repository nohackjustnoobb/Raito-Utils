import json
import ast
import os
import re
from PIL import Image
from io import BytesIO
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


inputFile = input('Input filename ("input.txt"): ') or "input.txt"

try:
    with open(f"./{inputFile}", "r") as file:
        content = file.read()

    if content[0] == "`":
        content = content[1:-1]
    else:
        content = ast.literal_eval(content)

    parsed = json.loads(content)
except:
    print("Failed to parse the input file.")
    exit(1)


title = []
configFile = input('Config filename ("config.json"): ') or "config.json"
config = None
try:
    with open(f"./{configFile}", "r") as file:
        content = file.read()

    config = json.loads(content)
    title = config.get("title", [])

except:
    print("Failed to parse the config file.")
    print("Please fill in the required options.")

    position = input("Title position (0): ") or 0
    regex = input('Title regex ("(.*)"): ') or "(.*)"
    template = input('Title template ("{}"): ') or "{}"

    title.append({"position": position, "regex": regex, "template": template})


if len(title) == 0:
    title.append({"position": 0, "regex": "(.*)", "template": "{}"})


def extractTitle(mesgs):
    result = []

    global title
    for i in title:
        try:
            result.append(
                i.get("template", "{}").replace(
                    "{}",
                    re.search(
                        i.get("regex", "(.*)"), mesgs[i.get("position", 0)]
                    ).group(1),
                )
            )
        except:
            pass

    if len(result) == 0:
        raise

    return " ".join(result)


data = []
failed = []
tooMuch = []
meta = []
for i in parsed:
    try:
        temp = {
            "title": extractTitle(i["message"]),
            "images": i["images"],
            "extra": i["extra"],
        }

        if i["extra"] == 0:
            data.append(temp)
        else:
            tooMuch.append(temp)

        meta.append(
            {
                "title": temp["title"],
                "count": i["extra"] + len(i["images"]),
            }
        )
    except:
        failed.append(i)


print()
if len([*data, *tooMuch]):
    print("Successfully parsed: ")
    for i in [*data, *tooMuch]:
        print(f'{i["title"]}')

if len(failed):
    print("Failed to parse: ")
    for i in failed:
        print(f'{i["message"]}')

os.makedirs("./output", exist_ok=True)

with open("./output/meta.json", "w") as json_file:
    json.dump(meta, json_file, ensure_ascii=False)

print()
print("Only the successfully parsed one will be fetched.")
confirm = input("Fetch images (N): ") or "N"
if confirm.lower() != "y":
    exit(0)

isFailed = False


def fetch_and_save_image(title, url, idx):
    global isFailed

    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        dir = os.path.join("./output", title)

        os.makedirs(dir, exist_ok=True)
        img.save(os.path.join(dir, f"{idx}.webp"), "webp")
        return f"Fetched {title} page {idx}"
    except:
        isFailed = True
        return f"Failed {title} page {idx}"


with ThreadPoolExecutor() as executor:
    futures = []
    for i in [*data, *tooMuch]:
        for idx, url in enumerate(i["images"]):
            futures.append(executor.submit(fetch_and_save_image, i["title"], url, idx))

    for future in as_completed(futures):
        print(future.result())


if len(tooMuch):
    print("Not capturing all images: ")
    for i in tooMuch:
        print(f'{i["title"]} {i["extra"]} more')
    print("Please download it manually before uploading.")
    print("You can run uploader.py directly without fetching the image again.")
    exit(1)


if isFailed:
    print("Some images failed. Please check it manually before uploading.")
    print("You can run uploader.py directly without fetching the image again.")
    exit(1)

print()
upload = input("Upload images (Y): ") or "Y"
if upload.lower() != "y":
    exit(0)

from uploader import upload

upload(config or {})
