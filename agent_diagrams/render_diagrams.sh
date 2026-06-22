#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$ROOT_DIR/rendered"
CONFIG_FILE="$ROOT_DIR/puppeteer-config.json"

mkdir -p "$OUT_DIR"

render_chart() {
  input_file="$1"
  base_name="$2"
  width="$3"
  height="$4"
  mmdc -i "$input_file" -o "$OUT_DIR/$base_name.png" -b transparent -w "$width" -H "$height" -p "$CONFIG_FILE"
  if [ -f "$OUT_DIR/${base_name}-1.png" ]; then
    mv "$OUT_DIR/${base_name}-1.png" "$OUT_DIR/$base_name.png"
  fi
}

render_chart "$ROOT_DIR/catalog_runtime.md" catalog_runtime 2400 2600
render_chart "$ROOT_DIR/baseagent_inheritance.md" baseagent_inheritance 2600 2600
render_chart "$ROOT_DIR/scenario_rootcause_fix_map.md" scenario_rootcause_fix_map 2800 3600
render_chart "$ROOT_DIR/catalog_deep_flow.md" catalog_deep_flow 2800 3200
render_chart "$ROOT_DIR/autocomplete_deep_flow.md" autocomplete_deep_flow 2800 3000
render_chart "$ROOT_DIR/merchandising_deep_flow.md" merchandising_deep_flow 2800 3000
render_chart "$ROOT_DIR/semantic_deep_flow.md" semantic_deep_flow 2800 3000
render_chart "$ROOT_DIR/catalog_variants.md" catalog_variants 2400 2200
render_chart "$ROOT_DIR/autocomplete_runtime.md" autocomplete_runtime 2400 2200
render_chart "$ROOT_DIR/merchandising_runtime.md" merchandising_runtime 2400 2200
render_chart "$ROOT_DIR/semantic_runtime.md" semantic_runtime 2400 2200
render_chart "$ROOT_DIR/temporal_runtime.md" temporal_runtime 2600 3200
