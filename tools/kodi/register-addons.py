#!/usr/bin/env python3
"""Registra skin.novatv, plugin.video.smarted e service.smarted.bootstrap
no addon-manifest.xml e addons.txt do fonte do Kodi."""

import sys

manifest_path = sys.argv[1]
addons_txt_path = sys.argv[2]
addons = ["skin.novatv", "plugin.video.smarted", "service.smarted.bootstrap"]

# --- addon-manifest.xml ---
with open(manifest_path, encoding="utf-8") as f:
    text = f.read()
for addon in addons:
    tag = "  <addon>" + addon + "</addon>"
    if tag not in text:
        anchor = "  <addon>skin.estuary</addon>"
        if anchor in text:
            text = text.replace(anchor, anchor + "\n" + tag, 1)
        else:
            text = text.replace("</addons>", tag + "\n</addons>", 1)
        print("  ok manifest: " + addon + " registrado")
    else:
        print("  -- manifest: " + addon + " já presente")
with open(manifest_path, "w", encoding="utf-8") as f:
    f.write(text)

# --- addons.txt ---
with open(addons_txt_path, encoding="utf-8") as f:
    lines = f.readlines()
for addon in addons:
    entry = "addons/" + addon + "/*"
    if not any(entry in line for line in lines):
        insert_at = None
        for i, line in enumerate(lines):
            if line.startswith("addons/skin.estuary/"):
                insert_at = i
                break
        if insert_at is not None:
            lines.insert(insert_at, entry + "\n")
        else:
            lines.append(entry + "\n")
        print("  ok addons.txt: " + entry + " adicionado")
    else:
        print("  -- addons.txt: " + entry + " já presente")
with open(addons_txt_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("--- addon-manifest.xml (últimas linhas) ---")
with open(manifest_path, encoding="utf-8") as f:
    print("".join(f.readlines()[-10:]))
print("--- addons.txt (entradas skin/addon) ---")
with open(addons_txt_path, encoding="utf-8") as f:
    for line in f:
        if "addons/skin" in line or "addons/plugin.video.smarted" in line or "addons/service.smarted.bootstrap" in line:
            print(line.rstrip())
