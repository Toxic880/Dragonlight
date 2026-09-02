# Dragonlight

Minecraft datapack. You can only get torches by killing the ender dragon.

The four torches on the exit portal pillar are the only ones in the world. Mine them off the
pillar. Respawn the dragon with four end crystals to get four more.

## Install

Download the zip for your version from `dist/` and put it in your world's datapacks folder.

- Singleplayer: `.minecraft/saves/<world>/datapacks/`
- Server: `<world>/datapacks/`

Run `/reload` or restart the world. Works on existing worlds.

## What it changes

You can't craft these, and the ones that generate in mineshafts, villages, strongholds, igloos,
mansions, outposts, ancient cities and trial chambers won't drop when you mine them:

torch, soul torch, copper torch, lantern, soul lantern, copper lantern.

Torches you place yourself drop normally, so you can pick them back up and move them around.
The exception is if you place one inside one of those structures.

Gone completely, no recipe and no drops: candles, candle cakes, campfires, soul campfires.

All of the above is also taken out of chest loot, trail ruins brushing, and villager trades.

Redstone torches and other light sources are untouched.

## Supported versions

1.16.5, 1.17.1, 1.18.2, 1.19.2, 1.19.4, 1.20.1, 1.20.4, 1.20.6, 1.21.1, 1.21.4, 1.21.5,
1.21.8, 1.21.11, 26.1.2, 26.2

Use the closest version at or below yours.

## Add-ons

Optional. Install next to the main pack, same version.

- `redstone-torch-lock`: locks redstone torches the same way.

## Building

```bash
python3 tools/build_dragonlight.py 1.21.4
```

Rebuilds the packs into `dist/`. Run it with no arguments to rebuild every version.
