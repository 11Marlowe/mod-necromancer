#!/usr/bin/env python3
"""Generate the Necromancer placeholder class quests (server SQL).

Design decision A85: until the real class quest chains exist, every
quest-gated spell gets a simple placeholder quest offered by both class
trainers.  Each quest is level-gated, turns in one item (a Corpse Bag item,
except Harvest which uses Linen Cloth) and rewards the real spell through the
existing trainer learn-spell wrappers
(61100-61130) in `RewSpellCast`; `RewSpell` carries the real spell so the
client shows its icon/name.

This batch:
  L10  Raise Zombie   1x Lump of Flesh     (63100)
  L10  Raise Shade    1x Ectoplasm         (63102)
  L10  Harvest        1x Linen Cloth       (2589)
  L14  Raise Ghoul    1x Lump of Flesh     (63100)
  L14  Raise Skeleton 1x Pile of Bones     (63101)
  L20  Raise Banshee  1x Banshee Essence   (63103)
  L30  Raise Wraith   1x Ectoplasm         (63102)

The quests are limited to class 10 (`RequiredClasses` 0x200), start and end
at both trainers (Orgrimmar 950010, Stormwind 950011), and the trainer rows
for these seven spells are removed from `npc_trainer`.

Usage:
  python tools/generate_placeholder_quests.py --out data/sql/world/20261019220000_world.sql
"""

import argparse
import subprocess

DEFAULT_MARIADB = r"C:\Users\gawrg\Desktop\TurtleTest\server\mariadb-portable\bin\mariadb.exe"

CLASS_MASK_NECROMANCER = 0x200
TRAINER_ENTRIES = (950010, 950011)
LEARN_SPELL_MIN = 61100
LEARN_SPELL_MAX = 61130
QUEST_BASE = 950100

NPC_FLAG_QUESTGIVER = 0x2

# (quest id, real spell, spell name, level, item id, item name, placeholder text)
QUESTS = [
    (950100, 61034, "Raise Zombie", 10, 63100, "Lump of Flesh",
     "Bring one Lump of Flesh from your Corpse Bag, and the trainer will "
     "teach you to raise a zombie."),
    (950101, 61035, "Raise Shade", 10, 63102, "Ectoplasm",
     "Bring one Ectoplasm from your Corpse Bag, and the trainer will teach "
     "you to raise a shade."),
    (950102, 61029, "Harvest", 10, 2589, "Linen Cloth",
     "Bring one Linen Cloth, and the trainer will teach you to harvest "
     "corpses."),
    (950103, 61024, "Raise Ghoul", 14, 63100, "Lump of Flesh",
     "Bring one Lump of Flesh from your Corpse Bag, and the trainer will "
     "teach you to raise a ghoul."),
    (950104, 61025, "Raise Skeleton", 14, 63101, "Pile of Bones",
     "Bring one Pile of Bones from your Corpse Bag, and the trainer will "
     "teach you to raise a skeleton."),
    (950105, 61036, "Raise Banshee", 20, 63103, "Banshee Essence",
     "Bring one Banshee Essence from your Corpse Bag, and the trainer will "
     "teach you to raise a banshee."),
    (950106, 61037, "Raise Wraith", 30, 63102, "Ectoplasm",
     "Bring one Ectoplasm from your Corpse Bag, and the trainer will teach "
     "you to raise a wraith."),
]

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
    rows = []
    for line in out.stdout.splitlines():
        line = line.rstrip("\r")
        if line:
            rows.append(line.split("\t"))
    return rows


def sql_text(value):
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_value(value):
    return str(value)


