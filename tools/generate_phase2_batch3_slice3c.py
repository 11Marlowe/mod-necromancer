#!/usr/bin/env python3
"""Generate the Necromancer Phase-2 batch-3 (minions, slice 3c) rules SQL.

Slice 3c aligns the minion *mechanics* with the design spellbook (A.6):

* the four Corpse Bag items (item_template rows; server-side only in 1.12):
  Lump of Flesh (63100), Pile of Bones (63101), Ectoplasm (63102),
  Banshee Essence (63103);
* the corpse-class override table `necromancer_corpse_class` (+ seeds for the
  class's own minion creatures);
* Harvest (61029) description + Harvest aura (61030) rework: a 3-sec
  channel whose single tick stores the corpse as a bag item;
* Raise Wight (61040) becomes a *transform* (Renew-style friendly-target
  dummy) and gains the internal guardian-summon spell (61047) the transform
  uses for non-tethered minions;
* design cast times for the raise spells (Zombie/Ghoul/Skeleton/Banshee 5 s,
  Shade 3 s, Wraith/Bloodmage/Wight 8 s, Abomination 10 s).

Usage:
  python tools/generate_phase2_batch3_slice3c.py --out data/sql/world/20261017180000_world.sql
"""

import argparse
import subprocess
import sys

# new/replaced spell id -> model spell id
NEW_SPELLS = [
    (61029, 20577),  # Harvest (cast) - description update
    (61030, 20578),  # Harvest aura  - 3 s channel, stores the corpse
    (61040, 139),    # Raise Wight   - transform (Renew carrier)
    (61047, 12151),  # Raise Wight summon - internal guardian summon
]

NAME_OVERRIDES = {
    61029: ("Harvest", ""),
    61030: ("Harvest", ""),
    61040: ("Raise Wight", ""),
    61047: ("Raise Wight", ""),
}

SPELL_SCRIPT_RAISE_MINION = "spell_necromancer_raise_minion"
SPELL_SCRIPT_HARVEST = "spell_necromancer_harvest"
SPELL_SCRIPT_HARVEST_AURA = "spell_necromancer_harvest_aura"
SPELL_SCRIPT_RAISE_WIGHT = "spell_necromancer_raise_wight"

# The summon clones drop the model's dummy second effect (script target 38).
RAISE_DROP_SECOND_EFFECT = {
    "effect2": 0,
    "effectDieSides2": 0,
    "effectBaseDice2": 0,
    "effectBasePoints2": 0,
    "effectApplyAuraName2": 0,
    "effectImplicitTargetA2": 0,
}

# Tether-style dummy scaffold (Renew carrier).
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
    61029: {
        "description": "Harvests a nearby corpse, storing it in your Corpse "
                       "Bag to be Raised at a later time.",
        "script_name": SPELL_SCRIPT_HARVEST,
    },
    61030: {
        # 3-sec channel aura (SpellDuration index 27 = 3000 ms); the single
        # tick at expiry is caught by the module's AuraScript.  Amount 0
        # (-1 + baseDice 1) so the OBS_MOD_HEALTH scaffold ticks without
        # regenerating anything.
        "durationIndex": 27,
        "effectApplyAuraName1": 20,     # SPELL_AURA_OBS_MOD_HEALTH (amount 0)
        "effectBasePoints1": -1,
        "effectAmplitude1": 3000,
        "description": "",
        "auraDescription": "",
        "script_name": SPELL_SCRIPT_HARVEST_AURA,
    },
    61040: {
        "description": "Transforms your Zombie or Ghoul minion into a Wight "
                       "that will fight for you for 1 min. If used on a "
                       "Tethered minion, the minion will remain Tethered.",
        "durationIndex": 0,
        "castingTimeIndex": 170,        # SpellCastTimes index 170 = 8000 ms
        "spellIconId": 88,              # Death Coil's skull icon (placeholder)
        "script_name": SPELL_SCRIPT_RAISE_WIGHT,
        **DUMMY_EFFECT,
    },
    61047: {
        "description": "",
        "castingTimeIndex": 1,          # instant (triggered only)
        "effectMiscValue1": 11621,      # Spectral Corpse (Wight model)
        "effectImplicitTargetA1": 32,   # TARGET_LOCATION_UNIT_MINION_POSITION
        "script_name": SPELL_SCRIPT_RAISE_MINION,
        **RAISE_DROP_SECOND_EFFECT,
    },
}

