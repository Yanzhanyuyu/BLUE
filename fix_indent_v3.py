# -*- coding: utf-8 -*-
"""Fix indentation in main_window.py"""

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []

# Track indentation state
in_try_block = False
try_start_line = 1646  # 0-indexed, line 1647

for i, line in enumerate(lines):
    if i < try_start_line:
        fixed_lines.append(line)
        continue
    
    # We're in or after the try block
    stripped = line.strip()
    
    # Check if we've reached except
    if stripped.startswith('except Exception as e:'):
        in_try_block = False
        fixed_lines.append(line)
        continue
    
    if stripped.startswith('else:') and i > 1720:  # The else paired with if self._is_running
        in_try_block = False
        fixed_lines.append(line)
        continue
    
    # If we're still in try block content (before except)
    if i < 1723:  # Before the blank line before except
        if not stripped:  # Blank line
            fixed_lines.append(line)
        elif stripped.startswith('#'):
            # Comments should be at 16 spaces
            fixed_lines.append('                ' + stripped + '\n')
        elif stripped.startswith('if ') or stripped.startswith('for '):
            # Control statements at 16 spaces
            fixed_lines.append('                ' + stripped + '\n')
        elif stripped in ['track_id, x, y, w, h, conf = det']:
            # For loop body at 20 spaces
            fixed_lines.append('                    ' + stripped + '\n')
        elif i >= 1710 and i <= 1714:
            # For loop body (lines 1711-1715, 0-indexed 1710-1714)
            fixed_lines.append('                    ' + stripped + '\n')
        else:
            # Regular statements at 16 spaces
            fixed_lines.append('                ' + stripped + '\n')
    else:
        fixed_lines.append(line)

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed indentation v3!")
