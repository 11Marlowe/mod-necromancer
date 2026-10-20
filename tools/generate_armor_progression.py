#!/usr/bin/env python3
"""Generate the Necromancer armor/weapon progression pass (server SQL + client YAML).

Design A.4 slots 9/17/25 (talent shortcuts until talents exist):
  Grim Reaper          (L20) - all two-handed weapons + dual wield one-handers
  Necro Knight         (L30) - Leather and Mail armor
  Will of the Death Knight (L40) - Plate armor

The spells are passive proficiency spells (effect 60 / 40) cloned from the
vanilla proficiency spells, so learning them via the class trainers applies
the proficiency exactly like a vanilla class.  Placeholders: Sigils do not
exist in 1.12, "no Wands" is not enforced yet, the Will's 4%-as-Shadow rider
and Grim Reaper's dual-wield strike are deferred.

Run generate_trainers.py afterwards (it appends 61143-61145 and the
npc_trainer rows), then rebuild patch-Z.mpq.

Outputs:
  data/sql/world/20261020140000_world.sql
  client/patches/45-armor-progression.yaml

Usage:
  python tools/generate_armor_progression.py
"""

import argparse
import json
import subprocess

DEFAULT_MARIADB = r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe"

SKILL_BLOOD = 701
CLASS_MASK = 0x200
SERVER_SLA_BASE = 7329
CLIENT_SLA_BASE = 7254

# (id, donor, name, icon, level, equipped class/mask, effects, desc)
SPELLS = [
    dict(id=61090, donor=9077, name="Necro Knight", icon=326, level=30,
         equipped_class=4, equipped_mask=12, effects={1: 60}, targets={1: 1},
         desc="Allows the use of Leather and Mail armor."),
    dict(id=61091, donor=750, name="Will of the Death Knight", icon=440, level=40,
         equipped_class=4, equipped_mask=16, effects={1: 60}, targets={1: 1},
         desc="Allows the use of Plate armor."),
    dict(id=61092, donor=674, name="Grim Reaper", icon=1884, level=20,
         equipped_class=2, equipped_mask=1529, effects={1: 40, 2: 60},
         targets={1: 1, 2: 1},
         desc="Allows the use of all two-handed weapons and dual wielding one-handed weapons."),
]


def query(mariadb, port, sql):
    out = subprocess.run(
        [mariadb, f"--port={port}", "-u", "root", "tw_world",
         "--batch", "--skip-column-names", "-e", sql],
        capture_output=True, text=True, check=True,
    )
    rows = []
    for line in out.stdout.splitlines():
        line = line.rstrip("\r")
        if not line:
            continue

        def unesc(s):
            r = []
            i = 0
            while i < len(s):
                if s[i] == "\\" and i + 1 < len(s):
                    n = s[i + 1]
                    r.append({"n": "\n", "t": "\t", "0": "\0", "\\": "\\"}.get(n, n))
                    i += 2
                else:
                    r.append(s[i])
                    i += 1
            return "".join(r)

        rows.append([unesc(f) for f in line.split("\t")])
    return rows


def table_columns(mariadb, port, table):
    rows = query(mariadb, port,
                 "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
                 f"WHERE table_schema='tw_world' AND table_name='{table}' "
                 "ORDER BY ORDINAL_POSITION")
    return [r[0] for r in rows], {r[0]: r[1] for r in rows}


def fetch_spell(mariadb, port, cols, entry):
    rows = query(mariadb, port, f"SELECT * FROM `spell_template` WHERE `entry` = {entry}")
    if len(rows) != 1 or len(rows[0]) != len(cols):
        raise SystemExit(f"spell_template donor {entry} not found/width mismatch")
    return dict(zip(cols, rows[0]))


