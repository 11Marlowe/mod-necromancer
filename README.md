# mod-necromancer

A custom **Necromancer** class (class id 10) for the
[Tortoise WoW](https://github.com/tortoise-wow/tortoise-wow) 1.12.1 server core,
built as a standalone module on the core's **class-support** layer.

**Status:** Phase 2 is content-complete through the remaining talent spells and
the **T1 talent-tree scaffolding** (2026-10-21). Identity, spells, minions,
trainers, placeholder quests, the three-tab spellbook, icons/tooltips, the
Blood-tree armor passives, the last talent-gated spells (Soul Strike, Icy
Touch/Frost Fever, Corrosion, Lichborne, Unholy Aura) and the three talent
trees (54 talents, icons, rank spells) are implemented, deployed and
server-side verified with `turtle-agent`. Class color (red) and a placeholder
creation-screen icon are now in the client patch. **T1 note:** the new passive
talent rank spells are inert placeholders; the talent effects are the T2
mechanics work. Remaining: T2 mechanics, custom creation-screen art; the
Corpse Bag container is deferred.

The canonical design, progress log, engine lessons and placeholder list live in
the project's `Necromancer-Design.md` (mirrored in the private
`11Marlowe/wow-tools` repo). Read its **§12** (current state), **§13** (engine
lessons) and **§14** (assumptions A1-A93) before changing spells or mechanics.

## Features

- Class 10, mana-based, playable by all 10 existing races.
- Three spellbook tabs: **Reanimation (700)**, **Blood (701)**, **Plague (702)**.
- **Talent trees T1:** Reanimation / Blood / Plague tabs (TalentTab 401-403),
  54 talents (Talent 478-531) with the site icons and prerequisites. The new
  passive rank spells (61200-61330) are placeholders with no effects yet; the
  T2 mechanics pass implements them.
- Class spells and minion abilities use ids **61010-61095**; trainer learn-spell
  wrappers use **61100-61150**; talent rank spells use **61200-61330**.
- Minion system: nine undead tiers, corpse/Corpse Bag requirements, Tether,
  per-tier abilities, Death Pact, Army of the Dead cap, Meat Catapult and the
  Wight transform.
- Trainers replace auto-learn; the eight quest-gated spells come from
  placeholder class quests.
- Client half ships as `patch-Z.mpq` (DBCs incl. `Talent`/`TalentTab`/
  `SpellIcon`, creation-screen Glue UI, red class color and a placeholder
  class icon).

## Spellbook

- **Reanimation:** Bone Armor, Death Coil, Ghoul Armor, Tether, Sacrifice
  Minion, Ghoul Frenzy, Embalm, Lobotomize, Rule Undead, Unholy Shield, Lich
  Armor, Meat Catapult, Army of the Dead (passive), Harvest and the Raise
  spells (Zombie, Shade, Ghoul, Skeleton, Banshee, Wraith, Bloodmage,
  Abomination, Wight).
- **Blood:** Reap, Bloodlet, Plague Strike, Dark Command, Dark Punishment,
  Grim Reaper, Necro Knight, Will of the Death Knight, Soul Strike, Unholy
  Aura.
- **Plague:** Plague Bolt (+ Toxic Plague), Call of the Grave, Terror,
  Desecration, Disease Cloud, Cripple, Outbreak, Icy Touch (+ Frost Fever),
  Corrosion, Lichborne.

Notable mechanics:

- Plague Bolt applies **Toxic Plague** and gains **+3% direct damage per
  disease** on the target; Plague Strike shares the rider.
- Reap is an instant shadow life-steal (10 yd, 8 s cooldown); Death Coil
  (61074) damages enemies or heals your undead minion.
- Raises use a matching nearby corpse or consume Corpse Bag items; Harvest
  channels 3 s to store a corpse item.
- Minion abilities are granted per tier through `petcreateinfo_spell` and cost
  0; toggle autocast on the pet bar.
- Bone, Ghoul and Lich Armor are mutually exclusive. The armor/weapon passives
  grant the matching skills and auto-unequip gear when the passive is lost.
- Icy Touch applies Frost Fever (a disease with Frost damage and melee/casting
  slows); Soul Strike heals 3% of max health per disease on the target (up to
  three); Lichborne and Unholy Aura are permanent self/party buffs.

Costs, damage values and some mechanics remain placeholders where the design
gives no numbers (e.g. Desecration is still a Rain of Fire channel, Bone Armor
is still Frost Armor, Dark Punishment buffs all damage, Lichborne does not yet
accelerate disease ticks). See the design doc §14 A78/A86/A88/A90/A92 for the
current list.

## Trainers

The class is trained, not auto-learned. Both NPCs use `trainer_class = 10` and
teach **28 non-quest spell/rank rows** through learn spells 61100-61150 at
vanilla class-trainer prices.  Fifteen spells are now talent-granted (see
**Talents**); **Corrosion (61089)** stays trainer-taught because it is not in
the current parsed Plague tree (creator drift).

### Talents (T1 scaffolding, 2026-10-21)

`patch-Z.mpq` adds the three talent tabs **Reanimation**, **Blood** and
**Plague** (`TalentTab` 401-403, classMask 0x200), 54 talents
(`Talent` 478-531) with the parsed tier/column and prerequisites, and the
site icons (rank-spell `SpellIconID`; 4 new `SpellIcon` rows, substitutes for
the rest).  The 131 new passive rank spells (61200-61330) are **inert** for
T1; active talents reuse the existing class spells.  The T2 mechanics pass
implements the real effects in five batches (T2a stat/defense, T2b spell
modifiers, T2c minion/pet, T2d proc/conditional, T2e active polish; see
design doc §10 item 17 / A94).  See §11/§12/A93 and
`client/patches/46-talent-trees.yaml`.

