#!/usr/bin/env python3
"""Generate the Necromancer trainer data (server SQL + client learn-spell DBC YAML).

The trainers replace the module's auto-learn (design step 9): one class trainer
in Orgrimmar (Cleft of Shadow) and one in Stormwind (Slaughtered Lamb cellar).
Both teach every currently shipped Necromancer spell and rank except the
quest-gated ones (A85 placeholder quests, see
tools/generate_placeholder_quests.py); the learn-spell wrappers for those stay
in the generated 61100-61142 block because the quests use them as
`RewSpellCast`.

Trainer spells follow the vanilla convention: `npc_trainer.spell` points at a
*learn spell* (Effect[0] = 36 LEARN_SPELL) whose EffectTriggerSpell[0] is the
real spell.  The learn spells (61100+) are cloned from Immolate's learn spell
1374 on the server and added to the client Spell.dbc via patch-Z.mpq.

Usage:
  python tools/generate_trainers.py --out data/sql/world/20261019200000_world.sql
  python tools/generate_trainers.py --client-yaml client/patches/41-learn-spells.yaml

(--out / --client-yaml write UTF-8 directly; do not use PowerShell ">".)
"""

import argparse
import json
import subprocess
import sys

DEFAULT_MARIADB = r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe"

CLASS_NECROMANCER = 10

# (creature entry, donor creature entry, name, subname, gossip menu, greeting,
#  map, x, y, z, orientation)
TRAINERS = [
    dict(entry=950010, donor=3324, name="Gorvoth the Gravewarden",
         subname="Necromancer Trainer", gossip_menu=0,
         greeting="The dead are patient.  What do you wish to learn?",
         map=1, x=1840.0, y=-4368.0, z=-14.8, o=1.5),
    dict(entry=950011, donor=5495, name="Mordecai Gravewhisper",
         subname="Necromancer Trainer", gossip_menu=0,
         greeting="The grave teaches many things.  What do you seek?",
         map=0, x=-8981.0, y=1028.0, z=101.487, o=3.5),
]

# (actual spell id, learn level, rank label) - every currently shipped
# spellbook spell/rank; rank-1 starting spells are included so the trainer
# window is complete (they show gray for characters that already know them).
TRAINABLE = [
    (61010, 1,  "Rank 1"),   # Plague Bolt
    (61013, 1,  "Rank 1"),   # Reap
    (61015, 1,  ""),         # Bone Armor
    (61011, 8,  "Rank 2"),   # Plague Bolt
    (61029, 10, ""),         # Harvest
    (61034, 10, ""),         # Raise Zombie
    (61035, 10, ""),         # Raise Shade
    (61016, 12, "Rank 1"),   # Call of the Grave
    (61014, 12, "Rank 2"),   # Reap
    (61074, 14, ""),         # Death Coil
    (61024, 14, ""),         # Raise Ghoul
    (61025, 14, ""),         # Raise Skeleton
    (61012, 16, "Rank 3"),   # Plague Bolt
    (61019, 20, "Rank 1"),   # Desecration
    (61022, 20, ""),         # Disease Cloud
    (61023, 20, ""),         # Cripple
    (61026, 20, ""),         # Tether
    (61028, 20, ""),         # Sacrifice Minion
    (61033, 20, ""),         # Ghoul Frenzy
    (61036, 20, ""),         # Raise Banshee
    (61049, 20, "Rank 1"),   # Army of the Dead
    (61017, 24, "Rank 2"),   # Call of the Grave
    (61037, 30, ""),         # Raise Wraith
    (61018, 34, "Rank 3"),   # Call of the Grave
    (61020, 34, "Rank 2"),   # Desecration
    (61038, 38, ""),         # Raise Bloodmage
    (61039, 40, ""),         # Raise Abomination
    (61050, 40, "Rank 2"),   # Army of the Dead
    (61048, 44, ""),         # Meat Catapult
    (61021, 46, "Rank 3"),   # Desecration
    (61040, 58, ""),         # Raise Wight
    (61075, 10, ""),         # Plague Strike (quest-gated, learn wrapper only)
    # remaining spellbook batch (2026-10-19; appended so learn ids stay stable)
    (61076, 6,  ""),         # Bloodlet
    (61077, 10, ""),         # Dark Command
    (61078, 14, ""),         # Terror
    (61079, 20, ""),         # Ghoul Armor
    (61080, 24, ""),         # Embalm
    (61081, 26, ""),         # Lobotomize
    (61082, 26, ""),         # Outbreak
    (61083, 28, ""),         # Rule Undead
    (61084, 34, ""),         # Unholy Shield
    (61085, 40, ""),         # Lich Armor
    (61086, 42, ""),         # Dark Punishment
]

