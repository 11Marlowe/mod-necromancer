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

namespace
{
    enum NecromancerSpellIds
    {
        NECRO_SPELL_PLAGUE_BOLT_R2       = 61011,
        NECRO_SPELL_REAP_R2              = 61014,
        NECRO_SPELL_PLAGUE_BOLT_R3       = 61012,
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
        NECRO_SPELL_DEATH_COIL           = 6789,
    };

    // creature_template entries summoned by the Raise spells (vanilla undead)
    enum NecromancerMinionEntries
    {
        NECRO_CREATURE_GHOUL    = 846,
        NECRO_CREATURE_SKELETON = 6412,
    };

    // Spells taught automatically when a Necromancer reaches the level.
    // The rank-1 spells of level 1 are granted at creation via
    // playercreateinfo_spell; this list covers rank-ups and later abilities
    // (idempotent: known spells are skipped).  Trainers are not used yet.
    struct ClassSpell
    {
        uint32 spellId;
        uint8  level;
    };

    constexpr ClassSpell NecromancerSpells[] =
    {
        { NECRO_SPELL_PLAGUE_BOLT_R2,        8 },
        { NECRO_SPELL_HARVEST,              10 },
        { NECRO_SPELL_CALL_OF_THE_GRAVE_R1, 12 },
        { NECRO_SPELL_REAP_R2,              12 },
        { NECRO_SPELL_DEATH_COIL,           14 },
        { NECRO_SPELL_RAISE_GHOUL,          14 },
        { NECRO_SPELL_RAISE_SKELETON,       14 },
        { NECRO_SPELL_PLAGUE_BOLT_R3,       16 },
        { NECRO_SPELL_DESECRATION_R1,       20 },
        { NECRO_SPELL_DISEASE_CLOUD,        20 },
        { NECRO_SPELL_CRIPPLE,              20 },
        { NECRO_SPELL_TETHER,               20 },
        { NECRO_SPELL_SACRIFICE_MINION,     20 },
        { NECRO_SPELL_GHOUL_FRENZY,         20 },
        { NECRO_SPELL_CALL_OF_THE_GRAVE_R2, 24 },
        { NECRO_SPELL_CALL_OF_THE_GRAVE_R3, 34 },
        { NECRO_SPELL_DESECRATION_R2,       34 },
        { NECRO_SPELL_DESECRATION_R3,       46 },
    };

    void TeachClassSpells(Player* player)
    {
        if (!player || player->GetClass() != 10)
            return;

        uint8 level = player->GetLevel();
        for (ClassSpell const& entry : NecromancerSpells)
        {
            if (level >= entry.level && !player->HasSpell(entry.spellId))
                player->LearnSpell(entry.spellId, false);
        }
    }

    class NecromancerPlayerScript : public PlayerScript
    {
    public:
        NecromancerPlayerScript()
            : PlayerScript("mod_necromancer_player",
                           { PLAYERHOOK_ON_LOGIN, PLAYERHOOK_ON_LEVEL_CHANGED })
        {
        }

        void OnLogin(Player* player) override
        {
            TeachClassSpells(player);
        }

        void OnLevelChanged(Player* player, uint8 /*oldLevel*/) override
        {
            TeachClassSpells(player);
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

    // The Necromancer's disease family, used by Disease Cloud.  Outbreak and
    // Corrosion will be added here with their batches.
    bool IsNecromancerDisease(uint32 spellId)
    {
        return IsCallOfTheGrave(spellId);
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
    // Minions (batch 3, slice 1: Raise Ghoul / Raise Skeleton / Tether)
    // ------------------------------------------------------------------

    bool IsRaiseMinionSpell(uint32 spellId)
    {
        return spellId == NECRO_SPELL_RAISE_GHOUL ||
               spellId == NECRO_SPELL_RAISE_SKELETON;
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
    }

    // Guardian minions use the creature template's flat values; re-initialize
    // at the caster's level and scale like summoned pets (placeholder tuning,
    // see the design doc assumptions).  Fires right after the guardian is
    // created, before it is added to the map.
    struct spell_necromancer_raise_minion : public SpellScript
    {
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

            // Death Pact effect (placeholder per-minion-type modifiers; see
            // the design doc assumptions).
            uint32 auraId = minion->GetEntry() == NECRO_CREATURE_SKELETON ?
                NECRO_SPELL_DEATH_PACT_SKELETON : NECRO_SPELL_DEATH_PACT_GHOUL;
            caster->CastSpell(caster, auraId, true);

            minion->Unsummon(PET_SAVE_AS_DELETED, caster);

            return false;   // effect fully handled by the script
        }
    };

    // Harvest: cannibalize-style corpse consumption.  Requires a nearby
    // humanoid/undead corpse (the core's own Cannibalize check); while the
    // aura lasts the caster regenerates mana.  The corpse finder is the core
    // helper Cannibalize uses itself, replicated here because the hardcoded
    // 20577 case does not apply to cloned ids.
    struct spell_necromancer_harvest : public SpellScript
    {
        static WorldObject* FindCorpse(Spell* spell)
        {
            if (!spell || !spell->m_casterUnit || !spell->m_casterUnit->IsInWorld())
                return nullptr;

            return spell->FindCorpseUsing<MaNGOS::CannibalizeObjectCheck>();
        }

        SpellCastResult OnCheckCast(Spell* spell, bool /*strict*/) const override
        {
            if (!spell || !spell->m_casterUnit)
                return SPELL_CAST_OK;

            return FindCorpse(spell) ? SPELL_CAST_OK : SPELL_FAILED_NO_EDIBLE_CORPSES;
        }

        void OnTargetMapFilled(Spell* spell, SpellEffectIndex effIdx, uint32 /*targetMode*/,
                               std::list<Unit*>& targets) const override
        {
            // Like the original Cannibalize: the corpse is the dummy effect's
            // target, so the effect executes and the script can run.
            if (effIdx != EFFECT_INDEX_0 || !targets.empty())
                return;

            if (WorldObject* result = FindCorpse(spell))
                if (Unit* unit = result->ToUnit())
                    targets.push_back(unit);
        }

        bool OnEffectExecute(Spell* spell, SpellEffectIndex effIdx) const override
        {
            if (effIdx != EFFECT_INDEX_0 || !spell->m_casterUnit)
                return false;

            spell->m_casterUnit->CastSpell(spell->m_casterUnit, NECRO_SPELL_HARVEST_AURA, true);
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

    SpellScript* GetGhoulFrenzySpellScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_ghoul_frenzy();
    }

    AuraScript* GetGhoulFrenzyAuraScript(SpellEntry const* /*spellInfo*/)
    {
        return new spell_necromancer_ghoul_frenzy();
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
            sLog.outString("[mod-necromancer] module loaded (Phase 2 batch 3 slice 2: minion control -- "
                           "Sacrifice Minion, Harvest, Ghoul Frenzy, minion abilities)");
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
    RegisterSpellAndAuraScript("spell_necromancer_ghoul_frenzy",
                               GetGhoulFrenzySpellScript, GetGhoulFrenzyAuraScript);
}
