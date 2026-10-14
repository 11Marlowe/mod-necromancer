# mod-necromancer

A custom **Necromancer** class (class id 10) for the
[Tortoise WoW](https://github.com/tortoise-wow/tortoise-wow) 1.12.1 server core,
built as a standalone module on the core's **class-support** layer.

> **Status: in development.** Phase 0 (module skeleton) is in place. Phase 1
> (class identity: database rows, client DBC patch, creation) and Phase 2
> (spell list) are next. See the design/handoff document:
> <https://github.com/11Marlowe/wow-tools> (private) or the project's
> `Necromancer-Design.md`.

## How this is split

A playable class is always **two halves**:

| Half | Where | What |
| --- | --- | --- |
| **Server** | this module | SQL data (`data/sql/`), behavior scripts (`src/`), stat formulas via the `class_descriptor` table |
| **Client** | MPQ patch (`client/`) | `ChrClasses.dbc`, `CharBaseInfo.dbc`, `CharStartOutfit.dbc`, Glue UI (creation screen) — shipped as a high-priority `patch-Z.mpq` |

The client knows nothing about modules; its half must be installed as a patch.
See `client/README.md`.

## Requirements

- **Core:** the `class-support` branch of
  <https://github.com/11Marlowe/tortoise-wow>, which provides:
  - `ClassRegistry` + the `playable_class` and `class_descriptor` world tables,
  - `PlayerScript::CanCreateCharacter` / `PLAYERHOOK_CAN_CREATE_CHARACTER`,
  - the runtime playable-class mask used by the player-info loaders.
- The module folder must be named **`Necromancer`** inside `modules/` — the core
  derives the loader symbol `AddNecromancerScripts` and the config/SQL paths
  from the folder name.

## Install (server)

1. Clone into the core's modules directory as `Necromancer`:
   ```
   git clone https://github.com/11Marlowe/mod-necromancer.git modules/Necromancer
   ```
2. Reconfigure and rebuild the core (`-DMODULES=static`, as usual).
3. Apply the module SQL by hand (this project runs with
   `Database.AutoUpdate.Enabled = 0`):
   ```
   for %f in (modules\Necromancer\data\sql\world\*.sql) do .\mariadb.exe --port=3307 -u root --force tw_world < %f
   for %f in (modules\Necromancer\data\sql\character\*.sql) do .\mariadb.exe --port=3307 -u root --force tw_char < %f
   ```
4. Restart `mangosd` (startup should log
   `[mod-necromancer] module loaded`). No SQL and no client patch is required
   for the skeleton; both arrive with Phase 1.

## Install (client)

See `client/README.md`. In short: use the prebuilt `patch-Z.mpq` from this
repo's releases, or regenerate it from your own client DBCs with the bundled
script + patch YAML. Without it the class is not selectable at character
creation.

## Layout

```
src/                module source (loader: AddNecromancerScripts)
data/sql/world/     world-DB migrations (class data, spells, trainers, ...)
data/sql/character/ character-DB migrations
client/             client-side patch assets, scripts and docs
```

## License

TBD. The core is GPL-2.0 and this module is compiled into the server binary;
the practical options are GPL-2.0 (matching the core) or AGPL-3.0 (matching
TortoiseBots). A `LICENSE` file will be added before the first release.
