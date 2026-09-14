#!/bin/bash
# fix-task_mmu.sh
# 手动合并 fs/proc/task_mmu.c 中失败的 SUSFS hunk #7
# 用法: bash fix-task_mmu.sh [kernel_root]
# 例:   bash fix-task_mmu.sh $GITHUB_WORKSPACE/device_kernel

set -e

KERNEL_ROOT="${1:-$GITHUB_WORKSPACE/device_kernel}"
TARGET="$KERNEL_ROOT/fs/proc/task_mmu.c"

if [ ! -f "$TARGET" ]; then
    echo "[-] 找不到文件: $TARGET"
    exit 1
fi

echo "[*] 目标文件: $TARGET"

# 如果已经打过补丁（有 SUSFS_IS_INODE_OPEN_REDIRECT），直接跳过
if grep -q "SUSFS_IS_INODE_OPEN_REDIRECT" "$TARGET"; then
    echo "[=] 已经打过补丁，跳过"
    rm -f "$TARGET.rej"
    exit 0
fi

echo "[*] 开始插入 SUSFS 钩子 ..."

python3 - "$TARGET" <<'PYEOF'
import sys
import re

path = sys.argv[1]
with open(path, 'r', encoding='utf-8', errors='surrogateescape') as f:
    src = f.read()

# ------------------------------------------------------------------
# 1. 先确认 SUSFS 头文件已包含
# ------------------------------------------------------------------
if '#include <linux/susfs.h>' not in src:
    # 在最后一个 #include 之后插入
    includes = list(re.finditer(r'^#include\s+[<"].+[>"]\s*$', src, re.MULTILINE))
    if includes:
        pos = includes[-1].end()
        src = src[:pos] + '\n#include <linux/susfs.h>' + src[pos:]
        print("[+] 已插入 #include <linux/susfs.h>")
    else:
        print("[!] 未找到 include 区，跳过 include 插入")

# ------------------------------------------------------------------
# 2. 用正则匹配 show_map_vma 里的 "if (file) { ... }" 块
#    允许 Tab/空格混合缩进，允许中间有别的语句
# ------------------------------------------------------------------
# 匹配 "if (file) {" 到 "} else {" 之间的内容
pattern = re.compile(
    r'(?P<indent>[ \t]*)if \(file\) \{\n'
    r'(?P<body>.*?)'
    r'(?P=indent)\} else \{',
    re.DOTALL
)

m = pattern.search(src)
if not m:
    print("[-] 未找到 'if (file) { ... } else {' 结构，请手动合并")
    sys.exit(1)

body = m.group('body')

# 确认里面确实有 inode/file_inode 用法（避免匹配错位置）
if 'file_inode(vma->vm_file)' not in body and 'file->f_path' not in body:
    print("[-] 匹配到的块内容不符合预期，请手动检查")
    sys.exit(1)

# ------------------------------------------------------------------
# 3. 构造新的 body（用 Tab 缩进，符合内核代码风格）
# ------------------------------------------------------------------
TAB = '\t'
inner = TAB * 2  # if(file) { 内部缩进

open_redirect_block = f"""{inner}#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
{inner}\tif (SUSFS_IS_INODE_OPEN_REDIRECT(inode)) {{
{inner}\t\tchar *spoofed_redirected_name = NULL;
{inner}\t\tint srcu_idx = srcu_read_lock(&susfs_srcu_open_redirect);
{inner}\t\tint ret = susfs_open_redirect_spoof_show_map_vma_srcu(inode, &ino, &dev, &spoofed_redirected_name);
{inner}\t\tif (!ret) {{
{inner}\t\t\tpgoff = ((loff_t)vma->vm_pgoff) << PAGE_SHIFT;
{inner}\t\t\tstart = vma->vm_start;
{inner}\t\t\tend = vma->vm_end;
{inner}\t\t\tshow_vma_header_prefix(m, start, end, flags, pgoff, dev, ino);
{inner}\t\t\tseq_pad(m, ' ');
{inner}\t\t\tif (spoofed_redirected_name)
{inner}\t\t\t\tseq_puts(m, spoofed_redirected_name);
{inner}\t\t\tseq_putc(m, '\\n');
{inner}\t\t\tsrcu_read_unlock(&susfs_srcu_open_redirect, srcu_idx);
{inner}\t\t\treturn;
{inner}\t\t}}
{inner}\t\tsrcu_read_unlock(&susfs_srcu_open_redirect, srcu_idx);
{inner}\t}}
{inner}#endif // CONFIG_KSU_SUSFS_OPEN_REDIRECT
{inner}#ifdef CONFIG_KSU_SUSFS_SUS_MAP
{inner}\tif (SUSFS_IS_INODE_SUS_MAP(inode))
{inner}\t\treturn;
{inner}#endif // CONFIG_KSU_SUSFS_SUS_MAP
"""

# 在 "dev = inode->i_sb->s_dev;" 之前插入上面两块
anchor_dev = re.search(
    r'(?P<indent>[ \t]*)dev = inode->i_sb->s_dev;',
    body
)

if not anchor_dev:
    print("[-] 未找到 'dev = inode->i_sb->s_dev;'，请手动合并")
    sys.exit(1)

indent_dev = anchor_dev.group('indent')
insert_pos = anchor_dev.start()

# 先补 open_redirect + sus_map
new_body = body[:insert_pos] + open_redirect_block + body[insert_pos:]

# ------------------------------------------------------------------
# 4. 在 pgoff 赋值之后插入 SUS_KSTAT
# ------------------------------------------------------------------
new_body = re.sub(
    r'(?P<indent>[ \t]*)pgoff = \(\(loff_t\)vma->vm_pgoff\) << PAGE_SHIFT;\n',
    lambda mm: (
        mm.group(0)
        + f"{mm.group('indent')}#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n"
        + f"{mm.group('indent')}\tsusfs_sus_kstat_spoof_show_map_vma(inode, &dev, &ino);\n"
        + f"{mm.group('indent')}#endif // CONFIG_KSU_SUSFS_SUS_KSTAT\n"
    ),
    new_body,
    count=1
)

# ------------------------------------------------------------------
# 5. 写回
# ------------------------------------------------------------------
src = src[:m.start('body')] + new_body + src[m.end('body'):]

with open(path, 'w', encoding='utf-8', errors='surrogateescape') as f:
    f.write(src)

print("[+] fs/proc/task_mmu.c 补丁插入完成")
PYEOF

# ------------------------------------------------------------------
# 6. 验证
# ------------------------------------------------------------------
echo "[*] 验证插入结果:"
grep -n "SUSFS_IS_INODE_OPEN_REDIRECT\|SUSFS_IS_INODE_SUS_MAP\|susfs_sus_kstat_spoof_show_map_vma" "$TARGET" || {
    echo "[-] 验证失败：未找到插入的代码"
    exit 1
}

# 删除 .rej
rm -f "$TARGET.rej"

echo "[+] 完成"
