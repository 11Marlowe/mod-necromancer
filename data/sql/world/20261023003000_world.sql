-- FILE: 20261023003000_world.sql
-- Plague fidelity pass (design A.9 Desecration, A.5 Disease Cloud, A.6 Harvest).
--
-- Desecration (61019-21): the channeled Fire Rain-of-Fire scaffold becomes an
-- instant Shadow ground patch (8 s, 8 s cooldown).  The module's aura script
-- wanes the damage over the duration and refreshes the -15% healing debuff
-- (61097) on every victim it ticks on.
UPDATE `spell_template` SET
  `school` = 5,
  `attributesEx` = `attributesEx` & ~68,
  `recoveryTime` = 8000,
  `script_name` = 'spell_necromancer_desecration',
  `description` = 'Desecrates the ground for 8 sec: enemies in the area take Shadow damage every second and receive 15% less healing.  Damage wanes over time.'
WHERE `entry` IN (61019, 61020, 61021);

-- Disease Cloud (61022): instant Nature spell driven by the module script;
-- effect 0 is a dummy that carries the script and the unit target.
UPDATE `spell_template` SET
  `school` = 3,
  `castingTimeIndex` = 1,
  `durationIndex` = 0,
  `recoveryTime` = 30000,
  `effect1` = 3,
  `effectApplyAuraName1` = 0,
  `effectBasePoints1` = 0,
  `effectDieSides1` = 1,
  `effectImplicitTargetA1` = 6,
  `effectAmplitude1` = 0,
  `effect2` = 0,
  `effectApplyAuraName2` = 0,
  `effectBasePoints2` = 0,
  `effectRadiusIndex2` = 0,
  `effect3` = 0,
  `effectApplyAuraName3` = 0,
  `script_name` = 'spell_necromancer_disease_cloud',
  `description` = 'Explodes a victim of your Toxic Plague, dealing one tick of its damage to enemies within 8 yards and inflicting the disease''s total damage as Nature damage over 8 sec.'
WHERE `entry` = 61022;

-- Harvest (61029): design A.6 says no cooldown.
UPDATE `spell_template` SET
  `recoveryTime` = 0,
  `categoryRecoveryTime` = 0
WHERE `entry` = 61029;

-- Hidden helpers (server + client rows).  They are hidden-client-side but not
-- passive, so the module can cast them on enemies (the cast has to announce).
--   61097 Desecration: SPELL_AURA_MOD_HEALING_PCT -15, 8 s
--   61098 Disease Cloud: periodic Nature damage, 8 s at 2 s ticks
--   61099 Disease Cloud: instant Nature damage
DELETE FROM `spell_template` WHERE `entry` IN (61097, 61098, 61099);

DROP TEMPORARY TABLE IF EXISTS `tmp_necro_plague_helper`;
CREATE TEMPORARY TABLE `tmp_necro_plague_helper` AS
  SELECT * FROM `spell_template` WHERE `entry` = 61081;

UPDATE `tmp_necro_plague_helper` SET
  `entry` = 61097,
  `name` = 'Desecration',
  `school` = 5,
  `attributes` = 128,
  `attributesEx` = 0,
  `durationIndex` = 31,
  `manaCost` = 0,
  `recoveryTime` = 0,
  `category` = 0,
  `procFlags` = 0,
  `procChance` = 0,
  `procCharges` = 0,
  `spellIconId` = 1614,
  `description` = '',
  `effect1` = 6,
  `effectApplyAuraName1` = 118,
  `effectBasePoints1` = -16,
  `effectDieSides1` = 1,
  `effectBaseDice1` = 1,
  `effectAmplitude1` = 0,
  `effectImplicitTargetA1` = 6,
  `effectMiscValue1` = 0,
  `effectTriggerSpell1` = 0;
INSERT INTO `spell_template` SELECT * FROM `tmp_necro_plague_helper`;

UPDATE `tmp_necro_plague_helper` SET
  `entry` = 61098,
  `name` = 'Disease Cloud',
  `school` = 3,
  `attributes` = 128,
  `attributesEx` = 0,
  `durationIndex` = 31,
  `manaCost` = 0,
  `recoveryTime` = 0,
  `category` = 0,
  `procFlags` = 0,
  `procChance` = 0,
  `procCharges` = 0,
  `spellIconId` = 1468,
  `description` = '',
  `effect1` = 6,
  `effectApplyAuraName1` = 3,
  `effectBasePoints1` = 0,
  `effectDieSides1` = 1,
  `effectBaseDice1` = 1,
  `effectAmplitude1` = 2000,
  `effectImplicitTargetA1` = 6,
  `effectMiscValue1` = 0,
  `effectTriggerSpell1` = 0;
INSERT INTO `spell_template` SELECT * FROM `tmp_necro_plague_helper`;

UPDATE `tmp_necro_plague_helper` SET
  `entry` = 61099,
  `name` = 'Disease Cloud',
  `school` = 3,
  `attributes` = 128,
  `attributesEx` = 0,
  `durationIndex` = 0,
  `manaCost` = 0,
  `recoveryTime` = 0,
  `category` = 0,
  `procFlags` = 0,
  `procChance` = 0,
  `procCharges` = 0,
  `spellIconId` = 1468,
  `description` = '',
  `effect1` = 2,
  `effectApplyAuraName1` = 0,
  `effectBasePoints1` = 0,
  `effectDieSides1` = 1,
  `effectBaseDice1` = 1,
  `effectAmplitude1` = 0,
  `effectImplicitTargetA1` = 6,
  `effectMiscValue1` = 0,
  `effectTriggerSpell1` = 0;
INSERT INTO `spell_template` SELECT * FROM `tmp_necro_plague_helper`;

DROP TEMPORARY TABLE `tmp_necro_plague_helper`;
