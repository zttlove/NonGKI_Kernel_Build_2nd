import re
import sys

path = 'include/linux/susfs_def.h'

with open(path) as f:
    content = f.read()

print("=== 处理前 ===")
print("文件行数:", content.count('\n'))
print("第一个 #endif:", content.find('#endif'))
print("最后一个 #endif:", content.rfind('#endif'))

# 1. 删除 #endif 之后的所有残留内容
first_endif_pos = content.find('#endif')
if first_endif_pos != -1:
    guard_end = first_endif_pos + len('#endif')
    after = content[guard_end:]
    if 'susfs_is_current_app_uid' in after or 'STATX_SUS_KSTAT' in after:
        content = content[:guard_end] + '\n'
        print("✅ 已删除 #endif 之后的残留追加内容")

# 2. 删除所有已存在的 susfs_is_current_app_uid 定义
pattern = re.compile(
    r'\nstatic inline bool susfs_is_current_app_uid\(void\) \{[^}]*\}\n',
    re.DOTALL
)
matches = list(pattern.finditer(content))
print(f"发现 {len(matches)} 处 susfs_is_current_app_uid 定义")
if matches:
    for m in reversed(matches):
        content = content[:m.start()] + '\n' + content[m.end():]

# 3. 去重 STATX_SUS_KSTAT
pattern_statx = re.compile(
    r'#ifndef STATX_SUS_KSTAT\n#define STATX_SUS_KSTAT 0x10000000U\n#endif\n',
    re.DOTALL
)
matches_statx = list(pattern_statx.finditer(content))
print(f"发现 {len(matches_statx)} 处 STATX_SUS_KSTAT 定义块")
if len(matches_statx) > 1:
    for m in reversed(matches_statx[1:]):
        content = content[:m.start()] + content[m.end():]
    print("✅ 已去重 STATX_SUS_KSTAT")

# 4. 去重 STATX_SUS_KSTAT_FUSE
pattern_fuse = re.compile(
    r'#ifndef STATX_SUS_KSTAT_FUSE\n#define STATX_SUS_KSTAT_FUSE 0x20000000U\n#endif\n',
    re.DOTALL
)
matches_fuse = list(pattern_fuse.finditer(content))
print(f"发现 {len(matches_fuse)} 处 STATX_SUS_KSTAT_FUSE 定义块")
if len(matches_fuse) > 1:
    for m in reversed(matches_fuse[1:]):
        content = content[:m.start()] + content[m.end():]
    print("✅ 已去重 STATX_SUS_KSTAT_FUSE")

# 5. 准备要插入的 v2.3 内容
additions = []
if 'STATX_SUS_KSTAT 0x10000000U' not in content:
    additions.append(
        "#ifndef STATX_SUS_KSTAT\n"
        "#define STATX_SUS_KSTAT 0x10000000U\n"
        "#endif"
    )
if 'STATX_SUS_KSTAT_FUSE 0x20000000U' not in content:
    additions.append(
        "#ifndef STATX_SUS_KSTAT_FUSE\n"
        "#define STATX_SUS_KSTAT_FUSE 0x20000000U\n"
        "#endif"
    )
if 'susfs_is_current_app_uid(void)' not in content:
    additions.append(
        "static inline bool susfs_is_current_app_uid(void) {\n"
        "    return ((current_uid().val % 100000) >= 10000);\n"
        "}"
    )

# 6. 在最后一个 #endif 之前插入
if additions:
    last_endif = content.rfind('#endif')
    if last_endif == -1:
        raise SystemExit("❌ 找不到 #endif")
    insert_text = '\n' + '\n\n'.join(additions) + '\n\n'
    content = content[:last_endif] + insert_text + content[last_endif:]
    print("✅ 已在最后一个 #endif 之前插入 v2.3 内容")

with open(path, 'w') as f:
    f.write(content)

print("=== 处理后 ===")
print("文件行数:", content.count('\n'))
print("susfs_is_current_app_uid 数量:", content.count('susfs_is_current_app_uid'))
print("STATX_SUS_KSTAT 数量:", content.count('STATX_SUS_KSTAT 0x10000000U'))
print("STATX_SUS_KSTAT_FUSE 数量:", content.count('STATX_SUS_KSTAT_FUSE 0x20000000U'))
