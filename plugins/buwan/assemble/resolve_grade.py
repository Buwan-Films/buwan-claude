"""DaVinci Resolve: apply the Buwan look to every camera clip in the current timeline.

Run INSIDE Resolve (works in the free version too): copy this file to Resolve's Scripts folder
  macOS:   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Edit/
  Windows: %APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Edit\\
then Workspace > Scripts > resolve_grade. Set LUT_PATH and SKIP_ROLES first (or pass via env BUWAN_LUT).
Studio users can also run it externally with DaVinciResolveScript.
"""
import os

LUT_PATH = os.environ.get("BUWAN_LUT", os.path.expanduser("~/Buwan/kit/luts/Buwan_Warm.cube"))
NODE_INDEX = 2          # node 1 stays for camera Log->709 / balance; the look goes on node 2
SKIP_NAME_CONTAINS = ("music", "Music", ".wav", ".mp3", ".mov_kit", "07.", "06.", "01.", "02.", "03.", "04.", "05.", "08.")  # kit graphics / music


def main():
    try:
        resolve = bmd.scriptapp("Resolve")  # noqa: F821  (provided inside Resolve)
    except NameError:
        import DaVinciResolveScript as dvr
        resolve = dvr.scriptapp("Resolve")
    pm = resolve.GetProjectManager()
    proj = pm.GetCurrentProject()
    tl = proj.GetCurrentTimeline()
    if not tl:
        print("Open a timeline first.")
        return
    done = skipped = 0
    for track in range(1, tl.GetTrackCount("video") + 1):
        for item in tl.GetItemListInTrack("video", track) or []:
            name = item.GetName() or ""
            if any(s in name for s in SKIP_NAME_CONTAINS):
                skipped += 1
                continue
            # make sure there are at least NODE_INDEX nodes; SetLUT creates on the given node
            ok = item.SetLUT(NODE_INDEX, LUT_PATH)
            if not ok:
                ok = item.SetLUT(1, LUT_PATH)
            done += int(bool(ok))
    print(f"Buwan grade: LUT applied to {done} clips, skipped {skipped} (music/graphics). LUT: {LUT_PATH}")


main()
