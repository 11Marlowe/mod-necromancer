#!/usr/bin/env python3
"""Generate the Necromancer Phase-2 batch-3 (minions, slice 3b) spell SQL.

Slice 3b ships the multi-minion limit and the corpse-launcher:

  Meat Catapult          (61048, L44)  - Thorium Grenade 19769 clone: launched
                                         at a destination (TARGET_ENUM_UNITS_
                                         ENEMY_AOE_AT_DEST_LOC), 1.5 sec cast,
                                         20 yd, 3 yd radius, X-Y Shadow damage
                                         + 2 sec stun, 1 min cooldown.  The
                                         module (script_name) requires and
                                         consumes one Corpse Bag item.
  Army of the Dead R1    (61049, L20)  - passive (no effects); the module reads
                                         HasSpell to allow +1 active minion.
  Army of the Dead R2    (61050, L40)  - passive; +2 active minions.  Rank 1 is
                                         removed when rank 2 is learned.

Design source: A.3 slot 21 ("Allows you to have an additional 1/2 minions
active at a time") and A.6 (Meat Catapult).  The passives clone vanilla
"Dodge" (81, attributes 0x50 = ability|passive) with the skill-step effect
dropped; the tanks are auto-learned until real talents exist (shortcut class
of A19/A34/A48).

Usage:
  python tools/generate_phase2_batch3_slice3b.py --out data/sql/world/20261018180000_world.sql
"""

import argparse
import subprocess
import sys

# new/replaced spell id -> model spell id
NEW_SPELLS = [
    (61048, 19769),  # Meat Catapult   <- Thorium Grenade
    (61049, 81),     # Army of the Dead R1 <- Dodge (passive scaffold)
    (61050, 81),     # Army of the Dead R2
]

NAME_OVERRIDES = {
    61048: ("Meat Catapult", ""),
    61049: ("Army of the Dead", "Rank 1"),
    61050: ("Army of the Dead", "Rank 2"),
}

SPELL_SCRIPT_MEAT_CATAPULT = "spell_necromancer_meat_catapult"

# Army of the Dead passives: drop Dodge's skill-step effect, keep the passive
# attributes, make it permanent-inert and give it the skull icon (placeholder).
ARMY_COMMON = {
    "effect1": 0,
    "effectDieSides1": 0,
    "effectBaseDice1": 0,
    "effectBasePoints1": 0,
    "effectMiscValue1": 0,
    "effectImplicitTargetA1": 0,
    "spellIconId": 88,           # skull (Death Coil / Death Pact icon)
    "castingTimeIndex": 1,       # instant (never cast)
    "durationIndex": 21,         # permanent (-1)
    "rangeIndex": 1,
    "manaCost": 0,
    "recoveryTime": 0,
    "spellLevel": 0,
    "baseLevel": 0,
    "maxLevel": 0,
    "school": 0,
    "script_name": "",
}

COLUMN_OVERRIDES = {
    61048: {
        "description": "Launches a corpse from your Corpse Bag at the target "
                       "location, inflicting $s1 Shadow damage and stunning "
                       "enemies within 3 yards for $d. Requires a corpse in "
                       "your Corpse Bag.",
        # design values (A.6: 1.5 sec cast, 20 yd, 1 min CD, Shadow damage).
        # The damage numbers stay Thorium Grenade's (1000 ms -> 1500 ms here).
        # NB: the `school` column is the school *index* (5 = Shadow; the
        # model's Fire is index 2), not the bitmask.
        "school": 5,                 # Shadow (model is Fire = 2)
        "castingTimeIndex": 16,      # SpellCastTimes index 16 = 1500 ms
        "rangeIndex": 3,             # SpellRange index 3 = 20 yd
        "durationIndex": 39,         # SpellDuration index 39 = 2000 ms (stun)
        "recoveryTime": 60000,       # 1 min cooldown
        "startRecoveryTime": 1500,   # standard GCD (the model is item-thrown)
        "startRecoveryCategory": 133,
        "effectBasePoints2": 1,      # stun "2 sec" (baseDice 1 + 1)
        "effectDieSides2": 1,
        "effectBaseDice2": 1,
        "effectMechanic2": 12,       # stun (the model uses knockout 14)
        "spellLevel": 44,
        "baseLevel": 44,
        "maxLevel": 0,
        "script_name": SPELL_SCRIPT_MEAT_CATAPULT,
    },
    61049: {
        **ARMY_COMMON,
        "description": "Allows you to have an additional minion active at a "
                       "time. Only one minion can be Tethered.",
    },
    61050: {
        **ARMY_COMMON,
        "description": "Allows you to have 2 additional minions active at a "
                       "time. Only one minion can be Tethered.",
    },
}

SKILL_LINE = 700          # "Necromancy"
CLASS_MASK = 512          # class 10
SPELLBOOK_SPELLS = [61048, 61049, 61050]


def run(mariadb, port, sql, db="tw_world"):
    out = subprocess.run(
        [mariadb, f"--port={port}", "-u", "root", db,
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


def table_columns(mariadb, port, table):
    columns = run(mariadb, port,
                  "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
                  f"WHERE table_schema='tw_world' AND table_name='{table}' "
                  "ORDER BY ORDINAL_POSITION")
    return [c[0] for c in columns], {c[0]: c[1] for c in columns}


def clone_row(mariadb, port, table, entry):
    rows = run(mariadb, port, f"SELECT * FROM {table} WHERE entry = {entry}")
    if len(rows) != 1:
        raise RuntimeError(f"{table}: model {entry} not found")
    return rows[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe")
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    spell_cols, spell_types = table_columns(args.mariadb, args.port, "spell_template")
    spell_entry_idx = spell_cols.index("entry")

    print(f"spell_template: {len(spell_cols)} cols", file=sys.stderr)

    out = []
    w = out.append
    w("-- FILE: 20261018180000_world.sql")
    w("-- Necromancer (class 10) Phase 2 batch 3 slice 3b: Army of the Dead")
    w("-- multi-minion limit (passives 61049/61050) and Meat Catapult (61048,")
    w("-- Thorium Grenade clone with the design cast/range/cooldown/values).")
    w("-- Generated by tools/generate_phase2_batch3_slice3b.py; re-runnable.")
    w("")
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i, _ in NEW_SPELLS))
    w("DELETE FROM `skill_line_ability` WHERE `skill_id` = %d AND `spell_id` IN (%s);" %
      (SKILL_LINE, ", ".join(str(i) for i in SPELLBOOK_SPELLS)))
    w("")

    w("-- ============================================================")
    w("-- spell_template rows (copies of the model spells, new entry ids)")
    w("-- ============================================================")
    for new_id, model_id in NEW_SPELLS:
        values = list(clone_row(args.mariadb, args.port, "spell_template", model_id))
        values[spell_entry_idx] = str(new_id)
        name, rank = NAME_OVERRIDES.get(new_id, (None, None))
        if name is not None:
            values[spell_cols.index("name")] = name
            values[spell_cols.index("nameSubtext")] = rank
        for column, value in COLUMN_OVERRIDES.get(new_id, {}).items():
            values[spell_cols.index(column)] = str(value)
        literals = [sql_literal(v, spell_types[c]) for v, c in zip(values, spell_cols)]
        w("INSERT INTO `spell_template` (`%s`) VALUES" % "`, `".join(spell_cols))
        w("  (%s);" % ", ".join(literals))
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
