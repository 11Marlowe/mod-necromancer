#!/usr/bin/env python3
"""Generate the T2d Necromancer talent mechanics (proc/conditional passives).

T2d turns the eleven proc/conditional rank spells into real effects:

  Shadowskin, Zombification, Bloodletting, Bloodgorged, Butchery,
  Phantom Armor, Early Grave, Metastasis, Death's Embrace, Icy Talons,
  Wandering Plague.

Data-only: Bloodgorged (melee crit + Reap damage), Butchery (strike damage +
melee-haste proc), Phantom Armor (armor percent), Icy Talons (direct-damage
percent) and the procedure auras for Butchery / Metastasis / Wandering Plague.

Module-applied: Shadowskin (armor-spell bonuses), Zombification (Intellect ->
Strength), Bloodletting (Bloodlet mana), Phantom Armor's conditional damage
reduction, Early Grave (Call of the Grave early triple tick), Death's Embrace
(low-health damage), Icy Talons' Frost Fever haste, and the Wandering Plague
area damage.

Helper spells 61342-61350 are hidden server-side auras/damage spells (they are
not learned or trainer-taught); the module casts them with custom base points.

Run this AFTER the T1 generator/SQL (it updates the rank spells created by
generate_talent_trees.py and needs 61049 in the live DB as the insert model).

Outputs (re-runnable):
  data/sql/world/20261022120000_world.sql
  client/patches/49b-talent-mechanics-t2d.yaml

Usage:
  python tools/generate_talent_mechanics_t2d.py
  python tools/generate_talent_mechanics_t2d.py --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
MODULE_DIR = TOOLS_DIR.parent
SOURCE_DIR = MODULE_DIR.parent.parent
ROOT_DIR = SOURCE_DIR.parent.parent
DATA_DIR = TOOLS_DIR / "data"

sys.path.insert(0, str(TOOLS_DIR))
from generate_talent_trees import query, sql_literal  # noqa: E402

APPLY_AURA = 6
APPLY_FLAT_MODIFIER = 107
APPLY_PCT_MODIFIER = 108
TARGET_UNIT_CASTER = 1
TARGET_UNIT_ENEMY = 6

# Spell aura ids / misc values (SpellAuraDefines.h).
AURA_MOD_RESISTANCE = 22
AURA_MOD_STAT = 29
AURA_PROC_TRIGGER_SPELL = 42
AURA_MOD_CRIT_PERCENT = 52
AURA_MOD_CASTING_SPEED_NOT_STACK = 65
AURA_MOD_DAMAGE_PERCENT_DONE = 79
AURA_MOD_DAMAGE_PERCENT_TAKEN = 87
AURA_MOD_RESISTANCE_PCT = 101
AURA_MOD_MANA_REGEN_INTERRUPT = 134
AURA_MOD_MELEE_HASTE = 138
AURA_MOD_PERIODIC_DAMAGE_PERCENT_TAKEN = 197

# Spell mod ops (SpellDefines.h).
SPELLMOD_DAMAGE = 0

# Spell family 5 flags.
REAP_FLAG = 1048576

# Family-0 flag shared by Plague Strike and Soul Strike (all family-0 class
# spells currently have SpellFamilyFlags 0).
BUTCHERY_FLAG = 1 << 29

# Proc flags (SpellDefines.h).
PROC_FLAG_DEAL_MELEE_SWING = 0x00000004
PROC_FLAG_TAKE_MELEE_SWING = 0x00000008
PROC_FLAG_DEAL_MELEE_ABILITY = 0x00000010
PROC_FLAG_TAKE_MELEE_ABILITY = 0x00000020
PROC_FLAG_DEAL_HARMFUL_SPELL = 0x00010000
PROC_FLAG_DEAL_HARMFUL_PERIODIC = 0x00040000

BUTCHERY_PROC_FLAGS = (PROC_FLAG_DEAL_MELEE_SWING |
                       PROC_FLAG_TAKE_MELEE_SWING |
                       PROC_FLAG_DEAL_MELEE_ABILITY |
                       PROC_FLAG_TAKE_MELEE_ABILITY)

STAT_STRENGTH = 0
SCHOOL_MASK_PHYSICAL = 1
SCHOOL_MASK_MAGIC = 126
SCHOOL_MASK_ALL = 127

PASSIVE_TALENT_ATTRIBUTES = 464
HELPER_ATTRIBUTES = 192          # passive + hidden client-side
DURATION_INFINITE = 21
DURATION_15S = 8
DURATION_10S = 1
DURATION_8S = 31
DURATION_30MIN = 30

HELPER_SPELL_BASE = 61342
HELPER_MODEL_SPELL = 61049       # inert T1 passive (exists in client and DB)

# Talent rank spells (from tools/data/talent-tree-build.json) and their
# mechanics.  Empty effect lists are module-implemented.
TALENT_NAMES = [
    "Shadowskin",
    "Zombification",
    "Bloodletting",
    "Bloodgorged",
    "Butchery",
    "Phantom Armor",
    "Early Grave",
    "Metastasis",
    "Death's Embrace",
    "Icy Talons",
    "Wandering Plague",
]


def effect(aura: int, bases: list[int], misc: int = 0,
           item_type: int = 0) -> dict:
    return {"aura": aura, "bases": bases, "misc": misc, "itemType": item_type}


# Data-only rank-spell effects.  Each bases list has one value per rank.
RANK_EFFECTS: dict[str, list[dict]] = {
    "Bloodgorged": [
        effect(AURA_MOD_CRIT_PERCENT, [0, 1, 2, 3, 4]),
        effect(APPLY_PCT_MODIFIER, [2, 5, 8, 11, 14],
               misc=SPELLMOD_DAMAGE, item_type=REAP_FLAG),
    ],
    "Butchery": [
        effect(APPLY_PCT_MODIFIER, [4, 9],
               misc=SPELLMOD_DAMAGE, item_type=BUTCHERY_FLAG),
        effect(AURA_PROC_TRIGGER_SPELL, [0, 0]),
    ],
    "Phantom Armor": [
        effect(AURA_MOD_RESISTANCE_PCT, [2, 5, 9], misc=SCHOOL_MASK_PHYSICAL),
    ],
    "Icy Talons": [
        effect(AURA_MOD_DAMAGE_PERCENT_DONE, [0, 1, 2, 3, 4],
               misc=SCHOOL_MASK_MAGIC),
    ],
    "Metastasis": [
        effect(AURA_PROC_TRIGGER_SPELL, [0, 0, 0, 0, 0]),
    ],
    "Wandering Plague": [
        effect(AURA_PROC_TRIGGER_SPELL, [0, 0]),
    ],
}

SPELL_FAMILY = {
    "Bloodgorged": 5,
}

# Proc rank spells: proc flags, per-rank proc chance and the module script.
PROC_RANK: dict[str, dict] = {
    "Butchery": dict(flags=BUTCHERY_PROC_FLAGS, chance=[100, 100],
                     script="spell_necromancer_butchery"),
    "Metastasis": dict(flags=PROC_FLAG_DEAL_HARMFUL_SPELL,
                       chance=[20, 40, 60, 80, 100],
                       script="spell_necromancer_metastasis"),
    "Wandering Plague": dict(flags=PROC_FLAG_DEAL_HARMFUL_PERIODIC,
                             chance=[100, 100],
                             script="spell_necromancer_wandering_plague"),
}

# Class spells whose family-0 flags are used by a T2d spell mod.
FLAG_UPDATES = {
    61075: BUTCHERY_FLAG,                       # Plague Strike
    61087: BUTCHERY_FLAG,                       # Soul Strike
}

# Server script_name additions (the client does not store script_name).
SCRIPT_NAMES = {
    61095: "spell_necromancer_frost_fever",
}

# Helper auras: id -> definition.  `effects` is a list of
# (aura, misc, basePoints); missing slots are cleared.  The module normally
# overrides the base points when it casts the helper.
HELPERS: dict[int, dict] = {
    61342: dict(name="Metastasis", icon=1737, duration=DURATION_15S,
                # hidden but not passive: the module applies this debuff to
                # the victim, and passive auras are self-only.
                attributes=0x80, stack=5,
                effects=[(AURA_MOD_PERIODIC_DAMAGE_PERCENT_TAKEN,
                          SCHOOL_MASK_ALL, 2)]),
    61343: dict(name="Icy Talons", icon=119, duration=DURATION_8S,
                attributes=HELPER_ATTRIBUTES, stack=0,
                effects=[(AURA_MOD_CASTING_SPEED_NOT_STACK, 0, 0)]),
    61344: dict(name="Zombification", icon=95, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, stack=0,
                effects=[(AURA_MOD_STAT, STAT_STRENGTH, 0)]),
    61345: dict(name="Butchery", icon=277, duration=DURATION_10S,
                attributes=HELPER_ATTRIBUTES, stack=0,
                effects=[(AURA_MOD_MELEE_HASTE, 0, 0)]),
    61346: dict(name="Shadowskin", icon=178, duration=DURATION_30MIN,
                attributes=HELPER_ATTRIBUTES, stack=0,
                effects=[(AURA_MOD_RESISTANCE, 32, 0)]),
    61347: dict(name="Shadowskin", icon=178, duration=DURATION_30MIN,
                attributes=HELPER_ATTRIBUTES, stack=0,
                effects=[(AURA_MOD_MANA_REGEN_INTERRUPT, 0, 0)]),
    61348: dict(name="Shadowskin", icon=178, duration=DURATION_30MIN,
                attributes=HELPER_ATTRIBUTES, stack=0,
                effects=[(AURA_MOD_RESISTANCE_PCT, SCHOOL_MASK_PHYSICAL, 0)]),
    61349: dict(name="Phantom Armor", icon=178, duration=DURATION_30MIN,
                attributes=HELPER_ATTRIBUTES, stack=0,
                effects=[(AURA_MOD_DAMAGE_PERCENT_TAKEN, SCHOOL_MASK_ALL, -4)]),
}

# Wandering Plague's area-damage helper (a normal instant shadow-damage hit).
DAMAGE_HELPERS: dict[int, dict] = {
    61350: dict(name="Wandering Plague", icon=1468, duration=0,
                attributes=0, school=5),
}

MODULE_TALENTS = {
    "Shadowskin": "armor-spell bonuses (module helper auras)",
    "Zombification": "Intellect -> Strength conversion (module helper aura)",
    "Bloodletting": "Bloodlet mana award (module)",
    "Phantom Armor": "conditional damage reduction while an Armor is active",
    "Early Grave": "Call of the Grave early triple tick (AuraScript)",
    "Death's Embrace": "low-health damage bonus (module hooks)",
    "Icy Talons": "Frost Fever casting-speed buff (AuraScript)",
    "Wandering Plague": "disease-tick area damage (AuraScript)",
    "Butchery": "parry/melee-crit haste proc (AuraScript)",
    "Metastasis": "direct-damage disease amplification (AuraScript)",
}


def load_rank_spells() -> dict[str, list[int]]:
    build = json.loads((DATA_DIR / "talent-tree-build.json").read_text(encoding="utf-8"))
    ranks = {t["name"]: t["ranks"] for t in build["talents"]}
    result: dict[str, list[int]] = {}
    for name in TALENT_NAMES:
        if name not in ranks:
            raise SystemExit(f"talent not found in talent-tree-build.json: {name}")
        spell_ids = ranks[name]
        if not spell_ids:
            raise SystemExit(f"{name}: no rank spells")
        for eff in RANK_EFFECTS.get(name, []):
            if len(eff["bases"]) != len(spell_ids):
                raise SystemExit(
                    f"{name}: {len(eff['bases'])} effect values for "
                    f"{len(spell_ids)} ranks"
                )
        proc = PROC_RANK.get(name)
        if proc and len(proc["chance"]) != len(spell_ids):
            raise SystemExit(
                f"{name}: {len(proc['chance'])} proc chances for "
                f"{len(spell_ids)} ranks"
            )
        result[name] = spell_ids
    return result


def helper_columns(effects: list[tuple[int, int, int]]) -> dict[str, int]:
    """Return the effect columns for a helper spell."""
    cols: dict[str, int] = {}
    for i in range(1, 4):
        index = i - 1
        if index < len(effects):
            aura, misc, base_points = effects[index]
            cols[f"effect{i}"] = APPLY_AURA
            cols[f"effectApplyAuraName{i}"] = aura
            cols[f"effectBasePoints{i}"] = base_points
            cols[f"effectMiscValue{i}"] = misc
            cols[f"effectItemType{i}"] = 0
            cols[f"effectImplicitTargetA{i}"] = TARGET_UNIT_CASTER
            cols[f"effectBaseDice{i}"] = 1
            cols[f"effectDieSides{i}"] = 1
        else:
            cols[f"effect{i}"] = 0
            cols[f"effectApplyAuraName{i}"] = 0
            cols[f"effectBasePoints{i}"] = 0
            cols[f"effectMiscValue{i}"] = 0
            cols[f"effectItemType{i}"] = 0
            cols[f"effectImplicitTargetA{i}"] = 0
            cols[f"effectBaseDice{i}"] = 0
            cols[f"effectDieSides{i}"] = 0
        cols[f"effectImplicitTargetB{i}"] = 0
        cols[f"effectDicePerLevel{i}"] = 0
        cols[f"effectRealPointsPerLevel{i}"] = 0
        cols[f"effectMechanic{i}"] = 0
        cols[f"effectRadiusIndex{i}"] = 0
        cols[f"effectAmplitude{i}"] = 0
        cols[f"effectMultipleValue{i}"] = 0
        cols[f"effectChainTarget{i}"] = 0
        cols[f"effectTriggerSpell{i}"] = 0
        cols[f"effectPointsPerComboPoint{i}"] = 0
        cols[f"effectBonusCoefficient{i}"] = 0
    return cols


def rank_columns(effects: list[dict], rank_index: int) -> dict[str, int]:
    cols = helper_columns([
        (eff["aura"], eff["misc"], eff["bases"][rank_index])
        for eff in effects
    ])
    for i in range(1, 4):
        index = i - 1
        if index < len(effects):
            cols[f"effectItemType{i}"] = effects[index]["itemType"]
    return cols


def emit_sql(path: Path, ranks: dict[str, list[int]], mariadb: str, port: str) -> None:
    cols_types = {
        r[0]: r[1] for r in
        query(mariadb, port, "SHOW COLUMNS FROM `spell_template`")
    }
    donor = query(
        mariadb, port,
        f"SELECT * FROM `spell_template` WHERE `entry` = {HELPER_MODEL_SPELL}"
    )
    if len(donor) != 1:
        raise SystemExit(f"model spell {HELPER_MODEL_SPELL} not found")
    col_names = list(cols_types)
    if len(donor[0]) != len(col_names):
        raise SystemExit("spell_template column/value width mismatch")
    donor_row = dict(zip(col_names, donor[0]))

    lines: list[str] = []
    w = lines.append
    w("-- FILE: 20261022120000_world.sql")
    w("-- Necromancer talent mechanics T2d: proc/conditional passives.")
    w("-- Generated by tools/generate_talent_mechanics_t2d.py; re-runnable.")
    w("--")
    w("-- Module-applied talents:")
    for name, note in MODULE_TALENTS.items():
        w(f"--   {name}: {note}")
    w("")

    # Class-spell family flags / script names.
    w("-- class spells selected by the T2d spell mods / scripts")
    for spell_id, flags in FLAG_UPDATES.items():
        w(f"UPDATE `spell_template` SET `spellFamilyName` = 0, "
          f"`spellFamilyFlags` = {flags} WHERE `entry` = {spell_id};")
    for spell_id, script_name in SCRIPT_NAMES.items():
        escaped = script_name.replace("'", "''")
        w(f"UPDATE `spell_template` SET `script_name` = '{escaped}' "
          f"WHERE `entry` = {spell_id};")
    w("")

    # Remove and re-insert the hidden helper spells (idempotent).
    helper_ids = ", ".join(map(str, HELPERS))
    damage_helper_ids = ", ".join(map(str, DAMAGE_HELPERS))
    w(f"DELETE FROM `spell_template` WHERE `entry` IN "
      f"({helper_ids}, {damage_helper_ids});")
    w("")

    for spell_id, helper in HELPERS.items():
        row = dict(donor_row)
        row.update({
            "entry": spell_id,
            "name": helper["name"],
            "nameSubtext": "",
            "description": "",
            "auraDescription": "",
            "spellIconId": helper["icon"],
            "school": 0,
            "attributes": helper["attributes"],
            "attributesEx": 0, "attributesEx2": 0,
            "attributesEx3": 0, "attributesEx4": 0,
            "stances": 0, "stancesNot": 0,
            "targets": 0, "targetCreatureType": 0,
            "requiresSpellFocus": 0, "casterAuraState": 0, "targetAuraState": 0,
            "castingTimeIndex": 1, "recoveryTime": 0,
            "categoryRecoveryTime": 0, "interruptFlags": 0,
            "auraInterruptFlags": 0, "channelInterruptFlags": 0,
            "procFlags": 0, "procChance": 0, "procCharges": 0,
            "maxLevel": 0, "baseLevel": 0, "spellLevel": 0,
            "durationIndex": helper["duration"],
            "powerType": 0, "manaCost": 0, "manCostPerLevel": 0,
            "manaPerSecond": 0, "manaPerSecondPerLevel": 0,
            "rangeIndex": 0, "speed": 0, "modelNextSpell": 0,
            "stackAmount": helper["stack"], "totem1": 0, "totem2": 0,
            "equippedItemClass": -1, "equippedItemSubClassMask": 0,
            "equippedItemInventoryTypeMask": 0,
            "spellFamilyName": 0, "spellFamilyFlags": 0,
            "spellVisual1": 0, "spellVisual2": 0,
            "activeIconId": 0, "spellPriority": 0,
            "dmgClass": 0, "preventionType": 0, "stanceBarOrder": 0,
            "dmgMultiplier1": 0, "dmgMultiplier2": 0, "dmgMultiplier3": 0,
            "manaCostPercentage": 0, "startRecoveryCategory": 0,
            "startRecoveryTime": 0, "minTargetLevel": 0, "maxTargetLevel": 0,
            "maxAffectedTargets": 0, "minFactionId": 0, "minReputation": 0,
            "requiredAuraVision": 0, "customFlags": 0,
            "script_name": "",
        })
        for i in range(1, 9):
            row[f"reagent{i}"] = 0
            row[f"reagentCount{i}"] = 0
        row.update(helper_columns(helper["effects"]))
        values = [sql_literal(row[c], cols_types[c]) for c in col_names]
        w(f"INSERT INTO `spell_template` (`{'`, `'.join(col_names)}`) VALUES")
        w("  (" + ", ".join(values) + ");")
        w("")

    for spell_id, helper in DAMAGE_HELPERS.items():
        row = dict(donor_row)
        row.update({
            "entry": spell_id,
            "name": helper["name"],
            "nameSubtext": "",
            "description": "",
            "auraDescription": "",
            "spellIconId": helper["icon"],
            "school": helper["school"],
            "attributes": helper["attributes"],
            "attributesEx": 0, "attributesEx2": 0,
            "attributesEx3": 0, "attributesEx4": 0,
            "stances": 0, "stancesNot": 0,
            "targets": 0, "targetCreatureType": 0,
            "requiresSpellFocus": 0, "casterAuraState": 0, "targetAuraState": 0,
            "castingTimeIndex": 1, "recoveryTime": 0,
            "categoryRecoveryTime": 0, "interruptFlags": 0,
            "auraInterruptFlags": 0, "channelInterruptFlags": 0,
            "procFlags": 0, "procChance": 0, "procCharges": 0,
            "maxLevel": 0, "baseLevel": 0, "spellLevel": 0,
            "durationIndex": helper["duration"],
            "powerType": 0, "manaCost": 0, "manCostPerLevel": 0,
            "manaPerSecond": 0, "manaPerSecondPerLevel": 0,
            "rangeIndex": 0, "speed": 0, "modelNextSpell": 0,
            "stackAmount": 0, "totem1": 0, "totem2": 0,
            "equippedItemClass": -1, "equippedItemSubClassMask": 0,
            "equippedItemInventoryTypeMask": 0,
            "spellFamilyName": 0, "spellFamilyFlags": 0,
            "spellVisual1": 0, "spellVisual2": 0,
            "activeIconId": 0, "spellPriority": 0,
            "dmgClass": 0, "preventionType": 0, "stanceBarOrder": 0,
            "dmgMultiplier1": 0, "dmgMultiplier2": 0, "dmgMultiplier3": 0,
            "manaCostPercentage": 0, "startRecoveryCategory": 0,
            "startRecoveryTime": 0, "minTargetLevel": 0, "maxTargetLevel": 0,
            "maxAffectedTargets": 0, "minFactionId": 0, "minReputation": 0,
            "requiredAuraVision": 0, "customFlags": 0,
            "script_name": "",
        })
        for i in range(1, 9):
            row[f"reagent{i}"] = 0
            row[f"reagentCount{i}"] = 0
        row.update({
            "effect1": 2,  # SPELL_EFFECT_SCHOOL_DAMAGE
            "effectApplyAuraName1": 0,
            "effectBasePoints1": 0,
            "effectMiscValue1": 0,
            "effectItemType1": 0,
            "effectImplicitTargetA1": TARGET_UNIT_ENEMY,
            "effectBaseDice1": 1,
            "effectDieSides1": 1,
            "effectImplicitTargetB1": 0,
            "effectDicePerLevel1": 0,
            "effectRealPointsPerLevel1": 0,
            "effectMechanic1": 0,
            "effectRadiusIndex1": 0,
            "effectAmplitude1": 0,
            "effectMultipleValue1": 0,
            "effectChainTarget1": 0,
            "effectTriggerSpell1": 0,
            "effectPointsPerComboPoint1": 0,
            "effectBonusCoefficient1": 0,
        })
        for i in range(2, 4):
            row[f"effect{i}"] = 0
            row[f"effectApplyAuraName{i}"] = 0
            row[f"effectBasePoints{i}"] = 0
            row[f"effectMiscValue{i}"] = 0
            row[f"effectItemType{i}"] = 0
            row[f"effectImplicitTargetA{i}"] = 0
            row[f"effectBaseDice{i}"] = 0
            row[f"effectDieSides{i}"] = 0
            row[f"effectImplicitTargetB{i}"] = 0
            row[f"effectDicePerLevel{i}"] = 0
            row[f"effectRealPointsPerLevel{i}"] = 0
            row[f"effectMechanic{i}"] = 0
            row[f"effectRadiusIndex{i}"] = 0
            row[f"effectAmplitude{i}"] = 0
            row[f"effectMultipleValue{i}"] = 0
            row[f"effectChainTarget{i}"] = 0
            row[f"effectTriggerSpell{i}"] = 0
            row[f"effectPointsPerComboPoint{i}"] = 0
            row[f"effectBonusCoefficient{i}"] = 0
        values = [sql_literal(row[c], cols_types[c]) for c in col_names]
        w(f"INSERT INTO `spell_template` (`{'`, `'.join(col_names)}`) VALUES")
        w("  (" + ", ".join(values) + ");")
        w("")

    # Rank spells.
    for name in TALENT_NAMES:
        rank_spells = ranks[name]
        effects = RANK_EFFECTS.get(name, [])
        family = SPELL_FAMILY.get(name, 0)
        proc = PROC_RANK.get(name)
        w(f"-- {name}")
        for rank_index, spell_id in enumerate(rank_spells):
            updates: dict[str, int] = {
                "attributes": PASSIVE_TALENT_ATTRIBUTES,
                "spellFamilyName": family,
                "spellFamilyFlags": 0,
                "equippedItemClass": -1,
                "equippedItemSubClassMask": 0,
                "equippedItemInventoryTypeMask": 0,
            }
            updates.update(rank_columns(effects, rank_index))

            if proc:
                updates.update({
                    "procFlags": proc["flags"],
                    "procChance": proc["chance"][rank_index],
                    "procCharges": 0,
                    "script_name": proc["script"],
                })
            else:
                updates.update({
                    "procFlags": 0,
                    "procChance": 0,
                    "procCharges": 0,
                    "script_name": "",
                })

            assignments = ", ".join(
                f"`{k}` = " + (f"'{v}'" if isinstance(v, str) else str(v))
                for k, v in updates.items()
            )
            w(f"UPDATE `spell_template` SET {assignments} WHERE `entry` = {spell_id};")
        w("")

    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def u32(value: int) -> int:
    return value & 0xFFFFFFFF


def emit_client_yaml(path: Path, ranks: dict[str, list[int]]) -> None:
    lines: list[str] = []
    w = lines.append
    w("# Talent mechanics T2d - generated by tools/generate_talent_mechanics_t2d.py.")
    w("# Turns the eleven proc/conditional rank spells into real effects and")
    w("# adds the hidden helpers 61342-61350.")
    w("# Loads after 49-talent-mechanics-t2c.yaml.")
    w("")
    w("Spell.dbc:")

    for spell_id, flags in FLAG_UPDATES.items():
        w("  - type: update")
        w(f"    key: {spell_id}")
        w("    values:")
        w("      SpellClassSet: 0")
        w(f"      SpellClassMask_1: {u32(flags)}")
        w("      SpellClassMask_2: 0")

    for spell_id, script_name in SCRIPT_NAMES.items():
        # script_name is server-only; no client field.
        pass

    # Hidden helper aura spells (copied from the T1 inert passive 61049).
    for spell_id, helper in HELPERS.items():
        w("  - type: copy")
        w(f"    key: {HELPER_MODEL_SPELL}")
        w("    values:")
        w(f"      ID: {spell_id}")
        for i in range(8):
            w(f"      Name_lang_{i}: {json.dumps(helper['name'])}")
        for i in range(8):
            w(f"      NameSubtext_lang_{i}: \"\"")
            w(f"      Description_lang_{i}: \"\"")
            w(f"      AuraDescription_lang_{i}: \"\"")
        w(f"      SpellIconID: {helper['icon']}")
        w(f"      Attributes: {helper['attributes']}")
        w("      AttributesEx: 0")
        w("      AttributesEx2: 0")
        w("      AttributesEx3: 0")
        w("      AttributesEx4: 0")
        w("      ShapeshiftMask: 0")
        w("      ShapeshiftExclude: 0")
        w("      Targets: 0")
        w("      TargetCreatureType: 0")
        w("      CastingTimeIndex: 1")
        w("      RecoveryTime: 0")
        w("      CategoryRecoveryTime: 0")
        w("      InterruptFlags: 0")
        w("      AuraInterruptFlags: 0")
        w("      ChannelInterruptFlags: 0")
        w("      ProcTypeMask: 0")
        w("      ProcChance: 0")
        w("      ProcCharges: 0")
        w(f"      DurationIndex: {helper['duration']}")
        w(f"      StackAmount: {helper['stack']}")
        w("      PowerType: 0")
        w("      ManaCost: 0")
        w("      RangeIndex: 0")
        w("      EquippedItemClass: 4294967295")
        w("      EquippedItemSubclass: 0")
        w("      EquippedItemInvType: 0")
        w("      SpellClassSet: 0")
        w("      SpellClassMask_1: 0")
        w("      SpellClassMask_2: 0")
        cols = helper_columns(helper["effects"])
        for i in range(1, 4):
            w(f"      Effect_{i}: {cols[f'effect{i}']}")
            w(f"      EffectAura_{i}: {cols[f'effectApplyAuraName{i}']}")
            w(f"      EffectBasePoints_{i}: {u32(cols[f'effectBasePoints{i}'])}")
            w(f"      EffectMiscValue_{i}: {cols[f'effectMiscValue{i}']}")
            w(f"      EffectItemType_{i}: {u32(cols[f'effectItemType{i}'])}")
            w(f"      ImplicitTargetA_{i}: {cols[f'effectImplicitTargetA{i}']}")
            w(f"      EffectBaseDice_{i}: {cols[f'effectBaseDice{i}']}")
            w(f"      EffectDieSides_{i}: {cols[f'effectDieSides{i}']}")
        w("")

    # Hidden area-damage helper.
    for spell_id, helper in DAMAGE_HELPERS.items():
        w("  - type: copy")
        w(f"    key: {HELPER_MODEL_SPELL}")
        w("    values:")
        w(f"      ID: {spell_id}")
        for i in range(8):
            w(f"      Name_lang_{i}: {json.dumps(helper['name'])}")
        for i in range(8):
            w(f"      NameSubtext_lang_{i}: \"\"")
            w(f"      Description_lang_{i}: \"\"")
            w(f"      AuraDescription_lang_{i}: \"\"")
        w(f"      SpellIconID: {helper['icon']}")
        w(f"      Attributes: {helper['attributes']}")
        w("      AttributesEx: 0")
        w("      AttributesEx2: 0")
        w("      AttributesEx3: 0")
        w("      AttributesEx4: 0")
        w("      ShapeshiftMask: 0")
        w("      ShapeshiftExclude: 0")
        w(f"      School: {helper['school']}")
        w("      Targets: 0")
        w("      TargetCreatureType: 0")
        w("      CastingTimeIndex: 1")
        w("      RecoveryTime: 0")
        w("      CategoryRecoveryTime: 0")
        w("      InterruptFlags: 0")
        w("      AuraInterruptFlags: 0")
        w("      ChannelInterruptFlags: 0")
        w("      ProcTypeMask: 0")
        w("      ProcChance: 0")
        w("      ProcCharges: 0")
        w("      DurationIndex: 0")
        w("      StackAmount: 0")
        w("      PowerType: 0")
        w("      ManaCost: 0")
        w("      RangeIndex: 0")
        w("      EquippedItemClass: 4294967295")
        w("      EquippedItemSubclass: 0")
        w("      EquippedItemInvType: 0")
        w("      SpellClassSet: 0")
        w("      SpellClassMask_1: 0")
        w("      SpellClassMask_2: 0")
        w("      Effect_1: 2")
        w("      EffectAura_1: 0")
        w("      EffectBasePoints_1: 0")
        w("      EffectMiscValue_1: 0")
        w("      EffectItemType_1: 0")
        w(f"      ImplicitTargetA_1: {TARGET_UNIT_ENEMY}")
        w("      EffectBaseDice_1: 1")
        w("      EffectDieSides_1: 1")
        for i in range(2, 4):
            w(f"      Effect_{i}: 0")
            w(f"      EffectAura_{i}: 0")
            w(f"      EffectBasePoints_{i}: 0")
            w(f"      EffectMiscValue_{i}: 0")
            w(f"      EffectItemType_{i}: 0")
            w(f"      ImplicitTargetA_{i}: 0")
            w(f"      EffectBaseDice_{i}: 0")
            w(f"      EffectDieSides_{i}: 0")
        w("")

    # Rank spells.
    for name in TALENT_NAMES:
        effects = RANK_EFFECTS.get(name, [])
        family = SPELL_FAMILY.get(name, 0)
        proc = PROC_RANK.get(name)
        for rank_index, spell_id in enumerate(ranks[name]):
            cols = rank_columns(effects, rank_index)
            w("  - type: update")
            w(f"    key: {spell_id}")
            w("    values:")
            w(f"      Attributes: {PASSIVE_TALENT_ATTRIBUTES}")
            w(f"      SpellClassSet: {family}")
            w("      SpellClassMask_1: 0")
            w("      SpellClassMask_2: 0")
            w("      EquippedItemClass: 4294967295")
            w("      EquippedItemSubclass: 0")
            w("      EquippedItemInvType: 0")
            if proc:
                w(f"      ProcTypeMask: {proc['flags']}")
                w(f"      ProcChance: {proc['chance'][rank_index]}")
                w("      ProcCharges: 0")
            else:
                w("      ProcTypeMask: 0")
                w("      ProcChance: 0")
                w("      ProcCharges: 0")
            for i in range(1, 4):
                w(f"      Effect_{i}: {cols[f'effect{i}']}")
                w(f"      EffectAura_{i}: {cols[f'effectApplyAuraName{i}']}")
                w(f"      EffectBasePoints_{i}: {u32(cols[f'effectBasePoints{i}'])}")
                w(f"      EffectMiscValue_{i}: {cols[f'effectMiscValue{i}']}")
                w(f"      EffectItemType_{i}: {u32(cols[f'effectItemType{i}'])}")
                w(f"      ImplicitTargetA_{i}: {cols[f'effectImplicitTargetA{i}']}")
                w(f"      EffectBaseDice_{i}: {cols[f'effectBaseDice{i}']}")
                w(f"      EffectDieSides_{i}: {cols[f'effectDieSides{i}']}")
                w(f"      ImplicitTargetB_{i}: 0")
                w(f"      EffectDicePerLevel_{i}: 0")
                w(f"      EffectRealPointsPerLevel_{i}: 0")
                w(f"      EffectMechanic_{i}: 0")
                w(f"      EffectRadiusIndex_{i}: 0")
                w(f"      EffectAmplitude_{i}: 0")
                w(f"      EffectMultipleValue_{i}: 0")
                w(f"      EffectChainTarget_{i}: 0")
                w(f"      EffectTriggerSpell_{i}: 0")
                w(f"      EffectPointsPerCombo_{i}: 0")
            w("")

    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb",
                    default=str(ROOT_DIR / "server/mariadb-portable/bin/mariadb.exe"))
    ap.add_argument("--port", default="3307")
    ap.add_argument("--apply", action="store_true",
                    help="apply the generated world SQL")
    args = ap.parse_args()

    ranks = load_rank_spells()
    out_sql = MODULE_DIR / "data/sql/world/20261022120000_world.sql"
    out_yaml = MODULE_DIR / "client/patches/49b-talent-mechanics-t2d.yaml"

    emit_sql(out_sql, ranks, args.mariadb, args.port)
    emit_client_yaml(out_yaml, ranks)

    print(f"T2d talents: {len(ranks)} | rank spells: "
          f"{sum(len(v) for v in ranks.values())} | helpers: "
          f"{len(HELPERS) + len(DAMAGE_HELPERS)}",
          file=sys.stderr)
    print(f"wrote {out_sql}", file=sys.stderr)
    print(f"wrote {out_yaml}", file=sys.stderr)

    if args.apply:
        with open(out_sql, "r", encoding="utf-8") as f:
            subprocess.run(
                [args.mariadb, f"--port={args.port}", "-u", "root", "tw_world"],
                stdin=f, check=True,
            )
        print(f"applied {out_sql.name} -> tw_world", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
