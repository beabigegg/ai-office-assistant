#!/usr/bin/env python
"""
Mermaid Diagram Renderer
========================
Render Mermaid syntax to PNG using Playwright (headless Chromium).

Usage:
  # From CLI
  python mermaid_render.py render --input diagram.mmd --output diagram.png
  python mermaid_render.py render --input diagram.mmd --output diagram.png --theme dark --scale 2
  python mermaid_render.py render --code "graph TD; A-->B" --output diagram.png

  # From Python
  from shared.tools.mermaid_render import render_mermaid
  render_mermaid("graph TD\\n  A-->B", "output.png", theme="default", scale=2)

Requires: playwright (pip install playwright && playwright install chromium)
"""

import argparse
import sys
import tempfile
from pathlib import Path

# HTML template with Mermaid CDN
_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: {bg_color};
    font-family: "Microsoft JhengHei", "Noto Sans TC", "Segoe UI", sans-serif;
    display: inline-block;
  }}
  #container {{
    display: inline-block;
    padding: {padding}px;
  }}
</style>
</head>
<body>
<div id="container">
<pre class="mermaid">
{mermaid_code}
</pre>
</div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: '{theme}',
    flowchart: {{ useMaxWidth: false }},
    sequence: {{ useMaxWidth: false }},
    gantt: {{ useMaxWidth: false }}
  }});
  mermaid.run().then(() => {{
    document.title = 'RENDER_DONE';
  }}).catch((err) => {{
    document.title = 'RENDER_ERROR';
    document.body.innerText = 'Mermaid Error: ' + err.message;
  }});
</script>
</body>
</html>"""

# Theme configs
_THEMES = {
    "default": {"mermaid_theme": "default", "bg": "white"},
    "dark": {"mermaid_theme": "dark", "bg": "#1a1a2e"},
    "forest": {"mermaid_theme": "forest", "bg": "white"},
    "neutral": {"mermaid_theme": "neutral", "bg": "white"},
}


def render_mermaid(
    code: str,
    output_path: str,
    theme: str = "default",
    scale: int = 2,
    padding: int = 20,
    timeout_ms: int = 15000,
) -> Path:
    """Render Mermaid code to PNG.

    Args:
        code: Mermaid diagram syntax (e.g. "graph TD\\n  A-->B")
        output_path: Where to save the PNG
        theme: One of "default", "dark", "forest", "neutral"
        scale: Device scale factor (2 = retina quality)
        padding: Padding around diagram in pixels
        timeout_ms: Max wait for render in milliseconds

    Returns:
        Path to the saved PNG file

    Raises:
        RuntimeError: If Mermaid rendering fails
        TimeoutError: If rendering exceeds timeout
    """
    from playwright.sync_api import sync_playwright

    theme_cfg = _THEMES.get(theme, _THEMES["default"])
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Generate HTML
    html = _HTML_TEMPLATE.format(
        mermaid_code=code,
        theme=theme_cfg["mermaid_theme"],
        bg_color=theme_cfg["bg"],
        padding=padding,
    )

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", encoding="utf-8", delete=False
    ) as f:
        f.write(html)
        html_path = Path(f.name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(device_scale_factor=scale)

            file_url = f"file:///{html_path.as_posix()}"
            page.goto(file_url)

            # Wait for Mermaid to finish rendering
            try:
                page.wait_for_function(
                    'document.title === "RENDER_DONE" || document.title === "RENDER_ERROR"',
                    timeout=timeout_ms,
                )
            except Exception:
                browser.close()
                raise TimeoutError(
                    f"Mermaid rendering did not complete within {timeout_ms}ms"
                )

            title = page.title()
            if title == "RENDER_ERROR":
                err_text = page.inner_text("body")
                browser.close()
                raise RuntimeError(f"Mermaid rendering failed: {err_text}")

            # Get bounding box of the container for tight crop
            container = page.query_selector("#container")
            if container:
                bbox = container.bounding_box()
                if bbox:
                    # Add small margin
                    clip = {
                        "x": max(0, bbox["x"] - 2),
                        "y": max(0, bbox["y"] - 2),
                        "width": bbox["width"] + 4,
                        "height": bbox["height"] + 4,
                    }
                    page.screenshot(path=str(output), clip=clip)
                else:
                    page.screenshot(path=str(output), full_page=True)
            else:
                page.screenshot(path=str(output), full_page=True)

            browser.close()
    finally:
        html_path.unlink(missing_ok=True)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Render Mermaid diagrams to PNG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    render_cmd = sub.add_parser("render", help="Render a Mermaid diagram")
    input_group = render_cmd.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input", "-i", type=str, help="Path to .mmd file with Mermaid code"
    )
    input_group.add_argument("--code", "-c", type=str, help="Mermaid code string")
    render_cmd.add_argument(
        "--output", "-o", type=str, required=True, help="Output PNG path"
    )
    render_cmd.add_argument(
        "--theme",
        "-t",
        choices=list(_THEMES.keys()),
        default="default",
        help="Mermaid theme (default: default)",
    )
    render_cmd.add_argument(
        "--scale",
        "-s",
        type=int,
        default=2,
        help="Device scale factor for retina output (default: 2)",
    )
    render_cmd.add_argument(
        "--padding",
        type=int,
        default=20,
        help="Padding around diagram in px (default: 20)",
    )

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "render":
        if args.input:
            code = Path(args.input).read_text(encoding="utf-8")
        else:
            code = args.code

        try:
            out = render_mermaid(
                code,
                args.output,
                theme=args.theme,
                scale=args.scale,
                padding=args.padding,
            )
            print(f"OK: {out}")
        except (RuntimeError, TimeoutError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
