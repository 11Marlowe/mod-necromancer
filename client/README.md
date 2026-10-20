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
| `DBFilesClient\Spell.dbc` | class spells (batches 1-4, corrections, remaining batch 61076-61086) and the trainer learn spells 61100-61142 |
| `DBFilesClient\SkillLine.dbc` | the three spellbook tabs: Reanimation (700), Blood (701), Plague (702) |
| `DBFilesClient\SkillLineAbility.dbc` | spell-to-tab mapping (rows 7211-7253) |
| `DBFilesClient\SkillRaceClassInfo.dbc` | grants skills 700/701/702 to class 10 (rows 1010-1012) |

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
.\client\build-client-patch.ps1 -ClientDbcDir "C:\path\to\TWoWClient\Game\dbc" `
                               -PatcherExe   "C:\path\to\wow_dbc_patcher.exe"
```

The script uses the `wow_dbc_patcher` fork
(<https://github.com/11Marlowe/twow-raid-visuals>) — needed because the upstream
patcher cannot write `CharBaseInfo.dbc` / `CharStartOutfit.dbc` (packed 8-bit
fields). Patch YAMLs live in `client\patches\`; the two Glue files (extracted
from Turtle's `patch-9.mpq` with the class additions applied) live in
`client\includes\Interface\GlueXML\`.

## zhCN clients

This client also has a loose, localized copy at `Data\GlueStrings.lua`. Add the
same class string there (UTF-8, after a `CLASS_` entry):

```
CLASS_NECROMANCER = "        亡灵法师掌握着死亡的禁忌之力。他们驱使亡者、散播瘟疫，并以自身的生命换取毁灭性的力量。黑暗法术与战斗纪律的结合，使他们在必要时也能成为坚韧的战士。";
```

(The deployed development client already has this line.)

## Known Phase-1 placeholders

- The creation-screen class icon points at a free atlas cell in
  `UI-CharacterCreate-Classes.blp`; the texture is not painted yet, so the icon
  is blank until Phase 2 art. The class name/description and everything else
  are functional.
