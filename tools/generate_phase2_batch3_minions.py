#!/usr/bin/env python3
"""Generate the Necromancer Phase-2 batch-3 (minions, slice 1) spell SQL.

Slice 1 ships three spells:
  Raise Ghoul     (61024, L14) - guardian summon of creature 846 (Ghoul)
  Raise Skeleton  (61025, L14) - guardian summon of creature 6412 (Skeleton)
  Tether          (61026, L20) - dummy spell; the module converts the target
                                 guardian into a permanent, controllable pet

`Raise` spells clone `Summon Atal'ai Skeleton` (12151: 1 sec cast, 150 mana,
60 sec duration) with the summoned creature entry and the implicit target
mode edited (32 = at the minion position near the caster; the model's mode 46
requires a `spell_script_target` row we do not want).  The model's second
(dummy) effect is dropped: its script target (mode 38) has no row for the
clones, which made every cast fail with "Invalid target".  `Tether` clones `Renew`
(139) because it is an instant, friendly-unit-target spell; its effect is
replaced by a DUMMY and the module's SpellScript does the work
(`spell_template.script_name`).

Usage:
  python tools/generate_phase2_batch3_minions.py --out data/sql/world/20261014180000_world.sql
"""

import argparse
import subprocess
import sys

# new spell id -> model spell id copied from spell_template
NEW_SPELLS = [
    (61024, 12151),  # Raise Ghoul     <- Summon Atal'ai Skeleton
    (61025, 12151),  # Raise Skeleton  <- Summon Atal'ai Skeleton
    (61026, 139),    # Tether          <- Renew (friendly-target carrier)
]

# Server-side display name/rank overrides (spell_template name columns; the
# client reads its own Spell.dbc patch instead).
NAME_OVERRIDES = {
    61024: ("Raise Ghoul", ""),
    61025: ("Raise Skeleton", ""),
    61026: ("Tether", ""),
}

# script_name values must match the registrations in
# AddNecromancerScripts() (src/mod_necromancer.cpp).
SPELL_SCRIPT_RAISE_MINION = "spell_necromancer_raise_minion"
SPELL_SCRIPT_TETHER = "spell_necromancer_tether"

# creature_template entries the Raise spells summon (vanilla undead models)
CREATURE_GHOUL = 846
CREATURE_SKELETON = 6412

# The model's second effect (a DUMMY on Atal'ai mobs) targets
# TARGET_UNIT_SCRIPT_NEAR_CASTER (38), which resolves through the
# spell_script_target table.  Only the model (12151) has such a row, so the
# clones failed at cast time with SPELL_FAILED_BAD_TARGETS ("Invalid target").
# The Raise spells do not need that effect, so it is dropped.
RAISE_DROP_SECOND_EFFECT = {
    "effect2": 0,
    "effectDieSides2": 0,
    "effectBaseDice2": 0,
    "effectBasePoints2": 0,
    "effectApplyAuraName2": 0,
    "effectImplicitTargetA2": 0,
}

COLUMN_OVERRIDES = {
    61024: {
        "description": "Raises a ghoul to fight for you for $d.",
        "effectMiscValue1": CREATURE_GHOUL,
        "effectImplicitTargetA1": 32,   # TARGET_LOCATION_UNIT_MINION_POSITION
        "script_name": SPELL_SCRIPT_RAISE_MINION,
        **RAISE_DROP_SECOND_EFFECT,
    },
    61025: {
        "description": "Raises a skeleton to fight for you for $d.",
        "effectMiscValue1": CREATURE_SKELETON,
        "effectImplicitTargetA1": 32,
        "script_name": SPELL_SCRIPT_RAISE_MINION,
        **RAISE_DROP_SECOND_EFFECT,
    },
    61026: {
        "description": "Tethers your undead minion to act as a permanent, "
                       "controllable pet. Only one minion can be tethered at "
                       "a time.",
        # friendly-unit target, but no aura/duration of its own: the module
        # replaces the target guardian with a real (permanent) pet.
        "durationIndex": 0,
        "effect1": 3,            # SPELL_EFFECT_DUMMY
        "effectDieSides1": 0,
        "effectBaseDice1": 0,
        "effectBasePoints1": 0,
        "effectApplyAuraName1": 0,
        "effectAmplitude1": 0,
        "effectMiscValue1": 0,
        "spellIconId": 1500,     # Enslave Demon's icon (chains)
        "script_name": SPELL_SCRIPT_TETHER,
    },
}

SKILL_LINE = 700          # "Necromancy"
CLASS_MASK = 512          # class 10


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
    w("-- FILE: 20261014180000_world.sql")
    w("-- Necromancer (class 10) Phase 2 batch 3 (minions, slice 1):")
    w("-- Raise Ghoul (61024), Raise Skeleton (61025), Tether (61026).")
    w("-- Generated by tools/generate_phase2_batch3_minions.py; re-runnable.")
    w("--")
    w("-- Raise Ghoul/Skeleton are guardian summons (SPELL_EFFECT_SUMMON_GUARDIAN)")
    w("-- of creature 846/6412; the module re-levels/scales the minion to the")
    w("-- caster (script_name spell_necromancer_raise_minion).")
    w("-- Tether is a friendly-target dummy spell; the module replaces the")
    w("-- target guardian with a permanent, controllable pet")
    w("-- (script_name spell_necromancer_tether).")
    w("")
    w("-- NOTE: no playercreateinfo and no spell_chain changes - all three are")
    w("-- single-rank and learned by the module at level 14/14/20.")
    w("")

    new_ids = [n for n, _ in NEW_SPELLS]
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i in new_ids))
    w("DELETE FROM `skill_line_ability` WHERE `skill_id` = %d AND `spell_id` IN (%s);" %
      (SKILL_LINE, ", ".join(str(i) for i in new_ids)))
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
    w("-- skill_line_ability rows (Necromancy, class mask 512)")
    w("-- ============================================================")
    next_id = int(run(args.mariadb, args.port,
                      "SELECT IFNULL(MAX(`id`), 0) + 1 FROM skill_line_ability")[0][0])
    w("INSERT INTO `skill_line_ability` (`id`, `skill_id`, `spell_id`, `race_mask`, `class_mask`, "
      "`req_skill_value`, `superseded_by_spell`, `learn_on_get_skill`, `max_value`, `min_value`, "
      "`req_train_points`) VALUES")
    rows = []
    for spell_id in new_ids:
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
