-- Still Here: the analysis, run in Snowflake.
--
-- The corpus is 99,905 completed dog stays at Austin Animal Center going back
-- to 2013, plus the 516 dogs that currently have an intake row and no outcome
-- row. Every number quoted on the site and in the writeup comes from one of the
-- views below.
--
-- Bully-type is a coat-and-jaw folk category, not a genetic one. It is defined
-- here exactly as the site defines it, in one place, so the definition is
-- auditable rather than buried in application code.

-- ---------------------------------------------------------------------------
-- 0. Structure
-- ---------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS STILL_HERE;
USE DATABASE STILL_HERE;
CREATE SCHEMA IF NOT EXISTS SHELTER;
USE SCHEMA SHELTER;

CREATE TABLE IF NOT EXISTS DOG_STAYS (
  ERA              STRING,       -- 'archive' (2013-2025) or 'live' (2025-now)
  ANIMAL_ID        STRING,
  NAME             STRING,
  BREED            STRING,
  COLOR            STRING,
  INTAKE_DATE      DATE,
  OUTCOME_DATE     DATE,
  DAYS_IN_SHELTER  NUMBER,
  OUTCOME_STATUS   STRING,
  ADOPTED          NUMBER,
  INTAKE_TYPE      STRING,
  INTAKE_CONDITION STRING
);

CREATE TABLE IF NOT EXISTS DOGS_WAITING (
  ANIMAL_ID       STRING,
  NAME            STRING,
  BREED           STRING,
  RAW_BREED       STRING,
  COLOR           STRING,
  SECONDARY_COLOR STRING,
  SEX             STRING,
  IS_PUPPY        NUMBER,
  INTAKE_DATE     DATE,
  DAYS_WAITING    NUMBER,
  INTAKE_REASON   STRING,
  HEALTH          STRING,
  DATE_OF_BIRTH   STRING
);

-- ---------------------------------------------------------------------------
-- 1. The one definition everything else depends on
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION IS_BULLY(BREED STRING)
RETURNS BOOLEAN
AS
$$
  LOWER(BREED) LIKE '%pit bull%'
  OR LOWER(BREED) LIKE '%staffordshire%'
  OR LOWER(BREED) LIKE '%american bulldog%'
$$;

CREATE OR REPLACE VIEW ADOPTIONS AS
SELECT
  *,
  IS_BULLY(BREED) AS BULLY
FROM DOG_STAYS
WHERE ADOPTED = 1
  AND DAYS_IN_SHELTER BETWEEN 0 AND 3650;

-- ---------------------------------------------------------------------------
-- 2. The headline. Bully-type dogs against everyone else.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW HEADLINE AS
SELECT
  IFF(BULLY, 'Bully-type', 'Everyone else')      AS GROUP_NAME,
  COUNT(*)                                        AS N,
  MEDIAN(DAYS_IN_SHELTER)                         AS MEDIAN_DAYS,
  ROUND(AVG(DAYS_IN_SHELTER), 1)                  AS MEAN_DAYS,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY DAYS_IN_SHELTER) AS P90_DAYS
FROM ADOPTIONS
GROUP BY BULLY;

-- ---------------------------------------------------------------------------
-- 3. The myth. Median wait by coat colour, uncontrolled.
--    This is the table that makes people believe in black dog syndrome, and
--    on its own it does look like colour is doing the work.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW BY_COLOR AS
SELECT
  COLOR,
  COUNT(*)                                    AS N,
  MEDIAN(DAYS_IN_SHELTER)                     AS MEDIAN_DAYS,
  ROUND(100.0 * AVG(IFF(BULLY, 1, 0)))        AS PCT_BULLY
FROM ADOPTIONS
GROUP BY COLOR
HAVING COUNT(*) >= 400
ORDER BY MEDIAN_DAYS DESC;

-- ---------------------------------------------------------------------------
-- 4. The answer. The same colours, split by breed type.
--    A colour needs 250 adoptions on BOTH sides of the split to appear: at a
--    lower floor a 35-dog cell sets the reported spread and the comparison
--    stops meaning anything.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW BY_COLOR_CONTROLLED AS
SELECT
  COLOR,
  COUNT_IF(BULLY)                                            AS N_BULLY,
  MEDIAN(CASE WHEN BULLY THEN DAYS_IN_SHELTER END)           AS BULLY_MEDIAN,
  COUNT_IF(NOT BULLY)                                        AS N_OTHER,
  MEDIAN(CASE WHEN NOT BULLY THEN DAYS_IN_SHELTER END)       AS OTHER_MEDIAN
