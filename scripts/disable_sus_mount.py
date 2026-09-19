#!/usr/bin/env python3
import re
import sys
import os


def disable_sus_mount(path):
    with open(path, "r") as f:
        content = f.read()

    before = len(re.findall(r'CONFIG_KSU_SUSFS_SUS_MOUNT', content))
    print(f"[before] SUS_MOUNT refs = {before}")

    content = re.sub(r'^#ifdef\s+CONFIG_KSU_SUSFS_SUS_MOUNT\s*$',
                     '#if 0', content, flags=re.MULTILINE)
    content = re.sub(r'^#ifndef\s+CONFIG_KSU_SUSFS_SUS_MOUNT\s*$',
                     '#if 1', content, flags=re.MULTILINE)
    content = re.sub(r'^#if\s+defined\s*\(\s*CONFIG_KSU_SUSFS_SUS_MOUNT\s*\)\s*$',
                     '#if 0', content, flags=re.MULTILINE)
    content = re.sub(r'^#if\s+defined\s*\(\s*CONFIG_KSU_SUSFS_SUS_MOUNT\s*\)\s*\|\|.*$',
                     '#if 0', content, flags=re.MULTILINE)

    with open(path, "w") as f:
        f.write(content)

    after = len(re.findall(r'^#if 0\s*$', content, re.M))
    print(f"[after] #if 0 count = {after}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: disable_sus_mount.py <kernel_dir>", file=sys.stderr)
        sys.exit(2)
    disable_sus_mount(os.path.join(sys.argv[1], "fs/namespace.c"))
