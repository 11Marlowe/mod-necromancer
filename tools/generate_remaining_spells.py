#!/usr/bin/env python3
"""Generate the remaining Necromancer spellbook batch (server SQL + client YAML).

Design A.6-A.9 (remaining non-talent spellbook entries):
  Bloodlet (Blood, L6), Dark Command (Blood, L10), Terror (Plague, L14),
  Ghoul Armor (Reanimation, L20), Embalm (Reanimation, L24),
  Lobotomize (Reanimation, L26), Outbreak (Plague, L26),
  Rule Undead (Reanimation, L28), Unholy Shield (Reanimation, L34),
  Lich Armor (Reanimation, L40), Dark Punishment (Blood, L42).

All are trainer-taught (generate_trainers.py appends them to TRAINABLE).
This script also splits the spellbook into the three design tabs: existing
skill_line_ability rows are reassigned to 700 (Reanimation), 701 (Blood) or
702 (Plague); the client half lives in client/patches/50-skilllines.yaml.

Outputs:
  data/sql/world/20261020090000_world.sql
  client/patches/43-remaining-spells.yaml

Usage:
  python tools/generate_remaining_spells.py
"""

import argparse
import json
import subprocess

DEFAULT_MARIADB = r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe"

CLASS_MASK = 0x200
SKILL_REANIMATION = 700
SKILL_BLOOD = 701
SKILL_PLAGUE = 702

# New server skill_line_ability ids (client rows 7243-7253 in 50-skilllines).
SERVER_SLA_BASE = 7318
CLIENT_SLA_BASE = 7243

