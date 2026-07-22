# HF Cachelight

HF Cachelight is a dependency-free desktop visualizer for Hugging Face caches. It scans the cache with Python's standard library, lists cached models and datasets by size, and presents the results as an interactive treemap.

The application is intentionally read-only. It never deletes cache files. Double-click a list row or treemap block to reveal that cache folder in Dolphin, then manage it using the file manager you already trust.

## Highlights

- One standalone Python entry point: `hf_cachelight.py`
- Python standard library only; no pip packages or virtual environment
- Dark blue custom Tkinter interface with rounded panels, shadows, hover states, and a colorful treemap
- Models and Datasets tabs
- Search and sorting by size, name, or modified time
- Progressive background scanning, progress feedback, and cancellation
- Dataset entries from `hub/datasets--...` and processed `datasets/...` are combined when their repository names match
- `xet`, lock files, tokens, and other cache contents are summarized as **Other Cache**
- Physical allocated size is used on Unix filesystems when available
- Symlink targets are not followed, avoiding duplicate snapshot weight counts
- No network access, Hugging Face login, or remote API calls

## Requirements

- Python 3.9 or newer
- Tcl/Tk 8.6 or newer
- Dolphin for folder selection, or `xdg-open` as a fallback

Tkinter belongs to Python's standard library, but Arch Linux packages the underlying Tk toolkit separately:

```bash
sudo pacman -S tk
```

No Python packages need to be installed.

## Run

```bash
python3 hf_cachelight.py
```

Or make it executable:

```bash
chmod +x hf_cachelight.py
./hf_cachelight.py
```

On first launch, the application checks `/mnt/8TB_HDD/hf_cache` and then `~/.cache/huggingface`. Choose another folder with **Browse** whenever needed.

The last cache path, sort mode, and window geometry are stored in:

```text
~/.config/hf-cachelight/settings.json
```

## KDE double-click setup

Dolphin may ask what should open a `.py` file. The safest options are:

1. Run the script from a terminal using the commands above.
2. Mark it executable and choose **Execute** in Dolphin.
3. Create a normal KDE application launcher whose command is:

```text
python3 /full/path/to/hf_cachelight.py
```

## Controls

| Action | Mouse or keyboard |
|---|---|
| Select a cache folder | Click a list row or treemap block |
| Open in Dolphin | Double-click an item, press Enter in the list, or use the detail button |
| Search | `Ctrl+F` |
| Focus cache path | `Ctrl+L` |
| Rescan | `Ctrl+R` or `F5` |
| Clear search / stop scan | `Escape` |
| Context menu | Right-click a list row |

## Cache interpretation

The scanner recognizes these layouts:

```text
hf_cache/
├── hub/
│   ├── models--owner--repository/
│   └── datasets--owner--repository/
├── datasets/
│   └── owner___repository/
└── xet/
```

A model's displayed size is the allocated disk space within its outer `models--...` directory. A dataset can occupy both the Hub cache and the processed datasets cache; matching names are combined into one entry and the larger location is used when opening Dolphin.

The scanner uses `os.scandir()` in a worker thread. It reads filesystem metadata only and never opens model weight contents.

## Project files

- `hf_cachelight.py` — complete standalone application
- `DESIGN.md` — visual and interaction design decisions
- `LICENSE` — MIT license
