#!/usr/bin/env python3
"""Generate the T2a Necromancer talent mechanics (stat/defense passives).

T2a is the first mechanics batch for the T1 talent scaffolding: it turns the
ten stat/defense passive rank spells from inert placeholders into real auras
(plus small module hooks for effects vanilla auras cannot express).

Run this AFTER the T1 generator/SQL: it updates the rank spells that
generate_talent_trees.py creates.  Re-running T1 afterwards resets them to
inert placeholders.

Outputs (re-runnable):
  data/sql/world/20261021140000_world.sql
  client/patches/47-talent-mechanics-t2a.yaml

Usage:
  python tools/generate_talent_mechanics_t2a.py
  python tools/generate_talent_mechanics_t2a.py --apply
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

APPLY_AURA = 6
TARGET_UNIT_CASTER = 1

# Spell aura ids / misc values (core enums).
AURA_MOD_THREAT = 10
AURA_MOD_SKILL = 30
AURA_MOD_PARRY_PERCENT = 47
AURA_MOD_HIT_CHANCE = 54
AURA_MOD_SPELL_HIT_CHANCE = 55
AURA_MOD_DAMAGE_PERCENT_DONE = 79
AURA_MOD_REGEN_DURING_COMBAT = 116
AURA_MOD_MECHANIC_RESISTANCE = 117
AURA_MOD_OFFHAND_DAMAGE_PCT = 122
AURA_MOD_TARGET_RESISTANCE = 123
AURA_ADD_FLAT_MODIFIER = 107

SPELLMOD_RANGE = 5
MECHANIC_FEAR = 5
SKILL_DEFENSE = 95

SCHOOL_MASK_PHYSICAL = 1
SCHOOL_MASK_ALL = 127
SCHOOL_MASK_MAGIC = 126

# Weapon subclass masks (1 << ItemSubclassWeapon).
ONE_HAND_SUBCLASS_MASK = (1 << 0) | (1 << 4) | (1 << 7) | (1 << 13) | (1 << 15)
TWO_HAND_SUBCLASS_MASK = (1 << 1) | (1 << 5) | (1 << 8)

# Spell family 5 flags of the Plague line and Death Coil / Reap.
PLAGUE_BOLT_FLAG = 1
CALL_OF_THE_GRAVE_FLAG = 2
DESECRATION_FLAG = 32
DEATH_COIL_FLAG = 524288
REAP_FLAG = 1048576  # reassigned from Death Coil's flag in this batch

# T2a rank spells are hidden passives like the vanilla talent passives.
PASSIVE_TALENT_ATTRIBUTES = 464

# Reap is moved off Death Coil's family flag so Death's Reach can give it a
# larger range bonus than Death Coil.
REAP_SPELL_IDS = (61013, 61014)


def effect(aura: int, bases: list[int], misc: int = 0,
           item_class: int = -1, item_subclass: int = 0,
           item_inv_type: int = 0, item_type: int = 0) -> dict:
    return {
        "aura": aura,
        "bases": bases,
        "misc": misc,
        "itemClass": item_class,
        "itemSubclass": item_subclass,
        "itemInvType": item_inv_type,
        "itemType": item_type,
    }


# Talent name -> effect list (max 3).  Each effect's `bases` has one value per
# talent rank.  An empty list means the talent is implemented by the module.
TALENTS: dict[str, list[dict]] = {
    # Blood
    "Unholy Regeneration": [
        effect(AURA_MOD_REGEN_DURING_COMBAT, [9, 19, 29, 39, 49]),
    ],
    "Deflection": [
        effect(AURA_MOD_PARRY_PERCENT, [1, 3, 5]),
    ],
    "Death March": [
        effect(AURA_MOD_MECHANIC_RESISTANCE, [4, 9], misc=MECHANIC_FEAR),
    ],
    "Dual Wield Specialization": [
        effect(AURA_MOD_DAMAGE_PERCENT_DONE, [1, 3, 5, 7, 9],
               misc=SCHOOL_MASK_PHYSICAL, item_class=2,
               item_subclass=ONE_HAND_SUBCLASS_MASK),
        effect(AURA_MOD_OFFHAND_DAMAGE_PCT, [4, 9, 14, 19, 24]),
    ],
    "Two-Handed Weapon Specialization": [
        # Damage aura only: the three weapon-skill bonuses are applied by the
        # module (a rank has three effect slots and the damage aura takes one).
        effect(AURA_MOD_DAMAGE_PERCENT_DONE, [1, 3, 5],
               misc=SCHOOL_MASK_PHYSICAL, item_class=2,
               item_subclass=TWO_HAND_SUBCLASS_MASK),
    ],
    "Looming Shadow": [
        effect(AURA_MOD_SKILL, [3, 7, 11, 15, 19], misc=SKILL_DEFENSE),
        effect(AURA_MOD_THREAT, [19, 39, 59, 79, 99], misc=SCHOOL_MASK_ALL),
    ],
    # Plague
    "Precision": [
        effect(AURA_MOD_HIT_CHANCE, [0, 1, 2]),
        effect(AURA_MOD_SPELL_HIT_CHANCE, [0, 1, 2]),
    ],
    "Susceptibility": [
        effect(AURA_MOD_TARGET_RESISTANCE, [-6, -11], misc=SCHOOL_MASK_MAGIC),
    ],
    "Terminal": [],  # module hook (disease dispel resistance)
    "Death's Reach": [
        effect(AURA_ADD_FLAT_MODIFIER, [2, 5], misc=SPELLMOD_RANGE,
               item_type=PLAGUE_BOLT_FLAG | CALL_OF_THE_GRAVE_FLAG |
                         DESECRATION_FLAG | DEATH_COIL_FLAG),
        # Reap's flag is not in the first effect's mask, so this effect is its
        # full +5/+10 bonus (not the +2/+4 delta over Death Coil).
        effect(AURA_ADD_FLAT_MODIFIER, [4, 9], misc=SPELLMOD_RANGE,
               item_type=REAP_FLAG),
    ],
}

# Talent rank spells whose spell family must be set for the range spell-mod
# auras (Death's Reach's aura spell must share the target spells' family).
SPELL_FAMILY = {
    "Death's Reach": 5,
}

# Module-applied mechanics (documented in the generated SQL header).
MODULE_TALENTS = {
    "Terminal": "disease dispel resistance (UnitScript)",
    "Death March": "movement-slow resistance (UnitScript; fear uses aura 117)",
    "Two-Handed Weapon Specialization": "2H sword/mace/axe skill bonuses (PlayerScript)",
}

# Non-aura effects merged into a rank spell's free slots (slot, effect).
# Deflection also enables parry itself: the Necromancer has no vanilla parry
# passive, and SPELL_AURA_MOD_PARRY_PERCENT does nothing until CanParry().
RAW_EFFECTS = {
    "Deflection": [(2, 22)],  # 2 = effect slot, 22 = SPELL_EFFECT_PARRY
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


def raw_slots(name: str) -> dict[int, int]:
    return {slot: effect_id for slot, effect_id in RAW_EFFECTS.get(name, [])}


def emit_sql(path: Path, ranks: dict[str, list[int]], mariadb: str, port: str) -> None:
    cols = {r[0] for r in query(mariadb, port, "SHOW COLUMNS FROM `spell_template`")}
    required = {
        "attributes", "spellFamilyName", "spellFamilyFlags",
        "equippedItemClass", "equippedItemSubClassMask",
        "equippedItemInventoryTypeMask",
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
    w("-- FILE: 20261021140000_world.sql")
    w("-- Necromancer talent mechanics T2a: the ten stat/defense passive")
    w("-- rank spells become real auras, plus the Reap spell-family split.")
    w("-- Generated by tools/generate_talent_mechanics_t2a.py; re-runnable.")
    w("--")
    w("-- Module-applied talents:")
    for name, note in MODULE_TALENTS.items():
        w(f"--   {name}: {note}")
    w("")

    for name, rank_spells in ranks.items():
        effects = TALENTS[name]
        family = SPELL_FAMILY.get(name, 0)
        raws = raw_slots(name)
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
                raw_effect = raws.get(eff_index)
                if eff:
                    updates[f"effect{eff_index}"] = APPLY_AURA
                    updates[f"effectApplyAuraName{eff_index}"] = eff["aura"]
                    updates[f"effectBasePoints{eff_index}"] = eff["bases"][rank_index]
                    updates[f"effectMiscValue{eff_index}"] = eff["misc"]
                    updates[f"effectItemType{eff_index}"] = eff["itemType"]
                    updates[f"effectImplicitTargetA{eff_index}"] = TARGET_UNIT_CASTER
                    # Vanilla passive aura convention: basePoints holds
                    # (value - 1), baseDice/dieSides 1 add it back.
                    updates[f"effectBaseDice{eff_index}"] = 1
                    updates[f"effectDieSides{eff_index}"] = 1
                    if eff_index == 1:
                        updates["equippedItemClass"] = eff["itemClass"]
                        updates["equippedItemSubClassMask"] = eff["itemSubclass"]
                        updates["equippedItemInventoryTypeMask"] = eff["itemInvType"]
                elif raw_effect:
                    updates[f"effect{eff_index}"] = raw_effect
                    updates[f"effectApplyAuraName{eff_index}"] = 0
                    updates[f"effectBasePoints{eff_index}"] = 0
                    updates[f"effectMiscValue{eff_index}"] = 0
                    updates[f"effectItemType{eff_index}"] = 0
                    updates[f"effectImplicitTargetA{eff_index}"] = TARGET_UNIT_CASTER
                    updates[f"effectBaseDice{eff_index}"] = 0
                    updates[f"effectDieSides{eff_index}"] = 0
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

    w("-- Reap moves to its own family flag (Death's Reach has a larger bonus)")
    w("UPDATE `spell_template` SET `spellFamilyFlags` = "
      f"{REAP_FLAG} WHERE `entry` IN ({', '.join(map(str, REAP_SPELL_IDS))});")
    w("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def u32(value: int) -> int:
    """The patcher reads DBC fields as u32; encode negative values as two's
    complement (e.g. -11 -> 4294967285), like the other client patches."""
    return value & 0xFFFFFFFF


def emit_client_yaml(path: Path, ranks: dict[str, list[int]]) -> None:
    lines: list[str] = []
    w = lines.append
    w("# Talent mechanics T2a - generated by tools/generate_talent_mechanics_t2a.py.")
    w("# Turns the ten stat/defense passive rank spells into real auras.")
    w("# Loads after 46-talent-trees.yaml.")
    w("")
    w("Spell.dbc:")
    for name, rank_spells in ranks.items():
        effects = TALENTS[name]
        family = SPELL_FAMILY.get(name, 0)
        raws = raw_slots(name)
        for rank_index, spell_id in enumerate(rank_spells):
            w("  - type: update")
            w(f"    key: {spell_id}")
            w("    values:")
            w(f"      Attributes: {PASSIVE_TALENT_ATTRIBUTES}")
            w(f"      SpellClassSet: {family}")
            w("      SpellClassMask_1: 0")
            w("      SpellClassMask_2: 0")
            item_class = -1
            item_subclass = 0
            item_inv_type = 0
            if effects:
                item_class = effects[0]["itemClass"]
                item_subclass = effects[0]["itemSubclass"]
                item_inv_type = effects[0]["itemInvType"]
            w(f"      EquippedItemClass: {u32(item_class)}")
            w(f"      EquippedItemSubclass: {u32(item_subclass)}")
            w(f"      EquippedItemInvType: {u32(item_inv_type)}")
            for eff_index in range(1, 4):
                eff = effects[eff_index - 1] if eff_index - 1 < len(effects) else None
                raw_effect = raws.get(eff_index)
                if eff:
                    w(f"      Effect_{eff_index}: {APPLY_AURA}")
                    w(f"      EffectAura_{eff_index}: {eff['aura']}")
                    w(f"      EffectBasePoints_{eff_index}: "
                      f"{u32(eff['bases'][rank_index])}")
                    w(f"      EffectMiscValue_{eff_index}: {eff['misc']}")
                    w(f"      EffectItemType_{eff_index}: {eff['itemType']}")
                    w(f"      ImplicitTargetA_{eff_index}: {TARGET_UNIT_CASTER}")
                    w(f"      EffectBaseDice_{eff_index}: 1")
                    w(f"      EffectDieSides_{eff_index}: 1")
                elif raw_effect:
                    w(f"      Effect_{eff_index}: {raw_effect}")
                    w(f"      EffectAura_{eff_index}: 0")
                    w(f"      EffectBasePoints_{eff_index}: 0")
                    w(f"      EffectMiscValue_{eff_index}: 0")
                    w(f"      EffectItemType_{eff_index}: 0")
                    w(f"      ImplicitTargetA_{eff_index}: {TARGET_UNIT_CASTER}")
                    w(f"      EffectBaseDice_{eff_index}: 0")
                    w(f"      EffectDieSides_{eff_index}: 0")
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
    w("")
    w("  # Reap's own spell-family flag (Death's Reach has a larger bonus)")
    for spell_id in REAP_SPELL_IDS:
        w("  - type: update")
        w(f"    key: {spell_id}")
        w("    values:")
        w("      SpellClassSet: 5")
        w(f"      SpellClassMask_1: {REAP_FLAG & 0xFFFFFFFF}")
        w("      SpellClassMask_2: 0")
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
    out_sql = MODULE_DIR / "data/sql/world/20261021140000_world.sql"
    out_yaml = MODULE_DIR / "client/patches/47-talent-mechanics-t2a.yaml"

    emit_sql(out_sql, ranks, args.mariadb, args.port)
    emit_client_yaml(out_yaml, ranks)

    print(f"T2a talents: {len(ranks)} | rank spells: "
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
