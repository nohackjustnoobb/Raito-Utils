import base64
from io import BytesIO
import json
import os
from PIL import Image
import requests


def upload(config):
    uploadConfig = config.get("upload", {})
    address = uploadConfig.get("address")
    accessKey = uploadConfig.get("accessKey")
    mangaId = uploadConfig.get("mangaId")
    isExtra = uploadConfig.get("isExtra")

    if address is None:
        address = input("Address: ")

    if not address.endswith("/"):
        address += "/"

    if accessKey is None:
        accessKey = input('Access Key (""): ') or ""

    if mangaId is None:
        mangaId = input("Manga Id: ")

    if isExtra is None:
        isExtra = (input("Is Extra (N): ") or "N").lower() == "y"

    print()

    resp = requests.get(
        f"{address}manga",
        params={"ids": mangaId},
        headers={"Access-Key": accessKey},
    )
    if not resp.ok:
        print(f"Failed to fetch manga: {resp.status_code}")
        exit(1)

    print(f'Manga Name: {resp.json()[0]["title"]}')
    confirm = input("Continue (N): ") or "N"

    if confirm.lower() != "y":
        exit(0)

    print()

    base_dir = "./output"
    try:
        with open(os.path.join(base_dir, "meta.json"), "r") as file:
            content = file.read()

        meta = json.loads(content)
        print("Order (from new to old): ")
        for item in meta:
            print(item["title"])
        reverse = input("Reverse (N): ") or "N"
        if reverse.lower() != "y":
            meta.reverse()

        print()
        for item in meta:
            images = []
            item_path = os.path.join(base_dir, item["title"])
            if os.path.isdir(item_path):
                images_path = os.listdir(item_path)
                if len(images_path) != item["count"]:
                    print(f"Page number not matching: {item['title']}")
                    continue

                for file in sorted(images_path):
                    image = Image.open(os.path.join(item_path, file))
                    buffered = BytesIO()
                    image.save(buffered, format="webp")
                    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    images.append(img_str)

            resp = requests.post(
                f"{address}chapters/edit",
                headers={"Access-Key": accessKey},
                json={
                    "title": item["title"],
                    "extraData": mangaId,
                    "isExtra": isExtra,
                },
            )
            if not resp.ok:
                print(f"Failed to create chapter: {resp.status_code}")
                exit(1)

            print(f"Created {item['title']}")
            body = resp.json()["extra" if isExtra else "serial"]
            id = next((x for x in body if x["title"] == item["title"]), None)

            if id is None:
                print(f"Failed to find chapter's id.")
                exit(1)

            id = id["id"]
            resp = requests.post(
                f"{address}image/edit",
                headers={"Access-Key": accessKey},
                params={"id": id, "extra-data": mangaId},
                json=images,
            )
            if not resp.ok:
                print(f"Failed to create chapter: {resp.status_code}")
                exit(1)

            if len(resp.json()) != len(images):
                print(f"Page number not matching: {item['title']}")
            else:
                print(f"Uploaded {item['title']}")

    except FileNotFoundError:
        print("Could not find the output directory.")
        exit(1)


if __name__ == "__main__":
    configFile = input('Config filename ("config.json"): ') or "config.json"
    config = None
    try:
        with open(f"./{configFile}", "r") as file:
            content = file.read()

        config = json.loads(content)
    except:
        pass

    upload(config or {})
