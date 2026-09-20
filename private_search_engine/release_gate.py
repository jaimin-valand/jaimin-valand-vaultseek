from __future__ import annotations
import subprocess, sys

def main() -> int:
    commands=[ [sys.executable,'-m','pytest','-q'], [sys.executable,'-m','compileall','-q','private_search_engine'] ]
    for cmd in commands:
        result=subprocess.run(cmd)
        if result.returncode: print('RELEASE_GATE_FAIL:', ' '.join(cmd)); return result.returncode
    print('RELEASE_GATE_PASS: Private Search Engine 3.0.0')
    return 0
if __name__=='__main__': raise SystemExit(main())
