#!/usr/bin/env python3
"""Build the Dragonlight datapack for each supported Minecraft version.

Patches are derived from each version's own vanilla data, so the output matches
that version's folder layout and json schemas.

    python3 tools/build_dragonlight.py            # all versions
    python3 tools/build_dragonlight.py 1.20.1     # one version
"""

import json
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
BUILD = ROOT / "build"
DIST = ROOT / "dist"

VERSIONS = [
    "1.16.5", "1.17.1", "1.18.2", "1.19.2", "1.19.4",
    "1.20.1", "1.20.4", "1.20.6",
    "1.21.1", "1.21.4", "1.21.5", "1.21.8", "1.21.11",
    "26.1.2", "26.2",
]

# Drop only when mined in the End.
GATED = [
    "torch", "soul_torch", "copper_torch",
    "lantern", "soul_lantern", "copper_lantern",
]

DYE_COLORS = [
    "white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
    "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black",
]
# No recipe, no drops, anywhere.
REMOVED = (
    ["candle"] + [f"{c}_candle" for c in DYE_COLORS] + ["campfire", "soul_campfire"]
)

LOCKED = GATED + REMOVED

# Structures that generate torches. Torches inside these never drop.
TORCH_STRUCTURES = [
    "mineshaft", "mineshaft_mesa", "stronghold", "igloo", "mansion",
    "pillager_outpost", "ancient_city", "trial_chambers", "village_desert",
    "village_plains", "village_savanna", "village_snowy", "village_taiga",
]

# Names used before 1.18.2, when the predicate took a structure feature id.
LEGACY_TORCH_STRUCTURES = [
    "mineshaft", "village", "stronghold", "igloo", "mansion", "pillager_outpost",
]

DV_1_19 = 3105       # location predicate gained "structure"
DV_1_20_5 = 3837     # location predicate gained "structures"

IN_THE_END = {
    "condition": "minecraft:location_check",
    "predicate": {"dimension": "minecraft:the_end"},
}


def structure_field(vanilla, lay, data_version):
    """Return the predicate field for structures, and whether ids are namespaced."""
    field = "structures" if data_version >= DV_1_20_5 else (
        "structure" if data_version >= DV_1_19 else "feature")
    namespaced = True
    for src in (vanilla / "data" / "minecraft" / lay["advancement"]).rglob("*.json"):
        text = src.read_text()
        marker = f'"{field}": "'
        if marker in text:
            namespaced = ":" in text.split(marker, 1)[1].split('"', 1)[0]
            break
    return field, namespaced


def can_drop(vanilla, lay, data_version):
    """Drop unless the block sits inside a structure that generates torches."""
    field, namespaced = structure_field(vanilla, lay, data_version)
    mcv = vanilla / "data" / "minecraft"
    if namespaced:
        for folder in ("structure", "configured_structure_feature"):
            available = {p.stem for p in (mcv / "worldgen" / folder).glob("*.json")}
            if available:
                break
        names = [f"minecraft:{n}" for n in TORCH_STRUCTURES if n in available]
    else:
        names = list(LEGACY_TORCH_STRUCTURES)

    if field == "structures":
        inside = {"condition": "minecraft:location_check", "predicate": {"structures": names}}
    else:
        terms = [{"condition": "minecraft:location_check", "predicate": {field: n}}
                 for n in names]
        inside = {"condition": "minecraft:any_of", "terms": terms}
    return {
        "condition": "minecraft:any_of",
        "terms": [deepcopy(IN_THE_END), {"condition": "minecraft:inverted", "term": inside}],
    }


# --- downloads ---

def fetch_vanilla(version):
    CACHE.mkdir(parents=True, exist_ok=True)
    extracted = CACHE / f"mcmeta-{version}-data"
    if not extracted.is_dir():
        tarball = CACHE / f"{version}-data.tar.gz"
        if not tarball.exists():
            url = f"https://github.com/misode/mcmeta/archive/refs/tags/{version}-data.tar.gz"
            urllib.request.urlretrieve(url, tarball)
        with tarfile.open(tarball) as tf:
            tf.extractall(CACHE)
    return extracted


def version_info(version):
    url = f"https://raw.githubusercontent.com/misode/mcmeta/{version}-summary/version.json"
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def zip_dir(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(src))


# --- json ---

def layout(vanilla):
    """Resolve folder names, which went plural to singular in 1.21."""
    singular = (vanilla / "data" / "minecraft" / "loot_table").is_dir()
    return {
        "loot": "loot_table" if singular else "loot_tables",
        "recipe": "recipe" if singular else "recipes",
        "advancement": "advancement" if singular else "advancements",
        "function": "function" if singular else "functions",
    }


