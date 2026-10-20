#!/usr/bin/env python3
"""Generate the Necromancer icon/tooltip cosmetic pass (server SQL + client YAML).

Every icon is an existing SpellIcon.dbc entry (no new art).  The pass also
replaces the remaining donor tooltips that describe the wrong class (Bone
Armor/Frost Armor, Desecration/Rain of Fire, Disease Cloud/Flamestrike) and
fixes the Tether/Death Pact/Harvest aura text.

Run this LAST after any other spell generator: it is the authoritative final
pass for icons and descriptions.

Outputs:
  data/sql/world/20261020120000_world.sql
  client/patches/44-cosmetic-pass.yaml

Usage:
  python tools/generate_cosmetic_pass.py
"""

import argparse
import json

# Existing SpellIcon.dbc entries (id -> texture name, for reference).
ICON_NAMES = {
    53: "Spell_Nature_Thorns",
    61: "Spell_Shadow_RaiseDead",
    75: "Spell_Shadow_SpectralSight",
    77: "Spell_Shadow_MindRot",
    88: "Spell_Shadow_DeathCoil",
    93: "Spell_Shadow_UnholyStrength",
    95: "Spell_Shadow_UnholyFrenzy",
    96: "Spell_Shadow_Cripple",
    97: "Spell_Shadow_PlagueCloud",
    98: "Spell_Shadow_Possession",
    99: "Spell_Shadow_AntiMagicShell",
    108: "Ability_GhoulFrenzy",
    113: "Spell_Shadow_Haunting",
    116: "Spell_Shadow_CarrionSwarm",
    118: "Spell_Shadow_DeathAndDecay",
    130: "Spell_Shadow_RitualOfSacrifice",
    134: "Spell_Shadow_DeathScream",
    146: "Ability_Racial_Cannibalize",
    147: "Spell_Shadow_VampiricAura",
    160: "Spell_Shadow_CorpseExplode",
    169: "Spell_Shadow_DeathPact",
    182: "Spell_Frost_ChillingArmor",
    201: "Ability_Physical_Taunt",
    207: "Spell_Shadow_AntiShadow",
    210: "Spell_Shadow_DetectInvisibility",
    213: "Spell_Shadow_ShadowBolt",
    221: "Spell_Shadow_AnimateDead",
    222: "Spell_Shadow_NightOfTheDead",
    245: "Ability_Gouge",
    277: "Ability_Warrior_Cleave",
    309: "Spell_Holy_TurnUndead",
    313: "Spell_Shadow_AbominationExplosion",
    331: "Spell_Magic_LesserInvisibilty",
    355: "INV_Misc_Bomb_05",
    498: "Ability_Rogue_Garrote",
    541: "Spell_Shadow_BloodBoil",
    543: "Spell_Shadow_CurseOfMannoroth",
    546: "Spell_Shadow_LifeDrain02",
    547: "Spell_Shadow_RainOfFire",
    548: "Spell_Shadow_SiphonMana",
    565: "Ability_Warrior_Sunder",
    596: "Spell_Shadow_Curse",
    599: "INV_Misc_Bone_09",
    756: "INV_Gauntlets_04",
    856: "Ability_Rogue_Ambush",
    1468: "Spell_Shadow_CreepingPlague",
    1477: "Ability_Warrior_PunishingBlow",
    1488: "Spell_Shadow_PsychicScream",
    1500: "Spell_Shadow_EnslaveDemon",
    1578: "Ability_Hunter_Pet_Boar",
    1591: "Spell_Shadow_DeadofNight",
    1611: "INV_Misc_Bone_HumanSkull_01",
    1614: "Spell_Shadow_CallofBone",
    1764: "Ability_Creature_Disease_01",
    2147: "Spell_Shadow_SoulLeech",
    2214: "Ability_Rogue_ShadowStrikes",
    2216: "Ability_Rogue_EnvelopingShadows",
    2520: "spell_shadow_devouringplague",
}

