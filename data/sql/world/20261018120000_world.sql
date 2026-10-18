-- FILE: 20261018120000_world.sql
-- Necromancer (class 10) batch 3 slice 3c follow-up: the Raise spell
-- descriptions now state the corpse/bag requirement (user request
-- 2026-10-18).  Server-side descriptions only; the client text lives in
-- client/patches/40-spells.yaml (patch-Z rebuilt separately).

UPDATE `spell_template` SET `description` =
  'Raises a ghoul to fight for you for $d. Requires a humanoid or ghoul corpse nearby, or 1 Lump of Flesh.'
  WHERE `entry` = 61024;

UPDATE `spell_template` SET `description` =
  'Raises a skeleton to fight for you for $d. Requires a humanoid or non-spectral undead corpse nearby, or 1 Pile of Bones.'
  WHERE `entry` = 61025;

UPDATE `spell_template` SET `description` =
  'Raises a zombie to fight for you for $d. Requires a humanoid or zombie corpse nearby, or 1 Lump of Flesh.'
  WHERE `entry` = 61034;

UPDATE `spell_template` SET `description` =
  'Raises a shade to fight for you for $d. Requires a humanoid, undead, demon, beast, giant or dragonkin corpse nearby, or 1 Ectoplasm.'
  WHERE `entry` = 61035;

UPDATE `spell_template` SET `description` =
  'Raises a banshee to fight for you for $d. Requires a female humanoid or banshee corpse nearby, or 1 Banshee Essence.'
  WHERE `entry` = 61036;

UPDATE `spell_template` SET `description` =
  'Raises a wraith to fight for you for $d. Requires a humanoid, undead, demon, beast, giant or dragonkin corpse nearby, or 1 Ectoplasm. Only one wraith at a time.'
  WHERE `entry` = 61037;

UPDATE `spell_template` SET `description` =
  'Raises a bloodmage to fight for you for $d. Requires a humanoid or non-spectral undead corpse nearby, or 1 Pile of Bones. Only one bloodmage at a time.'
  WHERE `entry` = 61038;

UPDATE `spell_template` SET `description` =
  'Raises an abomination to fight for you for $d. Requires three humanoid, undead or giant corpses nearby, or 3 Lumps of Flesh. Only one abomination at a time.'
  WHERE `entry` = 61039;

UPDATE `spell_template` SET `description` =
  'Transforms your Zombie or Ghoul minion into a Wight that will fight for you for 1 min. If used on a Tethered minion, the minion will remain Tethered. Only one Wight or Abomination can be active at a time.'
  WHERE `entry` = 61040;
