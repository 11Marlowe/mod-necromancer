-- FILE: 20261023010000_world.sql
-- Literal restatement of the plague-fidelity rows (same values as
-- 20261023003000_world.sql, idempotent).  turtle-agent's tools/spellnamegen
-- parses spell_template UPDATEs only when the first assignment follows
-- "SET " on the same line and every value is a literal, so the baking step
-- needs this form; the game data is unchanged.

UPDATE `spell_template` SET `school` = 5,
  `attributesEx` = 268435528,
  `recoveryTime` = 8000
WHERE `entry` IN (61019, 61020, 61021);

UPDATE `spell_template` SET `school` = 3,
  `castingTimeIndex` = 1,
  `durationIndex` = 0,
  `recoveryTime` = 30000,
  `effect1` = 3,
  `effectApplyAuraName1` = 0,
  `effectBasePoints1` = 0,
  `effect2` = 0,
  `effectApplyAuraName2` = 0,
  `effectBasePoints2` = 0,
  `effectRadiusIndex2` = 0,
  `effect3` = 0,
  `effectApplyAuraName3` = 0
WHERE `entry` = 61022;

UPDATE `spell_template` SET `recoveryTime` = 0,
  `categoryRecoveryTime` = 0
WHERE `entry` = 61029;
