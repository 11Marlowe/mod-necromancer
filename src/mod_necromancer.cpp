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

namespace
{
    // Phase 0 skeleton: proves module registration.  Real content (spell
    // scripts, minion behavior, class data validation) lands with Phase 1/2.
    class NecromancerWorldScript : public WorldScript
    {
    public:
        NecromancerWorldScript()
            : WorldScript("mod_necromancer_world", { WORLDHOOK_ON_STARTUP })
        {
        }

        void OnStartup() override
        {
            sLog.outString("[mod-necromancer] module loaded (Phase 1: identity data + client patch available)");
        }
    };
}

void AddNecromancerScripts()
{
    new NecromancerWorldScript();
}