# design cast times (SpellCastTimes.dbc indexes: 6=5 s, 14=3 s, 170=8 s, 7=10 s)
CAST_TIME_UPDATES = {
    61024: 6,    # Raise Ghoul
    61025: 6,    # Raise Skeleton
    61034: 6,    # Raise Zombie
    61035: 14,   # Raise Shade
    61036: 6,    # Raise Banshee
    61037: 170,  # Raise Wraith
    61038: 170,  # Raise Bloodmage
    61039: 7,    # Raise Abomination
}

# corpse items: (item id, name, display id) - cloned from Chunk of Boar Meat 769
ITEM_DONOR = 769
ITEMS = [
    (63100, "Lump of Flesh", 6348),
    (63101, "Pile of Bones", 13806),
    (63102, "Ectoplasm", 24211),
    (63103, "Banshee Essence", 23291),
]

# module override table seeds: entry -> corpse class flags
# (SKELETAL=1, SPECTRAL=2, ZOMBIE=4, GHOUL=8, BANSHEE=16)
CORPSE_CLASS_SEEDS = [
    (846, 8),      # Ghoul
    (1501, 4),     # Mindless Zombie (Zombie tier)
    (6412, 1),     # Skeleton
    (7370, 2),     # Restless Shade
    (10463, 18),   # Shrieking Banshee (BANSHEE|SPECTRAL)
    (1800, 2),     # Cold Wraith
    (11621, 2),    # Spectral Corpse (Wight model)
    (8526, 0),     # Dark Caster (corporeal -> Lump of Flesh)
    (8545, 0),     # Abomination (corporeal -> Lump of Flesh)
]


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
    item_cols, item_types = table_columns(args.mariadb, args.port, "item_template")
    spell_entry_idx = spell_cols.index("entry")
    item_entry_idx = item_cols.index("entry")

    print(f"spell_template: {len(spell_cols)} cols, item_template: {len(item_cols)} cols",
          file=sys.stderr)

    out = []
    w = out.append
    w("-- FILE: 20261017180000_world.sql")
    w("-- Necromancer (class 10) Phase 2 batch 3 slice 3c: minion rules --")
    w("-- corpse taxonomy + Corpse Bag items, raise requirements, Harvest")
    w("-- channel, Wight transform, design cast times.")
    w("-- Generated by tools/generate_phase2_batch3_slice3c.py; re-runnable.")
    w("")
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i, _ in NEW_SPELLS))
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
    w("-- design cast times for the raise spells")
    w("-- ============================================================")
    for spell_id, time_index in sorted(CAST_TIME_UPDATES.items()):
        w("UPDATE `spell_template` SET `castingTimeIndex` = %d WHERE `entry` = %d;" %
          (time_index, spell_id))
    w("")

    w("-- ============================================================")
    w("-- Corpse Bag items (clones of item 769; icons reused, no client patch)")
    w("-- ============================================================")
    w("DELETE FROM `item_template` WHERE `entry` IN (%s);" %
      ", ".join(str(i) for i, _, _ in ITEMS))
    for item_id, name, display_id in ITEMS:
        values = list(clone_row(args.mariadb, args.port, "item_template", ITEM_DONOR))
        values[item_entry_idx] = str(item_id)
        values[item_cols.index("name")] = name
        values[item_cols.index("display_id")] = str(display_id)
        values[item_cols.index("stackable")] = "20"
        values[item_cols.index("quality")] = "1"
        values[item_cols.index("buy_price")] = "0"
        values[item_cols.index("sell_price")] = "0"
        values[item_cols.index("flags")] = "0"
        if "description" in item_cols:
            values[item_cols.index("description")] = ""
        literals = [sql_literal(v, item_types[c]) for v, c in zip(values, item_cols)]
        w("INSERT INTO `item_template` (`%s`) VALUES" % "`, `".join(item_cols))
        w("  (%s);" % ", ".join(literals))
        w("")

    w("-- ============================================================")
    w("-- corpse-class override table (optional; heuristics run otherwise)")
    w("-- flags: 1 skeletal, 2 spectral, 4 zombie, 8 ghoul, 16 banshee, 32 female")
    w("-- ============================================================")
    w("CREATE TABLE IF NOT EXISTS `necromancer_corpse_class` (")
    w("  `entry` mediumint(8) unsigned NOT NULL,")
    w("  `flags` tinyint(3) unsigned NOT NULL DEFAULT 0,")
    w("  PRIMARY KEY (`entry`)")
    w(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;")
    w("DELETE FROM `necromancer_corpse_class` WHERE `entry` IN (%s);" %
      ", ".join(str(e) for e, _ in CORPSE_CLASS_SEEDS))
    w("INSERT INTO `necromancer_corpse_class` (`entry`, `flags`) VALUES")
    w(",\n".join(f"  ({e}, {f})" for e, f in CORPSE_CLASS_SEEDS) + ";")
    w("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
