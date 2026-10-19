#!/usr/bin/env python3
# Generate the Necromancer per-minion special abilities (design A.7) SQL + the
# client YAML fragment.
#
# Batch 4 ships the per-tier ability sets for the nine implemented minion
# creatures (Skeletal Archer / Skeletal Mage / Armored Skeleton are not
# implemented as minions and are skipped):
#
#   Zombie     (1501)  Infected Bite, Cannibalize
#   Shade      (7370)  Invisibility, True Sight
#   Ghoul      (846)   Rend, Charge, Cannibalize
#   Skeleton   (6412)  Strike, Sunder Armor
#   Banshee    (10463) Curse, Anti-Magic Shell
#   Wraith     (1800)  Debilitating Touch, Shadow Lash, Enrage
#   Bloodmage  (8526)  Shadow Bolt, Soul Tap, Dispel Magic
#   Abomination(8545)  Taunt, Cleave, Cannibalize, Pestilence (passive)
#   Wight      (11621) Taunt, Cleave, Crowd Pummel, Cannibalize
#
# All 20 abilities are cloned from vanilla donors and cost 0 (the design gives
# no costs; this also resolves finding A71: rage-power minions cannot pay mana).
# Ravage (61027) / Entropic Bolt (61041) are retired from petcreateinfo_spell
# (their mana costs are zeroed for already-tethered pets).
#
# Usage:
#   python tools/generate_batch4_minion_abilities.py \
#       --out data/sql/world/20261018230000_world.sql \
#       --yaml-out ../tmp-batch4-yaml.txt
import argparse
import re
import subprocess
import sys

SQL_FILE = "20261018230000_world.sql"
SCRIPT_CANNIBALIZE = "spell_necromancer_minion_cannibalize"

# per-effect zeroing helper for the fields of one effect slot
def zero_effect(n):
    return {
        "effect%d" % n: 0,
        "effectDieSides%d" % n: 0,
        "effectBaseDice%d" % n: 0,
        "effectBasePoints%d" % n: 0,
        "effectApplyAuraName%d" % n: 0,
        "effectMiscValue%d" % n: 0,
        "effectImplicitTargetA%d" % n: 0,
        "effectAmplitude%d" % n: 0,
    }


COST0 = {"manaCost": 0, "manaCostPercentage": 0}

# warrior/priest/druid-modeled abilities carry stance/form requirements the
# minion cannot satisfy (only_shapeshift); the clones must clear them
NOSTANCE = {"stances": 0, "stancesNot": 0}

