# HF Cachelight Design

## Product goal

HF Cachelight answers one question quickly: **which cached models or datasets are consuming the disk?**

The backend remains deliberately small. The product effort is concentrated in visual hierarchy, interaction, and making a standard-library Tkinter application feel like a polished KDE utility rather than a generic form.

## Visual direction

The application uses a deep blue-black foundation rather than neutral gray. Bright repository colors sit against quiet navy surfaces, borrowing Filelight's visual energy without copying its multi-ring hierarchy.

### Palette

| Role | Color |
|---|---|
| Window background | `#07111F` |
| Deep background | `#050C16` |
| Main surface | `#0C192A` |
| Elevated surface | `#102139` |
| Selected card | `#173653` |
| Border | `#203A58` |
| Primary text | `#EAF3FF` |
| Secondary text | `#8296AE` |
| Accent | `#55A8FF` |

The treemap uses sixteen stable jewel colors. A repository's name is hashed to a palette index, so its color stays consistent across scans and sorting changes.

## Layout

The window is divided into four visual zones:

1. **Header** — identity, cache total, cache path, Browse, and Rescan.
2. **Library panel** — Models/Datasets tabs, search, sorting, and custom rows.
3. **Storage panel** — treemap and category totals.
4. **Detail card** — selected folder share, size, file count, modified time, path, and Dolphin action.

The main panels live inside a resizable horizontal paned window. The library starts at roughly 390 pixels wide while the storage map receives most of the space.

## Custom drawing

Stock Tk controls are used only where they are strongest, chiefly the combobox, scrollbar, and progress bar. The major visual components are Canvas-based:

- Rounded cards and buttons
- Search and path fields
- Segmented tabs
- Scrollable cache rows
- Treemap cells and tooltips
- Selection ring and details card
- Application icon and loading indicator

Canvas drawing provides rounded corners, simulated shadows, subtle highlight gradients, stable colors, and precise spacing without third-party theme packages.

## Treemap

A squarified treemap was selected over a radial sunburst:

- Area maps directly to allocated size.
- Large repositories remain immediately recognizable.
- Roughly one hundred entries can coexist without a ring becoming a field of unreadable slivers.
- Clicking and hovering naturally map back to list items.

Each block receives dark spacing, a soft shadow, a top highlight, repository text when space permits, and a bright selection outline. Tiny blocks remain discoverable through hover tooltips.

## Library rows

Rows are drawn directly on a Canvas instead of using `ttk.Treeview`. Each row contains:

- Owner or source
- Repository name
- Human-readable size
- A proportional color bar
- Hover and selected states

This keeps the visual language consistent with the treemap and avoids native-theme inconsistencies.

## Filesystem model

The application scans outer cache directories only:

- `hub/models--*`
- `hub/datasets--*`
- top-level processed `datasets/*`

Directory walking uses `os.scandir()` and does not follow symlinks. On Unix, `st_blocks × 512` is used when available to approximate allocated disk usage; otherwise `st_size` is used.

Dataset directories with the same normalized `owner/repository` name are aggregated. Everything outside the recognized model and dataset directories is totaled as **Other Cache**.

## Interaction rules

- A single click selects an item and synchronizes list, map, and details.
- A double click opens the selected cache directory in Dolphin.
- Deletion is intentionally absent.
- Search filters both the list and map.
- Sorting affects the list; the treemap always lays blocks out by descending size for visual stability.
- Scanning runs off the UI thread and streams completed folders into the interface.
- Escape clears search first, then acts as scan cancellation when no search is active.

## Scope boundaries

The application does not parse model configs, inspect weights, calculate parameter counts, call Hugging Face services, or attempt cache cleanup. These features would expand complexity without improving the core disk-usage workflow.
