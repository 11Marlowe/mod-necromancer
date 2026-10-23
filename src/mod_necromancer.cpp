/*
 * mod-necromancer - Necromancer class module for the Tortoise WoW 1.12.1 core
 *
 * Requires the core's `class-support` branch (ClassRegistry, `playable_class`
 * and `class_descriptor` tables, PlayerScript::CanCreateCharacter hook).
 *
 * License: TBD (the core is GPL-2.0; this module is compiled into it).
 */

#include "ScriptObjects.h"
#include "Log.h"
#include "Player.h"
#include "SpellAuras.h"
#include "Spell.h"
#include "Unit.h"
#include "Pet.h"
#include "ClassRegistry.h"
#include "GridNotifiers.h"
#include "GridNotifiersImpl.h"
#include "CellImpl.h"
#include "Creature.h"
#include "ObjectMgr.h"
#include "DBCStores.h"
#include "Database/DatabaseEnv.h"
#include "ObjectAccessor.h"
#include "Util.h"

#include <algorithm>
#include <functional>
#include <string>
#include <unordered_map>

namespace
{
    enum NecromancerSpellIds
    {
        NECRO_SPELL_PLAGUE_BOLT_R1       = 61010,
        NECRO_SPELL_PLAGUE_BOLT_R2       = 61011,
        NECRO_SPELL_PLAGUE_BOLT_R3       = 61012,
        NECRO_SPELL_REAP_R1              = 61013,
        NECRO_SPELL_REAP_R2              = 61014,
        NECRO_SPELL_CALL_OF_THE_GRAVE_R1 = 61016,
        NECRO_SPELL_CALL_OF_THE_GRAVE_R2 = 61017,
        NECRO_SPELL_CALL_OF_THE_GRAVE_R3 = 61018,
        NECRO_SPELL_DESECRATION_R1       = 61019,
        NECRO_SPELL_DESECRATION_R2       = 61020,
        NECRO_SPELL_DESECRATION_R3       = 61021,
        NECRO_SPELL_DISEASE_CLOUD        = 61022,
        NECRO_SPELL_CRIPPLE              = 61023,
        NECRO_SPELL_RAISE_GHOUL          = 61024,
        NECRO_SPELL_RAISE_SKELETON       = 61025,
        NECRO_SPELL_TETHER               = 61026,
        NECRO_SPELL_RAVAGE               = 61027,
        NECRO_SPELL_SACRIFICE_MINION     = 61028,
        NECRO_SPELL_HARVEST              = 61029,
        NECRO_SPELL_HARVEST_AURA         = 61030,
        NECRO_SPELL_DEATH_PACT_GHOUL     = 61031,
        NECRO_SPELL_DEATH_PACT_SKELETON  = 61032,
        NECRO_SPELL_GHOUL_FRENZY         = 61033,
        NECRO_SPELL_RAISE_ZOMBIE         = 61034,
        NECRO_SPELL_RAISE_SHADE          = 61035,
        NECRO_SPELL_RAISE_BANSHEE        = 61036,
        NECRO_SPELL_RAISE_WRAITH         = 61037,
        NECRO_SPELL_RAISE_BLOODMAGE      = 61038,
        NECRO_SPELL_RAISE_ABOMINATION    = 61039,
        NECRO_SPELL_RAISE_WIGHT          = 61040,
        NECRO_SPELL_ENTROPIC_BOLT        = 61041,
        NECRO_SPELL_DEATH_PACT_BANSHEE   = 61042,
        NECRO_SPELL_DEATH_PACT_SHADE     = 61043,
        NECRO_SPELL_DEATH_PACT_WRAITH    = 61044,
        NECRO_SPELL_DEATH_PACT_HULK      = 61045,   // Abomination and Wight
        NECRO_SPELL_DEATH_PACT_BLOODMAGE = 61046,
        NECRO_SPELL_WIGHT_SUMMON         = 61047,   // internal: guardian summon used by the Wight transform
        NECRO_SPELL_MEAT_CATAPULT        = 61048,
        NECRO_SPELL_ARMY_OF_THE_DEAD_R1  = 61049,   // passive: +1 active minion
        NECRO_SPELL_ARMY_OF_THE_DEAD_R2  = 61050,   // passive: +2 active minions
        NECRO_SPELL_MINION_CANNIBALIZE   = 61052,   // pet ability (batch 4)
        NECRO_SPELL_TOXIC_PLAGUE_R1      = 61071,   // Plague Bolt's disease (corrections pass)
        NECRO_SPELL_TOXIC_PLAGUE_R2      = 61072,
        NECRO_SPELL_TOXIC_PLAGUE_R3      = 61073,
        NECRO_SPELL_DEATH_COIL           = 61074,   // the class's own clone (corrections pass)
        NECRO_SPELL_PLAGUE_STRIKE        = 61075,   // melee strike + Toxic Plague
        NECRO_SPELL_BLOODLET             = 61076,   // remaining spellbook batch
        NECRO_SPELL_DARK_COMMAND         = 61077,
        NECRO_SPELL_TERROR               = 61078,
        NECRO_SPELL_GHOUL_ARMOR          = 61079,
        NECRO_SPELL_EMBALM               = 61080,
        NECRO_SPELL_LOBOTOMIZE           = 61081,
        NECRO_SPELL_OUTBREAK             = 61082,
        NECRO_SPELL_RULE_UNDEAD          = 61083,
        NECRO_SPELL_UNHOLY_SHIELD        = 61084,
        NECRO_SPELL_LICH_ARMOR           = 61085,
        NECRO_SPELL_DARK_PUNISHMENT      = 61086,
        NECRO_SPELL_SOUL_STRIKE          = 61087,   // remaining talent spells
        NECRO_SPELL_ICY_TOUCH            = 61088,
        NECRO_SPELL_CORROSION            = 61089,
        NECRO_SPELL_LICHBORNE            = 61093,
        NECRO_SPELL_UNHOLY_AURA          = 61094,
        NECRO_SPELL_FROST_FEVER          = 61095,   // Icy Touch's hidden disease aura
        NECRO_SPELL_NECRO_KNIGHT         = 61090,   // armor/weapon progression passives
        NECRO_SPELL_WILL_OF_THE_DEATH_KNIGHT = 61091,
        NECRO_SPELL_GRIM_REAPER          = 61092,
        NECRO_TALENT_DEFLECTION_R1       = 61252,   // T2a stat/defense passives
        NECRO_TALENT_DEFLECTION_R2       = 61253,
        NECRO_TALENT_DEFLECTION_R3       = 61254,
        NECRO_TALENT_DEATH_MARCH_R1      = 61255,
        NECRO_TALENT_DEATH_MARCH_R2      = 61256,
        NECRO_TALENT_TWO_HANDED_R1       = 61262,
        NECRO_TALENT_TWO_HANDED_R2       = 61263,
        NECRO_TALENT_TWO_HANDED_R3       = 61264,
        NECRO_TALENT_TERMINAL_R1         = 61315,
        NECRO_TALENT_TERMINAL_R2         = 61316,
        NECRO_TALENT_TERMINAL_R3         = 61317,
        NECRO_TALENT_WITHERING_WORLD_R1  = 61307,   // T2b spell-modifier passives
        NECRO_TALENT_WITHERING_WORLD_R2  = 61308,
        NECRO_TALENT_WITHERING_WORLD_R3  = 61309,
        NECRO_TALENT_IMPROVED_CRIPPLE_R1 = 61320,
        NECRO_TALENT_IMPROVED_CRIPPLE_R2 = 61321,
        NECRO_TALENT_RUNNING_DEAD_R1     = 61200,   // T2c minion/pet passives
        NECRO_TALENT_RUNNING_DEAD_R2     = 61201,
        NECRO_TALENT_UNNATURAL_LIFE_R1   = 61202,
        NECRO_TALENT_UNNATURAL_LIFE_R2   = 61203,
        NECRO_TALENT_UNNATURAL_LIFE_R3   = 61204,
        NECRO_TALENT_UNNATURAL_LIFE_R4   = 61205,
        NECRO_TALENT_UNNATURAL_LIFE_R5   = 61206,
        NECRO_TALENT_SOLITUDE_R1         = 61207,
        NECRO_TALENT_SOLITUDE_R2         = 61208,
        NECRO_TALENT_SOLITUDE_R3         = 61209,
        NECRO_TALENT_GRAVEROBBING_R1     = 61216,
        NECRO_TALENT_GRAVEROBBING_R2     = 61217,
        NECRO_TALENT_UNHOLY_POWER_R1     = 61225,
        NECRO_TALENT_UNHOLY_POWER_R2     = 61226,
        NECRO_TALENT_UNHOLY_POWER_R3     = 61227,
        NECRO_TALENT_PIERCING_FINGERS_R1 = 61228,
        NECRO_TALENT_PIERCING_FINGERS_R2 = 61229,
        NECRO_TALENT_PIERCING_FINGERS_R3 = 61230,
        NECRO_TALENT_UNDEAD_DOMINATION   = 61231,
        NECRO_TALENT_RETAINED_INTELLECT_R1 = 61232,
        NECRO_TALENT_RETAINED_INTELLECT_R2 = 61233,
        NECRO_TALENT_RETAINED_INTELLECT_R3 = 61234,
        NECRO_TALENT_TWISTED_BOND_R1     = 61235,
        NECRO_TALENT_TWISTED_BOND_R2     = 61236,
        NECRO_TALENT_TWISTED_BOND_R3     = 61237,
        NECRO_HELPER_RUNNING_DEAD        = 61331,   // T2c hidden minion auras
        NECRO_HELPER_UNNATURAL_LIFE      = 61332,
        NECRO_HELPER_GRAVEROBBING        = 61333,
        NECRO_HELPER_PIERCING_MELEE      = 61334,
        NECRO_HELPER_PIERCING_CASTER     = 61335,
        NECRO_HELPER_RETAINED_INTELLECT  = 61336,
        NECRO_HELPER_TWISTED_BOND_MINION = 61337,
        NECRO_HELPER_TWISTED_BOND_PLAYER = 61338,
        NECRO_HELPER_TWISTED_BOND_PROC   = 61339,
        NECRO_HELPER_UNDEAD_DOMINATION   = 61340,
        NECRO_HELPER_UNDEAD_DOMINATION_CD = 61341,
        NECRO_TALENT_SHADOWSKIN_R1       = 61223,   // T2d proc/conditional passives
        NECRO_TALENT_SHADOWSKIN_R2       = 61224,
        NECRO_TALENT_ZOMBIFICATION_R1    = 61238,
        NECRO_TALENT_ZOMBIFICATION_R2    = 61239,
        NECRO_TALENT_ZOMBIFICATION_R3    = 61240,
        NECRO_TALENT_ZOMBIFICATION_R4    = 61241,
        NECRO_TALENT_ZOMBIFICATION_R5    = 61242,
        NECRO_TALENT_BLOODLETTING_R1     = 61248,
        NECRO_TALENT_BLOODLETTING_R2     = 61249,
        NECRO_TALENT_BLOODGORGED_R1      = 61265,
        NECRO_TALENT_BLOODGORGED_R2      = 61266,
        NECRO_TALENT_BLOODGORGED_R3      = 61267,
        NECRO_TALENT_BLOODGORGED_R4      = 61268,
        NECRO_TALENT_BLOODGORGED_R5      = 61269,
        NECRO_TALENT_BUTCHERY_R1         = 61277,
        NECRO_TALENT_BUTCHERY_R2         = 61278,
        NECRO_TALENT_PHANTOM_ARMOR_R1    = 61279,
        NECRO_TALENT_PHANTOM_ARMOR_R2    = 61280,
        NECRO_TALENT_PHANTOM_ARMOR_R3    = 61281,
        NECRO_TALENT_EARLY_GRAVE_R1      = 61302,
        NECRO_TALENT_EARLY_GRAVE_R2      = 61303,
        NECRO_TALENT_EARLY_GRAVE_R3      = 61304,
        NECRO_TALENT_EARLY_GRAVE_R4      = 61305,
        NECRO_TALENT_EARLY_GRAVE_R5      = 61306,
        NECRO_TALENT_METASTASIS_R1       = 61310,
        NECRO_TALENT_METASTASIS_R2       = 61311,
        NECRO_TALENT_METASTASIS_R3       = 61312,
        NECRO_TALENT_METASTASIS_R4       = 61313,
        NECRO_TALENT_METASTASIS_R5       = 61314,
        NECRO_TALENT_DEATHS_EMBRACE_R1   = 61322,
        NECRO_TALENT_DEATHS_EMBRACE_R2   = 61323,
        NECRO_TALENT_ICY_TALONS_R1       = 61324,
        NECRO_TALENT_ICY_TALONS_R2       = 61325,
        NECRO_TALENT_ICY_TALONS_R3       = 61326,
        NECRO_TALENT_ICY_TALONS_R4       = 61327,
        NECRO_TALENT_ICY_TALONS_R5       = 61328,
        NECRO_TALENT_WANDERING_PLAGUE_R1 = 61329,
        NECRO_TALENT_WANDERING_PLAGUE_R2 = 61330,
        NECRO_HELPER_METASTASIS          = 61342,   // T2d hidden helper spells
        NECRO_HELPER_ICY_TALONS          = 61343,
        NECRO_HELPER_ZOMBIFICATION       = 61344,
        NECRO_HELPER_BUTCHERY            = 61345,
        NECRO_HELPER_SHADOWSKIN_GHOUL    = 61346,
        NECRO_HELPER_SHADOWSKIN_LICH     = 61347,
        NECRO_HELPER_SHADOWSKIN_BONE     = 61348,
        NECRO_HELPER_PHANTOM_ARMOR       = 61349,
        NECRO_HELPER_WANDERING_PLAGUE    = 61350,
        // Plague fidelity pass (A.9/A.5): Desecration's healing reduction,
        // Disease Cloud's area damage and its 8 s area DoT.
        NECRO_HELPER_DESECRATION_HEAL    = 61097,
        NECRO_HELPER_DISEASE_CLOUD_DOT   = 61098,
        NECRO_HELPER_DISEASE_CLOUD_BURST = 61099,
        NECRO_SPELL_BONE_ARMOR           = 61015,   // armor buffs are mutually exclusive
        NECRO_SPELL_CANNIBALIZE_AURA     = 20578,   // vanilla Cannibalize regen aura
        NECRO_SPELL_DEATH_COIL_WARLOCK   = 6789,    // shared Warlock spell; no longer learned
    };

    // Base shield count of Bone Armor; Shadowskin adds 2 more per rank (A101).
    uint32 const NECRO_BONE_ARMOR_BASE_CHARGES = 4;

    // Corpse Bag items (server-side item_template; see the slice-3c SQL)
    enum NecromancerItemIds
    {
        NECRO_ITEM_LUMP_OF_FLESH    = 63100,
        NECRO_ITEM_PILE_OF_BONES    = 63101,
        NECRO_ITEM_ECTOPLASM        = 63102,
        NECRO_ITEM_BANSHEE_ESSENCE  = 63103,
    };

    // creature_template entries summoned by the Raise spells (vanilla undead
    // models; visuals/tuning are placeholders, see the design doc)
    enum NecromancerMinionEntries
    {
        NECRO_CREATURE_GHOUL       = 846,     // Ghoul
        NECRO_CREATURE_SKELETON    = 6412,    // Skeleton
        NECRO_CREATURE_ZOMBIE      = 1501,    // Mindless Zombie
        NECRO_CREATURE_SHADE       = 7370,    // Restless Shade
        NECRO_CREATURE_BANSHEE     = 10463,   // Shrieking Banshee
        NECRO_CREATURE_WRAITH      = 1800,    // Cold Wraith
        NECRO_CREATURE_BLOODMAGE   = 8526,    // Dark Caster
        NECRO_CREATURE_ABOMINATION = 8545,    // Abomination
        NECRO_CREATURE_WIGHT       = 11621,   // Spectral Corpse
    };

    // Module-private character_variables marker used by the T2e migration
    // (data/sql/character/20261022160000_char.sql).  PlayerVariables is an
    // open enum-to-string map, so the module can own a high id without a core
    // change.
    constexpr uint32 NECRO_VARIABLE_T2E_ARMOR_CLEANUP = 1001;

    // Trainers now teach the class (one in Orgrimmar, one in Stormwind; see
    // data/sql/world/20261019200000_world.sql).  The module only cleans up
    // the legacy auto-learned shared Warlock Death Coil (6789); the class's
    // own Death Coil (61074) replaces it.
    void CleanupLegacySpells(Player* player)
    {
        if (!player || player->GetClass() != 10)
            return;

        if (player->HasSpell(NECRO_SPELL_DEATH_COIL) &&
                player->HasSpell(NECRO_SPELL_DEATH_COIL_WARLOCK))
            player->RemoveSpell(NECRO_SPELL_DEATH_COIL_WARLOCK, false, false);
    }

