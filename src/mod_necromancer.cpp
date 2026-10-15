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
                guardian->Unsummon(PET_SAVE_AS_DELETED, caster);

            return false;   // effect fully handled by the script
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

    class NecromancerWorldScript : public WorldScript
    {
    public:
        NecromancerWorldScript()
            : WorldScript("mod_necromancer_world", { WORLDHOOK_ON_STARTUP })
        {
        }

        void OnStartup() override
        {
            sLog.outString("[mod-necromancer] module loaded (Phase 2 batch 3 slice 1: minions -- "
                           "Raise Ghoul, Raise Skeleton, Tether)");
        }
    };
}

void AddNecromancerScripts()
{
    new NecromancerWorldScript();
    new NecromancerPlayerScript();

    // spell_template.script_name bindings
    RegisterAuraScript("spell_necromancer_call_of_the_grave", GetCallOfTheGraveAuraScript);
    RegisterSpellScript("spell_necromancer_disease_cloud", GetDiseaseCloudSpellScript);
    RegisterSpellScript("spell_necromancer_raise_minion", GetRaiseMinionSpellScript);
    RegisterSpellScript("spell_necromancer_tether", GetTetherSpellScript);
}