# id -> existing SpellIcon.dbc entry.  Grouped by spellbook tab.
ICONS = {
    # Reanimation
    61015: 1614,   # Bone Armor - skeletal hand (was Frost Armor)
    61024: 221,    # Raise Ghoul - Animate Dead (was generic Raise Dead)
    61025: 599,    # Raise Skeleton - bones
    61026: 1500,   # Tether - Enslave Demon chains (kept)
    61028: 130,    # Sacrifice Minion - Ritual of Sacrifice
    61029: 146,    # Harvest - Cannibalize (kept)
    61030: 146,    # Harvest channel aura (kept)
    61031: 169,    # Death Pact (Ghoul/Zombie) - Death Pact skull
    61032: 169,    # Death Pact (Skeleton)
    61033: 108,    # Ghoul Frenzy - Ghoul Frenzy
    61034: 61,     # Raise Zombie - Raise Dead
    61035: 113,    # Raise Shade - Haunting
    61036: 134,    # Raise Banshee - Death Scream
    61037: 75,     # Raise Wraith - Spectral Sight
    61038: 541,    # Raise Bloodmage - Blood Boil
    61039: 160,    # Raise Abomination - Corpse Explode
    61040: 1591,   # Raise Wight - Dead of Night
    61042: 169,    # Death Pact variants
    61043: 169,
    61044: 169,
    61045: 169,
    61046: 169,
    61047: 61,     # internal Wight summon (kept)
    61048: 355,    # Meat Catapult - bomb (was Self Destruct)
    61049: 222,    # Army of the Dead R1 - Night of the Dead
    61050: 222,    # Army of the Dead R2
    61074: 88,     # Death Coil (kept)
    61076: 147,    # Bloodlet - Vampiric Aura (was Requiem)
    61077: 201,    # Dark Command - Taunt (was Reincarnation)
    61079: 93,     # Ghoul Armor - Unholy Strength (was Raging Scream)
    61080: 1611,   # Embalm - skull (was Anti-Magic Shell)
    61081: 77,     # Lobotomize - Mind Rot (was Curse of Mannoroth)
    61083: 309,    # Rule Undead - Turn Undead (was Slow)
    61084: 207,    # Unholy Shield - Anti Shadow (was Anti-Magic Shell)
    61085: 182,    # Lich Armor - Chilling Armor (was Mage Armor)
    61086: 1477,   # Dark Punishment - Punishing Blow (was Death Pact)
    # Blood
    61013: 2214,   # Reap - Shadow Strikes (was generic melee)
    61014: 2214,
    61075: 498,    # Plague Strike - Garrote (was Ritual of Sacrifice)
    # Plague
    61010: 2520,   # Plague Bolt - Devouring Plague (was Shadow Bolt)
    61011: 2520,
    61012: 2520,
    61016: 313,    # Call of the Grave (kept)
    61017: 313,
    61018: 313,
    61019: 118,    # Desecration - Death and Decay (was Rain of Fire)
    61020: 118,
    61021: 118,
    61022: 1468,   # Disease Cloud - Creeping Plague (was Self Destruct)
    61023: 96,     # Cripple (kept)
    61071: 97,     # Toxic Plague - Plague Cloud
    61072: 97,
    61073: 97,
    61078: 98,     # Terror - Possession/Fear (kept)
    61082: 116,    # Outbreak - Carrion Swarm (was Siphon Mana)
    # Minion abilities (batch 4)
    61051: 1764,   # Infected Bite - creature disease
    61052: 146,    # Cannibalize (kept)
    61053: 331,    # Invisibility (kept)
    61054: 210,    # True Sight (kept)
    61055: 245,    # Rend (kept)
    61056: 1578,   # Charge (kept)
    61057: 856,    # Strike (kept)
    61058: 565,    # Sunder Armor (kept)
    61059: 543,    # Curse (kept)
    61060: 99,     # Anti-Magic Shell (kept)
    61061: 213,    # Shadow Bolt (kept)
    61062: 2147,   # Soul Tap - Soul Leech (was Life Drain)
    61063: 546,    # Dispel Magic (kept)
    61064: 76,     # Debilitating Touch (kept)
    61065: 2216,   # Shadow Lash - Enveloping Shadows (was Curse)
    61066: 95,     # Enrage (kept)
    61067: 201,    # Taunt - physical taunt (kept)
    61068: 277,    # Cleave (kept)
    61069: 53,     # Pestilence (kept)
    61070: 756,    # Crowd Pummel (kept)
}