def insert_statement(table, columns, values):
    cols = ", ".join(f"`{c}`" for c in columns)
    vals = ", ".join(sql_value(v) for v in values)
    return f"INSERT INTO `{table}` ({cols}) VALUES ({vals});"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb", default=DEFAULT_MARIADB)
    ap.add_argument("--port", default="3307")
    ap.add_argument("--out", default="data/sql/world/20261019220000_world.sql")
    args = ap.parse_args()

    md, port = args.mariadb, args.port

    # --- sanity: trainers and items exist -----------------------------------
    trainer_rows = query(
        md, port,
        "SELECT `entry`, `name`, `npc_flags`, `trainer_class` FROM `creature_template` "
        f"WHERE `entry` IN ({','.join(str(t) for t in TRAINER_ENTRIES)})")
    trainers = {int(r[0]): r for r in trainer_rows}
    if len(trainers) != len(TRAINER_ENTRIES):
        raise SystemExit("the Necromancer trainers do not exist; apply the trainer SQL first")
    for entry, name, flags, trainer_class in trainer_rows:
        if trainer_class != "10":
            raise SystemExit(f"trainer {entry} has trainer_class {trainer_class}, expected 10")

    items = query(
        md, port,
        "SELECT `entry`, `name` FROM `item_template` "
        f"WHERE `entry` IN ({','.join(str(q[4]) for q in QUESTS)})")
    item_names = {int(r[0]): r[1] for r in items}
    for _, _, _, _, item_id, item_name, _ in QUESTS:
        if item_names.get(item_id) != item_name:
            raise SystemExit(f"item {item_id} is missing or not named '{item_name}'")

    # --- sort the real spells by the learn-spell wrappers --------------------
    learn_rows = query(
        md, port,
        "SELECT `entry`, `effect1`, `effectTriggerSpell1` FROM `spell_template` "
        f"WHERE `entry` BETWEEN {LEARN_SPELL_MIN} AND {LEARN_SPELL_MAX}")
    learn_by_trigger = {}
    for entry, effect, trigger in learn_rows:
        if effect != "36":
            raise SystemExit(f"spell {entry} is not a learn spell (effect1 {effect})")
        learn_by_trigger.setdefault(int(trigger), int(entry))

    for _, spell_id, spell_name, _, _, _, _ in QUESTS:
        if spell_id not in learn_by_trigger:
            raise SystemExit(
                f"no learn-spell wrapper for {spell_name} ({spell_id}) "
                f"in {LEARN_SPELL_MIN}-{LEARN_SPELL_MAX}")

    spell_rows = query(
        md, port,
        "SELECT `entry`, `name` FROM `spell_template` "
        f"WHERE `entry` IN ({','.join(str(q[1]) for q in QUESTS)})")
    spell_names = {int(r[0]): r[1] for r in spell_rows}
    for _, spell_id, spell_name, _, _, _, _ in QUESTS:
        if spell_names.get(spell_id) != spell_name:
            raise SystemExit(
                f"spell {spell_id} is missing or not named '{spell_name}'")

    # --- sanity: quest ids are free (or ours from a previous run) -----------
    quest_ids = [q[0] for q in QUESTS]
    existing = query(
        md, port,
        "SELECT `entry`, `Title` FROM `quest_template` "
        f"WHERE `entry` BETWEEN {QUEST_BASE} AND {QUEST_BASE + len(QUESTS) - 1}")
    expected_titles = {str(qid): f"PLACEHOLDER: {q[2]}" for q in QUESTS
                       for qid in [q[0]]}
    for entry, title in existing:
        if expected_titles.get(entry) != title:
            raise SystemExit(
                f"quest id {entry} is already used by '{title}'")

    lines = []
    lines.append("-- FILE: 20261019220000_world.sql")
    lines.append("-- Necromancer (class 10) placeholder class quests (A85, 2026-10-19).")
    lines.append("-- Seven level-gated item turn-ins (Corpse Bag items; Harvest uses Linen")
    lines.append("-- Cloth), offered by both")
    lines.append("-- trainers (Orgrimmar 950010, Stormwind 950011).  RewSpell is the real")
    lines.append("-- spell (client icon/name); RewSpellCast is its trainer learn-spell")
    lines.append("-- wrapper (61100-61130), so the reward actually teaches the spell.")
    lines.append("-- The seven spells are removed from npc_trainer; the trainers get the")
    lines.append("-- questgiver flag and use the core's generic gossip menu 0.  Generated by")
    lines.append("-- tools/generate_placeholder_quests.py;")
    lines.append("-- re-runnable.")
    lines.append("")
    lines.append(f"DELETE FROM `quest_template` WHERE `entry` BETWEEN {QUEST_BASE} "
                 f"AND {QUEST_BASE + len(QUESTS) - 1};")
    lines.append(f"DELETE FROM `creature_questrelation` WHERE `quest` BETWEEN {QUEST_BASE} "
                 f"AND {QUEST_BASE + len(QUESTS) - 1};")
    lines.append(f"DELETE FROM `creature_involvedrelation` WHERE `quest` BETWEEN {QUEST_BASE} "
                 f"AND {QUEST_BASE + len(QUESTS) - 1};")
    lines.append(f"UPDATE `creature_template` SET `npc_flags` = `npc_flags` | {NPC_FLAG_QUESTGIVER} "
                 f"WHERE `entry` IN ({', '.join(str(t) for t in TRAINER_ENTRIES)});")
    lines.append("-- The trainers use the core's generic gossip menu 0 (no custom menu rows).")
    lines.append("UPDATE `creature_template` SET `gossip_menu_id` = 0 "
                 f"WHERE `entry` IN ({', '.join(str(t) for t in TRAINER_ENTRIES)});")
    gated_learn_ids = sorted(learn_by_trigger[q[1]] for q in QUESTS)
    lines.append("DELETE FROM `npc_trainer` WHERE `entry` IN "
                 f"({', '.join(str(t) for t in TRAINER_ENTRIES)}) AND `spell` IN "
                 f"({', '.join(str(s) for s in gated_learn_ids)});")
    lines.append("")

    lines.append("-- Placeholder quests (titles/descriptions are marked PLACEHOLDER)")
    for quest_id, spell_id, spell_name, level, item_id, item_name, text in QUESTS:
        details = ("PLACEHOLDER QUEST - this will be replaced by the real "
                   f"Necromancer class quest chain.\n\n{text}")
        objectives = f"Bring 1 {item_name} to your Necromancer trainer."
        offer = ("The dead are patient, and now they answer you. "
                 "Take this knowledge.")
        request = f"Bring me 1 {item_name} from your Corpse Bag."
        values = [
            quest_id, 2, 0, level, 0, level, 0,
            CLASS_MASK_NECROMANCER, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0,
            sql_text(f"PLACEHOLDER: {spell_name}"),
            sql_text(details),
            sql_text(objectives),
            sql_text(offer),
            sql_text(request),
            sql_text(""),
            item_id, 1,
            spell_id, learn_by_trigger[spell_id],
            0, 0, 0,
            0, 0,
        ]
        lines.append(insert_statement("quest_template", QUEST_COLUMNS, values))
    lines.append("")

    lines.append("-- Quest relations: both trainers start and end every placeholder quest")
    for trainer in TRAINER_ENTRIES:
        for quest_id, _, _, _, _, _, _ in QUESTS:
            lines.append(
                f"INSERT INTO `creature_questrelation` (`id`, `quest`) VALUES ({trainer}, {quest_id});")
    for trainer in TRAINER_ENTRIES:
        for quest_id, _, _, _, _, _, _ in QUESTS:
            lines.append(
                f"INSERT INTO `creature_involvedrelation` (`id`, `quest`) VALUES ({trainer}, {quest_id});")
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    print(f"wrote {args.out}")
    print(f"{len(QUESTS)} placeholder quests, ids {QUEST_BASE}-{QUEST_BASE + len(QUESTS) - 1}")
    print(f"removed {len(gated_learn_ids)} trainer rows: {gated_learn_ids}")
    for quest_id, spell_id, spell_name, level, item_id, item_name, _ in QUESTS:
        print(f"  {quest_id}  L{level:<2}  {spell_name:<15} "
              f"{item_name} ({item_id}) -> learn {learn_by_trigger[spell_id]}")


if __name__ == "__main__":
    main()