def find_items(node, wanted, found=None):
    """Every locked item id produced anywhere inside this json."""
    if found is None:
        found = set()
    if isinstance(node, dict):
        if node.get("type") in (None, "minecraft:item") and node.get("name") in wanted:
            found.add(node["name"])
        for v in node.values():
            find_items(v, wanted, found)
    elif isinstance(node, list):
        for v in node:
            find_items(v, wanted, found)
    return found


def strip_items(node, wanted):
    """Swap locked item entries for empty entries of the same weight."""
    changed = False
    if isinstance(node, dict):
        entries = node.get("entries")
        if isinstance(entries, list):
            for i, entry in enumerate(entries):
                if (
                    isinstance(entry, dict)
                    and entry.get("type") == "minecraft:item"
                    and entry.get("name") in wanted
                ):
                    empty = {"type": "minecraft:empty"}
                    for keep in ("weight", "quality", "conditions"):
                        if keep in entry:
                            empty[keep] = entry[keep]
                    entries[i] = empty
                    changed = True
        for v in node.values():
            changed |= strip_items(v, wanted)
    elif isinstance(node, list):
        for v in node:
            changed |= strip_items(v, wanted)
    return changed


def gate(table, wanted, condition):
    """Add a drop condition to any pool that yields a gated item."""
    changed = False
    for pool in table.get("pools", []):
        if find_items(pool, wanted):
            pool.setdefault("conditions", []).append(deepcopy(condition))
            changed = True
    return changed


def barrier_like(sample):
    """An unobtainable ingredient written in this version's ingredient format."""
    if isinstance(sample, str):
        return "minecraft:barrier"
    if isinstance(sample, list) and sample:
        return barrier_like(sample[0])
    return {"item": "minecraft:barrier"}


def make_impossible(recipe):
    """Rewrite a recipe's ingredients to barriers, keeping its id and schema."""
    r = deepcopy(recipe)
    touched = False
    for field in ("key", "ingredients", "ingredient", "base", "addition", "template", "material", "input"):
        if field not in r:
            continue
        value = r[field]
        if isinstance(value, dict) and field == "key":
            r[field] = {k: barrier_like(v) for k, v in value.items()}
        elif isinstance(value, list):
            r[field] = [barrier_like(v) for v in value]
        else:
            r[field] = barrier_like(value)
        touched = True
    return r if touched else None


def item_predicate(vanilla, lay, item_id):
    """Build an item predicate in the shape this version's own files use."""
    root = vanilla / "data" / "minecraft" / lay["advancement"] / "recipes"
    for src in sorted(root.rglob("*.json")):
        for crit in json.loads(src.read_text()).get("criteria", {}).values():
            if crit.get("trigger") != "minecraft:inventory_changed":
                continue
            items = crit.get("conditions", {}).get("items")
            if isinstance(items, list) and items and isinstance(items[0], dict):
                sample = items[0]
                if "item" in sample:
                    return {"item": item_id}
                if isinstance(sample.get("items"), list):
                    return {"items": [item_id]}
                if isinstance(sample.get("items"), str):
                    return {"items": item_id}
    return {"items": item_id}


def never_unlock(advancement):
    """Keep the rewards, swap the criteria for a trigger that never fires."""
    return {
        "criteria": {"never": {"trigger": "minecraft:impossible"}},
        "requirements": [["never"]],
        "rewards": advancement.get("rewards", {}),
    }


# --- build ---

