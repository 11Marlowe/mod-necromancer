# Client patch (Necromancer class)

The WoW 1.12 client renders classes from **its own DBCs and Glue UI**, which
cannot come from a server module. The Necromancer therefore ships a client-side
MPQ patch.

## What is patched

| File | Purpose |
| --- | --- |
| `DBFilesClient\ChrClasses.dbc` | class row 10 (`NECROMANCER`, mana) |
| `DBFilesClient\CharBaseInfo.dbc` | `(race, 10)` pairs — makes the class selectable per race |
| `DBFilesClient\CharStartOutfit.dbc` | starting outfit per race/gender |
| `Interface\GlueXML\CharacterCreate.lua` | `CLASS_ICON_TCOORDS["NECROMANCER"]`, icon coords |
| `Interface\GlueXML\GlueStrings.lua` | `CLASS_NECROMANCER` creation-screen text |
| `Glues\CharacterCreate\UI-CharacterCreate-Classes.blp` | class icon in the free atlas cell |
| spell-related DBCs | Phase 2: `Spell.dbc`, `SpellIcon.dbc`, `SkillLine*.dbc`, ... |

Load order: the patch is named `patch-Z.mpq` so it loads after everything
including Turtle's `patch-9.mpq` (highest wins, whole-file replacement).

## How to install (end users)

1. Drop `patch-Z.mpq` into the client `Data\` folder.
2. The server must also run the core `class-support` branch with this module
   installed, otherwise the class will fail at creation.

A prebuilt `patch-Z.mpq` is attached to this repo's releases. Alternatively,
regenerate it from your own client DBCs:

## How to regenerate (from your own client)

```
client\build-client-patch.ps1 -ClientDataDir "C:\path\to\TWoWClient\Game\Data" -DbcDir "C:\path\to\extracted\dbc" -OutDir client\build
```

The script uses the `wow_dbc_patcher` fork
(<https://github.com/11Marlowe/twow-raid-visuals>) — needed because the upstream
patcher cannot write `CharBaseInfo.dbc` / `CharStartOutfit.dbc` (packed 8-bit
fields). Patch YAMLs and schemas live in `client/patches/` and
`client/schema/`.

**This folder will be completed in Phase 1** of the module (see the main
README). Both the prebuilt patch and the regeneration tooling are deliverables
of that phase.
