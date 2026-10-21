# Plague — Necromancer talent tree (talent-builder.dev)

- **Tree id:** 7MUHx-ICEg
- **Name:** Plague
- **Tree icon slug:** `spell_shadow_plaguecloud` (SpellIcon 97)
- **Class:** Necromancer (site class field 0)
- **Game version:** 1.12.1
- **Grid:** 7 rows × 4 columns × 1 page (talent `slot` keys are 0-based row-major flat indices)
- **Talents:** 18 | **Total ranks (points):** 53
- **Author:** nelsen94 | **Visibility:** public
- **Created:** 2026-08-06T15:22:49.000Z | **Updated:** 2026-10-13T23:39:08.000Z
- **Source:** https://www.talent-builder.dev/trees/7MUHx-ICEg
- **Saved HTML:** `C:\Users\gawrg\.local\share\opencode\tool-output\tool_13c0e870a001ftrawp8XEjardV`

| Slot # | Name | MaxRank | Icon slug | SpellIcon ID | Description | Position (row, col) | Requires | Highlight |
|---:|---|---:|---|---:|---|---|---|---|
| 1 | Improved Plague Bolt | 5 | `Spell_fire_felflamebolt` | — | Reduces the cast time of your Plague Bolt by 0.1/0.2/0.3/0.4/0.5 seconds. | 1, 2 | — | no |
| 2 | Preservation | 5 | `spell_frost_manaburn` | 145 | Reduces the mana cost of your Plague spells by 2/4/6/8/10%. | 1, 3 | — | no |
| 4 | Precision | 3 | `Spell_deathknight_spelldeflection` | — | Increases your chance to hit with melee attacks and spells by 1/2/3%. | 2, 1 | — | no |
| 5 | Susceptibility | 2 | `ability_creature_disease_03` | 1959 | Reduces the target's resistance to all your spells by 5/10. | 2, 2 | — | no |
| 6 | Improved Terror | 5 | `spell_shadow_auraofdarkness` | 91 | Reduces the cast time of your Terror spell by 0.4/0.8/1.2/1.6/2 seconds. | 2, 3 | — | no |
| 8 | Cripple | 1 | `spell_shadow_cripple` | 96 | Reduces the target's movement speed by 10% and reduces its attack power by X. Lasts 10 sec. | 3, 1 | — | no |
| 9 | Disease Cloud | 1 | `spell_shadow_plaguecloud` | 97 | Explodes a victim of your Toxic Plague, instantly inflicting damage equal to one tick to all enemies in an 8 yard radius, and additional Nature damage equal to the total base damage of your Toxic Plague for 8 seconds in the area. | 3, 2 | — | no |
| 10 | Early Grave | 5 | `spell_shadow_animatedead` | 221 | Your Call of the Grave has a 4/8/12/16/20% chance to trigger its final triple damage effect on an earlier tick. | 3, 3 | — | no |
| 11 | Withering World | 3 | `spell_shadow_deathanddecay` | 118 | Increases the damage of Desecration and Disease Cloud by 5/10/15%. | 3, 4 | — | no |
| 13 | Metastasis | 5 | `ability_creature_disease_02` | 1737 | Your direct damage spells have a 20/40/60/80/100% chance to increase the damage of your Diseases on the target by 3% for 15 seconds. Stacks up to 5 times. | 4, 2 | — | no |
| 14 | Terminal | 3 | `ability_rogue_feigndeath` | 857 | Reduces the chance that your Diseases will be dispelled by 7/14/20%. | 4, 3 | — | no |
| 15 | Death's Reach | 2 | `spell_shadow_fingerofdeath` | 76 | Increases the range of your Plague spells and Death Coil by 3/6 yards, and the range of your Reap ability by 5/10 yards. | 4, 4 | — | no |
| 16 | Improved Cripple | 2 | `spell_shadow_cripple` | 96 | Increases the movement speed reduction of your Cripple ability by 15/30%. | 5, 1 | #8 Cripple | no |
| 17 | Icy Touch | 1 | `spell_frost_manarecharge` | 36 | Causes X to Y Frost damage and infects the target with Frost Fever, causing an additional X Frost damage over 15 seconds and reducing ranged, melee attack and casting speed by 5% for the duration. | 5, 2 | — | no |
| 18 | Death's Embrace | 2 | `spell_shadow_devouringplague` | 2520 | Increases the damage of your Plague spells, Reap, and Death Coil by 3/6% when your target is at or below 35% health.  | 5, 3 | — | no |
| 21 | Icy Talons | 5 | `spell_frost_frostarmor` | 119 | Increases the damage of your direct damage spells by 1/2/3/4/5%. Additionally, any time an enemy is affected by your Frost Fever, you increase your spell casting speed by 1/2/3/4/5%. | 6, 2 | #17 Icy Touch | no |
| 22 | Wandering Plague | 2 | `spell_deathknight_necroticplague` | — | When your Diseases damage an enemy, there is a chance equal to your spell hit chance that they will deal 25/50% additional damage to the enemy and all enemies within 8 yards. | 6, 3 | — | no |
| 25 | Lichborne | 1 | `ability_creature_cursed_05` | 1739 | Assume a Lichform, reducing Physical damage taken by 10% and causing your casting speed increase effects to increase the tick speed of your Diseases and channeled abilities with 100% efficiency, reducing their duration. | 7, 2 | #21 Icy Talons | no |