def sql_literal(value, data_type):
    if value == "NULL":
        return "NULL"
    if data_type in ("tinyint", "smallint", "mediumint", "int", "bigint",
                     "float", "double", "decimal"):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def build_server_spell(spec, cols, donor):
    values = dict(donor)
    zero_cols = [
        "attributesEx", "attributesEx2", "attributesEx3", "attributesEx4",
        "stances", "stancesNot", "targets", "targetCreatureType",
        "requiresSpellFocus", "casterAuraState", "targetAuraState",
        "recoveryTime", "categoryRecoveryTime", "interruptFlags",
        "auraInterruptFlags", "channelInterruptFlags", "procFlags",
        "procChance", "procCharges", "maxLevel", "durationIndex",
        "powerType", "manaCost", "manCostPerLevel", "manaPerSecond",
        "manaPerSecondPerLevel", "speed", "modelNextSpell", "stackAmount",
        "equippedItemInventoryTypeMask", "effectDieSides1", "effectDieSides2",
        "effectDieSides3", "effectBaseDice1", "effectBaseDice2",
        "effectBaseDice3", "effectDicePerLevel1", "effectDicePerLevel2",
        "effectDicePerLevel3", "effectRealPointsPerLevel1",
        "effectRealPointsPerLevel2", "effectRealPointsPerLevel3",
        "effectBasePoints1", "effectBasePoints2", "effectBasePoints3",
        "effectMechanic1", "effectMechanic2", "effectMechanic3",
        "effectImplicitTargetA1", "effectImplicitTargetA2", "effectImplicitTargetA3",
        "effectImplicitTargetB1", "effectImplicitTargetB2", "effectImplicitTargetB3",
        "effectRadiusIndex1", "effectRadiusIndex2", "effectRadiusIndex3",
        "effectApplyAuraName1", "effectApplyAuraName2", "effectApplyAuraName3",
        "effectAmplitude1", "effectAmplitude2", "effectAmplitude3",
        "effectMultipleValue1", "effectMultipleValue2", "effectMultipleValue3",
        "effectChainTarget1", "effectChainTarget2", "effectChainTarget3",
        "effectItemType1", "effectItemType2", "effectItemType3",
        "effectMiscValue1", "effectMiscValue2", "effectMiscValue3",
        "effectTriggerSpell1", "effectTriggerSpell2", "effectTriggerSpell3",
        "effectPointsPerComboPoint1", "effectPointsPerComboPoint2",
        "effectPointsPerComboPoint3", "spellVisual1", "spellVisual2",
        "activeIconId", "spellPriority", "manaCostPercentage",
        "startRecoveryCategory", "startRecoveryTime", "minTargetLevel",
        "maxTargetLevel", "spellFamilyName", "spellFamilyFlags",
        "maxAffectedTargets", "dmgClass", "preventionType", "stanceBarOrder",
        "minFactionId", "minReputation", "requiredAuraVision", "customFlags",
    ]
    values.update({
        "entry": str(spec["id"]),
        "name": spec["name"],
        "nameSubtext": "",
        "description": spec["desc"],
        "auraDescription": "",
        "script_name": "",
        "nameFlags": "4128894",
        "nameSubtextFlags": "4128894",
        "descriptionFlags": "4128894",
        "auraDescriptionFlags": "4128892",
        "school": "0",
        "category": "0",
        "castUI": "0",
        "dispel": "0",
        "mechanic": "0",
        "castingTimeIndex": "1",
        "baseLevel": str(spec["level"]),
        "spellLevel": str(spec["level"]),
        "rangeIndex": "1",
        "equippedItemClass": str(spec["equipped_class"]),
        "equippedItemSubClassMask": str(spec["equipped_mask"]),
        "spellIconId": str(spec["icon"]),
        "attributes": "80",
        "stanceBarOrder": "0",
        "dmgMultiplier1": "1",
        "dmgMultiplier2": "1",
        "dmgMultiplier3": "1",
    })
    for col in zero_cols:
        if col in values:
            values[col] = "0"
    values["effect1"] = str(spec["effects"].get(1, 0))
    values["effect2"] = str(spec["effects"].get(2, 0))
    values["effect3"] = str(spec["effects"].get(3, 0))
    for n in (1, 2, 3):
        values[f"effectImplicitTargetA{n}"] = str(spec["targets"].get(n, 0))
    return values


