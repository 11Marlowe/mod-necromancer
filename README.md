# mod-necromancer

A custom **Necromancer** class (class id 10) for the
[Tortoise WoW](https://github.com/tortoise-wow/tortoise-wow) 1.12.1 server core,
built as a standalone module on the core's **class-support** layer.

> **Status: Phase 2, trainers + placeholder class quests (auto-learn retired; post-correction pass).**
> Class identity (Phase 1)
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
> design **cast times**. Batch 3 slice 3b adds the **Army of the Dead**
> multi-minion limit (base 1 active minion; +1/+2 via the two passives
> trainer-taught at L20/L40; over-limit raises are refused, one tethered
> minion at a time) and the **Meat Catapult** (L44: a Thorium Grenade clone
> - 1.5-sec cast, 20 yd, 3-yd radius Shadow damage + 2-sec stun, 1-min
> cooldown - that consumes one Corpse Bag item). Batch 4 gives every minion
> tier its design A.7 ability set (20 spells, 61051-61070; all free and
> autocast by default - this resolved A71); Ravage and Entropic Bolt are
> retired (an old saved pet keeps its old list: dismiss it, raise that tier
> again and Tether the new guardian once to pick up its new set). The
> **spell-correction pass** (2026-10-19, design A.6-A.9 + A72) aligns the
> shipped placeholders: **Plague Bolt** is Nature damage and infects the
> target with the new **Toxic Plague** disease (+3% direct damage per
> disease), **Reap** is a shadow life-steal (instant, 10 yd, 8 s CD; no
> longer Raptor Strike), **Call of the Grave** is instant with a 24 s Grave
> Rot, **Cripple** has no cooldown, **Ghoul Frenzy** has a 1.5 min cooldown,
> **Harvest** takes beast corpses, and the class got its **own Death Coil
> (61074)** that damages enemies or heals your undead minion (the shared
> Warlock spell is no longer learned). **Trainers (2026-10-19):** the
> module's auto-learn is retired. One class trainer in Orgrimmar (Cleft of
> Shadow) and one in Stormwind (Slaughtered Lamb cellar) teach every shipped
> spell/rank through learn spells 61100-61130 (see *Trainers* below). The
> **placeholder class quests (A85, 2026-10-19)** then gate the seven
> quest-gated spells: both trainers offer one level-gated item turn-in per
> spell (Raise Zombie/Shade/Harvest at 10, Raise Ghoul/Skeleton at 14, Raise
> Banshee at 20, Raise Wraith at 30); the items are Corpse Bag items except
> Harvest, which uses Linen Cloth. The real spell is the reward. Those spells
> were removed from `npc_trainer`. The design's real
> quest/item gates remain deferred. Later batches add the Corpse Bag
> container, the remaining spellbook entries and talents. See the
> design/handoff document: <https://github.com/11Marlowe/wow-tools> (private)
> or the project's `Necromancer-Design.md`.
>
> **Verification (2026-10-19):** every batch is checked headlessly with
> `turtle-agent` (see *Testing tips*) before the user's in-client pass, which
> covers client-rendered items only.  Batch 4 passed both (in-client:
> pet-bar icons and ability tooltips, 2026-10-18); the correction pass passed
> the server-side pass (2026-10-19) and the in-client check; the trainers
> and the placeholder class quests passed the server-side pass (2026-10-19).

## Spells

