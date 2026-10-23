-- FILE: 20261022223000_world.sql
-- Bone Armor (61015): the design's four bone shields (A.6), implemented with
-- the engine's own charge handling (the Lightning Shield pattern).
--   effect 0: SPELL_AURA_PROC_TRIGGER_SPELL, procFlags = taken melee/ranged
--             swing or ability (680), procChance 100, procCharges 4.  One
--             charge per qualifying hit; the core removes the whole aura (all
--             three effects) when the last shield breaks.
--   effect 1: SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN -20 on the physical school
--             mask: 20% less physical damage while a shield remains
--             (placeholder for the design's X).
--   effect 2: SPELL_AURA_RESIST_PUSHBACK 70: 70% chance to ignore spell
--             pushback while a shield remains.
-- effectBasePoints stores amount - 1 (EffectDieSides 1): 70 -> 69, -20 -> -21.
--
-- 61096 is the hidden, effect-less proc trigger.  It needs a server row for
-- the proc handler and a client row (SPELL_GO is still sent for a triggered
-- cast even though the spell is hidden client-side).

DELETE FROM `spell_template` WHERE `entry` = 61096;

DROP TEMPORARY TABLE IF EXISTS `tmp_necro_bone_shield`;
CREATE TEMPORARY TABLE `tmp_necro_bone_shield` AS
  SELECT * FROM `spell_template` WHERE `entry` = 61341;
UPDATE `tmp_necro_bone_shield` SET
  `entry` = 61096,
  `name` = 'Bone Shield',
  `attributes` = 128,
  `attributesEx` = 0,
  `durationIndex` = 0,
  `procFlags` = 0,
  `procChance` = 0,
  `procCharges` = 0,
  `manaCost` = 0,
  `recoveryTime` = 0,
  `category` = 0,
  `spellIconId` = 1614,
  `description` = '',
  `effect1` = 0,
  `effect2` = 0,
  `effect3` = 0,
  `effectApplyAuraName1` = 0,
  `effectApplyAuraName2` = 0,
  `effectApplyAuraName3` = 0,
  `effectBasePoints1` = 0,
  `effectBasePoints2` = 0,
  `effectBasePoints3` = 0,
  `effectDieSides1` = 1,
  `effectDieSides2` = 1,
  `effectDieSides3` = 1,
  `effectImplicitTargetA1` = 0,
  `effectImplicitTargetA2` = 0,
  `effectImplicitTargetA3` = 0,
  `effectMiscValue1` = 0,
  `effectMiscValue2` = 0,
  `effectMiscValue3` = 0,
  `effectTriggerSpell1` = 0,
  `effectTriggerSpell2` = 0,
  `effectTriggerSpell3` = 0;
INSERT INTO `spell_template` SELECT * FROM `tmp_necro_bone_shield`;
DROP TEMPORARY TABLE `tmp_necro_bone_shield`;

UPDATE `spell_template` SET
  `procFlags` = 680,
  `procChance` = 100,
  `procCharges` = 4,
  `effect1` = 6,
  `effectApplyAuraName1` = 42,
  `effectBasePoints1` = 0,
  `effectDieSides1` = 1,
  `effectBaseDice1` = 1,
  `effectImplicitTargetA1` = 1,
  `effectMiscValue1` = 0,
  `effectTriggerSpell1` = 61096,
  `effect2` = 6,
  `effectApplyAuraName2` = 87,
  `effectBasePoints2` = -21,
  `effectDieSides2` = 1,
  `effectBaseDice2` = 1,
  `effectImplicitTargetA2` = 1,
  `effectMiscValue2` = 1,
  `effectTriggerSpell2` = 0,
  `effect3` = 6,
  `effectApplyAuraName3` = 149,
  `effectBasePoints3` = 69,
  `effectDieSides3` = 1,
  `effectBaseDice3` = 1,
  `effectImplicitTargetA3` = 1,
  `effectMiscValue3` = 0,
  `effectTriggerSpell3` = 0,
  `description` = 'Surrounds you with 4 bone shields, reducing physical damage taken by 20% and pushback suffered by 70%.  Each melee or ranged hit consumes a shield.  Only one Armor spell can be active.  Lasts $d.'
WHERE `entry` = 61015;
