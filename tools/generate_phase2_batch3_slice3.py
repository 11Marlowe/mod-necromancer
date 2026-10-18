#!/usr/bin/env python3
"""Generate the Necromancer Phase-2 batch-3 (minions, slice 3) spell SQL.

Slice 3 ships the higher minion tiers (auto-learned for now; quest/item
gates come later - user decision 2026-10-16):

  Raise Zombie      (61034, L10)  - guardian of creature 1501 (Mindless Zombie)
  Raise Shade       (61035, L10)  - creature 7370 (Restless Shade)
  Raise Banshee     (61036, L20)  - creature 10463 (Shrieking Banshee)
  Raise Wraith      (61037, L30)  - creature 1800 (Cold Wraith)
  Raise Bloodmage   (61038, L38)  - creature 8526 (Dark Caster)
  Raise Abomination (61039, L40)  - creature 8545 (Abomination); the module
                                    requires three corpses nearby (cast gate)
  Raise Wight       (61040, L58)  - creature 11621 (Spectral Corpse)

plus the per-tier pet ability and Death Pact variants:

  Entropic Bolt     (61041, pet)  - ranged pet active (Firebolt 3110 clone)
                                    for Banshee/Bloodmage through
                                    `petcreateinfo_spell`; the melee tiers
                                    reuse Ravage (61027)
  Death Pact (Banshee)   (61042) - 2% mana per 4 sec
  Death Pact (Shade)     (61043) - -5% threat
  Death Pact (Wraith)    (61044) - +2% melee and casting speed
  Death Pact (Hulk)      (61045) - +5% total health (Abomination/Wight)
  Death Pact (Bloodmage) (61046) - +2% spell damage done

All Raise spells clone `Summon Atal'ai Skeleton` (12151) exactly like slice 1
(guardian summon, target mode 32, the model's dummy second effect dropped;
the module re-scales the minion to the caster).

Usage:
  python tools/generate_phase2_batch3_slice3.py --out data/sql/world/20261017120000_world.sql
"""

import argparse
import subprocess
import sys

# new spell id -> model spell id copied from spell_template
NEW_SPELLS = [
    (61034, 12151),  # Raise Zombie
    (61035, 12151),  # Raise Shade
    (61036, 12151),  # Raise Banshee
    (61037, 12151),  # Raise Wraith
    (61038, 12151),  # Raise Bloodmage
    (61039, 12151),  # Raise Abomination
    (61040, 12151),  # Raise Wight
    (61041, 3110),   # Entropic Bolt  <- Firebolt (ranged pet active)
    (61042, 20578),  # Death Pact (Banshee)
    (61043, 20578),  # Death Pact (Shade)
    (61044, 20578),  # Death Pact (Wraith)
    (61045, 20578),  # Death Pact (Hulk: Abomination/Wight)
    (61046, 20578),  # Death Pact (Bloodmage)
]

NAME_OVERRIDES = {
    61034: ("Raise Zombie", ""),
    61035: ("Raise Shade", ""),
    61036: ("Raise Banshee", ""),
    61037: ("Raise Wraith", ""),
    61038: ("Raise Bloodmage", ""),
    61039: ("Raise Abomination", ""),
    61040: ("Raise Wight", ""),
    61041: ("Entropic Bolt", ""),
    61042: ("Death Pact", ""),
    61043: ("Death Pact", ""),
    61044: ("Death Pact", ""),
    61045: ("Death Pact", ""),
    61046: ("Death Pact", ""),
}

# script_name values must match the registrations in
# AddNecromancerScripts() (src/mod_necromancer.cpp).
SPELL_SCRIPT_RAISE_MINION = "spell_necromancer_raise_minion"

# creature_template entries (vanilla undead models, placeholders)
CREATURES = {
    61034: (1501,  "zombie"),       # Mindless Zombie
    61035: (7370,  "shade"),        # Restless Shade
    61036: (10463, "banshee"),      # Shrieking Banshee
    61037: (1800,  "wraith"),       # Cold Wraith
    61038: (8526,  "bloodmage"),    # Dark Caster
    61039: (8545,  "abomination"),  # Abomination
    61040: (11621, "wight"),        # Spectral Corpse
}

# The model's second (dummy, script-target 38) effect is dropped, as in
# slice 1: for the clones it has no `spell_script_target` row and made every
# cast fail with "Invalid target".
RAISE_DROP_SECOND_EFFECT = {
    "effect2": 0,
    "effectDieSides2": 0,
    "effectBaseDice2": 0,
    "effectBasePoints2": 0,
    "effectApplyAuraName2": 0,
    "effectImplicitTargetA2": 0,
}

# Death Pact variants share the Cannibalize-aura scaffold cleanups of slice 2
# (duration 30 = 30 min; not dispellable; no channel name, no damage
# interrupt; skull icon).
DEATH_PACT_COMMON = {
    "durationIndex": 30,
    "dispel": 0,
    "attributesEx": 0,
    "auraInterruptFlags": 0,
    "spellIconId": 88,
    "description": "",
    "script_name": "",
}