    // T2e: the three armor/weapon passives used to be trainer-taught talent
    // shortcuts.  The character migration marks characters that still hold
    // them; remove them with RemoveSpell so OnForgotSpell clears the granted
    // skill lines and auto-unequips gear that no longer passes CanUseItem,
    // then make sure one free talent reset is available for the Blood tree.
    void CleanupLegacyArmorPassives(Player* player)
    {
        if (!player || player->GetClass() != 10)
            return;

        auto marker = player->GetPlayerVariable(
            static_cast<PlayerVariables>(NECRO_VARIABLE_T2E_ARMOR_CLEANUP));
        if (!marker || marker.value() != "1")
            return;

        uint32 const armorPassives[] = {
            NECRO_SPELL_NECRO_KNIGHT,
            NECRO_SPELL_WILL_OF_THE_DEATH_KNIGHT,
            NECRO_SPELL_GRIM_REAPER,
        };

        bool removed = false;
        for (uint32 spellId : armorPassives)
        {
            if (!player->HasSpell(spellId))
                continue;

            player->RemoveSpell(spellId, false, false);
            removed = true;
        }

        if (removed)
        {
            int freeResets = 0;
            if (auto free = player->GetPlayerVariable(
                    PlayerVariables::FreeTalentResets))
            {
                try
                {
                    freeResets = std::stoi(free.value());
                }
                catch (...)
                {
                    freeResets = 0;
                }
            }

            if (freeResets < 1)
                player->SetPlayerVariable(
                    PlayerVariables::FreeTalentResets, "1");
        }

        player->SetPlayerVariable(
            static_cast<PlayerVariables>(NECRO_VARIABLE_T2E_ARMOR_CLEANUP),
            "done");
    }

    // ------------------------------------------------------------------
    // T2a talent helpers (stat/defense passives)
    // ------------------------------------------------------------------

