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

namespace
{
    // Spells taught automatically when a Necromancer reaches the level.
    // Rank 1 spells are also granted at creation via playercreateinfo_spell;
    // this list only covers rank-ups and later abilities (idempotent: known
    // spells are skipped).  Trainers are intentionally not used yet.
    struct ClassSpell
    {
        uint32 spellId;
        uint8  level;
    };

    constexpr ClassSpell NecromancerSpells[] =
    {
        { 61011,  8 },   // Plague Bolt Rank 2
        { 61014, 12 },   // Reap Rank 2
        {  6789, 14 },   // Death Coil (shared with Warlock)
        { 61012, 16 },   // Plague Bolt Rank 3
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

    class NecromancerWorldScript : public WorldScript
    {
    public:
        NecromancerWorldScript()
            : WorldScript("mod_necromancer_world", { WORLDHOOK_ON_STARTUP })
        {
        }

        void OnStartup() override
        {
            sLog.outString("[mod-necromancer] module loaded (Phase 2 batch 1: Plague Bolt, Reap, Bone Armor, auto-learn)");
        }
    };
}

void AddNecromancerScripts()
{
    new NecromancerWorldScript();
    new NecromancerPlayerScript();
}
