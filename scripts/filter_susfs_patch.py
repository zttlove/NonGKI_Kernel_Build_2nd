#!/usr/bin/env python3
"""
Filter susfs_patch_to_5.4.patch to keep only the minimal feature set:
  Keep : SUS_PATH, SUS_KSTAT, ENABLE_LOG + core files
  Drop : SUS_MOUNT, SUS_MAP, OPEN_REDIRECT, SPOOF_UNAME, HIDE_KSU_SUSFS_SYMBOLS

Usage:
    python3 scripts/filter_susfs_patch.py <input.patch> <output.patch>
"""

import re
import sys


# 整文件丢弃
DROP_FILES = {
    "fs/namespace.c",
    "fs/statfs.c",
    "fs/proc/fd.c",
    "fs/proc_namespace.c",
    "fs/proc/task_mmu.c",
    "kernel/sys.c",
    "kernel/kallsyms.c",
    "fs/notify/fdinfo.c"
}

# 逐 hunk 过滤
HUNK_FILTER = {
    "fs/namei.c": [
        "CONFIG_KSU_SUSFS_OPEN_REDIRECT",
        "susfs_open_redirect_spoof",
        "SUSFS_IS_INODE_OPEN_REDIRECT",
    ],
}


def split_blocks(lines):
    """按 'diff --git' 切分成 block 列表"""
    blocks = []
    current = []
    for line in lines:
        if line.startswith("diff --git "):
            if current:
                blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def split_hunks(block):
    """把一个 file block 拆成 header + hunks"""
    header = []
    hunks = []
    cur = None
    for line in block:
        if line.startswith("@@ "):
            if cur is not None:
                hunks.append(cur)
            cur = [line]
        elif cur is None:
            header.append(line)
        else:
            cur.append(line)
    if cur is not None:
        hunks.append(cur)
    return header, hunks


def filter_patch(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    blocks = split_blocks(lines)

    out_blocks = []
    kept = set()
    dropped = set()
    filtered_hunks = 0

    for block in blocks:
        m = re.match(r"diff --git a/(\S+) b/(\S+)", block[0])
        if not m:
            continue
        fpath = m.group(1)

        # 整文件丢弃
        if fpath in DROP_FILES:
            dropped.add(fpath)
            continue

        # 逐 hunk 过滤
        if fpath in HUNK_FILTER:
            keywords = HUNK_FILTER[fpath]
            header, hunks = split_hunks(block)

            kept_hunks = []
            for h in hunks:
                txt = "".join(h)
                if any(kw in txt for kw in keywords):
                    filtered_hunks += 1
                    continue
                kept_hunks.append(h)

            if not kept_hunks:
                dropped.add(fpath + " (all hunks filtered)")
                continue

            out_blocks.append(header + [l for h in kept_hunks for l in h])
            kept.add(fpath)
        else:
            out_blocks.append(block)
            kept.add(fpath)

    with open(output_path, "w", encoding="utf-8") as f:
        for b in out_blocks:
            f.writelines(b)

    print("=== Filter results ===")
    print("Kept files:")
    for x in sorted(kept):
        print("  +", x)
    print("Dropped files:")
    for x in sorted(dropped):
        print("  -", x)
    print("Filtered hunks:", filtered_hunks)
    print("Output:", output_path)


def main():
    if len(sys.argv) != 3:
        print("Usage: filter_susfs_patch.py <input.patch> <output.patch>",
              file=sys.stderr)
        sys.exit(2)
    filter_patch(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
