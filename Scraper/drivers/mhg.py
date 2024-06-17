import json
import requests
from bs4 import BeautifulSoup
import lzstring
import time
import re

from models.driver import Driver
from models.manga import *

lz = lzstring.LZString()


def get(url, proxy):
    try:
        res = requests.get(
            url,
            timeout=5,
            proxies={"https": proxy},
        )
    except:
        return False
    m = re.match(r"^.*\}\(\'(.*)\',(\d*),(\d*),\'([\w|\+|\/|=]*)\'.*$", res.text)
    return packed(
        m.group(1),
        int(m.group(2)),
        int(m.group(3)),
        lz.decompressFromBase64(m.group(4)).split("|"),
    )


# parse.py
def packed(functionFrame, a, c, data):
    def e(innerC):
        return ("" if innerC < a else e(int(innerC / a))) + (
            chr(innerC % a + 29) if innerC % a > 35 else tr(innerC % a, 36)
        )

    c -= 1
    d = {}
    while c + 1:
        d[e(c)] = e(c) if data[c] == "" else data[c]
        c -= 1
    pieces = re.split(r"(\b\w+\b)", functionFrame)
    js = (
        "".join([d[x] if x in d else x for x in pieces])
        .replace("\\'", "'")
        .replace('\\"', '"')
    )
    return json.loads(re.search(r"^.*\((\{.*\})\).*$", js).group(1))


# tran.py
def itr(value, num):
    d = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "" if value <= 0 else itr(int(value / num), num) + d[value % num]


def tr(value, num):
    tmp = itr(value, num)
    return "0" if tmp == "" else tmp


class MHG(Driver):
    identifier = "MHG"
    timeout = 10
    initId = 1
    categories = {
        "rexue": Manga.categories_list[0],
        "aiqing": Manga.categories_list[1],
        "xiaoyuan": Manga.categories_list[2],
        "baihe": Manga.categories_list[3],
        "danmei": Manga.categories_list[4],
        "maoxian": Manga.categories_list[5],
        "hougong": Manga.categories_list[6],
        "kehuan": Manga.categories_list[7],
        "zhanzheng": Manga.categories_list[8],
        "xuanyi": Manga.categories_list[9],
        "tuili": Manga.categories_list[10],
        "gaoxiao": Manga.categories_list[11],
        "mohuan": Manga.categories_list[12],
        "mofa": Manga.categories_list[13],
        "kongbu": Manga.categories_list[14],
        "shengui": Manga.categories_list[15],
        "lishi": Manga.categories_list[16],
        "jingji": Manga.categories_list[18],
        "jizhan": Manga.categories_list[20],
        "weiniang": Manga.categories_list[22],
    }

    def get(self, id: int, proxy: str):
        response = requests.get(
            f"https://tw.manhuagui.com/comic/{id}/",
            proxies={"https": proxy},
            timeout=5,
        )

        if response.status_code != 200:
            raise

        soup = BeautifulSoup(response.text, "lxml")

        thumbnail = soup.find("p", class_="hcover")
        is_ended = "finish" in thumbnail.find_all("span")[-1]["class"]
        thumbnail = "https:" + thumbnail.find("img")["src"]

        title = soup.find("div", class_="book-title").find("h1").text.strip()
        info = soup.find("ul", class_="detail-list cf").find_all("li")
        categories = [
            MHG.categories[i["href"][6:-1]]
            for i in info[1].find("span").find_all("a")
            if i["href"][6:-1] in MHG.categories.keys()
        ]
        authors = [i.text.strip() for i in info[1].find_all("span")[1].find_all("a")]
        description = soup.find("div", id="intro-cut").text.strip()
        latest = soup.find("div", class_="chapter-bar").find("a").text.strip()

        tryAdult = soup.find("input", id="__VIEWSTATE")
        if tryAdult:
            chapter_list = BeautifulSoup(
                lzstring.LZString().decompressFromBase64(tryAdult.attrs.get("value")),
                "lxml",
            ).find_all("div", class_="chapter-list")
        else:
            chapter_list = soup.find_all("div", class_="chapter-list")

        def extract_chapter(raw):
            try:
                chapters = []
                for i in reversed(raw.find_all("ul")):
                    for j in i.find_all("a"):
                        chapters.append(
                            Chapter(
                                title=j["title"].strip(),
                                id=re.search("(\\d+)\\.html", j["href"]).group(1),
                            )
                        )
                return chapters
            except:
                return []

        serial = extract_chapter(chapter_list[0])
        extra = []
        for i in chapter_list[1:]:
            extra.extend(extract_chapter(i))

        manga = Manga(
            id=str(id),
            chapters=Chapters(serial=serial, extra=extra, extra_data=str(id)),
            thumbnail=thumbnail,
            title=title,
            latest=latest,
            authors=authors,
            description=description,
            is_ended=is_ended,
            categories=categories,
            update_time=time.time(),
        )

        return manga

    def next(self, id: int):
        return id + 1

    def get_update(self, proxy: str):
        response = requests.get(
            "https://tw.manhuagui.com/update/d1.html",
            proxies={"https": proxy},
            timeout=5,
        )
        soup = BeautifulSoup(response.text, "lxml")
        update = soup.find("div", class_="latest-cont").find_all("li")

        result = []
        for i in update:
            id = re.search("\/(\d+)\/", i.find("a")["href"]).group(1)
            latest = (
                i.find("span", class_="tt")
                .text.replace("更新至", "")
                .replace("共", "")
                .strip()
            )

            result.append(PreviewManga(id=id, latest=latest))

        return result

    def get_chapter(self, id, extra_data, proxy):
        details = get(f"https://tw.manhuagui.com/comic/{extra_data}/{id}.html", proxy)
        urls = list(
            map(
                lambda x: f"https://i.hamreus.com{details['path']}{x}", details["files"]
            )
        )

        return urls

    def is_same(self, val1, val2):
        return val1.replace("第", "") == val2.replace("第", "")