| Spell | Ranks | Learned at | Model used | Notes |
| --- | --- | --- | --- | --- |
| Plague Bolt | 1-3 | 1 / 8 / 16 | Shadow Bolt | Nature damage + **Toxic Plague** rider, 3 s cast (correction pass) |
| Toxic Plague | 1-3 | applied by Plague Bolt | Corruption | Nature disease, 15 s (3 s ticks 4/7/12), ids 61071-61073; no spellbook row |
| Reap | 1-2 | 1 / 12 | Death Coil 6789 (health leech) | instant **shadow life-steal**, 10 yd, 8 s CD, high threat (correction pass) |
| Bone Armor | 1 | 1 | Frost Armor | batch 1 |
| Death Coil | — | 14 | Death Coil 6789 | the class's own **61074**: 2.5 s cast, no CD, damages enemies **or heals your undead minion** (correction pass) |
| Call of the Grave | 1-3 | 12 / 24 / 34 | Corruption | disease, instant, 24 s, final tick x3 (AuraScript) |
| Desecration | 1-3 | 20 / 34 / 46 | Rain of Fire | disease, ground channel |
| Disease Cloud | 1 | 20 | Flamestrike | requires your disease (Toxic Plague/Grave Rot) on the target |
| Cripple | 1 | 20 | Cripple (mob 89) | 10% slow + -20 AP, 10 sec, no CD |
| Raise Ghoul | 1 | 14 (quest) | Summon Atal'ai Skeleton | guardian minion (creature 846), 60 sec |
| Raise Skeleton | 1 | 14 (quest) | Summon Atal'ai Skeleton | guardian minion (creature 6412), 60 sec |
| Tether | 1 | 20 | Renew (friendly-target carrier) | converts your minion into a permanent pet |
| Ravage | 1 | pet | Lash of Pain | pet-bar active of the melee minion tiers (61027) |
| Entropic Bolt | 1 | pet | Firebolt | ranged pet-bar active of Banshee/Bloodmage (61041) |
| Sacrifice Minion | 1 | 20 | Renew (friendly-target carrier) | heal (x2 on the tethered pet) + Death Pact buff, despawns the minion |
| Harvest | 1 | 10 (quest) | Cannibalize | 3-sec channel: stores a corpse as a Corpse Bag item (aura 61030); beast corpses included (A72 fixed) |
| Corpse Bag items | - | - | items 63100-63103 | Lump of Flesh / Pile of Bones / Ectoplasm / Banshee Essence (normal bags) |
| Death Pact (Ghoul/Skeleton) | 1 | buff | Cannibalize aura scaffold | +2% physical damage done / -2% physical damage taken, 30 min |
| Death Pact (Banshee/Shade/Wraith/Hulk/Bloodmage) | 1 | buff | same scaffold | 2% mana/4 s / -5% threat / +2% speed / +5% health / +2% spell damage, 30 min |
| Ghoul Frenzy | 1 | 20 | Renew | tethered minion: CC break, +25% melee/casting speed, 50% max-health heal over 30 sec; 1.5 min CD |
| Raise Zombie / Raise Shade | 1 | 10 (quest) | Summon Atal'ai Skeleton | guardian (creature 1501 / 7370) |
| Raise Banshee | 1 | 20 (quest) | Summon Atal'ai Skeleton | guardian (creature 10463) |
| Raise Wraith | 1 | 30 (quest) | Summon Atal'ai Skeleton | guardian (creature 1800) |
| Raise Bloodmage | 1 | 38 | Summon Atal'ai Skeleton | guardian (creature 8526) |
| Raise Abomination | 1 | 40 | Summon Atal'ai Skeleton | guardian (creature 8545); needs three corpses nearby (not consumed) |
| Raise Wight | 1 | 58 | Renew (friendly-target carrier) | transforms a Zombie/Ghoul minion into a Wight (tethered stays tethered) |
| Meat Catapult | 1 | 44 | Thorium Grenade | 1.5 s cast, 20 yd, 3-yd radius Shadow damage + 2 s stun, 1 min CD; consumes one Corpse Bag item |
| Army of the Dead | 2 (passive) | 20 / 40 | Dodge (passive scaffold) | active-minion limit: base 1, +1 (R1) / +2 (R2); R2 replaces R1 |

