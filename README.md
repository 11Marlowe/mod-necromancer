# mod-necromancer

A custom **Necromancer** class (class id 10) for the
[Tortoise WoW](https://github.com/tortoise-wow/tortoise-wow) 1.12.1 server core,
built as a standalone module on the core's **class-support** layer.

**Status:** Phase 2 and the **talent pass (T1 + T2a-T2e)** are complete
(2026-10-22). Identity, spells, minions, trainers, placeholder quests, the
three-tab spellbook, icons/tooltips, the Blood-tree armor passives, the last
talent-gated spells (Soul Strike, Icy Touch/Frost Fever, Corrosion, Lichborne,
Unholy Aura), the three talent trees (54 talents, icons, rank spells), all 40
new passive talents and the active-talent polish are implemented, deployed and
server-side verified with `turtle-agent`. **T2e** polished the 14 active
talents' names, ranks, levels, tooltips and icons, and stripped the pre-T1
trainer-taught armor passives through the `OnForgotSpell` path with one free
talent reset. Class
color (red) and a placeholder creation-screen icon are in the client patch.
Remaining: custom creation-screen art; the Corpse Bag container is deferred.

The canonical design, progress log, engine lessons and placeholder list live in
the project's `Necromancer-Design.md` (mirrored in the private
`11Marlowe/wow-tools` repo). Read its **§12** (current state), **§13** (engine
lessons) and **§14** (assumptions A1-A100) before changing spells or mechanics.

## Features

- Class 10, mana-based, playable by all 10 existing races.
- Three spellbook tabs: **Reanimation (700)**, **Blood (701)**, **Plague (702)**.
- **Talent trees T1:** Reanimation / Blood / Plague tabs (TalentTab 401-403),
  54 talents (Talent 478-531) with the site icons and prerequisites. **T2a**
  implements the ten stat/defense passives, **T2b** the ten spell-modifier
  passives, **T2c** the nine minion/pet passives and **T2d** the eleven
  proc/conditional passives among the rank spells (61200-61330; hidden helpers
  61331-61350). **T2e** gives the 14 active talents canonical tooltips, ranks,
  design levels and site/substitute icons, and retires the legacy trainer-taught
  armor passives with a free talent reset.
- Class spells and minion abilities use ids **61010-61095**; trainer learn-spell
  wrappers use **61100-61150**; talent rank spells use **61200-61330** and
  hidden talent helpers **61331-61350**.
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
**Talents**); **Corrosion (61089)** stays trainer-taught (decision locked
2026-10-22; it is not in the current parsed Plague tree - creator drift).

### Talents (T1 scaffolding + T2a-T2e, 2026-10-21/22)

