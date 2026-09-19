#!/usr/bin/env python3
"""
Strip SUS_MOUNT conditional blocks from fs/namespace.c

For each:
    #ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
    ...susfs code...
    #else
    ...original code...
    #endif

Keep only the original code (from #else to #endif).
If there is no #else, remove the entire block.

Handles nested #if / #ifdef / #ifndef / #endif correctly.

Usage:
    python3 scripts/disable_sus_mount.py <kernel_dir>
"""

import re
import sys
import os


SUS_HEAD_IFDEF = re.compile(r'^\s*#\s*ifdef\s+CONFIG_KSU_SUSFS_SUS_MOUNT\s*$')
SUS_HEAD_IFDEFINED = re.compile(
    r'^\s*#\s*if\s+defined\s*\(\s*CONFIG_KSU_SUSFS_SUS_MOUNT\s*\)\s*$'
)
ANY_IF = re.compile(r'^\s*#\s*if(?:def|ndef)?\b')
ELSE = re.compile(r'^\s*#\s*else\b')
ENDIF = re.compile(r'^\s*#\s*endif\b')


def strip_sus_mount(path):
    with open(path, 'r') as f:
        lines = f.readlines()

    out = []
    in_sus = False       # 是否在 SUS_MOUNT 块内
    nest = 0             # 块内嵌套深度
    past_else = False    # 是否已过 #else
    removed_count = 0

    for line in lines:
        if not in_sus:
            if SUS_HEAD_IFDEF.match(line) or SUS_HEAD_IFDEFINED.match(line):
                in_sus = True
                nest = 0
                past_else = False
                removed_count += 1
                continue
            out.append(line)
            continue

        # in_sus == True
        if ANY_IF.match(line):
            nest += 1
            if past_else:
                out.append(line)
            continue

        if ENDIF.match(line):
            if nest == 0:
                # SUS_MOUNT 块结束
                in_sus = False
                continue
            nest -= 1
            if past_else:
                out.append(line)
            continue

        if ELSE.match(line) and nest == 0:
            past_else = True
            continue

        # 普通行
        if past_else:
            out.append(line)
        # 未过 #else 的行全部丢弃

    with open(path, 'w') as f:
        f.writelines(out)

    print(f"[+] Stripped {removed_count} SUS_MOUNT block(s) from {path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: disable_sus_mount.py <kernel_dir>", file=sys.stderr)
        sys.exit(2)
    strip_sus_mount(os.path.join(sys.argv[1], "fs/namespace.c"))
