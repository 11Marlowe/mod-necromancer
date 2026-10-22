#!/usr/bin/env python3
"""Generate the T2c Necromancer talent mechanics (minion/pet passives).

T2c turns the nine minion/pet rank spells from inert placeholders into real
effects:

  Running Dead, Unnatural Life, Solitude, Graverobbing, Unholy Power,
  Piercing Fingers, Undead Domination, Retained Intellect, Twisted Bond.

Only Unnatural Life's player Stamina bonus and Twisted Bond's player proc aura
are data-only.  The other effects are applied by the module: minion auras are
cast on the pet when it enters the world, while Solitude / Unholy Power modify
damage in the shared UnitScript hook.

Helper spells 61331-61341 are hidden server-side auras (they are not learned
or trainer-taught); the module casts them with custom base points.

Run this AFTER the T1 generator/SQL (it updates the rank spells created by
generate_talent_trees.py and needs 61049 in the live DB as the insert model).

Outputs (re-runnable):
  data/sql/world/20261021180000_world.sql
  client/patches/49-talent-mechanics-t2c.yaml

Usage:
  python tools/generate_talent_mechanics_t2c.py
  python tools/generate_talent_mechanics_t2c.py --apply
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
TARGET_UNIT_CASTER = 1

# Aura ids / misc values (SpellAuraDefines.h).
AURA_DUMMY = 4
AURA_MOD_STAT = 29
AURA_MOD_INCREASE_SPEED = 31
AURA_PROC_TRIGGER_SPELL = 42
AURA_MOD_HIT_CHANCE = 54
AURA_MOD_SPELL_HIT_CHANCE = 55
AURA_MOD_SPELL_CRIT_CHANCE = 57
AURA_MOD_CASTING_SPEED_NOT_STACK = 65
AURA_MOD_DAMAGE_PERCENT_DONE = 79
AURA_MOD_MANA_REGEN_INTERRUPT = 134
AURA_MOD_TOTAL_STAT_PERCENTAGE = 137
AURA_MOD_MELEE_HASTE = 138
AURA_MOD_CRIT_PERCENT_VERSUS = 169
AURA_ADD_FLAT_MODIFIER = 107
AURA_ADD_PCT_MODIFIER = 108

SPELLMOD_CASTING_TIME = 10
SPELLMOD_COST = 14

STAT_STAMINA = 2
STAT_INTELLECT = 3

SCHOOL_MASK_ALL = 127
SCHOOL_MASK_MAGIC = 126
CREATURE_TYPEMASK_ALL = 0x7FFFFFFF

# T2b's family-0 flag for the Raise spells.
RAISE_FLAG = 1 << 27

PROC_FLAG_DEAL_MELEE_SWING = 0x00000004
PROC_FLAG_DEAL_MELEE_ABILITY = 0x00000010
PROC_FLAG_DEAL_HARMFUL_ABILITY = 0x00001000
PROC_FLAG_DEAL_HARMFUL_SPELL = 0x00010000
PROC_FLAGS_PLAYER = PROC_FLAG_DEAL_HARMFUL_ABILITY | PROC_FLAG_DEAL_HARMFUL_SPELL
PROC_FLAGS_MINION = (PROC_FLAG_DEAL_MELEE_SWING | PROC_FLAG_DEAL_MELEE_ABILITY |
                     PROC_FLAG_DEAL_HARMFUL_ABILITY | PROC_FLAG_DEAL_HARMFUL_SPELL)

PASSIVE_TALENT_ATTRIBUTES = 464
HELPER_ATTRIBUTES = 192          # passive + hidden client-side
DURATION_INFINITE = 21
DURATION_8S = 31
DURATION_10MIN = 6

HELPER_SPELL_BASE = 61331
HELPER_MODEL_SPELL = 61049       # inert T1 passive (exists in client and DB)

# Talent rank spells (from tools/data/talent-tree-build.json) and their
# mechanics.  Empty effect lists are module-implemented.
TALENT_NAMES = [
    "Running Dead",
    "Unnatural Life",
    "Solitude",
    "Graverobbing",
    "Unholy Power",
    "Piercing Fingers",
    "Undead Domination",
    "Retained Intellect",
    "Twisted Bond",
]

# Helper spells: id -> definition.  `effects` is a list of
# (aura, misc, itemType, basePoints); missing slots are cleared.
HELPERS: dict[int, dict] = {
    61331: dict(name="Running Dead", icon=9, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_INCREASE_SPEED, 0, 0, 0)]),
    61332: dict(name="Unnatural Life", icon=134, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_STAT, STAT_STAMINA, 0, 0)]),
    61333: dict(name="Graverobbing", icon=695, duration=DURATION_8S,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_MELEE_HASTE, 0, 0, 3),
                         (AURA_MOD_CASTING_SPEED_NOT_STACK, 0, 0, 3),
                         (AURA_MOD_INCREASE_SPEED, 0, 0, 3)]),
    61334: dict(name="Piercing Fingers", icon=2214, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_HIT_CHANCE, 0, 0, 0),
                         (AURA_MOD_CRIT_PERCENT_VERSUS, CREATURE_TYPEMASK_ALL, 0, 0)]),
    61335: dict(name="Piercing Fingers", icon=2214, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_SPELL_HIT_CHANCE, 0, 0, 0),
                         (AURA_MOD_SPELL_CRIT_CHANCE, 0, 0, 0)]),
    61336: dict(name="Retained Intellect", icon=119, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_STAT, STAT_INTELLECT, 0, 0),
                         (AURA_MOD_MANA_REGEN_INTERRUPT, 0, 0, 0)]),
    61337: dict(name="Twisted Bond", icon=164, duration=DURATION_8S,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_DAMAGE_PERCENT_DONE, SCHOOL_MASK_ALL, 0, 0)]),
    61338: dict(name="Twisted Bond", icon=164, duration=DURATION_8S,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_MOD_DAMAGE_PERCENT_DONE, SCHOOL_MASK_MAGIC, 0, 0)]),
    61339: dict(name="Twisted Bond", icon=164, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, procFlags=PROC_FLAGS_MINION,
                effects=[(AURA_PROC_TRIGGER_SPELL, 0, 0, 0)],
                script_name="spell_necromancer_twisted_bond_minion"),
    61340: dict(name="Undead Domination", icon=88, duration=DURATION_INFINITE,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_ADD_FLAT_MODIFIER, SPELLMOD_CASTING_TIME, RAISE_FLAG, -3001),
                         (AURA_ADD_PCT_MODIFIER, SPELLMOD_COST, RAISE_FLAG, -61)]),
    61341: dict(name="Undead Domination", icon=88, duration=DURATION_10MIN,
                attributes=HELPER_ATTRIBUTES, procFlags=0,
                effects=[(AURA_DUMMY, 0, 0, 0)],
                script_name="spell_necromancer_undead_domination_cd"),
}

# Data-only rank-spell effects.  Each bases list has one value per rank.
RANK_EFFECTS: dict[str, list[tuple[int, int, int, list[int]]]] = {
    "Unnatural Life": [
        (AURA_MOD_TOTAL_STAT_PERCENTAGE, STAT_STAMINA, 0, [1, 3, 5, 7, 9]),
    ],
    "Twisted Bond": [
        (AURA_PROC_TRIGGER_SPELL, 0, 0, [0, 0, 0]),
    ],
}

# Twisted Bond's player aura is a proc trigger (its OnProc is a module script).
PROC_RANK_TALENTS = {"Twisted Bond"}
TWISTED_BOND_SCRIPT = "spell_necromancer_twisted_bond_player"

MODULE_TALENTS = {
    "Running Dead": "minion movement speed aura (PetScript)",
    "Unnatural Life": "minion Stamina aura (PetScript); player Stamina is data",
    "Solitude": "damage bonus while no minion is active (UnitScript)",
    "Graverobbing": "8 s haste buff after Harvest/Raise (module)",
    "Unholy Power": "minion damage bonus (UnitScript)",
    "Piercing Fingers": "minion hit/crit auras + tethered inheritance (PetScript)",
    "Undead Domination": "next-Raise cast/cost buff + 10 min cooldown (module)",
    "Retained Intellect": "minion Intellect/regen aura (PetScript)",
    "Twisted Bond": "crit procs between the player and minions (AuraScript)",
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
        for _aura, _misc, _item_type, bases in RANK_EFFECTS.get(name, []):
            if len(bases) != len(spell_ids):
                raise SystemExit(
                    f"{name}: {len(bases)} effect values for {len(spell_ids)} ranks"
                )
        result[name] = spell_ids
    return result


def helper_columns(effects: list[tuple[int, int, int, int]]) -> dict[str, int]:
    """Return the effect columns for a rank/helper spell."""
    cols: dict[str, int] = {}
    for i in range(1, 4):
        index = i - 1
        if index < len(effects):
            aura, misc, item_type, base_points = effects[index]
            cols[f"effect{i}"] = APPLY_AURA
            cols[f"effectApplyAuraName{i}"] = aura
            cols[f"effectBasePoints{i}"] = base_points
            cols[f"effectMiscValue{i}"] = misc
            cols[f"effectItemType{i}"] = item_type
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
    w("-- FILE: 20261021180000_world.sql")
    w("-- Necromancer talent mechanics T2c: minion/pet passives.")
    w("-- Generated by tools/generate_talent_mechanics_t2c.py; re-runnable.")
    w("--")
    w("-- Module-applied talents:")
    for name, note in MODULE_TALENTS.items():
        w(f"--   {name}: {note}")
    w("")

    # Remove and re-insert the hidden helper spells (idempotent).
    helper_ids = ", ".join(map(str, HELPERS))
    w(f"DELETE FROM `spell_template` WHERE `entry` IN ({helper_ids});")
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
            "attributes": helper["attributes"],
            "attributesEx": 0, "attributesEx2": 0,
            "attributesEx3": 0, "attributesEx4": 0,
            "stances": 0, "stancesNot": 0,
            "targets": 0, "targetCreatureType": 0,
            "requiresSpellFocus": 0, "casterAuraState": 0, "targetAuraState": 0,
            "castingTimeIndex": 1, "recoveryTime": 0,
            "categoryRecoveryTime": 0, "interruptFlags": 0,
            "auraInterruptFlags": 0, "channelInterruptFlags": 0,
            "procFlags": helper["procFlags"],
            "procChance": 100 if helper["procFlags"] else 0,
            "procCharges": 0, "maxLevel": 0, "baseLevel": 0, "spellLevel": 0,
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
            "script_name": helper.get("script_name", ""),
        })
        for i in range(1, 9):
            row[f"reagent{i}"] = 0
            row[f"reagentCount{i}"] = 0
        row.update(helper_columns([
            (aura, misc, item_type, bp)
            for aura, misc, item_type, bp in helper["effects"]
        ]))
        values = [sql_literal(row[c], cols_types[c]) for c in col_names]
        w(f"INSERT INTO `spell_template` (`{'`, `'.join(col_names)}`) VALUES")
        w("  (" + ", ".join(values) + ");")
        w("")

    # Rank spells.
    for name in TALENT_NAMES:
        rank_spells = ranks[name]
        effects = RANK_EFFECTS.get(name, [])
        w(f"-- {name}")
        for rank_index, spell_id in enumerate(rank_spells):
            rank_effects = [
                (aura, misc, item_type, bases[rank_index])
                for aura, misc, item_type, bases in effects
            ]
            updates: dict[str, int] = {
                "attributes": PASSIVE_TALENT_ATTRIBUTES,
                "spellFamilyName": 0,
                "spellFamilyFlags": 0,
                "equippedItemClass": -1,
                "equippedItemSubClassMask": 0,
                "equippedItemInventoryTypeMask": 0,
            }
            updates.update(helper_columns(rank_effects))

            if name in PROC_RANK_TALENTS:
                updates.update({
                    "procFlags": PROC_FLAGS_PLAYER,
                    "procChance": 100,
                    "procCharges": 0,
                    "script_name": TWISTED_BOND_SCRIPT,
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
    w("# Talent mechanics T2c - generated by tools/generate_talent_mechanics_t2c.py.")
    w("# Turns the nine minion/pet rank spells into real effects and adds the")
    w("# hidden helper auras 61331-61341.")
    w("# Loads after 48-talent-mechanics-t2b.yaml.")
    w("")
    w("Spell.dbc:")

    # Hidden helper spells (copied from the T1 inert passive 61049).
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
        w(f"      ProcTypeMask: {helper['procFlags']}")
        w(f"      ProcChance: {100 if helper['procFlags'] else 0}")
        w("      ProcCharges: 0")
        w(f"      DurationIndex: {helper['duration']}")
        w("      PowerType: 0")
        w("      ManaCost: 0")
        w("      RangeIndex: 0")
        w("      StackAmount: 0")
        w("      EquippedItemClass: 4294967295")
        w("      EquippedItemSubclass: 0")
        w("      EquippedItemInvType: 0")
        w("      SpellClassSet: 0")
        w("      SpellClassMask_1: 0")
        w("      SpellClassMask_2: 0")
        cols = helper_columns([
            (aura, misc, item_type, bp)
            for aura, misc, item_type, bp in helper["effects"]
        ])
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

    # Rank spells.
    for name in TALENT_NAMES:
        effects = RANK_EFFECTS.get(name, [])
        for rank_index, spell_id in enumerate(ranks[name]):
            rank_effects = [
                (aura, misc, item_type, bases[rank_index])
                for aura, misc, item_type, bases in effects
            ]
            cols = helper_columns(rank_effects)
            w("  - type: update")
            w(f"    key: {spell_id}")
            w("    values:")
            w(f"      Attributes: {PASSIVE_TALENT_ATTRIBUTES}")
            w("      SpellClassSet: 0")
            w("      SpellClassMask_1: 0")
            w("      SpellClassMask_2: 0")
            w("      EquippedItemClass: 4294967295")
            w("      EquippedItemSubclass: 0")
            w("      EquippedItemInvType: 0")
            if name in PROC_RANK_TALENTS:
                w(f"      ProcTypeMask: {PROC_FLAGS_PLAYER}")
                w("      ProcChance: 100")
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
    out_sql = MODULE_DIR / "data/sql/world/20261021180000_world.sql"
    out_yaml = MODULE_DIR / "client/patches/49-talent-mechanics-t2c.yaml"

    emit_sql(out_sql, ranks, args.mariadb, args.port)
    emit_client_yaml(out_yaml, ranks)

    print(f"T2c talents: {len(ranks)} | rank spells: "
          f"{sum(len(v) for v in ranks.values())} | helpers: {len(HELPERS)}",
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
