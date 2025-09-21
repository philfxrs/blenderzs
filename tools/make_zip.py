"""将插件目录打包为可安装的 Zip。"""
from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
ADDON_DIR = ROOT / "addons" / "ai_modeler"


def make_zip(output: Path) -> None:
    if not ADDON_DIR.exists():
        raise SystemExit("未找到 addons/ai_modeler 目录")
    with ZipFile(output, "w", ZIP_DEFLATED) as zf:
        for path in ADDON_DIR.rglob("*"):
            if path.is_dir():
                continue
            arcname = Path("ai_modeler") / path.relative_to(ADDON_DIR)
            zf.write(path, arcname)
    print(f"已生成 {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="打包 AI Modeler 插件")
    parser.add_argument("--output", default=str(ROOT / "ai_modeler.zip"))
    args = parser.parse_args()
    make_zip(Path(args.output))


if __name__ == "__main__":
    main()
