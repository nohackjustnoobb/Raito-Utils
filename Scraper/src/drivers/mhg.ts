import { decompressFromBase64 } from "lz-string";
import fetch from "node-fetch";
import { HTMLElement, parse } from "node-html-parser";

import { Manga as MangaModel } from "@prisma/client";

import Driver from "../models/driver";
import Manga, { Chapter, Genre } from "../models/manga";

interface PreviewManga {
  id: string;
  latest: string;
}

class MHG extends Driver<PreviewManga> {
  id = "MHG";
  timeout = 5000;
  numPerPage = 42;
  static baseUrl = "https://tw.manhuagui.com";
  static imageBaseUrl = "https://i.hamreus.com";
  static genresMapping: { [key: string]: Genre } = {
    rexue: Genre.HotBlooded,
    aiqing: Genre.Romance,
    xiaoyuan: Genre.Campus,
    baihe: Genre.Yuri,
    danmei: Genre.BL,
    maoxian: Genre.Adventure,
    hougong: Genre.Harem,
    kehuan: Genre.SciFi,
    zhanzheng: Genre.War,
    xuanyi: Genre.Suspense,
    tuili: Genre.Speculation,
    gaoxiao: Genre.Funny,
    mohuan: Genre.Fantasy,
    mofa: Genre.Magic,
    kongbu: Genre.Horror,
    shengui: Genre.Ghosts,
    lishi: Genre.Historical,
    jingji: Genre.Sports,
    jizhan: Genre.Mecha,
    weiniang: Genre.Otokonoko,
  };

  async fetch(url: string): Promise<HTMLElement> {
    const resp = await fetch(`${MHG.baseUrl}${url}`, { agent: this.agent });
    const doc = parse(await resp.text());

    if (!resp.ok) throw new Error(`Failed to fetch. Code ${resp.status}`);

    return doc;
  }

  async get(id: string): Promise<Manga> {
    const doc = await this.fetch(`/comic/${id}`);

    const thumbnailContainer = doc.querySelector("p.hcover")!;
    const isEned = thumbnailContainer
      .getElementsByTagName("span")
      .at(-1)!
      .classList.contains("finish");
    const thumbnail = `https:${thumbnailContainer
      .getElementsByTagName("img")[0]
      .getAttribute("src")!}`;

    const title = doc.querySelector("div.book-title > h1")!.textContent.trim();

    const infoContainer = doc.querySelector(
      "ul.detail-list.cf > li:nth-child(2)"
    )!;

    const genres: Genre[] = [];
    for (const genre of infoContainer.querySelectorAll("span:first-child a")) {
      const match = genre.getAttribute("href")?.match(/\/list\/(.*)\//);
      if (match && MHG.genresMapping[match[1]])
        genres.push(MHG.genresMapping[match[1]]);
    }
    const authors = infoContainer
      .querySelectorAll("span:last-child a")
      .map((e) => e.textContent.trim());
    const description = doc.getElementById("intro-cut")!.textContent.trim();
    const latest = doc.querySelector("div.chapter-bar a")!.textContent.trim();
    const updateTime = Math.floor(
      new Date(
        doc
          .querySelectorAll("div.chapter-bar > span > span")[1]
          .textContent.trim()
      ).getTime() / 1000
    );

    let chaptersList = doc.querySelectorAll("div.chapter-list");

    const tryAdult = doc.querySelector("input#__VIEWSTATE");
    if (tryAdult) {
      chaptersList = parse(
        decompressFromBase64(tryAdult.getAttribute("value")!).toString()
      ).querySelectorAll("div.chapter-list");
    }

    function extractChapters(elem: HTMLElement): Array<Chapter> {
      const chapters: Array<Chapter> = [];

      for (const ul of elem.getElementsByTagName("ul").reverse()) {
        for (const link of ul.getElementsByTagName("a")) {
          try {
            chapters.push({
              title: link.getAttribute("title")!.trim(),
              id: link
                .getAttribute("href")!
                .match(/\/comic\/.*\/(.*).html/)![1],
            });
          } catch {}
        }
      }

      return chapters.reverse();
    }

    const serial = extractChapters(chaptersList[0]);
    chaptersList.shift();
    const extra = chaptersList
      .map((v) => extractChapters(v))
      .reduce((prev, v) => [...prev, ...v], []);

    return new Manga(
      id,
      title,
      authors,
      genres,
      description,
      thumbnail,
      isEned,
      latest,
      updateTime,
      { serial, extra, extraData: id }
    );
  }

  async getTotal() {
    const doc = await this.fetch("/list");

    return Number(
      doc.querySelector("div.result-count strong:last-child")!.textContent
    );
  }

  async getAll(page: number) {
    const doc = await this.fetch(`/list/index_p${page + 1}.html`);

    return doc
      .querySelectorAll("#contList a.bcover")
      .map((v) => v.getAttribute("href")!.match(/\/comic\/(.*)\//)![1]);
  }

  async getUpdates() {
    const doc = await this.fetch("/update/d30.html");

    return doc.querySelectorAll("div.latest-list li").map((v) => ({
      id: v
        .querySelector("a.cover")!
        .getAttribute("href")!
        .match(/\/comic\/(.*)\//)![1],
      latest: v.querySelector("a.cover")!.textContent.replace(/更新至|共/, ""),
    }));
  }

  async getChapter(id: string, extraData: string) {
    const doc = await this.fetch(`/comic/${extraData}/${id}.html`);

    const raw = doc.querySelector("script:not([src])[type]")!.textContent;
    const rawCode = raw.match(/(\(.*\))/)![1];

    // Replace splic with parsed and split
    const regex = new RegExp(
      /\'([-A-Za-z0-9+\/]*={0,3})\'\['\\x73\\x70\\x6c\\x69\\x63'\]/
    );
    const match = rawCode.match(regex)!;
    const replaced = rawCode.replace(
      regex,
      `${JSON.stringify(decompressFromBase64(match[1]))}.split`
    );

    // extract the arguments
    const parsed = (0, eval)(replaced) as string;
    const json = JSON.parse(parsed.match(/\((\{.*\})\)/)![1]);

    return json.files.map((v: string) => `${MHG.imageBaseUrl}${json.path}${v}`);
  }

  isEqual(newManga: PreviewManga, oldManga: MangaModel) {
    function normalize(str: string) {
      return str.replace("/第| .*/g", "").trim();
    }

    return normalize(oldManga.latest) === normalize(newManga.latest);
  }

  new() {
    return new MHG();
  }
}

export default MHG;
