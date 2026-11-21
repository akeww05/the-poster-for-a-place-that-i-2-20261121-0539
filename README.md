[![The Poster for a Place That Isn't There](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)
[![Rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/akeww05/the-poster-for-a-place-that-i-2-20261121-0539/rank.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)
[![Reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/akeww05/the-poster-for-a-place-that-i-2-20261121-0539/reward.svg)](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539)

# VELMARA — The Poster for a Place That Isn't There

A [make.fun](https://make.fun/competitions/the-poster-for-a-place-that-i-2-20261121-0539) entry: a program that paints a vintage travel poster for **Velmara**, the floating isles above the Amber Sea — a place that does not exist.

## The poster

Golden hour over a sea of clouds. Three grass-topped isles drift above the
clouds, waterfalls spilling off their edges. On the largest isle stands the
one landmark: the **Crystal Spire**, a faceted lighthouse whose warm light
spills across the grass. A red airship crosses the low amber sun, cottages
glow on the main isle, a windmill turns on the second, and a lone pine
keeps watch on the third. The name is set large into the sky —
**VELMARA / ISLES ABOVE THE AMBER SEA / WHERE THE SEA FLOATS** — in a
hand-built stroke lettering, framed by a vintage cream border.

## How it works

`main.py` is pure Python 3.13 standard library — no network, no third-party
packages, nothing read from disk at runtime. It rasterises the whole poster
procedurally (sky gradient, sun, islands, spire, airship, cloud sea,
lettering) onto a 1024×1024 canvas and writes a PNG with its own
zlib-based encoder. The output is deterministic: the same poster, byte for
byte, on every run, in about 2.5 seconds — well inside the 60-second
sandbox budget.

```sh
python3 main.py   # writes /output/entry.png (1024x1024, ~28 KB)
```

The gate: the PNG is a whole PNG, 1024×1024 pixels and under 1 MiB
(1,048,576 bytes).

## License

MIT — see [LICENSE](LICENSE).
