#!/usr/bin/env python3
"""Generate the Necromancer Plague Strike batch (server SQL + client YAML).

Design A.8: Plague Strike is the level-10 quest spell of the Blood tree:
"weapon damage + X and infects the target with Toxic Plague (X-Y Nature over
15 s); direct damage +3% per disease on the target.  Instant, 6 s CD."

The spell is a mana-cost, instant melee strike cloned from Sinister Strike
(normalized weapon damage + flat bonus); the combo-point effect is removed.
The module script `spell_necromancer_plague_strike` applies Toxic Plague
rank 1 and the shared +3%-per-disease hook.  The spell is quest-gated by the
A85 placeholder quest 950107 (1x Lump of Flesh), offered by both trainers.

Outputs:
  data/sql/world/20261019230000_world.sql
  client/patches/42-plague-strike.yaml

The client learn-spell row 61131 is generated into
client/patches/41-learn-spells.yaml by generate_trainers.py (Plague Strike is
in TRAINABLE + QUEST_GATED there); the server row is emitted here.

Usage:
  python tools/generate_plague_strike.py
"""

import argparse
import subprocess

DEFAULT_MARIADB = r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe"

SPELL_ID = 61075
LEARN_SPELL_ID = 61131
QUEST_ID = 950107
DONOR = 1752           # Sinister Strike
LEARN_DONOR = 1374     # Immolate's learn spell
ITEM_ID = 63100        # Lump of Flesh
CLASS_MASK = 0x200
SKILL_LINE = 700
SERVER_SLA_ID = 7317
CLIENT_SLA_ID = 7242
TRAINERS = (950010, 950011)

SPELL_NAME = "Plague Strike"
SPELL_DESC = ("An instant strike that causes weapon damage plus $s1 and "
              "infects the target with Toxic Plague, causing Nature damage "
              "over 15 sec.  Direct damage is increased by 3% per disease on "
              "the target.")
QUEST_DETAILS = ("PLACEHOLDER QUEST - this will be replaced by the real "
                 "Necromancer class quest chain.\n\nBring one Lump of Flesh "
                 "from your Corpse Bag, and the trainer will teach you Plague "
                 "Strike.")

QUEST_COLUMNS = [
    "entry", "Method", "ZoneOrSort", "MinLevel", "MaxLevel", "QuestLevel",
    "Type", "RequiredClasses", "RequiredRaces", "RequiredSkill",
    "RequiredSkillValue", "RequiredCondition", "SuggestedPlayers",
    "LimitTime", "QuestFlags", "SpecialFlags", "PrevQuestId", "NextQuestId",
    "ExclusiveGroup", "NextQuestInChain", "SrcItemId", "SrcItemCount",
    "SrcSpell", "Title", "Details", "Objectives", "OfferRewardText",
    "RequestItemsText", "EndText", "ReqItemId1", "ReqItemCount1",
    "RewSpell", "RewSpellCast", "RewXP", "RewOrReqMoney", "RewMoneyMaxLevel",
    "StartScript", "CompleteScript",
]


def query(mariadb, port, sql):
    out = subprocess.run(
        [mariadb, f"--port={port}", "-u", "root", "tw_world",
         "--batch", "--skip-column-names", "-e", sql],
        capture_output=True, text=True, check=True,
    )
    return [line.split("\t") for line in out.stdout.splitlines() if line.strip()]


def table_columns(mariadb, port, table):
    rows = query(mariadb, port,
                 "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
                 f"WHERE table_schema='tw_world' AND table_name='{table}' "
                 "ORDER BY ORDINAL_POSITION")
    return [r[0] for r in rows], {r[0]: r[1] for r in rows}