# id -> {"description": ..., "aura": ...} (only the listed fields are changed).
TEXTS = {
    61015: dict(
        description="Surrounds you with a shield of bone, increasing Armor by $s1.  Melee attackers may have their movement and attack speed slowed.  Only one Armor spell can be active.  Lasts $d.",
        aura="Increases Armor by $s1 and may slow attackers.",
    ),
    61016: dict(aura="Grave Rot: $s1 Shadow damage every $t1 sec."),
    61017: dict(aura="Grave Rot: $s1 Shadow damage every $t1 sec."),
    61018: dict(aura="Grave Rot: $s1 Shadow damage every $t1 sec."),
    61019: dict(
        description="Desecrates the target area, calling down a plague rain that deals $o1 damage to enemies over $d.  The affliction is a disease.",
        aura="$s1 damage every $t1 sec.",
    ),
    61020: dict(
        description="Desecrates the target area, calling down a plague rain that deals $o1 damage to enemies over $d.  The affliction is a disease.",
        aura="$s1 damage every $t1 sec.",
    ),
    61021: dict(
        description="Desecrates the target area, calling down a plague rain that deals $o1 damage to enemies over $d.  The affliction is a disease.",
        aura="$s1 damage every $t1 sec.",
    ),
    61022: dict(
        description="Explodes a diseased enemy, dealing $s1 damage to enemies in the area and an additional $o2 damage over $d.  Requires one of your diseases on the target.",
        aura="$s2 damage every $t2 sec.",
    ),
    61026: dict(aura="Tethered to a Necromancer."),
    61028: dict(
        description="Sacrifices your minion, healing you and granting a Death Pact effect that varies by minion type.  The healing is doubled when used on your tethered minion.",
    ),
    61029: dict(
        description="Harvests a nearby corpse, storing a corpse item in your Corpse Bag to be used for Raising.  Channeled for $d; moving or taking damage interrupts the harvest.",
    ),
    61071: dict(aura="Toxic Plague: $s1 Nature damage every $t1 sec."),
    61072: dict(aura="Toxic Plague: $s1 Nature damage every $t1 sec."),
    61073: dict(aura="Toxic Plague: $s1 Nature damage every $t1 sec."),
    61079: dict(
        description="Increases armor by $s1 and Shadow resistance by $s2, and heals you for 3% of all damage you deal.  Only one Armor spell can be active.",
        aura="Armor increased by $s1.  Shadow resistance increased by $s2.  Heals you for 3% of all damage you deal.",
    ),
}

# real spell -> trainer learn-spell wrapper (TRAINABLE order).
LEARN = {
    61010: 61100, 61013: 61101, 61015: 61102, 61011: 61103,
    61029: 61104, 61034: 61105, 61035: 61106, 61016: 61107,
    61014: 61108, 61074: 61109, 61024: 61110, 61025: 61111,
    61012: 61112, 61019: 61113, 61022: 61114, 61023: 61115,
    61026: 61116, 61028: 61117, 61033: 61118, 61036: 61119,
    61049: 61120, 61017: 61121, 61037: 61122, 61018: 61123,
    61020: 61124, 61038: 61125, 61039: 61126, 61050: 61127,
    61048: 61128, 61021: 61129, 61040: 61130, 61075: 61131,
    61076: 61132, 61077: 61133, 61078: 61134, 61079: 61135,
    61080: 61136, 61081: 61137, 61082: 61138, 61083: 61139,
    61084: 61140, 61085: 61141, 61086: 61142,
}


