#!/usr/bin/env python3
"""Generate the T2b Necromancer talent mechanics (spell-modifier passives).

T2b turns the ten spell-modifier rank spells into spell-mod auras and two
small module-supported effects:

  Improved Plague Bolt, Preservation, Improved Terror, Improved Dark Command,
  Reaping, Life and Death, Restlessness, Reclusion, Withering World,
  Improved Cripple.

Most effects are SPELL_AURA_ADD_FLAT_MODIFIER / ADD_PCT_MODIFIER auras.  The
rank spell's spell family and EffectItemType mask select the class spells they
modify; a few class spells get a dedicated family-0 flag for that purpose.
Withering World (periodic/direct damage) and Improved Cripple (slow amount)
are implemented in the module.

Run this AFTER the T1 generator/SQL (it updates the rank spells created by
generate_talent_trees.py).  T2a is independent and can be applied before or
after this batch.

Outputs (re-runnable):
  data/sql/world/20261021160000_world.sql
  client/patches/48-talent-mechanics-t2b.yaml

Usage:
  python tools/generate_talent_mechanics_t2b.py
  python tools/generate_talent_mechanics_t2b.py --apply
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
from generate_talent_trees import query  # noqa: E402

APPLY_PCT_MODIFIER = 108
APPLY_FLAT_MODIFIER = 107
TARGET_UNIT_CASTER = 1

# Spell mod ops (SpellDefines.h).
SPELLMOD_DAMAGE = 0
SPELLMOD_DURATION = 1
SPELLMOD_CASTING_TIME = 10
SPELLMOD_COOLDOWN = 11
SPELLMOD_COST = 14
SPELLMOD_RESIST_MISS_CHANCE = 16

# Spell family 5 flags.
PLAGUE_BOLT_FLAG = 1
CALL_OF_THE_GRAVE_FLAG = 2
DESECRATION_FLAG = 32
DEATH_COIL_FLAG = 524288
REAP_FLAG = 1048576

# Family-0 flags for the affected class spells.  All family-0 spells in the
# DB have SpellFamilyFlags 0, so these bits are free.
TERROR_FLAG = 1 << 24
DARK_COMMAND_FLAG = 1 << 25
RECLUSION_FLAG = 1 << 26
RAISE_FLAG = 1 << 27
HARVEST_FLAG = 1 << 28

PASSIVE_TALENT_ATTRIBUTES = 464

# Class spells whose family-0 flags are used by a T2b spell mod.  The value is
# the full new flag set (existing family-0 flags are all 0).
FLAG_UPDATES = {
    61077: DARK_COMMAND_FLAG,                    # Dark Command
    61078: TERROR_FLAG,                          # Terror
    61029: RECLUSION_FLAG,                       # Harvest (cast)
    61048: RECLUSION_FLAG,                       # Meat Catapult
    61079: RECLUSION_FLAG,                       # Ghoul Armor
    61080: RECLUSION_FLAG,                       # Embalm
    61081: RECLUSION_FLAG,                       # Lobotomize
    61083: RECLUSION_FLAG,                       # Rule Undead
    61084: RECLUSION_FLAG,                       # Unholy Shield
    61085: RECLUSION_FLAG,                       # Lich Armor
    61024: RECLUSION_FLAG | RAISE_FLAG,          # Raise Ghoul
    61025: RECLUSION_FLAG | RAISE_FLAG,          # Raise Skeleton
    61034: RECLUSION_FLAG | RAISE_FLAG,          # Raise Zombie
    61035: RECLUSION_FLAG | RAISE_FLAG,          # Raise Shade
    61036: RECLUSION_FLAG | RAISE_FLAG,          # Raise Banshee
    61037: RECLUSION_FLAG | RAISE_FLAG,          # Raise Wraith
    61038: RECLUSION_FLAG | RAISE_FLAG,          # Raise Bloodmage
    61039: RECLUSION_FLAG | RAISE_FLAG,          # Raise Abomination
    61040: RECLUSION_FLAG | RAISE_FLAG,          # Raise Wight (family -> 0)
    61030: HARVEST_FLAG,                         # Harvest aura (duration)
}

# Class spells whose family changes so the family-0 spell mod can select them.
FAMILY_OVERRIDES = {
    61040: 0,  # Raise Wight: Renew family 6 -> family 0
}

# Server script_name additions (the client does not store script_name).
SCRIPT_NAMES = {
    61023: "spell_necromancer_cripple",
}


def effect(aura: int, bases: list[int], misc: int = 0,
           item_type: int = 0) -> dict:
    return {"aura": aura, "bases": bases, "misc": misc, "itemType": item_type}


# Talent name -> effect list.  Each bases list has one value per rank.
TALENTS: dict[str, list[dict]] = {
    "Reaping": [
        effect(APPLY_FLAT_MODIFIER, [-1001, -2001], misc=SPELLMOD_COOLDOWN,
               item_type=REAP_FLAG),
    ],
    "Improved Dark Command": [
        effect(APPLY_FLAT_MODIFIER, [3, 7], misc=SPELLMOD_RESIST_MISS_CHANCE,
               item_type=DARK_COMMAND_FLAG),
    ],
    "Improved Plague Bolt": [
        effect(APPLY_FLAT_MODIFIER, [-101, -201, -301, -401, -501],
               misc=SPELLMOD_CASTING_TIME, item_type=PLAGUE_BOLT_FLAG),
    ],
    "Preservation": [
        # Negative percentages: SPELLMOD_COST with a positive PCT mod would
        # *increase* the mana cost.
        effect(APPLY_PCT_MODIFIER, [-3, -5, -7, -9, -11], misc=SPELLMOD_COST,
               item_type=PLAGUE_BOLT_FLAG | CALL_OF_THE_GRAVE_FLAG |
                         DESECRATION_FLAG),
    ],
    "Improved Terror": [
        effect(APPLY_FLAT_MODIFIER,
               [-401, -801, -1201, -1601, -2001], misc=SPELLMOD_CASTING_TIME,
               item_type=TERROR_FLAG),
    ],
    "Withering World": [],  # module (periodic + Disease Cloud direct damage)
    "Improved Cripple": [],  # module (Cripple's slow aura value)
    "Reclusion": [
        # Negative percentages: SPELLMOD_COST with a positive PCT mod would
        # *increase* the mana cost.
        effect(APPLY_PCT_MODIFIER, [-4, -7, -11], misc=SPELLMOD_COST,
               item_type=RECLUSION_FLAG),
        effect(10, [-9, -17, -26], misc=127),  # MOD_THREAT
    ],
    "Life and Death": [
        effect(APPLY_PCT_MODIFIER, [2, 5, 9], misc=SPELLMOD_DAMAGE,
               item_type=DEATH_COIL_FLAG),
    ],
    "Restlessness": [
        effect(APPLY_FLAT_MODIFIER, [-401, -801, -1201, -1601, -2001],
               misc=SPELLMOD_CASTING_TIME, item_type=RAISE_FLAG),
        effect(APPLY_FLAT_MODIFIER, [-201, -401, -601, -801, -1001],
               misc=SPELLMOD_DURATION, item_type=HARVEST_FLAG),
    ],
}

SPELL_FAMILY = {
    "Reaping": 5,
    "Improved Plague Bolt": 5,
    "Preservation": 5,
    "Life and Death": 5,
}

MODULE_TALENTS = {
    "Withering World": "periodic Desecration/Disease Cloud damage (UnitScript) "
                       "+ Disease Cloud direct damage (SpellScript)",
    "Improved Cripple": "Cripple's slow value (AuraScript)",
}


def load_rank_spells() -> dict[str, list[int]]:
    build = json.loads((DATA_DIR / "talent-tree-build.json").read_text(encoding="utf-8"))
    ranks = {t["name"]: t["ranks"] for t in build["talents"]}
    result: dict[str, list[int]] = {}
    for name, effects in TALENTS.items():
        if name not in ranks:
            raise SystemExit(f"talent not found in talent-tree-build.json: {name}")
        spell_ids = ranks[name]
        if not spell_ids:
            raise SystemExit(f"{name}: no rank spells")
        for eff in effects:
            if len(eff["bases"]) != len(spell_ids):
                raise SystemExit(
                    f"{name}: {len(eff['bases'])} effect values for "
                    f"{len(spell_ids)} ranks"
                )
        result[name] = spell_ids
    return result


def effect_slots(effects: list[dict], rank_index: int) -> list[dict | None]:
    return [effects[i] if i < len(effects) else None for i in range(3)]


def emit_sql(path: Path, ranks: dict[str, list[int]], mariadb: str, port: str) -> None:
    cols = {r[0] for r in query(mariadb, port, "SHOW COLUMNS FROM `spell_template`")}
    required = {
        "attributes", "spellFamilyName", "spellFamilyFlags",
        "equippedItemClass", "equippedItemSubClassMask",
        "equippedItemInventoryTypeMask", "script_name",
    }
    for i in range(1, 4):
        required |= {
            f"effect{i}", f"effectApplyAuraName{i}", f"effectBasePoints{i}",
            f"effectMiscValue{i}", f"effectItemType{i}",
            f"effectImplicitTargetA{i}", f"effectImplicitTargetB{i}",
            f"effectDieSides{i}", f"effectBaseDice{i}",
            f"effectDicePerLevel{i}", f"effectRealPointsPerLevel{i}",
            f"effectMechanic{i}", f"effectRadiusIndex{i}",
            f"effectAmplitude{i}", f"effectMultipleValue{i}",
            f"effectChainTarget{i}", f"effectTriggerSpell{i}",
            f"effectPointsPerComboPoint{i}", f"effectBonusCoefficient{i}",
        }
    missing = required - cols
    if missing:
        raise SystemExit(f"spell_template is missing columns: {sorted(missing)}")

    lines: list[str] = []
    w = lines.append
    w("-- FILE: 20261021160000_world.sql")
    w("-- Necromancer talent mechanics T2b: spell-modifier passives.")
    w("-- Generated by tools/generate_talent_mechanics_t2b.py; re-runnable.")
    w("--")
    w("-- Module-applied talents:")
    for name, note in MODULE_TALENTS.items():
        w(f"--   {name}: {note}")
    w("")

    # Class-spell family flags / family overrides / script names.
    w("-- class spells selected by the T2b spell mods")
    for spell_id, flags in FLAG_UPDATES.items():
        family = FAMILY_OVERRIDES.get(spell_id, 0)
        w(f"UPDATE `spell_template` SET `spellFamilyName` = {family}, "
          f"`spellFamilyFlags` = {flags} WHERE `entry` = {spell_id};")
    for spell_id, script_name in SCRIPT_NAMES.items():
        escaped = script_name.replace("'", "''")
        w(f"UPDATE `spell_template` SET `script_name` = '{escaped}' "
          f"WHERE `entry` = {spell_id};")
    w("")

    for name, rank_spells in ranks.items():
        effects = TALENTS[name]
        family = SPELL_FAMILY.get(name, 0)
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
            for eff_index in range(1, 4):
                eff = effects[eff_index - 1] if eff_index - 1 < len(effects) else None
                if eff:
                    updates[f"effect{eff_index}"] = 6  # SPELL_EFFECT_APPLY_AURA
                    updates[f"effectApplyAuraName{eff_index}"] = eff["aura"]
                    updates[f"effectBasePoints{eff_index}"] = eff["bases"][rank_index]
                    updates[f"effectMiscValue{eff_index}"] = eff["misc"]
                    updates[f"effectItemType{eff_index}"] = eff["itemType"]
                    updates[f"effectImplicitTargetA{eff_index}"] = TARGET_UNIT_CASTER
                    updates[f"effectBaseDice{eff_index}"] = 1
                    updates[f"effectDieSides{eff_index}"] = 1
                else:
                    updates[f"effect{eff_index}"] = 0
                    updates[f"effectApplyAuraName{eff_index}"] = 0
                    updates[f"effectBasePoints{eff_index}"] = 0
                    updates[f"effectMiscValue{eff_index}"] = 0
                    updates[f"effectItemType{eff_index}"] = 0
                    updates[f"effectImplicitTargetA{eff_index}"] = 0
                    updates[f"effectBaseDice{eff_index}"] = 0
                    updates[f"effectDieSides{eff_index}"] = 0
                updates[f"effectImplicitTargetB{eff_index}"] = 0
                updates[f"effectDicePerLevel{eff_index}"] = 0
                updates[f"effectRealPointsPerLevel{eff_index}"] = 0
                updates[f"effectMechanic{eff_index}"] = 0
                updates[f"effectRadiusIndex{eff_index}"] = 0
                updates[f"effectAmplitude{eff_index}"] = 0
                updates[f"effectMultipleValue{eff_index}"] = 0
                updates[f"effectChainTarget{eff_index}"] = 0
                updates[f"effectTriggerSpell{eff_index}"] = 0
                updates[f"effectPointsPerComboPoint{eff_index}"] = 0
                updates[f"effectBonusCoefficient{eff_index}"] = 0
            assignments = ", ".join(f"`{k}` = {v}" for k, v in updates.items())
            w(f"UPDATE `spell_template` SET {assignments} WHERE `entry` = {spell_id};")
        w("")

    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def u32(value: int) -> int:
    return value & 0xFFFFFFFF


def emit_client_yaml(path: Path, ranks: dict[str, list[int]]) -> None:
    lines: list[str] = []
    w = lines.append
    w("# Talent mechanics T2b - generated by tools/generate_talent_mechanics_t2b.py.")
    w("# Turns the ten spell-modifier rank spells into spell-mod auras.")
    w("# Loads after 47-talent-mechanics-t2a.yaml.")
    w("")
    w("Spell.dbc:")
    for spell_id, flags in FLAG_UPDATES.items():
        family = FAMILY_OVERRIDES.get(spell_id, 0)
        w("  - type: update")
        w(f"    key: {spell_id}")
        w("    values:")
        w(f"      SpellClassSet: {family}")
        w(f"      SpellClassMask_1: {u32(flags)}")
        w(f"      SpellClassMask_2: {u32(flags >> 32)}")
    for name, rank_spells in ranks.items():
        effects = TALENTS[name]
        family = SPELL_FAMILY.get(name, 0)
        for rank_index, spell_id in enumerate(rank_spells):
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
            for eff_index in range(1, 4):
                eff = effects[eff_index - 1] if eff_index - 1 < len(effects) else None
                if eff:
                    w(f"      Effect_{eff_index}: 6")
                    w(f"      EffectAura_{eff_index}: {eff['aura']}")
                    w(f"      EffectBasePoints_{eff_index}: "
                      f"{u32(eff['bases'][rank_index])}")
                    w(f"      EffectMiscValue_{eff_index}: {eff['misc']}")
                    w(f"      EffectItemType_{eff_index}: {eff['itemType']}")
                    w(f"      ImplicitTargetA_{eff_index}: {TARGET_UNIT_CASTER}")
                    w(f"      EffectBaseDice_{eff_index}: 1")
                    w(f"      EffectDieSides_{eff_index}: 1")
                else:
                    w(f"      Effect_{eff_index}: 0")
                    w(f"      EffectAura_{eff_index}: 0")
                    w(f"      EffectBasePoints_{eff_index}: 0")
                    w(f"      EffectMiscValue_{eff_index}: 0")
                    w(f"      EffectItemType_{eff_index}: 0")
                    w(f"      ImplicitTargetA_{eff_index}: 0")
                    w(f"      EffectBaseDice_{eff_index}: 0")
                    w(f"      EffectDieSides_{eff_index}: 0")
                w(f"      ImplicitTargetB_{eff_index}: 0")
                w(f"      EffectDicePerLevel_{eff_index}: 0")
                w(f"      EffectRealPointsPerLevel_{eff_index}: 0")
                w(f"      EffectMechanic_{eff_index}: 0")
                w(f"      EffectRadiusIndex_{eff_index}: 0")
                w(f"      EffectAmplitude_{eff_index}: 0")
                w(f"      EffectMultipleValue_{eff_index}: 0")
                w(f"      EffectChainTarget_{eff_index}: 0")
                w(f"      EffectTriggerSpell_{eff_index}: 0")
                w(f"      EffectPointsPerCombo_{eff_index}: 0")
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
    out_sql = MODULE_DIR / "data/sql/world/20261021160000_world.sql"
    out_yaml = MODULE_DIR / "client/patches/48-talent-mechanics-t2b.yaml"

    emit_sql(out_sql, ranks, args.mariadb, args.port)
    emit_client_yaml(out_yaml, ranks)

    print(f"T2b talents: {len(ranks)} | rank spells: "
          f"{sum(len(v) for v in ranks.values())}", file=sys.stderr)
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
