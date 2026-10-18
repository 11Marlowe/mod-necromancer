# mod-necromancer

A custom **Necromancer** class (class id 10) for the
[Tortoise WoW](https://github.com/tortoise-wow/tortoise-wow) 1.12.1 server core,
built as a standalone module on the core's **class-support** layer.

> **Status: Phase 2, batch 3 (minions, slice 3c).** Class identity (Phase 1)
> works end-to-end for all 10 races. Batch 1: **Plague Bolt** (ranks 1-3),
> **Reap** (ranks 1-2), **Bone Armor** and a shared **Death Coil** at level
> 14. Batch 2 (disease mechanics): **Call of the Grave** (ranks 1-3, disease
> DoT whose final tick deals triple damage), **Desecration** (ranks 1-3,
> ground plague rain), **Disease Cloud** (area disease burst, cast gate
> requires your disease on the victim) and **Cripple** (10% slow, -20 attack
> power, 10 sec). Batch 3 slice 1 (minions): **Raise Ghoul** / **Raise
> Skeleton** (temporary guardian minions that follow and fight) and
> **Tether** (turns your minion into a permanent, controllable pet). Batch 3
> slice 2 (minion control): raised minions fight with **Ravage** (their pet
> bar active), **Sacrifice Minion** heals you and grants a Death Pact buff,
> **Harvest** consumes a nearby corpse for mana, and **Ghoul Frenzy** breaks
> crowd control, hastes and heals the tethered minion. Batch 3 slice 3
> (higher tiers): **Raise Zombie/Shade** (L10), **Banshee** (L20),
> **Wraith** (L30), **Bloodmage** (L38), **Abomination** (L40, needs three
> corpses) and **Wight** (L58, a *transform* of a Zombie/Ghoul), with
> per-tier pet actives (**Ravage** or **Entropic Bolt**) and per-kind Death
> Pact effects. Batch 3 slice 3c aligns the minion **rules** with the design
> spellbook: the **Corpse Bag** (four real items: Lump of Flesh, Pile of
> Bones, Ectoplasm, Banshee Essence), **Harvest** as a 3-sec channel that
> stores a corpse as an item, per-raise **corpse/bag requirements** (raise
> from a matching nearby corpse or pay the bag cost), corpse-class
> classification (model/gender heuristics + an override table) and the
> design **cast times**. All spells/ranks are taught automatically at
> level-up/login (no trainers yet; the quest/item gates are deferred). Later
> batches add the Corpse Bag container, Army of the Dead/Meat Catapult,
> per-minion abilities, the remaining spellbook entries and talents. See the
> design/handoff document:
> <https://github.com/11Marlowe/wow-tools> (private) or the project's
> `Necromancer-Design.md`.

## Spells

| Spell | Ranks | Learned at | Model used | Notes |
| --- | --- | --- | --- | --- |
| Plague Bolt | 1-3 | 1 / 8 / 16 | Shadow Bolt | batch 1 |
| Reap | 1-2 | 1 / 12 | Raptor Strike | on-next-melee-swing (batch 1) |
| Bone Armor | 1 | 1 | Frost Armor | batch 1 |
| Death Coil | — | 14 | Warlock's Death Coil | shared spell id (batch 1) |
| Call of the Grave | 1-3 | 12 / 24 / 34 | Corruption | disease, final tick x3 (AuraScript) |
| Desecration | 1-3 | 20 / 34 / 46 | Rain of Fire | disease, ground channel |
| Disease Cloud | 1 | 20 | Flamestrike | requires your disease on the target |
| Cripple | 1 | 20 | Cripple (mob 89) | 10% slow + -20 AP, 10 sec |
| Raise Ghoul | 1 | 14 | Summon Atal'ai Skeleton | guardian minion (creature 846), 60 sec |
| Raise Skeleton | 1 | 14 | Summon Atal'ai Skeleton | guardian minion (creature 6412), 60 sec |
| Tether | 1 | 20 | Renew (friendly-target carrier) | converts your minion into a permanent pet |
| Ravage | 1 | pet | Lash of Pain | pet-bar active of the melee minion tiers (61027) |
| Entropic Bolt | 1 | pet | Firebolt | ranged pet-bar active of Banshee/Bloodmage (61041) |
| Sacrifice Minion | 1 | 20 | Renew (friendly-target carrier) | heal (x2 on the tethered pet) + Death Pact buff, despawns the minion |
| Harvest | 1 | 10 | Cannibalize | 3-sec channel: stores a corpse as a Corpse Bag item (aura 61030) |
| Corpse Bag items | - | - | items 63100-63103 | Lump of Flesh / Pile of Bones / Ectoplasm / Banshee Essence (normal bags) |
| Death Pact (Ghoul/Skeleton) | 1 | buff | Cannibalize aura scaffold | +2% physical damage done / -2% physical damage taken, 30 min |
| Death Pact (Banshee/Shade/Wraith/Hulk/Bloodmage) | 1 | buff | same scaffold | 2% mana/4 s / -5% threat / +2% speed / +5% health / +2% spell damage, 30 min |
| Ghoul Frenzy | 1 | 20 | Renew | tethered minion: CC break, +25% melee/casting speed, 50% max-health heal over 30 sec |
| Raise Zombie / Raise Shade | 1 | 10 | Summon Atal'ai Skeleton | guardian (creature 1501 / 7370) |
| Raise Banshee | 1 | 20 | Summon Atal'ai Skeleton | guardian (creature 10463) |
| Raise Wraith | 1 | 30 | Summon Atal'ai Skeleton | guardian (creature 1800) |
| Raise Bloodmage | 1 | 38 | Summon Atal'ai Skeleton | guardian (creature 8526) |
| Raise Abomination | 1 | 40 | Summon Atal'ai Skeleton | guardian (creature 8545); needs three corpses nearby (not consumed) |
| Raise Wight | 1 | 58 | Renew (friendly-target carrier) | transforms a Zombie/Ghoul minion into a Wight (tethered stays tethered) |

For these batches the icons, costs and (except Cripple's) tooltips are the
model spells' (renamed via the client patch). The disease spells' rank-up
mechanics are placeholders until the talent/effect polish batches; "Disease
Cloud", "Cripple" and "Tether" are talents in the source design and are
auto-learned at level 20 until talents exist. Custom tuning/tooltips and the
rest of the design (Sacrifice Minion, Harvest, higher minion tiers, Grim
Reaper, Lichborne, ...) arrive in later batches. Spells are granted by the
module's auto-learn (`src/mod_necromancer.cpp`); trainers are planned but not
required yet.

Server data: `data/sql/world/20261014160000_world.sql` (batch 1),
`20261014170000_world.sql` (batch 2), `20261014180000_world.sql` (batch 3
slice 1), `20261015120000_world.sql` (batch 3 slice 2),
`20261017120000_world.sql` (batch 3 slice 3) and
`20261017180000_world.sql` (batch 3 slice 3c: Corpse Bag items, corpse-class
table, Harvest/Wight cast-time + spell updates), all generated by the scripts
in `tools/`. Client patch: `client/patches/40-spells.yaml` and
`50-skilllines.yaml` (new "Necromancy" skill line 700).

Nine spells are bound to module scripts through `spell_template.script_name`
(SQL): `spell_necromancer_call_of_the_grave` (AuraScript, final-tick triple
damage), `spell_necromancer_disease_cloud` (SpellScript, cast gate),
`spell_necromancer_raise_minion` (re-scales the guardian to the caster's
level and enforces the corpse/bag requirement), `spell_necromancer_tether`
(guardian -> permanent pet conversion),
`spell_necromancer_sacrifice_minion` (heal + per-kind Death Pact + despawn),
`spell_necromancer_harvest` (corpse gate + channel start),
`spell_necromancer_harvest_aura` (the 3-sec channel: stores the corpse item),
`spell_necromancer_ghoul_frenzy` (SpellScript *and* AuraScript; CC break +
script-computed heal) and `spell_necromancer_raise_wight` (Zombie/Ghoul ->
Wight transform).  The names must match the registrations in
`AddNecromancerScripts()`.  The module also registers its class's
`permanentSummonPetTypes` (undead) on the core's `ClassDescriptor` at
startup - without it a tethered minion has no pet-bar abilities (see below).

## Testing tips

- `.character level <n>` is a **GM command**. Either use a GM-rank account or
  run `account set gmlevel <user> 4 -1` in the mangosd console. Beware
  `GM.StartOnGMIsland = 1`: characters *created* on a GM account spawn on GM
  island with a GM starter kit — create test characters on a normal account.
- **Batch-2 test flow:** level a Necromancer to 12 (Call of the Grave is
  auto-learned on level-up/login), cast it on a mob and watch the ticks — the
  **final tick deals triple damage**; the debuff is a *disease* (dispellable
  by cure-disease effects). At 20 you also get Desecration (ground channel),
  Disease Cloud and Cripple. Disease Cloud cast on an enemy shows
  "You can't do that yet" until the enemy carries your Call of the Grave;
  ground-target casts cannot be verified server-side yet (placeholder, see
  the design doc) and are allowed. Cripple should show -10% move speed and
  -20 attack power for 10 sec.
- **Batch-3 minion checks:** at 14 cast Raise Ghoul / Raise Skeleton — a
  temporary (60 sec) guardian appears, follows you and fights nearby enemies;
  casting the same Raise again dismisses it (toggle). At 20 cast Tether on
  your minion (select it, then cast): it becomes your **permanent,
  controllable pet** (pet bar appears; only one at a time; persists across
  logout and taxis like a warlock pet). Minions are vanilla undead models
  (Ghoul 846 / Skeleton 6412) re-scaled to your level by the module
  (placeholder tuning). Known placeholder: a tethered minion is not restored
  by the spirit healer / BG resurrect yet.
- **Reap** is an *on next melee swing* attack (Raptor Strike clone): it needs
  an equipped weapon, otherwise the queued swing blocks other abilities
  ("another action in progress").
- **Batch-3 slice-2 checks:** a tethered minion's **pet bar shows "Ravage"**
  (a pet tethered *before* this update must be re-tethered once) - click it
  while the pet fights.  At 20, **Sacrifice Minion** on your minion heals you
  (doubled on the tethered pet), grants the skull-icon **Death Pact** buff
  (+2% physical damage done for a Ghoul, -2% physical damage taken for a
  Skeleton) and despawns the minion; the buff disappears when you Raise or
  Tether a new minion.  **Harvest** (learned at 10) channels 3 s on a
  corpse within 5 yd and stores it as a Corpse Bag item (see the slice-3c
  checks below); damage/movement interrupts it.
  **Ghoul Frenzy** on the tethered minion hastes it (+25% melee/casting) and
  heals 5% of its max health every 3 s for 30 s; fear/root the pet first to
  see the CC break.  Die with a tethered pet and take the spirit healer's
  resurrection: the minion is re-summoned (new in slice 2).
- **Batch-3 slice-3 checks:** level to 58 (`.character level` is GM-only) to
  see every tier: Raise Zombie/Shade (10), Banshee (20), Wraith (30),
  Bloodmage (38), Abomination (40), Wight (58).  Each raises its guardian;
  different tiers can be summoned at the same time (no limit yet).  Raise
  Abomination fails without three humanoid/undead corpses within 10 yards
  (the corpses are not consumed).  Tether each tier once: melee tiers get
  **Ravage** on the pet bar, Banshee/Bloodmage get the ranged **Entropic
  Bolt** (mana cost).  Sacrifice each tier to see its Death Pact buff
  (mana/4 s, threat, speed, health, spell damage ... - see the table) and
  note it clears on the next Raise/Tether.  Test visuals are placeholders
  (vanilla undead models; no "Wight" creature exists - Spectral Corpse
  stands in).
- **Batch-3 slice-3c checks:** **Harvest** now channels 3 s on a raiseable
  corpse within 5 yd and gives you a **Corpse Bag item** in your normal bags:
  Lump of Flesh (corporeal), Pile of Bones (skeletal), Ectoplasm (spectral),
  Banshee Essence (female humanoids/banshees).  **Raises** consume matching
  bag items when no valid corpse is nearby (Zombie/Ghoul 1x Flesh,
  Skeleton/Bloodmage 1x Bones, Shade/Wraith 1x Ectoplasm, Banshee 1x Essence,
  Abomination 3x Flesh), otherwise they use the corpse (not consumed);
  failing both, the cast is refused.  Design **cast times** are in effect.
  **Raise Wight** is now a transform: target your Zombie/Ghoul minion - it
  becomes a Wight (tethered stays tethered); Abomination and Wight replace
  each other.  If a corpse harvests into the wrong item type, that entry
  needs a row in `necromancer_corpse_class` (see the design doc A.58).
- Startup should log `mask 0x7DF`, `Loaded 1 class descriptor override(s)` and
  the module line. `Wrong class 10` means one of the halves is missing
  (`ChrClasses.dbc` in the server's `dbc\`, or the SQL not applied).
  `Script not found: spell_necromancer_*` means the batch-2 SQL was not
  applied (or applied after the server read `spell_template`).
- `client/patches/60-skillgrants.yaml` extends `SkillRaceClassInfo` so class 10
  gets the shared skills (Cloth, Defence, weapons, languages, ...). Without it
  the class cannot equip cloth/dagger items and they silently land in the
  backpack. Characters created before the fix do not retroactively gain all
  skills — recreate them.

## How this is split

A playable class is always **two halves**:

| Half | Where | What |
| --- | --- | --- |
| **Server** | this module | SQL data (`data/sql/`), behavior scripts (`src/`), stat formulas via the `class_descriptor` table |
| **Client** | MPQ patch (`client/`) | `ChrClasses.dbc`, `CharBaseInfo.dbc`, `CharStartOutfit.dbc`, Glue UI (creation screen) — shipped as a high-priority `patch-Z.mpq` |

The client knows nothing about modules; its half must be installed as a patch.
See `client/README.md`.

## Requirements

- **Core:** the `class-support` branch of
  <https://github.com/11Marlowe/tortoise-wow>, which provides:
  - `ClassRegistry` + the `playable_class` and `class_descriptor` world tables,
  - `PlayerScript::CanCreateCharacter` / `PLAYERHOOK_CAN_CREATE_CHARACTER`,
  - the runtime playable-class mask used by the player-info loaders,
  - the `MAX_SPELL_ID` cast fix (60000 → 65535 in `src/game/Spells/Spell.h`):
    without it the class spells (ids 61010+) play their cast bar but never
    fire and leave the caster stuck,
  - `ClassDescriptor::permanentSummonPetTypes` (consulted by
    `Pet::IsPermanentPetFor`): without it the tethered minion gets no pet-bar
    abilities, no pet tab and no spirit-healer restore (the module sets the
    undead bit for class 10 at startup),
  - the `CreatureDisplayInfoExtra.Gender` field (parsed via
    `Database\DBCStructure.h` + `Database\DBCfmt.h` on the class-support
    branch): without it female-humanoid corpses cannot be detected and
    Banshee Essence harvesting/banshee raises degrade to the override table
    only.
- The module folder must be named **`Necromancer`** inside `modules/` — the core
  derives the loader symbol `AddNecromancerScripts` and the config/SQL paths
  from the folder name.

## Install (server)

1. Clone into the core's modules directory as `Necromancer`:
   ```
   git clone https://github.com/11Marlowe/mod-necromancer.git modules/Necromancer
   ```
2. Reconfigure and rebuild the core (`-DMODULES=static`, as usual).
3. Apply the module SQL by hand (this project runs with
   `Database.AutoUpdate.Enabled = 0`):
   ```
   for %f in (modules\Necromancer\data\sql\world\*.sql) do .\mariadb.exe --port=3307 -u root --force tw_world < %f
   for %f in (modules\Necromancer\data\sql\character\*.sql) do .\mariadb.exe --port=3307 -u root --force tw_char < %f
   ```
4. Copy the patched `ChrClasses.dbc` (from `client\build\` or the release) into
   the server's `dbc\` folder — the server reads the class table from there.
5. Restart `mangosd` (startup should log `[mod-necromancer] module loaded` and
   neither `Wrong class 10` nor `exit(1)` stat errors).

## Install (client)

See `client/README.md`. In short: use the prebuilt `patch-Z.mpq` from this
repo's releases, or regenerate it from your own client DBCs with the bundled
script + patch YAML. Without it the class is not selectable at character
creation.

## Layout

```
src/                module source (loader: AddNecromancerScripts)
data/sql/world/     world-DB migrations (class data, spells, trainers, ...)
data/sql/character/ character-DB migrations
client/             client-side patch assets, scripts and docs
```

## License

TBD. The core is GPL-2.0 and this module is compiled into the server binary;
the practical options are GPL-2.0 (matching the core) or AGPL-3.0 (matching
TortoiseBots). A `LICENSE` file will be added before the first release.