# These spells are quest-gated by the A85 placeholder quests
# (tools/generate_placeholder_quests.py) and must not appear in npc_trainer.
# Their learn-spell wrappers stay in the 61100-61142 block (RewSpellCast).
QUEST_GATED = {
    61029,  # Harvest
    61034,  # Raise Zombie
    61035,  # Raise Shade
    61024,  # Raise Ghoul
    61025,  # Raise Skeleton
    61036,  # Raise Banshee
    61037,  # Raise Wraith
    61075,  # Plague Strike
}

LEARN_SPELL_BASE = 61100
LEARN_SPELL_DONOR = 1374  # vanilla learn-spell scaffold (Effect[0] = LEARN_SPELL)
LEARN_SPELL_MAX = LEARN_SPELL_BASE + len(TRAINABLE) - 1

# vanilla class-trainer prices by required level (copper)
COST_BY_LEVEL = {
    1: 10, 4: 100, 6: 100, 8: 200, 10: 300, 12: 600, 14: 900,
    16: 1200, 18: 1500, 20: 2000, 22: 2500, 24: 3000, 26: 4000,
    28: 5000, 30: 6000, 32: 7000, 34: 8000, 36: 9000, 38: 10000,
    40: 11000, 42: 11000, 44: 12000, 46: 13000, 48: 14000,
    50: 15000, 52: 18000, 54: 20000, 56: 22000, 58: 24000, 60: 26000,
}

NPC_FLAG_TRAINER = 16
NPC_FLAG_GOSSIP = 1
NPC_FLAG_QUESTGIVER = 2


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
        # mysql --batch escapes backslash, tab, newline and NUL
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


def columns(mariadb, port, table):
    return [r[0] for r in query(mariadb, port, f"SHOW COLUMNS FROM `{table}`")]


def fetch_row(mariadb, port, table, entry):
    cols = columns(mariadb, port, table)
    rows = query(mariadb, port, f"SELECT * FROM `{table}` WHERE `entry` = {entry}")
    if len(rows) != 1:
        raise SystemExit(f"expected one row in {table} for {entry}, got {len(rows)}")
    if len(rows[0]) != len(cols):
        raise SystemExit(f"{table} row width {len(rows[0])} != {len(cols)} columns")
    return cols, dict(zip(cols, rows[0]))


def is_text_col(col_type):
    t = col_type.lower()
    return any(x in t for x in ("char", "text", "enum", "set"))


def sql_literal(value, col_type):
    if value == "NULL":
        return "NULL"
    if is_text_col(col_type):
        return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"
    return value


