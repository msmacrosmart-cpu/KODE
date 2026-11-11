"""Delivery contracts for the Omega 21 skin package (static; no Kodi runtime)."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / "ENTREGA_FINAL" / "PREVIEW_KODI.html"
DOCS = ROOT / "docs" / "skin-omega21"
EXPECTED_DOCS = [
    "ANALISE_INICIAL.md",
    "MAPA_REFERENCIAS_VISUAIS.md",
    "DESIGN_SYSTEM_ORIGINAL.md",
    "INVENTARIO_TELAS_KODI_OMEGA21.md",
    "COMPARATIVO_TELAS.md",
    "PLANO_DE_IMPLEMENTACAO.md",
    "RELATORIO_VALIDACAO_VISUAL.md",
    "RELATORIO_PERFORMANCE.md",
    "RELATORIO_BUILD_RELEASE.md",
    "CONFIGURACAO_RELEASE.md",
]
# Monochrome palette actually used by the preview (grays/black/white only).
ALLOWED_HEX = {
    "#000", "#0d0d0d", "#181818", "#1f1f1f", "#262626", "#2b2b2b",
    "#333", "#3a3a3a", "#3d3d3d", "#555", "#a6a6a6", "#d9d9d9",
    "#f2f2f2", "#fff",
}


class PreviewTest(unittest.TestCase):
    def test_preview_has_44_screens_and_no_external_deps(self):
        text = PREVIEW.read_text(encoding="utf-8")
        screens = re.findall(r"^\['([^']+)'", text, re.M)
        self.assertEqual(len(screens), 44)
        self.assertEqual(screens[0], "Aurora")
        self.assertEqual(screens[-1], "CPerf")
        self.assertEqual(re.findall(r"https?://[^\s\"'<>]+", text), [])
        self.assertNotIn("cdn", text.lower())
        self.assertNotIn("rocket-loader", text.lower())

    def test_preview_is_monochrome_and_covers_tv_filmes_series(self):
        text = PREVIEW.read_text(encoding="utf-8")
        found = set(re.findall(r"#[0-9a-fA-F]{3,8}\b", text))
        self.assertTrue(found.issubset(ALLOWED_HEX), found - ALLOWED_HEX)
        for label in ("TV ao vivo", "Filmes", "Séries", "Doramas", "Animes", "Novelas", "Desenhos"):
            self.assertIn(label, text)


class DocsTest(unittest.TestCase):
    def test_all_delivery_docs_exist(self):
        for name in EXPECTED_DOCS:
            with self.subTest(doc=name):
                self.assertTrue((DOCS / name).is_file(), name)
                self.assertGreater((DOCS / name).stat().st_size, 500, name)


class ZipBuildTest(unittest.TestCase):
    def test_build_script_produces_valid_skin_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "SKIN_KODI_OMEGA21.zip"
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools/kodi/build-skin-zip.py"), "--output", str(out)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(out) as zf:
                names = zf.namelist()
                self.assertIn("skin.novatv/addon.xml", names)
                self.assertTrue(all(n.startswith("skin.novatv/") for n in names))
                self.assertFalse(any(n.startswith("skin.novatv/docs/") for n in names))
                self.assertFalse(any(n == "skin.novatv/README.md" for n in names))


if __name__ == "__main__":
    unittest.main()