    int GetDeathMarchRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_DEATH_MARCH_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_DEATH_MARCH_R1))
            return 1;
        return 0;
    }

    int GetTerminalRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_TERMINAL_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_TERMINAL_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_TERMINAL_R1))
            return 1;
        return 0;
    }

    int GetTwoHandedRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_TWO_HANDED_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_TWO_HANDED_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_TWO_HANDED_R1))
            return 1;
        return 0;
    }

    int GetWitheringWorldRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_WITHERING_WORLD_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_WITHERING_WORLD_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_WITHERING_WORLD_R1))
            return 1;
        return 0;
    }

    int GetImprovedCrippleRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_IMPROVED_CRIPPLE_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_IMPROVED_CRIPPLE_R1))
            return 1;
        return 0;
    }

    // ------------------------------------------------------------------
    // T2c talent helpers (minion/pet passives)
    // ------------------------------------------------------------------

    bool IsMinionEntry(uint32 entry);           // defined in the minion section
    uint32 GetActiveMinionCount(Unit* caster);  // defined in the minion section

    int GetRunningDeadRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_RUNNING_DEAD_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_RUNNING_DEAD_R1))
            return 1;
        return 0;
    }

    int GetUnnaturalLifeRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_UNNATURAL_LIFE_R5))
            return 5;
        if (player->HasSpell(NECRO_TALENT_UNNATURAL_LIFE_R4))
            return 4;
        if (player->HasSpell(NECRO_TALENT_UNNATURAL_LIFE_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_UNNATURAL_LIFE_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_UNNATURAL_LIFE_R1))
            return 1;
        return 0;
    }

    int GetSolitudeRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_SOLITUDE_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_SOLITUDE_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_SOLITUDE_R1))
            return 1;
        return 0;
    }

    int GetGraverobbingRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_GRAVEROBBING_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_GRAVEROBBING_R1))
            return 1;
        return 0;
    }

    int GetUnholyPowerRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_UNHOLY_POWER_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_UNHOLY_POWER_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_UNHOLY_POWER_R1))
            return 1;
        return 0;
    }

    int GetPiercingFingersRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_PIERCING_FINGERS_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_PIERCING_FINGERS_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_PIERCING_FINGERS_R1))
            return 1;
        return 0;
    }

    int GetRetainedIntellectRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_RETAINED_INTELLECT_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_RETAINED_INTELLECT_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_RETAINED_INTELLECT_R1))
            return 1;
        return 0;
    }

    int GetTwistedBondRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_TWISTED_BOND_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_TWISTED_BOND_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_TWISTED_BOND_R1))
            return 1;
        return 0;
    }

    bool IsT2cTalentSpell(uint32 spellId)
    {
        return (spellId >= NECRO_TALENT_RUNNING_DEAD_R1 &&
                spellId <= NECRO_TALENT_RUNNING_DEAD_R2) ||
               (spellId >= NECRO_TALENT_UNNATURAL_LIFE_R1 &&
                spellId <= NECRO_TALENT_UNNATURAL_LIFE_R5) ||
               (spellId >= NECRO_TALENT_SOLITUDE_R1 &&
                spellId <= NECRO_TALENT_SOLITUDE_R3) ||
               spellId == NECRO_TALENT_GRAVEROBBING_R1 ||
               spellId == NECRO_TALENT_GRAVEROBBING_R2 ||
               (spellId >= NECRO_TALENT_UNHOLY_POWER_R1 &&
                spellId <= NECRO_TALENT_UNHOLY_POWER_R3) ||
               (spellId >= NECRO_TALENT_PIERCING_FINGERS_R1 &&
                spellId <= NECRO_TALENT_PIERCING_FINGERS_R3) ||
               spellId == NECRO_TALENT_UNDEAD_DOMINATION ||
               (spellId >= NECRO_TALENT_RETAINED_INTELLECT_R1 &&
                spellId <= NECRO_TALENT_RETAINED_INTELLECT_R3) ||
               (spellId >= NECRO_TALENT_TWISTED_BOND_R1 &&
                spellId <= NECRO_TALENT_TWISTED_BOND_R3);
    }

    // ------------------------------------------------------------------
    // T2d talent helpers (proc/conditional passives)
    // ------------------------------------------------------------------

    int GetShadowskinRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_SHADOWSKIN_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_SHADOWSKIN_R1))
            return 1;
        return 0;
    }

    int GetZombificationRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_ZOMBIFICATION_R5))
            return 5;
        if (player->HasSpell(NECRO_TALENT_ZOMBIFICATION_R4))
            return 4;
        if (player->HasSpell(NECRO_TALENT_ZOMBIFICATION_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_ZOMBIFICATION_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_ZOMBIFICATION_R1))
            return 1;
        return 0;
    }

    int GetBloodlettingRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_BLOODLETTING_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_BLOODLETTING_R1))
            return 1;
        return 0;
    }

    int GetButcheryRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_BUTCHERY_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_BUTCHERY_R1))
            return 1;
        return 0;
    }

    int GetPhantomArmorRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_PHANTOM_ARMOR_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_PHANTOM_ARMOR_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_PHANTOM_ARMOR_R1))
            return 1;
        return 0;
    }

    int GetEarlyGraveRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_EARLY_GRAVE_R5))
            return 5;
        if (player->HasSpell(NECRO_TALENT_EARLY_GRAVE_R4))
            return 4;
        if (player->HasSpell(NECRO_TALENT_EARLY_GRAVE_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_EARLY_GRAVE_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_EARLY_GRAVE_R1))
            return 1;
        return 0;
    }

    int GetMetastasisRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_METASTASIS_R5))
            return 5;
        if (player->HasSpell(NECRO_TALENT_METASTASIS_R4))
            return 4;
        if (player->HasSpell(NECRO_TALENT_METASTASIS_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_METASTASIS_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_METASTASIS_R1))
            return 1;
        return 0;
    }

    int GetDeathsEmbraceRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_DEATHS_EMBRACE_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_DEATHS_EMBRACE_R1))
            return 1;
        return 0;
    }

    int GetIcyTalonsRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_ICY_TALONS_R5))
            return 5;
        if (player->HasSpell(NECRO_TALENT_ICY_TALONS_R4))
            return 4;
        if (player->HasSpell(NECRO_TALENT_ICY_TALONS_R3))
            return 3;
        if (player->HasSpell(NECRO_TALENT_ICY_TALONS_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_ICY_TALONS_R1))
            return 1;
        return 0;
    }

    int GetWanderingPlagueRank(Player* player)
    {
        if (!player)
            return 0;
        if (player->HasSpell(NECRO_TALENT_WANDERING_PLAGUE_R2))
            return 2;
        if (player->HasSpell(NECRO_TALENT_WANDERING_PLAGUE_R1))
            return 1;
        return 0;
    }

    bool IsT2dTalentSpell(uint32 spellId)
    {
        return (spellId >= NECRO_TALENT_SHADOWSKIN_R1 &&
                spellId <= NECRO_TALENT_SHADOWSKIN_R2) ||
               (spellId >= NECRO_TALENT_ZOMBIFICATION_R1 &&
                spellId <= NECRO_TALENT_ZOMBIFICATION_R5) ||
               (spellId >= NECRO_TALENT_BLOODLETTING_R1 &&
                spellId <= NECRO_TALENT_BLOODLETTING_R2) ||
               (spellId >= NECRO_TALENT_BLOODGORGED_R1 &&
                spellId <= NECRO_TALENT_BLOODGORGED_R5) ||
               (spellId >= NECRO_TALENT_BUTCHERY_R1 &&
                spellId <= NECRO_TALENT_BUTCHERY_R2) ||
               (spellId >= NECRO_TALENT_PHANTOM_ARMOR_R1 &&
                spellId <= NECRO_TALENT_PHANTOM_ARMOR_R3) ||
               (spellId >= NECRO_TALENT_EARLY_GRAVE_R1 &&
                spellId <= NECRO_TALENT_EARLY_GRAVE_R5) ||
               (spellId >= NECRO_TALENT_METASTASIS_R1 &&
                spellId <= NECRO_TALENT_METASTASIS_R5) ||
               (spellId >= NECRO_TALENT_DEATHS_EMBRACE_R1 &&
                spellId <= NECRO_TALENT_DEATHS_EMBRACE_R2) ||
               (spellId >= NECRO_TALENT_ICY_TALONS_R1 &&
                spellId <= NECRO_TALENT_ICY_TALONS_R5) ||
               (spellId >= NECRO_TALENT_WANDERING_PLAGUE_R1 &&
                spellId <= NECRO_TALENT_WANDERING_PLAGUE_R2);
    }

    bool IsDeathsEmbracePeriodicSpell(uint32 spellId)
    {
        switch (spellId)
        {
            case NECRO_SPELL_CALL_OF_THE_GRAVE_R1:
            case NECRO_SPELL_CALL_OF_THE_GRAVE_R2:
            case NECRO_SPELL_CALL_OF_THE_GRAVE_R3:
            case NECRO_SPELL_DESECRATION_R1:
            case NECRO_SPELL_DESECRATION_R2:
            case NECRO_SPELL_DESECRATION_R3:
            case NECRO_SPELL_DISEASE_CLOUD:
            case NECRO_HELPER_DISEASE_CLOUD_DOT:
            case NECRO_SPELL_TOXIC_PLAGUE_R1:
            case NECRO_SPELL_TOXIC_PLAGUE_R2:
            case NECRO_SPELL_TOXIC_PLAGUE_R3:
            case NECRO_SPELL_OUTBREAK:
            case NECRO_SPELL_FROST_FEVER:
                return true;
            default:
                return false;
        }
    }

    void ApplyDeathsEmbrace(Player* player, Unit* target, float& damage)
    {
        if (!player || !target || damage <= 0.0f)
            return;

        int rank = GetDeathsEmbraceRank(player);
        if (!rank || target->GetHealthPercent() > 35.0f)
            return;

        damage *= 1.0f + 0.03f * float(rank);
    }

    void ApplyDeathsEmbrace(Player* player, Unit* target, int32& damage)
    {
        float value = float(damage);
        ApplyDeathsEmbrace(player, target, value);
        damage = int32(value);
    }

    void ApplyIcyTalonsHaste(Unit* caster)
    {
        Player* player = caster ? caster->ToPlayer() : nullptr;
        if (!player || player->GetClass() != 10)
            return;

        int rank = GetIcyTalonsRank(player);
        if (!rank)
            return;

        int32 basePoints = rank - 1;
        player->CastCustomSpell(player, NECRO_HELPER_ICY_TALONS,
                                &basePoints, nullptr, nullptr, true);
    }

    // Armor-spell conditional helpers (Shadowskin + Phantom Armor).  The
    // helpers use the armor buff's 30 min duration and are removed when the
    // armor is replaced or expires.
    void RemoveArmorTalentAuras(Player* player)
    {
        if (!player)
            return;

        player->RemoveAurasDueToSpell(NECRO_HELPER_SHADOWSKIN_GHOUL);
        player->RemoveAurasDueToSpell(NECRO_HELPER_SHADOWSKIN_LICH);
        player->RemoveAurasDueToSpell(NECRO_HELPER_SHADOWSKIN_BONE);
        player->RemoveAurasDueToSpell(NECRO_HELPER_PHANTOM_ARMOR);
    }

    void ApplyArmorTalentAuras(Player* player, uint32 armorSpellId)
    {
        if (!player || !armorSpellId)
            return;

        if (int rank = GetShadowskinRank(player))
        {
            uint32 helper = 0;
            int32 basePoints = 0;

            switch (armorSpellId)
            {
                case NECRO_SPELL_BONE_ARMOR:
                    // Bone Armor's bonus is extra shields
                    // (RefillBoneArmorCharges), not an armor helper.
                    break;
                case NECRO_SPELL_GHOUL_ARMOR:
                    // +25/+50% of the armor's 10 shadow resistance.
                    helper = NECRO_HELPER_SHADOWSKIN_GHOUL;
                    basePoints = rank == 1 ? 2 : 4;
                    break;
                case NECRO_SPELL_LICH_ARMOR:
                    // +50/+100% of the armor's 15% regen-while-casting.
                    helper = NECRO_HELPER_SHADOWSKIN_LICH;
                    basePoints = rank == 1 ? 7 : 14;
                    break;
                default:
                    break;
            }

            if (helper)
                player->CastCustomSpell(player, helper, &basePoints,
                                        nullptr, nullptr, true);
        }

        if (int rank = GetPhantomArmorRank(player))
        {
            static const int32 basePointsByRank[3] = { -4, -7, -11 };
            int32 basePoints = basePointsByRank[rank - 1];
            player->CastCustomSpell(player, NECRO_HELPER_PHANTOM_ARMOR,
                                    &basePoints, nullptr, nullptr, true);
        }
    }

    // Bone Armor's shield cap: the design's four shields plus Shadowskin's
    // +2/+4 charges.  The base count mirrors the spell's procCharges (A101).
    uint32 BoneArmorMaxCharges(Player* player)
    {
        return NECRO_BONE_ARMOR_BASE_CHARGES +
               2u * uint32(GetShadowskinRank(player));
    }

    void RefillBoneArmorCharges(Player* player)
    {
        if (!player)
            return;

        if (SpellAuraHolder* holder = player->GetSpellAuraHolder(NECRO_SPELL_BONE_ARMOR))
            holder->SetAuraCharges(BoneArmorMaxCharges(player));
    }

    // Clamps the shield count to the current cap (delta 0) or shifts it
    // (delta +/-2).  Losing a rank only lowers the cap; learning one refills
    // through RefillBoneArmorCharges.
    void AdjustBoneArmorCharges(Player* player, int delta)
    {
        if (!player)
            return;

        SpellAuraHolder* holder = player->GetSpellAuraHolder(NECRO_SPELL_BONE_ARMOR);
        if (!holder)
            return;

        int charges = int(holder->GetAuraCharges()) + delta;
        int maxCharges = int(BoneArmorMaxCharges(player));
        if (charges < 0)
            charges = 0;
        if (charges > maxCharges)
            charges = maxCharges;

        holder->SetAuraCharges(uint32(charges));
    }

    void RefreshArmorTalentAuras(Player* player)
    {
        if (!player)
            return;

        RemoveArmorTalentAuras(player);

        uint32 armor = 0;
        if (player->GetAura(NECRO_SPELL_BONE_ARMOR, EFFECT_INDEX_0))
            armor = NECRO_SPELL_BONE_ARMOR;
        else if (player->GetAura(NECRO_SPELL_GHOUL_ARMOR, EFFECT_INDEX_0))
            armor = NECRO_SPELL_GHOUL_ARMOR;
        else if (player->GetAura(NECRO_SPELL_LICH_ARMOR, EFFECT_INDEX_0))
            armor = NECRO_SPELL_LICH_ARMOR;

        if (armor)
            ApplyArmorTalentAuras(player, armor);
    }

    std::unordered_map<uint64, uint32> sZombificationTimers;

    void UpdateZombification(Player* player)
    {
        if (!player)
            return;

        int rank = GetZombificationRank(player);
        if (!rank)
        {
            if (player->HasAura(NECRO_HELPER_ZOMBIFICATION))
                player->RemoveAurasDueToSpell(NECRO_HELPER_ZOMBIFICATION);
            return;
        }

        int32 strength = int32(float(player->GetStat(STAT_INTELLECT)) *
                               0.05f * float(rank));
        if (strength < 0)
            strength = 0;

        Aura* aura = player->GetAura(NECRO_HELPER_ZOMBIFICATION, EFFECT_INDEX_0);
        if (aura && aura->GetModifier()->m_amount == strength)
            return;

        player->RemoveAurasDueToSpell(NECRO_HELPER_ZOMBIFICATION);
        if (strength > 0)
        {
            int32 basePoints = strength - 1;
            player->CastCustomSpell(player, NECRO_HELPER_ZOMBIFICATION,
                                    &basePoints, nullptr, nullptr, true);
        }
    }

    bool IsCasterMinion(uint32 entry)
    {
        return entry == NECRO_CREATURE_WRAITH || entry == NECRO_CREATURE_BLOODMAGE;
    }

    void ApplyGraverobbing(Player* player)
    {
        if (!player || player->GetClass() != 10)
            return;

        int rank = GetGraverobbingRank(player);
        if (!rank)
            return;

        int32 basePoints = rank * 4 - 1;    // +4% / +8% (aura value - 1)
        player->CastCustomSpell(player, NECRO_HELPER_GRAVEROBBING,
                                &basePoints, &basePoints, &basePoints, true);
    }

    void TryApplyUndeadDomination(Player* player)
    {
        if (!player || player->GetClass() != 10)
            return;
        if (!player->HasSpell(NECRO_TALENT_UNDEAD_DOMINATION))
            return;
        if (player->HasAura(NECRO_HELPER_UNDEAD_DOMINATION) ||
                player->HasAura(NECRO_HELPER_UNDEAD_DOMINATION_CD))
            return;

        player->CastSpell(player, NECRO_HELPER_UNDEAD_DOMINATION, true);
    }

    void ConsumeUndeadDomination(Player* player)
    {
        if (!player || !player->HasAura(NECRO_HELPER_UNDEAD_DOMINATION))
            return;

        player->RemoveAurasDueToSpell(NECRO_HELPER_UNDEAD_DOMINATION);
        player->CastSpell(player, NECRO_HELPER_UNDEAD_DOMINATION_CD, true);
    }

    void ApplyTwistedBondMinionBuff(Player* player, int rank)
    {
        if (!player || !rank)
            return;

        static const int32 basePointsByRank[3] = { 2, 5, 9 };   // +3/6/10%
        int32 basePoints = basePointsByRank[rank - 1];

        static const uint32 minionEntries[] =
        {
            NECRO_CREATURE_GHOUL,
            NECRO_CREATURE_SKELETON,
            NECRO_CREATURE_ZOMBIE,
            NECRO_CREATURE_SHADE,
            NECRO_CREATURE_BANSHEE,
            NECRO_CREATURE_WRAITH,
            NECRO_CREATURE_BLOODMAGE,
            NECRO_CREATURE_ABOMINATION,
            NECRO_CREATURE_WIGHT,
        };

        for (uint32 entry : minionEntries)
            if (Pet* minion = player->FindGuardianWithEntry(entry))
                minion->CastCustomSpell(minion, NECRO_HELPER_TWISTED_BOND_MINION,
                                        &basePoints, nullptr, nullptr, true);

        if (Pet* pet = player->GetPet())
            if (pet->IsAlive() && IsMinionEntry(pet->GetEntry()))
                pet->CastCustomSpell(pet, NECRO_HELPER_TWISTED_BOND_MINION,
                                     &basePoints, nullptr, nullptr, true);
    }

    void ApplyTwistedBondPlayerBuff(Player* player, int rank)
    {
        if (!player || !rank)
            return;

        static const int32 basePointsByRank[3] = { 2, 5, 9 };   // +3/6/10%
        int32 basePoints = basePointsByRank[rank - 1];
        player->CastCustomSpell(player, NECRO_HELPER_TWISTED_BOND_PLAYER,
                                &basePoints, nullptr, nullptr, true);
    }

    // Applies the persistent T2c minion auras.  The values are snapshots of
    // the owner's stats at summon/refresh time (a placeholder: the design has
    // no dynamic-update rule).
    void ApplyMinionTalentAuras(Player* player, Pet* minion)
    {
        if (!player || player->GetClass() != 10 || !minion ||
                !IsMinionEntry(minion->GetEntry()))
            return;

        static const uint32 helperAuras[] =
        {
            NECRO_HELPER_RUNNING_DEAD,
            NECRO_HELPER_UNNATURAL_LIFE,
            NECRO_HELPER_PIERCING_MELEE,
            NECRO_HELPER_PIERCING_CASTER,
            NECRO_HELPER_RETAINED_INTELLECT,
            NECRO_HELPER_TWISTED_BOND_PROC,
        };
        for (uint32 auraId : helperAuras)
            minion->RemoveAurasDueToSpell(auraId);

        if (int rank = GetRunningDeadRank(player))
        {
            int32 basePoints = rank * 5 - 1;    // +5% / +10%
            minion->CastCustomSpell(minion, NECRO_HELPER_RUNNING_DEAD,
                                    &basePoints, nullptr, nullptr, true);
        }

        if (int rank = GetUnnaturalLifeRank(player))
        {
            uint32 stamina = uint32(player->GetStat(STAT_STAMINA) *
                                    float(rank * 10) / 100.0f);
            if (stamina)
            {
                int32 basePoints = int32(stamina) - 1;
                minion->CastCustomSpell(minion, NECRO_HELPER_UNNATURAL_LIFE,
                                        &basePoints, nullptr, nullptr, true);
            }
        }

        if (int rank = GetPiercingFingersRank(player))
        {
            bool tethered = minion->getPetType() == SUMMON_PET;
            bool caster = IsCasterMinion(minion->GetEntry());

            int meleeHit = rank;
            int meleeCrit = rank;
            int spellHit = rank;
            int spellCrit = rank;

            if (tethered)
            {
                float inheritance = 0.30f * float(rank);
                int hit = int(player->m_modSpellHitChance * inheritance);
                int crit = int(player->GetSpellCritPercent(SPELL_SCHOOL_SHADOW) *
                               inheritance);
                meleeHit += hit;
                spellHit += hit;
                meleeCrit += crit;
                spellCrit += crit;
            }

            if (caster || tethered)
            {
                int32 hitPoints = spellHit - 1;
                int32 critPoints = spellCrit - 1;
                minion->CastCustomSpell(minion, NECRO_HELPER_PIERCING_CASTER,
                                        &hitPoints, &critPoints, nullptr, true);
            }
            if (!caster || tethered)
            {
                int32 hitPoints = meleeHit - 1;
                int32 critPoints = meleeCrit - 1;
                minion->CastCustomSpell(minion, NECRO_HELPER_PIERCING_MELEE,
                                        &hitPoints, &critPoints, nullptr, true);
            }
        }

        if (int rank = GetRetainedIntellectRank(player))
        {
            uint32 intellect = uint32(player->GetStat(STAT_INTELLECT) *
                                      float(rank * 10) / 100.0f);
            int32 intellectPoints = int32(intellect) - 1;
            int32 regenPoints = rank * 5 - 1;
            minion->CastCustomSpell(minion, NECRO_HELPER_RETAINED_INTELLECT,
                                    &intellectPoints, &regenPoints, nullptr, true);
        }

        if (GetTwistedBondRank(player))
            minion->CastSpell(minion, NECRO_HELPER_TWISTED_BOND_PROC, true);

        // Newly created pets have CanModifyStats() false in this core, so the
        // stat auras above only stored their modifiers.  Recompute now.
        minion->UpdateAllStats();
    }

    void RefreshAllMinionTalentAuras(Player* player)
    {
        if (!player || player->GetClass() != 10)
            return;

        if (Pet* pet = player->GetPet())
            ApplyMinionTalentAuras(player, pet);

        static const uint32 minionEntries[] =
        {
            NECRO_CREATURE_GHOUL,
            NECRO_CREATURE_SKELETON,
            NECRO_CREATURE_ZOMBIE,
            NECRO_CREATURE_SHADE,
            NECRO_CREATURE_BANSHEE,
            NECRO_CREATURE_WRAITH,
            NECRO_CREATURE_BLOODMAGE,
            NECRO_CREATURE_ABOMINATION,
            NECRO_CREATURE_WIGHT,
        };
        for (uint32 entry : minionEntries)
            if (Pet* guardian = player->FindGuardianWithEntry(entry))
                ApplyMinionTalentAuras(player, guardian);
    }

    bool IsWitheringWorldSpell(uint32 spellId)
    {
        return (spellId >= NECRO_SPELL_DESECRATION_R1 &&
                spellId <= NECRO_SPELL_DESECRATION_R3) ||
               spellId == NECRO_SPELL_DISEASE_CLOUD ||
               spellId == NECRO_HELPER_DISEASE_CLOUD_BURST ||
               spellId == NECRO_HELPER_DISEASE_CLOUD_DOT;
    }

    // Two-Handed Weapon Specialization's +1/2/3 weapon skill is applied here
    // (the rank spell has only three effect slots; its damage aura takes one).
    // The bonus is stored in the skill's permanent-bonus field, which is not
    // saved with character_skills, so it is reconciled on login as well.
    void RefreshTwoHandedSkillBonus(Player* player)
    {
        if (!player || player->GetClass() != 10)
            return;

        int16 target = int16(GetTwoHandedRank(player));
        static const uint16 skills[] = { SKILL_2H_SWORDS, SKILL_2H_MACES, SKILL_2H_AXES };
        for (uint16 skill : skills)
        {
            if (!player->GetSkillValue(skill))
                continue;
            int16 current = player->GetSkillBonusPermanent(skill);
            if (current != target)
                player->ModifySkillBonus(skill, target - current, true);
        }
    }

    // T2c: apply the minion/pet talent auras when a minion enters the world
    // (new summon, Tether conversion, saved-pet login).
    class NecromancerPetScript : public PetScript
    {
    public:
        NecromancerPetScript() : PetScript("mod_necromancer_pet") {}

        void OnPetAddToWorld(Pet* pet) override
        {
            if (!pet)
                return;
            Unit* owner = pet->GetOwner();
            Player* player = owner ? owner->ToPlayer() : nullptr;
            if (player && player->GetClass() == 10)
                ApplyMinionTalentAuras(player, pet);
        }
    };

    class NecromancerPlayerScript : public PlayerScript
    {
    public:
        NecromancerPlayerScript()
            : PlayerScript("mod_necromancer_player",
                           { PLAYERHOOK_ON_LOGIN, PLAYERHOOK_ON_LEARN_SPELL,
                             PLAYERHOOK_ON_FORGOT_SPELL, PLAYERHOOK_ON_UPDATE,
                             PLAYERHOOK_ON_LOGOUT })
        {
        }

        void OnLogin(Player* player) override
        {
            CleanupLegacySpells(player);
            CleanupLegacyArmorPassives(player);
            RefreshTwoHandedSkillBonus(player);

            TryApplyUndeadDomination(player);
            RefreshAllMinionTalentAuras(player);
            RefreshArmorTalentAuras(player);
            UpdateZombification(player);
        }

        void OnUpdate(Player* player, uint32 diff) override
        {
            if (!player || player->GetClass() != 10)
                return;
            if (!GetZombificationRank(player) &&
                    !player->HasAura(NECRO_HELPER_ZOMBIFICATION))
                return;

            uint32& timer =
                sZombificationTimers[player->GetObjectGuid().GetRawValue()];
            timer += diff;
            if (timer < 1000)
                return;
            timer = 0;

            UpdateZombification(player);
        }

        void OnLogout(Player* player) override
        {
            if (!player)
                return;
            sZombificationTimers.erase(
                player->GetObjectGuid().GetRawValue());
        }

        void OnLearnSpell(Player* player, uint32 spellId) override
        {
            if (!player || player->GetClass() != 10)
                return;

            if (IsT2cTalentSpell(spellId))
            {
                if (spellId == NECRO_TALENT_UNDEAD_DOMINATION)
                    TryApplyUndeadDomination(player);
                RefreshAllMinionTalentAuras(player);
            }

            if (IsT2dTalentSpell(spellId))
            {
                if (spellId == NECRO_TALENT_SHADOWSKIN_R1 ||
                        spellId == NECRO_TALENT_SHADOWSKIN_R2)
                    RefillBoneArmorCharges(player);
                RefreshArmorTalentAuras(player);
                UpdateZombification(player);
            }

            if (spellId == NECRO_SPELL_DEATH_COIL &&
                    player->HasSpell(NECRO_SPELL_DEATH_COIL_WARLOCK))
                player->RemoveSpell(NECRO_SPELL_DEATH_COIL_WARLOCK, false, false);

            // Armor/weapon progression (A.4 slots 9/17/25; talent shortcuts).
            // The passives' SPELL_EFFECT_PROFICIENCY sets the item-proficiency
            // mask, but CanUseItem also checks the actual skill value, so the
            // skill lines are granted here on learn (no SRCI class bit, which
            // would hand them out at character creation).
            switch (spellId)
            {
                case NECRO_SPELL_NECRO_KNIGHT:
                    GrantNecroKnightSkills(player);
                    break;
                case NECRO_SPELL_WILL_OF_THE_DEATH_KNIGHT:
                    GrantWillSkills(player);
                    break;
                case NECRO_SPELL_GRIM_REAPER:
                    GrantGrimReaperSkills(player);
                    break;
                case NECRO_TALENT_TWO_HANDED_R1:
                case NECRO_TALENT_TWO_HANDED_R2:
                case NECRO_TALENT_TWO_HANDED_R3:
                    RefreshTwoHandedSkillBonus(player);
                    break;
                default:
                    break;
            }
        }

        void OnForgotSpell(Player* player, uint32 spellId) override
        {
            if (!player || player->GetClass() != 10)
                return;

            if (IsT2cTalentSpell(spellId))
            {
                if (spellId == NECRO_TALENT_UNDEAD_DOMINATION)
                {
                    player->RemoveAurasDueToSpell(NECRO_HELPER_UNDEAD_DOMINATION);
                    player->RemoveAurasDueToSpell(NECRO_HELPER_UNDEAD_DOMINATION_CD);
                }
                RefreshAllMinionTalentAuras(player);
            }

            if (IsT2dTalentSpell(spellId))
            {
                if (!GetIcyTalonsRank(player))
                    player->RemoveAurasDueToSpell(NECRO_HELPER_ICY_TALONS);

                if (spellId == NECRO_TALENT_SHADOWSKIN_R1 ||
                        spellId == NECRO_TALENT_SHADOWSKIN_R2)
                    AdjustBoneArmorCharges(player, 0);

                RefreshArmorTalentAuras(player);
                UpdateZombification(player);
            }

            // Talent removal (or a GM unlearn) must invalidate the gear the
            // passive allowed.  Remove the skill lines and move any item that
            // no longer passes CanUseItem back to the bags (or mail it when
            // the bags are full).
            switch (spellId)
            {
                case NECRO_SPELL_NECRO_KNIGHT:
                    RemoveSkill(player, SKILL_LEATHER);
                    RemoveSkill(player, SKILL_MAIL);
                    UnequipInvalidArmor(player);
                    break;
                case NECRO_SPELL_WILL_OF_THE_DEATH_KNIGHT:
                    RemoveSkill(player, SKILL_PLATE_MAIL);
                    UnequipInvalidArmor(player);
                    break;
                case NECRO_SPELL_GRIM_REAPER:
                    RemoveSkill(player, SKILL_AXES);
                    RemoveSkill(player, SKILL_2H_AXES);
                    RemoveSkill(player, SKILL_MACES);
                    RemoveSkill(player, SKILL_2H_MACES);
                    RemoveSkill(player, SKILL_POLEARMS);
                    RemoveSkill(player, SKILL_SWORDS);
                    RemoveSkill(player, SKILL_2H_SWORDS);
                    player->SetCanDualWield(false);
                    player->AutoUnequipItemFromSlot(EQUIPMENT_SLOT_OFFHAND);
                    player->AutoUnequipWeaponsIfNeed();
                    break;
                case NECRO_TALENT_TWO_HANDED_R1:
                case NECRO_TALENT_TWO_HANDED_R2:
                case NECRO_TALENT_TWO_HANDED_R3:
                    RefreshTwoHandedSkillBonus(player);
                    break;
                case NECRO_TALENT_DEFLECTION_R1:
                case NECRO_TALENT_DEFLECTION_R2:
                case NECRO_TALENT_DEFLECTION_R3:
                    // Deflection's rank spell enables parry itself (the
                    // class has no vanilla parry passive); drop the ability
                    // only when the last rank is gone.
                    if (!player->HasSpell(NECRO_TALENT_DEFLECTION_R1) &&
                            !player->HasSpell(NECRO_TALENT_DEFLECTION_R2) &&
                            !player->HasSpell(NECRO_TALENT_DEFLECTION_R3))
                        player->SetCanParry(false);
                    break;
                default:
                    break;
            }
        }

    private:
        static void GrantSkill(Player* player, uint16 skill)
        {
            // HasSkill() can be true for a skill entry with value 0 (some
            // class skills are initialized empty); check the value instead.
            if (player->GetSkillValue(skill) == 0)
                player->SetSkill(skill, 1, player->GetSkillMaxForLevel());
        }

        static void RemoveSkill(Player* player, uint16 skill)
        {
            if (player->GetSkillValue(skill) != 0)
                player->SetSkill(skill, 0, 0);
        }

        static void UnequipInvalidArmor(Player* player)
        {
            for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
            {
                if (Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
                    if (player->CanUseItem(item) != EQUIP_ERR_OK)
                        player->AutoUnequipItemFromSlot(slot);
            }
        }

        static void GrantNecroKnightSkills(Player* player)
        {
            GrantSkill(player, SKILL_LEATHER);
            GrantSkill(player, SKILL_MAIL);
        }

        static void GrantWillSkills(Player* player)
        {
            GrantSkill(player, SKILL_PLATE_MAIL);
        }

        static void GrantGrimReaperSkills(Player* player)
        {
            GrantSkill(player, SKILL_AXES);
            GrantSkill(player, SKILL_2H_AXES);
            GrantSkill(player, SKILL_MACES);
            GrantSkill(player, SKILL_2H_MACES);
            GrantSkill(player, SKILL_POLEARMS);
            GrantSkill(player, SKILL_SWORDS);
            GrantSkill(player, SKILL_2H_SWORDS);
            player->SetCanDualWield(true);
        }
    };

    // Ghoul Armor (remaining spellbook batch): heals the Necromancer for 3%
    // of all damage they deal while the armor buff is active.  Player damage
    // can come from spells, melee or pets the player owns; the hook only
    // counts damage whose attacker is the player itself (design "damage you
    // deal"), and skips self-damage.
    class NecromancerGhoulArmorUnitScript : public UnitScript
    {
    public:
        NecromancerGhoulArmorUnitScript()
            : UnitScript("mod_necromancer_ghoul_armor", { UNITHOOK_ON_DAMAGE })
        {
        }

        void OnDamage(Unit* attacker, Unit* victim, uint32& damage) override
        {
            if (!attacker || !victim || attacker == victim || damage == 0)
                return;

            Player* player = attacker->ToPlayer();
            if (!player || player->GetClass() != 10)
                return;

            Aura* armor = player->GetAura(NECRO_SPELL_GHOUL_ARMOR, EFFECT_INDEX_0);
            if (!armor)
                return;

            uint32 heal = std::max<uint32>(1, damage * 3 / 100);
            player->DealHeal(player, heal, armor->GetSpellProto());
        }
    };

    // ------------------------------------------------------------------
    // Plague diseases (batch 2)
    // ------------------------------------------------------------------

    bool IsCallOfTheGrave(uint32 spellId)
    {
        return spellId == NECRO_SPELL_CALL_OF_THE_GRAVE_R1 ||
               spellId == NECRO_SPELL_CALL_OF_THE_GRAVE_R2 ||
               spellId == NECRO_SPELL_CALL_OF_THE_GRAVE_R3;
    }

    bool IsToxicPlague(uint32 spellId)
    {
        return spellId == NECRO_SPELL_TOXIC_PLAGUE_R1 ||
               spellId == NECRO_SPELL_TOXIC_PLAGUE_R2 ||
               spellId == NECRO_SPELL_TOXIC_PLAGUE_R3;
    }

    bool IsFrostFever(uint32 spellId)
    {
        return spellId == NECRO_SPELL_FROST_FEVER;
    }

    // The Necromancer's disease family, used by Disease Cloud.  The design
    // explodes "a victim of your Toxic Plague"; Grave Rot stays accepted as a
    // superset placeholder.  Frost Fever (Icy Touch) joins the Plague identity.
    bool IsNecromancerDisease(uint32 spellId)
    {
        return IsCallOfTheGrave(spellId) || IsToxicPlague(spellId) ||
               IsFrostFever(spellId);
    }

    bool HasCasterDisease(Unit* target, ObjectGuid const& casterGuid)
    {
        if (!target || !casterGuid)
            return false;

        for (auto const& itr : target->GetSpellAuraHolderMap())
        {
            SpellAuraHolder const* holder = itr.second;
            if (holder && holder->GetCasterGuid() == casterGuid && IsNecromancerDisease(holder->GetId()))
                return true;
        }

        return false;
    }

    // T2a: Death March's movement-slow resistance (fear is handled by the
    // rank spell's SPELL_AURA_MOD_MECHANIC_RESISTANCE aura) and Terminal's
    // disease dispel resistance.  Both are approximations of effects the
    // 1.12 aura set cannot express directly; see the T2a generator header.
    class NecromancerTalentUnitScript : public UnitScript
    {
    public:
        NecromancerTalentUnitScript()
            : UnitScript("mod_necromancer_t2a_t2b_t2c_talents",
                         { UNITHOOK_ON_AURA_APPLY, UNITHOOK_ON_AURA_REMOVE,
                           UNITHOOK_MODIFY_SPELL_DAMAGE_TAKEN,
                           UNITHOOK_ON_DAMAGE })
        {
        }

        // T2c: Solitude (all damage while no minion is active) and Unholy
        // Power (minion damage done).
        void OnDamage(Unit* attacker, Unit* victim, uint32& damage) override
        {
            if (!attacker || !victim || attacker == victim || damage == 0)
                return;

            if (Player* player = attacker->ToPlayer())
            {
                if (player->GetClass() != 10)
                    return;

                int rank = GetSolitudeRank(player);
                if (rank && GetActiveMinionCount(player) == 0)
                    damage = uint32(float(damage) * (1.0f + 0.02f * float(rank)));
                return;
            }

            Pet* minion = attacker->ToPet();
            if (!minion || !IsMinionEntry(minion->GetEntry()))
                return;

            Unit* owner = minion->GetOwner();
            Player* player = owner ? owner->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10)
                return;

            int rank = GetUnholyPowerRank(player);
            if (rank)
                damage = uint32(float(damage) * (1.0f + 0.05f * float(rank)));
        }

        void OnAuraApply(Unit* unit, Aura* aura) override
        {
            Player* player = unit ? unit->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10 || !aura)
                return;

            int rank = GetDeathMarchRank(player);
            if (!rank || aura->GetModifier()->m_auraname != SPELL_AURA_MOD_DECREASE_SPEED)
                return;

            // A resisted slow is removed immediately after it lands.  The
            // dispel-style "chance to resist" roll is the closest match for
            // a movement slow in this core.
            if (roll_chance_i(rank * 5))
                unit->RemoveAura(aura);
        }

        void OnAuraRemove(Unit* unit, Aura* aura) override
        {
            Player* player = unit ? unit->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10 || !aura)
                return;

            if (aura->GetRemoveMode() != AURA_REMOVE_BY_DISPEL)
                return;

            int rank = GetTerminalRank(player);
            if (!rank || !IsNecromancerDisease(aura->GetId()))
                return;

            static const uint8 chance[3] = { 7, 14, 20 };
            if (!roll_chance_i(chance[rank - 1]))
                return;

            // Re-apply the disease the dispel just removed.  This is the
            // closest analogue to a resisted dispel: the dispeller's effect
            // is consumed, but the disease stays on the target.  The cast is
            // delayed because a re-cast during the removal can be caught by
            // the same dispel and removed again.
            if (!unit->IsAlive())
                return;
            Unit* caster = aura->GetCaster();
            if (!caster || !caster->IsPlayer())
                return;
            Player* casterPlayer = caster->ToPlayer();
            ObjectGuid targetGuid = unit->GetObjectGuid();
            ObjectGuid casterGuid = casterPlayer->GetObjectGuid();
            uint32 spellId = aura->GetId();
            casterPlayer->m_Events.AddEvent(
                new LambdaBasicEvent<std::function<void()>>(
                    [targetGuid, casterGuid, spellId]()
                    {
                        Player* caster = ObjectAccessor::FindPlayer(casterGuid);
                        if (!caster || !caster->IsInWorld())
                            return;
                        Unit* target = ObjectAccessor::GetUnit(*caster, targetGuid);
                        if (target && target->IsAlive())
                            caster->CastSpell(target, spellId, true);
                    }),
                casterPlayer->m_Events.CalculateTime(150));
        }

        void ModifySpellDamageTaken(Unit* target, Unit* attacker,
                                    int32& damage, SpellEntry const* spellInfo) override
        {
            if (!attacker || !spellInfo || damage <= 0)
                return;

            Player* player = attacker->ToPlayer();
            if (!player || player->GetClass() != 10)
                return;

            if (IsWitheringWorldSpell(spellInfo->Id))
            {
                int rank = GetWitheringWorldRank(player);
                if (rank)
                    damage = int32(float(damage) * (1.0f + 0.05f * float(rank)));
            }

            if (IsDeathsEmbracePeriodicSpell(spellInfo->Id))
                ApplyDeathsEmbrace(player, target, damage);
        }
    };

    // Call of the Grave: a plague that festers on the victim; the final tick
    // deals triple damage.  Bound to the ranks via spell_template.script_name.
    struct spell_necromancer_call_of_the_grave : public AuraScript
    {
        void OnPeriodicDamageCalculateAmount(Aura* aura, float& amount) override
        {
            if (!aura || amount <= 0.0f || !IsCallOfTheGrave(aura->GetId()))
                return;

            uint32 ticks = aura->GetAuraTicks();
            uint32 maxTicks = aura->GetAuraMaxTicks();

            if (ticks && ticks == maxTicks)
            {
                amount *= 3.0f;
                return;
            }

            // Early Grave: a chance for the final triple-damage tick to
            // happen on an earlier tick as well.
            Player* player = aura->GetCaster() ? aura->GetCaster()->ToPlayer() : nullptr;
            int rank = GetEarlyGraveRank(player);
            if (rank && ticks && roll_chance_i(rank * 4))
                amount *= 3.0f;
        }
    };

    // Disease Cloud: explodes the caster's disease on the victim.  Best-effort
    // cast gate for now: when a unit target is provided (cast on an enemy) it
    // must carry one of the caster's diseases; ground casts cannot be verified
    // yet and stay allowed (placeholder, see the design doc).
    struct spell_necromancer_disease_cloud : public SpellScript
    {
        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            Unit* target = spell->m_targets.getUnitTarget();
            if (!target || target == spell->m_casterUnit)
                return SPELL_CAST_OK;

            if (!HasCasterDisease(target, spell->m_casterUnit->GetObjectGuid()))
                return SPELL_FAILED_TARGET_AURASTATE;

            return SPELL_CAST_OK;
        }

        // Explodes the victim's Toxic Plague (A.5): one tick of its damage to
        // every enemy within 8 yd, then the disease's total base damage as an
        // 8 s area DoT.  The dummy effect 0 carries the script; the damage
        // comes from the two hidden helper spells.
        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            Unit* target = spell->GetUnitTarget();
            Player* player = spell->m_casterUnit->ToPlayer();
            if (!target || !player || player->GetClass() != 10)
                return;

            static uint32 const toxicPlagues[] =
            {
                NECRO_SPELL_TOXIC_PLAGUE_R1,
                NECRO_SPELL_TOXIC_PLAGUE_R2,
                NECRO_SPELL_TOXIC_PLAGUE_R3,
            };

            Aura* plague = nullptr;
            for (uint32 id : toxicPlagues)
            {
                Aura* aura = target->GetAura(id, EFFECT_INDEX_0);
                if (aura && (!plague ||
                        aura->GetModifier()->m_amount > plague->GetModifier()->m_amount))
                    plague = aura;
            }
            if (!plague)
                return;

            int32 period = plague->GetModifier()->periodictime;
            if (period <= 0)
                period = 3000;

            int32 maxDuration = plague->GetAuraMaxDuration();
            if (maxDuration <= 0)
                maxDuration = 15000;

            int32 tick = plague->GetModifier()->m_amount;
            if (tick <= 0)
                return;

            int32 total = tick * (maxDuration / period);
            int32 burstPoints = tick - 1;
            int32 dotPoints = total / 4 - 1;    // 8 s at 2 s ticks

            std::list<Unit*> nearby;
            MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck check(target, player, 8.0f);
            MaNGOS::UnitListSearcher<MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck> searcher(nearby, check);
            Cell::VisitAllObjects(target, searcher, 8.0f);

            for (Unit* unit : nearby)
            {
                if (!unit || !unit->IsAlive())
                    continue;
                player->CastCustomSpell(unit, NECRO_HELPER_DISEASE_CLOUD_BURST,
                                        &burstPoints, nullptr, nullptr, true);
                player->CastCustomSpell(unit, NECRO_HELPER_DISEASE_CLOUD_DOT,
                                        &dotPoints, nullptr, nullptr, true);
            }
        }
    };

    // Desecration (A.9): an instant Shadow patch on the ground.  Its damage
    // wanes with the remaining duration, and every tick refreshes the healing
    // reduction on the victims standing in it.
    struct spell_necromancer_desecration : public AuraScript
    {
        void OnPeriodicDamageCalculateAmount(Aura* aura, float& amount) override
        {
            if (!aura || amount <= 0.0f)
                return;

            int32 maxDuration = aura->GetAuraMaxDuration();
            if (maxDuration > 0)
                amount *= 0.4f + 0.6f * (float(aura->GetAuraDuration()) / float(maxDuration));

            Unit* target = aura->GetTarget();
            Unit* caster = aura->GetCaster();
            if (target && caster && target->IsAlive())
                caster->CastSpell(target, NECRO_HELPER_DESECRATION_HEAL, true);
        }
    };

    // Improved Cripple: multiply the movement-slow aura value on the Cripple
    // spell.  Bound to 61023 via spell_template.script_name.
    struct spell_necromancer_cripple : public AuraScript
    {
        int32 OnAuraValueCalculate(Aura* /*aura*/, Unit* caster,
                                   Unit* /*target*/, SpellEntry const* spellProto,
                                   SpellEffectIndex effIdx, Item* /*castItem*/,
                                   int32 value) override
        {
            if (!caster || !spellProto || spellProto->Id != NECRO_SPELL_CRIPPLE)
                return value;

            Player* player = caster->ToPlayer();
            if (!player || player->GetClass() != 10)
                return value;

            int rank = GetImprovedCrippleRank(player);
            if (!rank)
                return value;

            if (spellProto->EffectApplyAuraName[effIdx] != SPELL_AURA_MOD_DECREASE_SPEED)
                return value;

            return int32(float(value) * (rank == 1 ? 1.15f : 1.30f));
        }
    };

    // Twisted Bond (T2c): the player's harmful spell crits buff the minions'
    // damage, and the minions' crits buff the player's spell damage for 8 s.
    // The player half is carried by the rank spell's proc aura; the minion
    // half by helper 61339, applied by the PetScript.
    struct spell_necromancer_twisted_bond_player : public AuraScript
    {
        std::optional<SpellProcEventTriggerCheck> OnCheckProc(
                Unit const* owner, Unit* /*victim*/, SpellAuraHolder* /*holder*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 procExtra, WeaponAttackType /*attType*/,
                bool /*isVictim*/) override
        {
            if (!(procExtra & PROC_EX_CRITICAL_HIT))
                return SPELL_PROC_TRIGGER_FAILED;

            Player* player = owner ? const_cast<Unit*>(owner)->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10 || !GetTwistedBondRank(player))
                return SPELL_PROC_TRIGGER_FAILED;

            return SPELL_PROC_TRIGGER_OK;
        }

        std::optional<SpellAuraProcResult> OnProc(
                Unit* owner, Unit* /*victim*/, uint32 /*amount*/,
                int32 /*originalAmount*/, Aura* /*triggeredByAura*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 /*procEx*/, uint32 /*cooldown*/) override
        {
            Player* player = owner ? owner->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10)
                return SPELL_AURA_PROC_CANT_TRIGGER;

            int rank = GetTwistedBondRank(player);
            if (!rank)
                return SPELL_AURA_PROC_CANT_TRIGGER;

            ApplyTwistedBondMinionBuff(player, rank);
            return SPELL_AURA_PROC_OK;
        }
    };

    struct spell_necromancer_twisted_bond_minion : public AuraScript
    {
        static Player* GetOwnerPlayer(Unit const* unit)
        {
            if (!unit)
                return nullptr;
            Unit* owner = const_cast<Unit*>(unit)->GetCharmerOrOwnerPlayerOrPlayerItself();
            return owner ? owner->ToPlayer() : nullptr;
        }

        std::optional<SpellProcEventTriggerCheck> OnCheckProc(
                Unit const* owner, Unit* /*victim*/, SpellAuraHolder* /*holder*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 procExtra, WeaponAttackType /*attType*/,
                bool /*isVictim*/) override
        {
            if (!(procExtra & PROC_EX_CRITICAL_HIT))
                return SPELL_PROC_TRIGGER_FAILED;

            Player* player = GetOwnerPlayer(owner);
            if (!player || player->GetClass() != 10 || !GetTwistedBondRank(player))
                return SPELL_PROC_TRIGGER_FAILED;

            return SPELL_PROC_TRIGGER_OK;
        }

        std::optional<SpellAuraProcResult> OnProc(
                Unit* owner, Unit* /*victim*/, uint32 /*amount*/,
                int32 /*originalAmount*/, Aura* /*triggeredByAura*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 /*procEx*/, uint32 /*cooldown*/) override
        {
            Player* player = GetOwnerPlayer(owner);
            if (!player || player->GetClass() != 10)
                return SPELL_AURA_PROC_CANT_TRIGGER;

            int rank = GetTwistedBondRank(player);
            if (!rank)
                return SPELL_AURA_PROC_CANT_TRIGGER;

            ApplyTwistedBondPlayerBuff(player, rank);
            return SPELL_AURA_PROC_OK;
        }
    };

    // Undead Domination (T2c): the 10 min cooldown marker re-arms the buff
    // when it expires, provided the talent is still learned.
    struct spell_necromancer_undead_domination : public AuraScript
    {
        void OnAfterApply(Aura* aura, bool apply) override
        {
            if (apply || !aura || aura->GetRemoveMode() != AURA_REMOVE_BY_EXPIRE)
                return;

            Unit* target = aura->GetTarget();
            Player* player = target ? target->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10)
                return;
            if (!player->HasSpell(NECRO_TALENT_UNDEAD_DOMINATION))
                return;

            player->CastSpell(player, NECRO_HELPER_UNDEAD_DOMINATION, true);
        }
    };

    // T2d: Frost Fever ticks keep Icy Talons' casting-speed buff up while an
    // enemy is affected by the disease.
    struct spell_necromancer_frost_fever : public AuraScript
    {
        void OnAfterApply(Aura* aura, bool apply) override
        {
            if (!aura || !apply || aura->GetId() != NECRO_SPELL_FROST_FEVER)
                return;

            ApplyIcyTalonsHaste(aura->GetCaster());
        }

        void OnPeriodicTick(Aura* aura) override
        {
            if (!aura || aura->GetId() != NECRO_SPELL_FROST_FEVER)
                return;

            ApplyIcyTalonsHaste(aura->GetCaster());
        }
    };

    // T2d: Metastasis - direct class damage has a chance to apply a stacking
    // debuff that increases the target's periodic damage taken by 3% (5
    // stacks).
    struct spell_necromancer_metastasis : public AuraScript
    {
        static bool IsTriggerSpell(uint32 spellId)
        {
            switch (spellId)
            {
                case NECRO_SPELL_PLAGUE_BOLT_R1:
                case NECRO_SPELL_PLAGUE_BOLT_R2:
                case NECRO_SPELL_PLAGUE_BOLT_R3:
                case NECRO_SPELL_REAP_R1:
                case NECRO_SPELL_REAP_R2:
                case NECRO_SPELL_DISEASE_CLOUD:
                case NECRO_SPELL_DEATH_COIL:
                case NECRO_SPELL_PLAGUE_STRIKE:
                case NECRO_SPELL_BLOODLET:
                case NECRO_SPELL_SOUL_STRIKE:
                case NECRO_SPELL_ICY_TOUCH:
                    return true;
                default:
                    return false;
            }
        }

        std::optional<SpellProcEventTriggerCheck> OnCheckProc(
                Unit const* owner, Unit* victim, SpellAuraHolder* /*holder*/,
                SpellEntry const* procSpell, uint32 /*procFlag*/,
                uint32 /*procExtra*/, WeaponAttackType /*attType*/,
                bool /*isVictim*/) override
        {
            if (!owner || !victim || !procSpell)
                return SPELL_PROC_TRIGGER_FAILED;

            Player* player = const_cast<Unit*>(owner)->ToPlayer();
            if (!player || player->GetClass() != 10 ||
                    !GetMetastasisRank(player))
                return SPELL_PROC_TRIGGER_FAILED;

            if (!IsTriggerSpell(procSpell->Id))
                return SPELL_PROC_TRIGGER_FAILED;

            return SPELL_PROC_TRIGGER_OK;
        }

        std::optional<SpellAuraProcResult> OnProc(
                Unit* owner, Unit* victim, uint32 /*amount*/,
                int32 /*originalAmount*/, Aura* /*triggeredByAura*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 /*procEx*/, uint32 /*cooldown*/) override
        {
            Player* player = owner ? owner->ToPlayer() : nullptr;
            if (!player || !victim || !victim->IsAlive() ||
                    !GetMetastasisRank(player))
                return SPELL_AURA_PROC_CANT_TRIGGER;

            player->CastSpell(victim, NECRO_HELPER_METASTASIS, true);
            return SPELL_AURA_PROC_OK;
        }
    };

    // T2d: Wandering Plague - disease ticks can splash 25/50% extra damage to
    // the victim and nearby enemies (chance = the caster's spell hit chance).
    struct spell_necromancer_wandering_plague : public AuraScript
    {
        std::optional<SpellProcEventTriggerCheck> OnCheckProc(
                Unit const* owner, Unit* victim, SpellAuraHolder* /*holder*/,
                SpellEntry const* procSpell, uint32 /*procFlag*/,
                uint32 /*procExtra*/, WeaponAttackType /*attType*/,
                bool /*isVictim*/) override
        {
            if (!owner || !victim || !procSpell)
                return SPELL_PROC_TRIGGER_FAILED;

            Player* player = const_cast<Unit*>(owner)->ToPlayer();
            if (!player || player->GetClass() != 10 ||
                    !GetWanderingPlagueRank(player))
                return SPELL_PROC_TRIGGER_FAILED;

            if (!IsNecromancerDisease(procSpell->Id))
                return SPELL_PROC_TRIGGER_FAILED;

            int32 chance = player->MagicSpellHitChance(victim, procSpell) / 100;
            if (chance < 0)
                chance = 0;
            if (chance > 100)
                chance = 100;

            return roll_chance_i(chance) ? SPELL_PROC_TRIGGER_OK
                                         : SPELL_PROC_TRIGGER_FAILED;
        }

        std::optional<SpellAuraProcResult> OnProc(
                Unit* owner, Unit* victim, uint32 amount,
                int32 /*originalAmount*/, Aura* /*triggeredByAura*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 /*procEx*/, uint32 /*cooldown*/) override
        {
            Player* player = owner ? owner->ToPlayer() : nullptr;
            int rank = GetWanderingPlagueRank(player);
            if (!player || !victim || !amount || !rank)
                return SPELL_AURA_PROC_CANT_TRIGGER;

            uint32 extra = amount * uint32(rank == 1 ? 25 : 50) / 100;
            if (!extra)
                return SPELL_AURA_PROC_CANT_TRIGGER;

            std::list<Unit*> nearby;
            MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck check(victim, player, 8.0f);
            MaNGOS::UnitListSearcher<MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck>
                searcher(nearby, check);
            Cell::VisitAllObjects(victim, searcher, 8.0f);

            bool cast = false;
            for (Unit* unit : nearby)
            {
                if (!unit || !unit->IsAlive())
                    continue;

                int32 basePoints = int32(extra) - 1;
                player->CastCustomSpell(unit, NECRO_HELPER_WANDERING_PLAGUE,
                                        &basePoints, nullptr, nullptr, true);
                cast = true;
            }

            return cast ? SPELL_AURA_PROC_OK : SPELL_AURA_PROC_CANT_TRIGGER;
        }
    };

    // T2d: Butchery - after a parry or a melee critical strike the next
    // swings are hasted by 7/15% (approximated as a 10 s buff).
    struct spell_necromancer_butchery : public AuraScript
    {
        std::optional<SpellProcEventTriggerCheck> OnCheckProc(
                Unit const* owner, Unit* /*victim*/, SpellAuraHolder* /*holder*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 procExtra, WeaponAttackType /*attType*/,
                bool /*isVictim*/) override
        {
            if (!(procExtra & (PROC_EX_CRITICAL_HIT | PROC_EX_PARRY)))
                return SPELL_PROC_TRIGGER_FAILED;

            Player* player = owner ? const_cast<Unit*>(owner)->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10 || !GetButcheryRank(player))
                return SPELL_PROC_TRIGGER_FAILED;

            return SPELL_PROC_TRIGGER_OK;
        }

        std::optional<SpellAuraProcResult> OnProc(
                Unit* owner, Unit* /*victim*/, uint32 /*amount*/,
                int32 /*originalAmount*/, Aura* /*triggeredByAura*/,
                SpellEntry const* /*procSpell*/, uint32 /*procFlag*/,
                uint32 /*procEx*/, uint32 /*cooldown*/) override
        {
            Player* player = owner ? owner->ToPlayer() : nullptr;
            int rank = GetButcheryRank(player);
            if (!player || !rank)
                return SPELL_AURA_PROC_CANT_TRIGGER;

            int32 basePoints = rank == 1 ? 6 : 14;   // +7% / +15%
            player->CastCustomSpell(player, NECRO_HELPER_BUTCHERY,
                                    &basePoints, nullptr, nullptr, true);
            return SPELL_AURA_PROC_OK;
        }
    };

    // ------------------------------------------------------------------
    // Minions (batch 3, slices 1-3: Raise tiers, Tether, minion control)
    // ------------------------------------------------------------------

    bool IsRaiseMinionSpell(uint32 spellId)
    {
        switch (spellId)
        {
            case NECRO_SPELL_RAISE_GHOUL:
            case NECRO_SPELL_RAISE_SKELETON:
            case NECRO_SPELL_RAISE_ZOMBIE:
            case NECRO_SPELL_RAISE_SHADE:
            case NECRO_SPELL_RAISE_BANSHEE:
            case NECRO_SPELL_RAISE_WRAITH:
            case NECRO_SPELL_RAISE_BLOODMAGE:
            case NECRO_SPELL_RAISE_ABOMINATION:
            case NECRO_SPELL_WIGHT_SUMMON:
                return true;
            default:
                return false;
        }
    }

    // The Death Pact effect of Sacrifice Minion is canceled when a new
    // minion is raised or tethered (design: "Canceled upon Raising or
    // Tethering a new minion").
    void RemoveDeathPactAuras(Unit* caster)
    {
        if (!caster)
            return;

        caster->RemoveAurasDueToSpell(NECRO_SPELL_DEATH_PACT_GHOUL);
        caster->RemoveAurasDueToSpell(NECRO_SPELL_DEATH_PACT_SKELETON);
        caster->RemoveAurasDueToSpell(NECRO_SPELL_DEATH_PACT_BANSHEE);
        caster->RemoveAurasDueToSpell(NECRO_SPELL_DEATH_PACT_SHADE);
        caster->RemoveAurasDueToSpell(NECRO_SPELL_DEATH_PACT_WRAITH);
        caster->RemoveAurasDueToSpell(NECRO_SPELL_DEATH_PACT_HULK);
        caster->RemoveAurasDueToSpell(NECRO_SPELL_DEATH_PACT_BLOODMAGE);
    }

    // ------------------------------------------------------------------
    // Corpse taxonomy (batch 3, slice 3c)
    //
    // The base categories come from creature_template.type (Humanoid, Undead,
    // Demon, Beast, Giant, Dragonkin are raiseable).  The sub-classes
    // (skeletal / spectral / zombie / ghoul / banshee / female humanoid)
    // have no data source and are classified best-effort: an optional
    // override table (`necromancer_corpse_class`, row = exact flags) wins,
    // otherwise the creature's model path (CreatureModelData.modelName
    // keywords) plus the character-model gender (CreatureDisplayInfoExtra)
    // are used.  See the design doc A.48-A.60 for the assumptions.
    // ------------------------------------------------------------------

    enum NecroCorpseFlags : uint8
    {
        NECRO_CORPSE_FLAG_SKELETAL = 0x01,
        NECRO_CORPSE_FLAG_SPECTRAL = 0x02,
        NECRO_CORPSE_FLAG_ZOMBIE   = 0x04,
        NECRO_CORPSE_FLAG_GHOUL    = 0x08,
        NECRO_CORPSE_FLAG_BANSHEE  = 0x10,
        NECRO_CORPSE_FLAG_FEMALE   = 0x20,
    };

    constexpr uint32 NECRO_RAISEABLE_TYPEMASK =
        (uint32(1) << (CREATURE_TYPE_HUMANOID - 1)) |
        (uint32(1) << (CREATURE_TYPE_UNDEAD - 1)) |
        (uint32(1) << (CREATURE_TYPE_DEMON - 1)) |
        (uint32(1) << (CREATURE_TYPE_BEAST - 1)) |
        (uint32(1) << (CREATURE_TYPE_GIANT - 1)) |
        (uint32(1) << (CREATURE_TYPE_DRAGONKIN - 1));

    constexpr float NECRO_RAISE_CORPSE_RANGE = 20.0f;   // design: 20 yd for the raises
    constexpr float NECRO_HARVEST_CORPSE_RANGE = 5.0f;  // cannibalize-style adjacency (design silent)

    std::unordered_map<uint32, uint8> sNecroCorpseOverrides;    // entry -> flags
    std::unordered_map<uint32, uint8> sNecroCorpseClassCache;   // entry -> flags

    bool HasKeyword(std::string const& path, char const* keyword)
    {
        return path.find(keyword) != std::string::npos;
    }

    uint8 GetCorpseClassFlags(uint32 entry)
    {
        auto cached = sNecroCorpseClassCache.find(entry);
        if (cached != sNecroCorpseClassCache.end())
            return cached->second;

        uint8 flags = 0;

        auto override = sNecroCorpseOverrides.find(entry);
        if (override != sNecroCorpseOverrides.end())
            flags = override->second;
        else if (CreatureInfo const* info = sObjectMgr.GetCreatureTemplate(entry))
        {
            if (CreatureDisplayInfoEntry const* display = info->display_id[0] ?
                    sCreatureDisplayInfoStore.LookupEntry(info->display_id[0]) : nullptr)
            {
                if (CreatureModelDataEntry const* model = sCreatureModelDataStore.LookupEntry(display->ModelId))
                {
                    std::string path = model->modelName ? model->modelName : "";
                    std::transform(path.begin(), path.end(), path.begin(), ::tolower);

                    if (HasKeyword(path, "skeleton") || HasKeyword(path, "skull") || HasKeyword(path, "bone"))
                        flags |= NECRO_CORPSE_FLAG_SKELETAL;
                    if (HasKeyword(path, "ghost") || HasKeyword(path, "spectre") || HasKeyword(path, "spectral") ||
                        HasKeyword(path, "spirit") || HasKeyword(path, "wraith") || HasKeyword(path, "shade") ||
                        HasKeyword(path, "phantom") || HasKeyword(path, "apparition") || HasKeyword(path, "banshee"))
                        flags |= NECRO_CORPSE_FLAG_SPECTRAL;
                    if (HasKeyword(path, "zombie"))
                        flags |= NECRO_CORPSE_FLAG_ZOMBIE;
                    if (HasKeyword(path, "ghoul"))
                        flags |= NECRO_CORPSE_FLAG_GHOUL;
                    if (HasKeyword(path, "banshee"))
                        flags |= NECRO_CORPSE_FLAG_BANSHEE | NECRO_CORPSE_FLAG_SPECTRAL;
                }

                // Character-model NPCs carry race/gender in CreatureDisplayInfoExtra
                if (info->type == CREATURE_TYPE_HUMANOID && display->ExtendedDisplayInfoID)
                {
                    if (CreatureDisplayInfoExtraEntry const* extra =
                            sCreatureDisplayInfoExtraStore.LookupEntry(display->ExtendedDisplayInfoID))
                        if (extra->Gender == 1)     // 0 male, 1 female
                            flags |= NECRO_CORPSE_FLAG_FEMALE;
                }
            }
        }

        sNecroCorpseClassCache[entry] = flags;
        return flags;
    }

    // Dead-corpse finder for the raiseable creature types (player corpses and
    // other creature types are never eligible; the design's raises target
    // "enemy corpses").
    class NecroCorpseCheck
    {
    public:
        NecroCorpseCheck(Unit const* fobj, float range) : i_fobj(fobj), i_range(range) {}

        WorldObject const& GetFocusObject() const { return *i_fobj; }

        bool operator()(Creature* u)
        {
            if (i_fobj->IsFriendlyTo(u) || u->IsAlive() || u->IsTaxiFlying() || !i_fobj->CanSeeInWorld(u))
                return false;
            if ((u->GetCreatureTypeMask() & NECRO_RAISEABLE_TYPEMASK) == 0)
                return false;
            return i_fobj->IsWithinDistInMap(u, i_range);
        }

        bool operator()(Player*) { return false; }
        template<class NOT_INTERESTED> bool operator()(NOT_INTERESTED*) { return false; }

    private:
        Unit const* i_fobj;
        float i_range;
    };

    Creature* FindRaiseCorpse(Unit* caster, float range)
    {
        if (!caster || !caster->IsInWorld())
            return nullptr;

        WorldObject* result = nullptr;
        NecroCorpseCheck check(caster, range);
        MaNGOS::WorldObjectSearcher<NecroCorpseCheck> searcher(result, check);

        Cell::VisitGridObjects(caster, searcher, range);

        return result ? result->ToCreature() : nullptr;
    }

    // Design corpse requirements per raise (see design doc A.6):
    //   Zombie: Humanoid or Zombie;  Ghoul: Humanoid or Ghoul;
    //   Skeleton: Humanoid or non-spectral Undead;
    //   Banshee: female Humanoid or Banshee;
    //   Shade/Wraith: Humanoid, Undead, Demon, Beast, Giant, Dragonkin;
    //   Bloodmage: Humanoid or non-spectral Undead;
    //   Abomination: Humanoid, Undead or Giant, three corpses.
    bool CorpseMatchesRaise(uint32 spellId, Creature* corpse)
    {
        if (!corpse || !corpse->GetCreatureInfo())
            return false;

        uint32 type = corpse->GetCreatureInfo()->type;
        uint8 flags = GetCorpseClassFlags(corpse->GetEntry());

        switch (spellId)
        {
            case NECRO_SPELL_RAISE_ZOMBIE:
                return type == CREATURE_TYPE_HUMANOID || (flags & NECRO_CORPSE_FLAG_ZOMBIE) != 0;
            case NECRO_SPELL_RAISE_GHOUL:
                return type == CREATURE_TYPE_HUMANOID || (flags & NECRO_CORPSE_FLAG_GHOUL) != 0;
            case NECRO_SPELL_RAISE_SKELETON:
            case NECRO_SPELL_RAISE_BLOODMAGE:
                return type == CREATURE_TYPE_HUMANOID ||
                       (type == CREATURE_TYPE_UNDEAD && (flags & NECRO_CORPSE_FLAG_SPECTRAL) == 0);
            case NECRO_SPELL_RAISE_BANSHEE:
                return (type == CREATURE_TYPE_HUMANOID && (flags & NECRO_CORPSE_FLAG_FEMALE) != 0) ||
                       (flags & NECRO_CORPSE_FLAG_BANSHEE) != 0;
            case NECRO_SPELL_RAISE_SHADE:
            case NECRO_SPELL_RAISE_WRAITH:
                return (NECRO_RAISEABLE_TYPEMASK & (uint32(1) << (type - 1))) != 0;
            case NECRO_SPELL_RAISE_ABOMINATION:
                return type == CREATURE_TYPE_HUMANOID || type == CREATURE_TYPE_UNDEAD ||
                       type == CREATURE_TYPE_GIANT;
            default:
                return false;
        }
    }

    uint32 CountRaiseCorpses(Unit* caster, uint32 spellId, float range)
    {
        if (!caster || !caster->IsInWorld())
            return 0;

        // collect the raiseable corpses first, then apply the per-spell rule
        // (the designer rules reuse the same base category set)
        uint32 count = 0;
        std::list<WorldObject*> corpses;
        NecroCorpseCheck check(caster, range);
        MaNGOS::WorldObjectListSearcher<NecroCorpseCheck> searcher(corpses, check);
        Cell::VisitGridObjects(caster, searcher, range);

        for (WorldObject* obj : corpses)
            if (Creature* corpse = obj->ToCreature())
                if (CorpseMatchesRaise(spellId, corpse))
                    ++count;

        return count;
    }

    uint32 GetRaiseCorpseCount(uint32 spellId)
    {
        return spellId == NECRO_SPELL_RAISE_ABOMINATION ? 3 : 1;
    }

    // Corpse Bag cost used when no matching corpse is nearby (design A.6):
    //   Zombie/Ghoul 1x Flesh; Skeleton 1x Bones; Shade/Wraith 1x Ectoplasm;
    //   Banshee 1x Essence; Bloodmage 1x Bones (placeholder - the design has
    //   no note for it); Abomination 3x Flesh.
    bool GetRaiseBagCost(uint32 spellId, uint32& itemId, uint32& count)
    {
        switch (spellId)
        {
            case NECRO_SPELL_RAISE_ZOMBIE:
            case NECRO_SPELL_RAISE_GHOUL:
                itemId = NECRO_ITEM_LUMP_OF_FLESH; count = 1; return true;
            case NECRO_SPELL_RAISE_SKELETON:
            case NECRO_SPELL_RAISE_BLOODMAGE:
                itemId = NECRO_ITEM_PILE_OF_BONES; count = 1; return true;
            case NECRO_SPELL_RAISE_SHADE:
            case NECRO_SPELL_RAISE_WRAITH:
                itemId = NECRO_ITEM_ECTOPLASM; count = 1; return true;
            case NECRO_SPELL_RAISE_BANSHEE:
                itemId = NECRO_ITEM_BANSHEE_ESSENCE; count = 1; return true;
            case NECRO_SPELL_RAISE_ABOMINATION:
                itemId = NECRO_ITEM_LUMP_OF_FLESH; count = 3; return true;
            default:
                return false;
        }
    }

    bool PlayerCanPayRaise(Player* player, uint32 spellId)
    {
        uint32 itemId, count;
        if (!player || !GetRaiseBagCost(spellId, itemId, count))
            return false;

        return player->HasItemCount(itemId, count);
    }

    // Harvest item yield (design A.6): Banshee Essence from female humanoids
    // and banshees (exclusively), Ectoplasm from spectral, Bones from
    // skeletal, Flesh from anything else corporeal.
    uint32 GetHarvestItemForCorpse(Creature* corpse)
    {
        uint32 type = corpse->GetCreatureInfo()->type;
        uint8 flags = GetCorpseClassFlags(corpse->GetEntry());

        if ((flags & NECRO_CORPSE_FLAG_BANSHEE) != 0 ||
                (type == CREATURE_TYPE_HUMANOID && (flags & NECRO_CORPSE_FLAG_FEMALE) != 0))
            return NECRO_ITEM_BANSHEE_ESSENCE;
        if (flags & NECRO_CORPSE_FLAG_SPECTRAL)
            return NECRO_ITEM_ECTOPLASM;
        if (flags & NECRO_CORPSE_FLAG_SKELETAL)
            return NECRO_ITEM_PILE_OF_BONES;

        return NECRO_ITEM_LUMP_OF_FLESH;
    }

    // Design: "Only 1 Wight or Abomination can be active at a time" - the new
    // one replaces the old (placeholder interpretation).
    void RemoveMinionOfEntry(Unit* caster, uint32 entry)
    {
        if (!caster)
            return;

        if (Pet* pet = caster->GetPet())
            if (pet->GetEntry() == entry)
                pet->Unsummon(PET_SAVE_AS_DELETED, caster);

        while (Pet* guardian = caster->FindGuardianWithEntry(entry))
            guardian->Unsummon(PET_SAVE_AS_DELETED, caster);
    }

    // Army of the Dead (design A.3 slot 21): each rank allows an additional
    // active minion.  Base cap 1 is a placeholder (the design gives no base
    // value); the ranks are trainer-taught at L20/L40 until talents exist.
    // "Only one minion can be Tethered" is inherent - a player has one pet.
    uint32 GetMinionCap(Player const* player)
    {
        if (player->HasSpell(NECRO_SPELL_ARMY_OF_THE_DEAD_R2))
            return 3;
        if (player->HasSpell(NECRO_SPELL_ARMY_OF_THE_DEAD_R1))
            return 2;
        return 1;
    }

    bool IsMinionEntry(uint32 entry)
    {
        switch (entry)
        {
            case NECRO_CREATURE_GHOUL:
            case NECRO_CREATURE_SKELETON:
            case NECRO_CREATURE_ZOMBIE:
            case NECRO_CREATURE_SHADE:
            case NECRO_CREATURE_BANSHEE:
            case NECRO_CREATURE_WRAITH:
            case NECRO_CREATURE_BLOODMAGE:
            case NECRO_CREATURE_ABOMINATION:
            case NECRO_CREATURE_WIGHT:
                return true;
            default:
                return false;
        }
    }

    // Active minions = the living summoned guardians of the class's minion
    // creatures + the tethered minion (a permanent pet).
    uint32 GetActiveMinionCount(Unit* caster)
    {
        static const uint32 minionEntries[] =
        {
            NECRO_CREATURE_GHOUL,
            NECRO_CREATURE_SKELETON,
            NECRO_CREATURE_ZOMBIE,
            NECRO_CREATURE_SHADE,
            NECRO_CREATURE_BANSHEE,
            NECRO_CREATURE_WRAITH,
            NECRO_CREATURE_BLOODMAGE,
            NECRO_CREATURE_ABOMINATION,
            NECRO_CREATURE_WIGHT,
        };

        uint32 count = 0;
        for (uint32 entry : minionEntries)
            count += caster->GetGuardianCountWithEntry(entry);

        if (Pet* pet = caster->GetPet())
            if (pet->IsAlive() && IsMinionEntry(pet->GetEntry()))
                ++count;

        return count;
    }

    // Guardian minions use the creature template's flat values; re-initialize
    // at the caster's level and scale like summoned pets (placeholder tuning,
    // see the design doc assumptions).  Fires right after the guardian is
    // created, before it is added to the map.
    struct spell_necromancer_raise_minion : public SpellScript
    {
        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            uint32 spellId = spell->m_spellInfo->Id;
            if (spellId == NECRO_SPELL_WIGHT_SUMMON)
                return SPELL_CAST_OK;   // internal triggered summon (no gate)

            Unit* caster = spell->m_casterUnit;

            // Army of the Dead: active-minion cap (slice 3b).  Recasting a
            // raise whose own minion is up just dismisses/replaces it (the
            // core toggles on the creature entry), so it never adds a minion
            // and stays allowed.
            if (Player* player = caster->ToPlayer())
            {
                uint32 entry = spell->m_spellInfo->EffectMiscValue[EFFECT_INDEX_0];
                if (!caster->GetGuardianCountWithEntry(entry))
                {
                    uint32 active = GetActiveMinionCount(caster);

                    // "Only 1 Wight or Abomination can be active at a time":
                    // the Abomination replaces an active Wight
                    if (spellId == NECRO_SPELL_RAISE_ABOMINATION)
                    {
                        active -= caster->GetGuardianCountWithEntry(NECRO_CREATURE_WIGHT);
                        if (Pet* pet = caster->GetPet())
                            if (pet->IsAlive() && pet->GetEntry() == NECRO_CREATURE_WIGHT && active)
                                --active;
                    }

                    if (active >= GetMinionCap(player))
                        return SPELL_FAILED_ALREADY_HAVE_SUMMON;
                }
            }

            // a matching corpse (or enough of them) satisfies the design gate
            if (CountRaiseCorpses(caster, spellId, NECRO_RAISE_CORPSE_RANGE) >= GetRaiseCorpseCount(spellId))
                return SPELL_CAST_OK;

            // otherwise the Corpse Bag items are consumed (see OnEffectExecute)
            if (Player* player = caster->ToPlayer())
                if (PlayerCanPayRaise(player, spellId))
                    return SPELL_CAST_OK;

            return SPELL_FAILED_NO_EDIBLE_CORPSES;
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell->m_casterUnit)
                return true;

            Unit* caster = spell->m_casterUnit;
            uint32 spellId = spell->m_spellInfo->Id;

            if (spellId == NECRO_SPELL_WIGHT_SUMMON)
                return true;

            // "Only 1 Wight or Abomination can be active at a time": the new
            // one replaces the old
            if (spellId == NECRO_SPELL_RAISE_ABOMINATION)
                RemoveMinionOfEntry(caster, NECRO_CREATURE_WIGHT);

            // Pay for the raise: a matching corpse nearby, or Corpse Bag
            // items (design A.6).  Placeholder: corpses are not consumed.
            if (CountRaiseCorpses(caster, spellId, NECRO_RAISE_CORPSE_RANGE) >= GetRaiseCorpseCount(spellId))
                return true;

            uint32 itemId, count;
            Player* player = caster->ToPlayer();
            if (!player || !GetRaiseBagCost(spellId, itemId, count) || !player->HasItemCount(itemId, count))
                return false;   // nothing left to pay with - abort the summon

            player->DestroyItemCount(itemId, count, true);
            return true;
        }

        void OnSummonBeforeAdd(Spell* spell, Pet* summon, uint32 /*summonIndex*/) const override
        {
            if (!spell || !summon || !spell->m_casterUnit || !IsRaiseMinionSpell(spell->m_spellInfo->Id))
                return;

            Unit* caster = spell->m_casterUnit;
            uint32 level = caster->GetLevel();
            if (!level)
                return;

            RemoveDeathPactAuras(caster);

            summon->InitStatsForLevel(level, caster);

            CreatureInfo const* info = summon->GetCreatureInfo();
            if (info && info->level_max)
            {
                // same as the protected Unit::SetCreateHealth (UNIT_FIELD_BASE_HEALTH)
                uint32 health = uint32(float(info->health_max) * float(level) / float(info->level_max));
                summon->SetUInt32Value(UNIT_FIELD_BASE_HEALTH, health);
            }

            float attackTime = float(summon->GetAttackTime(BASE_ATTACK));
            summon->SetBaseWeaponDamage(BASE_ATTACK, MINDAMAGE, float(level) * 1.15f * 1.05f * attackTime / 2000.0f);
            summon->SetBaseWeaponDamage(BASE_ATTACK, MAXDAMAGE, float(level) * 1.45f * 1.05f * attackTime / 2000.0f);

            summon->UpdateAllStats();
            summon->SetHealth(summon->GetMaxHealth());
        }

        void OnSuccessfulFinish(Spell* spell) const override
        {
            if (!spell || !spell->m_casterUnit || !spell->m_spellInfo)
                return;
            if (spell->m_spellInfo->Id == NECRO_SPELL_WIGHT_SUMMON)
                return;

            Player* player = spell->m_casterUnit->ToPlayer();
            if (!player || player->GetClass() != 10)
                return;

            ApplyGraverobbing(player);
            ConsumeUndeadDomination(player);
        }
    };

    // Tether: replaces the target raised guardian with a permanent,
    // controllable pet of the same creature entry (warlock-pet mechanics).
    struct spell_necromancer_tether : public SpellScript
    {
        static Pet* GetTetherableGuardian(Spell* spell)
        {
            if (!spell || !spell->m_casterUnit)
                return nullptr;

            Unit* target = spell->m_targets.getUnitTarget();
            Pet* guardian = target ? target->ToPet() : nullptr;
            if (!guardian || guardian->getPetType() != GUARDIAN_PET ||
                    guardian->GetOwnerGuid() != spell->m_casterUnit->GetObjectGuid())
                return nullptr;

            return guardian;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return GetTetherableGuardian(spell) ? SPELL_CAST_OK : SPELL_FAILED_BAD_TARGETS;
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0)
                return false;

            Pet* guardian = GetTetherableGuardian(spell);
            if (!guardian)
                return false;

            Unit* caster = spell->m_casterUnit;
            uint32 entry = guardian->GetEntry();

            ObjectGuid petGuid = caster->EffectSummonPet(spell->m_spellInfo->Id, entry, caster->GetLevel());
            if (petGuid)
            {
                RemoveDeathPactAuras(caster);
                guardian->Unsummon(PET_SAVE_AS_DELETED, caster);
            }

            return false;   // effect fully handled by the script
        }
    };

    // ------------------------------------------------------------------
    // Minion control (batch 3, slice 2: Sacrifice Minion, Harvest, Ghoul
    // Frenzy, minion actives)
    // ------------------------------------------------------------------

    // Per-minion-kind Death Pact effect (design values: 2% physical damage
    // done for Ghoul/Zombie, -2% physical damage taken for Skeleton, 2% mana
    // per 4 sec for Banshee, -5% threat for Shade, +2% melee/casting speed
    // for Wraith, +5% total health for Abomination/Wight, +2% spell damage
    // done for Bloodmage).  Unknown kinds fall back to the Ghoul effect.
    uint32 GetDeathPactAuraId(uint32 entry)
    {
        switch (entry)
        {
            case NECRO_CREATURE_SKELETON:    return NECRO_SPELL_DEATH_PACT_SKELETON;
            case NECRO_CREATURE_SHADE:       return NECRO_SPELL_DEATH_PACT_SHADE;
            case NECRO_CREATURE_BANSHEE:     return NECRO_SPELL_DEATH_PACT_BANSHEE;
            case NECRO_CREATURE_WRAITH:      return NECRO_SPELL_DEATH_PACT_WRAITH;
            case NECRO_CREATURE_BLOODMAGE:   return NECRO_SPELL_DEATH_PACT_BLOODMAGE;
            case NECRO_CREATURE_ABOMINATION:
            case NECRO_CREATURE_WIGHT:       return NECRO_SPELL_DEATH_PACT_HULK;
            case NECRO_CREATURE_GHOUL:
            case NECRO_CREATURE_ZOMBIE:
            default:                         return NECRO_SPELL_DEATH_PACT_GHOUL;
        }
    }

    // Sacrifice Minion: sacrifices the target minion (guardian or tethered
    // pet), healing the caster for (placeholder) the minion's maximum health
    // - doubled on a tethered minion - and granting a Death Pact effect that
    // depends on the minion's kind.  The effect is canceled by the next
    // Raise/Tether (see RemoveDeathPactAuras).
    struct spell_necromancer_sacrifice_minion : public SpellScript
    {
        static Pet* GetSacrificableMinion(Spell* spell)
        {
            if (!spell || !spell->m_casterUnit)
                return nullptr;

            Unit* target = spell->m_targets.getUnitTarget();
            Pet* minion = target ? target->ToPet() : nullptr;
            if (!minion || !minion->IsAlive())
                return nullptr;
            if (minion->GetOwnerGuid() != spell->m_casterUnit->GetObjectGuid())
                return nullptr;

            // raised guardians and tethered minions only
            if (minion->getPetType() != GUARDIAN_PET && minion->getPetType() != SUMMON_PET)
                return nullptr;

            return minion;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return GetSacrificableMinion(spell) ? SPELL_CAST_OK : SPELL_FAILED_BAD_TARGETS;
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0)
                return false;

            Pet* minion = GetSacrificableMinion(spell);
            if (!minion)
                return false;

            Unit* caster = spell->m_casterUnit;
            bool tethered = minion->getPetType() == SUMMON_PET;

            // Placeholder: heal equals the minion's maximum health, doubled
            // when it is the tethered minion (design's X is not defined).
            uint32 heal = minion->GetMaxHealth();
            if (tethered)
                heal *= 2;
            caster->DealHeal(caster, heal, spell->m_spellInfo);

            // Death Pact effect (per-minion-kind, placeholder tuning)
            caster->CastSpell(caster, GetDeathPactAuraId(minion->GetEntry()), true);

            minion->Unsummon(PET_SAVE_AS_DELETED, caster);

            return false;   // effect fully handled by the script
        }
    };

    // Harvest: channels for 3 sec over a raiseable corpse, storing it in the
    // Corpse Bag as one of the four items (design A.6).  Like the original
    // Cannibalize, the corpse is the dummy effect's target (needed so the
    // effect executes); the aura (61030) ticks once after 3 sec and the aura
    // script adds the item.  Placeholder: the corpse itself is not consumed.
    struct spell_necromancer_harvest : public SpellScript
    {
        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return FindRaiseCorpse(spell->m_casterUnit, NECRO_HARVEST_CORPSE_RANGE) ?
                SPELL_CAST_OK : SPELL_FAILED_NO_EDIBLE_CORPSES;
        }

        void OnTargetMapFilled(Spell* spell, SpellEffectIndex effIdx, uint32 /*targetMode*/,
                               std::list<Unit*>& targets) const override
        {
            // Like the original Cannibalize: the corpse is the dummy effect's
            // target, so the effect executes and the script can run.
            if (effIdx != EFFECT_INDEX_0 || !targets.empty() || !spell->m_casterUnit)
                return;

            if (Creature* corpse = FindRaiseCorpse(spell->m_casterUnit, NECRO_HARVEST_CORPSE_RANGE))
                targets.push_back(corpse);
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell->m_casterUnit)
                return false;

            spell->m_casterUnit->CastSpell(spell->m_casterUnit, NECRO_SPELL_HARVEST_AURA, true);
            return false;   // effect fully handled by the script
        }
    };

    // Harvest aura (61030): the 3-sec channel; its single periodic tick fires
    // at expiry (see Aura::Update's lost-last-tick guard) and stores the
    // corpse as the appropriate Corpse Bag item.
    struct spell_necromancer_harvest_aura : public AuraScript
    {
        void OnPeriodicTick(Aura* aura) override
        {
            if (!aura || aura->GetId() != NECRO_SPELL_HARVEST_AURA)
                return;

            Unit* caster = aura->GetCaster();
            Player* player = caster ? caster->ToPlayer() : nullptr;
            if (!player)
                return;

            Creature* corpse = FindRaiseCorpse(player, NECRO_HARVEST_CORPSE_RANGE);
            if (!corpse)
                return;     // corpse gone mid-channel - nothing is stored

            uint32 itemId = GetHarvestItemForCorpse(corpse);

            ItemPosCountVec dest;
            uint8 msg = player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, itemId, 1);
            if (msg != EQUIP_ERR_OK)
            {
                player->SendEquipError(InventoryResult(msg), nullptr, nullptr);
                return;
            }

            if (Item* item = player->StoreNewItem(dest, itemId, true))
                player->SendNewItem(item, 1, true, false);

            ApplyGraverobbing(player);
        }
    };

    // Raise Wight: transforms the target Zombie (1501) or Ghoul (846) minion
    // into a Wight (creature 11621), keeping a tethered minion tethered
    // (design A.6).  "Only 1 Wight or Abomination can be active at a time":
    // the transform replaces an active Abomination and vice versa (see the
    // raise script).
    struct spell_necromancer_raise_wight : public SpellScript
    {
        static Pet* GetTransformableMinion(Spell* spell)
        {
            if (!spell || !spell->m_casterUnit)
                return nullptr;

            Unit* target = spell->m_targets.getUnitTarget();
            Pet* minion = target ? target->ToPet() : nullptr;
            if (!minion || !minion->IsAlive())
                return nullptr;
            if (minion->GetOwnerGuid() != spell->m_casterUnit->GetObjectGuid())
                return nullptr;
            if (minion->getPetType() != GUARDIAN_PET && minion->getPetType() != SUMMON_PET)
                return nullptr;

            if (minion->GetEntry() != NECRO_CREATURE_ZOMBIE &&
                    minion->GetEntry() != NECRO_CREATURE_GHOUL)
                return nullptr;

            return minion;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return GetTransformableMinion(spell) ? SPELL_CAST_OK : SPELL_FAILED_BAD_TARGETS;
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0)
                return false;

            Pet* minion = GetTransformableMinion(spell);
            if (!minion)
                return false;

            Unit* caster = spell->m_casterUnit;
            bool tethered = minion->getPetType() == SUMMON_PET;

            // "Only 1 Wight or Abomination can be active at a time"
            RemoveMinionOfEntry(caster, NECRO_CREATURE_ABOMINATION);

            minion->Unsummon(PET_SAVE_AS_DELETED, caster);

            if (tethered)
                caster->EffectSummonPet(spell->m_spellInfo->Id, NECRO_CREATURE_WIGHT, caster->GetLevel());
            else
                caster->CastSpell(caster, NECRO_SPELL_WIGHT_SUMMON, true);

            return false;   // effect fully handled by the script
        }

        void OnSuccessfulFinish(Spell* spell) const override
        {
            if (!spell || !spell->m_casterUnit)
                return;

            Player* player = spell->m_casterUnit->ToPlayer();
            if (!player || player->GetClass() != 10)
                return;

            ApplyGraverobbing(player);
            ConsumeUndeadDomination(player);
        }
    };

    // ------------------------------------------------------------------
    // Corpse launcher (batch 3, slice 3b)
    // ------------------------------------------------------------------

    // Meat Catapult (L44, design A.6): launches a corpse from the Corpse Bag
    // at the target location (X-Y Shadow damage + a 2 sec stun in 3 yards,
    // 1.5 sec cast, 20 yd, 1 min cooldown - the client spell is a Thorium
    // Grenade clone).  Requires a Corpse Bag item of any kind and consumes
    // one on a completed cast.
    struct spell_necromancer_meat_catapult : public SpellScript
    {
        static uint32 FindCorpseBagItem(Player* player)
        {
            static const uint32 items[] =
            {
                NECRO_ITEM_LUMP_OF_FLESH,
                NECRO_ITEM_PILE_OF_BONES,
                NECRO_ITEM_ECTOPLASM,
                NECRO_ITEM_BANSHEE_ESSENCE,
            };

            for (uint32 itemId : items)
                if (player->HasItemCount(itemId, 1))
                    return itemId;

            return 0;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            Player* player = spell->m_casterUnit->ToPlayer();
            if (!player)
                return SPELL_CAST_OK;

            return FindCorpseBagItem(player) ? SPELL_CAST_OK : SPELL_FAILED_NO_EDIBLE_CORPSES;
        }

        void OnSuccessfulFinish(Spell* spell) const override
        {
            if (!spell || !spell->m_casterUnit)
                return;

            Player* player = spell->m_casterUnit->ToPlayer();
            if (!player)
                return;

            if (uint32 itemId = FindCorpseBagItem(player))
                player->DestroyItemCount(itemId, 1, true);
        }
    };

    // ------------------------------------------------------------------
    // Per-minion special abilities (batch 4, design A.7)
    // ------------------------------------------------------------------

    // Minion Cannibalize (pet ability of Zombie/Ghoul/Abomination/Wight):
    // like Harvest, the clone's dummy effect only runs once the corpse is
    // pushed as its target; the effect handler then applies the vanilla
    // Cannibalize aura (20578: 7% max health per 2 sec for 10 sec) to the
    // minion.  Design A.7: humanoid/undead corpses within 5 yd, 2 min CD.
    struct spell_necromancer_minion_cannibalize : public SpellScript
    {
        class CorpseChecker
        {
        public:
            CorpseChecker(Unit const* fobj, float range) : i_fobj(fobj), i_range(range) {}

            WorldObject const& GetFocusObject() const { return *i_fobj; }

            bool operator()(Creature* u)
            {
                if (i_fobj->IsFriendlyTo(u) || u->IsAlive() || u->IsTaxiFlying() || !i_fobj->CanSeeInWorld(u))
                    return false;
                CreatureInfo const* info = u->GetCreatureInfo();
                if (!info || (info->type != CREATURE_TYPE_HUMANOID && info->type != CREATURE_TYPE_UNDEAD))
                    return false;
                return i_fobj->IsWithinDistInMap(u, i_range);
            }

            bool operator()(Player*) { return false; }
            template<class NOT_INTERESTED> bool operator()(NOT_INTERESTED*) { return false; }

        private:
            Unit const* i_fobj;
            float i_range;
        };

        static Creature* FindCannibalizeCorpse(Unit* caster)
        {
            if (!caster || !caster->IsInWorld())
                return nullptr;

            WorldObject* result = nullptr;
            CorpseChecker check(caster, NECRO_HARVEST_CORPSE_RANGE);
            MaNGOS::WorldObjectSearcher<CorpseChecker> searcher(result, check);

            Cell::VisitGridObjects(caster, searcher, NECRO_HARVEST_CORPSE_RANGE);

            return result ? result->ToCreature() : nullptr;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return FindCannibalizeCorpse(spell->m_casterUnit) ?
                SPELL_CAST_OK : SPELL_FAILED_NO_EDIBLE_CORPSES;
        }

        void OnTargetMapFilled(Spell* spell, SpellEffectIndex effIdx, uint32 /*targetMode*/,
                               std::list<Unit*>& targets) const override
        {
            // like the original Cannibalize: the corpse is the dummy effect's
            // target, so the effect executes and the script can run
            if (effIdx != EFFECT_INDEX_0 || !targets.empty() || !spell->m_casterUnit)
                return;

            if (Creature* corpse = FindCannibalizeCorpse(spell->m_casterUnit))
                targets.push_back(corpse);
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell->m_casterUnit)
                return false;

            spell->m_casterUnit->CastSpell(spell->m_casterUnit, NECRO_SPELL_CANNIBALIZE_AURA, true);
            return false;   // the dummy effect is fully handled by the script
        }
    };

    // ------------------------------------------------------------------
    // Spell corrections (2026-10-19, design A.6-A.9 + A72)
    // ------------------------------------------------------------------

    // Plague Bolt (A.9): Nature damage that also infects the target with the
    // Toxic Plague disease (the matching rank) and deals 3% more direct
    // damage per disease already on the victim.
    struct spell_necromancer_plague_bolt : public SpellScript
    {
        static uint32 GetToxicPlagueId(uint32 spellId)
        {
            switch (spellId)
            {
                case NECRO_SPELL_PLAGUE_BOLT_R1: return NECRO_SPELL_TOXIC_PLAGUE_R1;
                case NECRO_SPELL_PLAGUE_BOLT_R2: return NECRO_SPELL_TOXIC_PLAGUE_R2;
                case NECRO_SPELL_PLAGUE_BOLT_R3: return NECRO_SPELL_TOXIC_PLAGUE_R3;
                case NECRO_SPELL_PLAGUE_STRIKE:  return NECRO_SPELL_TOXIC_PLAGUE_R1;
                default: return 0;
            }
        }

        void OnEffectDamageCalculate(Spell* spell, SpellEffectIndex effIdx, float& damage) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || damage <= 0.0f)
                return;

            Unit* target = spell->GetUnitTarget();
            if (!target)
                return;

            uint32 diseases = 0;
            for (auto const& itr : target->GetSpellAuraHolderMap())
            {
                SpellAuraHolder const* holder = itr.second;
                if (holder && !holder->IsDeleted() && holder->GetSpellProto() &&
                        holder->GetSpellProto()->Dispel == DISPEL_DISEASE)
                    ++diseases;
            }

            if (diseases)
                damage *= 1.0f + 0.03f * float(diseases);

            // Death's Embrace: Plague Bolt only (Plague Strike is a Blood
            // spell and is not in the talent's spell list).
            if (spell->m_spellInfo->Id != NECRO_SPELL_PLAGUE_STRIKE &&
                    spell->m_casterUnit)
            {
                if (Player* player = spell->m_casterUnit->ToPlayer())
                    ApplyDeathsEmbrace(player, target, damage);
            }
        }

        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            uint32 plagueId = GetToxicPlagueId(spell->m_spellInfo->Id);
            Unit* target = spell->GetUnitTarget();
            if (!plagueId || !target || !target->IsAlive())
                return;

            if (spell->m_spellInfo->Id == NECRO_SPELL_PLAGUE_STRIKE &&
                    (target->HasAura(NECRO_SPELL_TOXIC_PLAGUE_R2) ||
                     target->HasAura(NECRO_SPELL_TOXIC_PLAGUE_R3)))
                return;

            // only one rank of the disease at a time
            static const uint32 toxicPlagueRanks[] =
            {
                NECRO_SPELL_TOXIC_PLAGUE_R1,
                NECRO_SPELL_TOXIC_PLAGUE_R2,
                NECRO_SPELL_TOXIC_PLAGUE_R3,
            };
            for (uint32 rank : toxicPlagueRanks)
                if (rank != plagueId)
                    target->RemoveAurasDueToSpell(rank);

            spell->m_casterUnit->CastSpell(target, plagueId, true);
        }
    };

    struct spell_necromancer_plague_strike : public spell_necromancer_plague_bolt
    {
    };

    // Armor buffs (Bone Armor, Ghoul Armor, Lich Armor) are mutually
    // exclusive: the design treats them as one armor line.  The script is
    // bound to all three spells through spell_template.script_name.
    struct spell_necromancer_armor : public SpellScript, public AuraScript
    {
        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            static const uint32 armorSpells[] =
            {
                NECRO_SPELL_BONE_ARMOR,
                NECRO_SPELL_GHOUL_ARMOR,
                NECRO_SPELL_LICH_ARMOR,
            };

            for (uint32 id : armorSpells)
                if (id != spell->m_spellInfo->Id)
                    spell->m_casterUnit->RemoveAurasDueToSpell(id);
        }

        // T2d: Shadowskin's armor bonuses and Phantom Armor's damage
        // reduction are conditional on an Armor buff being active.
        void OnAfterApply(Aura* aura, bool apply) override
        {
            if (!aura)
                return;

            Unit* target = aura->GetTarget();
            Player* player = target ? target->ToPlayer() : nullptr;
            if (!player || player->GetClass() != 10)
                return;

            RemoveArmorTalentAuras(player);
            if (apply)
            {
                ApplyArmorTalentAuras(player, aura->GetId());
                // A fresh Bone Armor gets its full shield count, including
                // Shadowskin's extra charges.
                if (aura->GetId() == NECRO_SPELL_BONE_ARMOR)
                    RefillBoneArmorCharges(player);
            }
        }
    };

    // Bloodlet: takes one tick of the strongest disease the caster has on
    // the victim, deals that much Shadow damage and restores the same amount
    // of mana.  Placeholder: the strongest tick is read from the aura and the
    // disease's duration is shortened by one tick; the design's exact value
    // is undefined.
    struct spell_necromancer_bloodlet : public SpellScript
    {
        static Aura* FindStrongestDisease(Unit* caster, Unit* target)
        {
            if (!caster || !target)
                return nullptr;

            Aura* best = nullptr;
            int32 bestAmount = 0;
            for (auto const& itr : target->GetSpellAuraHolderMap())
            {
                SpellAuraHolder* holder = itr.second;
                if (!holder || holder->IsDeleted() || !holder->GetSpellProto())
                    continue;
                if (holder->GetSpellProto()->Dispel != DISPEL_DISEASE)
                    continue;
                if (holder->GetCasterGuid() != caster->GetObjectGuid())
                    continue;

                for (uint8 i = 0; i < MAX_EFFECT_INDEX; ++i)
                {
                    Aura* aura = holder->GetAuraByEffectIndex(SpellEffectIndex(i));
                    if (!aura || aura->GetModifier()->m_auraname != SPELL_AURA_PERIODIC_DAMAGE)
                        continue;
                    if (aura->GetModifier()->m_amount > bestAmount)
                    {
                        bestAmount = aura->GetModifier()->m_amount;
                        best = aura;
                    }
                }
            }

            return best;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            Unit* target = spell->m_targets.getUnitTarget();
            if (!target || !target->IsAlive() ||
                    !FindStrongestDisease(spell->m_casterUnit, target))
                return SPELL_FAILED_BAD_TARGETS;

            return SPELL_CAST_OK;
        }

        void OnEffectDamageCalculate(Spell* spell, SpellEffectIndex effIdx, float& damage) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            Aura* disease = FindStrongestDisease(spell->m_casterUnit, spell->GetUnitTarget());
            if (disease)
                damage = float(std::max<int32>(1, disease->GetModifier()->m_amount));
        }

        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit || spell->damage == 0)
                return;

            Aura* disease = FindStrongestDisease(spell->m_casterUnit, spell->GetUnitTarget());
            if (!disease)
                return;

            // "in exchange for stealing an equal amount of mana"; Bloodletting
            // increases the mana award by 10/20%.
            uint32 mana = spell->damage;
            if (Player* player = spell->m_casterUnit->ToPlayer())
            {
                int rank = GetBloodlettingRank(player);
                if (rank)
                    mana = mana * uint32(100 + 10 * rank) / 100;
            }

            spell->m_casterUnit->EnergizeBySpell(spell->m_casterUnit,
                    spell->m_spellInfo->Id, mana, POWER_MANA);

            // One tick of the disease is consumed by the transfer.
            SpellAuraHolder* holder = disease->GetHolder();
            if (holder)
            {
                int32 period = disease->GetModifier()->periodictime;
                if (period > 0)
                    holder->SetAuraDuration(std::max(0, holder->GetAuraDuration() - period));
            }
        }
    };

    // Embalm: reduces the damage received by the caster's tethered minion by
    // 10% for 1 min.  The aura itself is data (SPELL_AURA_MOD_DAMAGE_PERCENT_TAKEN);
    // the script only gates the target to the tethered minion.
    struct spell_necromancer_embalm : public SpellScript
    {
        static Pet* GetTetheredMinion(Spell* spell)
        {
            if (!spell || !spell->m_casterUnit)
                return nullptr;

            Unit* target = spell->m_targets.getUnitTarget();
            Pet* minion = target ? target->ToPet() : nullptr;
            if (!minion || !minion->IsAlive())
                return nullptr;
            if (minion->GetOwnerGuid() != spell->m_casterUnit->GetObjectGuid())
                return nullptr;
            if (minion->getPetType() != SUMMON_PET)
                return nullptr;

            return minion;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return GetTetheredMinion(spell) ? SPELL_CAST_OK : SPELL_FAILED_BAD_TARGETS;
        }
    };

    // Outbreak: channeled Shadow damage that refreshes the caster's diseases
    // on the victim and spreads them to up to 3 nearby enemies (design A.9).
    struct spell_necromancer_outbreak : public AuraScript
    {
        void OnPeriodicTick(Aura* aura) override
        {
            if (!aura || aura->GetId() != NECRO_SPELL_OUTBREAK ||
                    aura->GetEffIndex() != EFFECT_INDEX_0)
                return;

            Unit* caster = aura->GetCaster();
            Unit* target = aura->GetTarget();
            if (!caster || !target || !target->IsAlive())
                return;

            std::vector<uint32> diseaseIds;
            for (auto const& itr : target->GetSpellAuraHolderMap())
            {
                SpellAuraHolder* holder = itr.second;
                if (!holder || holder->IsDeleted() || !holder->GetSpellProto())
                    continue;
                if (holder->GetSpellProto()->Dispel != DISPEL_DISEASE)
                    continue;
                if (holder->GetCasterGuid() != caster->GetObjectGuid())
                    continue;

                diseaseIds.push_back(holder->GetId());
                holder->RefreshHolder();
            }

            if (diseaseIds.empty())
                return;

            std::list<Unit*> nearby;
            MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck check(target, caster, 8.0f);
            MaNGOS::UnitListSearcher<MaNGOS::AnyUnfriendlyUnitInObjectRangeCheck> searcher(nearby, check);
            Cell::VisitAllObjects(target, searcher, 8.0f);

            uint32 spread = 0;
            for (Unit* unit : nearby)
            {
                if (!unit || unit == target)
                    continue;
                if (spread >= 3)
                    break;

                for (uint32 diseaseId : diseaseIds)
                    caster->CastSpell(unit, diseaseId, true);
                ++spread;
            }
        }
    };

    // Reap (A.8): "Generates a high amount of threat" - the health-leech
    // effect only produces the normal damage threat, so an equal amount of
    // school threat is added on a hostile hit (placeholder magnitude).
    struct spell_necromancer_reap : public SpellScript
    {
        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            Unit* target = spell->GetUnitTarget();
            if (!target || !target->IsAlive() || !spell->m_casterUnit->IsHostileTo(target))
                return;

            // Death's Embrace: Reap is a health-leech effect (it does not go
            // through OnEffectDamageCalculate), so the low-health bonus is
            // added here with the matching extra lifesteal.
            uint32 extra = 0;
            if (Player* player = spell->m_casterUnit->ToPlayer())
            {
                int rank = GetDeathsEmbraceRank(player);
                if (rank && target->GetHealthPercent() <= 35.0f)
                    extra = spell->damage * uint32(3 * rank) / 100;
            }

            if (extra)
            {
                spell->m_casterUnit->DealDamage(target, extra, nullptr,
                        DIRECT_DAMAGE, SPELL_SCHOOL_MASK_SHADOW,
                        spell->m_spellInfo, false);
                spell->m_casterUnit->DealHeal(spell->m_casterUnit, extra,
                        spell->m_spellInfo);
            }

            uint32 total = spell->damage + extra;
            if (total && target->IsAlive())
                target->AddThreat(spell->m_casterUnit, float(total), false,
                                  SPELL_SCHOOL_MASK_SHADOW, spell->m_spellInfo);
        }
    };

    // Death Coil (the class's own 61074, A.6): "X-Y Shadow damage to an enemy
    // or heals an Undead minion for X-Y".  The clone targets any unit
    // (implicit target 25); friendly casts are gated to the caster's own
    // undead minion and heal it, hostile casts keep the default damage.
    struct spell_necromancer_death_coil : public SpellScript
    {
        static Pet* GetHealableMinion(Spell* spell)
        {
            if (!spell || !spell->m_casterUnit)
                return nullptr;

            Unit* target = spell->m_targets.getUnitTarget();
            Pet* minion = target ? target->ToPet() : nullptr;
            if (!minion || !minion->IsAlive())
                return nullptr;
            if (minion->GetOwnerGuid() != spell->m_casterUnit->GetObjectGuid())
                return nullptr;
            if (!IsMinionEntry(minion->GetEntry()))
                return nullptr;

            return minion;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            Unit* target = spell->m_targets.getUnitTarget();
            if (!target)
                return SPELL_FAILED_BAD_TARGETS;

            // hostile targets take the default damage; friendly targets must
            // be one of the caster's own undead minions (guardians included)
            if (spell->m_casterUnit->IsFriendlyTo(target) && !GetHealableMinion(spell))
                return SPELL_FAILED_BAD_TARGETS;

            return SPELL_CAST_OK;
        }

        void OnEffectDamageCalculate(Spell* spell, SpellEffectIndex effIdx,
                                     float& damage) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit ||
                    damage <= 0.0f)
                return;

            Unit* target = spell->GetUnitTarget();
            if (!target || !spell->m_casterUnit->IsHostileTo(target))
                return;

            if (Player* player = spell->m_casterUnit->ToPlayer())
                ApplyDeathsEmbrace(player, target, damage);
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return true;

            Pet* minion = GetHealableMinion(spell);
            if (!minion)
                return true;    // enemy target: the default damage runs

            // "or heals an Undead minion for X-Y" - heal for the computed
            // amount of the damage effect
            if (spell->damage > 0)
                spell->m_casterUnit->DealHeal(minion, uint32(spell->damage), spell->m_spellInfo);

            return false;   // effect fully handled by the script
        }
    };

    // Soul Strike (design A.4 slot 11): a 50% weapon strike that heals the
    // caster for 3% of their total health for each of their diseases on the
    // target (up to three).
    struct spell_necromancer_soul_strike : public SpellScript
    {
        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            Unit* target = spell->GetUnitTarget();
            if (!target || !target->IsAlive())
                return;

            uint32 diseases = 0;
            for (auto const& itr : target->GetSpellAuraHolderMap())
            {
                SpellAuraHolder const* holder = itr.second;
                if (holder && !holder->IsDeleted() && holder->GetSpellProto() &&
                        holder->GetCasterGuid() == spell->m_casterUnit->GetObjectGuid() &&
                        holder->GetSpellProto()->Dispel == DISPEL_DISEASE)
                    ++diseases;
            }

            if (!diseases)
                return;

            if (diseases > 3)
                diseases = 3;

            uint32 heal = spell->m_casterUnit->GetMaxHealth() * 3 * diseases / 100;
            if (heal)
                spell->m_casterUnit->DealHeal(spell->m_casterUnit, heal, spell->m_spellInfo);
        }
    };

    // Icy Touch (design A.5 slot 17): Frost damage that infects the target
    // with Frost Fever (periodic Frost damage plus a melee/casting speed
    // reduction).  Frost Fever also counts as one of the class's diseases.
    struct spell_necromancer_icy_touch : public SpellScript
    {
        void OnEffectDamageCalculate(Spell* spell, SpellEffectIndex effIdx,
                                     float& damage) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit ||
                    damage <= 0.0f)
                return;

            Unit* target = spell->GetUnitTarget();
            if (!target)
                return;

            if (Player* player = spell->m_casterUnit->ToPlayer())
                ApplyDeathsEmbrace(player, target, damage);
        }

        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            Unit* target = spell->GetUnitTarget();
            if (!target || !target->IsAlive())
                return;

            spell->m_casterUnit->CastSpell(target, NECRO_SPELL_FROST_FEVER, true);
        }
    };

    // Ghoul Frenzy: sends the tethered minion into a frenzy - breaks all
    // crowd control on it, +25% melee and casting speed and a heal of 50% of
    // its maximum health over the duration (the periodic amount is computed
    // by the aura script; the aura spell carries the two haste effects).
    struct spell_necromancer_ghoul_frenzy : public SpellScript, public AuraScript
    {
        static Pet* GetTetheredMinion(Spell* spell)
        {
            if (!spell || !spell->m_casterUnit)
                return nullptr;

            Unit* target = spell->m_targets.getUnitTarget();
            Pet* minion = target ? target->ToPet() : nullptr;
            if (!minion || !minion->IsAlive())
                return nullptr;
            if (minion->GetOwnerGuid() != spell->m_casterUnit->GetObjectGuid())
                return nullptr;
            if (minion->getPetType() != SUMMON_PET)
                return nullptr;

            return minion;
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return GetTetheredMinion(spell) ? SPELL_CAST_OK : SPELL_FAILED_BAD_TARGETS;
        }

        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0)
                return;

            Unit* target = spell->GetUnitTarget();
            if (!target)
                return;

            // breaks all crowd control effects on the minion
            std::vector<uint32> ccAuras;
            for (auto const& itr : target->GetSpellAuraHolderMap())
            {
                SpellAuraHolder* holder = itr.second;
                if (holder && !holder->IsDeleted() && holder->GetSpellProto() &&
                        holder->GetSpellProto()->IsCCSpell())
                    ccAuras.push_back(holder->GetId());
            }
            for (uint32 id : ccAuras)
                target->RemoveAurasDueToSpell(id);
        }

        void OnPeriodicCalculateAmount(Aura* aura, float& amount) override
        {
            if (!aura || aura->GetId() != NECRO_SPELL_GHOUL_FRENZY ||
                    aura->GetEffIndex() != EFFECT_INDEX_2)
                return;

            Unit* target = aura->GetTarget();
            if (!target)
                return;

            // 50% of maximum health over 30 sec (10 ticks of 3 sec)
            amount = float(target->GetMaxHealth()) * 5.0f / 100.0f;
        }
    };

    AuraScript* GetCallOfTheGraveAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_call_of_the_grave();
    }

    SpellScript* GetDiseaseCloudSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_disease_cloud();
    }

    AuraScript* GetDesecrationAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_desecration();
    }

    AuraScript* GetCrippleAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_cripple();
    }

    SpellScript* GetRaiseMinionSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_raise_minion();
    }

    SpellScript* GetTetherSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_tether();
    }

    SpellScript* GetSacrificeMinionSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_sacrifice_minion();
    }

    SpellScript* GetHarvestSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_harvest();
    }

    AuraScript* GetHarvestAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_harvest_aura();
    }

    SpellScript* GetRaiseWightSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_raise_wight();
    }

    SpellScript* GetGhoulFrenzySpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_ghoul_frenzy();
    }

    AuraScript* GetGhoulFrenzyAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_ghoul_frenzy();
    }

    SpellScript* GetMeatCatapultSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_meat_catapult();
    }

    SpellScript* GetMinionCannibalizeSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_minion_cannibalize();
    }

    SpellScript* GetPlagueBoltSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_plague_bolt();
    }

    SpellScript* GetPlagueStrikeSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_plague_strike();
    }

    SpellScript* GetArmorSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_armor();
    }

    SpellScript* GetBloodletSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_bloodlet();
    }

    SpellScript* GetEmbalmSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_embalm();
    }

    AuraScript* GetOutbreakAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_outbreak();
    }

    SpellScript* GetReapSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_reap();
    }

    SpellScript* GetDeathCoilSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_death_coil();
    }

    SpellScript* GetSoulStrikeSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_soul_strike();
    }

    SpellScript* GetIcyTouchSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_icy_touch();
    }

    // T2c talent scripts (2026-10-22)
    AuraScript* GetTwistedBondPlayerAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_twisted_bond_player();
    }

    AuraScript* GetTwistedBondMinionAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_twisted_bond_minion();
    }

    AuraScript* GetUndeadDominationAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_undead_domination();
    }

    // T2d talent scripts (2026-10-22)
    AuraScript* GetFrostFeverAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_frost_fever();
    }

    AuraScript* GetMetastasisAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_metastasis();
    }

    AuraScript* GetWanderingPlagueAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_wandering_plague();
    }

    AuraScript* GetButcheryAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_butchery();
    }

    AuraScript* GetArmorAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_armor();
    }

    // Spell scripts are resolved by script_name through the core's ScriptMgr;
    // the names below must match spell_template.script_name (set by the
    // generators in tools/).
    void RegisterAuraScript(char const* name, AuraScript* (*getter)(SpellEntry const*))
    {
        Script* script = new Script;
        script->Name = name;
        script->GetAuraScript = getter;
        script->RegisterSelf();
    }

    void RegisterSpellScript(char const* name, SpellScript* (*getter)(SpellEntry const*))
    {
        Script* script = new Script;
        script->Name = name;
        script->GetSpellScript = getter;
        script->RegisterSelf();
    }

    // One script_name may need both a SpellScript (cast-time work) and an
    // AuraScript (the buff it applies), like the core's own
    // spell_warlock_demonic_sacrifice.
    void RegisterSpellAndAuraScript(char const* name,
                                    SpellScript* (*spellGetter)(SpellEntry const*),
                                    AuraScript* (*auraGetter)(SpellEntry const*))
    {
        Script* script = new Script;
        script->Name = name;
        script->GetSpellScript = spellGetter;
        script->GetAuraScript = auraGetter;
        script->RegisterSelf();
    }

    class NecromancerWorldScript : public WorldScript
    {
    public:
        NecromancerWorldScript()
            : WorldScript("mod_necromancer_world", { WORLDHOOK_ON_STARTUP })
        {
        }

        void OnStartup() override
        {
            // corpse-class overrides (optional module table; absent = heuristics only)
            sNecroCorpseOverrides.clear();
            sNecroCorpseClassCache.clear();

            std::unique_ptr<QueryResult> result(WorldDatabase.Query(
                    "SELECT `entry`, `flags` FROM `necromancer_corpse_class`"));
            if (result)
            {
                do
                {
                    Field* fields = result->Fetch();
                    sNecroCorpseOverrides[fields[0].GetUInt32()] = uint8(fields[1].GetUInt32());
                }
                while (result->NextRow());

                sLog.outString("[mod-necromancer] loaded %u corpse class override(s)",
                               uint32(sNecroCorpseOverrides.size()));
            }

        sLog.outString("[mod-necromancer] module loaded (Phase 2 trainers: class spells "
                       "are trainer-taught; auto-learn retired; T2a-T2e talents active)");
        }
    };
}