`patch-Z.mpq` adds the three talent tabs **Reanimation**, **Blood** and
**Plague** (`TalentTab` 401-403, classMask 0x200), 54 talents
(`Talent` 478-531) with the parsed tier/column and prerequisites, and the
site icons (rank-spell `SpellIconID`; 4 new `SpellIcon` rows, substitutes for
the rest).  Active talents reuse the existing class spells.  The 131 new
passive rank spells (61200-61330) were inert in T1; **T2a** implements the ten
stat/defense passives and **T2b** the ten spell-modifier passives (Improved
Plague Bolt, Preservation, Improved Terror, Improved Dark Command, Reaping,
Life and Death, Restlessness, Reclusion, Withering World, Improved Cripple)
through `client/patches/47-talent-mechanics-t2a.yaml` /
`48-talent-mechanics-t2b.yaml` and SQL `20261021140000` /
`20261021160000`.  **T2c** implements the nine minion/pet passives (Running
Dead, Unnatural Life, Solitude, Graverobbing, Unholy Power, Piercing Fingers,
Undead Domination, Retained Intellect, Twisted Bond) with hidden helper spells
61331-61341, a new `PetScript`, and module damage/proc hooks through
`client/patches/49-talent-mechanics-t2c.yaml` and SQL `20261021180000`.
**T2d** implements the eleven proc/conditional passives (Shadowskin,
Zombification, Bloodletting, Bloodgorged, Butchery, Phantom Armor, Early
Grave, Metastasis, Death's Embrace, Icy Talons, Wandering Plague) with hidden
helpers 61342-61350 through `client/patches/49b-talent-mechanics-t2d.yaml`
and SQL `20261022120000`.  **T2e** finishes the active talents: the 14
shortcuts get canonical names/ranks, design levels, full tooltips and the
site/substitute icons through `client/patches/49c-talent-polish-t2e.yaml` and
SQL `20261022160000`; the trainer cleanup remains idempotent (28 rows, Corrosion
61148 stays).  T2e decisions (A99): Corrosion stays trainer-taught; the 3 armor
passives (61090-61092) are stripped from pre-T1 characters through the module's
`RemoveSpell` login cleanup (marker variable 1001; `OnForgotSpell` removes the
granted skills and auto-unequips gear) with one free talent reset.  The
client-rendered talent tooltips/icons still need an in-client check.

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
  client-rendered; `turtle-agent` cannot verify them.  T1-T2e are all live;
  the remaining check is the in-client talent/respec pass.
- T2e server checks: active spell metadata (`level` 20/30/40 and the Army
  ranks), trainer list still 28 rows with none of the 15 talent-gated learn
  ids, and the legacy armor-passive cleanup.  For the cleanup, mark a pre-T1
  character in `character_variables` (type 1001 = '1'), log in, and confirm a
  `spell_removed` event for 61090-61092, skills 43/44/54/55/160/172/229/293/
  413/414 reading 0 (`gm getskillvalue`), invalid plate/mail/weapons moved to
  the bags, and variable type 4 (`FreeTalentResets`) at 1.
- T2e client check: talent tooltips/icons/ranks and the free respec prompt
  (icons/tooltips are rendered by the real client only).
- T2a server checks: `unit statinfo` (Parry chance, melee/spell hit, damage
  mods), `getskillvalue 55/160/172` (2H skill bonus), `list auras` (rank-spell
  auras), `.aura 61023` repeatedly (Death March slow resist) and
  `.aura 61071` + `.cast 528` (Terminal; refill mana with
  `modify mana 2743 2743`).  Use `target <self guid>` first for the GM
  commands that read the selected player.
- T2b server checks: `spell_start` cast_ms for Improved Plague Bolt (2500),
  Improved Terror (0), Raise Ghoul (3000) and Harvest's channel (2000);
  Reap's second cast after ~6.3 s (Reaping); mana deltas for Preservation
  (Call of the Grave 144 vs 160) and Reclusion (Ghoul Armor 108 vs 120);
  Death Coil damage 598 vs 544 with/without Life and Death.  Remember
  `.gm off` before debuff tests (GM mode wipes auras) and that direct Toxic
  Plague has a 1.5 s cast.
- T2c server checks: `list auras` on the player (Unnatural Life 137, Twisted
  Bond 42, Undead Domination 61340) and on a tethered Ghoul (61331/61332/
  61334/61335/61336/61339; `unit statinfo` shows the Stamina/Intellect/health
  gains).  Raise a minion and confirm Graverobbing 61333 (8 s) on the player
  and, with Undead Domination learned, an instant `spell_start` (`cast_ms` 0)
  replaced by the 10 min marker 61341.  Solitude is measured via the mob's
  health delta (Death Coil 544 -> 576 with no minion; the `spell_damage`
  event still reports the pre-hook amount).  Newly created pets need the
  `UpdateAllStats()` refresh the PetScript performs, so test on a fresh
  summon/tether.
- T2d server checks: `list auras` (Zombification 61344; Icy Talons 61343 while
  Frost Fever is active; Butchery 61345 after a parry; Shadowskin/Phantom
  61346-61349 with Bone/Ghoul/Lich Armor).  Bloodlet's energize should be
  1.2x its damage with Bloodletting 2 (12 damage -> 14 mana); Wandering
  Plague's 61350 should hit the victim and enemies within 8 yd; Early Grave
  makes an early Call of the Grave tick triple (56 -> 168 at rank 5);
  Death's Embrace raises Death Coil's low-health hit by 6% (~760 -> 806).
  Metastasis 61342 is a **hidden client-side** debuff: `unit.auras` and the
  agent's aura events do not show it, so verify with GM `aura 61342` +
  `list auras` on the mob or a temporary module log.  A hidden helper cast on
  an enemy must not have the passive bit (use `Attributes` 128, not 192).
  `modify parry 100` (self selected) makes the Butchery parry proc easy to
  test; reset it afterwards.
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
