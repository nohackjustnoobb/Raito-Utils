import fetch from "node-fetch";

import { Manga as MangaModel } from "@prisma/client";

import Driver from "../models/driver";
import Manga, { Chapter, Chapters, Genre } from "../models/manga";
import { sleep } from "../utils";

interface PreviewManga {
  id: string;
  updateTime: number;
}

class CPM extends Driver<PreviewManga> {
  id = "CPM";
  maxTries = 3;
  static baseUrl = "https://api.copymanga.tv/api/v3";
  static genresMapping: { [key: string]: Genre } = {
    aiqing: Genre.Romance,
    huanlexiang: Genre.Funny,
    maoxian: Genre.Adventure,
    qihuan: Genre.Fantasy,
    xiaoyuan: Genre.Campus,
    baihe: Genre.Yuri,
    kehan: Genre.SciFi,
    xuanyi: Genre.Speculation,
    rexue: Genre.HotBlooded,
    hougong: Genre.Harem,
    zhanzheng: Genre.War,
    lishi: Genre.Historical,
  };

  async fetch(url: string): Promise<any> {
    const resp = await fetch(`${CPM.baseUrl}${url}`, { agent: this.agent });
    const json = (await resp.json()) as any;

    if (!resp.ok || json.code !== 200)
      throw new Error(`Failed to fetch. Code ${json.code}\n${json}`);

    return json.results;
  }

  async get(id: string) {
    const results = await this.fetch(`/comic2/${id}?platform=3`);

    const comic = results.comic;

    const genres = [];
    for (const genre of comic.theme) {
      if (CPM.genresMapping[genre.path_word]) {
        genres.push(CPM.genresMapping[genre.path_word]);
      }
    }

    const chapters: Chapters = {
      extra: [],
      serial: [],
      extraData: comic.path_word,
    };

    const fetchChapters = async (
      name: string,
      count: number
    ): Promise<Chapter[]> => {
      let counter = 0;
      const chapters: Array<Chapter> = [];

      while (counter * 500 < count) {
        await sleep(this.timeout);

        const results = await this.fetch(
          `/comic/${comic.path_word}/group/${name}/chapters?limit=500&offset=${counter}&platform=3`
        );

        for (const chapter of results.list)
          chapters.push({ id: chapter.uuid, title: chapter.name });

        counter++;
      }

      return chapters;
    };

    const groups = results.groups;
    const count = groups["default"].count;
    chapters.serial = await fetchChapters("default", count);

    delete groups["default"];
    for (const group of Object.values(groups) as any)
      chapters.extra.push(
        ...(await fetchChapters(group.path_word, group.count))
      );

    return new Manga(
      comic.path_word,
      comic.name,
      comic.author.map((v: any) => v.name),
      genres,
      comic.brief,
      comic.cover,
      comic.status.value === 1,
      comic.last_chapter.name,
      Math.floor(new Date(comic.datetime_updated).getTime() / 1000),
      chapters
    );
  }

  async getTotal() {
    const results = await this.fetch("/comics?limit=1&platform=3");

    return results.total;
  }

  async getMangas(page: number): Promise<any> {
    return (
      await this.fetch(
        `/comics?limit=${this.numPerPage}&offset=${
          page * this.numPerPage
        }&platform=3`
      )
    ).list;
  }

  async getAll(page: number) {
    return (await this.getMangas(page)).map((v: any) => v.path_word);
  }

  async getUpdates() {
    const results = [];

    results.push(...(await this.getMangas(0)));
    await sleep(this.timeout);
    results.push(...(await this.getMangas(1)));

    return results.map((v: any) => ({
      id: v.path_word,
      updateTime: Math.floor(new Date(v.datetime_updated).getTime() / 1000),
    }));
  }

  async getChapter(id: string, extraData: string) {
    const results = await this.fetch(
      `/comic/${extraData}/chapter2/${id}?platform=3`
    );

    return results.chapter.contents.map((v: any) => v.url);
  }

  isEqual(newManga: PreviewManga, oldManga: MangaModel) {
    return newManga.updateTime === oldManga.update_time;
  }

  new() {
    return new CPM();
  }
}

export default CPM;