def build(version):
    vanilla = fetch_vanilla(version)
    info = version_info(version)
    fmt, data_version = info["data_pack_version"], info["data_version"]
    lay = layout(vanilla)
    mcv = vanilla / "data" / "minecraft"

    out = BUILD / version / "Dragonlight"
    if out.exists():
        shutil.rmtree(out)
    mc = out / "data" / "minecraft"

    gated = {f"minecraft:{i}" for i in GATED}
    removed = {f"minecraft:{i}" for i in REMOVED}
    locked = gated | removed
    report = {"version": version, "pack_format": fmt, "gated": [], "stripped": [],
              "recipes": [], "advancements": [], "trades": [], "sweep": [], "unhandled": []}

    # loot tables
    recipe_ids_to_kill = set()
    loot_roots = [mcv / lay["loot"]]
    for extra in sorted((mcv / "datapacks").glob("*/data/minecraft/" + lay["loot"])):
        loot_roots.append(extra)  # built-in feature packs

    drop_rule = can_drop(vanilla, lay, data_version)
    seen = set()
    for root in loot_roots:
        if not root.is_dir():
            continue
        base_game = root == loot_roots[0]
        for src in sorted(root.rglob("*.json")):
            rel = src.relative_to(root)
            table = json.loads(src.read_text())
            if rel in seen:
                continue  # higher priority copy already written
            is_block_table = rel.parts[0] in ("blocks", "block")
            if is_block_table and find_items(table, gated):
                # Torch blocks keep their drop, gated to the End.
                if gate(table, gated, drop_rule):
                    strip_items(table, removed)
                    write_json(mc / lay["loot"] / rel, table)
                    report["gated"].append(str(rel))
                    seen.add(rel)
                continue
            if strip_items(table, locked):
                write_json(mc / lay["loot"] / rel, table)
                report["stripped"].append(str(rel) + ("" if base_game else f"  [{root.parents[2].name}]"))
                seen.add(rel)

    # recipes
    recipe_root = mcv / lay["recipe"]
    for src in sorted(recipe_root.rglob("*.json")):
        recipe = json.loads(src.read_text())
        result = recipe.get("result")
        rid = None
        if isinstance(result, dict):
            rid = result.get("id") or result.get("item")
        elif isinstance(result, str):
            rid = result
        if rid not in locked:
            continue
        blocked = make_impossible(recipe)
        rel = src.relative_to(recipe_root)
        if blocked is None:
            report["unhandled"].append(f"recipe {rel} (no ingredient field)")
            continue
        write_json(mc / lay["recipe"] / rel, blocked)
        recipe_ids_to_kill.add("minecraft:" + str(rel.with_suffix("")).replace("\\", "/"))
        report["recipes"].append(str(rel))

    # recipe book unlocks
    adv_root = mcv / lay["advancement"]
    for src in sorted(adv_root.rglob("*.json")):
        adv = json.loads(src.read_text())
        rewards = adv.get("rewards", {}).get("recipes", [])
        if not any(r in recipe_ids_to_kill for r in rewards):
            continue
        rel = src.relative_to(adv_root)
        write_json(mc / lay["advancement"] / rel, never_unlock(adv))
        report["advancements"].append(str(rel))

    # un-learn recipes players already knew
    fn = out / "data" / "dragonlight" / lay["function"] / "setup.mcfunction"
    fn.parent.mkdir(parents=True, exist_ok=True)
    fn.write_text(
        "# Un-learn the locked recipes.\n"
        + "".join(f"recipe take @a {r}\n" for r in sorted(recipe_ids_to_kill))
        + "schedule function dragonlight:setup 5s replace\n"
    )
    load = ["dragonlight:setup"]
    write_json(mc / "tags" / lay["function"] / "load.json", {"values": load})

    # villager trades, tag-driven since 26.1
    trade_root = mcv / "villager_trade"
    locked_trades = set()
    if trade_root.is_dir():
        for src in sorted(trade_root.rglob("*.json")):
            trade = json.loads(src.read_text())
            if find_items(trade.get("gives", {}), locked) or (
                isinstance(trade.get("gives"), dict) and trade["gives"].get("id") in locked
            ):
                rel = src.relative_to(trade_root).with_suffix("")
                locked_trades.add("minecraft:" + str(rel).replace("\\", "/"))

    emptied_tags = set()
    if locked_trades:
        tag_root = mcv / "tags" / "villager_trade"
        for src in sorted(tag_root.rglob("*.json")):
            tag = json.loads(src.read_text())
            values = tag.get("values", [])
            keep = [v for v in values if v not in locked_trades]
            if len(keep) == len(values):
                continue
            rel = src.relative_to(tag_root)
            # Tags merge, so removal means replacing the tag.
            write_json(mc / "tags" / "villager_trade" / rel, {"replace": True, "values": keep})
            tag_id = "#minecraft:" + str(rel.with_suffix("")).replace("\\", "/")
            report["trades"].append(f"{rel} (removed {len(values) - len(keep)})")
            if not keep:
                emptied_tags.add(tag_id)

    # An emptied pool draws nothing.
    for src in sorted((mcv / "trade_set").rglob("*.json")) if emptied_tags else []:
        ts = json.loads(src.read_text())
        if ts.get("trades") in emptied_tags:
            ts["amount"] = 0
            rel = src.relative_to(mcv / "trade_set")
            write_json(mc / "trade_set" / rel, ts)
            report["trades"].append(f"trade_set/{rel} (amount 0)")

    # Older versions hardcode trades, so take the purchase back instead.
    if not trade_root.is_dir():
        fdir = out / "data" / "dragonlight" / lay["function"]
        for item in LOCKED:
            if not (mcv / lay["loot"] / "blocks" / f"{item}.json").exists():
                continue  # not in this version
            write_json(
                out / "data" / "dragonlight" / lay["advancement"] / "trade" / f"{item}.json",
                {
                    "criteria": {"traded": {
                        "trigger": "minecraft:villager_trade",
                        "conditions": {"item": item_predicate(vanilla, lay, f"minecraft:{item}")},
                    }},
                    "requirements": [["traded"]],
                    "rewards": {"function": f"dragonlight:untrade/{item}"},
                },
            )
            (fdir / "untrade").mkdir(parents=True, exist_ok=True)
            (fdir / "collect").mkdir(parents=True, exist_ok=True)
            # The purchase is on the cursor at trigger time, so wait for it to land.
            (fdir / "untrade" / f"{item}.mcfunction").write_text(
                f"advancement revoke @s only dragonlight:trade/{item}\n"
                f"tag @s add dl_{item}\n"
                f"schedule function dragonlight:collect/{item} 1s replace\n"
            )
            (fdir / "collect" / f"{item}.mcfunction").write_text(
                f"execute as @a[tag=dl_{item}] run clear @s minecraft:{item} 1\n"
                f"tag @a remove dl_{item}\n"
            )
            report["sweep"].append(item)

    # report anything else mentioning a locked item
    for src in sorted((vanilla / "data").rglob("*.json")):
        rel = src.relative_to(vanilla / "data")
        parts = rel.parts
        if any(p in ("worldgen", "structure", "advancement", "advancements", "tags") for p in parts):
            continue
        if parts[1] in (lay["loot"], lay["recipe"]) if len(parts) > 1 else False:
            continue
        text = src.read_text()
        if parts[-2:-1] and parts[1] in (lay["loot"], lay["recipe"], "villager_trade", "trade_set"):
            continue
        if parts[0] == "minecraft" and parts[1] == "datapacks":
            shadowed = str(rel).split("/data/minecraft/", 1)[-1]
            handled = [x.split("  [")[0] for x in report["stripped"] + report["gated"]]
            if shadowed.split("/", 1)[-1] in handled:
                continue  # same id, base-game override wins
        hit = [i for i in locked if f'"{i}"' in text]
        if hit:
            report["unhandled"].append(f"{rel}: {', '.join(sorted(hit))}")

    write_json(out / "pack.mcmeta", {"pack": {
        "pack_format": fmt,
        "description": f"Dragonlight - torches only from the dragon. Built for {version}.",
    }})
    return out, report, fmt, data_version, lay, vanilla


