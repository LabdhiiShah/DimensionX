"""Scan DimensionX semantic DXF files and generate architecture JSON at runtime.

Default:
    python tools/scan_dxf_folder.py

Custom folder:
    python tools/scan_dxf_folder.py --input "C:/path/to/dxf_folder" --output "C:/path/to/json_output"

Requires Python 3.10+ and ezdxf. This reader targets the DimensionX DX_* layer
and DIMENSIONX XDATA contract. It does not infer architectural meaning from an
arbitrary third-party DXF whose entities have unrelated layers/metadata.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONVERTER = Path(__file__).with_name("dimensionx_dxf_to_json.py")
DEFAULT_INPUT = PACKAGE_ROOT / "plans"
DEFAULT_OUTPUT = PACKAGE_ROOT / "generated_json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan DXF floor plans and generate matching architecture JSON files."
    )
    parser.add_argument(
        "--input", "-i", type=Path, default=DEFAULT_INPUT,
        help=f"Folder to scan recursively (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=DEFAULT_OUTPUT,
        help=f"Output folder for generated JSON (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="Stop on the first DXF that cannot be converted.",
    )
    args = parser.parse_args()

    input_dir = args.input.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"ERROR: input folder does not exist: {input_dir}", file=sys.stderr)
        return 2
    if not CONVERTER.is_file():
        print(f"ERROR: converter not found: {CONVERTER}", file=sys.stderr)
        return 2

    dxfs = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".dxf")
    if not dxfs:
        print(f"ERROR: no .dxf files found under {input_dir}", file=sys.stderr)
        return 2

    succeeded = []
    failed = []
    print(f"Input DXF folder: {input_dir}")
    print(f"JSON output folder: {output_dir}")
    print(f"Found {len(dxfs)} DXF files. JSON files will be generated now.\n")

    for index, dxf_path in enumerate(dxfs, 1):
        relative = dxf_path.relative_to(input_dir)
        json_path = output_dir / relative.parent / f"{dxf_path.stem}_architecture.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{index:02d}/{len(dxfs):02d}] {relative}")

        result = subprocess.run(
            [sys.executable, str(CONVERTER), str(dxf_path), "--output", str(json_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0 and json_path.is_file():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                summary = (
                    f"BHK={data['bhk']} | walls={len(data['walls'])} | "
                    f"doors={len(data['doors'])} | windows={len(data['windows'])} | "
                    f"rooms={len(data['rooms'])} | balconies={len(data.get('balconies', []))}"
                )
                print(f"    JSON created: {json_path}\n    {summary}")
                succeeded.append((dxf_path, json_path))
            except Exception as exc:
                failed.append((dxf_path, f"generated JSON could not be read: {exc}"))
                print(f"    ERROR: generated JSON could not be read: {exc}")
                if args.fail_fast:
                    break
        else:
            message = (result.stderr or result.stdout or "converter failed").strip()
            failed.append((dxf_path, message))
            print(f"    ERROR: {message}")
            if args.fail_fast:
                break
        print()

    print("=" * 66)
    print(f"DXF files scanned: {len(dxfs)}")
    print(f"JSON files created: {len(succeeded)}")
    print(f"Failed conversions: {len(failed)}")
    print(f"Output: {output_dir}")

    if failed:
        print("\nFailed files:")
        for path, message in failed:
            print(f"- {path}: {message.splitlines()[-1] if message else 'unknown error'}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