def yaml_lang(field, value):
    return [f'      {field}_{i}: {json.dumps(value)}' for i in range(8)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=DEFAULT_MARIADB)
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", default="data/sql/world/20261020140000_world.sql")
    ap.add_argument("--client-yaml", default="client/patches/45-armor-progression.yaml")
    args = ap.parse_args()

    md, port = args.mariadb, args.port
    cols, types = table_columns(md, port, "spell_template")

    our_ids = {s["id"] for s in SPELLS}
    for s in SPELLS:
        rows = query(md, port, f"SELECT `name` FROM `spell_template` WHERE `entry` = {s['id']}")
        for (name,) in rows:
            if name != s["name"]:
                raise SystemExit(f"spell id {s['id']} is used by '{name}'")

    donors = {s["id"]: fetch_spell(md, port, cols, s["donor"]) for s in SPELLS}

    # --- server SQL ---------------------------------------------------------
    lines = [
        "-- FILE: 20261020140000_world.sql",
        "-- Necromancer armor/weapon progression (A.4 slots 9/17/25, 2026-10-20).",
        "-- Trainer-taught passive proficiency spells (talent shortcuts):",
        "--   61092 Grim Reaper (L20) - 2H weapons + dual wield",
        "--   61090 Necro Knight (L30) - Leather + Mail",
        "--   61091 Will of the Death Knight (L40) - Plate",
        "-- The trainer learn spells 61143-61145 and npc_trainer rows are",
        "-- generated by generate_trainers.py.  Generated by",
        "-- tools/generate_armor_progression.py; re-runnable.",
        "",
        "DELETE FROM `spell_template` WHERE `entry` IN (61090, 61091, 61092);",
        "DELETE FROM `skill_line_ability` WHERE `id` BETWEEN 7329 AND 7331 OR `spell_id` IN (61090, 61091, 61092);",
        "",
    ]

    for s in SPELLS:
        values = build_server_spell(s, cols, donors[s["id"]])
        vals = [sql_literal(values[c], types[c]) for c in cols]
        lines.append(f"-- {s['id']} {s['name']} (donor {s['donor']})")
        lines.append("INSERT INTO `spell_template` (" +
                     ", ".join(f"`{c}`" for c in cols) + ") VALUES (" +
                     ", ".join(vals) + ");")
        lines.append("")

    lines.append("-- Server skill_line_ability rows (Blood tab, class 10)")
    for i, s in enumerate(SPELLS):
        lines.append(
            "INSERT INTO `skill_line_ability` (`id`, `skill_id`, `spell_id`, "
            "`race_mask`, `class_mask`, `req_skill_value`, `superseded_by_spell`, "
            "`learn_on_get_skill`, `max_value`, `min_value`, `req_train_points`) VALUES (" +
            f"{SERVER_SLA_BASE + i}, {SKILL_BLOOD}, {s['id']}, 0, {CLASS_MASK}, "
            "1, 0, 0, 0, 0, 0);")
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # --- client YAML --------------------------------------------------------
    y = [
        "# Necromancer armor/weapon progression (A.4 slots 9/17/25, 2026-10-20).",
        "# Trainer-taught passive proficiency spells; train spells 61143-61145",
        "# and npc_trainer rows come from generate_trainers.py.  Generated by",
        "# tools/generate_armor_progression.py; re-runnable.",
        "Spell.dbc:",
    ]
    for s in SPELLS:
        y.append("  - type: copy")
        y.append(f"    key: {s['donor']}")
        y.append("    values:")
        y.append(f"      ID: {s['id']}")
        y += yaml_lang("Name_lang", s["name"])
        y += yaml_lang("NameSubtext_lang", "")
        y += yaml_lang("Description_lang", s["desc"])
        y += yaml_lang("AuraDescription_lang", "")
        y.append(f"      Name_lang_Mask: 4128894")
        y.append(f"      NameSubtext_lang_Mask: 4128894")
        y.append(f"      Description_lang_Mask: 4128894")
        y.append(f"      AuraDescription_lang_Mask: 4128892")
        y.append("      SpellIconID: " + str(s["icon"]))
        y.append("      Attributes: 80")
        y.append("      CastingTimeIndex: 1")
        y.append("      DurationIndex: 0")
        y.append("      RangeIndex: 1")
        y.append("      PowerType: 0")
        y.append("      ManaCost: 0")
        y.append("      MaxLevel: 0")
        y.append(f"      BaseLevel: {s['level']}")
        y.append(f"      SpellLevel: {s['level']}")
        y.append("      School: 0")
        y.append("      Category: 0")
        y.append("      Targets: 0")
        y.append("      TargetCreatureType: 0")
        y.append("      EquippedItemClass: " + str(s["equipped_class"]))
        y.append("      EquippedItemSubclass: " + str(s["equipped_mask"]))
        y.append("      EquippedItemInvType: 0")
        for n in (1, 2, 3):
            y.append(f"      Effect_{n}: {s['effects'].get(n, 0)}")
            for f in ("EffectDieSides", "EffectBaseDice", "EffectDicePerLevel",
                      "EffectRealPointsPerLevel", "EffectBasePoints",
                      "EffectMechanic", "ImplicitTargetB",
                      "EffectRadiusIndex", "EffectAura", "EffectAmplitude",
                      "EffectMultipleValue", "EffectChainTarget", "EffectItemType",
                      "EffectMiscValue", "EffectTriggerSpell", "EffectPointsPerCombo"):
                y.append(f"      {f}_{n}: 0")
            y.append(f"      ImplicitTargetA_{n}: {s['targets'].get(n, 0)}")
        y.append("      AttributesEx: 0")
        y.append("      AttributesEx2: 0")
        y.append("      AttributesEx3: 0")
        y.append("      AttributesEx4: 0")
        y.append("      ShapeshiftMask: 0")
        y.append("      ShapeshiftExclude: 0")
        y.append("      ProcTypeMask: 0")
        y.append("      ProcChance: 0")
        y.append("      ProcCharges: 0")
        y.append("      StartRecoveryCategory: 0")
        y.append("      StartRecoveryTime: 0")
        y.append("      SpellClassSet: 0")
        y.append("      SpellClassMask_1: 0")
        y.append("      SpellClassMask_2: 0")
        y.append("      MaxTargets: 0")
        y.append("      MaxTargetLevel: 0")
        y.append("      SpellVisualID_1: 0")
        y.append("      SpellVisualID_2: 0")
        y.append("      StanceBarOrder: 0")
        y.append("      MinFactionId: 0")
        y.append("      MinReputation: 0")
        y.append("      RequiredAuraVision: 0")
        y.append("")

    with open(args.client_yaml, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(y))

    print(f"wrote {args.out}")
    print(f"wrote {args.client_yaml}")
    print(f"{len(SPELLS)} passives, server SLA {SERVER_SLA_BASE}-{SERVER_SLA_BASE + len(SPELLS) - 1}, "
          f"client SLA {CLIENT_SLA_BASE}-{CLIENT_SLA_BASE + len(SPELLS) - 1}")


if __name__ == "__main__":
    main()
