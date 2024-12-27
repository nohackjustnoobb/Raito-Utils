import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

enum Genre {
  HotBlooded = "HotBlooded",
  Romance = "Romance",
  Campus = "Campus",
  Yuri = "Yuri",
  BL = "BL",
  Adventure = "Adventure",
  Harem = "Harem",
  SciFi = "SciFi",
  War = "War",
  Suspense = "Suspense",
  Speculation = "Speculation",
  Funny = "Funny",
  Fantasy = "Fantasy",
  Magic = "Magic",
  Horror = "Horror",
  Ghosts = "Ghosts",
  Historical = "Historical",
  FanFi = "FanFi",
  Sports = "Sports",
  Hentai = "Hentai",
  Mecha = "Mecha",
  Restricted = "Restricted",
  Otokonoko = "Otokonoko",
}

interface Chapter {
  id: string;
  title: string;
  urls?: Array<string>;
}

interface Chapters {
  extra: Array<Chapter>;
  serial: Array<Chapter>;
  extraData: string;
}

class Manga {
  constructor(
    public id: string,
    public title: string,
    public authors: Array<string>,
    public genres: Array<Genre>,
    public description: string,
    public thumbnail: string,
    public isEnded: boolean,
    public latest: string,
    public updateTime: number,
    public chapters: Chapters
  ) {}

  async save() {
    const manga: any = {};

    for (const [key, value] of Object.entries(this)) {
      switch (key) {
        case "authors":
        case "genres":
          manga[key] = value.join("|");
          break;
        case "isEnded":
        case "updateTime":
          const match = key.match(/([A-Z])/)!;
          manga[key.replace(/([A-Z])/, `_${match[1].toLowerCase()}`)] = value;
          break;
        case "chapters":
          const chapters = value as Chapters;

          manga["extra_data"] = chapters.extraData;
          manga["chapters"] = [
            ...chapters.serial.map((v, i) => ({
              is_extra: false,
              manga_id: this.id,
              idx: i,
              ...v,
            })),
            ...chapters.extra.map((v, i) => ({
              is_extra: true,
              manga_id: this.id,
              idx: i,
              ...v,
            })),
          ];
          break;
        default:
          manga[key] = value;
          break;
      }
    }

    const chapters = manga.chapters;
    delete manga.chapters;

    await prisma.manga.upsert({
      where: { id: this.id },
      create: manga,
      update: manga,
    });

    // remove deleted chapters
    await prisma.chapter.deleteMany({
      where: {
        manga_id: this.id,
        id: { notIn: chapters.map((v: any) => v.id) },
      },
    });

    // get existing chapters
    const existingIds = (
      await prisma.chapter.findMany({
        where: { manga_id: this.id },
        select: { id: true },
      })
    ).map((v) => v.id);

    // save the new chapters
    await prisma.chapter.createMany({
      data: chapters.filter((r: any) => !existingIds.includes(r.id)),
    });
  }
}

export default Manga;
export { Chapter, Chapters, Genre };
