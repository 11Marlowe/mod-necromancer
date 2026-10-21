#!/usr/bin/env python3
"""Parse a saved talent-builder.dev tree page into JSON + Markdown.

The site is a Next.js app; the tree payload is embedded in the React Flight
data inside ``self.__next_f.push(...)`` script tags.  The payload contains one
entry per talent with (among others) ``icon``, ``name``, ``ranks``,
``description``, ``notes``, ``requires`` and ``spellIds``.

Usage (after saving the raw tree page HTML, e.g. with a browser):
    python parse_talent_tree.py --html reanimation.html \
        --out-prefix data/reanimation-tree --dbc-dir <server>/dbc

The optional DBC directory is used to resolve each icon slug against
``SpellIcon.dbc`` (the slug is the texture basename).  Icon slugs that do not
exist in the 1.12 client are reported so they can be substituted later.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from datetime import datetime, timezone

PUSH_MARKER = "self.__next_f.push("


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def extract_flight(html: str) -> str:
    """Concatenate all React Flight text chunks pushes."""
    chunks: list = []
    pos = 0
    while True:
        i = html.find(PUSH_MARKER, pos)
        if i == -1:
            break
        j = i + len(PUSH_MARKER)
        depth = 0
        k = j
        in_str = False
        esc = False
        while k < len(html):
            ch = html[k]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch in "[{":
                    depth += 1
                elif ch in "]}":
                    depth -= 1
                    if depth == 0:
                        k += 1
                        break
            k += 1
        chunks.append(json.loads(html[j:k]))
        pos = k
    return "".join(
        c[1] for c in chunks if isinstance(c, list) and len(c) >= 2 and c[0] == 1
    )


def extract_tree_node(flight: str) -> dict:
    """Find the chunk that carries ``defaultValues`` and return its node.

    The chunk id is normally ``6`` on the current site, but it is not
    guaranteed to stay stable; scan backwards for any ``<hex>:`` / ``<hex>:T…``
    marker and keep the one whose payload decodes to a tree object.
    """
    idx = flight.find('"defaultValues"')
    if idx < 0:
        raise SystemExit("could not find a tree payload (defaultValues) in the HTML")
    search_from = idx
    while search_from > 0:
        colon = flight.rfind(":", 0, search_from)
        if colon < 0:
            break
        id_start = colon
        while id_start > 0 and flight[id_start - 1] in "0123456789abcdefABCDEF":
            id_start -= 1
        if id_start == colon or colon - id_start > 8:
            search_from = colon
            continue
        payload = flight[colon + 1 :]
        if payload.startswith("T"):
            comma = payload.find(",")
            if comma < 0:
                search_from = colon
                continue
            payload = payload[comma + 1 :]
        try:
            obj, _ = json.JSONDecoder().raw_decode(payload)
        except Exception:
            search_from = colon
            continue
        node = None
        if isinstance(obj, list) and obj and len(obj[0]) > 3:
            node = obj[0][3]
        if isinstance(node, str):
            node = json.loads(node)
        if isinstance(node, dict) and "defaultValues" in node:
            return node
        search_from = colon
    raise SystemExit("could not find the tree chunk before defaultValues")


def extract_notes(flight: str, ref: str | None) -> str | None:
    """Extract the raw notes text referenced by e.g. ``$1e``."""
    if not ref or not ref.startswith("$"):
        return None
    chunk_id = ref[1:]
    fb = flight.encode("utf-8")
    marker = f"{chunk_id}:T".encode("ascii")
    i = fb.find(marker)
    if i < 0:
        return None
    j = fb.find(b",", i + len(marker))
    if j < 0:
        return None
    try:
        length = int(fb[i + len(marker) : j].decode("ascii"), 16)
    except ValueError:
        return None
    return fb[j + 1 : j + 1 + length].decode("utf-8", errors="replace")


def rsc_date(value):
    if isinstance(value, str) and value.startswith("$D"):
        return value[2:]
    return value


def site_url(html: str) -> str | None:
    for pattern in (
        r'<link rel="canonical" href="([^"]+)"',
        r'property="og:url" content="([^"]+)"',
    ):
        m = re.search(pattern, html)
        if m:
            return m.group(1)
    return None


def read_spellicons(dbc_path: str) -> dict[str, list[tuple[int, str]]]:
    """Return texture basename (lowercase, no .blp) -> [(id, filename)]."""
    with open(dbc_path, "rb") as f:
        buf = f.read()
    magic, record_count, field_count, record_size, string_size = struct.unpack_from(
        "<4sIIII", buf, 0
    )
    if magic != b"WDBC" or field_count < 2:
        raise SystemExit(f"not a usable WDBC file: {dbc_path}")
    strings_start = 20 + record_count * record_size
    strings = buf[strings_start : strings_start + string_size]

    def string_at(offset: int) -> str:
        end = strings.find(b"\x00", offset)
        if end < 0:
            end = len(strings)
        return strings[offset:end].decode("utf-8", errors="replace")

    result: dict[str, list[tuple[int, str]]] = {}
    for i in range(record_count):
        offset = 20 + i * record_size
        values = struct.unpack_from("<" + "I" * field_count, buf, offset)
        icon_id = values[0]
        filename = string_at(values[1])
        base = filename.replace("/", "\\").split("\\")[-1]
        if base.lower().endswith(".blp"):
            base = base[:-4]
        result.setdefault(base.lower(), []).append((icon_id, filename))
    return result


def setup_talents(dv: dict, columns: int) -> list[dict]:
    talents = dv["talents"]
    name_by_slot = {int(k): v["name"] for k, v in talents.items()}
    rows = []
    for key in sorted(talents, key=int):
        slot = int(key)
        t = talents[key]
        rows.append(
            {
                "slot": slot,
                "order": slot,
                "position": {
                    "row": slot // columns + 1,
                    "column": slot % columns + 1,
                    "page": 1,
                },
                "icon": t.get("icon"),
                "name": t.get("name"),
                "maxRank": t.get("ranks"),
                "highlight": t.get("highlight"),
                "description": t.get("description"),
                "talentNotes": t.get("notes"),
                "requires": t.get("requires"),
                "requiresName": (
                    name_by_slot.get(t["requires"])
                    if t.get("requires") is not None
                    else None
                ),
                "spellIds": t.get("spellIds"),
            }
        )
    return rows


def write_markdown(
    path: str,
    tree: dict,
    talents: list[dict],
    icons: dict,
    notes_raw: str | None,
) -> None:
    def esc(value) -> str:
        if value is None:
            return ""
        return str(value).replace("|", "\\|").replace("\r\n", "\n").replace("\n", "<br>")

    lines = [
        f"# {tree['name']} — Necromancer talent tree (talent-builder.dev)",
        "",
        f"- **Tree id:** {tree['id']}",
        f"- **Name:** {tree['name']}",
        f"- **Tree icon slug:** `{tree['icon']}`"
        + (
            f" (SpellIcon {', '.join(str(i) for i in icons['treeIconIds'])})"
            if icons["treeIconIds"]
            else " (not in 1.12 `SpellIcon.dbc`)"
        ),
        f"- **Class:** {tree['classLabel']} (site class field {tree['class']})",
        "- **Game version:** 1.12.1",
        f"- **Grid:** {tree['rows']} rows × {tree['columns']} columns × 1 page "
        "(talent `slot` keys are 0-based row-major flat indices)",
        f"- **Talents:** {len(talents)} | **Total ranks (points):** {tree['points']}",
        f"- **Author:** {tree['author'].get('name')} | **Visibility:** {tree['visibility']}",
        f"- **Created:** {tree['createdAt']} | **Updated:** {tree['updatedAt']}",
        f"- **Source:** {tree['source']}",
        f"- **Saved HTML:** `{tree['savedHtml']}`",
        "",
        "| Slot # | Name | MaxRank | Icon slug | SpellIcon ID | Description | Position (row, col) | Requires | Highlight |",
        "|---:|---|---:|---|---:|---|---|---|---|",
    ]
    for t in talents:
        ids = t.get("spellIconIds") or []
        icon_id = ", ".join(str(i) for i in ids) if ids else "—"
        requires = (
            f"#{t['requires']} {t['requiresName']}"
            if t["requires"] is not None
            else "—"
        )
        lines.append(
            f"| {t['slot']} | {esc(t['name'])} | {t['maxRank']} | `{esc(t['icon'])}` | "
            f"{icon_id} | {esc(t['description'])} | "
            f"{t['position']['row']}, {t['position']['column']} | {esc(requires)} | "
            f"{'yes' if t['highlight'] else 'no'} |"
        )
    lines += [
        "",
        "_Slot keys are the site's raw talent keys; positions are derived from the "
        f"rendered grid ({tree['columns']} columns). Descriptions are verbatim._",
        "",
    ]

    if icons["missing"]:
        lines += [
            "## Icons missing from the 1.12 `SpellIcon.dbc`",
            "",
            "These site icon slugs are not registered in the 1.12 "
            "`SpellIcon.dbc`.  The texture may still exist in the client "
            "(common for item icons) and then only needs a new SpellIcon row; "
            "otherwise use a substitute or custom art:",
            "",
        ]
        lines += [f"- `{slug}`" for slug in icons["missing"]]
        lines.append("")

    duplicates = {k: v for k, v in icons["textureIds"].items() if len(v) > 1}
    if duplicates:
        lines += [
            "## Icon slugs with multiple SpellIcon rows",
            "",
            "The texture is identical; either id can be used in `Talent.dbc`.",
            "",
        ]
        for slug, ids in sorted(duplicates.items()):
            lines.append(f"- `{slug}` -> {', '.join(str(i) for i in ids)}")
        lines.append("")

    lines += [
        "## Per-talent spell ids (spellIds)",
        "",
        "| Slot # | Name | spellIds |",
        "|---:|---|---|",
    ]
    for t in talents:
        spell_ids = t["spellIds"] if t["spellIds"] is not None else "(null)"
        lines.append(f"| {t['slot']} | {esc(t['name'])} | {esc(spell_ids)} |")
    lines.append("")

    if notes_raw:
        lines += [
            "## Tree notes (verbatim, as stored — HTML-formatted text)",
            "",
            "```html",
            notes_raw,
            "```",
            "",
        ]

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="saved talent-builder tree page")
    parser.add_argument(
        "--out-prefix",
        required=True,
        help="output path without extension (writes .json and .md)",
    )
    parser.add_argument(
        "--dbc-dir",
        help="directory containing SpellIcon.dbc (optional; enables icon ID resolution)",
    )
    parser.add_argument(
        "--class-label",
        default="Necromancer",
        help="class label for the output (default: Necromancer)",
    )
    args = parser.parse_args()

    html = read_text(args.html)
    flight = extract_flight(html)
    node = extract_tree_node(flight)
    dv = node["defaultValues"]

    columns_match = re.search(r"grid-cols-\[repeat\((\d+),max-content\)\]", html)
    if not columns_match:
        raise SystemExit("could not determine the grid column count from the HTML")
    columns = int(columns_match.group(1))

    talents = setup_talents(dv, columns)
    notes_ref = dv.get("notes")
    notes_raw = extract_notes(flight, notes_ref)

    icon_lookup: dict[str, list[tuple[int, str]]] = {}
    dbc_path = None
    if args.dbc_dir:
        dbc_path = os.path.join(args.dbc_dir, "SpellIcon.dbc")
        if not os.path.isfile(dbc_path):
            raise SystemExit(f"SpellIcon.dbc not found: {dbc_path}")
        icon_lookup = read_spellicons(dbc_path)

    tree_icon = dv.get("icon")
    missing: list[str] = []
    texture_ids: dict[str, list[int]] = {}
    for entry in talents:
        slug = entry.get("icon")
        matches = icon_lookup.get(slug.lower(), []) if slug and icon_lookup else []
        entry["spellIconIds"] = [i for i, _ in matches]
        entry["spellIconFile"] = matches[0][1] if matches else None
        if slug:
            texture_ids[slug] = [i for i, _ in matches]
            if icon_lookup and not matches:
                missing.append(slug)
    if tree_icon:
        matches = icon_lookup.get(tree_icon.lower(), []) if icon_lookup else []
        texture_ids.setdefault(tree_icon, [i for i, _ in matches])
        if icon_lookup and not matches:
            missing.append(tree_icon)
    missing = sorted(set(missing))

    saved_mtime = datetime.fromtimestamp(
        os.path.getmtime(args.html), tz=timezone.utc
    ).isoformat(timespec="seconds")

    out = {
        "source": site_url(html),
        "savedHtml": os.path.abspath(args.html),
        "savedHtmlMtime": saved_mtime,
        "tree": {
            "id": dv["id"],
            "name": dv["name"],
            "icon": tree_icon,
            "class": dv.get("class"),
            "classLabel": args.class_label,
            "gameVersion": "1.12.1",
            "rows": dv.get("rows"),
            "columns": columns,
            "pages": 1,
            "talents": len(talents),
            "points": sum(t["maxRank"] for t in talents),
            "visibility": dv.get("visibility"),
            "author": dv.get("createdBy"),
            "createdById": dv.get("createdById"),
            "createdAt": rsc_date(dv.get("createdAt")),
            "updatedAt": rsc_date(dv.get("updatedAt")),
            "source": site_url(html),
            "savedHtml": os.path.abspath(args.html),
        },
        "icons": {
            "spellIconDbc": dbc_path,
            "resolved": len(talents) + (1 if tree_icon else 0) - len(missing),
            "missing": missing,
            "textureIds": texture_ids,
        },
        "talents": talents,
        "notes_raw": notes_raw,
    }
    out["tree"]["points"] = sum(t["maxRank"] for t in talents)
    if tree_icon:
        out["tree"]["iconSpellIconIds"] = texture_ids.get(tree_icon, [])

    with open(args.out_prefix + ".json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")

    write_markdown(
        args.out_prefix + ".md",
        {**out["tree"], "author": out["tree"]["author"] or {}},
        talents,
        {
            "treeIconIds": tree_icon and texture_ids.get(tree_icon, []) or [],
            "missing": missing,
            "textureIds": texture_ids,
        },
        notes_raw,
    )

    print(
        f"{dv['name']}: {len(talents)} talents, {sum(t['maxRank'] for t in talents)} ranks, "
        f"{len(missing)} icon(s) missing from 1.12 SpellIcon.dbc",
        file=sys.stderr,
    )
    print(f"wrote {args.out_prefix}.json and .md", file=sys.stderr)


if __name__ == "__main__":
    main()