void AddNecromancerScripts()
{
    new NecromancerWorldScript();
    new NecromancerPlayerScript();
    new NecromancerPetScript();
    new NecromancerGhoulArmorUnitScript();
    new NecromancerTalentUnitScript();

    // class-support: the class's summon pets of the declared creature types
    // count as permanent pets (pet action-bar spells, spirit-healer restore,
    // saved pet tab).  See ClassRegistry::ClassDescriptor.
    if (ClassDescriptor* descriptor = sClassRegistry.GetMutableDescriptor(10))
        descriptor->permanentSummonPetTypes |= (uint32(1) << (CREATURE_TYPE_UNDEAD - 1));

    // spell_template.script_name bindings
    RegisterAuraScript("spell_necromancer_call_of_the_grave", GetCallOfTheGraveAuraScript);
    RegisterSpellScript("spell_necromancer_disease_cloud", GetDiseaseCloudSpellScript);
    RegisterAuraScript("spell_necromancer_desecration", GetDesecrationAuraScript);
    RegisterAuraScript("spell_necromancer_cripple", GetCrippleAuraScript);
    RegisterSpellScript("spell_necromancer_raise_minion", GetRaiseMinionSpellScript);
    RegisterSpellScript("spell_necromancer_tether", GetTetherSpellScript);
    RegisterSpellScript("spell_necromancer_sacrifice_minion", GetSacrificeMinionSpellScript);
    RegisterSpellScript("spell_necromancer_harvest", GetHarvestSpellScript);
    RegisterAuraScript("spell_necromancer_harvest_aura", GetHarvestAuraScript);
    RegisterSpellAndAuraScript("spell_necromancer_ghoul_frenzy",
                               GetGhoulFrenzySpellScript, GetGhoulFrenzyAuraScript);
    RegisterSpellScript("spell_necromancer_raise_wight", GetRaiseWightSpellScript);
    RegisterSpellScript("spell_necromancer_meat_catapult", GetMeatCatapultSpellScript);
    RegisterSpellScript("spell_necromancer_minion_cannibalize", GetMinionCannibalizeSpellScript);

    // spell-correction pass (2026-10-19, design A.6-A.9 + A72)
    RegisterSpellScript("spell_necromancer_plague_bolt", GetPlagueBoltSpellScript);
    RegisterSpellScript("spell_necromancer_plague_strike", GetPlagueStrikeSpellScript);
    RegisterSpellScript("spell_necromancer_reap", GetReapSpellScript);
    RegisterSpellScript("spell_necromancer_death_coil", GetDeathCoilSpellScript);

    // remaining spellbook batch (2026-10-19)
    RegisterSpellAndAuraScript("spell_necromancer_armor",
                               GetArmorSpellScript, GetArmorAuraScript);
    RegisterSpellScript("spell_necromancer_bloodlet", GetBloodletSpellScript);
    RegisterSpellScript("spell_necromancer_embalm", GetEmbalmSpellScript);
    RegisterAuraScript("spell_necromancer_outbreak", GetOutbreakAuraScript);

    // remaining talent spells (2026-10-20)
    RegisterSpellScript("spell_necromancer_soul_strike", GetSoulStrikeSpellScript);
    RegisterSpellScript("spell_necromancer_icy_touch", GetIcyTouchSpellScript);

    // T2c minion/pet talents (2026-10-22)
    RegisterAuraScript("spell_necromancer_twisted_bond_player",
                       GetTwistedBondPlayerAuraScript);
    RegisterAuraScript("spell_necromancer_twisted_bond_minion",
                       GetTwistedBondMinionAuraScript);
    RegisterAuraScript("spell_necromancer_undead_domination_cd",
                       GetUndeadDominationAuraScript);

    // T2d proc/conditional talents (2026-10-22)
    RegisterAuraScript("spell_necromancer_frost_fever",
                       GetFrostFeverAuraScript);
    RegisterAuraScript("spell_necromancer_metastasis",
                       GetMetastasisAuraScript);
    RegisterAuraScript("spell_necromancer_wandering_plague",
                       GetWanderingPlagueAuraScript);
    RegisterAuraScript("spell_necromancer_butchery",
                       GetButcheryAuraScript);
}