ABILITIES = [
    dict(
        new=61051, model=7367, name="Infected Bite",
        desc="Bites the target, inflicting $s1 Nature damage every $t1 sec "
             "and increasing the Physical damage it takes by $s2 for $d.",
        aura_desc="Suffering Nature damage every $t1 sec and taking increased "
                  "Physical damage.",
        overrides={**COST0, "durationIndex": 2, "effectAmplitude1": 3000,
                   "recoveryTime": 4000},
    ),
    dict(
        new=61052, model=20577, name="Cannibalize",
        desc="Cannibalizes a nearby humanoid or undead corpse, restoring 7% "
             "of the minion's health every 2 sec for 10 sec.",
        overrides={**COST0, "script_name": SCRIPT_CANNIBALIZE},
    ),
    dict(
        new=61053, model=7870, name="Invisibility",
        desc="Turns the minion invisible until it attacks.",
        overrides={**COST0, "durationIndex": 21},
    ),
    dict(
        new=61054, model=11649, name="True Sight",
        desc="Reveals nearby invisible enemies to the minion for $d.",
        overrides={**COST0, "durationIndex": 1, "recoveryTime": 10000},
    ),
    dict(
        new=61055, model=6548, name="Rend",
        desc="Wounds the target, causing it to bleed for $o1 damage over $d.",
        overrides={**COST0, **NOSTANCE, "durationIndex": 2, "recoveryTime": 4000},
    ),
    dict(
        new=61056, model=7371, name="Charge",
        desc="Charges an enemy up to 25 yd away, immobilizes it for 1 sec "
             "and increases the minion's attack power for its next attack.",
        overrides={**COST0, "recoveryTime": 30000},
    ),
    dict(
        new=61057, model=12057, name="Strike",
        desc="Strikes at an enemy, inflicting weapon damage plus $s1.",
        overrides={**COST0, "recoveryTime": 4000},
    ),
    dict(
        new=61058, model=7386, name="Sunder Armor",
        desc="Hacks at an enemy's armor, reducing it by $s1 per Sunder "
             "Armor. Can be applied up to 5 times. Lasts $d.",
        overrides={**COST0},
    ),
    dict(
        new=61059, model=1108, name="Curse",
        desc="Curses the target, reducing its chance to hit by 3% for $d.",
        aura_desc="Chance to hit reduced by 3%.",
        overrides={**COST0, "durationIndex": 8,
                   "effectApplyAuraName1": 54, "effectBasePoints1": -4,
                   "effectMiscValue1": 0,
                   **zero_effect(2), **zero_effect(3)},
    ),
    dict(
        new=61060, model=6065, name="Anti-Magic Shell",
        desc="Shields an ally with an anti-magic shell, absorbing $s1 magic "
             "damage for $d.",
        overrides={**COST0, "effectMiscValue1": 126, "durationIndex": 31,
                   "recoveryTime": 30000, "rangeIndex": 4},
    ),
    dict(
        new=61061, model=7641, name="Shadow Bolt",
        desc="Hurls a bolt of dark magic at an enemy, inflicting $s1 Shadow "
             "damage.",
        overrides={**COST0},
    ),
    dict(
        new=61062, model=7651, name="Soul Tap",
        desc="Taps into an enemy's soul, stealing $s1 health and $s2 mana "
             "every $t1 sec for $d, transferring it to the Bloodmage.",
        overrides={**COST0, "durationIndex": 29, "effectAmplitude1": 2000,
                   "rangeIndex": 4, "recoveryTime": 30000,
                   "effect2": 6, "effectApplyAuraName2": 64,
                   "effectBasePoints2": 40, "effectDieSides2": 1,
                   "effectBaseDice2": 1, "effectMiscValue2": 0,
                   "effectImplicitTargetA2": 6, "effectAmplitude2": 2000},
    ),
    dict(
        new=61063, model=527, name="Dispel Magic",
        desc="Dispels magic on the target, removing 1 harmful or beneficial "
             "magic effect.",
        overrides={**COST0, **NOSTANCE, "recoveryTime": 8000},
    ),
    dict(
        new=61064, model=16333, name="Debilitating Touch",
        desc="Reduces an enemy's Stamina by $s1 for $d.",
        aura_desc="Stamina reduced by $s1.",
        overrides={**COST0, "durationIndex": 8, **zero_effect(2)},
    ),
    dict(
        new=61065, model=7814, name="Shadow Lash",
        desc="Lashes the target with shadow, dealing $s1 Shadow damage and "
             "increasing the Shadow damage it takes by 5% for $d.",
        aura_desc="Shadow damage taken increased by 5%.",
        overrides={**COST0, "durationIndex": 8, "recoveryTime": 4000,
                   "effect2": 6, "effectApplyAuraName2": 87,
                   "effectBasePoints2": 4, "effectDieSides2": 1,
                   "effectBaseDice2": 1, "effectMiscValue2": 32,
                   "effectImplicitTargetA2": 6},
    ),
    dict(
        new=61066, model=15061, name="Enrage",
        desc="Increases the minion's attack speed by 15% for $d.",
        aura_desc="Attack speed increased by 15%.",
        overrides={**COST0, "durationIndex": 8, "recoveryTime": 30000,
                   "effectBasePoints2": 14, **zero_effect(1)},
    ),
    dict(
        new=61067, model=355, name="Taunt",
        desc="Taunts the target to attack the minion.",
        overrides={**COST0, **NOSTANCE, "recoveryTime": 10000},
    ),
    dict(
        new=61068, model=11608, name="Cleave",
        desc="A sweeping attack that does the minion's melee damage plus "
             "$s1 to the target and up to 2 nearby enemies.",
        overrides={**COST0, "recoveryTime": 6000},
    ),
    dict(
        new=61069, model=782, name="Pestilence",
        desc="Passive: the minion lashes out at melee attackers, dealing "
             "Nature damage for every hit.",
        aura_desc="Deals Nature damage to melee attackers.",
        overrides={**COST0, **NOSTANCE, "attributes": 65600, "durationIndex": 21,
                   "effectImplicitTargetA1": 1},
    ),
    dict(
        new=61070, model=6552, name="Crowd Pummel",
        desc="Pummels an enemy for $s1 damage, interrupting the spell being "
             "cast for $d.",
        overrides={**COST0, **NOSTANCE, "recoveryTime": 20000, "durationIndex": 7},
    ),
]

# creature entry -> (spell1, spell2, spell3, spell4)
PETS = [
    (846,   [61055, 61056, 61052, 0]),      # Ghoul
    (6412,  [61057, 61058, 0, 0]),          # Skeleton
    (1501,  [61051, 61052, 0, 0]),          # Zombie
    (7370,  [61053, 61054, 0, 0]),          # Shade
    (10463, [61059, 61060, 0, 0]),          # Banshee
    (1800,  [61064, 61065, 61066, 0]),      # Wraith
    (8526,  [61061, 61062, 61063, 0]),      # Bloodmage / Dark Caster
    (8545,  [61067, 61068, 61052, 61069]),  # Abomination
    (11621, [61067, 61068, 61070, 61052]),  # Wight / Spectral Corpse
]

