import re

path = "fs/namespace.c"
with open(path) as f:
    lines = f.readlines()

out = []
i = 0
while i < len(lines):
    line = lines[i]
    if re.match(r'^\s*#\s*ifdef\s+CONFIG_KSU_SUSFS_SUS_MOUNT\s*$', line):
        # 找到匹配的 #else 或 #endif
        nest = 0
        else_idx = -1
        endif_idx = -1
        j = i + 1
        while j < len(lines):
            l = lines[j]
            if re.match(r'^\s*#\s*if(?:def|ndef)?\b', l):
                nest += 1
            elif re.match(r'^\s*#\s*endif\b', l):
                if nest == 0:
                    endif_idx = j
                    break
                nest -= 1
            elif re.match(r'^\s*#\s*else\b', l) and nest == 0:
                else_idx = j
            j += 1
        
        if else_idx >= 0:
            # 保留 #else 到 #endif 之间的内容
            out.extend(lines[else_idx + 1 : endif_idx])
        # 否则删除整块
        i = endif_idx + 1 if endif_idx >= 0 else i + 1
        continue
    
    out.append(line)
    i += 1

with open(path, "w") as f:
    f.writelines(out)
