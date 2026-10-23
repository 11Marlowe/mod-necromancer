#!/usr/bin/env python3
"""Generate the Necromancer rider-fidelity batch (server SQL + client YAML).

Implements the four backlog items R1-R4 (see docs/Necromancer-Backlog.md):

  R1  Unholy Shield (61084): the design's "-50% spell damage taken for 8 s and
      prevents the application of harmful magical effects" instead of the
      Anti-Magic Shield clone's flat magic immunity.  The -50% is an aura 87
      (MOD_DAMAGE_PERCENT_TAKEN, magic school mask); the "prevents harmful
      magic" half has no 1.12 aura, so the module strips harmful auras that
      land while the shield is up (NecromancerUnholyShieldUnitScript).

  R2  Lich Armor (61085): "melee attackers may be slowed 30% for 5 s".  The
      armor spell already uses all three effect slots, so a hidden proc aura
      (61354, procFlags = melee swing/ability taken) applies the slow (61355)
      to the attacker.  The module casts/removes 61354 with the armor buff.

  R3  Will of the Death Knight (61091): "deal an additional 4% of your physical
      damage as Shadow damage".  Not expressible as data; the module adds the
      rider as a separate Shadow hit through the hidden damage spell 61356
      (NecromancerWillUnitScript).

  R4  Grave Rot: Call of the Grave's debuff used to be the cast spell itself,
      so the target's debuff read "Call of the Grave".  The disease is now its
      own aura spell (61351-61353, "Grave Rot", script-bound for the triple
      final tick); 61016-61018 become instant cast spells whose only effect
      triggers the matching Grave Rot rank.

Outputs:
  data/sql/world/20261023120000_world.sql
  client/patches/49f-rider-fidelity.yaml

Usage:
  python tools/generate_rider_fidelity.py

Requires the live world DB (the generators clone donor spell rows).
"""

import argparse
import re
import subprocess
import sys

SQL_FILE = "20261023120000_world.sql"

SPELL_SCRIPT_CALL_OF_THE_GRAVE = "spell_necromancer_call_of_the_grave"

DEFAULT_MARIADB = r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe"


def zero_effect(n):
    """Zero every effect column of one effect slot."""
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


GRAVE_ROT_AURA_DESC = ("Grave Rot: $s1 Shadow damage every $t1 sec.  "
                       "The final tick deals triple damage.")
GRAVE_ROT_CAST_DESC = ("Infects the target with Grave Rot, causing Shadow "
                       "damage every 3 sec for 24 sec.  The final tick deals "
                       "triple damage.")

