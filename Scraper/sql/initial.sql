CREATE TABLE IF NOT EXISTS CHAPTER (
    CHAPTERS_ID INTEGER NOT NULL,
    ID VARCHAR(255) NOT NULL,
    IDX INTEGER NOT NULL,
    TITLE VARCHAR(255) NOT NULL,
    IS_EXTRA BOOLEAN NOT NULL,
    URLS TEXT,
    FOREIGN KEY (CHAPTERS_ID) REFERENCES CHAPTERS(ID)
);

CREATE TABLE IF NOT EXISTS CHAPTERS (
    MANGA_ID VARCHAR(255) PRIMARY KEY,
    EXTRA_DATA VARCHAR(255),
    FOREIGN KEY (MANGA_ID) REFERENCES MANGA(ID)
);

CREATE TABLE IF NOT EXISTS MANGA(
    ID VARCHAR(255) PRIMARY KEY,
    THUMBNAIL VARCHAR(255) NOT NULL,
    TITLE VARCHAR(255) NOT NULL,
    DESCRIPTION TEXT NOT NULL,
    IS_END BOOLEAN NOT NULL,
    AUTHORS VARCHAR(255) NOT NULL,
    CATEGORIES VARCHAR(255) NOT NULL,
    LATEST VARCHAR(255) NOT NULL,
    UPDATE_TIME INTEGER(255) NOT NULL
);