# design-required corpse/bag costs are part of the tooltip (user request
# 2026-10-18; see design doc A.6)
RAISE_DESCRIPTIONS = {
    61034: "Raises a zombie to fight for you for $d. Requires a humanoid or "
           "zombie corpse nearby, or 1 Lump of Flesh.",
    61035: "Raises a shade to fight for you for $d. Requires a humanoid, "
           "undead, demon, beast, giant or dragonkin corpse nearby, or 1 "
           "Ectoplasm.",
    61036: "Raises a banshee to fight for you for $d. Requires a female "
           "humanoid or banshee corpse nearby, or 1 Banshee Essence.",
    61037: "Raises a wraith to fight for you for $d. Requires a humanoid, "
           "undead, demon, beast, giant or dragonkin corpse nearby, or 1 "
           "Ectoplasm. Only one wraith at a time.",
    61038: "Raises a bloodmage to fight for you for $d. Requires a humanoid "
           "or non-spectral undead corpse nearby, or 1 Pile of Bones. Only "
           "one bloodmage at a time.",
    61039: "Raises an abomination to fight for you for $d. Requires three "
           "humanoid, undead or giant corpses nearby, or 3 Lumps of Flesh. "
           "Only one abomination at a time.",
}

COLUMN_OVERRIDES = {}
for spell_id, (entry, noun) in CREATURES.items():
    COLUMN_OVERRIDES[spell_id] = {
        "description": RAISE_DESCRIPTIONS[spell_id],
        "effectMiscValue1": entry,
        "effectImplicitTargetA1": 32,   # TARGET_LOCATION_UNIT_MINION_POSITION
        "script_name": SPELL_SCRIPT_RAISE_MINION,
        **RAISE_DROP_SECOND_EFFECT,
    }

COLUMN_OVERRIDES.update({
    61041: {
        "description": "Hurls a bolt of fire at an enemy, dealing $s1 Fire damage.",
    },
    61042: {
        **DEATH_PACT_COMMON,
        "effectApplyAuraName1": 21,    # SPELL_AURA_OBS_MOD_MANA
        "effectBasePoints1": 1,        # 2% (basePoints + baseDice)
        "effectAmplitude1": 4000,
        "auraDescription": "Restores $s1% of total mana every $t1 sec.",
    },
    61043: {
        **DEATH_PACT_COMMON,
        "effectApplyAuraName1": 10,    # SPELL_AURA_MOD_THREAT
        "effectMiscValue1": 127,       # all spell schools
        "effectBasePoints1": -6,       # -5% (basePoints + baseDice)
        "effectAmplitude1": 0,
        "auraDescription": "Reduces threat generated by $s1%.",
    },
    61044: {
        **DEATH_PACT_COMMON,
        "effectApplyAuraName1": 138,   # SPELL_AURA_MOD_MELEE_HASTE
        "effectBasePoints1": 1,        # +2%
        "effectAmplitude1": 0,
        "effect2": 6,                  # SPELL_EFFECT_APPLY_AURA
        "effectDieSides2": 1,
        "effectBaseDice2": 1,
        "effectBasePoints2": 1,        # +2% casting speed
        "effectImplicitTargetA2": 1,   # self
        "effectApplyAuraName2": 65,    # SPELL_AURA_MOD_CASTING_SPEED_NOT_STACK
        "effectAmplitude2": 0,
        "auraDescription": "Increases melee and casting speed by $s1%.",
    },
    61045: {
        **DEATH_PACT_COMMON,
        "effectApplyAuraName1": 133,   # SPELL_AURA_MOD_INCREASE_HEALTH_PERCENT
        "effectBasePoints1": 4,        # +5% (basePoints + baseDice)
        "effectAmplitude1": 0,
        "auraDescription": "Increases your total health by $s1%.",
    },
    61046: {
        **DEATH_PACT_COMMON,
        "effectApplyAuraName1": 79,    # SPELL_AURA_MOD_DAMAGE_PERCENT_DONE
        "effectMiscValue1": 126,       # magic schools (physical excluded)
        "effectBasePoints1": 1,        # +2% (basePoints + baseDice)
        "effectAmplitude1": 0,
        "auraDescription": "Increases your spell damage done by $s1%.",
    },
})

# pet abilities: creature entry -> spell learned by the tethered pet
# (melee tiers share Ravage 61027; the caster tiers use Entropic Bolt 61041)
PET_CREATE_SPELLS = [
    (1501, 61027),
    (7370, 61027),
    (10463, 61041),
    (1800, 61027),
    (8526, 61041),
    (8545, 61027),
    (11621, 61027),
]

SKILL_LINE = 700          # "Necromancy"
CLASS_MASK = 512          # class 10
SPELLBOOK_SPELLS = [61034, 61035, 61036, 61037, 61038, 61039, 61040]