# retired pet actives: zero their mana cost so pre-batch pets can still use them
RETIRED_COST_FIX = [61027, 61041]


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
    "effectMiscValue": "EffectMiscValue",
    "effectImplicitTargetA": "ImplicitTargetA",
    "effectAmplitude": "EffectAmplitude",
    "effectChainTarget": "EffectChainTarget",
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
    "attributes": "Attributes",
    "school": "School",
}


def db_to_dbc(col):
    """spell_template camelCase -> patcher schema field name."""
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


def yaml_block(ability):
    lines = []
    o = ability["overrides"]
    lines.append("  # %d <- %d: %s" % (ability["new"], ability["model"],
                                       ability["name"]))
    lines.append("  - type: copy")
    lines.append("    key: %d" % ability["model"])
    lines.append("    values:")
    lines.append("      ID: %d" % ability["new"])
    for i in range(8):
        lines.append('      Name_lang_%d: "%s"' % (i, ability["name"]))
    for i in range(8):
        lines.append('      NameSubtext_lang_%d: ""' % i)
    if ability.get("desc"):
        for i in range(8):
            lines.append('      Description_lang_%d: "%s"' % (i, ability["desc"]))
    if ability.get("aura_desc"):
        for i in range(8):
            lines.append('      AuraDescription_lang_%d: "%s"'
                         % (i, ability["aura_desc"]))
    for col, value in o.items():
        if col in ("script_name", "description", "auraDescription"):
            continue
        field = db_to_dbc(col)
        if field is None:
            raise RuntimeError("no DBC name for %s" % col)
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
    w("-- Necromancer (class 10) batch 4: per-minion special abilities")
    w("-- (design A.7) - 20 ability spells (61051-61070) + petcreateinfo_spell")
    w("-- rows for the nine minion creatures.  Generated by")
    w("-- tools/generate_batch4_minion_abilities.py; re-runnable.")
    w("")
    w("DELETE FROM `spell_template` WHERE `entry` IN (%s);" %
      ", ".join(str(a["new"]) for a in ABILITIES))
    w("DELETE FROM `petcreateinfo_spell` WHERE `entry` IN (%s);" %
      ", ".join(str(e) for e, _ in PETS))
    w("")

    for ability in ABILITIES:
        values = list(clone_row(args.mariadb, args.port, "spell_template",
                                ability["model"]))
        values[entry_idx] = str(ability["new"])
        values[spell_cols.index("name")] = ability["name"]
        values[spell_cols.index("nameSubtext")] = ""
        # donors may carry script_name bindings (e.g. PW:S, Drain Life); the
        # clones must not inherit them - only the abilities that set their own
        values[spell_cols.index("script_name")] = ""
        if ability.get("desc"):
            values[spell_cols.index("description")] = ability["desc"]
        if ability.get("aura_desc"):
            values[spell_cols.index("auraDescription")] = ability["aura_desc"]
        for column, value in ability["overrides"].items():
            if column in ("description", "auraDescription"):
                continue
            values[spell_cols.index(column)] = str(value)
        literals = [sql_literal(v, spell_types[c]) for v, c in zip(values, spell_cols)]
        w("-- %s (donor %d)" % (ability["name"], ability["model"]))
        w("INSERT INTO `spell_template` (`%s`) VALUES" % "`, `".join(spell_cols))
        w("  (%s);" % ", ".join(literals))
        w("")

    w("-- ============================================================")
    w("-- petcreateinfo_spell (per-tier ability sets; replaces slices 2-3 rows)")
    w("-- ============================================================")
    w("INSERT INTO `petcreateinfo_spell` (`entry`, `spell1`, `spell2`, `spell3`, `spell4`) VALUES")
    w(",\n".join("  (%d, %d, %d, %d, %d)" % (e, s[0], s[1], s[2], s[3])
                 for e, s in PETS) + ";")
    w("")

    w("-- ============================================================")
    w("-- retired pet actives (Ravage / Entropic Bolt): zero the cost so")
    w("-- already-tethered pets are not blocked by no_power (finding A71)")
    w("-- ============================================================")
    for spell_id in RETIRED_COST_FIX:
        w("UPDATE `spell_template` SET `manaCost` = 0, `manaCostPercentage` = 0 "
          "WHERE `entry` = %d;" % spell_id)
    w("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    with open(args.yaml_out, "w", encoding="utf-8", newline="\n") as f:
        f.write("  # ---- batch 4: per-minion special abilities (61051-61070) ----\n")
        f.write("  # Design A.7 per-tier ability sets; donors in the per-spell\n")
        f.write("  # comments.  All cost 0 (design gives no costs; resolves A71).\n")
        f.write("  # Ravage/Entropic Bolt leave petcreateinfo_spell (retired).\n")
        for ability in ABILITIES:
            f.write(yaml_block(ability) + "\n")

    print(f"wrote {args.out}", file=sys.stderr)
    print(f"wrote {args.yaml_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
