"""图形界面：给零代码经验的老师用，双击程序即可打开。"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .pipeline import DEFAULT_OUTPUT_NAME, FriendlyError, run

WINDOW_TITLE = "二模质量分析结果生成工具"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(WINDOW_TITLE)
        root.resizable(False, False)

        padding = {"padx": 10, "pady": 6}

        frame = ttk.Frame(root)
        frame.grid(row=0, column=0, sticky="nsew", **padding)

        ttk.Label(frame, text="① 学生成绩表格：").grid(row=0, column=0, sticky="w")
        self.input_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.input_var, width=52).grid(row=1, column=0, sticky="we")
        ttk.Button(frame, text="浏览…", command=self.browse_input).grid(row=1, column=1, padx=(6, 0))

        ttk.Label(frame, text="② 分析结果另存为：").grid(row=2, column=0, sticky="w", pady=(12, 0))
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_NAME)
        ttk.Entry(frame, textvariable=self.output_var, width=52).grid(row=3, column=0, sticky="we")
        ttk.Button(frame, text="另存为…", command=self.browse_output).grid(row=3, column=1, padx=(6, 0))

        self.generate_btn = ttk.Button(frame, text="③ 生成分析报告", command=self.generate)
        self.generate_btn.grid(row=4, column=0, columnspan=2, pady=(16, 6), sticky="we")

        self.status_var = tk.StringVar(value="请选择学生成绩表格后点击生成")
        ttk.Label(frame, textvariable=self.status_var, foreground="#555").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

    def browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="选择学生成绩表格",
            filetypes=[("Excel 表格", "*.xlsx *.xls"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.input_var.set(path)
        folder = os.path.dirname(path)
        self.output_var.set(os.path.join(folder, DEFAULT_OUTPUT_NAME))

    def browse_output(self) -> None:
        initial_dir = os.path.dirname(self.input_var.get()) or os.getcwd()
        path = filedialog.asksaveasfilename(
            title="分析结果另存为",
            defaultextension=".xlsx",
            filetypes=[("Excel 表格", "*.xlsx")],
            initialdir=initial_dir,
            initialfile=os.path.basename(self.output_var.get()) or DEFAULT_OUTPUT_NAME,
        )
        if path:
            self.output_var.set(path)

    def generate(self) -> None:
        input_path = self.input_var.get().strip()
        output_path = self.output_var.get().strip() or DEFAULT_OUTPUT_NAME

        if not input_path:
            messagebox.showwarning(WINDOW_TITLE, "请先选择学生成绩表格。")
            return

        self.generate_btn.state(["disabled"])
        self.status_var.set("正在生成，请稍候…")

        def worker() -> None:
            try:
                out = run(input_path, output_path)
            except FriendlyError as exc:
                self.root.after(0, self._on_error, str(exc))
            except Exception as exc:  # noqa: BLE001 - 兜底，不让老师看到 Python 报错
                self.root.after(0, self._on_error, f"发生未知错误：{exc}")
            else:
                self.root.after(0, self._on_success, out)

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, output_path: str) -> None:
        self.generate_btn.state(["!disabled"])
        self.status_var.set("生成完成 ✓")
        messagebox.showinfo(WINDOW_TITLE, f"分析结果已生成：\n{output_path}")

    def _on_error(self, message: str) -> None:
        self.generate_btn.state(["!disabled"])
        self.status_var.set("生成失败")
        messagebox.showerror(WINDOW_TITLE, message)


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
