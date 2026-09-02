# Pellier Workshop Architecture Diagrams

This directory is the source of truth for the governed workshop architecture
diagrams. The diagrams use Graphviz so the source, generated assets, and
participant-facing variants stay reviewable and reproducible.

## Contents

- `sources/` contains six hand-authored Graphviz diagrams.
- `render.py` renders every source to SVG and PNG.
- `generated-assets/` contains the checked-in source-repository output.
- `tests/` checks syntax, required architecture labels, and deterministic
  rendering.

The palette mirrors Pellier's Daylight tokens:

| Role | Color |
|---|---|
| Linen background | `#f7f3ec` |
| Paper surface | `#fbf8f2` |
| Espresso ink | `#1f1410` |
| Terracotta action | `#9a3412` |
| Verified state | `#3f6212` |
| Denied state | `#991b1b` |
| Managed Memory | `#6b21a8` |

## Render

Render into the checked-in source output directory:

```bash
python3 workshop/architecture-diagrams/render.py
```

Render directly into a Workshop Studio asset directory:

```bash
python3 workshop/architecture-diagrams/render.py \
  --output-dir /path/to/workshop-studio/static/architecture
```

Verify that checked-in assets match the current Graphviz sources:

```bash
python3 workshop/architecture-diagrams/render.py --check
```

Run the focused checks:

```bash
python3 -m unittest discover \
  -s workshop/architecture-diagrams/tests \
  -p 'test_*.py'
```

The renderer requires the `dot` executable. It sets a fixed locale, timezone,
source epoch, layout size, and DPI. SVG generator-version comments are removed
so assets do not change solely because the Graphviz patch version changed.
