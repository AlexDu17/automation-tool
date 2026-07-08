"""程序入口。

- 双击运行（不带参数）：打开图形界面。
- 带 --input/--output 参数运行：走命令行模式，方便批处理。
"""
import os
import sys

_SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


def main() -> int:
    if len(sys.argv) > 1:
        from grade_report.cli import main as cli_main

        return cli_main()
    from grade_report.gui import main as gui_main

    gui_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
