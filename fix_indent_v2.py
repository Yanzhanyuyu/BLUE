# -*- coding: utf-8 -*-
"""Fix indentation in main_window.py - lines 1701-1722 should be 16 spaces, not 12"""

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []

for i, line in enumerate(lines):
    # Lines 1701-1722 (0-indexed: 1700-1721) need to be indented to 16 spaces
    # These are inside the try block which starts at line 1647 (0-indexed 1646) with 12 spaces
    # The content inside try should be at 16 spaces
    if 1700 <= i <= 1721:
        # Check if line has content and is not a blank line
        if line.strip():
            current_indent = len(line) - len(line.lstrip())
            if current_indent == 12:
                # Change from 12 to 16 spaces
                fixed_lines.append('    ' + line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed indentation!")
