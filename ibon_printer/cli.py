"""命令列介面：上傳單一檔案並印出取件編號與期限。"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import traceback
from pathlib import Path
from typing import Sequence

from .client import IbonClient, IbonUploadResult, PrintSpec
from .errors import IbonRequestError, IbonValidationError

# 將 CLI 友善別名映射成完整 SelectType 字串。傳入未列出的別名時，
# 視為已是 SelectType 字串（例：``--spec FA3CN2``），原樣轉送。
_SPEC_ALIASES: dict[str, PrintSpec] = {
    "default": PrintSpec.default(),
    "a4": PrintSpec.a4(),
    "a4-color": PrintSpec.a4(color=True),
    "a4-duplex": PrintSpec.a4(duplex=True),
    "a4-color-duplex": PrintSpec.a4(color=True, duplex=True),
    "a4-special": PrintSpec.a4(special_paper=True),
    "a4-color-special": PrintSpec.a4(color=True, special_paper=True),
    "a4-color-duplex-special": PrintSpec.a4(
        color=True, duplex=True, special_paper=True
    ),
    "a3": PrintSpec.a3(),
    "a3-color": PrintSpec.a3(color=True),
    "a3-duplex": PrintSpec.a3(duplex=True),
    "a3-color-duplex": PrintSpec.a3(color=True, duplex=True),
    "photo-4x6": PrintSpec.photo_4x6(),
    "sticker-4x6": PrintSpec.sticker_4x6(),
}


def _resolve_spec(raw: str | None) -> PrintSpec:
    if not raw:
        return PrintSpec.default()
    key = raw.strip().lower()
    if key in _SPEC_ALIASES:
        return _SPEC_ALIASES[key]
    # 未列入 alias 時視為原始 SelectType 字串。
    return PrintSpec(raw.strip(), description=raw.strip())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ibon-printer",
        description="上傳單一檔案至 7-11 ibon 雲端列印並取得取件編號。",
    )
    parser.add_argument("file", help="要上傳的檔案路徑")
    parser.add_argument("--name", default=" ", help="轉送給 ibon 的寄件人姓名")
    parser.add_argument("--email", default=" ", help="轉送給 ibon 的寄件人 email")
    parser.add_argument(
        "--spec",
        default=None,
        help=(
            "預選列印規格。可用 alias（例：a3-color-duplex、a4-color、photo-4x6），"
            "或直接傳 ibon SelectType 字串（例：FA3CN2）。預設為 FNOMAL（不預選）。"
        ),
    )
    parser.add_argument(
        "--qr-out",
        default=None,
        help="把 client 端產生的 QR Code PNG 寫到指定路徑；未給時不寫檔。",
    )
    parser.add_argument("--json", action="store_true", help="以單行 JSON 取代文字輸出")
    parser.add_argument("--debug", action="store_true", help="失敗時印出 traceback")
    return parser


def _format_text(
    result: IbonUploadResult, spec: PrintSpec, qr_path: Path | None = None
) -> str:
    lines = [
        f"取件編號: {result.pincode}",
        f"列印期限: {result.deadline.isoformat()}",
    ]
    if spec.select_type != "FNOMAL":
        lines.append(f"列印規格: {spec.description or spec.select_type}")
    if qr_path is not None:
        lines.append(f"QR PNG: {qr_path}")
    return "\n".join(lines)


def _format_json(
    result: IbonUploadResult, spec: PrintSpec, qr_path: Path | None = None
) -> str:
    payload = {
        "pincode": result.pincode,
        "deadline": result.deadline.isoformat(),
        "select_type": spec.select_type,
        "qrcode_base64": result.qrcode_base64,
    }
    if spec.description:
        payload["spec_description"] = spec.description
    if qr_path is not None:
        payload["qrcode_path"] = str(qr_path)
    return json.dumps(payload, ensure_ascii=False)


def _handle_error(exc: BaseException, debug: bool) -> int:
    if isinstance(exc, IbonValidationError):
        print(f"驗證錯誤：{exc}", file=sys.stderr)
        if debug:
            traceback.print_exc(file=sys.stderr)
        return 2
    if isinstance(exc, IbonRequestError):
        print(f"請求錯誤：{exc}", file=sys.stderr)
        if debug:
            traceback.print_exc(file=sys.stderr)
        return 1
    print(f"未預期錯誤：{exc}", file=sys.stderr)
    if debug:
        traceback.print_exc(file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    spec = _resolve_spec(args.spec)
    try:
        client = IbonClient()
        result = client.upload(args.file, user=args.name, email=args.email, spec=spec)
    except (IbonValidationError, IbonRequestError) as exc:
        return _handle_error(exc, args.debug)
    except Exception as exc:  # noqa: BLE001 — CLI 必須優雅退場
        return _handle_error(exc, args.debug)

    qr_path: Path | None = None
    if args.qr_out:
        qr_path = Path(args.qr_out)
        png_bytes = base64.b64decode(result.qrcode_base64) if result.qrcode_base64 else b""
        qr_path.write_bytes(png_bytes)
        if not result.qrcode_base64:
            print(
                f"QR Code generation failed; wrote zero-byte file at {qr_path}",
                file=sys.stderr,
            )

    if args.json:
        print(_format_json(result, spec, qr_path))
    else:
        print(_format_text(result, spec, qr_path))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
