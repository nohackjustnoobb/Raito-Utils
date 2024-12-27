-- CreateTable
CREATE TABLE "WaitingManga" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "tries" INTEGER NOT NULL DEFAULT 0
);

-- CreateTable
CREATE TABLE "Manga" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "title" TEXT NOT NULL,
    "authors" TEXT NOT NULL,
    "genres" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "is_ended" BOOLEAN NOT NULL,
    "latest" TEXT NOT NULL,
    "thumbnail" TEXT NOT NULL,
    "update_time" INTEGER NOT NULL,
    "extra_data" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "Chapter" (
    "manga_id" TEXT NOT NULL,
    "id" TEXT NOT NULL,
    "idx" INTEGER NOT NULL,
    "is_extra" BOOLEAN NOT NULL,
    "title" TEXT NOT NULL,
    "urls" TEXT,
    "tries" INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY ("manga_id", "id"),
    CONSTRAINT "Chapter_manga_id_fkey" FOREIGN KEY ("manga_id") REFERENCES "Manga" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);
