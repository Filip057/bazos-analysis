BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "cars" (
	"id"	INTEGER NOT NULL,
	"brand"	VARCHAR(50),
	"model"	VARCHAR(50),
	"year_manufacture"	INTEGER,
	"mileage"	INTEGER,
	"power"	INTEGER,
	"price"	INTEGER,
	PRIMARY KEY("id")
);
INSERT INTO "cars" VALUES (1,'mazda','3',2022,8000,'',499900);
INSERT INTO "cars" VALUES (2,'mazda','3',2022,8000,NULL,499900);
INSERT INTO "cars" VALUES (3,'mazda','CX-5',2018,NULL,143,595000);
INSERT INTO "cars" VALUES (4,'mazda','6',2018,58000,120,799900);
INSERT INTO "cars" VALUES (5,'mazda','CX-3',2015,NULL,143,695000);
COMMIT;
