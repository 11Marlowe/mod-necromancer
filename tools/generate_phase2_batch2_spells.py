#!/usr/bin/env python3
"""Generate the Necromancer Phase-2 batch-2 spell SQL (server side).

Batch 2 (disease mechanics) copies full `spell_template` rows of model spells
under new IDs, adds the rank chains and registers the spells under the
"Necromancy" skill line (700, class mask 512).  Rank 1 spells are NOT granted
at creation (levels 12+); the module auto-learns every spell/rank at the right
level (see src/mod_necromancer.cpp).

Model spells and edits:
  Call of the Grave R1-3 <- Corruption 6222/6223/7648   (dispel -> disease)
  Desecration R1-3       <- Rain of Fire 5740/6219/11677 (dispel -> disease)
  Disease Cloud          <- Flamestrike 2120            (dispel -> disease)
  Cripple                <- Cripple 89 (edited effects: 10% slow, -20 AP,
                           10 sec; original melee/ranged haste removed)
The Call of the Grave and Disease Cloud rows get `script_name` values that
bind the module's AuraScript/SpellScript (final-tick triple damage; cast
requires one of the caster's diseases on the target).

Negative values are written as plain SQL integer literals (server side is a
normal signed MariaDB column); the client patch YAML uses two's-complement
u32 literals because the DBC patcher reads DBC fields as u32.

Usage:
  python tools/generate_phase2_batch2_spells.py --out data/sql/world/20261014170000_world.sql
"""

import argparse
import subprocess
import sys

# new spell id -> model spell id copied from spell_template
NEW_SPELLS = [
    (61016, 6222),   # Call of the Grave Rank 1   <- Corruption Rank 2
    (61017, 6223),   # Call of the Grave Rank 2   <- Corruption Rank 3
    (61018, 7648),   # Call of the Grave Rank 3   <- Corruption Rank 4
    (61019, 5740),   # Desecration Rank 1         <- Rain of Fire Rank 1
    (61020, 6219),   # Desecration Rank 2         <- Rain of Fire Rank 2
    (61021, 11677),  # Desecration Rank 3         <- Rain of Fire Rank 3
    (61022, 2120),   # Disease Cloud              <- Flamestrike Rank 1
    (61023, 89),     # Cripple                    <- Cripple (mob version)
]

# (spell_id, prev_spell, first_spell, rank)
SPELL_CHAIN = [
    (61016, 0, 61016, 1),
    (61017, 61016, 61016, 2),
    (61018, 61017, 61016, 3),
    (61019, 0, 61019, 1),
    (61020, 61019, 61019, 2),
    (61021, 61020, 61019, 3),
]

# Server-side display name/rank overrides (spell_template name columns; the
# client reads its own Spell.dbc patch instead).
NAME_OVERRIDES = {
    61016: ("Call of the Grave", "Rank 1"),
    61017: ("Call of the Grave", "Rank 2"),
    61018: ("Call of the Grave", "Rank 3"),
    61019: ("Desecration", "Rank 1"),
    61020: ("Desecration", "Rank 2"),
    61021: ("Desecration", "Rank 3"),
    61022: ("Disease Cloud", ""),
    61023: ("Cripple", ""),
}

# spell_template column overrides applied after copying the model row.
# "dispel" 3 = disease.  The script names must match the module's
# AddNecromancerScripts() registrations exactly.
SPELL_SCRIPT_CALL_OF_THE_GRAVE = "spell_necromancer_call_of_the_grave"
SPELL_SCRIPT_DISEASE_CLOUD = "spell_necromancer_disease_cloud"

COLUMN_OVERRIDES = {
    61016: {"dispel": 3, "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
    61017: {"dispel": 3, "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
    61018: {"dispel": 3, "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
    61019: {"dispel": 3},
    61020: {"dispel": 3},
    61021: {"dispel": 3},
    61022: {"dispel": 3, "script_name": SPELL_SCRIPT_DISEASE_CLOUD},
    61023: {
        # design values: -10% movement speed, -20 attack power, 10 seconds.
        # CalculateSimpleValue = EffectBasePoints + EffectBaseDice, so store
        # one less than the intended magnitude (baseDice stays 1).
        "durationIndex": 1,            # SpellDuration.dbc index 1 = 10000 ms
        "effectApplyAuraName1": 33,    # SPELL_AURA_MOD_DECREASE_SPEED
        "effectBasePoints1": -11,      # -10 %
        "effectApplyAuraName2": 99,    # SPELL_AURA_MOD_ATTACK_POWER
        "effectBasePoints2": -21,      # -20 attack power
        # drop the model's third effect (ranged haste) entirely
        "effect3": 0,
        "effectDieSides3": 0,
        "effectBaseDice3": 0,
        "effectBasePoints3": 0,
        "effectApplyAuraName3": 0,
        "effectImplicitTargetA3": 0,
        # the model's tooltip text describes the old effects; replace it
        "description": "Cripples the target, reducing its movement speed by "
                       "$s1% and its attack power by $s2 for $d.",
        "auraDescription": "Movement speed reduced by $s1%.  Attack power "
                           "reduced by $s2.",
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
    w("-- FILE: 20261014170000_world.sql")
    w("-- Necromancer (class 10) Phase 2 batch 2: disease mechanics --")
    w("-- Call of the Grave R1-3 (61016-61018), Desecration R1-3 (61019-61021),")
    w("-- Disease Cloud (61022), Cripple (61023).  Generated by")
    w("-- tools/generate_phase2_batch2_spells.py; re-runnable.")
    w("-- Spell rows are full copies of the model spells' spell_template rows;")
    w("-- names/ranks and edited tooltips come from the client Spell.dbc patch.")
    w("")
    w("-- NOTE: expect no playercreateinfo changes - these spells are learned")
    w("-- by the module at level 12/20/24/34/46, not at creation.")
    w("")

    new_ids = [n for n, _ in NEW_SPELLS]
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i in new_ids))
    w("DELETE FROM `spell_chain` WHERE `spell_id` IN (%s);" %
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
    w("-- spell chains (ranks)")
    w("-- ============================================================")
    w("INSERT INTO `spell_chain` (`spell_id`, `prev_spell`, `first_spell`, `rank`, `req_spell`) VALUES")
    w(",\n".join(f"  ({s}, {p}, {f}, {r}, 0)" for s, p, f, r in SPELL_CHAIN) + ";")
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
