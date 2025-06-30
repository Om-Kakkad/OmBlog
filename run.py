#!/usr/bin/env python3
"""
sync_and_push.py
────────────────
One-click helper for OmBlog.

• Sync Obsidian notes → Hugo content
• Run images.py to copy/rename embedded images
• Build once with Hugo     (fail fast if front-matter is broken)
• Commit & push with an auto-numbered message

Author: Om Kakkad – 2025-06-30
"""

import subprocess
import time
from pathlib import Path

# ──── CONFIG ────
OBS_POSTS   = Path("/Users/omkakkad/Obsidian/Om/posts")
BLOG_ROOT   = Path("/Users/omkakkad/Obsidian/OmBlog")
DEST_POSTS  = BLOG_ROOT / "content" / "posts"
IMAGES_PY   = BLOG_ROOT / "images.py"          # your image-processor script
COUNTER_FN  = BLOG_ROOT / ".commit_counter"    # stores last commit number
PAUSE       = 1.0  # seconds to breathe between steps (RSYNC → IMAGES → BUILD)

# ──── HELPERS ────
def run(cmd, cwd=None):
    """Run shell command, raise if it fails, and stream output live."""
    print(f"\n\033[96m$ {' '.join(map(str, cmd))}\033[0m")
    subprocess.run(cmd, cwd=cwd, check=True)

def next_commit_msg() -> str:
    """Read/increment counter file so each push has a new number."""
    last = 0
    if COUNTER_FN.exists():
        last = int(COUNTER_FN.read_text().strip() or 0)
    new  = last + 1
    COUNTER_FN.write_text(str(new))
    return f"Post update {new}"

# ──── MAIN WORK ────
def main():
    if not OBS_POSTS.is_dir():
        raise SystemExit(f"Obsidian posts path not found: {OBS_POSTS}")
    if not BLOG_ROOT.is_dir():
        raise SystemExit(f"Hugo project path not found: {BLOG_ROOT}")

    # 1) rsync posts
    run([
        "rsync", "-av", "--delete",
        str(OBS_POSTS) + "/",          # trailing slash → copy *contents*
        str(DEST_POSTS)                # no slash → put into folder
    ])
    time.sleep(PAUSE)

    # 2) image-processing helper (skip if it doesn’t exist)
    if IMAGES_PY.exists():
        run(["python3", str(IMAGES_PY)], cwd=BLOG_ROOT)
        time.sleep(PAUSE)

    # 3) local build (fast) – catches bad front-matter before we push
    run(["hugo", "--gc", "--minify", "-b", "http://localhost"], cwd=BLOG_ROOT)
    time.sleep(PAUSE)

    # 4) git commit & push
    run(["git", "add", "."], cwd=BLOG_ROOT)
    commit_msg = next_commit_msg()
    run(["git", "commit", "-m", commit_msg], cwd=BLOG_ROOT)

    # Figure out current branch (master-vs-main) and push
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=BLOG_ROOT
    ).decode().strip()
    run(["git", "push", "origin", branch], cwd=BLOG_ROOT)

    print(f"\n✅  Done!  ({commit_msg} → pushed to {branch})")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"\n❌  Command failed with exit-code {e.returncode}")

