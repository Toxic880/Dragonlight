# Dragonlight

Minecraft, but you can only get torches by killing the ender dragon.

The four torches on the exit portal pillar are the only torches in the world. Mine them off the
pillar like normal — that's it, that's the only way to get one. Want more? Respawn the dragon
with four end crystals and the pillar's torches come back with it.

Java Edition datapack — no mods, works on servers.

## Install

Grab the zip for your version from `dist/` and drop it in your world's datapacks folder:

- Singleplayer: `.minecraft/saves/<world>/datapacks/`
- Server: `<world>/datapacks/`

Then `/reload`, or just restart the world. Starting a new world instead? Click **Data Packs**
on the world creation screen and drag the zip in.

Works on worlds you've already been playing.

## What changes

**Dragon-only** — torches, soul torches, copper torches, lanterns, soul lanterns and copper
lanterns. They still drop, but only when mined in the End.

**Gone** — candles, candle cakes, campfires and soul campfires. No recipes, no drops. Breaking
a campfire still gives you its charcoal.

**Untouched** — redstone torches, and every other light source (glowstone, sea lanterns,
shroomlight, froglights, end rods, copper bulbs).

That covers crafting, mining torches out of mineshafts and villages, chest loot in mineshafts,
trial chambers, ancient cities and savanna village houses, brushing trail ruins, and the
villager trades for campfires, lanterns and candles.

Two things to know: a torch you place outside the End can't be picked back up, and you can
steal the four fountain torches before you ever kill the dragon.

## Versions

1.16.5, 1.17.1, 1.18.2, 1.19.2, 1.19.4, 1.20.1, 1.20.4, 1.20.6, 1.21.1, 1.21.4, 1.21.5,
1.21.8, 1.21.11, 26.1.2, 26.2. Take the closest one at or below your version.

## Add-ons

Drop these in alongside the main pack, same version.

- `redstone-torch-lock` — locks redstone torches too.
- `lenient-recovery` — torches and lanterns drop again when you mine them, except inside
  mineshafts, strongholds, villages, igloos, mansions, outposts, ancient cities and trial
  chambers. Lets you pick your own torches back up. Needs 1.19+.

## Building

```bash
python3 tools/build_dragonlight.py 1.21.4
```

Pulls that version's vanilla data, rebuilds the packs into `dist/`, and writes
`dist/coverage.json` listing every file it patched. No arguments rebuilds everything. To change
what's locked, edit the `GATED` and `REMOVED` lists at the top of the script.
