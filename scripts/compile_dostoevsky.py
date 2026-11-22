# -*- coding: utf-8 -*-
import sys
import io
import os
import subprocess
import shutil

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def compile_typst(src_path="dostoevsky_canvas.typ", out_path="dostoevsky_canvas.pdf"):
    if not shutil.which("typst"):
        print("❌ 'typst' CLI not found on system path.")
        return False
    
    if not os.path.exists(src_path):
        print(f"❌ Source file not found: {src_path}")
        return False

    cmd = ["typst", "compile", src_path, out_path]
    print(f"🚀 Compiling {src_path} -> {out_path}...")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
        print(f"✅ Compilation successful: {out_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Compilation failed with code {e.returncode}:")
        print(e.stderr)
        return False

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "dostoevsky_canvas.typ"
    out = sys.argv[2] if len(sys.argv) > 2 else "dostoevsky_canvas.pdf"
    success = compile_typst(src, out)
    if not success:
        sys.exit(1)
