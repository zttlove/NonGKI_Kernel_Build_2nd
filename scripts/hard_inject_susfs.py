#!/usr/bin/env python3
"""
Hard-inject SUSFS declarations at the top of fs/namei.c
and force-declare locals in __lookup_hash()

Usage:
    python3 scripts/hard_inject_susfs.py <kernel_dir>
"""

import os
import re
import sys


def hard_inject(path):
    with open(path, "r") as f:
        content = f.read()

    if "SUSFS HARD-INJECT" in content:
        print("[+] Header already injected, skip.")
        return

    header = (
        "/* SUSFS HARD-INJECT - start */\n"
        "#include <linux/susfs_def.h>\n"
        "#include <uapi/linux/magic.h>\n"
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


def force_lookup_hash_locals(path):
    with open(path, "r") as f:
        lines = f.readlines()

    in_func = False
    out = []
    injected_decl = False
    injected_label = False

    for line in lines:
        if "static struct dentry *__lookup_hash(" in line:
            in_func = True

        if in_func:
            if ("struct inode *dir = base->d_inode;" in line
                    and not injected_decl):
                out.append(line)
                out.append("\tbool found_sus_path = false;\n")
                injected_decl = True
                continue

            if ("dentry = d_alloc(base, name);" in line
                    and not injected_label):
                out.append(line)
                out.append("retry:\n")
                injected_label = True
                continue

        out.append(line)

        if in_func and line.startswith("}"):
            in_func = False

    with open(path, "w") as f:
        f.writelines(out)

    print("[+] found_sus_path decl injected:", injected_decl)
    print("[+] retry: label injected:", injected_label)


def main():
    kernel_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    namei = os.path.join(kernel_dir, "fs/namei.c")
    hard_inject(namei)
    force_lookup_hash_locals(namei)


if __name__ == "__main__":
    main()
