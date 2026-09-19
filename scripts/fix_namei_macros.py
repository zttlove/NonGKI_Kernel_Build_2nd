#!/usr/bin/env python3
"""
Re-inject SUS_PATH macros and struct nameidata.state after
susfs_patch_to_5.4.patch is applied to fs/namei.c

Usage:
    python3 scripts/fix_namei_macros.py <kernel_dir>
"""

import os
import sys


def fix_namei(kernel_dir):
    path = os.path.join(kernel_dir, "fs/namei.c")
    with open(path, "r") as f:
        content = f.read()

    changed = False

    # 1) 注入 ND_STATE 宏
    if "ND_STATE_LOOKUP_LAST" not in content:
        needle = "#ifdef CONFIG_KSU_SUSFS_SUS_PATH\nextern bool susfs_is_inode_sus_path"
        replacement = (
            "#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n"
            "#define ND_STATE_LOOKUP_LAST\t0x00000008\n"
            "#define ND_STATE_OPEN_LAST\t0x00000010\n"
            "#define ND_FLAGS_LOOKUP_LAST\t0x00000001\n"
            "extern bool susfs_is_inode_sus_path"
        )
        if needle in content:
            content = content.replace(needle, replacement, 1)
            print("[+] Injected ND_STATE macros.")
            changed = True
        else:
            print("[!] Extern declaration not found, cannot inject macros.")
    else:
        print("[+] ND_STATE macros already present.")

    # 2) 注入 state 字段
    if "unsigned int\tstate;" not in content:
        idx = content.find("struct nameidata {")
        if idx > 0:
            flags_pos = content.find("unsigned int\tflags;", idx)
            if flags_pos > 0:
                # 找到这一行末尾（\n）
                line_end = content.find("\n", flags_pos)
                insert_pos = line_end + 1
                content = (
                    content[:insert_pos]
                    + "#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n"
                    + "\tunsigned int\tstate;\n"
                    + "#endif\n"
                    + content[insert_pos:]
                )
                print("[+] Injected state field.")
                changed = True
            else:
                print("[!] flags field not found in struct nameidata.")
        else:
            print("[!] struct nameidata not found.")
    else:
        print("[+] state field already present.")

    if changed:
        with open(path, "w") as f:
            f.write(content)
        print("[+] fs/namei.c updated.")
    else:
        print("[+] No change needed.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fix_namei_macros.py <kernel_dir>", file=sys.stderr)
        sys.exit(2)
    fix_namei(sys.argv[1])
