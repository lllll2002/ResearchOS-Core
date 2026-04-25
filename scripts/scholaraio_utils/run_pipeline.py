"""包装 scholaraio pipeline ingest，输出写到文件避免 GBK 编码错误。"""
import subprocess, sys, os

out_path = r'E:\scholaraio\scholaraio-main\scholaraio-main\data\pipeline_output.txt'

env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'

result = subprocess.run(
    [sys.executable, '-m', 'scholaraio.cli', 'pipeline', 'ingest'],
    capture_output=True,
    encoding='utf-8',
    errors='replace',
    env=env,
    cwd=r'E:\scholaraio\scholaraio-main\scholaraio-main',
)

output = result.stdout + result.stderr
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"exit={result.returncode}, output -> {out_path}")
