#!/usr/bin/env python3
"""Generate the T1 Necromancer talent-tree data (grid + icons + rank spells).

T1 scope:
  * 3 TalentTab rows (Reanimation / Blood / Plague), classMask 0x200
  * 54 Talent.dbc rows (parsed layout/prerequisites)
  * 131 new inert passive rank spells for talents without an existing spell
  * existing Necromancer spells reused for the active talents
  * site icons resolved against SpellIcon.dbc, with explicit substitutes for
    slugs that are not in 1.12 (and 4 new SpellIcon rows whose textures exist
    in the client MPQs)
  * server spell_template rows + icon updates
  * trainer rows for the talent-gated spells removed (T1 migration)
  * character cleanup for the 12 non-proficiency trainer shortcuts

Placeholders: the new passive rank spells have no effects yet (they only carry
the talent name/description/icon); T1 wires the grid and point spending.
Existing active spells are used as rank 1, so their behavior is unchanged.

Outputs (all re-runnable):
  client/patches/46-talent-trees.yaml
  data/sql/world/20261021120000_world.sql
  data/sql/character/20261021120000_char.sql
  tools/data/talent-tree-build.json

Usage:
  python tools/generate_talent_trees.py
  python tools/generate_talent_trees.py --apply   # apply the two SQL files
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
MODULE_DIR = TOOLS_DIR.parent
SOURCE_DIR = MODULE_DIR.parent.parent
ROOT_DIR = SOURCE_DIR.parent.parent
DATA_DIR = TOOLS_DIR / "data"
DBC_DIR = ROOT_DIR / "server" / "dbc"

sys.path.insert(0, str(TOOLS_DIR))
from parse_talent_tree import read_spellicons  # noqa: E402

TREES = [
    dict(name="Reanimation", json="reanimation-tree.json", tab_id=401,
         order=0, icon=1750, background="WarlockSummoning"),
    dict(name="Blood", json="blood-tree.json", tab_id=402,
         order=1, icon=541, background="WarlockCurses"),
    dict(name="Plague", json="plague-tree.json", tab_id=403,
         order=2, icon=97, background="WarlockDestruction"),
]

TALENT_ID_BASE = 478
PASSIVE_SPELL_BASE = 61200
SPELLICON_ID_BASE = 2522
NAME_FLAGS = 4128894
RACE_MASK = 1023
CLASS_MASK = 512
PASSIVE_MODEL_SPELL = 61049  # Army of the Dead rank 1: inert passive, family 0

# The site's icon slugs that are not in the 1.12 SpellIcon.dbc.  Item icons
# with a client texture get a new SpellIcon row below; the rest use these
# existing 1.12 icons as T1 substitutes.
NEW_SPELLICONS = [
    ("inv_sword_62", 2522, r"Interface\Icons\INV_Sword_62"),
    ("inv_boots_plate_05", 2523, r"Interface\Icons\INV_Boots_Plate_05"),
    ("inv_chest_plate06", 2524, r"Interface\Icons\INV_Chest_Plate06"),
    ("ability_creature_disease_05", 2525, r"Interface\Icons\Ability_Creature_Disease_05"),
]

ICON_SUBSTITUTES = {
    "Spell_deathknight_frostfever": "spell_frost_frostarmor",          # 119
    "Spell_deathknight_strangulate": "ability_rogue_shadowstrikes",    # 2214
    "Spell_shadow_shadesofdarkness": "spell_shadow_twilight",          # 164
    "spell_shadow_deathsembrace": "spell_shadow_deathcoil",            # 88
    "spell_shadow_nethercloak": "spell_shadow_shadowward",             # 178
    "Spell_deathknight_vendetta": "spell_shadow_unholyfrenzy",         # 95
    "inv12_ability_deathknight_cleavingdeathstrikes": "ability_warrior_cleave",  # 277
    "inv_chest_leather_13": "spell_shadow_shadowward",                 # 178
    "Spell_deathknight_spelldeflection": "ability_parry",              # 558
    "Spell_fire_felflamebolt": "spell_shadow_shadowbolt",              # 213
    "spell_deathknight_necroticplague": "spell_shadow_creepingplague", # 1468
}

# Existing Necromancer spells reused as talent rank spells.  The list length
# must equal the talent's max rank.
EXISTING = {
    "Tether": [61026],
    "Sacrifice Minion": [61028],
    "Ghoul Frenzy": [61033],
    "Army of the Dead": [61049, 61050],
    "Raise Abomination": [61039],
    "Grim Reaper": [61092],
    "Necro Knight": [61090],
    "Will of the Death Knight": [61091],
    "Soul Strike": [61087],
    "Icy Touch": [61088],
    "Lichborne": [61093],
    "Unholy Aura": [61094],
    "Disease Cloud": [61022],
    "Cripple": [61023],
}

# NeedAddInSpellBook=1 (active talents).  Everything else is a passive talent.
# Corrosion (61089) is not in the current parsed Plague tree (creator drift:
# A.2/A.9 still list it, but the A.5 tree and the current page have Wandering Plague at slot 22); it
# stays trainer-taught for T1.
ACTIVE = {
    "Tether", "Sacrifice Minion", "Ghoul Frenzy", "Raise Abomination",
    "Disease Cloud", "Cripple", "Soul Strike", "Icy Touch",
    "Lichborne", "Unholy Aura",
}

# Existing spells whose site icon has no 1.12 texture and no substitute:
# keep the icon they already have.
KEEP_EXISTING_ICON = {"Army of the Dead", "Grim Reaper", "Raise Abomination"}

# Trainer-taught talent shortcuts removed from npc_trainer in T1.
# Corrosion (61089) is excluded: it is not in the current parsed Plague tree.
TALENT_GATED = {
    61026, 61028, 61033, 61049, 61050, 61039, 61087, 61088,
    61093, 61094, 61022, 61023,
    61090, 61091, 61092,
}

# Character cleanup: remove the non-proficiency trainer shortcuts; the three
# armor passives stay on existing characters until the mechanics pass.
CHAR_CLEANUP_SPELLS = {
    61026, 61028, 61033, 61049, 61050, 61039, 61087, 61088,
    61093, 61094, 61022, 61023,
}


def read_wdbc_ids(path: Path) -> set[int]:
    buf = path.read_bytes()
    magic, record_count, field_count, record_size, _ = struct.unpack_from(
        "<4sIIII", buf, 0
    )
    if magic != b"WDBC":
        raise SystemExit(f"not a WDBC file: {path}")
    return {
        struct.unpack_from("<I", buf, 20 + i * record_size)[0]
        for i in range(record_count)
    }


def query(mariadb: str, port: str, sql: str) -> list[list[str]]:
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

        def unesc(s: str) -> str:
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


def sql_literal(value, dtype: str) -> str:
    if value is None:
        return "NULL"
    t = dtype.lower()
    if any(x in t for x in ("char", "text", "enum", "set")):
        return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"
    return str(value)


def yaml_scalar(value) -> str:
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def resolve_icon(slug: str | None, icon_lookup) -> int | None:
    if not slug:
        return None
    for new_slug, icon_id, _ in NEW_SPELLICONS:
        if slug == new_slug:
            return icon_id
    matches = icon_lookup.get(slug.lower())
    if matches:
        return matches[0][0]
    sub = ICON_SUBSTITUTES.get(slug)
    if sub:
        matches = icon_lookup.get(sub.lower())
        if matches:
            return matches[0][0]
    return None


def load_build() -> dict:
    icon_lookup = read_spellicons(str(DBC_DIR / "SpellIcon.dbc"))
    for slug, icon_id, texture in NEW_SPELLICONS:
        icon_lookup.setdefault(slug.lower(), []).append((icon_id, texture))

    talent_store = read_wdbc_ids(DBC_DIR / "Talent.dbc")
    tab_store = read_wdbc_ids(DBC_DIR / "TalentTab.dbc")
    icon_store = read_wdbc_ids(DBC_DIR / "SpellIcon.dbc")

    next_spell = PASSIVE_SPELL_BASE
    next_talent = TALENT_ID_BASE
    used_spells: set[int] = set()
    build = {
        "tabs": [],
        "talents": [],
        "new_spells": [],
        "icon_updates": [],
        "new_icons": [
            {"id": i, "slug": s, "texture": t} for s, i, t in NEW_SPELLICONS
        ],
        "spell_model": PASSIVE_MODEL_SPELL,
    }

    for tree in TREES:
        doc = json.loads((DATA_DIR / tree["json"]).read_text(encoding="utf-8"))
        talents = sorted(doc["talents"], key=lambda t: t["slot"])
        slot_to_talent: dict[int, dict] = {}

        for t in talents:
            t["_talent_id"] = next_talent
            next_talent += 1
            slot_to_talent[t["slot"]] = t

        tab = {
            "id": tree["tab_id"],
            "name": doc["tree"]["name"],
            "nameFlags": NAME_FLAGS,
            "spellIcon": tree["icon"],
            "raceMask": RACE_MASK,
            "classMask": CLASS_MASK,
            "orderIndex": tree["order"],
            "backgroundFile": tree["background"],
        }
        if tab["id"] in tab_store:
            raise SystemExit(f"TalentTab id {tab['id']} already exists")
        build["tabs"].append(tab)

        for t in talents:
            name = t["name"]
            max_rank = t["maxRank"]
            existing = EXISTING.get(name)
            if existing:
                if len(existing) != max_rank:
                    raise SystemExit(
                        f"{name}: {len(existing)} existing spells for maxRank {max_rank}"
                    )
                spells = list(existing)
            else:
                spells = list(range(next_spell, next_spell + max_rank))
                next_spell += max_rank
            for spell_id in spells:
                if spell_id in used_spells:
                    raise SystemExit(f"duplicate rank spell {spell_id} ({name})")
                used_spells.add(spell_id)

            icon = resolve_icon(t.get("icon"), icon_lookup)
            if icon is None and not (existing and name in KEEP_EXISTING_ICON):
                raise SystemExit(f"no icon for talent {name} ({t.get('icon')})")
            if not existing and icon is None:
                raise SystemExit(f"passive talent {name} has no icon")

            req_slot = t.get("requires")
            if req_slot is not None:
                if req_slot not in slot_to_talent:
                    raise SystemExit(f"{name}: prerequisite slot {req_slot} missing")
                dep = slot_to_talent[req_slot]
                prereq_talent = dep["_talent_id"]
                prereq_rank = dep["maxRank"] - 1
            else:
                prereq_talent = 0
                prereq_rank = 0

            row = {
                "id": t["_talent_id"],
                "talentTab": tree["tab_id"],
                "tierID": t["position"]["row"] - 1,
                "columnIndex": t["position"]["column"] - 1,
                "ranks": spells,
                "prereqTalent": prereq_talent,
                "prereqRank": prereq_rank,
                "flags": 1 if name in ACTIVE else 0,
                "requiredSpellID": 0,
                "name": name,
                "slot": t["slot"],
                "tree": tree["name"],
                "maxRank": max_rank,
                "icon": t.get("icon"),
                "iconId": icon,
                "existing": bool(existing),
            }
            build["talents"].append(row)

            if existing:
                if icon is not None and name not in KEEP_EXISTING_ICON:
                    for spell_id in spells:
                        build["icon_updates"].append(
                            {"spell": spell_id, "icon": icon, "talent": name}
                        )
            else:
                rank_label = lambda r: "" if max_rank == 1 else f"Rank {r}"
                for rank, spell_id in enumerate(spells, start=1):
                    build["new_spells"].append({
                        "id": spell_id,
                        "talent": name,
                        "rank": rank,
                        "maxRank": max_rank,
                        "rankLabel": rank_label(rank),
                        "description": t.get("description") or "",
                        "icon": icon,
                        "tree": tree["name"],
                        "slot": t["slot"],
                    })

    if next_spell - PASSIVE_SPELL_BASE != len(build["new_spells"]):
        raise SystemExit("new-spell count mismatch")
    if len(build["talents"]) != 54:
        raise SystemExit(f"expected 54 talents, got {len(build['talents'])}")
    if sum(t["maxRank"] for t in build["talents"]) != 146:
        raise SystemExit("expected 146 talent ranks")
    if any(t["id"] in talent_store for t in build["talents"]):
        raise SystemExit("Talent id collision")
    if len(used_spells) != sum(t["maxRank"] for t in build["talents"]):
        raise SystemExit("rank spell count mismatch")
    for icon in build["new_icons"]:
        if icon["id"] in icon_store:
            raise SystemExit(f"SpellIcon id {icon['id']} already exists")
    return build


def emit_client_yaml(path: Path, build: dict) -> None:
    lines: list[str] = []
    w = lines.append
    w("# Talent trees T1 - generated by tools/generate_talent_trees.py.")
    w("# 3 TalentTab rows, 54 Talent rows, 4 SpellIcon rows, icon updates and")
    w("# inert passive rank spells.  Loads after 45-armor-progression.yaml.")
    w("")
    w("TalentTab.dbc:")
    for tab in build["tabs"]:
        w("  - type: insert")
        w("    values:")
        for key in ("id", "name_lang_0", "nameFlags", "spellIcon",
                    "raceMask", "classMask", "orderIndex", "backgroundFile"):
            value = tab["name"] if key == "name_lang_0" else tab[key]
            w(f"      {key}: {yaml_scalar(value)}")
    w("")
    w("Talent.dbc:")
    for t in build["talents"]:
        w("  - type: insert")
        w("    values:")
        w(f"      id: {t['id']}")
        w(f"      talentTab: {t['talentTab']}")
        w(f"      tierID: {t['tierID']}")
        w(f"      columnIndex: {t['columnIndex']}")
        for i in range(5):
            w(f"      rank{i + 1}: {t['ranks'][i] if i < len(t['ranks']) else 0}")
        w(f"      prereqTalent: {t['prereqTalent']}")
        w(f"      prereqRank: {t['prereqRank']}")
        w(f"      flags: {t['flags']}")
        w(f"      requiredSpellID: {t['requiredSpellID']}")
    w("")
    w("SpellIcon.dbc:")
    for icon in build["new_icons"]:
        w("  - type: insert")
        w(f"    key: {icon['id']}")
        w("    values:")
        w(f"      ID: {icon['id']}")
        w(f"      TextureFilename: {yaml_scalar(icon['texture'])}")
    w("")
    w("Spell.dbc:")
    for upd in build["icon_updates"]:
        w("  - type: update")
        w(f"    key: {upd['spell']}")
        w("    values:")
        w(f"      SpellIconID: {upd['icon']}")
    for spell in build["new_spells"]:
        w("  - type: copy")
        w(f"    key: {build['spell_model']}")
        w("    values:")
        w(f"      ID: {spell['id']}")
        for i in range(8):
            w(f"      Name_lang_{i}: {yaml_scalar(spell['talent'])}")
        for i in range(8):
            w(f"      NameSubtext_lang_{i}: {yaml_scalar(spell['rankLabel'])}")
        w(f"      Description_lang_0: {yaml_scalar(spell['description'])}")
        w("      AuraDescription_lang_0: \"\"")
        w(f"      SpellIconID: {spell['icon']}")
        w("      School: 0")
        w("      Category: 0")
        w("      DispelType: 0")
        w("      Mechanic: 0")
        w("      Attributes: 80")
        w("      AttributesEx: 0")
        w("      AttributesEx2: 0")
        w("      AttributesEx3: 0")
        w("      AttributesEx4: 0")
        w("      ShapeshiftMask: 0")
        w("      ShapeshiftExclude: 0")
        w("      Targets: 0")
        w("      TargetCreatureType: 0")
        w("      RequiresSpellFocus: 0")
        w("      CasterAuraState: 0")
        w("      TargetAuraState: 0")
        w("      CastingTimeIndex: 1")
        w("      RecoveryTime: 0")
        w("      CategoryRecoveryTime: 0")
        w("      InterruptFlags: 0")
        w("      AuraInterruptFlags: 0")
        w("      ChannelInterruptFlags: 0")
        w("      ProcTypeMask: 0")
        w("      ProcChance: 0")
        w("      ProcCharges: 0")
        w("      MaxLevel: 0")
        w("      BaseLevel: 0")
        w("      SpellLevel: 0")
        w("      DurationIndex: 21")
        w("      PowerType: 0")
        w("      ManaCost: 0")
        w("      ManaCostPerLevel: 0")
        w("      ManaCostPerSecond: 0")
        w("      ManaCostPerSecondPerLevel: 0")
        w("      RangeIndex: 0")
        w("      Speed: 0")
        w("      ModalNextSpell: 0")
        w("      StackAmount: 0")
        w("      Totem_1: 0")
        w("      Totem_2: 0")
        for i in range(1, 9):
            w(f"      Reagent_{i}: 0")
            w(f"      ReagentCount_{i}: 0")
        w("      EquippedItemClass: 0")
        w("      EquippedItemSubclass: 0")
        w("      EquippedItemInvType: 0")
        for i in range(1, 4):
            w(f"      Effect_{i}: 0")
            w(f"      EffectDieSides_{i}: 0")
            w(f"      EffectBaseDice_{i}: 0")
            w(f"      EffectDicePerLevel_{i}: 0")
            w(f"      EffectRealPointsPerLevel_{i}: 0")
            w(f"      EffectBasePoints_{i}: 0")
            w(f"      EffectMechanic_{i}: 0")
            w(f"      ImplicitTargetA_{i}: 0")
            w(f"      ImplicitTargetB_{i}: 0")
            w(f"      EffectRadiusIndex_{i}: 0")
            w(f"      EffectAura_{i}: 0")
            w(f"      EffectAmplitude_{i}: 0")
            w(f"      EffectMultipleValue_{i}: 0")
            w(f"      EffectChainTarget_{i}: 0")
            w(f"      EffectItemType_{i}: 0")
            w(f"      EffectMiscValue_{i}: 0")
            w(f"      EffectTriggerSpell_{i}: 0")
            w(f"      EffectPointsPerCombo_{i}: 0")
        w("      SpellVisualID_1: 0")
        w("      SpellVisualID_2: 0")
        w("      PreventionType: 0")
        w("      StanceBarOrder: 0")
        w("      ActiveIconID: 0")
        w("      SpellPriority: 0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def emit_world_sql(path: Path, build: dict, mariadb: str, port: str) -> None:
    cols_types = {
        r[0]: r[1] for r in
        query(mariadb, port, "SHOW COLUMNS FROM `spell_template`")
    }
    donor = query(
        mariadb, port,
        f"SELECT * FROM `spell_template` WHERE `entry` = {build['spell_model']}"
    )
    if len(donor) != 1:
        raise SystemExit(f"model spell {build['spell_model']} not found")
    col_names = list(cols_types)
    donor_values = donor[0]
    if len(donor_values) != len(col_names):
        raise SystemExit("spell_template column/value width mismatch")
    donor_row = dict(zip(col_names, donor_values))

    new_ids = [s["id"] for s in build["new_spells"]]
    lines: list[str] = []
    w = lines.append
    w("-- FILE: 20261021120000_world.sql")
    w("-- Necromancer talent trees T1: new inert passive rank spells, icon")
    w("-- updates, and trainer cleanup.  Generated by")
    w("-- tools/generate_talent_trees.py; re-runnable.")
    w("")
    w(f"DELETE FROM `spell_template` WHERE `entry` BETWEEN {PASSIVE_SPELL_BASE} "
      f"AND {PASSIVE_SPELL_BASE + len(new_ids) - 1};")
    w("")

    for spell in build["new_spells"]:
        row = dict(donor_row)
        row.update({
            "entry": spell["id"],
            "name": spell["talent"],
            "nameSubtext": spell["rankLabel"],
            "description": spell["description"],
            "auraDescription": "",
            "spellIconId": spell["icon"],
            "school": 0, "category": 0, "castUI": 0, "dispel": 0, "mechanic": 0,
            "attributes": 80, "attributesEx": 0, "attributesEx2": 0,
            "attributesEx3": 0, "attributesEx4": 0,
            "stances": 0, "stancesNot": 0, "targets": 0, "targetCreatureType": 0,
            "requiresSpellFocus": 0, "casterAuraState": 0, "targetAuraState": 0,
            "castingTimeIndex": 1, "recoveryTime": 0, "categoryRecoveryTime": 0,
            "interruptFlags": 0, "auraInterruptFlags": 0,
            "channelInterruptFlags": 0, "procFlags": 0, "procChance": 0,
            "procCharges": 0, "maxLevel": 0, "baseLevel": 0, "spellLevel": 0,
            "durationIndex": 21, "powerType": 0, "manaCost": 0,
            "manCostPerLevel": 0, "manaPerSecond": 0,
            "manaPerSecondPerLevel": 0, "rangeIndex": 0, "speed": 0,
            "modelNextSpell": 0, "stackAmount": 0, "totem1": 0, "totem2": 0,
            "equippedItemClass": 0, "equippedItemSubClassMask": 0,
            "equippedItemInventoryTypeMask": 0,
            "spellFamilyName": 0, "spellFamilyFlags": 0,
            "spellVisual1": 0, "spellVisual2": 0,
            "activeIconId": 0, "spellPriority": 0,
            "dmgClass": 0, "preventionType": 0, "stanceBarOrder": 0,
            "dmgMultiplier1": 0, "dmgMultiplier2": 0, "dmgMultiplier3": 0,
            "manaCostPercentage": 0, "startRecoveryCategory": 0,
            "startRecoveryTime": 0, "minTargetLevel": 0, "maxTargetLevel": 0,
            "maxAffectedTargets": 0, "minFactionId": 0, "minReputation": 0,
            "requiredAuraVision": 0, "customFlags": 0, "script_name": "",
        })
        for i in range(1, 9):
            row[f"reagent{i}"] = 0
            row[f"reagentCount{i}"] = 0
        for i in range(1, 4):
            row[f"effect{i}"] = 0
            row[f"effectDieSides{i}"] = 0
            row[f"effectBaseDice{i}"] = 0
            row[f"effectDicePerLevel{i}"] = 0
            row[f"effectRealPointsPerLevel{i}"] = 0
            row[f"effectBasePoints{i}"] = 0
            row[f"effectBonusCoefficient{i}"] = 0
            row[f"effectMechanic{i}"] = 0
            row[f"effectImplicitTargetA{i}"] = 0
            row[f"effectImplicitTargetB{i}"] = 0
            row[f"effectRadiusIndex{i}"] = 0
            row[f"effectApplyAuraName{i}"] = 0
            row[f"effectAmplitude{i}"] = 0
            row[f"effectMultipleValue{i}"] = 0
            row[f"effectChainTarget{i}"] = 0
            row[f"effectItemType{i}"] = 0
            row[f"effectMiscValue{i}"] = 0
            row[f"effectTriggerSpell{i}"] = 0
            row[f"effectPointsPerComboPoint{i}"] = 0
        values = [sql_literal(row[c], cols_types[c]) for c in col_names]
        w(f"INSERT INTO `spell_template` (`{'`, `'.join(col_names)}`) VALUES")
        w("  (" + ", ".join(values) + ");")
        w("")

    if build["icon_updates"]:
        w("-- existing talent spells: site/substitute icons")
        for upd in build["icon_updates"]:
            w(f"UPDATE `spell_template` SET `spellIconId` = {upd['icon']} "
              f"WHERE `entry` = {upd['spell']};")
        w("")

    from generate_trainers import LEARN_SPELL_BASE, TALENT_GATED as TG, TRAINABLE
    learn_ids = [
        LEARN_SPELL_BASE + i for i, (spell_id, _, _) in enumerate(TRAINABLE)
        if spell_id in TG
    ]
    w("-- talent-gated spells are no longer trainer-taught")
    w(f"DELETE FROM `npc_trainer` WHERE `spell` IN ({', '.join(map(str, learn_ids))});")
    w("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def emit_char_sql(path: Path) -> None:
    ids = ", ".join(map(str, sorted(CHAR_CLEANUP_SPELLS)))
    lines = [
        "-- FILE: 20261021120000_char.sql",
        "-- Necromancer talent trees T1: strip the 12 non-proficiency",
        "-- trainer-learned talent shortcuts from existing class-10 characters.",
        "-- Grim Reaper/Necro Knight/Will of the Death Knight stay on existing",
        "-- characters (they carry proficiency skills/gear); new characters get",
        "-- them from the Blood tree.  Generated by",
        "-- tools/generate_talent_trees.py; re-runnable.",
        "",
        f"DELETE cs FROM `character_spell` cs",
        f"JOIN `characters` c ON c.guid = cs.guid",
        f"WHERE c.class = 10 AND cs.spell IN ({ids});",
        "",
        f"DELETE cs FROM `character_spell_dual_spec` cs",
        f"JOIN `characters` c ON c.guid = cs.guid",
        f"WHERE c.class = 10 AND cs.spell IN ({ids});",
        "",
        f"DELETE ca FROM `character_action` ca",
        f"JOIN `characters` c ON c.guid = ca.guid",
        f"WHERE c.class = 10 AND ca.type = 0 AND ca.action IN ({ids});",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mariadb",
                    default=str(ROOT_DIR / "server/mariadb-portable/bin/mariadb.exe"))
    ap.add_argument("--port", default="3307")
    ap.add_argument("--apply", action="store_true",
                    help="apply the generated world/character SQL")
    args = ap.parse_args()

    build = load_build()
    out_yaml = MODULE_DIR / "client/patches/46-talent-trees.yaml"
    out_world = MODULE_DIR / "data/sql/world/20261021120000_world.sql"
    out_char = MODULE_DIR / "data/sql/character/20261021120000_char.sql"
    out_json = DATA_DIR / "talent-tree-build.json"

    emit_client_yaml(out_yaml, build)
    emit_world_sql(out_world, build, args.mariadb, args.port)
    emit_char_sql(out_char)
    out_json.write_text(json.dumps(build, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"tabs: {len(build['tabs'])} | talents: {len(build['talents'])} | "
          f"new passive ranks: {len(build['new_spells'])} | "
          f"icon updates: {len(build['icon_updates'])} | "
          f"new SpellIcons: {len(build['new_icons'])}", file=sys.stderr)
    print(f"wrote {out_yaml}", file=sys.stderr)
    print(f"wrote {out_world}", file=sys.stderr)
    print(f"wrote {out_char}", file=sys.stderr)
    print(f"wrote {out_json}", file=sys.stderr)

    if args.apply:
        for db, path_ in (("tw_world", out_world), ("tw_char", out_char)):
            with open(path_, "r", encoding="utf-8") as f:
                subprocess.run(
                    [args.mariadb, f"--port={args.port}", "-u", "root", db],
                    stdin=f, check=True,
                )
            print(f"applied {path_.name} -> {db}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())



