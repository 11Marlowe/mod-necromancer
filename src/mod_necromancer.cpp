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

#include <algorithm>
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
        NECRO_SPELL_CANNIBALIZE_AURA     = 20578,   // vanilla Cannibalize regen aura
        NECRO_SPELL_DEATH_COIL_WARLOCK   = 6789,    // shared Warlock spell; no longer learned
    };

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

    class NecromancerPlayerScript : public PlayerScript
    {
    public:
        NecromancerPlayerScript()
            : PlayerScript("mod_necromancer_player",
                           { PLAYERHOOK_ON_LOGIN, PLAYERHOOK_ON_LEARN_SPELL })
        {
        }

        void OnLogin(Player* player) override
        {
            CleanupLegacySpells(player);
        }

        void OnLearnSpell(Player* player, uint32 spellId) override
        {
            if (!player || player->GetClass() != 10)
                return;

            if (spellId == NECRO_SPELL_DEATH_COIL &&
                    player->HasSpell(NECRO_SPELL_DEATH_COIL_WARLOCK))
                player->RemoveSpell(NECRO_SPELL_DEATH_COIL_WARLOCK, false, false);
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

    // The Necromancer's disease family, used by Disease Cloud.  The design
    // explodes "a victim of your Toxic Plague"; Grave Rot stays accepted as a
    // superset placeholder.  Outbreak and Corrosion will be added here with
    // their batches.
    bool IsNecromancerDisease(uint32 spellId)
    {
        return IsCallOfTheGrave(spellId) || IsToxicPlague(spellId);
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

    // Call of the Grave: a plague that festers on the victim; the final tick
    // deals triple damage.  Bound to the ranks via spell_template.script_name.
    struct spell_necromancer_call_of_the_grave : public AuraScript
    {
        void OnPeriodicDamageCalculateAmount(Aura* aura, float& amount) override
        {
            if (!aura || amount <= 0.0f || !IsCallOfTheGrave(aura->GetId()))
                return;

            if (aura->GetAuraTicks() && aura->GetAuraTicks() == aura->GetAuraMaxTicks())
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
        }

        void OnEffectExecuted(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell || !spell->m_casterUnit)
                return;

            uint32 plagueId = GetToxicPlagueId(spell->m_spellInfo->Id);
            Unit* target = spell->GetUnitTarget();
            if (!plagueId || !target || !target->IsAlive())
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

            if (spell->damage > 0)
                target->AddThreat(spell->m_casterUnit, float(spell->damage), false,
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

    SpellScript* GetReapSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_reap();
    }

    SpellScript* GetDeathCoilSpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_death_coil();
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
                           "are trainer-taught; auto-learn retired)");
        }
    };
}

void AddNecromancerScripts()
{
    new NecromancerWorldScript();
    new NecromancerPlayerScript();

    // class-support: the class's summon pets of the declared creature types
    // count as permanent pets (pet action-bar spells, spirit-healer restore,
    // saved pet tab).  See ClassRegistry::ClassDescriptor.
    if (ClassDescriptor* descriptor = sClassRegistry.GetMutableDescriptor(10))
        descriptor->permanentSummonPetTypes |= (uint32(1) << (CREATURE_TYPE_UNDEAD - 1));

    // spell_template.script_name bindings
    RegisterAuraScript("spell_necromancer_call_of_the_grave", GetCallOfTheGraveAuraScript);
    RegisterSpellScript("spell_necromancer_disease_cloud", GetDiseaseCloudSpellScript);
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
    RegisterSpellScript("spell_necromancer_reap", GetReapSpellScript);
    RegisterSpellScript("spell_necromancer_death_coil", GetDeathCoilSpellScript);
}