# (id, donor, skill line, skill_line_ability id)
SPELLS = [
    dict(id=61076, donor=8092,  skill=SKILL_BLOOD,      server_sla=7318, client_sla=7243,
         name="Bloodlet", icon=152, level=6, school=5, mana=30, cast=1, duration=0,
         range=4, script="spell_necromancer_bloodlet",
         desc="Takes one tick of the strongest disease on the target, dealing that much Shadow damage and restoring the same amount of mana.",
         aura_desc="",
         custom_flags=128,
         effects=[dict(type=2, die=1, base_dice=1, base=0, target_a=6)]),
    dict(id=61077, donor=355,   skill=SKILL_BLOOD,      server_sla=7319, client_sla=7244,
         name="Dark Command", icon=24, level=10, school=0, mana=20, cast=1, duration=27,
         range=2, keep_effects=True,
         desc="Commands the target to attack you.",
         aura_desc="",
         category=82, category_recovery=10000),
    dict(id=61078, donor=5782,  skill=SKILL_PLAGUE,     server_sla=7320, client_sla=7245,
         name="Terror", icon=98, level=14, school=5, mana=40, cast=5, duration=1,
         range=3, recovery=10000, keep_effects=True,
         desc="Strikes fear into the enemy, causing it to flee in terror for up to $d.  Damage caused may interrupt the effect.  Only one target can be feared at a time.",
         aura_desc="Feared.",
         dispel=1, mechanic=5, custom_flags=256),
    dict(id=61079, donor=706,   skill=SKILL_REANIMATION, server_sla=7321, client_sla=7246,
         name="Ghoul Armor", icon=89, level=20, school=5, mana=120, cast=1, duration=30,
         range=1, script="spell_necromancer_armor",
         desc="Increases Shadow resistance by $s2 and heals you for 3% of all damage you deal.  Only one Armor spell can be active.",
         aura_desc="Shadow resistance increased by $s2.  Heals you for 3% of all damage you deal.",
         effects=[
             dict(type=6, die=1, base_dice=1, base=99, target_a=1, aura=22, misc=1),
             dict(type=6, die=1, base_dice=1, base=9, target_a=1, aura=22, misc=32),
         ]),
    dict(id=61080, donor=52694, skill=SKILL_REANIMATION, server_sla=7322, client_sla=7247,
         name="Embalm", icon=99, level=24, school=0, mana=100, cast=1, duration=3,
         range=4, recovery=180000, script="spell_necromancer_embalm",
         desc="Reduces the damage received by your Tethered minion by 10% for $d.",
         aura_desc="Damage received reduced by 10%.",
         attributes=0, attributes_ex=0, attributes_ex2=0,
         proc_flags=0, proc_chance=0, proc_charges=0,
         effects=[dict(type=6, die=1, base_dice=1, base=-11, target_a=21,
                       aura=87, misc=127)]),
    dict(id=61081, donor=1010,  skill=SKILL_REANIMATION, server_sla=7323, client_sla=7248,
         name="Lobotomize", icon=543, level=26, school=5, mana=60, cast=1, duration=2,
         range=4, dispel=1,
         desc="Reduces the target's Intellect by $s1 for $d.",
         aura_desc="Intellect reduced by $s1.",
         effects=[dict(type=6, die=1, base_dice=1, base=-16, target_a=6,
                       aura=29, misc=3)]),
    dict(id=61082, donor=15407, skill=SKILL_PLAGUE,      server_sla=7324, client_sla=7249,
         name="Outbreak", icon=548, level=26, school=5, mana=70, cast=1, duration=35,
         range=3, script="spell_necromancer_outbreak", custom_flags=128,
         desc="Channels Shadow energy into the target for $d, refreshing your diseases on it and spreading them to up to 3 nearby enemies.",
         aura_desc="Shadow damage and disease spread.",
         effects=[dict(type=6, die=1, base_dice=1, base=24, target_a=6,
                       aura=3, amplitude=1000)]),
    dict(id=61083, donor=9484,  skill=SKILL_REANIMATION, server_sla=7325, client_sla=7250,
         name="Rule Undead", icon=27, level=28, school=1, mana=100, cast=1, duration=22,
         range=4, keep_effects=True,
         desc="Shackles the target undead enemy for up to $d.  The shackled unit is unable to move, attack or cast spells.  Any damage caused will release the target.  Only one target can be shackled at a time.",
         aura_desc="Shackled.",
         dispel=1, mechanic=20, target_creature_type=32, custom_flags=256),
    dict(id=61084, donor=24021, skill=SKILL_REANIMATION, server_sla=7326, client_sla=7251,
         name="Unholy Shield", icon=99, level=34, school=5, mana=200, cast=1, duration=31,
         range=1, recovery=180000, keep_effects=True,
         desc="Surrounds you with an unholy shield, granting immunity to magic for $d.",
         aura_desc="Immune to magic.",
         dispel=0, mechanic=0),
    dict(id=61085, donor=6117,  skill=SKILL_REANIMATION, server_sla=7327, client_sla=7252,
         name="Lich Armor", icon=1711, level=40, school=4, mana=200, cast=1, duration=30,
         range=1, script="spell_necromancer_armor",
         desc="Increases Frost resistance by $s1, spell critical chance by $s3% and allows $s2% of your mana regeneration to continue while casting.  Only one Armor spell can be active.",
         aura_desc="Frost resistance increased by $s1.  Spell critical chance increased by $s3%.  $s2% of mana regeneration continues while casting.",
         effects=[
             dict(type=6, die=1, base_dice=1, base=9, target_a=1, aura=22, misc=16),
             dict(type=6, die=1, base_dice=1, base=14, target_a=1, aura=134),
             dict(type=6, die=1, base_dice=1, base=2, target_a=1, aura=57),
         ]),
    dict(id=61086, donor=12328, skill=SKILL_BLOOD,       server_sla=7328, client_sla=7253,
         name="Dark Punishment", icon=169, level=42, school=0, mana=100, cast=1, duration=18,
         range=1, recovery=180000,
         desc="Increases all damage you deal by 15% for $d, but drains 2% of your maximum health every second.  This effect cannot be cancelled.",
         aura_desc="Damage dealt increased by 15%.  Losing 2% of maximum health every second.",
         attributes_extra=0x80000000,
         effects=[
             dict(type=6, die=1, base_dice=1, base=14, target_a=1, aura=79, misc=1),
             dict(type=6, die=1, base_dice=1, base=14, target_a=1, aura=79, misc=126),
             dict(type=6, die=1, base_dice=1, base=1, target_a=1, aura=89, amplitude=1000),
         ]),
]

# Existing spellbook spells and their tab (design A.6/A.8/A.9).
TAB_MAP = {
    SKILL_REANIMATION: [61015, 61024, 61025, 61026, 61028, 61029, 61033,
                        61034, 61035, 61036, 61037, 61038, 61039, 61040,
                        61048, 61049, 61050, 61074],
    SKILL_BLOOD: [61013, 61014, 61075],
    SKILL_PLAGUE: [61010, 61011, 61012, 61016, 61017, 61018,
                   61019, 61020, 61021, 61022, 61023],
}

