# -*- coding: utf-8 -*-
"""Fix indentation in main_window.py - for loop body needs 20 spaces"""

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []

for i, line in enumerate(lines):
    # Lines 1711-1715 (0-indexed: 1710-1714) are for loop body, need 20 spaces
    if 1710 <= i <= 1714:
        stripped = line.strip()
        if stripped:
            fixed_lines.append('                    ' + stripped + '\n')
        else:
            fixed_lines.append(line)
    # Line 1718 (0-indexed: 1717) is inside if hasattr, needs 20 spaces
    elif i == 1717:
        stripped = line.strip()
        if stripped:
            fixed_lines.append('                    ' + stripped + '\n')
        else:
            fixed_lines.append(line)
    # Line 1722 (0-indexed: 1721) is inside if hasattr, needs 20 spaces
    elif i == 1721:
        stripped = line.strip()
        if stripped:
            fixed_lines.append('                    ' + stripped + '\n')
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed indentation v4!")
