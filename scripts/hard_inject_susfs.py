#!/usr/bin/env python3
"""
Hard-inject SUSFS declarations at the top of fs/namei.c

Usage:
    python3 scripts/hard_inject_susfs.py <kernel_dir>
"""

import os
import re
import sys


def hard_inject(kernel_dir):
    path = os.path.join(kernel_dir, "fs/namei.c")

    with open(path, "r") as f:
        content = f.read()

    if "SUSFS HARD-INJECT" in content:
        print("[+] Already injected, skip.")
        return

    header = (
        "/* SUSFS HARD-INJECT - start */\n"
        "#include <linux/susfs_def.h>\n"
        "#include <uapi/linux/magic.h>\n"
        "#define ND_STATE_LOOKUP_LAST\t0x00000008\n"
        "#define ND_STATE_OPEN_LAST\t0x00000010\n"
        "#define ND_FLAGS_LOOKUP_LAST\t0x00000001\n"
        "extern bool susfs_is_inode_sus_path(struct inode *inode);\n"
        "extern const struct qstr susfs_fake_qstr_name;\n"
        "/* SUSFS HARD-INJECT - end */\n\n"
    )

    m = re.search(r"^#include", content, re.MULTILINE)
    if m:
        content = content[:m.start()] + header + content[m.start():]
        with open(path, "w") as f:
            f.write(content)
        print("[+] Hard-injected at top of fs/namei.c")
    else:
        print("[!] No #include found, injection failed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: hard_inject_susfs.py <kernel_dir>", file=sys.stderr)
        sys.exit(2)
    hard_inject(sys.argv[1])
