#!/usr/bin/env python3
"""Generate the remaining Necromancer talent spells (server SQL + client YAML).

Design A.4/A.8/A.9 (the last talent-gated spells; talent shortcuts until the
talent trees exist):
  Soul Strike  (Blood, L20)  - 50% weapon damage + 3% max health per disease
  Icy Touch    (Plague, L30) - Frost damage + Frost Fever (damage + slows)
  Corrosion    (Plague, L32) - -X armor for 20 sec
  Lichborne    (Plague, L40) - -10% physical damage taken, 25% mana regen
  Unholy Aura  (Blood, L30)  - party aura: +8% speed, 25% health regen in combat

Frost Fever (61095) is the hidden aura applied by Icy Touch (it is not in the
spellbook and has no skill-line row).

Run generate_trainers.py afterwards (it appends learn spells 61146-61150 and
the npc_trainer rows), then generate_cosmetic_pass.py (icons/tooltips), then
rebuild patch-Z.mpq.

Outputs:
  data/sql/world/20261020160000_world.sql
  client/patches/43b-talent-spells.yaml

Usage:
  python tools/generate_talent_spells.py
"""

import argparse
import json
import subprocess

DEFAULT_MARIADB = r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe"

CLASS_MASK = 0x200
SKILL_BLOOD = 701
SKILL_PLAGUE = 702

# New server skill_line_ability ids (client rows 7257-7261 in 50-skilllines).
SERVER_SLA_BASE = 7332
CLIENT_SLA_BASE = 7257

# (id, donor, name, tab, server_sla, client_sla, ...)
SPELLS = [
    dict(id=61087, donor=1752, name="Soul Strike", tab=SKILL_BLOOD,
         server_sla=7332, client_sla=7257, icon=2147, level=20, school=0,
         mana=25, cast=1, duration=0, range=2,
         equipped_class=2, equipped_mask=0, custom_flags=128,
         dmg_class=2, prevention_type=2,
         script="spell_necromancer_soul_strike",
         desc="Instantly strike the target for 50% weapon damage and heal "
              "yourself for 3% of your total health for each of your diseases "
              "on the target, up to three diseases.",
         aura_desc="",
         effects=[dict(type=31, die=1, base_dice=1, base=49, target_a=6)]),
    dict(id=61088, donor=116, name="Icy Touch", tab=SKILL_PLAGUE,
         server_sla=7333, client_sla=7258, icon=182, level=30, school=4,
         mana=60, cast=1, duration=0, range=4,
         script="spell_necromancer_icy_touch",
         desc="Causes $s1 Frost damage and infects the target with Frost Fever, "
              "causing Frost damage over 15 sec and reducing melee and casting "
              "speed by 5%.",
         aura_desc="",
         effects=[dict(type=2, die=16, base_dice=1, base=39, target_a=6)]),
    dict(id=61089, donor=7386, name="Corrosion", tab=SKILL_PLAGUE,
         server_sla=7334, client_sla=7259, icon=565, level=32, school=0,
         mana=40, cast=1, duration=18, range=4,
         dmg_class=1, prevention_type=1,
         attributes=65536, attributes_ex=0, attributes_ex2=0,
         attributes_ex3=0, attributes_ex4=0,
         desc="Corrodes the target's armor, reducing it by $s1 for $d.",
         aura_desc="Armor reduced by $s1.",
         effects=[dict(type=6, die=1, base_dice=1, base=-151, target_a=6,
                       aura=22, misc=1)]),
    dict(id=61093, donor=6117, name="Lichborne", tab=SKILL_PLAGUE,
         server_sla=7335, client_sla=7260, icon=1591, level=40, school=4,
         mana=0, cast=1, duration=21, range=1,
         desc="Assume a lich form, reducing physical damage taken by 10% and "
              "allowing 25% of your mana regeneration to continue while casting.",
         aura_desc="Physical damage taken reduced by 10%.  25% of mana "
                   "regeneration continues while casting.",
         effects=[
             dict(type=6, die=1, base_dice=1, base=-11, target_a=1,
                  aura=87, misc=1),
             dict(type=6, die=1, base_dice=1, base=24, target_a=1,
                  aura=134),
         ]),
    dict(id=61094, donor=465, name="Unholy Aura", tab=SKILL_BLOOD,
         server_sla=7336, client_sla=7261, icon=147, level=30, school=5,
         mana=0, cast=1, duration=21, range=1,
         attributes_ex2=0,
         desc="Increases movement speed by 8% and allows 25% of health "
              "regeneration to continue in combat for you and your allies "
              "within 30 yards.",
         aura_desc="Movement speed increased by 8%.  25% of health regeneration "
                   "continues in combat.",
         effects=[
             dict(type=35, die=1, base_dice=1, base=7, target_a=1,
                  aura=31, radius=10),
             dict(type=35, die=1, base_dice=1, base=24, target_a=1,
                  aura=116, radius=10),
         ]),
    # Hidden Frost Fever aura (script-applied by Icy Touch; no spellbook row).
    dict(id=61095, donor=172, name="Frost Fever", tab=None,
         server_sla=0, client_sla=0, icon=182, level=30, school=4,
         mana=0, cast=1, duration=8, range=4, dispel=3,
         desc="Frost Fever: Frost damage over 15 sec and 5% reduced melee and "
              "casting speed.",
         aura_desc="Frost Fever: $s1 Frost damage every $t1 sec.  Melee and "
                   "casting speed reduced by 5%.",
         effects=[
             dict(type=6, die=1, base_dice=1, base=9, target_a=6,
                  aura=3, amplitude=3000),
             dict(type=6, die=1, base_dice=1, base=-6, target_a=6,
                  aura=138),
             dict(type=6, die=1, base_dice=1, base=-6, target_a=6,
                  aura=65),
         ]),
]

