import re

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the except block indentation - it should be indented to match try block
# The try is at indent 12, except should also be at indent 12

# Find and fix the pattern
lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    # Fix line 1724 (index 1723): except should be 12 spaces, not 8
    if i == 1723 and 'except Exception as e:' in line:
        new_lines.append('            except Exception as e:')
    # Fix line 1725-1728: should be 16 spaces
    elif i == 1724 and "if hasattr(self, '_log_panel'):" in line:
        new_lines.append('                if hasattr(self, \'_log_panel\'):')
    elif i == 1725 and 'self._log_panel.log_error' in line:
        new_lines.append('                    self._log_panel.log_error(f"检测错误: {str(e)}")')
    elif i == 1726 and '出错时显示原始帧' in line:
        new_lines.append('                # 出错时显示原始帧')
    elif i == 1727 and 'self._video_canvas.set_frame(frame)' in line and i < 1729:
        new_lines.append('                self._video_canvas.set_frame(frame)')
    else:
        new_lines.append(line)

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Fixed!")
