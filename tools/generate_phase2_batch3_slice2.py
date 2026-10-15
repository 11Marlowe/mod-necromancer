#!/usr/bin/env python3
"""Generate the Necromancer Phase-2 batch-3 (minions, slice 2) spell SQL.

Slice 2 ships minion control and minion actives:

  Ravage           (61027, pet ability) - cloned from Lash of Pain 7814;
                                  learned by the raised minions through
                                  `petcreateinfo_spell` (creature 846/6412)
  Sacrifice Minion (61028, L20) - cloned from Renew 139; the module heals the
                                  caster (doubled on the tethered minion),
                                  grants a per-minion-type Death Pact buff and
                                  despawns the minion
  Harvest          (61029, L10) - cloned from Cannibalize 20577; the module
                                  finds the corpse and applies the mana-
                                  regeneration aura (61030)
  Harvest aura     (61030)      - cloned from Cannibalize 20578 (health ->
                                  mana regeneration)
  Death Pact (Ghoul)    (61031) - +2% physical damage done (30 min; canceled
                                  by raising/tethering a new minion)
  Death Pact (Skeleton) (61032) - -2% physical damage taken (30 min)
  Ghoul Frenzy     (61033, L20) - cloned from Renew 139; breaks crowd control
                                  on the tethered minion, +25% melee/casting
                                  speed and a heal of 50% max health over
                                  30 sec (amount computed by the module)

The three player spells get `skill_line_ability` rows (Necromancy, class
mask 512); Ravage and the internal auras do not (pet abilities are learned
via `petcreateinfo_spell`, the auras are applied by scripts).

Usage:
  python tools/generate_phase2_batch3_slice2.py --out data/sql/world/20261015120000_world.sql
"""

import argparse
import subprocess
import sys

# new spell id -> model spell id copied from spell_template
NEW_SPELLS = [
    (61027, 7814),   # Ravage              <- Lash of Pain (pet ability)
    (61028, 139),    # Sacrifice Minion    <- Renew (friendly-target carrier)
    (61029, 20577),  # Harvest             <- Cannibalize
    (61030, 20578),  # Harvest aura        <- Cannibalize (aura)
    (61031, 20578),  # Death Pact (Ghoul)  <- Cannibalize (aura scaffold)
    (61032, 20578),  # Death Pact (Skeleton)
    (61033, 139),    # Ghoul Frenzy        <- Renew (friendly-target carrier)
]

# Server-side display name/rank overrides (spell_template name columns; the
# client reads its own Spell.dbc patch instead).
NAME_OVERRIDES = {
    61027: ("Ravage", ""),
    61028: ("Sacrifice Minion", ""),
    61029: ("Harvest", ""),
    61030: ("Harvest", ""),
    61031: ("Death Pact", ""),
    61032: ("Death Pact", ""),
    61033: ("Ghoul Frenzy", ""),
}

# script_name values must match the registrations in
# AddNecromancerScripts() (src/mod_necromancer.cpp).
SPELL_SCRIPT_SACRIFICE_MINION = "spell_necromancer_sacrifice_minion"
SPELL_SCRIPT_HARVEST = "spell_necromancer_harvest"
SPELL_SCRIPT_GHOUL_FRENZY = "spell_necromancer_ghoul_frenzy"

# creature_template entries the Raise spells summon (vanilla undead models)
CREATURE_GHOUL = 846
CREATURE_SKELETON = 6412

# The Raise clones' model (Summon Atal'ai Skeleton 12151) has a dummy second
# effect whose script target needs a `spell_script_target` row; the Tether/
# Sacrifice pattern replaces the carrier spell's single effect with a dummy.
DUMMY_EFFECT = {
    "effect1": 3,            # SPELL_EFFECT_DUMMY
    "effectDieSides1": 0,
    "effectBaseDice1": 0,
    "effectBasePoints1": 0,
    "effectApplyAuraName1": 0,
    "effectAmplitude1": 0,
    "effectMiscValue1": 0,
}