def sql_str(value):
    return "'" + value.replace("'", "''") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sql/world/20261020120000_world.sql")
    ap.add_argument("--client-yaml", default="client/patches/44-cosmetic-pass.yaml")
    args = ap.parse_args()

    # --- server SQL ---------------------------------------------------------
    lines = [
        "-- FILE: 20261020120000_world.sql",
        "-- Necromancer icon/tooltip cosmetic pass (2026-10-20).  Existing",
        "-- SpellIcon.dbc icons only (no new art) plus the remaining donor-text",
        "-- fixes (Bone Armor, Desecration, Disease Cloud, Tether, Harvest,",
        "-- Grave Rot, Toxic Plague, Ghoul Armor).  Also updates the trainer",
        "-- learn-spell rows so the trainer list matches the spellbook.",
        "-- Generated by tools/generate_cosmetic_pass.py; run LAST.",
        "",
    ]

    for spell_id in sorted(ICONS):
        lines.append(
            f"UPDATE `spell_template` SET `spellIconId` = {ICONS[spell_id]} "
            f"WHERE `entry` = {spell_id};")

    text_ids = sorted(i for i in ICONS if i in TEXTS)
    for spell_id in text_ids:
        text = TEXTS[spell_id]
        sets = []
        if "description" in text:
            sets.append(f"`description` = {sql_str(text['description'])}")
        if "aura" in text:
            sets.append(f"`auraDescription` = {sql_str(text['aura'])}")
        lines.append(
            f"UPDATE `spell_template` SET {', '.join(sets)} "
            f"WHERE `entry` = {spell_id};")
    lines.append("")

    for real_id, learn_id in sorted(LEARN.items()):
        lines.append(
            f"UPDATE `spell_template` SET `spellIconId` = {ICONS[real_id]} "
            f"WHERE `entry` = {learn_id};")
        if real_id in TEXTS:
            text = TEXTS[real_id]
            sets = []
            if "description" in text:
                sets.append(f"`description` = {sql_str(text['description'])}")
            if "aura" in text:
                sets.append(f"`auraDescription` = {sql_str(text['aura'])}")
            lines.append(
                f"UPDATE `spell_template` SET {', '.join(sets)} "
                f"WHERE `entry` = {learn_id};")
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    # --- client YAML --------------------------------------------------------
    y = [
        "# Necromancer icon/tooltip cosmetic pass (2026-10-20).",
        "# Uses only existing SpellIcon.dbc entries (no new art) and fixes the",
        "# remaining donor tooltips (Bone Armor, Desecration, Disease Cloud,",
        "# Tether, Harvest, Grave Rot, Toxic Plague, Ghoul Armor).",
        "# Generated by tools/generate_cosmetic_pass.py; run LAST.",
        "Spell.dbc:",
    ]

    for spell_id in sorted(ICONS):
        y.append("  - type: update")
        y.append(f"    key: {spell_id}")
        y.append("    values:")
        y.append(f"      SpellIconID: {ICONS[spell_id]}")
    for spell_id in text_ids:
        text = TEXTS[spell_id]
        y.append("  - type: update")
        y.append(f"    key: {spell_id}")
        y.append("    values:")
        if "description" in text:
            for i in range(8):
                y.append(
                    f"      Description_lang_{i}: {json.dumps(text['description'])}")
        if "aura" in text:
            for i in range(8):
                y.append(
                    f"      AuraDescription_lang_{i}: {json.dumps(text['aura'])}")
    for real_id, learn_id in sorted(LEARN.items()):
        y.append("  - type: update")
        y.append(f"    key: {learn_id}")
        y.append("    values:")
        y.append(f"      SpellIconID: {ICONS[real_id]}")
        if real_id in TEXTS:
            text = TEXTS[real_id]
            if "description" in text:
                for i in range(8):
                    y.append(
                        f"      Description_lang_{i}: {json.dumps(text['description'])}")
            if "aura" in text:
                for i in range(8):
                    y.append(
                        f"      AuraDescription_lang_{i}: {json.dumps(text['aura'])}")

    with open(args.client_yaml, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(y) + "\n")

    print(f"wrote {args.out}")
    print(f"wrote {args.client_yaml}")
    print(f"{len(ICONS)} icons, {len(text_ids)} tooltip updates, "
          f"{len(LEARN)} learn-spell mirrors")


if __name__ == "__main__":
    main()
