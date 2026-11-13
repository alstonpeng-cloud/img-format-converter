# img-format-converter

一个基于 Python + Pillow 的图片格式互相转换命令行工具。支持单张、批量、目录递归转换，以及缩放、质量调节等常用处理。

## 特性

- 支持 **PNG / JPEG / WebP / BMP / GIF / TIFF / ICO** 之间互转
- 批量转换整个目录，`-r` 递归子目录
- `--resize` 保持宽高比缩放（只缩不放）
- `-q` 调节 JPEG / WebP 质量，压缩比一目了然
- 透明图转 JPEG / BMP 时自动铺白底，避免黑块
- 自动生成 ICO 图标（超过 256px 自动缩小）
- 转换前检查输出文件是否存在，需要时用 `--overwrite` 显式覆盖

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 单张转换：png -> webp
python imgconv.py photo.png -t webp

# 批量转换目录到指定输出目录，质量 85
python imgconv.py ./images -t jpg -q 85 -o ./out

# 递归处理子目录，并缩放到宽 1280 以内
python imgconv.py ./photos -t png -r --resize 1280x

# 生成网站图标（自动限制在 256x256 内）
python imgconv.py logo.png -t ico

# 查看支持的格式
python imgconv.py --list-formats
```

### 参数说明

| 参数 | 说明 |
| --- | --- |
| `inputs` | 待转换的图片文件或目录，可传多个 |
| `-t, --to` | 目标格式，如 `png` / `jpg` / `webp` / `bmp` / `gif` / `tiff` / `ico` |
| `-o, --output` | 输出目录，默认与源文件同目录 |
| `-q, --quality` | JPEG / WebP 质量，1-100，默认 90 |
| `--resize WxH` | 按比例缩放到指定范围，支持 `1280x720`、`1280x`、`x720` |
| `-r, --recursive` | 递归处理子目录 |
| `--overwrite` | 允许覆盖已存在的输出文件 |
| `-f, --force-same` | 源格式与目标格式相同时也重新编码 |
| `--list-formats` | 列出支持的格式 |
| `-v, --verbose` | 输出更多处理细节 |

## 支持格式

| 目标别名 | Pillow 格式 | 说明 |
| --- | --- | --- |
| `png` | PNG | 支持透明 |
| `jpg` / `jpeg` | JPEG | 不支持透明，透明区域铺白底 |
| `webp` | WEBP | 支持透明，压缩率高 |
| `bmp` | BMP | 无压缩，不支持透明 |
| `gif` | GIF | 输出静态 GIF（不支持动图转换） |
| `tif` / `tiff` | TIFF | 无损 |
| `ico` | ICO | 自动限制在 256px 内 |

## 说明

- 动图（GIF / WebP 动画）只会转换第一帧，本工具定位是静态图片格式转换。
- CMYK 图片转换前会由 Pillow 自动处理为 RGB。

## 许可证

[MIT](LICENSE)