EFFECT_SERVER = [
    ("type", "effect{n}"), ("die", "effectDieSides{n}"),
    ("base_dice", "effectBaseDice{n}"), ("dice_per_level", "effectDicePerLevel{n}"),
    ("real_points_per_level", "effectRealPointsPerLevel{n}"),
    ("base", "effectBasePoints{n}"), ("bonus_coeff", "effectBonusCoefficient{n}"),
    ("mechanic", "effectMechanic{n}"), ("target_a", "effectImplicitTargetA{n}"),
    ("target_b", "effectImplicitTargetB{n}"), ("radius", "effectRadiusIndex{n}"),
    ("aura", "effectApplyAuraName{n}"), ("amplitude", "effectAmplitude{n}"),
    ("multiple", "effectMultipleValue{n}"), ("chain", "effectChainTarget{n}"),
    ("item", "effectItemType{n}"), ("misc", "effectMiscValue{n}"),
    ("trigger", "effectTriggerSpell{n}"), ("combo", "effectPointsPerComboPoint{n}"),
]

EFFECT_CLIENT = [
    ("type", "Effect_{n}"), ("die", "EffectDieSides_{n}"),
    ("base_dice", "EffectBaseDice_{n}"), ("dice_per_level", "EffectDicePerLevel_{n}"),
    ("real_points_per_level", "EffectRealPointsPerLevel_{n}"),
    ("base", "EffectBasePoints_{n}"), ("mechanic", "EffectMechanic_{n}"),
    ("target_a", "ImplicitTargetA_{n}"), ("target_b", "ImplicitTargetB_{n}"),
    ("radius", "EffectRadiusIndex_{n}"), ("aura", "EffectAura_{n}"),
    ("amplitude", "EffectAmplitude_{n}"), ("multiple", "EffectMultipleValue_{n}"),
    ("chain", "EffectChainTarget_{n}"), ("item", "EffectItemType_{n}"),
    ("misc", "EffectMiscValue_{n}"), ("trigger", "EffectTriggerSpell_{n}"),
    ("combo", "EffectPointsPerCombo_{n}"),
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


def u32(value):
    value = int(value)
    return value if value >= 0 else value + (1 << 32)


def build_server_spell(spec, cols, donor):
    values = dict(donor)
    values.update({
        "entry": str(spec["id"]),
        "name": spec["name"],
        "nameSubtext": "",
        "description": spec["desc"],
        "auraDescription": spec["aura_desc"],
        "school": str(spec.get("school", 0)),
        "category": str(spec.get("category", 0)),
        "castUI": "0",
        "dispel": str(spec.get("dispel", 0)),
        "mechanic": str(spec.get("mechanic", 0)),
        "targets": str(spec.get("targets", 0)),
        "targetCreatureType": str(spec.get("target_creature_type", 0)),
        "castingTimeIndex": str(spec.get("cast", 1)),
        "recoveryTime": str(spec.get("recovery", 0)),
        "categoryRecoveryTime": str(spec.get("category_recovery", 0)),
        "powerType": "0",
        "manaCost": str(spec.get("mana", 0)),
        "manaCostPercentage": str(spec.get("mana_pct", 0)),
        "maxLevel": "0",
        "baseLevel": str(spec.get("level", 1)),
        "spellLevel": str(spec.get("level", 1)),
        "durationIndex": str(spec.get("duration", 0)),
        "rangeIndex": str(spec.get("range", 1)),
        "speed": "0",
        "equippedItemClass": "-1",
        "equippedItemSubClassMask": "0",
        "equippedItemInventoryTypeMask": "0",
        "spellIconId": str(spec.get("icon", 1)),
        "spellFamilyName": "0",
        "spellFamilyFlags": "0",
        "startRecoveryCategory": "133",
        "startRecoveryTime": "1500",
        "stances": "0",
        "stancesNot": "0",
        "customFlags": str(spec.get("custom_flags", 0)),
        "script_name": spec.get("script", ""),
        "minTargetLevel": "0",
        "maxTargetLevel": "0",
        "maxAffectedTargets": "0",
    })

    for key, col in (("attributes", "attributes"),
                     ("attributes_ex", "attributesEx"),
                     ("attributes_ex2", "attributesEx2"),
                     ("proc_flags", "procFlags"),
                     ("proc_chance", "procChance"),
                     ("proc_charges", "procCharges")):
        if key in spec:
            values[col] = str(spec[key])

    if spec.get("attributes_extra"):
        values["attributes"] = str(int(values.get("attributes", 0)) | spec["attributes_extra"])

    if not spec.get("keep_effects"):
        for n in (1, 2, 3):
            for _, col in EFFECT_SERVER:
                values[col.format(n=n)] = "0"
        for n, effect in enumerate(spec.get("effects", []), 1):
            for key, col in EFFECT_SERVER:
                if key in effect:
                    values[col.format(n=n)] = str(effect[key])
            values.setdefault(f"effect{n}", "0")

    return values


def build_client_values(spec, donor):
    v = {
        "ID": str(spec["id"]),
        "Name_lang": spec["name"],
        "NameSubtext_lang": "",
        "Description_lang": spec["desc"],
        "AuraDescription_lang": spec["aura_desc"],
        "School": spec.get("school", 0),
        "Category": spec.get("category", 0),
        "CastUI": 0,
        "DispelType": spec.get("dispel", 0),
        "Mechanic": spec.get("mechanic", 0),
        "Targets": spec.get("targets", 0),
        "TargetCreatureType": spec.get("target_creature_type", 0),
        "CastingTimeIndex": spec.get("cast", 1),
        "RecoveryTime": spec.get("recovery", 0),
        "CategoryRecoveryTime": spec.get("category_recovery", 0),
        "PowerType": 0,
        "ManaCost": spec.get("mana", 0),
        "ManaCostPct": spec.get("mana_pct", 0),
        "MaxLevel": 0,
        "BaseLevel": spec.get("level", 1),
        "SpellLevel": spec.get("level", 1),
        "DurationIndex": spec.get("duration", 0),
        "RangeIndex": spec.get("range", 1),
        "EquippedItemClass": -1,
        "EquippedItemSubclass": 0,
        "EquippedItemInvType": 0,
        "SpellIconID": spec.get("icon", 1),
        "SpellClassSet": 0,
        "SpellClassMask_1": 0,
        "SpellClassMask_2": 0,
        "StartRecoveryCategory": 133,
        "StartRecoveryTime": 1500,
        "ShapeshiftMask": 0,
        "ShapeshiftExclude": 0,
        "MaxTargetLevel": 0,
        "MaxTargets": 0,
    }

    for key, field in (("attributes", "Attributes"),
                       ("attributes_ex", "AttributesEx"),
                       ("attributes_ex2", "AttributesEx2"),
                       ("proc_flags", "ProcTypeMask"),
                       ("proc_chance", "ProcChance"),
                       ("proc_charges", "ProcCharges")):
        if key in spec:
            v[field] = spec[key]

    if spec.get("attributes_extra"):
        v["Attributes"] = int(v.get("Attributes", 0)) | spec["attributes_extra"]

    if not spec.get("keep_effects"):
        for n in (1, 2, 3):
            for _, field in EFFECT_CLIENT:
                v[field.format(n=n)] = 0
        for n, effect in enumerate(spec.get("effects", []), 1):
            for key, field in EFFECT_CLIENT:
                if key in effect:
                    v[field.format(n=n)] = effect[key]

    return v


def yaml_lang(field, value):
    return [f'      {field}_{i}: {json.dumps(value)}' for i in range(8)]


def yaml_scalar(value):
    if isinstance(value, str):
        return json.dumps(value)
    return str(u32(value))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=DEFAULT_MARIADB)
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", default="data/sql/world/20261020090000_world.sql")
    ap.add_argument("--client-yaml", default="client/patches/43-remaining-spells.yaml")
    args = ap.parse_args()

    md, port = args.mariadb, args.port
    cols, types = table_columns(md, port, "spell_template")

    # --- sanity -------------------------------------------------------------
    our_ids = {spec["id"] for spec in SPELLS}
    for spec in SPELLS:
        rows = query(md, port,
                     f"SELECT `name` FROM `spell_template` WHERE `entry` = {spec['id']}")
        for (name,) in rows:
            if name != spec["name"]:
                raise SystemExit(f"spell id {spec['id']} is used by '{name}'")
    for row in query(md, port,
                     f"SELECT `id`, `spell_id` FROM `skill_line_ability` "
                     f"WHERE `id` BETWEEN {SERVER_SLA_BASE} AND {SERVER_SLA_BASE + len(SPELLS) - 1}"):
        if int(row[1]) not in our_ids:
            raise SystemExit(f"server skill_line_ability id {row[0]} is used by spell {row[1]}")

    donors = {spec["id"]: fetch_spell(md, port, cols, spec["donor"]) for spec in SPELLS}

    # --- server SQL ---------------------------------------------------------
    lines = []
    lines.append("-- FILE: 20261020090000_world.sql")
    lines.append("-- Necromancer (class 10) remaining spellbook batch (design A.6-A.9,")
    lines.append("-- 2026-10-19): Bloodlet, Dark Command, Terror, Ghoul Armor, Embalm,")
    lines.append("-- Lobotomize, Outbreak, Rule Undead, Unholy Shield, Lich Armor and")
    lines.append("-- Dark Punishment, plus the three-tab spellbook split (A87: skill lines")
    lines.append("-- 700 Reanimation / 701 Blood / 702 Plague).  Trainer learn spells")
    lines.append("-- 61132-61142 and npc_trainer rows are generated by generate_trainers.py.")
    lines.append("-- Generated by tools/generate_remaining_spells.py; re-runnable.")
    lines.append("")
    lines.append(f"DELETE FROM `spell_template` WHERE `entry` BETWEEN {SPELLS[0]['id']} AND {SPELLS[-1]['id']};")
    lines.append(f"DELETE FROM `skill_line_ability` WHERE `id` BETWEEN {SERVER_SLA_BASE} AND {SERVER_SLA_BASE + len(SPELLS) - 1} OR `spell_id` BETWEEN {SPELLS[0]['id']} AND {SPELLS[-1]['id']};")
    lines.append("")
    lines.append("-- Bone Armor joins the exclusive armor line (A87 batch)")
    lines.append("UPDATE `spell_template` SET `script_name` = 'spell_necromancer_armor' WHERE `entry` = 61015;")
    lines.append("")

    for spec in SPELLS:
        values = build_server_spell(spec, cols, donors[spec["id"]])
        vals = [sql_literal(values[c], types[c]) for c in cols]
        lines.append(f"-- {spec['id']} {spec['name']} (donor {spec['donor']})")
        lines.append("INSERT INTO `spell_template` (" +
                     ", ".join(f"`{c}`" for c in cols) + ") VALUES (" +
                     ", ".join(vals) + ");")
        lines.append("")

    lines.append("-- Server skill_line_ability rows (new spells)")
    for spec in SPELLS:
        lines.append("INSERT INTO `skill_line_ability` (`id`, `skill_id`, `spell_id`, `race_mask`, `class_mask`, `req_skill_value`, `superseded_by_spell`, `learn_on_get_skill`, `max_value`, `min_value`, `req_train_points`) VALUES (" +
                     f"{spec['server_sla']}, {spec['skill']}, {spec['id']}, 0, {CLASS_MASK}, 1, 0, 0, 0, 0, 0);")
    lines.append("")

    lines.append("-- Reassign the existing spellbook rows to the three tabs (A87)")
    for skill, ids in TAB_MAP.items():
        lines.append(f"UPDATE `skill_line_ability` SET `skill_id` = {skill} WHERE `spell_id` IN ({', '.join(str(i) for i in ids)});")
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # --- client YAML --------------------------------------------------------
    y = []
    y.append("# Remaining Necromancer spellbook entries (design A.6-A.9, 2026-10-19).")
    y.append("# Server rows are generated by tools/generate_remaining_spells.py.")
    y.append("# Skill-line/tab assignments live in 50-skilllines.yaml (A87).")
    y.append("Spell.dbc:")
    for spec in SPELLS:
        v = build_client_values(spec, donors[spec["id"]])
        y.append("  - type: copy")
        y.append(f"    key: {spec['donor']}")
        y.append("    values:")
        y.append(f"      ID: {v.pop('ID')}")
        for field in ("Name", "NameSubtext", "Description", "AuraDescription"):
            y += yaml_lang(field + "_lang", v.pop(field + "_lang"))
        for field, value in v.items():
            y.append(f"      {field}: {yaml_scalar(value)}")
        y.append("")

    with open(args.client_yaml, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(y))

    print(f"wrote {args.out}")
    print(f"wrote {args.client_yaml}")
    print(f"{len(SPELLS)} spells, ids {SPELLS[0]['id']}-{SPELLS[-1]['id']}, "
          f"server SLA {SERVER_SLA_BASE}-{SERVER_SLA_BASE + len(SPELLS) - 1}")


if __name__ == "__main__":
    main()
