-- FILE: 20261020090000_char.sql
-- Necromancer three-tab spellbook split (A87, 2026-10-19): existing class-10
-- characters already know skill 700 (Reanimation); grant the new Blood (701)
-- and Plague (702) skill lines so the client shows all three tabs.  New
-- characters learn them from the rank-1 starting spells.
-- Re-runnable.

INSERT IGNORE INTO `character_skills` (`guid`, `skill`, `value`, `max`)
SELECT `guid`, 700, 1, 1 FROM `characters` WHERE `class` = 10;

INSERT IGNORE INTO `character_skills` (`guid`, `skill`, `value`, `max`)
SELECT c.`guid`, 701, COALESCE(cs.`value`, 1), COALESCE(cs.`max`, 1)
FROM `characters` c
LEFT JOIN `character_skills` cs ON cs.`guid` = c.`guid` AND cs.`skill` = 700
WHERE c.`class` = 10;

INSERT IGNORE INTO `character_skills` (`guid`, `skill`, `value`, `max`)
SELECT c.`guid`, 702, COALESCE(cs.`value`, 1), COALESCE(cs.`max`, 1)
FROM `characters` c
LEFT JOIN `character_skills` cs ON cs.`guid` = c.`guid` AND cs.`skill` = 700
WHERE c.`class` = 10;
