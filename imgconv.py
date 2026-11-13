#!/usr/bin/env python3
"""imgconv - 一个简单的图片格式批量转换命令行工具。

依赖 Pillow，支持 PNG / JPEG / WebP / BMP / GIF / TIFF / ICO 之间的互转，
可批量处理目录、递归子目录、按比例缩放、质量调节。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image
except ImportError:  # pragma: no cover - 依赖缺失时给出友好提示
    sys.exit("缺少依赖 Pillow，请先执行：pip install -r requirements.txt")

# 格式别名 -> Pillow 格式名
FORMAT_ALIASES = {
    "png": ("PNG", ".png"),
    "jpg": ("JPEG", ".jpg"),
    "jpeg": ("JPEG", ".jpg"),
    "webp": ("WEBP", ".webp"),
    "bmp": ("BMP", ".bmp"),
    "gif": ("GIF", ".gif"),
    "tif": ("TIFF", ".tif"),
    "tiff": ("TIFF", ".tif"),
    "ico": ("ICO", ".ico"),
}

# 输入文件扫描时认作图片的扩展名
INPUT_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".jfif", ".webp",
    ".bmp", ".gif", ".tif", ".tiff", ".ico",
}

# 不支持透明通道的格式，转换时需要铺白底
NO_ALPHA_FORMATS = {"JPEG", "BMP"}


def parse_size(text: str) -> tuple[int | None, int | None]:
    """解析 --resize 参数，支持 800x600 / 800x / x600 三种写法。"""
    raw = text.lower().strip()
    if "x" not in raw:
        raise argparse.ArgumentTypeError("缩放尺寸格式应为 宽x高，例如 800x600、800x、x600")
    width_text, height_text = raw.split("x", 1)
    try:
        width = int(width_text) if width_text else None
        height = int(height_text) if height_text else None
    except ValueError:
        raise argparse.ArgumentTypeError("缩放尺寸必须是数字，例如 800x600") from None
    if width is None and height is None:
        raise argparse.ArgumentTypeError("缩放尺寸至少要指定宽或高之一")
    for value in (width, height):
        if value is not None and value <= 0:
            raise argparse.ArgumentTypeError("缩放尺寸必须大于 0")
    return width, height


def collect_inputs(paths: Iterable[str], recursive: bool) -> list[Path]:
    """把命令行传入的文件/目录展开成待处理的图片文件列表。"""
    files: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if path.is_file():
            if path.suffix.lower() in INPUT_EXTENSIONS:
                files.append(path)
            else:
                print(f"跳过（不是支持的图片格式）：{path}", file=sys.stderr)
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            files.extend(
                p for p in sorted(path.glob(pattern))
                if p.is_file() and p.suffix.lower() in INPUT_EXTENSIONS
            )
        else:
            print(f"跳过（路径不存在）：{path}", file=sys.stderr)
    # 去重并保持顺序
    seen: set[Path] = set()
    unique: list[Path] = []
    for item in files:
        resolved = item.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(item)
    return unique


def fit_size(
    size: tuple[int, int], box: tuple[int | None, int | None]
) -> tuple[int, int]:
    """在保持宽高比的前提下，把图片缩放到指定宽高范围内。"""
    width, height = size
    max_width, max_height = box
    if max_width is None and max_height is None:
        return width, height

    scale = None
    if max_width is not None:
        scale = max_width / width
    if max_height is not None:
        height_scale = max_height / height
        scale = height_scale if scale is None else min(scale, height_scale)
    assert scale is not None

    # 不放大，只缩小
    if scale >= 1:
        return width, height
    return max(1, round(width * scale)), max(1, round(height * scale))


def convert_one(
    src: Path,
    dest: Path,
    pil_format: str,
    quality: int,
    box: tuple[int | None, int | None],
) -> tuple[int, int]:
    """转换单张图片，返回 (原始字节数, 输出字节数)。"""
    with Image.open(src) as image:
        image.load()

        new_size = fit_size(image.size, box)
        if new_size != image.size:
            image = image.resize(new_size, Image.LANCZOS)

        has_alpha = image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        )
        if has_alpha:
            image = image.convert("RGBA")
            if pil_format in NO_ALPHA_FORMATS:
                # 无透明通道的格式：铺白底，避免出现黑块
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            elif pil_format == "ICO":
                image = image.convert("RGBA")
            else:
                image = image.convert("RGBA")
        elif pil_format in ("JPEG", "WEBP", "BMP", "GIF"):
            image = image.convert("RGB")
        elif pil_format == "ICO":
            image = image.convert("RGBA")

        save_kwargs: dict[str, object] = {}
        if pil_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = quality
        if pil_format == "JPEG":
            save_kwargs["optimize"] = True
        if pil_format == "ICO":
            # ICO 单边最大 256px
            if max(image.size) > 256:
                ratio = 256 / max(image.size)
                image = image.resize(
                    (max(1, round(image.width * ratio)), max(1, round(image.height * ratio))),
                    Image.LANCZOS,
                )

        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, pil_format, **save_kwargs)

    return src.stat().st_size, dest.stat().st_size


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imgconv",
        description="图片格式互相转换工具（支持批量、递归、缩放、质量调节）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  imgconv photo.png -t webp
  imgconv ./images -t jpg -q 85 -o ./out --resize 1280x
  imgconv a.png b.bmp ./pics -t png -r --overwrite
  imgconv --list-formats
""",
    )
    parser.add_argument("inputs", nargs="*", help="待转换的图片文件或目录（可多个）")
    parser.add_argument("-t", "--to", metavar="FORMAT", help="目标格式，如 png / jpg / webp / bmp / gif / tiff / ico")
    parser.add_argument("-o", "--output", metavar="DIR", help="输出目录，默认与源文件同目录")
    parser.add_argument("-q", "--quality", type=int, default=90, metavar="1-100", help="JPEG/WebP 质量，默认 90")
    parser.add_argument("--resize", type=parse_size, metavar="WxH", help="按比例缩放到指定范围，例如 1280x720、1280x、x720")
    parser.add_argument("-r", "--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的输出文件")
    parser.add_argument("-f", "--force-same", action="store_true", help="即使源格式与目标格式相同也重新编码")
    parser.add_argument("--list-formats", action="store_true", help="列出支持的格式后退出")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出更多处理细节")
    return parser


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}B"
        size /= 1024
    return f"{size:.1f}GB"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_formats:
        print("支持的目标格式：")
        for alias, (pil_name, ext) in FORMAT_ALIASES.items():
            print(f"  {alias:<6} -> {pil_name:<5} 扩展名 {ext}")
        return 0

    if not args.inputs:
        parser.error("请至少指定一个待转换的图片文件或目录")
    if not args.to:
        parser.error("请用 -t/--to 指定目标格式")

    target = args.to.lower().lstrip(".")
    if target not in FORMAT_ALIASES:
        parser.error(f"不支持的目标格式：{args.to}，可用：{', '.join(FORMAT_ALIASES)}")
    pil_format, target_ext = FORMAT_ALIASES[target]

    if not 1 <= args.quality <= 100:
        parser.error("质量参数必须在 1-100 之间")

    files = collect_inputs(args.inputs, args.recursive)
    if not files:
        print("没有找到可转换的图片文件。", file=sys.stderr)
        return 1

    output_dir = Path(args.output).expanduser() if args.output else None
    box = args.resize if args.resize else (None, None)

    converted = 0
    skipped = 0
    failed = 0
    total_before = 0
    total_after = 0

    for src in files:
        if src.suffix.lower() == target_ext and not args.force_same:
            skipped += 1
            if args.verbose:
                print(f"跳过（已是目标格式）：{src}")
            continue

        dest_dir = output_dir if output_dir else src.parent
        dest = dest_dir / f"{src.stem}{target_ext}"
        if dest.exists() and not args.overwrite:
            skipped += 1
            print(f"跳过（文件已存在，加 --overwrite 可覆盖）：{dest}", file=sys.stderr)
            continue

        try:
            before, after = convert_one(src, dest, pil_format, args.quality, box)
        except Exception as exc:  # noqa: BLE001 - CLI 场景下逐条汇报错误
            failed += 1
            print(f"失败：{src} -> {exc}", file=sys.stderr)
            continue

        converted += 1
        total_before += before
        total_after += after
        ratio = f"{(1 - after / before) * 100:+.0f}%" if before else "n/a"
        print(f"OK  {src} -> {dest}  {human_size(before)} -> {human_size(after)} ({ratio})")

    print(
        f"\n完成：成功 {converted} 张，跳过 {skipped} 张，失败 {failed} 张。"
        f" 总计 {human_size(total_before)} -> {human_size(total_after)}。"
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
