import sys
print(f"sys.executable: {sys.executable}")
print(f"Type: {type(sys.executable)}")
print(f"Length: {len(sys.executable)}")
print(f"Last 10 characters: {sys.executable[-10:]}")

# 测试 join 操作
dev_command = [sys.executable, "main_async.py", "--debug"]
print(f"Joined command: {' '.join(dev_command)}")