def sql_literal(value, data_type):
    if value == "NULL":
        return "NULL"
    if data_type in ("tinyint", "smallint", "mediumint", "int", "bigint",
                     "float", "double", "decimal"):
        return value
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_text(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def insert_statement(table, columns, values):
    cols = ", ".join(f"`{c}`" for c in columns)
    vals = ", ".join(values)
    return f"INSERT INTO `{table}` ({cols}) VALUES ({vals});"


def lang_block(field, value):
    return [f"      {field}_lang_{i}: \"{value}\"" for i in range(8)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=DEFAULT_MARIADB)
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", default="data/sql/world/20261019230000_world.sql")
    ap.add_argument("--client-yaml", default="client/patches/42-plague-strike.yaml")
    args = ap.parse_args()

    md, port = args.mariadb, args.port

    spell_cols, spell_types = table_columns(md, port, "spell_template")
    entry_idx = spell_cols.index("entry")

    def fetch_spell(entry):
        rows = query(md, port, f"SELECT * FROM `spell_template` WHERE `entry` = {entry}")
        if len(rows) != 1:
            raise SystemExit(f"spell_template donor {entry} not found")
        if len(rows[0]) != len(spell_cols):
            raise SystemExit(f"spell_template donor {entry} column width mismatch")
        return rows[0]

    donor = fetch_spell(DONOR)
    learn_donor = fetch_spell(LEARN_DONOR)

    quest_rows = query(md, port,
                       f"SELECT `entry`, `Title` FROM `quest_template` WHERE `entry` = {QUEST_ID}")
    for entry, title in quest_rows:
        if title != f"PLACEHOLDER: {SPELL_NAME}":
            raise SystemExit(f"quest {entry} is already used by '{title}'")
    sla_rows = query(md, port,
                     f"SELECT `id`, `spell_id` FROM `skill_line_ability` WHERE `id` = {SERVER_SLA_ID}")
    for entry, spell_id in sla_rows:
        if spell_id != str(SPELL_ID):
            raise SystemExit(f"server skill_line_ability id {entry} is used by spell {spell_id}")
    if query(md, port, f"SELECT `entry` FROM `item_template` WHERE `entry` = {ITEM_ID}")[0][0] != str(ITEM_ID):
        raise SystemExit(f"item {ITEM_ID} not found")

    # --- server spell row ---------------------------------------------------
    values = dict(zip(spell_cols, donor))
    values.update({
        "entry": str(SPELL_ID),
        "name": SPELL_NAME,
        "nameSubtext": "",
        "description": SPELL_DESC,
        "auraDescription": "",
        "school": "0",
        "category": "0",
        "castUI": "0",
        "dispel": "0",
        "mechanic": "0",
        "targets": "0",
        "targetCreatureType": "0",
        "castingTimeIndex": "0",
        "recoveryTime": "6000",
        "categoryRecoveryTime": "0",
        "powerType": "0",
        "manaCost": "25",
        "manaCostPercentage": "0",
        "rangeIndex": "2",
        "speed": "0",
        "maxLevel": "0",
        "baseLevel": "10",
        "spellLevel": "10",
        "equippedItemClass": "2",
        "equippedItemSubClassMask": "0",
        "equippedItemInventoryTypeMask": "0",
        "spellIconId": "130",
        "spellFamilyName": "0",
        "spellFamilyFlags": "0",
        "startRecoveryCategory": "133",
        "startRecoveryTime": "1500",
        "customFlags": "128",
        "script_name": "spell_necromancer_plague_strike",
    })
    for idx in ("2", "3"):
        for col in ("effectDieSides", "effectBaseDice", "effectDicePerLevel",
                    "effectRealPointsPerLevel", "effectBasePoints",
                    "effectBonusCoefficient", "effectMechanic",
                    "effectImplicitTargetA", "effectImplicitTargetB",
                    "effectRadiusIndex", "effectApplyAuraName",
                    "effectAmplitude", "effectMultipleValue",
                    "effectChainTarget", "effectItemType", "effectMiscValue",
                    "effectTriggerSpell", "effectPointsPerComboPoint"):
            values[f"{col}{idx}"] = "0"
    values["effect2"] = "0"
    values["effect3"] = "0"
    spell_values = [sql_literal(values[c], spell_types[c]) for c in spell_cols]

    # --- server learn-spell row --------------------------------------------
    learn_values = dict(zip(spell_cols, learn_donor))
    learn_values.update({
        "entry": str(LEARN_SPELL_ID),
        "name": SPELL_NAME,
        "nameSubtext": "",
        "description": SPELL_DESC,
        "auraDescription": "",
        "spellIconId": "130",
        "effect1": "36",
        "effect2": "0",
        "effect3": "0",
        "effectTriggerSpell1": str(SPELL_ID),
        "effectTriggerSpell2": "0",
        "effectTriggerSpell3": "0",
        "spellLevel": "0",
        "baseLevel": "0",
        "maxLevel": "0",
        "manaCost": "0",
        "customFlags": "0",
        "script_name": "",
    })
    learn_spell_values = [sql_literal(learn_values[c], spell_types[c]) for c in spell_cols]

    # --- SQL ----------------------------------------------------------------
    lines = []
    lines.append("-- FILE: 20261019230000_world.sql")
    lines.append("-- Necromancer (class 10) Plague Strike batch (design A.8, 2026-10-19):")
    lines.append("-- 61075 Plague Strike (Sinister Strike clone; instant, 6 s CD, mana;")
    lines.append("-- Toxic Plague rider + 3%/disease handled by the module), its learn")
    lines.append("-- spell 61131, the Necromancy skill-line row, and the A85 placeholder")
    lines.append("-- quest 950107 (1x Lump of Flesh, both trainers).  Generated by")
    lines.append("-- tools/generate_plague_strike.py; re-runnable.")
    lines.append("")
    lines.append(f"DELETE FROM `spell_template` WHERE `entry` IN ({SPELL_ID}, {LEARN_SPELL_ID});")
    lines.append(f"DELETE FROM `skill_line_ability` WHERE `id` = {SERVER_SLA_ID} OR `spell_id` = {SPELL_ID};")
    lines.append(f"DELETE FROM `npc_trainer` WHERE `spell` = {LEARN_SPELL_ID};")
    lines.append(f"DELETE FROM `quest_template` WHERE `entry` = {QUEST_ID};")
    lines.append(f"DELETE FROM `creature_questrelation` WHERE `quest` = {QUEST_ID};")
    lines.append(f"DELETE FROM `creature_involvedrelation` WHERE `quest` = {QUEST_ID};")
    lines.append("UPDATE `creature_template` SET `npc_flags` = `npc_flags` | 2, "
                 f"`gossip_menu_id` = 0 WHERE `entry` IN ({', '.join(str(t) for t in TRAINERS)});")
    lines.append("")
    lines.append("-- Plague Strike (server spell_template copy of Sinister Strike 1752)")
    lines.append(insert_statement("spell_template", spell_cols, spell_values))
    lines.append("")
    lines.append("-- Learn-spell wrapper 61131 (quest reward cast; not a trainer row)")
    lines.append(insert_statement("spell_template", spell_cols, learn_spell_values))
    lines.append("")
    lines.append("-- Necromancy skill line (server side; client SkillLineAbility row is 7242)")
    lines.append(insert_statement("skill_line_ability",
                                  ["id", "skill_id", "spell_id", "race_mask",
                                   "class_mask", "req_skill_value",
                                   "superseded_by_spell", "learn_on_get_skill",
                                   "max_value", "min_value", "req_train_points"],
                                  [str(SERVER_SLA_ID), str(SKILL_LINE), str(SPELL_ID),
                                   "0", str(CLASS_MASK), "1", "0", "0", "0", "0", "0"]))
    lines.append("")
    lines.append("-- A85 placeholder quest 950107: 1x Lump of Flesh -> Plague Strike")
    quest_values = [
        str(QUEST_ID), "2", "0", "10", "0", "10", "0",
        str(CLASS_MASK), "0", "0", "0", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "0", "0",
        sql_text(f"PLACEHOLDER: {SPELL_NAME}"),
        sql_text(QUEST_DETAILS),
        sql_text("Bring 1 Lump of Flesh to your Necromancer trainer."),
        sql_text("The dead are patient, and now they answer you. Take this knowledge."),
        sql_text("Bring me 1 Lump of Flesh from your Corpse Bag."),
        sql_text(""),
        str(ITEM_ID), "1",
        str(SPELL_ID), str(LEARN_SPELL_ID),
        "0", "0", "0",
        "0", "0",
    ]
    lines.append(insert_statement("quest_template", QUEST_COLUMNS, quest_values))
    lines.append("")
    for trainer in TRAINERS:
        lines.append(f"INSERT INTO `creature_questrelation` (`id`, `quest`) VALUES ({trainer}, {QUEST_ID});")
    for trainer in TRAINERS:
        lines.append(f"INSERT INTO `creature_involvedrelation` (`id`, `quest`) VALUES ({trainer}, {QUEST_ID});")
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # --- client YAML --------------------------------------------------------
    y = []
    y.append("# Plague Strike (61075), design A.8 (2026-10-19).")
    y.append("# Copy of Sinister Strike 1752: normalized weapon damage + flat bonus,")
    y.append("# instant, 5 yd, 6 s cooldown, mana cost 25 (placeholder; design gives")
    y.append("# no numbers).  The combo-point effect is removed.  The module script")
    y.append("# `spell_necromancer_plague_strike` applies Toxic Plague rank 1 and the")
    y.append("# +3%-per-disease direct damage hook.  Generated by")
    y.append("# tools/generate_plague_strike.py.")
    y.append("Spell.dbc:")
    y.append("  - type: copy")
    y.append(f"    key: {DONOR}")
    y.append("    values:")
    y.append(f"      ID: {SPELL_ID}")
    y += lang_block("Name", SPELL_NAME)
    y += lang_block("NameSubtext", "")
    y += lang_block("Description", SPELL_DESC)
    y += lang_block("AuraDescription", "")
    y.append("      SpellIconID: 130")
    y.append("      School: 0")
    y.append("      Category: 0")
    y.append("      CastUI: 0")
    y.append("      DispelType: 0")
    y.append("      Mechanic: 0")
    y.append("      Targets: 0")
    y.append("      TargetCreatureType: 0")
    y.append("      CastingTimeIndex: 0")
    y.append("      RecoveryTime: 6000")
    y.append("      CategoryRecoveryTime: 0")
    y.append("      PowerType: 0")
    y.append("      ManaCost: 25")
    y.append("      ManaCostPct: 0")
    y.append("      RangeIndex: 2")
    y.append("      Speed: 0")
    y.append("      MaxLevel: 0")
    y.append("      BaseLevel: 10")
    y.append("      SpellLevel: 10")
    y.append("      EquippedItemClass: 2")
    y.append("      EquippedItemSubclass: 0")
    y.append("      EquippedItemInvType: 0")
    y.append("      SpellClassSet: 0")
    y.append("      SpellClassMask_1: 0")
    y.append("      SpellClassMask_2: 0")
    y.append("      StartRecoveryCategory: 133")
    y.append("      StartRecoveryTime: 1500")
    for idx in ("2", "3"):
        y.append(f"      Effect_{idx}: 0")
        y.append(f"      EffectDieSides_{idx}: 0")
        y.append(f"      EffectBaseDice_{idx}: 0")
        y.append(f"      EffectDicePerLevel_{idx}: 0")
        y.append(f"      EffectRealPointsPerLevel_{idx}: 0")
        y.append(f"      EffectBasePoints_{idx}: 0")
        y.append(f"      EffectMechanic_{idx}: 0")
        y.append(f"      ImplicitTargetA_{idx}: 0")
        y.append(f"      ImplicitTargetB_{idx}: 0")
        y.append(f"      EffectRadiusIndex_{idx}: 0")
        y.append(f"      EffectAura_{idx}: 0")
        y.append(f"      EffectAmplitude_{idx}: 0")
        y.append(f"      EffectMultipleValue_{idx}: 0")
        y.append(f"      EffectChainTarget_{idx}: 0")
        y.append(f"      EffectItemType_{idx}: 0")
        y.append(f"      EffectMiscValue_{idx}: 0")
        y.append(f"      EffectTriggerSpell_{idx}: 0")
        y.append(f"      EffectPointsPerCombo_{idx}: 0")
    with open(args.client_yaml, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(y) + "\n")

    print(f"wrote {args.out}")
    print(f"wrote {args.client_yaml}")
    print(f"Plague Strike {SPELL_ID}, learn {LEARN_SPELL_ID}, quest {QUEST_ID}, "
          f"server SLA {SERVER_SLA_ID}, client SLA {CLIENT_SLA_ID}")


if __name__ == "__main__":
    main()
