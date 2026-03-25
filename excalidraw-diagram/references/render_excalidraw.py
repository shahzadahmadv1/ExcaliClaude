#!/usr/bin/env python3
"""Render .excalidraw files to PNG using Excalidraw's export utility."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright

    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


EXCALIDRAW_VERSION = "0.18.0"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      margin: 0;
      padding: 24px;
      background: #ffffff;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
      box-sizing: border-box;
    }}
    img {{
      display: block;
      max-width: none;
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <img id="output" alt="Excalidraw render" />
  <script type="module">
    window.ready = false;
    window.renderError = null;

    try {{
      const sceneData = {scene_json};
      const {{ exportToBlob }} = await import("https://esm.sh/@excalidraw/excalidraw@{excalidraw}?bundle");
      const blob = await exportToBlob({{
        elements: sceneData.elements || [],
        appState: {{
          ...(sceneData.appState || {{}}),
          exportBackground: true,
          exportWithDarkMode: false,
          viewBackgroundColor: "#ffffff",
        }},
        files: sceneData.files || {{}},
        exportPadding: 32,
        maxWidthOrHeight: 2400,
      }});

      const img = document.getElementById("output");
      img.src = URL.createObjectURL(blob);
      await img.decode();
      window.ready = true;
    }} catch (error) {{
      window.renderError = error && error.stack ? error.stack : String(error);
    }}
  </script>
</body>
</html>"""


def render(filepath: str) -> str:
    """Render .excalidraw to PNG. Returns output PNG path."""
    if not HAS_PLAYWRIGHT:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium"
        )

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    scene_data = json.loads(path.read_text(encoding="utf-8"))
    page_html = HTML_TEMPLATE.format(
        excalidraw=EXCALIDRAW_VERSION,
        scene_json=json.dumps(scene_data),
    )

    output_path = path.with_suffix(".png")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 2800, "height": 2200}, device_scale_factor=2)
        page.set_content(page_html)
        page.wait_for_function("window.ready === true || window.renderError !== null", timeout=15000)
        render_error = page.evaluate("window.renderError")
        if render_error:
            raise RuntimeError(render_error)
        page.locator("#output").screenshot(path=str(output_path))
        browser.close()

    return str(output_path)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python render_excalidraw.py <file.excalidraw>")
        return 1

    try:
        output = render(sys.argv[1])
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Rendered: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
