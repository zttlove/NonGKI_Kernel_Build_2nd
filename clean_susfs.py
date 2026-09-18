#!/usr/bin/env python3
"""
清除内核源码中的 SUSFS 代码。
用法: python3 clean_susfs.py <文件1> <文件2> ...
"""
import sys
import re
import os

def remove_susfs_blocks(content):
    lines = content.split('\n')
    result = []
    stack = []

    for line in lines:
        stripped = line.strip()

        # 检测 SUSFS 相关的条件编译开头
        is_susfs_ifdef = (
            re.match(r'#\s*ifdef\s+CONFIG_KSU_SUSFS', stripped) or
            re.match(r'#\s*if\s+defined\(CONFIG_KSU_SUSFS', stripped) or
            re.match(r'#\s*if\s+.*CONFIG_KSU_SUSFS', stripped)
        )

        if is_susfs_ifdef:
            stack.append('susfs')
            continue

        if re.match(r'#\s*ifdef\s+', stripped) or re.match(r'#\s*if\s+', stripped):
            stack.append('other')
            result.append(line)
            continue

        if re.match(r'#\s*else', stripped):
            if stack and stack[-1] == 'susfs':
                continue
            result.append(line)
            continue

        if re.match(r'#\s*endif', stripped):
            if stack:
                top = stack.pop()
                if top == 'susfs':
                    continue
                result.append(line)
                continue
            result.append(line)
            continue

        # 普通代码行
        if stack and stack[-1] == 'susfs':
            continue
        result.append(line)

    return '\n'.join(result)


def clean_file(path):
    if not os.path.exists(path):
        print(f"[-] 文件不存在，跳过: {path}")
        return False
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    cleaned = remove_susfs_blocks(content)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    print(f"[+] 已清理: {path}")
    return True


def main():
    if len(sys.argv) < 2:
        print("用法: python3 clean_susfs.py <文件1> <文件2> ...")
        sys.exit(1)
    for path in sys.argv[1:]:
        clean_file(path)


if __name__ == '__main__':
    main()