COLUMN_OVERRIDES = {
    61027: {
        "description": "Ravages an enemy, dealing $s1 Shadow damage.",
    },
    61028: {
        "description": "Sacrifices your minion, healing you and granting you a "
                       "Death Pact effect. The healing is doubled when used "
                       "on your tethered minion.",
        "auraDescription": "",   # drop Renew's periodic-heal text
        "durationIndex": 0,
        "spellIconId": 1488,   # Demonic Sacrifice's icon
        "script_name": SPELL_SCRIPT_SACRIFICE_MINION,
        **DUMMY_EFFECT,
    },
    61029: {
        "description": "Harvests a nearby humanoid or undead corpse, "
                       "restoring mana over 10 seconds.",
        "script_name": SPELL_SCRIPT_HARVEST,   # replaces spell_cannibalize
    },
    61030: {
        # Cannibalize aura 20578 restores health; ours restores mana
        "effectApplyAuraName1": 21,   # SPELL_AURA_OBS_MOD_MANA
        "description": "",
        "auraDescription": "Restores $s1% of total mana every $t1 seconds.",
        "script_name": "",             # drop spell_cannibalize_aura
    },
    61031: {
        # Death Pact (Ghoul): +2% physical damage done for 30 min
        "durationIndex": 30,           # SpellDuration.dbc index 30 = 1800000 ms
        "dispel": 0,
        # the Cannibalize scaffold interrupts on damage / channels; a pact
        # buff must do neither
        "attributesEx": 0,
        "auraInterruptFlags": 0,
        "effectApplyAuraName1": 79,    # SPELL_AURA_MOD_DAMAGE_PERCENT_DONE
        "effectMiscValue1": 1,         # physical school
        "effectBasePoints1": 1,        # +2% (basePoints + baseDice)
        "effectAmplitude1": 0,
        "spellIconId": 88,             # Death Coil's skull icon
        "description": "",
        "auraDescription": "Increases your physical damage done by $s1%.",
        "script_name": "",
    },
    61032: {
        # Death Pact (Skeleton): -2% physical damage taken for 30 min
        "durationIndex": 30,
        "dispel": 0,
        "attributesEx": 0,
        "auraInterruptFlags": 0,
        "effectApplyAuraName1": 87,    # SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN
        "effectMiscValue1": 1,         # physical school
        "effectBasePoints1": -3,       # -2% (basePoints + baseDice)
        "effectAmplitude1": 0,
        "spellIconId": 88,
        "description": "",
        "auraDescription": "Reduces physical damage taken by $s1%.",
        "script_name": "",
    },
    61033: {
        # Ghoul Frenzy: Renew scaffold, three self-auras on the minion
        "durationIndex": 2,            # SpellDuration.dbc index 2 = 30000 ms
        "description": "Sends your tethered minion into a frenzy, breaking "
                       "all crowd control effects, increasing its melee and "
                       "casting speed by $s1% and healing it for 50% of its "
                       "health over $d.",
        "auraDescription": "Melee and casting speed increased by $s1%. "
                           "Healing $s3% of maximum health every $t3 sec.",
        "effect1": 6,                  # SPELL_EFFECT_APPLY_AURA
        "effectApplyAuraName1": 138,   # SPELL_AURA_MOD_MELEE_HASTE
        "effectBasePoints1": 24,       # +25% (basePoints + baseDice)
        "effectAmplitude1": 0,
        "effect2": 6,
        "effectDieSides2": 1,
        "effectBaseDice2": 1,
        "effectBasePoints2": 24,       # +25% casting speed
        "effectImplicitTargetA2": 21,  # friendly unit target (as effect 1)
        "effectApplyAuraName2": 65,    # SPELL_AURA_MOD_CASTING_SPEED_NOT_STACK
        "effectAmplitude2": 0,
        "effect3": 6,
        "effectDieSides3": 1,
        "effectBaseDice3": 1,
        "effectBasePoints3": 4,        # placeholder; the module computes 5%/tick
        "effectImplicitTargetA3": 21,
        "effectApplyAuraName3": 8,     # SPELL_AURA_PERIODIC_HEAL
        "effectAmplitude3": 3000,
        "spellIconId": 957,            # Frenzy icon
        "script_name": SPELL_SCRIPT_GHOUL_FRENZY,
    },
}

# pet abilities: creature entry -> spell learned by the tethered pet
PET_CREATE_SPELLS = [
    (CREATURE_GHOUL, 61027),
    (CREATURE_SKELETON, 61027),
]

# player spells that appear in the Necromancy spellbook tab
SKILL_LINE = 700          # "Necromancy"
CLASS_MASK = 512          # class 10
SPELLBOOK_SPELLS = [61028, 61029, 61033]

NEW_IDS = [n for n, _ in NEW_SPELLS] + [PET_CREATE_SPELLS[0][1]]


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
    w("-- FILE: 20261015120000_world.sql")
    w("-- Necromancer (class 10) Phase 2 batch 3 (minions, slice 2):")
    w("-- Ravage (61027, pet ability), Sacrifice Minion (61028), Harvest")
    w("-- (61029) + Harvest aura (61030), Death Pact Ghoul/Skeleton")
    w("-- (61031/61032) and Ghoul Frenzy (61033).")
    w("-- Generated by tools/generate_phase2_batch3_slice2.py; re-runnable.")
    w("--")
    w("-- Ravage is learned by the raised minions (creature 846/6412) through")
    w("-- `petcreateinfo_spell`; the tethered pet counts as permanent after")
    w("-- the class descriptor's permanentSummonPetTypes is set by the module")
    w("-- (C++, no SQL column).")
    w("")
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i in NEW_IDS))
    w("DELETE FROM `skill_line_ability` WHERE `skill_id` = %d AND `spell_id` IN (%s);" %
      (SKILL_LINE, ", ".join(str(i) for i in SPELLBOOK_SPELLS)))
    w("DELETE FROM `petcreateinfo_spell` WHERE `entry` IN (%d, %d);" %
      (CREATURE_GHOUL, CREATURE_SKELETON))
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
    w("-- petcreateinfo_spell (the tethered minions' active: Ravage)")
    w("-- ============================================================")
    rows = []
    for entry, spell_id in PET_CREATE_SPELLS:
        rows.append(f"  ({entry}, {spell_id}, 0, 0, 0)")
    w("INSERT INTO `petcreateinfo_spell` (`entry`, `spell1`, `spell2`, `spell3`, `spell4`) VALUES")
    w(",\n".join(rows) + ";")
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
