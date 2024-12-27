import * as fs from "fs";
import * as path from "path";
import pino from "pino";
import pretty from "pino-pretty";

import { PrismaClient } from "@prisma/client";

import CPM from "./drivers/cpm";
import MHG from "./drivers/mhg";
import Driver from "./models/driver";
import { sleep as sleep_ } from "./utils";

// Main Loop
async function main() {
  // All available drivers
  const availableDrivers = [new CPM(), new MHG()];

  // Read config.json
  const configPath = path.resolve(__dirname, "../config.json");
  const rawData = fs.readFileSync(configPath, "utf-8");
  const config = JSON.parse(rawData);

  // Setup driver and proxy
  const driver: Driver | undefined = availableDrivers.find(
    (v) => v.id.toLowerCase() === config.driver.toLowerCase()
  );
  if (!driver) throw new Error("Invalid driver");

  const proxies: string[] = config.proxies ?? [];

  const drivers = proxies.map((v) => {
    const newDriver = driver.new();
    newDriver.setProxy(v);
    return newDriver;
  });
  if (!drivers.length) drivers.push(driver);

  // Initialize database
  const prisma = new PrismaClient();
  const stream = pretty({ colorize: true, translateTime: "SYS:standard" });
  const logger = pino({ level: "debug" }, stream);
  const timeout = driver.timeout;
  const sleep = async (timeout: number) => {
    logger.info(`\x1b[90mSleeping for ${timeout}ms`);
    await sleep_(timeout);
  };

  async function checkAndFixMissing() {
    logger.info("Checking missing...");

    const total = await drivers[0].getTotal();
    let dbTotal = Number(
      (
        (await prisma.$queryRaw`
          SELECT COUNT(DISTINCT id) AS total
            FROM (
              SELECT id FROM manga
              UNION ALL
              SELECT id FROM waitingmanga
            )`) as any
      )[0].total
    );

    if (total === dbTotal) return logger.info("No missing");
    logger.info("Fixing missing...");

    async function getAll(driver: Driver, page: number): Promise<string[]> {
      let counter = 0;

      while (counter < driver.maxTries)
        try {
          const result = await driver.getAll(page);
          return result;
        } catch (err) {
          counter++;
        }

      throw new Error("Failed to fix missing");
    }

    let counter = 0;
    while (dbTotal < total) {
      // Check if reached the end
      if (counter * drivers[0].numPerPage >= total)
        throw new Error("Failed to fix missing");

      await sleep(timeout);

      // get all ids
      const promises = [];
      for (const driver of drivers) {
        promises.push(getAll(driver, counter));
        counter++;
      }
      const result = await Promise.all(promises);
      const ids = result.reduce((prev, cur) => [...prev, ...cur]);

      const existingIds = (
        (await prisma.$queryRaw`SELECT DISTINCT id
                                  FROM (
                                    SELECT id FROM manga
                                    UNION ALL
                                    SELECT id FROM waitingmanga
                                  )`) as any
      ).map((v: any) => v.id) as string[];

      const missingIds = ids.filter((v) => !existingIds.includes(v));

      // Add to waiting list
      await prisma.waitingManga.createMany({
        data: missingIds.map((v) => ({ id: v })),
      });

      logger.info(`Found ${missingIds.length} missing`);
      dbTotal += missingIds.length;
    }
  }

  // TODO not tested
  async function checkUpdates() {
    logger.info("Checking updates...");

    const updates = await drivers[0].getUpdates();
    const mangas = await prisma.manga.findMany({
      where: { id: { in: updates.map((v) => v.id) } },
    });

    const filtered = updates.filter((update) => {
      const manga = mangas.find((v) => v.id === update.id);
      return !(manga && drivers[0].isEqual(update, manga));
    });

    const waitingIds = (
      await prisma.waitingManga.findMany({
        select: { id: true },
      })
    ).map((v) => v.id);

    const filteredIds = filtered.filter((v) => !waitingIds.includes(v.id));

    await prisma.waitingManga.createMany({
      data: filteredIds.map((v) => ({ id: v.id })),
    });

    logger.info(`Found ${filteredIds.length} updates`);
  }

  async function getManga(id: string, driver: Driver) {
    try {
      logger.info(`Getting ${id}`);
      const manga = await driver.get(id);
      logger.info(`Saving ${id}`);
      await manga.save();

      await prisma.waitingManga.delete({ where: { id: id } });
    } catch (e) {
      logger.error(`Failed to get ${id}`);
      logger.debug(e);

      await prisma.waitingManga.update({
        where: { id: id },
        data: { tries: { increment: 1 } },
      });
    }
  }

  async function getChapter(
    id: string,
    manga_id: string,
    extraData: string,
    driver: Driver
  ) {
    try {
      logger.info(`Getting ${manga_id}:${id}`);
      const urls = await driver.getChapter(id, extraData);

      await prisma.chapter.update({
        where: { manga_id_id: { id: id, manga_id: manga_id } },
        data: { urls: urls.join("|"), tries: { increment: 1 } },
      });

      logger.info(`Updating ${manga_id}:${id}`);
    } catch (e) {
      logger.error(`Failed to get ${manga_id}:${id}`);
      logger.debug(e);

      await prisma.chapter.update({
        where: { manga_id_id: { id: id, manga_id: manga_id } },
        data: { tries: { increment: 1 } },
      });
    }
  }

  // counter
  let updateCounter = Number.MAX_VALUE;
  let missingCounter = Number.MAX_VALUE;
  // let updateCounter = 0;
  // let missingCounter = 0;

  while (true) {
    await sleep(timeout);
    updateCounter += timeout / 1000;
    missingCounter += timeout / 1000;

    // Run every 24 hours
    if (missingCounter >= 86400) {
      try {
        await checkAndFixMissing();
        missingCounter = 0;
      } catch (e) {
        logger.error("Failed to check and fix missing");
        logger.debug(e);
      }
      continue;
    }

    // Run every 5 minutes
    if (updateCounter >= 300) {
      try {
        await checkUpdates();
        updateCounter = 0;
      } catch (e) {
        logger.error("Failed to check updates");
        logger.debug(e);
      }
      // TODO don't continue if more than 1 driver
      continue;
    }

    // Get manga first
    const mangas = await prisma.waitingManga.findMany({
      take: drivers.length,
      where: { tries: { lt: driver.maxTries } },
    });
    if (mangas.length) {
      const promises = [];

      for (let i = 0; i < mangas.length; i++)
        promises.push(getManga(mangas[i].id, drivers[i]));

      await Promise.all(promises);

      continue;
    }

    // If no manga, get chapter
    const chapters = await prisma.chapter.findMany({
      take: drivers.length,
      select: {
        id: true,
        manga_id: true,
        manga: { select: { extra_data: true } },
      },
      where: {
        OR: [{ urls: null }, { urls: "" }],
        tries: { lt: driver.maxTries },
      },
    });
    if (chapters.length) {
      const promises = [];

      for (let i = 0; i < chapters.length; i++)
        promises.push(
          getChapter(
            chapters[i].id,
            chapters[i].manga_id,
            chapters[i].manga.extra_data,
            drivers[i]
          )
        );

      await Promise.all(promises);

      continue;
    }
  }
}

main();