| City | NPC | Where | Entry |
| --- | --- | --- | --- |
| Orgrimmar | Gorvoth the Gravewarden | Cleft of Shadow, by the warlock trainers | 950010 |
| Stormwind | Mordecai Gravewhisper | Slaughtered Lamb cellar, by the warlock trainers | 950011 |

### Placeholder class quests

Both trainers are questgivers (`npc_flags` 19) and offer these level-gated,
class-10-only turn-ins. The reward teaches the real spell; the seven A85 spells
are not in `npc_trainer`.

| Level | Quest | Spell | Turn-in |
| --- | --- | --- | --- |
| 10 | 950100 | Raise Zombie | 1x Lump of Flesh (63100) |
| 10 | 950101 | Raise Shade | 1x Ectoplasm (63102) |
| 10 | 950102 | Harvest | 1x Linen Cloth (2589) |
| 14 | 950103 | Raise Ghoul | 1x Lump of Flesh (63100) |
| 14 | 950104 | Raise Skeleton | 1x Pile of Bones (63101) |
| 20 | 950105 | Raise Banshee | 1x Banshee Essence (63103) |
| 30 | 950106 | Raise Wraith | 1x Ectoplasm (63102) |
| 10 | 950107 | Plague Strike | 1x Lump of Flesh (63100) |

Harvest deliberately uses Linen Cloth so a fresh character can bootstrap the
Harvest -> corpse item -> raise chain. Titles and text are marked PLACEHOLDER.

## How this is split

A playable class is always **two halves**:

| Half | Where | What |
| --- | --- | --- |
| **Server** | this module | SQL data (`data/sql/`), behavior scripts (`src/`), stat formulas via `class_descriptor` |
| **Client** | MPQ patch (`client/`) | `ChrClasses`/`CharBaseInfo`/`CharStartOutfit`, Glue UI, skill/spell/talent DBCs (`SkillLine*`, `Spell`, `SpellIcon`, `Talent`, `TalentTab`) — shipped as `patch-Z.mpq` |

The client knows nothing about modules; its half must be installed as a patch.

## Requirements

- **Core:** the `class-support` branch of
  <https://github.com/11Marlowe/tortoise-wow>. It provides the runtime
  playable-class mask (`ClassRegistry`, `playable_class`,
  `class_descriptor`), `PlayerScript::CanCreateCharacter`, the `MAX_SPELL_ID`
  cast fix (60000 -> 65535), `ClassDescriptor::permanentSummonPetTypes` (pet
  bar and spirit-healer restore) and the parsed
  `CreatureDisplayInfoExtra.Gender` field (corpse classification).
- The module folder must be named **`Necromancer`** under `modules/` — the core
  derives `AddNecromancerScripts` and the module config/SQL paths from it.

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
   the server's `dbc\` folder.
5. Restart `mangosd`. Startup should log `mask 0x7DF`,
   `Loaded 1 class descriptor override(s)` and `[mod-necromancer] module loaded`.
   `Wrong class 10` means a DBC/SQL half is missing.

## Install (client)

See `client/README.md`. Use the prebuilt `patch-Z.mpq` from releases, or
regenerate it from your own client DBCs with the bundled script + YAML patches.
Without it the class is not selectable at character creation.

## Testing

**Standard since 2026-10-18:** verify server behavior with the headless
`turtle-agent` client first (`TurtleAgent-Workflow.md`); ask for an in-client
pass only for rendered items (icons, tooltips, models, tabs, Glue UI).

- Turn GM mode off before combat/debuff tests (`.gm off`); a GM attacker makes
  creatures evade and wipes debuffs.
- Level with `.levelup <n>` (GM-only; there is no `.character level`).
- Trainer lists send **learn-spell ids** (61100+); the real spell appears in
  `spells` after training.  The T1 trainer list has **28 rows**; the 15
  talent-gated learn ids are gone and 61148 (Corrosion) remains.
- A pet saved before a pet-ability change keeps its old list: apply the
  character migration, or dismiss + re-raise + Tether it.
- Spellbook tabs and the **talent tabs/icons/tooltips/point spending** are
  client-rendered; `turtle-agent` cannot verify them.  T1's new passive rank
  spells (61200-61330) are inert placeholders until T2.
- If module SQL changed, re-bake the agent's spell names and rebuild it before
  testing.
- **pfQuest:** class-quest filtering needs the custom class bit (512) in
  `pfDB.bitclasses`; without it a Necromancer raises `bad argument #2 to
  'band'`. The fix and nil guards are documented in the design doc A91.

## Layout

```
src/                module source (loader: AddNecromancerScripts)
data/sql/world/     world-DB migrations (class data, spells, trainers, ...)
data/sql/character/ character-DB migrations
client/             client-side patch assets, scripts and docs
tools/              generators + parsed talent-tree data (tools/data/)
tools/data/         talent-builder JSON/Markdown (with icons) and build map
```

## License

TBD. The core is GPL-2.0 and this module is compiled into the server binary;
the practical options are GPL-2.0 (matching the core) or AGPL-3.0 (matching
TortoiseBots). A `LICENSE` file will be added before the first release.
