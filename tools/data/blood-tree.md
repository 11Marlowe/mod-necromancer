# Blood — Necromancer talent tree (talent-builder.dev)

- **Tree id:** XZQH7kv2N2
- **Name:** Blood
- **Tree icon slug:** `Spell_deathknight_butcher2` (not in 1.12 `SpellIcon.dbc`)
- **Class:** Necromancer (site class field 0)
- **Game version:** 1.12.1
- **Grid:** 7 rows × 4 columns × 1 page (talent `slot` keys are 0-based row-major flat indices)
- **Talents:** 18 | **Total ranks (points):** 49
- **Author:** nelsen94 | **Visibility:** public
- **Created:** 2026-10-11T01:08:42.000Z | **Updated:** 2026-10-14T18:28:34.000Z
- **Source:** https://www.talent-builder.dev/trees/XZQH7kv2N2
- **Saved HTML:** `C:\Users\gawrg\.local\share\opencode\tool-output\tool_13c0e867e001bFbzjCjW4NFDxj`

| Slot # | Name | MaxRank | Icon slug | SpellIcon ID | Description | Position (row, col) | Requires | Highlight |
|---:|---|---:|---|---:|---|---|---|---|
| 1 | Zombification | 5 | `spell_shadow_unholyfrenzy` | 95 | Converts 5/10/15/20/25% of your Intellect into Strength. | 1, 2 | — | no |
| 2 | Unholy Regeneration | 5 | `Spell_deathknight_vendetta` | — | Allows 10/20/30/40/50% of your health regeneration to continue while in combat. | 1, 3 | — | no |
| 4 | Bloodletting | 2 | `spell_shadow_bloodboil` | 541 | Increases the amount of Mana awarded by your Bloodlet ability by 10/20%. | 2, 1 | — | no |
| 5 | Reaping | 2 | `spell_shadow_ritualofsacrifice` | 130 | Reduces the cooldown of your Reap ability by 1/2 sec. | 2, 2 | — | no |
| 6 | Deflection | 3 | `ability_parry` | 558 | Increases your Parry chance by 2/4/6%. | 2, 3 | — | no |
| 7 | Death March | 2 | `inv_boots_plate_05` | — | Increases your chance to resist Fear and movement slowing effects by an additional 5/10%. | 2, 4 | — | no |
| 8 | Dual Wield Specialization | 5 | `ability_dualwield` | 533 | Increases the damage dealt with one-handed weapons by 2/4/6/8/10% and the damage done by your off-hand weapon by an additional 5/10/15/20/25%. | 3, 1 | #9 Grim Reaper | no |
| 9 | Grim Reaper | 1 | `ability_rogue_nightblade` | — | Allows the use of all two-handed weapons and dual wielding all one-handed weapons. While dual wielding, you strike with both weapons when using any melee ability. Additionally, allows the use of Sigils but you can no longer use Wands. | 3, 2 | — | no |
| 10 | Two-Handed Weapon Specialization | 3 | `inv_axe_09` | 366 | Increases the damage you deal with two-handed melee weapons by 2/4/6%, and your weapon skill with two-handed swords, maces and axes by 1/2/3. | 3, 3 | #9 Grim Reaper | no |
| 11 | Soul Strike | 1 | `inv_sword_62` | — | Instantly strike the target for 50% weapon damage and healing you by 3% of your total health for each of your diseases on the target, up to a total of three diseases. | 3, 4 | — | no |
| 12 | Bloodgorged | 5 | `ability_racial_cannibalize` | 146 | Increases your chance to get a critical strike with melee weapons by 1/2/3/4/5% and increases the damage and lifesteal of your Reap ability by 3/6/9/12/15%. | 4, 1 | — | no |
| 14 | Improved Dark Command | 2 | `ability_creature_disease_05` | — | Improves your chance to hit with Dark Command by 4/8%. | 4, 3 | — | no |
| 17 | Necro Knight | 1 | `inv_chest_plate06` | — | Allows the use of Leather and Mail armor. | 5, 2 | #9 Grim Reaper | no |
| 18 | Looming Shadow | 5 | `spell_nature_shamanrage` | 2153 | Increases your Defense skill by 4/8/12/16/20, and all threat you generate by 20/40/60/80/100%. | 5, 3 | — | no |
| 19 | Unholy Aura | 1 | `inv_helmet_08` | 1599 | Increases movement speed by 8% and allows 25% of health regeneration to continue in combat for you and your allies in a 30 yard range. | 5, 4 | #18 Looming Shadow | no |
| 20 | Butchery | 2 | `inv12_ability_deathknight_cleavingdeathstrikes` | — | Increases the damage of your Plague Strike and Soul Strike by 5/10%. Additionally, your attack speed is increased by 7/15% for your next 3 swings after parrying or dealing a melee critical strike. | 6, 1 | — | no |
| 22 | Phantom Armor | 3 | `inv_chest_leather_13` | — | Increases your armor value from items by 3/6/10%, and while your Bone Armor, Ghoul Armor or Lich Armor are active, your damage taken is reduced by 3/6/10%.  | 6, 3 | #18 Looming Shadow | no |
| 25 | Will of the Death Knight | 1 | `ability_warrior_improveddisciplines` | 2200 | Empowers you with the will of a Death Knight, allowing the use of Plate armor and causing you to deal an additional 4% physical damage as Shadow damage. | 7, 2 | #17 Necro Knight | no |

_Slot keys are the site's raw talent keys; positions are derived from the rendered grid (4 columns). Descriptions are verbatim._