def insert_statement(table, cols, values):
    col_list = ", ".join(f"`{c}`" for c in cols)
    val_list = ", ".join(values)
    return f"INSERT INTO `{table}` ({col_list}) VALUES ({val_list});"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=DEFAULT_MARIADB)
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", default="data/sql/world/20261019200000_world.sql")
    ap.add_argument("--client-yaml", default="client/patches/41-learn-spells.yaml")
    args = ap.parse_args()

    md, port = args.mariadb, args.port

    # --- sanity: ids are free (or ours from a previous run) -----------------
    used = query(md, port,
                 f"SELECT `entry`, `name` FROM `creature_template` "
                 f"WHERE `entry` IN ({','.join(str(t['entry']) for t in TRAINERS)})")
    for entry, name in used:
        if name not in [t["name"] for t in TRAINERS]:
            raise SystemExit(f"creature_template {entry} is used by '{name}'")
    expected_triggers = {str(s) for s, _, _ in TRAINABLE}
    existing = query(md, port,
                     f"SELECT `entry`, `effect1`, `effectTriggerSpell1` FROM `spell_template` "
                     f"WHERE `entry` BETWEEN {LEARN_SPELL_BASE} AND {LEARN_SPELL_MAX}")
    for entry, effect, trigger in existing:
        if effect != "36" or trigger not in expected_triggers:
            raise SystemExit(f"learn-spell id {entry} is already used by another spell")

    # --- donor template rows ------------------------------------------------
    ct_cols = columns(md, port, "creature_template")
    ct_donors = {}
    for t in TRAINERS:
        cols, row = fetch_row(md, port, "creature_template", t["donor"])
        if cols != ct_cols:
            raise SystemExit("creature_template column order mismatch")
        ct_donors[t["entry"]] = row
    st_cols, donor_st = fetch_row(md, port, "spell_template", LEARN_SPELL_DONOR)

    ct_types = {r[0]: r[1] for r in query(md, port, "SHOW COLUMNS FROM `creature_template`")}
    st_types = {r[0]: r[1] for r in query(md, port, "SHOW COLUMNS FROM `spell_template`")}

    # --- actual spell metadata ---------------------------------------------
    spell_ids = ",".join(str(s) for s, _, _ in TRAINABLE)
    spell_rows = query(
        md, port,
        "SELECT `entry`, `name`, `nameSubtext`, `description`, `auraDescription`, `spellIconId` "
        f"FROM `spell_template` WHERE `entry` IN ({spell_ids})")
    spell_meta = {}
    for r in spell_rows:
        if len(r) != 6:
            raise SystemExit(f"unexpected spell_template row: {r}")
        spell_meta[r[0]] = dict(zip(
            ["entry", "name", "nameSubtext", "description", "auraDescription", "spellIconId"], r))
    missing = [s for s, _, _ in TRAINABLE if str(s) not in spell_meta]
    if missing:
        raise SystemExit(f"missing actual spells: {missing}")

    learn_ids = {}
    for i, (spell_id, level, rank) in enumerate(TRAINABLE):
        learn_ids[spell_id] = LEARN_SPELL_BASE + i
        if level not in COST_BY_LEVEL:
            raise SystemExit(f"no trainer price for level {level} (spell {spell_id})")

    lines = []
    lines.append("-- FILE: 20261019200000_world.sql")
    lines.append("-- Necromancer (class 10) trainers (2026-10-19): one class trainer in")
    lines.append("-- Orgrimmar (Cleft of Shadow) and one in Stormwind (Slaughtered Lamb).")
    lines.append("-- Replaces the module's auto-learn: every shipped spell/rank is now")
    lines.append("-- trained.  Trainer rows point at learn spells 61100-61142 (cloned from")
    lines.append("-- Immolate's learn spell 1374); patch-Z adds their client Spell.dbc rows.")
    lines.append("-- Generated by tools/generate_trainers.py; re-runnable.")
    lines.append("")
    lines.append("DELETE FROM `npc_trainer` WHERE `entry` IN (950010, 950011);")
    lines.append("DELETE FROM `npc_trainer_greeting` WHERE `entry` IN (950010, 950011);")
    lines.append("DELETE FROM `creature` WHERE `id` IN (950010, 950011);")
    lines.append("DELETE FROM `creature_template` WHERE `entry` IN (950010, 950011);")
    lines.append(f"DELETE FROM `spell_template` WHERE `entry` BETWEEN {LEARN_SPELL_BASE} AND {LEARN_SPELL_MAX};")
    lines.append("")

    # --- creature_template rows --------------------------------------------
    lines.append("-- Trainer NPCs (cloned from the city warlock trainers; trainer_class 10)")
    for t in TRAINERS:
        row = dict(ct_donors[t["entry"]])
        row.update({
            "entry": str(t["entry"]),
            "name": t["name"],
            "subname": t["subname"],
            "gossip_menu_id": str(t["gossip_menu"]),
            "npc_flags": str(NPC_FLAG_TRAINER | NPC_FLAG_GOSSIP | NPC_FLAG_QUESTGIVER),
            "trainer_type": "0",
            "trainer_spell": "0",
            "trainer_class": str(CLASS_NECROMANCER),
            "trainer_race": "0",
            "trainer_id": "0",
            "script_name": "",
        })
        vals = [sql_literal(row[c], ct_types[c]) for c in ct_cols]
        lines.append(insert_statement("creature_template", ct_cols, vals))
    lines.append("")

    # --- spawns -------------------------------------------------------------
    lines.append("-- Trainer spawns (no explicit guid: auto-increment; re-runs delete first)")
    spawn_cols = ["id", "map", "position_x", "position_y", "position_z", "orientation",
                  "spawntimesecsmin", "spawntimesecsmax", "wander_distance",
                  "health_percent", "mana_percent", "movement_type", "spawn_flags",
                  "visibility_mod"]
    for t in TRAINERS:
        vals = [str(t["entry"]), str(t["map"]), f"{t['x']:.4f}", f"{t['y']:.4f}",
                f"{t['z']:.4f}", f"{t['o']:.4f}", "25", "25", "0", "100", "100",
                "0", "0", "0"]
        lines.append(insert_statement("creature", spawn_cols, vals))
    lines.append("")

    # --- trainer greeting + gossip option -----------------------------------
    lines.append("-- Trainer window title")
    greet_cols = ["entry", "content_default"] + [f"content_loc{i}" for i in range(1, 9)]
    for t in TRAINERS:
        vals = [str(t["entry"]), sql_literal(t["greeting"], "text")] + \
               [sql_literal("", "text") for _ in range(8)]
        lines.append(insert_statement("npc_trainer_greeting", greet_cols, vals))
    lines.append("")

    # --- learn spells (server) ---------------------------------------------
    lines.append("-- Learn spells 61100-61142 (Effect[0] = LEARN_SPELL; trigger = real spell)")
    for spell_id, level, rank in TRAINABLE:
        meta = spell_meta[str(spell_id)]
        learn_id = learn_ids[spell_id]
        row = dict(donor_st)
        row.update({
            "entry": str(learn_id),
            "name": meta["name"],
            "nameSubtext": rank,
            "description": meta["description"],
            "auraDescription": meta["auraDescription"],
            "spellIconId": meta["spellIconId"],
            "effect1": "36",
            "effect2": "0",
            "effect3": "0",
            "effectTriggerSpell1": str(spell_id),
            "effectTriggerSpell2": "0",
            "effectTriggerSpell3": "0",
            "spellLevel": "0",
            "baseLevel": "0",
            "maxLevel": "0",
            "manaCost": "0",
            "script_name": "",
        })
        vals = [sql_literal(row[c], st_types[c]) for c in st_cols]
        lines.append(insert_statement("spell_template", st_cols, vals))
    lines.append("")

    # --- npc_trainer rows ---------------------------------------------------
    lines.append("-- Trainer spell lists (learn spell id, price by level)")
    lines.append("-- Quest-gated spells are omitted (A85 placeholder quests).")
    for t in TRAINERS:
        for spell_id, level, rank in TRAINABLE:
            if spell_id in QUEST_GATED:
                continue
            vals = [str(t["entry"]), str(learn_ids[spell_id]),
                    str(COST_BY_LEVEL[level]), "0", "0", str(level)]
            lines.append(insert_statement("npc_trainer",
                                          ["entry", "spell", "spellcost", "reqskill",
                                           "reqskillvalue", "reqlevel"], vals))
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # --- client YAML --------------------------------------------------------
    y = []
    y.append("# Learn spells 61100-61142 for the Necromancer trainers.")
    y.append("# Cloned from Immolate's vanilla learn spell 1374 (Effect[0] =")
    y.append("# LEARN_SPELL); the trigger is the real Necromancer spell.  The")
    y.append("# trainer packet sends these ids, so the client needs their names/")
    y.append("# ranks/icons/descriptions.  Generated by generate_trainers.py.")
    y.append("Spell.dbc:")
    for spell_id, level, rank in TRAINABLE:
        meta = spell_meta[str(spell_id)]
        learn_id = learn_ids[spell_id]
        y.append("  - type: copy")
        y.append(f"    key: {LEARN_SPELL_DONOR}")
        y.append("    values:")
        y.append(f"      ID: {learn_id}")
        for i in range(8):
            y.append(f"      Name_lang_{i}: {json.dumps(meta['name'])}")
        for i in range(8):
            y.append(f"      NameSubtext_lang_{i}: {json.dumps(rank)}")
        for i in range(8):
            y.append(f"      Description_lang_{i}: {json.dumps(meta['description'])}")
        for i in range(8):
            y.append(f"      AuraDescription_lang_{i}: {json.dumps(meta['auraDescription'])}")
        y.append(f"      SpellIconID: {meta['spellIconId']}")
        y.append(f"      EffectTriggerSpell_1: {spell_id}")
    with open(args.client_yaml, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(y) + "\n")

    print(f"wrote {args.out}")
    print(f"wrote {args.client_yaml}")
    print(f"{len(TRAINABLE)} trainable spells, learn ids "
          f"{LEARN_SPELL_BASE}-{LEARN_SPELL_MAX}")


if __name__ == "__main__":
    main()