def build_addons(version, fmt, data_version, lay, vanilla):
    """Build the opt-in add-on packs."""
    made = []
    mcv = vanilla / "data" / "minecraft"
    drop_rule = can_drop(vanilla, lay, data_version)

    # redstone torches
    red = BUILD / version / "redstone-torch-lock"
    if red.exists():
        shutil.rmtree(red)
    src = mcv / lay["loot"] / "blocks" / "redstone_torch.json"
    if src.exists():
        table = json.loads(src.read_text())
        gate(table, {"minecraft:redstone_torch"}, drop_rule)
        write_json(red / "data" / "minecraft" / lay["loot"] / "blocks" / "redstone_torch.json", table)
        rsrc = mcv / lay["recipe"] / "redstone_torch.json"
        if rsrc.exists():
            blocked = make_impossible(json.loads(rsrc.read_text()))
            if blocked:
                write_json(red / "data" / "minecraft" / lay["recipe"] / "redstone_torch.json", blocked)
        write_json(red / "pack.mcmeta", {"pack": {
            "pack_format": fmt,
            "description": "Dragonlight add-on - redstone torches are dragon-only too",
        }})
        made.append(("redstone-torch-lock", red))

    return made


def main():
    versions = sys.argv[1:] or VERSIONS
    DIST.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:  # prefetch
        list(pool.map(fetch_vanilla, versions))

    reports = []
    for version in versions:
        out, report, fmt, dv, lay, vanilla = build(version)
        zip_dir(out, DIST / f"Dragonlight-{version}.zip")
        for name, folder in build_addons(version, fmt, dv, lay, vanilla):
            zip_dir(folder, DIST / f"Dragonlight-{version}-{name}.zip")
        reports.append(report)
        print(f"{version:8} fmt {fmt:>3}  gated {len(report['gated'])}  "
              f"loot {len(report['stripped'])}  recipes {len(report['recipes'])}  "
              f"advs {len(report['advancements'])}  trades {len(report['trades'])}"
              + (f"  sweep {len(report['sweep'])}" if report["sweep"] else "")
              + (f"  UNHANDLED {report['unhandled']}" if report["unhandled"] else ""))
    (DIST / "coverage.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
