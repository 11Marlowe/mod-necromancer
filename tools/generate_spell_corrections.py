#!/usr/bin/env python3
"""Generate the Necromancer spell-correction pass SQL + the client YAML fragment.

The pass aligns the shipped placeholder spells with the design spellbook blobs
A.6-A.9 (found 2026-10-17) and fixes finding A72:

* Plague Bolt R1-3 (61010-61012): Nature damage (was Shadow) and applies the
  new **Toxic Plague** disease (61071-61073, Nature DoT over 15 s) on hit; the
  module also adds the design's +3% direct damage per disease on the target.
* Reap R1-2 (61013/61014): no longer a Raptor Strike (on-next-swing, physical)
  clone - it is now a Shadow-damage life-steal (health leech, heals the caster
  for 100% of the damage), instant, 10 yd, 8 s cooldown, high threat (the
  module adds extra threat).  Donor: Death Coil 6789 (health leech effect).
* Call of the Grave R1-3 (61016-61018): instant cast and 24 s duration
  (Grave Rot; the final tick still deals triple damage via the module
  AuraScript).
* Cripple (61023): no cooldown (the model's 30 s is removed).
* Harvest (61029): `targetCreatureType` 96 -> 0 so beast corpses can be
  harvested (finding A72; the module's own corpse taxonomy still gates the
  item types).  The client check made a selected beast corpse fail with
  "Invalid target"; an unselected one was silently dropped.
* Ghoul Frenzy (61033): 1.5 min cooldown (design A.6).
* Death Coil (new 61074, replaces the shared Warlock 6789 for this class):
  X-Y Shadow damage to an enemy or heals an Undead minion, 2.5 s cast, 30 yd,
  no cooldown.  The fear effect of the warlock spell is dropped; the module
  script routes friendly casts to a heal.  The server `skill_line_ability`
  row and the client `SkillLineAbility.dbc` row 7217 are repointed.

All rows are full copies of a donor `spell_template` row (DELETE + INSERT, so
re-running is idempotent); the SQL must run *after* the earlier batch SQL
(same as every other migration in data/sql/world).

Usage:
  python tools/generate_spell_corrections.py \
      --out data/sql/world/20261019120000_world.sql \
      --yaml-out ../tmp-corrections-yaml.txt
"""

import argparse
import re
import subprocess
import sys

SQL_FILE = "20261019120000_world.sql"

SPELL_SCRIPT_PLAGUE_BOLT = "spell_necromancer_plague_bolt"
SPELL_SCRIPT_REAP = "spell_necromancer_reap"
SPELL_SCRIPT_DEATH_COIL = "spell_necromancer_death_coil"
SPELL_SCRIPT_CALL_OF_THE_GRAVE = "spell_necromancer_call_of_the_grave"
SPELL_SCRIPT_HARVEST = "spell_necromancer_harvest"
SPELL_SCRIPT_GHOUL_FRENZY = "spell_necromancer_ghoul_frenzy"


def zero_effect(n):
    """Zero every effect column of one effect slot (the clones drop it)."""
    fields = ["effect%d" % n, "effectDieSides%d" % n, "effectBaseDice%d" % n,
              "effectDicePerLevel%d" % n, "effectRealPointsPerLevel%d" % n,
              "effectBasePoints%d" % n, "effectBonusCoefficient%d" % n,
              "effectMechanic%d" % n, "effectImplicitTargetA%d" % n,
              "effectImplicitTargetB%d" % n, "effectRadiusIndex%d" % n,
              "effectApplyAuraName%d" % n, "effectAmplitude%d" % n,
              "effectMultipleValue%d" % n, "effectChainTarget%d" % n,
              "effectItemType%d" % n, "effectMiscValue%d" % n,
              "effectTriggerSpell%d" % n, "effectPointsPerComboPoint%d" % n]
    return {f: 0 for f in fields}