_Slot keys are the site's raw talent keys; positions are derived from the rendered grid (4 columns). Descriptions are verbatim._

## Icons missing from the 1.12 `SpellIcon.dbc`

These site icon slugs are not registered in the 1.12 `SpellIcon.dbc`.  The texture may still exist in the client (common for item icons) and then only needs a new SpellIcon row; otherwise use a substitute or custom art:

- `Spell_deathknight_spelldeflection`
- `Spell_fire_felflamebolt`
- `spell_deathknight_necroticplague`

## Per-talent spell ids (spellIds)

| Slot # | Name | spellIds |
|---:|---|---|
| 1 | Improved Plague Bolt | (null) |
| 2 | Preservation | (null) |
| 4 | Precision | (null) |
| 5 | Susceptibility | (null) |
| 6 | Improved Terror | (null) |
| 8 | Cripple | (null) |
| 9 | Disease Cloud | (null) |
| 10 | Early Grave | (null) |
| 11 | Withering World | (null) |
| 13 | Metastasis | (null) |
| 14 | Terminal | (null) |
| 15 | Death's Reach | (null) |
| 16 | Improved Cripple | (null) |
| 17 | Icy Touch | (null) |
| 18 | Death's Embrace | (null) |
| 21 | Icy Talons | (null) |
| 22 | Wandering Plague | (null) |
| 25 | Lichborne | (null) |

## Tree notes (verbatim, as stored — HTML-formatted text)

```html
## Plague Spellbook (WIP):

***

***Level 1 - Plague Bolt:*** Causes X to Y Nature damage and infects the target with Toxic Plague, causing an additional X Nature damage over 15 seconds.  The direct damage of your Plague Bolt increases by 3% for each of your Diseases on the target. ***(3 second cast time, 30 yard range, No CD)***

***

***Level 12 - Call of the Grave:*** Infects the target with Grave Rot, dealing X Shadow damage over 24 seconds and causing triple damage on the final tick. ***(Instant, 30 yard range, 24 sec duration, No CD)***

***

***Level 14 - Terror:*** Terrorize the enemy, causing it to run in fear for up to 10 sec. Damage caused may interrupt the effect. Only 1 target can be terrorized at a time. ***(2 sec cast time, 20 yard range, 10 sec duration, 10 sec CD)***

***

***Level 20 - Desecration:*** Desecrates the land beneath the Necromancer, doing X Shadow damage over 8 sec to enemies who enter the area and reducing their healing received by 15%. The desecrated power wanes, dealing reduced damage as time passes. ***(Instant, 8 yard radius, 8 sec duration, 8 sec CD)***

***

***Level 20 (Talent) - Disease Cloud:*** Explodes a victim of your Toxic Plague, instantly inflicting damage equal to one tick to all enemies in an 8 yard radius, and additional Nature damage equal to the total base damage of your Toxic Plague for 8 seconds in the area. ***(Instant, 30 yard range, 8 yard radius, 8 sec duration, 30 sec CD)***

***

***Level 20 (Talent) - Cripple:*** Reduces the target's movement speed by 10% and reduces its attack power by X. Lasts 10 sec. ***(Instant, 30 yard range, 10 sec duration, 10 sec CD)***

***

***Level 26 - Outbreak:*** Inflicts X to Y Shadow damage to the target over 4 seconds, renewing the duration of any damaging Diseases on the target and spreading them to up to 3 additional nearby targets. ***(Channeled for 4 sec, 20 yard range, No CD)***

***

***Level 30 (Talent) - Icy Touch:*** Causes X to Y Frost damage and infects the target with Frost Fever, causing an additional X Frost damage over 15 seconds and reducing ranged, melee attack, and casting speed by 5% for the duration. ***(Instant, 30 yard range, No CD)***

***

***Level 32 (Talent) - Corrosion:*** Reduces the target's armor by X for 20 sec. ***(Instant, 30 yard range, No CD)***

***

***Level 40 (Talent) - Lichborne:*** Assume a Lichform, reducing Physical damage taken by 10% and causing your casting speed increase effects to increase the tick speed of your Diseases and channeled abilities with 100% efficiency, reducing their duration. Additionally, your Mana regenerates at 25% of the normal rate while casting. ***(Instant, No Duration)***
* ***Note:*** This is *not* a transformation into an actual Lich model. It is a custom dark frosty skin, similar in style to priest's Shadowform.


```