TRAINABLE = [s for s in SPELLS if s["tab"] is not None]

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
        "equippedItemClass": str(spec.get("equipped_class", -1)),
        "equippedItemSubClassMask": str(spec.get("equipped_mask", 0)),
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
        "procFlags": "0",
        "procChance": "0",
        "procCharges": "0",
        "dmgClass": str(spec.get("dmg_class", 1)),
        "preventionType": str(spec.get("prevention_type", 1)),
    })

    for key, col in (("attributes", "attributes"),
                     ("attributes_ex", "attributesEx"),
                     ("attributes_ex2", "attributesEx2"),
                     ("attributes_ex3", "attributesEx3"),
                     ("attributes_ex4", "attributesEx4")):
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
        "EquippedItemClass": spec.get("equipped_class", -1),
        "EquippedItemSubclass": spec.get("equipped_mask", 0),
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
        "DefenseType": spec.get("dmg_class", 1),
        "PreventionType": spec.get("prevention_type", 1),
    }

    for key, field in (("attributes", "Attributes"),
                       ("attributes_ex", "AttributesEx"),
                       ("attributes_ex2", "AttributesEx2"),
                       ("attributes_ex3", "AttributesEx3"),
                       ("attributes_ex4", "AttributesEx4"),
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
    ap.add_argument("--out", default="data/sql/world/20261020160000_world.sql")
    ap.add_argument("--client-yaml", default="client/patches/43b-talent-spells.yaml")
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
                     f"WHERE `id` BETWEEN {SERVER_SLA_BASE} AND "
                     f"{SERVER_SLA_BASE + len(TRAINABLE) - 1}"):
        if int(row[1]) not in our_ids:
            raise SystemExit(f"server skill_line_ability id {row[0]} is used by spell {row[1]}")

    donors = {spec["id"]: fetch_spell(md, port, cols, spec["donor"]) for spec in SPELLS}

    # --- server SQL ---------------------------------------------------------
    lines = []
    lines.append("-- FILE: 20261020160000_world.sql")
    lines.append("-- Necromancer (class 10) remaining talent spells (design A.4/A.8/A.9,")
    lines.append("-- 2026-10-20; talent shortcuts until the talent trees exist):")
    lines.append("--   61087 Soul Strike (Blood, L20) - 50% weapon damage + heal/disease")
    lines.append("--   61088 Icy Touch (Plague, L30) - Frost damage + Frost Fever 61095")
    lines.append("--   61089 Corrosion (Plague, L32) - -150 armor for 20 sec")
    lines.append("--   61093 Lichborne (Plague, L40) - -10% physical taken, 25% mana regen")
    lines.append("--   61094 Unholy Aura (Blood, L30) - party +8% speed / 25% regen")
    lines.append("-- Trainer learn spells 61146-61150 and npc_trainer rows are generated")
    lines.append("-- by generate_trainers.py; icons/tooltips by generate_cosmetic_pass.py.")
    lines.append("-- Generated by tools/generate_talent_spells.py; re-runnable.")
    lines.append("")
    spell_id_list = ", ".join(str(s["id"]) for s in SPELLS)
    lines.append(f"DELETE FROM `spell_template` WHERE `entry` IN ({spell_id_list});")
    lines.append(f"DELETE FROM `skill_line_ability` WHERE `id` BETWEEN {SERVER_SLA_BASE} AND "
                 f"{SERVER_SLA_BASE + len(TRAINABLE) - 1} OR `spell_id` IN ({spell_id_list});")
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
    for spec in TRAINABLE:
        lines.append("INSERT INTO `skill_line_ability` (`id`, `skill_id`, `spell_id`, `race_mask`, `class_mask`, `req_skill_value`, `superseded_by_spell`, `learn_on_get_skill`, `max_value`, `min_value`, `req_train_points`) VALUES (" +
                     f"{spec['server_sla']}, {spec['tab']}, {spec['id']}, 0, {CLASS_MASK}, 1, 0, 0, 0, 0, 0);")
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # --- client YAML --------------------------------------------------------
    y = []
    y.append("# Remaining Necromancer talent spells (design A.4/A.8/A.9, 2026-10-20).")
    y.append("# Server rows are generated by tools/generate_talent_spells.py.")
    y.append("# Frost Fever 61095 is the hidden Icy Touch aura (no spellbook row).")
    y.append("# Skill-line/tab assignments live in 50-skilllines.yaml.")
    y.append("Spell.dbc:")
    for spec in SPELLS:
        v = build_client_values(spec, donors[spec["id"]])
        y.append("  - type: copy")
        y.append(f"    key: {spec['donor']}")
        y.append("    values:")
        y.append(f"      ID: {v.pop('ID')}")
        for field in ("Name", "NameSubtext", "Description", "AuraDescription"):
            y += yaml_lang(field + "_lang", v.pop(field + "_lang"))
        y.append("      Name_lang_Mask: 4128894")
        y.append("      NameSubtext_lang_Mask: 4128894")
        y.append("      Description_lang_Mask: 4128894")
        y.append("      AuraDescription_lang_Mask: 4128892")
        for field, value in v.items():
            y.append(f"      {field}: {yaml_scalar(value)}")
        y.append("")

    with open(args.client_yaml, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(y))

    print(f"wrote {args.out}")
    print(f"wrote {args.client_yaml}")
    print(f"{len(SPELLS)} spells (5 trainable + Frost Fever), ids "
          f"{SPELLS[0]['id']}-{SPELLS[-1]['id']}, server SLA "
          f"{SERVER_SLA_BASE}-{SERVER_SLA_BASE + len(TRAINABLE) - 1}")


if __name__ == "__main__":
    main()


