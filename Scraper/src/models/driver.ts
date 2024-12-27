import { SocksProxyAgent } from "socks-proxy-agent";

import { Manga as MangaModel } from "@prisma/client";

import Manga from "./manga";

class Driver<T extends { id: string } = { id: string }> {
  id: string = "";
  maxTries: number = 5;
  timeout: number = 1000;
  numPerPage: number = 50;
  proxy?: string;
  agent?: SocksProxyAgent;

  setProxy(proxy: string) {
    this.proxy = proxy;
    this.agent = new SocksProxyAgent(proxy);
  }

  async get(id: string): Promise<Manga> {
    return {} as Manga;
  }

  async getTotal(): Promise<number> {
    return 0;
  }

  async getAll(page: number): Promise<string[]> {
    return [];
  }

  async getUpdates(): Promise<T[]> {
    return [];
  }

  async getChapter(id: string, extraData: string): Promise<string[]> {
    return [];
  }

  isEqual(newManga: T, oldManga: MangaModel): boolean {
    return false;
  }

  new(): Driver<T> {
    return new Driver<T>();
  }
}

export default Driver;
