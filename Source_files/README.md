# CPO file generator - source

Desktop app: load an SEM image of an emitter tip, extract its profile, optionally add a flare and shank,
and export a CPO2D `.DAT` input file (tip electrode plus a flat annular extractor).

## Running / building
- Run from source (Python 3.10+; needs `numpy`, `scipy`, `matplotlib`, `pillow`; Tkinter ships with Python):
  `py run_cpogen.py`
- Build the single-file exe: `build_exe.bat` (needs `pyinstaller`). Output goes to `dist\CPO-File-Generator.exe`
  and copies `SEM-Images\*.jpg` into `dist\SEM-Images\test images`. Unneeded modules are excluded to keep the exe small.
  Keep the `SEM-Images` folder next to the exe.

## Top-level files
| File | Purpose |
|---|---|
| `run_cpogen.py` | Entry point for both source runs and the packaged exe. |
| `projectpaths.py` | `project_root()`: folder holding `SEM-Images/`; the exe's folder when packaged. |
| `build_exe.bat` | PyInstaller one-file build with module exclusions. |

## `tipmodel/` - SEM image to tip profile
| File | Purpose |
|---|---|
| `imageio.py` | Locate and load images (greyscale, scaled 0-1). |
| `scalebar.py` | Find the scale bar, give metres per pixel, mask the valid image area, parse lengths like `1um`. |
| `segmentation.py` | Otsu-threshold segmentation of the tip from the background. |
| `profile.py` | Orient the tip apex-up and extract radius r(z) from the mask (apex at z=0). |
| `revolve.py` | Revolve the profile about the z axis into a 3D surface mesh. |
| `pipeline.py` | `build_tip_model`: runs the steps above from image file to model. |
| `types.py` | Plain data containers (`TipProfile`, `Mesh`, ...). |
| `visualize.py` | Matplotlib plots of segmentation, profile and surface. |
| `__main__.py` | Command line: `py -m tipmodel IMAGE --bar-length 1e-6 [--apex up]`. |

## `cpogen/` - tip profile to CPO2D file
| File | Purpose |
|---|---|
| `geometry.py` | `add_shank` (convex flare + cylinder); outline simplification (Ramer-Douglas-Peucker) that keeps at least *min tip points* on the measured tip; builds tip and extractor electrodes in a chosen unit. |
| `writer.py` | Writes the CPO2D `.DAT` text file (CRLF line endings). |
| `ui.py` | Tkinter GUI: image/voltage/gap fields, min tip points, shank settings, previews, export. |
| `__main__.py` | `py -m cpogen` launches the GUI. |

## GUI fields
Image and scale bar length; tip and extractor voltages; tip-extractor gap; extractor aperture and outer radius;
**Min. tip profile points** (default 150, applies to the measured tip only, so the shank cannot reduce tip detail);
apex direction; shank radius, flare length and shank length (leave radius blank for no shank).
Lengths accept units (`um`, `mm`, `nm`).