FROM ADOPTIONS
GROUP BY COLOR
HAVING COUNT_IF(BULLY) >= 250 AND COUNT_IF(NOT BULLY) >= 250
ORDER BY BULLY_MEDIAN DESC;

-- How much does colour move the wait once breed is held still, against how
-- much breed moves it? This single row is the finding.
CREATE OR REPLACE VIEW SPREAD AS
SELECT
  MAX(BULLY_MEDIAN) - MIN(BULLY_MEDIAN)  AS COLOUR_SPREAD_WITHIN_BULLY,
  MAX(OTHER_MEDIAN) - MIN(OTHER_MEDIAN)  AS COLOUR_SPREAD_WITHIN_OTHER,
  MIN(BULLY_MEDIAN) - MAX(OTHER_MEDIAN)  AS WORST_CASE_GAP_BETWEEN_GROUPS
FROM BY_COLOR_CONTROLLED;

-- ---------------------------------------------------------------------------
-- 5. Breeds, for every breed with enough adoptions to be worth quoting
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW BY_BREED AS
SELECT
  BREED,
  IS_BULLY(BREED)           AS BULLY,
  COUNT(*)                  AS N,
  MEDIAN(DAYS_IN_SHELTER)   AS MEDIAN_DAYS
FROM ADOPTIONS
GROUP BY BREED
HAVING COUNT(*) >= 400
ORDER BY MEDIAN_DAYS DESC;

-- ---------------------------------------------------------------------------
-- 6. The 516. For each dog still waiting, where its current wait falls in the
--    distribution of completed stays for its own breed group.
--
--    This is the number on every card: "99.7% of similar dogs were home by
--    now". It is a rank of one live value against 51,404 historical ones, which
--    is the part that actually wants a warehouse rather than a spreadsheet.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW WAITING_RANKED AS
WITH COHORT AS (
  SELECT BULLY, DAYS_IN_SHELTER FROM ADOPTIONS
),
W AS (
  SELECT *, IS_BULLY(COALESCE(RAW_BREED, BREED)) AS BULLY FROM DOGS_WAITING
)
SELECT
  W.ANIMAL_ID,
  W.NAME,
  W.RAW_BREED                                   AS BREED,
  W.COLOR,
  W.INTAKE_DATE,
  W.DAYS_WAITING,
  W.BULLY,
  (SELECT MEDIAN(DAYS_IN_SHELTER) FROM COHORT C WHERE C.BULLY = W.BULLY)
                                                AS COHORT_MEDIAN,
  ROUND(
    100.0 * (SELECT COUNT(*) FROM COHORT C
             WHERE C.BULLY = W.BULLY AND C.DAYS_IN_SHELTER <= W.DAYS_WAITING)
          / (SELECT COUNT(*) FROM COHORT C WHERE C.BULLY = W.BULLY)
  , 1)                                          AS PCT_OF_COHORT_HOME_BY_NOW
FROM W
ORDER BY W.DAYS_WAITING DESC;

-- ---------------------------------------------------------------------------
-- 7. What the site and the writeup actually print
-- ---------------------------------------------------------------------------
SELECT * FROM HEADLINE;
SELECT * FROM BY_COLOR;
SELECT * FROM BY_COLOR_CONTROLLED;
SELECT * FROM SPREAD;
SELECT * FROM BY_BREED LIMIT 14;
SELECT * FROM WAITING_RANKED LIMIT 12;

-- Who is still in the building, grouped the way the shelter would think of it.
SELECT
  IFF(BULLY, 'Bully-type', 'Everyone else') AS GROUP_NAME,
  COUNT(*)                                   AS DOGS_WAITING,
  MEDIAN(DAYS_WAITING)                       AS MEDIAN_DAYS_SO_FAR,
  COUNT_IF(DAYS_WAITING >= 365)              AS OVER_A_YEAR
FROM WAITING_RANKED
GROUP BY BULLY;
