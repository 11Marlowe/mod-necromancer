-- FILE: 20261019210000_char.sql
-- Necromancer (class 10) - refresh saved pets to the batch-4 ability sets.
--
-- Pets that were summoned/tethered before the 2026-10-18 batch 4 keep their
-- old `pet_spell` rows (Ravage 61027 / Entropic Bolt 61041) forever: Tether
-- reuses the saved pet number, so re-tethering does not re-run
-- `InitPetCreateSpells`.  This one-time repair rewrites every class-10
-- character's saved pet spell list from the batch-4 `petcreateinfo_spell`
-- mapping and clears the saved pet action bar so the client rebuilds it.
--
-- Active flags: ACT_ENABLED = 193 (autocast + castable); Pestilence (61069)
-- is passive, ACT_PASSIVE = 1.
--
-- Re-runnable (it always replaces the rows).  Apply to the CHARACTER DB:
--   mariadb --port=3307 -u root tw_char < 20261019210000_char.sql
-- The player must relog for the repaired list to load.

DROP TEMPORARY TABLE IF EXISTS `necromancer_pet_spells`;
CREATE TEMPORARY TABLE `necromancer_pet_spells` (
  `entry`  int(10) unsigned NOT NULL,
  `spell`  int(10) unsigned NOT NULL,
  `active` tinyint(3) unsigned NOT NULL
);

INSERT INTO `necromancer_pet_spells` (`entry`, `spell`, `active`) VALUES
  (846,   61055, 193),   -- Ghoul: Rend
  (846,   61056, 193),   -- Ghoul: Charge
  (846,   61052, 193),   -- Ghoul: Cannibalize
  (1501,  61051, 193),   -- Zombie: Infected Bite
  (1501,  61052, 193),   -- Zombie: Cannibalize
  (1800,  61064, 193),   -- Wraith: Debilitating Touch
  (1800,  61065, 193),   -- Wraith: Shadow Lash
  (1800,  61066, 193),   -- Wraith: Enrage
  (6412,  61057, 193),   -- Skeleton: Strike
  (6412,  61058, 193),   -- Skeleton: Sunder Armor
  (7370,  61053, 193),   -- Shade: Invisibility
  (7370,  61054, 193),   -- Shade: True Sight
  (8526,  61061, 193),   -- Bloodmage: Shadow Bolt
  (8526,  61062, 193),   -- Bloodmage: Soul Tap
  (8526,  61063, 193),   -- Bloodmage: Dispel Magic
  (8545,  61067, 193),   -- Abomination: Taunt
  (8545,  61068, 193),   -- Abomination: Cleave
  (8545,  61052, 193),   -- Abomination: Cannibalize
  (8545,  61069,   1),   -- Abomination: Pestilence (passive)
  (10463, 61059, 193),   -- Banshee: Curse
  (10463, 61060, 193),   -- Banshee: Anti-Magic Shell
  (11621, 61067, 193),   -- Wight: Taunt
  (11621, 61068, 193),   -- Wight: Cleave
  (11621, 61070, 193),   -- Wight: Crowd Pummel
  (11621, 61052, 193);   -- Wight: Cannibalize

DELETE ps
FROM `pet_spell` ps
JOIN `character_pet` cp ON cp.id = ps.guid
JOIN `characters` c ON c.guid = cp.owner
JOIN `necromancer_pet_spells` nps ON nps.entry = cp.entry
WHERE c.class = 10;

INSERT INTO `pet_spell` (`guid`, `spell`, `active`)
SELECT cp.id, nps.spell, nps.active
FROM `character_pet` cp
JOIN `characters` c ON c.guid = cp.owner
JOIN `necromancer_pet_spells` nps ON nps.entry = cp.entry
WHERE c.class = 10;

UPDATE `character_pet` cp
JOIN `characters` c ON c.guid = cp.owner
JOIN `necromancer_pet_spells` nps ON nps.entry = cp.entry
SET cp.abdata = NULL
WHERE c.class = 10;

DROP TEMPORARY TABLE `necromancer_pet_spells`;
