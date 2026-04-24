with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []

for i, line in enumerate(lines):
    # Fix except at line 1724 (0-indexed 1723)
    if i == 1723 and 'except Exception as e:' in line:
        fixed_lines.append('            except Exception as e:\n')
    # Fix lines 1725-1728 (except body) should be 16 spaces
    elif i == 1724 and "if hasattr(self, '_log_panel'):" in line:
        fixed_lines.append("                if hasattr(self, '_log_panel'):\n")
    elif i == 1725 and 'self._log_panel.log_error' in line:
        fixed_lines.append('                    self._log_panel.log_error(f"检测错误: {str(e)}")\n')
    elif i == 1726 and '出错时显示原始帧' in line:
        fixed_lines.append('                # 出错时显示原始帧\n')
    elif i == 1727 and 'self._video_canvas.set_frame(frame)' in line and i < 1729:
        fixed_lines.append('                self._video_canvas.set_frame(frame)\n')
    # Fix else at line 1729 should be 8 spaces
    elif i == 1728 and line.strip() == 'else:':
        fixed_lines.append('        else:\n')
    # Fix lines 1730-1733 (else body) should be 12 spaces
    elif i == 1729 and '仅显示预览' in line:
        fixed_lines.append('            # 仅显示预览\n')
    elif i == 1730 and 'self._video_canvas.set_frame(frame)' in line:
        fixed_lines.append('            self._video_canvas.set_frame(frame)\n')
    elif i == 1731 and 'self._fps_status.setText' in line:
        fixed_lines.append('            self._fps_status.setText("FPS: --")\n')
    elif i == 1732 and 'self._count_status.setText' in line:
        fixed_lines.append('            self._count_status.setText("预览模式")\n')
    else:
        fixed_lines.append(line)

with open('C:\\Users\\YanYu\\Desktop\\BLUE\\person_tracking\\src\\gui\\main_window.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed!")