# ---------------------------------------------------------------------------
# New spells: cloned from a donor and fully overridden (DELETE + INSERT).
# ---------------------------------------------------------------------------
INSERTS = [
    # ---- R4: the Grave Rot disease aura (the debuff the target sees) ----
    dict(id=61351, donor=6222, name="Grave Rot", rank="Rank 1",
         server={"spellIconId": 313, "durationIndex": 106,
                 "castingTimeIndex": 1, "manaCost": 0, "dispel": 3,
                 "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
         desc="Causes $s1 Shadow damage every $t1 sec for $d.  "
              "The final tick deals triple damage.",
         aura_desc=GRAVE_ROT_AURA_DESC),
    dict(id=61352, donor=6223, name="Grave Rot", rank="Rank 2",
         server={"spellIconId": 313, "durationIndex": 106,
                 "castingTimeIndex": 1, "manaCost": 0, "dispel": 3,
                 "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
         desc="Causes $s1 Shadow damage every $t1 sec for $d.  "
              "The final tick deals triple damage.",
         aura_desc=GRAVE_ROT_AURA_DESC),
    dict(id=61353, donor=7648, name="Grave Rot", rank="Rank 3",
         server={"spellIconId": 313, "durationIndex": 106,
                 "castingTimeIndex": 1, "manaCost": 0, "dispel": 3,
                 "script_name": SPELL_SCRIPT_CALL_OF_THE_GRAVE},
         desc="Causes $s1 Shadow damage every $t1 sec for $d.  "
              "The final tick deals triple damage.",
         aura_desc=GRAVE_ROT_AURA_DESC),
    # ---- R2: Lich Armor's hidden melee-attacker proc carrier ----
    # Cloned from Bone Armor (61015) because it already carries the
    # "taken hit -> trigger a hidden spell on the attacker" shape.
    dict(id=61354, donor=61015, name="Lich Armor", rank="",
         server={"spellIconId": 182, "durationIndex": 30,
                 "castingTimeIndex": 1, "manaCost": 0, "dispel": 0,
                 "attributes": 192, "attributesEx": 0, "attributesEx2": 0,
                 "procFlags": 40, "procChance": 25, "procCharges": 0,
                 "recoveryTime": 0, "category": 0, "categoryRecoveryTime": 0,
                 "effect1": 6, "effectApplyAuraName1": 42,
                 "effectBasePoints1": 0, "effectDieSides1": 1,
                 "effectBaseDice1": 1, "effectAmplitude1": 0,
                 "effectMiscValue1": 0, "effectImplicitTargetA1": 1,
                 "effectTriggerSpell1": 61355,
                 **zero_effect(2), **zero_effect(3)},
         desc="", aura_desc=""),
    # ---- R2: the slow the Lich Armor proc applies to the attacker ----
    dict(id=61355, donor=61023, name="Lich Armor", rank="",
         server={"spellIconId": 96, "school": 4, "durationIndex": 7,
                 "castingTimeIndex": 1, "manaCost": 0, "dispel": 1,
                 "attributes": 0, "attributesEx": 0, "attributesEx2": 0,
                 "recoveryTime": 0, "category": 0, "categoryRecoveryTime": 0,
                 "effect1": 6, "effectApplyAuraName1": 33,
                 "effectBasePoints1": -31, "effectDieSides1": 1,
                 "effectBaseDice1": 1, "effectAmplitude1": 0,
                 "effectMiscValue1": 0, "effectImplicitTargetA1": 6,
                 "effectTriggerSpell1": 0,
                 **zero_effect(2), **zero_effect(3)},
         desc="Movement speed reduced by $s1% for $d.",
         aura_desc="Movement speed reduced by $s1%."),
    # ---- R3: the Shadow rider damage Will of the Death Knight deals ----
    # Hidden but not passive (attributes 128): the module casts it on an
    # enemy; a passive aura would silently fail there.
    dict(id=61356, donor=61350, name="Will of the Death Knight", rank="",
         server={"spellIconId": 2200, "school": 32, "durationIndex": 0,
                 "castingTimeIndex": 1, "manaCost": 0, "dispel": 0,
                 "attributes": 128, "attributesEx": 0, "attributesEx2": 0,
                 "recoveryTime": 0, "category": 0, "categoryRecoveryTime": 0,
                 "effect1": 2, "effectDieSides1": 1, "effectBaseDice1": 1,
                 "effectBasePoints1": 0, "effectAmplitude1": 0,
                 "effectMiscValue1": 0, "effectImplicitTargetA1": 6,
                 "effectTriggerSpell1": 0},
         desc="", aura_desc=""),
]

# ---------------------------------------------------------------------------
# Existing spells: literal UPDATE (idempotent; does not disturb other fields).
# `yaml` carries the same values under their client-DBC field names.
# ---------------------------------------------------------------------------
UPDATES = [
    # ---- R4: Call of the Grave becomes the cast that triggers Grave Rot ----
    dict(id=61016, name="Call of the Grave",
         server={"durationIndex": 0, "dispel": 0, "script_name": "",
                 "effect1": 64, "effectApplyAuraName1": 0,
                 "effectBasePoints1": 0, "effectDieSides1": 1,
                 "effectBaseDice1": 1, "effectAmplitude1": 0,
                 "effectMiscValue1": 0, "effectImplicitTargetA1": 6,
                 "effectTriggerSpell1": 61351,
                 "description": GRAVE_ROT_CAST_DESC, "auraDescription": ""},
         yaml={"DurationIndex": 0, "DispelType": 0, "Effect_1": 64,
               "EffectAura_1": 0, "EffectBasePoints_1": 0,
               "EffectDieSides_1": 1, "EffectBaseDice_1": 1,
               "EffectAmplitude_1": 0, "EffectMiscValue_1": 0,
               "ImplicitTargetA_1": 6, "EffectTriggerSpell_1": 61351},
         desc=GRAVE_ROT_CAST_DESC, aura_desc=""),
    dict(id=61017, name="Call of the Grave",
         server={"durationIndex": 0, "dispel": 0, "script_name": "",
                 "effect1": 64, "effectApplyAuraName1": 0,
                 "effectBasePoints1": 0, "effectDieSides1": 1,
                 "effectBaseDice1": 1, "effectAmplitude1": 0,
                 "effectMiscValue1": 0, "effectImplicitTargetA1": 6,
                 "effectTriggerSpell1": 61352,
                 "description": GRAVE_ROT_CAST_DESC, "auraDescription": ""},
         yaml={"DurationIndex": 0, "DispelType": 0, "Effect_1": 64,
               "EffectAura_1": 0, "EffectBasePoints_1": 0,
               "EffectDieSides_1": 1, "EffectBaseDice_1": 1,
               "EffectAmplitude_1": 0, "EffectMiscValue_1": 0,
               "ImplicitTargetA_1": 6, "EffectTriggerSpell_1": 61352},
         desc=GRAVE_ROT_CAST_DESC, aura_desc=""),
    dict(id=61018, name="Call of the Grave",
         server={"durationIndex": 0, "dispel": 0, "script_name": "",
                 "effect1": 64, "effectApplyAuraName1": 0,
                 "effectBasePoints1": 0, "effectDieSides1": 1,
                 "effectBaseDice1": 1, "effectAmplitude1": 0,
                 "effectMiscValue1": 0, "effectImplicitTargetA1": 6,
                 "effectTriggerSpell1": 61353,
                 "description": GRAVE_ROT_CAST_DESC, "auraDescription": ""},
         yaml={"DurationIndex": 0, "DispelType": 0, "Effect_1": 64,
               "EffectAura_1": 0, "EffectBasePoints_1": 0,
               "EffectDieSides_1": 1, "EffectBaseDice_1": 1,
               "EffectAmplitude_1": 0, "EffectMiscValue_1": 0,
               "ImplicitTargetA_1": 6, "EffectTriggerSpell_1": 61353},
         desc=GRAVE_ROT_CAST_DESC, aura_desc=""),
    # ---- R1: Unholy Shield, -50% magic damage instead of immunity ----
    dict(id=61084, name="Unholy Shield",
         server={"effect1": 6, "effectApplyAuraName1": 87,
                 "effectBasePoints1": -51, "effectDieSides1": 1,
                 "effectBaseDice1": 1, "effectAmplitude1": 0,
                 "effectMiscValue1": 126, "effectImplicitTargetA1": 1,
                 "effectTriggerSpell1": 0,
                 "description": "Surrounds you with an unholy shield, "
                                "reducing magic damage taken by 50% for $d and "
                                "preventing harmful magical effects from being "
                                "applied to you.",
                 "auraDescription": "Magic damage taken reduced by 50%.  "
                                    "Harmful magical effects are prevented."},
         yaml={"Effect_1": 6, "EffectAura_1": 87, "EffectBasePoints_1": -51,
               "EffectDieSides_1": 1, "EffectBaseDice_1": 1,
               "EffectAmplitude_1": 0, "EffectMiscValue_1": 126,
               "ImplicitTargetA_1": 1, "EffectTriggerSpell_1": 0},
         desc="Surrounds you with an unholy shield, reducing magic damage taken "
              "by 50% for $d and preventing harmful magical effects from being "
              "applied to you.",
         aura_desc="Magic damage taken reduced by 50%.  Harmful magical effects "
                   "are prevented."),
    # ---- R2: Lich Armor's slow is documented in the tooltip ----
    dict(id=61085, name="Lich Armor",
         server={"description": "Increases Frost resistance by $s1, spell "
                                "critical chance by $s3% and allows $s2% of "
                                "your mana regeneration to continue while "
                                "casting.  Melee attackers may be slowed by "
                                "30% for 5 sec.  Only one Armor spell can be "
                                "active.",
                 "auraDescription": "Frost resistance increased by $s1.  "
                                    "Spell critical chance increased by $s3%.  "
                                    "$s2% of mana regeneration continues while "
                                    "casting."},
         yaml={},
         desc="Increases Frost resistance by $s1, spell critical chance by "
              "$s3% and allows $s2% of your mana regeneration to continue "
              "while casting.  Melee attackers may be slowed by 30% for "
              "5 sec.  Only one Armor spell can be active.",
         aura_desc="Frost resistance increased by $s1.  Spell critical chance "
                   "increased by $s3%.  $s2% of mana regeneration continues "
                   "while casting."),
    # ---- R3: Will of the Death Knight's rider ----
    dict(id=61091, name="Will of the Death Knight",
         server={"description": "Allows the use of Plate armor and causes you "
                                "to deal an additional 4% of your physical "
                                "damage as Shadow damage.",
                 "auraDescription": ""},
         yaml={},
         desc="Allows the use of Plate armor and causes you to deal an "
              "additional 4% of your physical damage as Shadow damage.",
         aura_desc=""),
]

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
    "procFlags": "ProcTypeMask",
    "procChance": "ProcChance",
    "procCharges": "ProcCharges",
    "targetCreatureType": "TargetCreatureType",
    "baseLevel": "BaseLevel",
    "spellLevel": "SpellLevel",
    "maxLevel": "MaxLevel",
}

# columns that exist server-side but have no client DBC slot
YAML_SKIP_SERVER_COLUMNS = {"effectBonusCoefficient1",
                            "effectBonusCoefficient2",
                            "effectBonusCoefficient3"}


def db_to_dbc(col):
    if col in COLUMN_RENAMES:
        return COLUMN_RENAMES[col]
    m = re.match(r"^effect(\d)$", col)
    if m:
        return "Effect_" + m.group(1)
    for prefix, repl in EFFECT_RENAMES.items():
        if col.startswith(prefix):
            return repl + "_" + col[len(prefix):]
    return None


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
    rows = run(mariadb, port,
               "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
               f"WHERE table_schema='tw_world' AND table_name='{table}' "
               "ORDER BY ORDINAL_POSITION")
    return [r[0] for r in rows], {r[0]: r[1] for r in rows}


def clone_row(mariadb, port, table, entry):
    rows = run(mariadb, port, f"SELECT * FROM {table} WHERE entry = {entry}")
    if len(rows) != 1:
        raise RuntimeError(f"{table}: model {entry} not found")
    return rows[0]


def lang_block(field, value):
    return ['      %s_lang_%d: "%s"' % (field, i, value) for i in range(8)]


def yaml_copy_block(spell):
    lines = ["  # %d <- %d: %s" % (spell["id"], spell["donor"], spell["name"]),
             "  - type: copy",
             "    key: %d" % spell["donor"],
             "    values:",
             "      ID: %d" % spell["id"]]
    lines += lang_block("Name", spell["name"])
    lines += lang_block("NameSubtext", spell["rank"])
    lines += lang_block("Description", spell["desc"])
    lines += lang_block("AuraDescription", spell["aura_desc"] or "")
    skip = ("description", "auraDescription", "script_name")
    for col, value in spell["server"].items():
        if col in skip or col in YAML_SKIP_SERVER_COLUMNS:
            continue
        field = db_to_dbc(col)
        if field is None:
            raise RuntimeError("no DBC name for %s" % col)
        if isinstance(value, int) and value < 0:
            value &= 0xFFFFFFFF
        lines.append("      %s: %d" % (field, value))
    return "\n".join(lines)


def yaml_update_block(spell):
    lines = ["  # %d: %s" % (spell["id"], spell["name"]),
             "  - type: update",
             "    key: %d" % spell["id"],
             "    values:"]
    lines += lang_block("Description", spell["desc"])
    lines += lang_block("AuraDescription", spell["aura_desc"] or "")
    for field, value in spell["yaml"].items():
        if isinstance(value, int) and value < 0:
            value &= 0xFFFFFFFF
        lines.append("      %s: %d" % (field, value))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=DEFAULT_MARIADB)
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", required=True)
    ap.add_argument("--yaml-out", required=True)
    args = ap.parse_args()

    spell_cols, spell_types = table_columns(args.mariadb, args.port, "spell_template")
    entry_idx = spell_cols.index("entry")

    out = []
    w = out.append
    w("-- FILE: %s" % SQL_FILE)
    w("-- Necromancer (class 10) rider-fidelity batch (2026-10-23): the four")
    w("-- backlog items R1-R4.")
    w("--")
    w("--  R1 Unholy Shield 61084: -50% magic damage taken (aura 87) instead of")
    w("--     flat magic immunity; the harmful-magic block is module-side.")
    w("--  R2 Lich Armor 61085: hidden proc aura 61354 (melee hit taken) casts")
    w("--     the 30%/5 s slow 61355 on the attacker.")
    w("--  R3 Will of the Death Knight 61091: hidden Shadow damage spell 61356")
    w("--     for the module's 4%-of-physical rider.")
    w("--  R4 Grave Rot is its own disease aura (61351-61353, script-bound for")
    w("--     the triple final tick); 61016-61018 now trigger it.")
    w("--")
    w("-- Generated by tools/generate_rider_fidelity.py; re-runnable.")
    w("")
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(s["id"]) for s in INSERTS))
    w("")

    for spell in INSERTS:
        values = list(clone_row(args.mariadb, args.port, "spell_template",
                                spell["donor"]))
        values[entry_idx] = str(spell["id"])
        values[spell_cols.index("name")] = spell["name"]
        values[spell_cols.index("nameSubtext")] = spell["rank"]
        values[spell_cols.index("script_name")] = spell["server"].get("script_name", "")
        values[spell_cols.index("description")] = spell["desc"]
        values[spell_cols.index("auraDescription")] = spell["aura_desc"] or ""
        for column, value in spell["server"].items():
            if column in ("description", "auraDescription"):
                continue
            values[spell_cols.index(column)] = str(value)
        literals = [sql_literal(v, spell_types[c]) for v, c in zip(values, spell_cols)]
        w("-- %s (donor %d)" % (spell["name"] or spell["id"], spell["donor"]))
        w("INSERT INTO `spell_template` (`%s`) VALUES" % "`, `".join(spell_cols))
        w("  (%s);" % ", ".join(literals))
        w("")

    for spell in UPDATES:
        assignments = []
        for column, value in spell["server"].items():
            assignments.append("`%s` = %s" %
                               (column, sql_literal(str(value),
                                                    spell_types[column])))
        w("-- R-update: %s (%d)" % (spell["name"], spell["id"]))
        # one line, first assignment right after SET: turtle-agent's
        # spellnamegen only parses that shape
        w("UPDATE `spell_template` SET %s WHERE `entry` = %d;" %
          (", ".join(assignments), spell["id"]))
        w("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    with open(args.yaml_out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# ---- rider-fidelity batch (2026-10-23): R1-R4 ----\n")
        f.write("# New helper/aura spells below; the update blocks patch the\n")
        f.write("# existing 61016-61018 / 61084 / 61085 / 61091 rows.\n")
        f.write("Spell.dbc:\n")
        for spell in UPDATES:
            f.write(yaml_update_block(spell) + "\n")
        for spell in INSERTS:
            f.write(yaml_copy_block(spell) + "\n")

    print(f"wrote {args.out}", file=sys.stderr)
    print(f"wrote {args.yaml_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