For these batches the icons and costs are mostly the model spells' (renamed
via the client patch).  Tooltips are the models' except where the mechanics
differ: Cripple, Harvest, all Raise spells (since 2026-10-18 the raise
tooltips state the corpse/bag requirement, e.g. "requires a humanoid or
zombie corpse nearby, or 1 Lump of Flesh"), the Wight transform and the
correction-pass spells (Plague Bolt, Toxic Plague, Reap, Call of the Grave,
Death Coil).  The disease spells' rank-up mechanics are placeholders until
the talent/effect polish batches; "Disease Cloud", "Cripple" and "Tether"
are talents in the source design and are trainer-taught at level 20 until
talents exist. Custom tuning/tooltips and the rest of the design (the
Corpse Bag container, the Desecration/Disease Cloud/Bone Armor corrections,
Grim Reaper, Lichborne, ...) arrive in later batches. Spells are now taught
by the trainers (see *Trainers* below), not auto-learned.

**Minion abilities (batch 4, design A.7):** taught per tier through
`petcreateinfo_spell`; they autocast by default and all cost 0 mana.
Donors in parentheses: Ghoul Rend, Charge (boar), Cannibalize (20577/8);
Skeleton Strike (mob), Sunder Armor; Zombie Infected Bite, Cannibalize;
Shade Invisibility (Succubus Lesser Invisibility), True Sight (Detect
Invisibility); Banshee Curse (Curse of Weakness, rewritten to -3% hit),
Anti-Magic Shell (Power Word: Shield, magic-only absorb); Wraith
Debilitating Touch, Shadow Lash (Lash of Pain + 5% shadow vulnerability),
Enrage; Bloodmage Shadow Bolt, Soul Tap (Drain Life + mana leech), Dispel
Magic; Abomination Taunt, Cleave, Cannibalize, Pestilence (passive
Thorns-style aura); Wight Taunt, Cleave, Crowd Pummel (Pummel), Cannibalize.

**Known server-side issues:**

- ✅ **Ravage/Entropic Bolt fixed (batch 4):** the two actives are retired
  from `petcreateinfo_spell` (their costs are also zeroed so pets tethered
  earlier are not blocked by `no_power`); every minion ability costs 0.
- ✅ **Harvest beast corpses fixed (correction pass 2026-10-19):**
  `targetCreatureType` is 0 now; verified on a Rabid Dire Wolf corpse
  (Lump of Flesh).  The module's corpse taxonomy still gates the item types.
- **Spell-correction placeholders (design doc A78):** Harvest keeps the
  model's 2-min cooldown (design: no cooldown); Desecration is still a
  channeled Rain of Fire (design: instant Shadow + healing reduction);
  Disease Cloud's damage/tooltip are still Flamestrike's; Bone Armor is
  still Frost Armor; "Grave Rot" displays as "Call of the Grave"; damage
  values are placeholders.

Server data: `data/sql/world/20261014160000_world.sql` (batch 1),
`20261014170000_world.sql` (batch 2), `20261014180000_world.sql` (batch 3
slice 1), `20261015120000_world.sql` (batch 3 slice 2),
`20261017120000_world.sql` (batch 3 slice 3),
`20261017180000_world.sql` (batch 3 slice 3c: Corpse Bag items, corpse-class
table, Harvest/Wight cast-time + spell updates),
`20261018180000_world.sql` (batch 3 slice 3b: Army of the Dead passives +
Meat Catapult), `20261018230000_world.sql` (batch 4: per-minion abilities +
petcreateinfo sets), `20261019120000_world.sql` (spell-correction pass:
A.6-A.9 + A72, Death Coil 61074 + Toxic Plague) and
`20261019200000_world.sql` (trainers: NPCs, spawns, learn spells 61100-61130,
`npc_trainer`), `20261019220000_world.sql` (placeholder class quests, quest
relations, questgiver flag, removal of the seven gated trainer rows) and
`data/sql/character/20261019210000_char.sql` (one-time refresh of
pre-batch-4 saved pets), all generated by the scripts in `tools/` (the
character migration is hand-written).  Client patches:
`client/patches/40-spells.yaml` (corrections as `update` blocks after the
`copy` blocks), `41-learn-spells.yaml` (the trainer learn spells) and
`50-skilllines.yaml` (new "Necromancy" skill line 700; Death Coil row 7217
points at 61074).

Fourteen spells are bound to module scripts through
`spell_template.script_name` (SQL): `spell_necromancer_plague_bolt`
(Toxic Plague rider + 3% damage per disease), `spell_necromancer_reap`
(extra threat), `spell_necromancer_death_coil` (friendly-minion heal gate),
`spell_necromancer_call_of_the_grave` (AuraScript, final-tick triple
damage), `spell_necromancer_disease_cloud` (SpellScript, cast gate),
`spell_necromancer_raise_minion` (re-scales the guardian to the caster's
level; enforces the corpse/bag requirement and the Army of the Dead minion
cap), `spell_necromancer_tether`
(guardian -> permanent pet conversion),
`spell_necromancer_sacrifice_minion` (heal + per-kind Death Pact + despawn),
`spell_necromancer_harvest` (corpse gate + channel start),
`spell_necromancer_harvest_aura` (the 3-sec channel: stores the corpse item),
`spell_necromancer_ghoul_frenzy` (SpellScript *and* AuraScript; CC break +
script-computed heal), `spell_necromancer_raise_wight` (Zombie/Ghoul ->
Wight transform), `spell_necromancer_meat_catapult` (cast gate + Corpse
Bag item consumption) and `spell_necromancer_minion_cannibalize` (minion
corpse gate + the vanilla Cannibalize regen aura 20578).  The names must
match the registrations in
`AddNecromancerScripts()`.  The module also registers its class's
`permanentSummonPetTypes` (undead) on the core's `ClassDescriptor` at
startup - without it a tethered minion has no pet-bar abilities (see below).

## Trainers

The class is trained, not auto-learned (the module's level-up/login grants
were removed on 2026-10-19):

| City | NPC | Where | Entry |
| --- | --- | --- | --- |
| Orgrimmar | **Gorvoth the Gravewarden** | Cleft of Shadow, by the warlock trainers | 950010 |
| Stormwind | **Mordecai Gravewhisper** | Slaughtered Lamb cellar, by the warlock trainers | 950011 |

Both have `trainer_class = 10` and teach the **24 non-quest spells and ranks**
(learn spells 61100-61130, `npc_trainer` rows); the other seven are the rewards
of the placeholder class quests below.  Prices use the vanilla class-trainer
level table (10 copper at level 1 up to 240 silver at 58); rank 2/3 spells still
require the previous rank (`spell_chain`).  The design's real quest/item gates
(L10 quest chain, L38 Amnennar, L58 Gandling, L40 Abomination) remain deferred.

### Placeholder class quests (A85)

Both trainers have `npc_flags` **19** (gossip + trainer + questgiver) and
`creature_questrelation` / `creature_involvedrelation` rows for every quest.
The quests are class-10 only (`RequiredClasses` 0x200), level-gated, and each
turns in one item (a Corpse Bag item, except Harvest, which uses Linen Cloth).
`RewSpell` is the real spell (client icon/name)
and `RewSpellCast` is the matching learn-spell wrapper, so the reward teaches
the spell.  The seven spells were removed from `npc_trainer`; existing
characters keep any spell they already know.

| Level | Quest | Spell | Turn-in |
| --- | --- | --- | --- |
| 10 | 950100 | Raise Zombie | 1x Lump of Flesh (63100) |
| 10 | 950101 | Raise Shade | 1x Ectoplasm (63102) |
| 10 | 950102 | Harvest | 1x Linen Cloth (2589) |
| 14 | 950103 | Raise Ghoul | 1x Lump of Flesh (63100) |
| 14 | 950104 | Raise Skeleton | 1x Pile of Bones (63101) |
| 20 | 950105 | Raise Banshee | 1x Banshee Essence (63103) |
| 30 | 950106 | Raise Wraith | 1x Ectoplasm (63102) |

Quest IDs 950100-950106 are reserved for these placeholders; the titles and
descriptions are marked PLACEHOLDER.  Harvest deliberately uses **Linen Cloth**
(2589) rather than a Corpse Bag item, so a fresh character can start the
Harvest -> corpse item -> raise chain without a GM or trade; the other six
quests use the design's Corpse Bag items.  Recorded in the design doc A85.

- **Learn-spell wrappers:** vanilla trainers list *learn spells* (effect 36)
  whose `EffectTriggerSpell[0]` is the real spell.  The server rows are
  `spell_template` 61100-61130 (cloned from Immolate's learn spell 1374); the
  client gets their names/ranks/icons/descriptions from
  `client/patches/41-learn-spells.yaml` (rebuilt into `patch-Z.mpq`).
- **Auto-learn retired:** new characters use the trainers; existing characters
  keep what they already know.  The module still strips the old shared Warlock
  Death Coil (6789) on login/learn.
- **Army of the Dead:** both ranks are trainer-taught; rank 2 is not removed
  from characters that already have rank 1 (the minion cap checks rank 2 first).
- Regenerate the server SQL and client YAML with
  `tools/generate_trainers.py` (re-runnable; it uses the live DB for donors).
- Regenerate the quest SQL with `tools/generate_placeholder_quests.py`
  (re-runnable; it validates the trainers, items and learn-spell wrappers).
- Trainer SQL: `data/sql/world/20261019200000_world.sql` (trainers, spawns,
  greetings, learn spells, `npc_trainer`).  Quest SQL:
  `data/sql/world/20261019220000_world.sql`.

## Testing tips

**Standard (since 2026-10-18): verify server-side first.** Module changes are
checked with the headless `turtle-agent` client (JSON-RPC; project
`TurtleAgent-Workflow.md`, `SESSION_NOTES.md` §10f) — trainers/spells,
casts and event damage/auras, cast gates, minions/pet, bag items — before the
in-client pass, which is only for client-rendered items (icons, tooltips,
models, Glue UI). The 2026-10-18 spike verified the whole slice-3b list and
batch 4; the 2026-10-19 pass verified the spell corrections + A72.

- ⚠️ **Turn GM mode off first.** The test character can log in with GM mode
  ON (a persisted flag). A GM attacker makes creatures evade/reset, which
  wipes debuffs between casts — debuff-persistence checks (Toxic Plague,
  the +3%/disease) fail spuriously. Send `.gm off` after login.

- **Level changes use `.levelup <n>`** (adds n levels; the core has no
  `.character level`) and are a **GM command** (rank 3+). Either use a GM-rank
  account or run `account set gmlevel <user> 4 -1` in the mangosd console (a
  rank change needs a mangosd restart — the rank cache loads at startup).
  Beware `GM.StartOnGMIsland = 1`: characters *created* on a GM account spawn
  on GM island with a GM starter kit — create test characters on a normal
  account.
- **Placeholder class quest checks (2026-10-19, server-side verified with
  `turtle-agent`):** both trainers list 7 PLACEHOLDER quests in the gossip
  menu, and `trainer_list` has 24 entries (the seven quest spells are gone).
  Accept a quest, fetch its item with `.additem <id> 1` (GM), hand it in and
  take the reward: the NPC casts the learn spell and the real spell appears in
  `spells`.  Harvest's item is Linen Cloth (2589); the rest are Corpse Bag
  items.  Quests 950100-950106; see the table above.
- **Batch-2 test flow:** level a Necromancer to 12 and **train Call of the
  Grave** (Orgrimmar/Stormwind trainer), cast it on a mob and watch the ticks —
  the **final tick deals triple damage**; the debuff is a *disease*
  (dispellable by cure-disease effects). At 20 train Desecration (ground
  channel), Disease Cloud and Cripple. Disease Cloud cast on an enemy shows
  "You can't do that yet" until the enemy carries your Toxic Plague (or
  Call of the Grave); ground-target casts cannot be verified server-side yet
  (placeholder, see the design doc) and are allowed. Cripple should show
  -10% move speed and -20 attack power for 10 sec and has no cooldown.
- **Batch-3 minion checks:** at 14 train and cast Raise Ghoul / Raise Skeleton —
  a temporary (60 sec) guardian appears, follows you and fights nearby enemies;
  casting the same Raise again dismisses it (toggle). At 20 train Tether and
  cast it on your minion (select it, then cast): it becomes your **permanent,
  controllable pet** (pet bar appears; only one at a time; persists across
  logout and taxis like a warlock pet). Minions are vanilla undead models
  (Ghoul 846 / Skeleton 6412) re-scaled to your level by the module
  (placeholder tuning). Known placeholder: a tethered minion is not restored
  by the spirit healer / BG resurrect yet.
- **Reap** (correction pass) is an instant **shadow life-steal**: it damages
  the target and heals you, has a 10 yd range and an 8 s cooldown, and no
  longer needs a weapon (it is no longer Raptor Strike).
- **Batch-3 slice-2 checks:** a tethered minion's **pet bar shows "Ravage"**
  (a pet tethered *before* this update must be re-tethered once) - click it
  while the pet fights.  At 20, **Sacrifice Minion** on your minion heals you
  (doubled on the tethered pet), grants the skull-icon **Death Pact** buff
  (+2% physical damage done for a Ghoul, -2% physical damage taken for a
  Skeleton) and despawns the minion; the buff disappears when you Raise or
  Tether a new minion.  **Harvest** (trained at 10) channels 3 s on a
  corpse within 5 yd and stores it as a Corpse Bag item (see the slice-3c
  checks below); damage/movement interrupts it.
  **Ghoul Frenzy** on the tethered minion hastes it (+25% melee/casting) and
  heals 5% of its max health every 3 s for 30 s; fear/root the pet first to
  see the CC break.  Die with a tethered pet and take the spirit healer's
  resurrection: the minion is re-summoned (new in slice 2).
- **Batch-3 slice-3 checks:** level to 58 with `.levelup` (GM-only) to
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
- **Batch-3 slice-3b checks:** the **minion limit** is 1 active minion
  (guardian or tethered) until **Army of the Dead** is trained at 20
  (2 minions) and 40 (3 minions; rank 2 is checked first) - over-limit raises
  are refused ("You already control a summoned creature"); recasting a raise
  whose own minion is up still dismisses it, and an Abomination replaces an
  active Wight.  **Meat Catapult** (L44) throws your Corpse Bag corpse at a
  target/ground point within 20 yd: 1.5-sec cast, 3-yd Shadow damage + 2-sec
  stun, 1-min cooldown, and consumes one bag item (Flesh first, then Bones,
  Ectoplasm, Essence); without any corpse item the cast is refused.  It
  cannot be used while moving (engine limitation).
- **Batch-4 checks (server-side ✅ verified with `turtle-agent`; the client
  pass is pet-bar icons/tooltips only):** a minion saved **before** batch 4
  keeps its old Ravage/Entropic Bolt rows; Tether reuses the saved pet number,
  so re-tethering alone does not refresh it.  Apply
  `data/sql/character/20261019210000_char.sql` (rewrites every class-10 saved
  pet's `pet_spell` rows and clears `abdata`) and relog/restart the server
  cache.  New pets get the set at summon; the migration also enables autocast
  on the refreshed saved pets.  Cannibalize needs a humanoid/undead corpse within 5 yd
  (`no_edible_corpses` otherwise); the Wight transform (Raise Wight on a
  Zombie/Ghoul minion) keeps the Wight's Taunt/Cleave/Crowd
  Pummel/Cannibalize set.
- **Correction-pass checks (server-side ✅ verified with `turtle-agent`
  2026-10-19; the in-client pass covers the tooltips/icons):** Plague Bolt is
  Nature (green numbers) and applies the **Toxic Plague** disease (+3% direct
  damage per disease on the target); Reap is the instant shadow life-steal
  with an 8 s cooldown; Call of the Grave is instant with a 24 s Grave Rot
  (final tick x3); Cripple has no cooldown; Ghoul Frenzy shows 1.5 min;
  Death Coil is the class's own 2.5 s/no-CD spell and **heals your undead
  minion** when cast on it; Harvest takes beast corpses.
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