## Icons missing from the 1.12 `SpellIcon.dbc`

These site icon slugs are not registered in the 1.12 `SpellIcon.dbc`.  The texture may still exist in the client (common for item icons) and then only needs a new SpellIcon row; otherwise use a substitute or custom art:

- `Spell_deathknight_butcher2`
- `Spell_deathknight_vendetta`
- `ability_creature_disease_05`
- `ability_rogue_nightblade`
- `inv12_ability_deathknight_cleavingdeathstrikes`
- `inv_boots_plate_05`
- `inv_chest_leather_13`
- `inv_chest_plate06`
- `inv_sword_62`

## Per-talent spell ids (spellIds)

| Slot # | Name | spellIds |
|---:|---|---|
| 1 | Zombification | (null) |
| 2 | Unholy Regeneration | (null) |
| 4 | Bloodletting | (null) |
| 5 | Reaping | (null) |
| 6 | Deflection | (null) |
| 7 | Death March | (null) |
| 8 | Dual Wield Specialization | (null) |
| 9 | Grim Reaper | (null) |
| 10 | Two-Handed Weapon Specialization | (null) |
| 11 | Soul Strike | (null) |
| 12 | Bloodgorged | (null) |
| 14 | Improved Dark Command | (null) |
| 17 | Necro Knight | (null) |
| 18 | Looming Shadow | (null) |
| 19 | Unholy Aura | (null) |
| 20 | Butchery | (null) |
| 22 | Phantom Armor | (null) |
| 25 | Will of the Death Knight | (null) |

## Tree notes (verbatim, as stored — HTML-formatted text)

```html
## Blood Spellbook (WIP)

***

***General Note:*** 
* The Necromancer is a Horde only class, available to Undead, Orcs, Trolls, and Ogres. This Necromancer design approach bridges a major gap in lore and RP for Classic+, as a dark mirror to paladins and avoids class bloat by combining Necromancer and Death Knight into one class.
* The Necromancer's three talent trees are Reanimation (summoning), Plague (spreading disease), and Blood (melee combat Death Knight pathway). The class has very strong DPS capabilities overall and plays as a competitive tank via the Blood tree.
* While both the Horde and Alliance broadly shun necromancy, the Forsaken have found a particular affinity to it and see the practice as a point of strength. Thus, the Forsaken lead necromancy within the Horde at the behest of Sylvanas, and have taken hidden sects of Orc, Troll, and Ogre disciples under their wing. 
* Having witnessed the strength of Death Knights during the Scourge's war on Lordaeron, Sylvanas discussed with her council how the Forsaken may harness these powers too. However, since the Forsaken do not possess the powers to raise new conscious undead, the Horde's necromancers can only become Death Knights through sheer martial will. The Forsaken realized it is far easier for a master of volatile death magic to train their body in physical combat than for a common brute to learn complex necromancy. 
* Thus, Horde Necromancers learn to train as Death Knights, just as Alliance Priests learned to train as Paladins. 

***

***Level 1 - Reap:*** Steals X to Y life from the target, causing Shadow damage. This ability generates a high amount of threat. ***(Instant, 10 yard range, 8 sec CD)***

***

***Level 6 - Bloodlet:*** Reduces the duration of a disease on the target by one tick, causing you the damage of that tick in exchange for stealing an equal amount of mana. If the target has multiple diseases, this effect will always apply to the strongest disease. ***(Instant, 30 yard range, No CD)***

***

***Level 10 (Quest) - Plague Strike:*** A strike that deals weapon damage plus X and infects the target with Toxic Plague, dealing an additional X to Y Nature damage over 15 seconds. The direct damage is increased by 3% for each of your Diseases on the target. ***(Instant, 6 sec CD)***
* ***Note:*** At level 10, the Necromancer class trainers provide a quest chain that kicks off the path of a Death Knight and ends in learning Plague Strike. As such, Necromancers do not have melee abilities at baseline - they are obtained through quests (Plague Strike) or through talents (Soul Strike).

***

***Level 10 - Dark Command:*** Commands the target to attack you, but has no effect if the target is already attacking you. ***(Instant, 5 yard range, 10 sec CD)***

***

***Level 20 (Talent) - Grim Reaper:*** Allows the use of all two-handed weapons and dual wielding all one-handed weapons. While dual wielding, you strike with both weapons when using any melee ability. Additionally, allows the use of Sigils but you can no longer use Wands. ***(Passive)***

***

***Level 20 (Talent) - Soul Strike:*** Instantly strike the target for 60% weapon damage and healing you by 3% of your total health for each of your Diseases on the target. ***(Instant, 6 sec CD)***

***

***Level 30 (Talent) - Necro Knight:*** Allows the use of Leather and Mail armor. ***(Passive)***

***

***Level 30 (Talent) - Unholy Aura:*** Increases movement speed by 8% and allows 25% of health regeneration to continue in combat for you and your allies in a 30 yard range. ***(Instant, 30 yard radius, No Duration)***

***

***Level 40 (Talent) - Will of the Death Knight:*** Empowers you with the will of a Death Knight, allowing the use of Plate armor and causing you to deal an additional 4% physical damage as Shadow damage. ***(Passive)***

***

***Level 40 - Dark Punishment:*** When activated, increases your damage done by physical attacks and direct damaging spells by 15% while draining 2% of your maximum health per second. Lasts 20 seconds and cannot be cancelled. ***(Instant, Self-Buff, 20 sec duration, 3 min CD)***



```