DELETE_PET_CREATURE_IDS = [e for e, _ in PET_CREATE_SPELLS]


def run(mariadb, port, sql):
    out = subprocess.run(
        [mariadb, f"--port={port}", "-u", "root", "tw_world",
         "--batch", "--skip-column-names", "-e", sql],
        capture_output=True, text=True, check=True,
    )
    return [line.split("\t") for line in out.stdout.splitlines() if line.strip()]


def sql_literal(value, data_type):
    if value == "NULL":
        return "NULL"
    if data_type in ("tinyint", "smallint", "mediumint", "int", "bigint",
                     "float", "double", "decimal"):
        return value
    escaped = value.replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe")
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    columns = run(args.mariadb, args.port,
                  "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
                  "WHERE table_schema='tw_world' AND table_name='spell_template' "
                  "ORDER BY ORDINAL_POSITION")
    col_names = [c[0] for c in columns]
    col_types = {c[0]: c[1] for c in columns}
    entry_idx = col_names.index("entry")

    print(f"spell_template: {len(col_names)} columns", file=sys.stderr)

    out = []
    w = out.append
    w("-- FILE: 20261017120000_world.sql")
    w("-- Necromancer (class 10) Phase 2 batch 3 (minions, slice 3): raise")
    w("-- tiers Zombie/Shade (61034/61035), Banshee (61036), Wraith (61037),")
    w("-- Bloodmage (61038), Abomination (61039), Wight (61040) + Entropic")
    w("-- Bolt pet active (61041) + Death Pact variants (61042-61046).")
    w("-- Generated by tools/generate_phase2_batch3_slice3.py; re-runnable.")
    w("--")
    w("-- All Raise spells clone Summon Atal'ai Skeleton 12151 (guardian,")
    w("-- target mode 32, dummy second effect dropped); the module re-scales")
    w("-- the minion, gates the Abomination on three nearby corpses and maps")
    w("-- each minion kind to its Death Pact effect.")
    w("")
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i in [n for n, _ in NEW_SPELLS]))
    w("DELETE FROM `skill_line_ability` WHERE `skill_id` = %d AND `spell_id` IN (%s);" %
      (SKILL_LINE, ", ".join(str(i) for i in SPELLBOOK_SPELLS)))
    w("DELETE FROM `petcreateinfo_spell` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i in DELETE_PET_CREATURE_IDS))
    w("")

    w("-- ============================================================")
    w("-- spell_template rows (copies of the model spells, new entry ids)")
    w("-- ============================================================")
    for new_id, model_id in NEW_SPELLS:
        rows = run(args.mariadb, args.port,
                   f"SELECT * FROM spell_template WHERE entry = {model_id}")
        if len(rows) != 1:
            print(f"ERROR: model {model_id} not found", file=sys.stderr)
            return 1
        values = list(rows[0])
        values[entry_idx] = str(new_id)
        name, rank = NAME_OVERRIDES.get(new_id, (None, None))
        if name is not None:
            values[col_names.index("name")] = name
            values[col_names.index("nameSubtext")] = rank
        for column, value in COLUMN_OVERRIDES.get(new_id, {}).items():
            values[col_names.index(column)] = str(value)
        literals = [sql_literal(v, col_types[c]) for v, c in zip(values, col_names)]
        w("INSERT INTO `spell_template` (`%s`) VALUES" % "`, `".join(col_names))
        w("  (%s);" % ", ".join(literals))
        w("")

    w("-- ============================================================")
    w("-- petcreateinfo_spell (per-tier pet actives)")
    w("-- ============================================================")
    w("INSERT INTO `petcreateinfo_spell` (`entry`, `spell1`, `spell2`, `spell3`, `spell4`) VALUES")
    w(",\n".join(f"  ({entry}, {spell_id}, 0, 0, 0)" for entry, spell_id in PET_CREATE_SPELLS) + ";")
    w("")

    w("-- ============================================================")
    w("-- skill_line_ability rows (Necromancy, class mask 512)")
    w("-- ============================================================")
    next_id = int(run(args.mariadb, args.port,
                      "SELECT IFNULL(MAX(`id`), 0) + 1 FROM skill_line_ability")[0][0])
    w("INSERT INTO `skill_line_ability` (`id`, `skill_id`, `spell_id`, `race_mask`, `class_mask`, "
      "`req_skill_value`, `superseded_by_spell`, `learn_on_get_skill`, `max_value`, `min_value`, "
      "`req_train_points`) VALUES")
    rows = []
    for spell_id in SPELLBOOK_SPELLS:
        rows.append(f"  ({next_id}, {SKILL_LINE}, {spell_id}, 0, {CLASS_MASK}, 1, 0, 0, 0, 0, 0)")
        next_id += 1
    w(",\n".join(rows) + ";")
    w("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