# Design values (see the design doc A.6-A.9 and the impact note).  `mode`
# controls only the client YAML: "update" patches the existing row in place,
# "copy" emits a fresh copy block (new or fully reworked spell).
SPELLS = [
    # ---- Plague Bolt R1-3: Nature + Toxic Plague rider (A.9) ----
    dict(id=61010, donor=686, mode="update", name="Plague Bolt", rank="Rank 1",
         server={"school": 3, "castingTimeIndex": 14,
                 "script_name": SPELL_SCRIPT_PLAGUE_BOLT},
         yaml={"School": 3, "CastingTimeIndex": 14},
         desc="Hurls a bolt of plague at an enemy, inflicting $s1 Nature "
              "damage and infecting it with Toxic Plague.  Damage increased "
              "by 3% per disease on the target."),
    dict(id=61011, donor=695, mode="update", name="Plague Bolt", rank="Rank 2",
         server={"school": 3, "castingTimeIndex": 14,
                 "script_name": SPELL_SCRIPT_PLAGUE_BOLT},
         yaml={"School": 3, "CastingTimeIndex": 14},
         desc="Hurls a bolt of plague at an enemy, inflicting $s1 Nature "
              "damage and infecting it with Toxic Plague.  Damage increased "
              "by 3% per disease on the target."),
    dict(id=61012, donor=705, mode="update", name="Plague Bolt", rank="Rank 3",
         server={"school": 3, "castingTimeIndex": 14,
                 "script_name": SPELL_SCRIPT_PLAGUE_BOLT},
         yaml={"School": 3, "CastingTimeIndex": 14},
         desc="Hurls a bolt of plague at an enemy, inflicting $s1 Nature "
              "damage and infecting it with Toxic Plague.  Damage increased "
              "by 3% per disease on the target."),
    # ---- Reap R1-2: Shadow life-steal (A.8; not Raptor Strike) ----
    dict(id=61013, donor=6789, mode="copy", name="Reap", rank="Rank 1",
         server={"rangeIndex": 7, "recoveryTime": 8000, "category": 0,
                 "categoryRecoveryTime": 0, "manaCost": 15, "spellIconId": 26,
                 "attributesEx2": 0, "script_name": SPELL_SCRIPT_REAP,
                 "baseLevel": 1, "spellLevel": 1, "maxLevel": 0,
                 "effectDieSides1": 4, "effectBasePoints1": 9,
                 **zero_effect(2)},
         desc="Steals $s1 life from the target, causing Shadow damage.  "
              "Generates a high amount of threat.",
         aura_desc=""),
    dict(id=61014, donor=6789, mode="copy", name="Reap", rank="Rank 2",
         server={"rangeIndex": 7, "recoveryTime": 8000, "category": 0,
                 "categoryRecoveryTime": 0, "manaCost": 25, "spellIconId": 26,
                 "attributesEx2": 0, "script_name": SPELL_SCRIPT_REAP,
                 "baseLevel": 1, "spellLevel": 1, "maxLevel": 0,
                 "effectDieSides1": 8, "effectBasePoints1": 30,
                 **zero_effect(2)},
         desc="Steals $s1 life from the target, causing Shadow damage.  "
              "Generates a high amount of threat.",
         aura_desc=""),
    # ---- Call of the Grave R1-3: Grave Rot lasts 24 s (A.9) ----
    dict(id=61016, donor=6222, mode="update", name="Call of the Grave",
         rank="Rank 1",
         server={"dispel": 3, "durationIndex": 106, "castingTimeIndex": 1,
                 "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
         yaml={"DurationIndex": 106, "CastingTimeIndex": 1},
         desc="Infects the target with Grave Rot, causing $*8;s1 Shadow "
              "damage over $d.  The final tick deals triple damage."),
    dict(id=61017, donor=6223, mode="update", name="Call of the Grave",
         rank="Rank 2",
         server={"dispel": 3, "durationIndex": 106, "castingTimeIndex": 1,
                 "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
         yaml={"DurationIndex": 106, "CastingTimeIndex": 1},
         desc="Infects the target with Grave Rot, causing $*8;s1 Shadow "
              "damage over $d.  The final tick deals triple damage."),
    dict(id=61018, donor=7648, mode="update", name="Call of the Grave",
         rank="Rank 3",
         server={"dispel": 3, "durationIndex": 106, "castingTimeIndex": 1,
                 "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
         yaml={"DurationIndex": 106, "CastingTimeIndex": 1},
         desc="Infects the target with Grave Rot, causing $*8;s1 Shadow "
              "damage over $d.  The final tick deals triple damage."),
    # ---- Cripple: design says no cooldown (A.9) ----
    dict(id=61023, donor=89, mode="update", name="Cripple", rank="",
         server={"durationIndex": 1, "recoveryTime": 0,
                 "effectApplyAuraName1": 33, "effectBasePoints1": -11,
                 "effectApplyAuraName2": 99, "effectBasePoints2": -21,
                 "effect3": 0, "effectDieSides3": 0, "effectBaseDice3": 0,
                 "effectBasePoints3": 0, "effectApplyAuraName3": 0,
                 "effectImplicitTargetA3": 0,
                 "description": "Cripples the target, reducing its movement "
                                "speed by $s1% and its attack power by $s2 "
                                "for $d.",
                 "auraDescription": "Movement speed reduced by $s1%.  Attack "
                                    "power reduced by $s2."},
         yaml={"RecoveryTime": 0},
         desc="Cripples the target, reducing its movement speed by $s1% and "
              "its attack power by $s2 for $d.",
         aura_desc="Movement speed reduced by $s1%.  Attack power reduced by "
                   "$s2."),
    # ---- Harvest: beast corpses (A72) ----
    dict(id=61029, donor=20577, mode="update", name="Harvest", rank="",
         server={"targetCreatureType": 0,
                 "description": "Harvests a nearby corpse, storing it in your "
                                "Corpse Bag to be Raised at a later time.",
                 "script_name": SPELL_SCRIPT_HARVEST},
         yaml={"TargetCreatureType": 0},
         desc="Harvests a nearby corpse, storing it in your Corpse Bag to be "
              "Raised at a later time."),
    # ---- Ghoul Frenzy: 1.5 min cooldown (A.6) ----
    dict(id=61033, donor=139, mode="update", name="Ghoul Frenzy", rank="",
         server={"durationIndex": 2, "recoveryTime": 90000,
                 "effect1": 6, "effectApplyAuraName1": 138,
                 "effectBasePoints1": 24, "effectAmplitude1": 0,
                 "effect2": 6, "effectDieSides2": 1, "effectBaseDice2": 1,
                 "effectBasePoints2": 24, "effectImplicitTargetA2": 21,
                 "effectApplyAuraName2": 65, "effectAmplitude2": 0,
                 "effect3": 6, "effectDieSides3": 1, "effectBaseDice3": 1,
                 "effectBasePoints3": 4, "effectImplicitTargetA3": 21,
                 "effectApplyAuraName3": 8, "effectAmplitude3": 3000,
                 "spellIconId": 957,
                 "description": "Sends your tethered minion into a frenzy, "
                                "breaking all crowd control effects, "
                                "increasing its melee and casting speed by "
                                "$s1% and healing it for 50% of its health "
                                "over $d.",
                 "auraDescription": "Melee and casting speed increased by "
                                    "$s1%. Healing $s3% of maximum health "
                                    "every $t3 sec.",
                 "script_name": SPELL_SCRIPT_GHOUL_FRENZY},
         yaml={"RecoveryTime": 90000},
         desc="Sends your tethered minion into a frenzy, breaking all crowd "
              "control effects, increasing its melee and casting speed by "
              "$s1% and healing it for 50% of its health over $d.",
         aura_desc="Melee and casting speed increased by $s1%. Healing $s3% "
                   "of maximum health every $t3 sec."),
    # ---- Toxic Plague R1-3 (new; the disease Plague Bolt applies) ----
    dict(id=61071, donor=6222, mode="copy", name="Toxic Plague", rank="Rank 1",
         server={"school": 3, "dispel": 3, "durationIndex": 8,
                 "effectBasePoints1": 3},
         desc="Infects the target with Toxic Plague, causing $*5;s1 Nature "
              "damage over $d.",
         aura_desc="$s1 Nature damage periodically."),
    dict(id=61072, donor=6223, mode="copy", name="Toxic Plague", rank="Rank 2",
         server={"school": 3, "dispel": 3, "durationIndex": 8,
                 "effectBasePoints1": 6},
         desc="Infects the target with Toxic Plague, causing $*5;s1 Nature "
              "damage over $d.",
         aura_desc="$s1 Nature damage periodically."),
    dict(id=61073, donor=7648, mode="copy", name="Toxic Plague", rank="Rank 3",
         server={"school": 3, "dispel": 3, "durationIndex": 8,
                 "effectBasePoints1": 11},
         desc="Infects the target with Toxic Plague, causing $*5;s1 Nature "
              "damage over $d.",
         aura_desc="$s1 Nature damage periodically."),
    # ---- Death Coil (new class spell; replaces the shared Warlock 6789) ----
    dict(id=61074, donor=6789, mode="copy", name="Death Coil", rank="",
         server={"castingTimeIndex": 19, "recoveryTime": 0,
                 "categoryRecoveryTime": 0, "category": 0,
                 "baseLevel": 1, "spellLevel": 1, "maxLevel": 0,
                 "effect1": 2, "effectImplicitTargetA1": 25,
                 "script_name": SPELL_SCRIPT_DEATH_COIL,
                 **zero_effect(2)},
         desc="Causes $s1 Shadow damage to an enemy target, or heals your "
              "Undead minion for $s1.",
         aura_desc=""),
]

# The Necromancer should no longer learn the shared Warlock Death Coil.
DEATH_COIL_OLD = 6789
DEATH_COIL_NEW = 61074


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
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
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


EFFECT_RENAMES = {
    "effectApplyAuraName": "EffectAura",
    "effectBasePoints": "EffectBasePoints",
    "effectDieSides": "EffectDieSides",
    "effectBaseDice": "EffectBaseDice",
    "effectDicePerLevel": "EffectDicePerLevel",
    "effectRealPointsPerLevel": "EffectRealPointsPerLevel",
    "effectMiscValue": "EffectMiscValue",
    "effectImplicitTargetA": "ImplicitTargetA",
    "effectImplicitTargetB": "ImplicitTargetB",
    "effectAmplitude": "EffectAmplitude",
    "effectChainTarget": "EffectChainTarget",
    "effectMultipleValue": "EffectMultipleValue",
    "effectMechanic": "EffectMechanic",
    "effectRadiusIndex": "EffectRadiusIndex",
    "effectItemType": "EffectItemType",
    "effectTriggerSpell": "EffectTriggerSpell",
    "effectPointsPerComboPoint": "EffectPointsPerCombo",
}

# DB-only columns (cmangos' table carries fields the 1.12 client DBC has no
# slot for); they are zeroed server-side but cannot appear in the YAML.
YAML_SKIP_SERVER_COLUMNS = {"effectBonusCoefficient2"}

COLUMN_RENAMES = {
    "manaCost": "ManaCost",
    "manaCostPercentage": "ManaCostPct",
    "stances": "ShapeshiftMask",
    "stancesNot": "ShapeshiftExclude",
    "durationIndex": "DurationIndex",
    "rangeIndex": "RangeIndex",
    "castingTimeIndex": "CastingTimeIndex",
    "recoveryTime": "RecoveryTime",
    "categoryRecoveryTime": "CategoryRecoveryTime",
    "category": "Category",
    "attributes": "Attributes",
    "attributesEx": "AttributesEx",
    "attributesEx2": "AttributesEx2",
    "school": "School",
    "dispel": "DispelType",
    "spellIconId": "SpellIconID",
    "targetCreatureType": "TargetCreatureType",
    "baseLevel": "BaseLevel",
    "spellLevel": "SpellLevel",
    "maxLevel": "MaxLevel",
}


def db_to_dbc(col):
    if col in COLUMN_RENAMES:
        return COLUMN_RENAMES[col]
    m = re.match(r"^effect(\d)$", col)
    if m:
        return "Effect_" + m.group(1)
    for prefix, repl in EFFECT_RENAMES.items():
        if col.startswith(prefix):
            n = col[len(prefix):]
            return repl + "_" + n
    return None


def lang_block(field, value):
    return ['      %s_lang_%d: "%s"' % (field, i, value) for i in range(8)]


def yaml_copy_block(spell):
    lines = []
    lines.append("  # %d <- %d: %s" % (spell["id"], spell["donor"],
                                       spell["name"]))
    lines.append("  - type: copy")
    lines.append("    key: %d" % spell["donor"])
    lines.append("    values:")
    lines.append("      ID: %d" % spell["id"])
    lines += lang_block("Name", spell["name"])
    lines += lang_block("NameSubtext", spell["rank"])
    lines += lang_block("Description", spell["desc"])
    if spell.get("aura_desc") is not None:
        lines += lang_block("AuraDescription", spell["aura_desc"])
    skip = ("description", "auraDescription", "script_name")
    for col, value in spell["server"].items():
        if col in skip or col in YAML_SKIP_SERVER_COLUMNS:
            continue
        field = db_to_dbc(col)
        if field is None:
            raise RuntimeError("no DBC name for %s" % col)
        if isinstance(value, int) and value < 0:
            value = value & 0xFFFFFFFF
        lines.append("      %s: %d" % (field, value))
    return "\n".join(lines)


def yaml_update_block(spell):
    lines = []
    lines.append("  # %d: %s" % (spell["id"], spell["name"]))
    lines.append("  - type: update")
    lines.append("    key: %d" % spell["id"])
    lines.append("    values:")
    lines += lang_block("Description", spell["desc"])
    for field, value in spell["yaml"].items():
        if isinstance(value, int) and value < 0:
            value = value & 0xFFFFFFFF
        lines.append("      %s: %d" % (field, value))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe")
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", required=True)
    ap.add_argument("--yaml-out", required=True)
    args = ap.parse_args()

    spell_cols, spell_types = table_columns(args.mariadb, args.port, "spell_template")
    entry_idx = spell_cols.index("entry")
    print(f"spell_template: {len(spell_cols)} cols", file=sys.stderr)

    out = []
    w = out.append
    w("-- FILE: %s" % SQL_FILE)
    w("-- Necromancer (class 10) spell-correction pass (2026-10-19): align the")
    w("-- shipped placeholder spells with the design spellbook blobs A.6-A.9 and")
    w("-- fix A72 - Plague Bolt (Nature + Toxic Plague), Reap (shadow life")
    w("-- steal), Call of the Grave (24 s Grave Rot), Cripple (no CD), Harvest")
    w("-- (beast corpses), Ghoul Frenzy (1.5 min CD), new Death Coil 61074.")
    w("-- Generated by tools/generate_spell_corrections.py; re-runnable.")
    w("-- Must run after the earlier batch SQL (data/sql/world filename order).")
    w("")
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(s["id"]) for s in SPELLS))
    w("")

    for spell in SPELLS:
        values = list(clone_row(args.mariadb, args.port, "spell_template",
                                spell["donor"]))
        values[entry_idx] = str(spell["id"])
        values[spell_cols.index("name")] = spell["name"]
        values[spell_cols.index("nameSubtext")] = spell["rank"]
        values[spell_cols.index("script_name")] = ""
        if spell.get("desc") is not None:
            values[spell_cols.index("description")] = spell["desc"]
        values[spell_cols.index("auraDescription")] = spell.get("aura_desc") or ""
        for column, value in spell["server"].items():
            if column in ("description", "auraDescription"):
                continue
            values[spell_cols.index(column)] = str(value)
        literals = [sql_literal(v, spell_types[c]) for v, c in zip(values, spell_cols)]
        w("-- %s (donor %d)" % (spell["name"] or spell["id"], spell["donor"]))
        w("INSERT INTO `spell_template` (`%s`) VALUES" % "`, `".join(spell_cols))
        w("  (%s);" % ", ".join(literals))
        w("")

    w("-- ============================================================")
    w("-- Death Coil: the class's own spell 61074 replaces the shared")
    w("-- Warlock 6789 in the Necromancy skill line (server table).")
    w("-- ============================================================")
    w("UPDATE `skill_line_ability` SET `spell_id` = %d "
      "WHERE `skill_id` = 700 AND `spell_id` = %d;" % (DEATH_COIL_NEW, DEATH_COIL_OLD))
    w("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    with open(args.yaml_out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# ---- spell-correction pass (2026-10-19, A.6-A.9 + A72) ----\n")
        f.write("# Updates patch the existing copy blocks above in place; the\n")
        f.write("# copy blocks below are the new/reworked spells (61013/14/71-74).\n")
        for spell in SPELLS:
            if spell["mode"] == "update":
                f.write(yaml_update_block(spell) + "\n")
            else:
                f.write(yaml_copy_block(spell) + "\n")

    print(f"wrote {args.out}", file=sys.stderr)
    print(f"wrote {args.yaml_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
