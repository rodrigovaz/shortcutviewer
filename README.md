# Shortcut Keyboard Viewer

A Blender 5.0 add-on that draws a keyboard overlay in the 3D View and helps inspect which shortcuts are assigned to each key and key combination.

## Features

- On-screen keyboard overlay in the 3D View
- Click a key to see all unique shortcut combinations assigned to it
- Click a shortcut combination to see the actions assigned to that exact combination
- Start and stop the overlay from the sidebar `N` panel

## How To Use

1. Open a 3D View.
2. Press `N` to open the right sidebar if it is hidden.
3. Open the `Shortcut Viewer` tab.
4. Click `Start Overlay`.

The overlay shows three layers of information:

1. Keyboard overlay
   Click any key on the keyboard drawing.
2. Shortcut Variants panel
   After clicking a key, the panel to the left of the keyboard lists every unique shortcut combination for that key.
   Example: `A`, `Shift + A`, `Ctrl + Shift + A`.
3. Actions panel
   Click one of the shortcut combinations in the variants panel.
   A third panel opens to the left and shows the Blender actions assigned to that exact shortcut combination.

## Color Behavior

- Unused key: grey
- Used key: grey-red
- More combinations on the same base key: brighter and less grey
- Selected key: highlighted so it is easy to track
- Recently pressed key: brighter active tint

## Notes

- The add-on reads active keyboard shortcuts from Blender keymaps.
- The overlay is drawn in the `3D View` and is controlled from the sidebar panel.
- If you change keymaps while Blender is open, click `Refresh Shortcuts`.

## Stop The Overlay

To stop the overlay:

1. Open the `Shortcut Viewer` tab in the 3D View sidebar.
2. Click `Stop Overlay`.

## Files

- `__init__.py`: Blender add-on source
- `README.md`: usage instructions
