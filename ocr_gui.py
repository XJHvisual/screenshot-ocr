#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图 OCR 转 Obsidian 笔记 - GUI 版本（美化版）
功能：粘贴截图 → OCR 识别 → 预览笔记 → 确认存入
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import json
import threading
from datetime import datetime

# 笔记库路径
VAULT_PATH = r"D:\12081\Documents\PCO"

# ==================== 主题配色 ====================
COLORS = {
    "bg":           "#f0f2f5",       # 主背景（浅灰）
    "card_bg":      "#ffffff",        # 卡片/区域背景（纯白）
    "title":        "#1a1a2e",        # 主标题色（深墨）
    "subtitle":     "#6b7280",        # 副标题/提示文字（灰）
    "accent":       "#6366f1",        # 强调色（靛蓝紫）
    "accent_hover": "#4f46e5",        # 强调色悬停
    "success":      "#10b981",        # 成功/保存（翠绿）
    "success_hover":"#059669",
    "danger":       "#ef4444",        # 危险/丢弃（红）
    "danger_hover": "#dc2626",
    "warning":      "#f59e0b",        # 警告/刷新（琥珀）
    "warning_hover":"#d97706",
    "info":         "#3b82f6",        # 信息/加载（蓝）
    "info_hover":   "#2563eb",
    "muted":        "#9ca3af",        # 禁用态灰
    "border":       "#e5e7eb",        # 边框色
    "text":         "#374151",        # 正文文字
    "text_light":   "#6b7280",        # 次要文字
}

FONT_FAMILY = "Microsoft YaHei UI"  # 主字体（Win11 自带，比 YaHei 新）

# OCR 工具
try:
    from rapidocr_onnxruntime import RapidOCR
    OCR_ENGINE = RapidOCR()
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# 总结配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUMMARIZE_CONFIG_PATH = os.path.join(SCRIPT_DIR, "summarize_config.json")

def load_summarize_config():
    """加载总结配置，API Key 优先从环境变量 DEEPSEEK_API_KEY 读取"""
    defaults = {
        "enabled": True, "threshold": 500,
        "api_type": "deepseek",
        "api_base": "https://api.deepseek.com/v1", "model": "deepseek-chat",
        "prompt": "请用中文总结以下OCR识别的文字内容，提炼出关键信息，要求简洁清晰，不超过200字：\n\n{text}"
    }
    cfg = defaults.copy()
    try:
        with open(SUMMARIZE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            file_cfg = json.load(f)
            cfg.update(file_cfg)
    except Exception:
        pass
    # 环境变量优先
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        cfg["api_key"] = env_key
    return cfg

def get_api_key_status():
    """检查 API Key 配置状态，返回 (是否已配置, 状态提示文字)"""
    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key:
        return True, "✅ 已配置（环境变量）"
    try:
        with open(SUMMARIZE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            if cfg.get("api_key", "").strip() and cfg.get("api_key") != "YOUR_API_KEY_HERE":
                return True, "⚠️ 已配置（配置文件，建议改用环境变量）"
    except Exception:
        pass
    return False, "❌ 未配置 - 请设置环境变量 DEEPSEEK_API_KEY 或在 summarize_config.json 中配置"


class OcrGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("截图 OCR 转笔记")
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(820, 600)

        # OCR 结果
        self.ocr_text = ""
        self.summary_text = ""
        self.current_image = None
        self.vault_path = VAULT_PATH
        self.summarize_cfg = load_summarize_config()

        # 三种状态窗口配置 (宽x高)
        # 状态1: 初始态（无截图）— 紧凑
        # 状态2: 有截图未识别 — 展示预览+结果区（空）
        # 状态3: 已识别 — 展示预览+结果区（有内容）+ 底部操作栏
        self.state_sizes = {
            "idle":      "820x580",   # 无截图
            "preview":   "920x900",   # 有图未识别
            "recognized": "920x1350",  # 已识别（结果文字多要更高）
        }

        self.setup_ui()
        self.set_window_state("idle")  # 初始状态

        # 绑定 Ctrl+V 粘贴
        self.root.bind('<Control-v>', self.paste_image)
        self.root.bind('<Control-V>', self.paste_image)

    # ---- 通用组件工厂 ----

    def _make_card(self, parent, title_text, icon=""):
        """创建卡片式 LabelFrame"""
        frame = tk.LabelFrame(
            parent, text=f" {icon} {title_text} ",
            font=(FONT_FAMILY, 10, "bold"),
            bg=COLORS["card_bg"], fg=COLORS["title"],
            bd=1, padx=12, pady=10,
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        return frame

    def _make_btn(self, parent, text, cmd, color_key="accent",
                   font_size=10, bold=False, state=tk.NORMAL, width=None):
        """创建带悬停效果的按钮"""
        fg = COLORS.get(f"{color_key}_hover", COLORS[color_key])
        bg = COLORS[color_key]
        weight = "bold" if bold else "normal"
        btn = tk.Button(
            parent, text=text, command=cmd, state=state,
            font=(FONT_FAMILY, font_size, weight),
            bg=bg, fg="white", activebackground=fg, activeforeground="white",
            relief=tk.FLAT, cursor="hand2",
            padx=16 if width is None else width, pady=7,
            bd=0,
        )
        # 悬停变色
        btn.bind("<Enter>", lambda e, b=btn, f=fg, s=state: b.config(bg=f) if str(s) == str(tk.NORMAL) else None)
        btn.bind("<Leave>", lambda e, b=btn, c=bg, s=state: b.config(bg=c) if str(s) == str(tk.NORMAL) else None)
        return btn

    # ---- 布局 ----

    def setup_ui(self):
        # ===== 顶部标题区 =====
        header = tk.Frame(self.root, bg=COLORS["bg"], pady=8)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="📷 截图 OCR 转 Obsidian 笔记",
            font=(FONT_FAMILY, 18, "bold"),
            bg=COLORS["bg"], fg=COLORS["title"],
        ).pack()

        tk.Label(
            header,
            text="按 Ctrl+V 粘贴截图  ·  或点击下方按钮选择图片文件",
            font=(FONT_FAMILY, 10),
            bg=COLORS["bg"], fg=COLORS["subtitle"],
        ).pack(pady=(2, 0))

        # 分隔线
        sep = tk.Frame(self.root, height=1, bg=COLORS["border"])
        sep.pack(fill=tk.X, padx=30, pady=8)

        # ===== 截图预览卡片 =====
        preview_card = self._make_card(self.root, "截图预览", "📸")
        preview_card.pack(fill=tk.BOTH, expand=False, padx=25, pady=(0, 8))

        preview_container = tk.Frame(preview_card, bg="#fafafa")
        preview_container.pack(fill=tk.BOTH, expand=True, pady=3)

        self.preview_canvas = tk.Canvas(
            preview_container, bg="#fafafa",
            highlightthickness=0, width=800, height=280,
        )
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vscroll = tk.Scrollbar(preview_container, orient=tk.VERTICAL,
                               command=self.preview_canvas.yview)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        hscroll = tk.Scrollbar(preview_card, orient=tk.HORIZONTAL,
                               command=self.preview_canvas.xview)
        hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.preview_canvas.configure(yscrollcommand=vscroll.set,
                                      xscrollcommand=hscroll.set)

        self.preview_canvas.create_text(
            400, 140,
            text="尚未粘贴截图\n\n请按 Ctrl+V 粘贴截图\n或点击下方按钮加载图片",
            font=(FONT_FAMILY, 12), fill=COLORS["muted"], justify=tk.CENTER,
        )

        # ===== 操作按钮行 =====
        btn_bar = tk.Frame(self.root, bg=COLORS["bg"])
        btn_bar.pack(fill=tk.X, padx=25, pady=8)

        self.ocr_btn = self._make_btn(btn_bar, "🔍 开始 OCR 识别",
                                       self.do_ocr, color_key="success",
                                       font_size=11, state=tk.DISABLED)
        self.ocr_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.load_btn = self._make_btn(btn_bar, "📁 加载图片文件",
                                       self.load_image_file, color_key="info",
                                        font_size=11)
        self.load_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.summarize_btn = self._make_btn(btn_bar, "🤖 AI 总结",
                                            self.do_summarize, color_key="accent",
                                            font_size=11, state=tk.DISABLED)
        self.summarize_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.clear_btn = self._make_btn(btn_bar, "🗑 清空",
                                        self.clear_all, color_key="muted",
                                        font_size=11)
        self.clear_btn.pack(side=tk.LEFT)

        # ===== OCR 结果卡片 =====
        result_card = self._make_card(self.root, "OCR 识别结果", "📝")
        result_card.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 8))

        scroll_y = tk.Scrollbar(result_card)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.result_text = tk.Text(
            result_card,
            font=(FONT_FAMILY, 11),
            yscrollcommand=scroll_y.set,
            wrap=tk.WORD, padx=14, pady=12,
            bg=COLORS["card_bg"], fg=COLORS["text"],
            relief=tk.FLAT, bd=0,
            insertbackground=COLORS["accent"],
            selectbackground=COLORS["accent"],
            selectforeground="white",
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.result_text.yview)

        # ===== 底部操作栏 =====
        bottom = tk.Frame(self.root, bg=COLORS["card_bg"],
                          pady=12, padx=15)
        bottom.pack(fill=tk.X, padx=25, pady=(0, 15))

        # 左侧：目标笔记
        note_area = tk.Frame(bottom, bg=COLORS["card_bg"])
        note_area.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(note_area, text="📚 目标笔记:",
                 font=(FONT_FAMILY, 10, "bold"),
                 bg=COLORS["card_bg"], fg=COLORS["title"]).pack(side=tk.LEFT, padx=(0, 6))

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox",
                        fieldbackground=COLORS["card_bg"],
                        background=COLORS["card_bg"],
                        arrowcolor=COLORS["text_light"])

        self.note_combo = ttk.Combobox(note_area, width=38,
                                        font=(FONT_FAMILY, 10))
        self.note_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.refresh_notes()

        refresh_btn = self._make_btn(bottom, "🔄 刷新",
                                     self.refresh_notes, color_key="warning",
                                     font_size=9)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 20))

        # 右侧：操作按钮
        btn_right = tk.Frame(bottom, bg=COLORS["card_bg"])
        btn_right.pack(side=tk.RIGHT)

        self.discard_btn = self._make_btn(btn_right, "✕ 丢弃",
                                          self.discard_result,
                                          color_key="danger", font_size=10,
                                          state=tk.DISABLED)
        self.discard_btn.pack(side=tk.RIGHT, padx=(6, 0))

        self.save_btn = self._make_btn(btn_right, "💾 存入 Obsidian",
                                       self.save_to_obsidian,
                                       color_key="success", font_size=11,
                                       bold=True, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT)

    # ---- 业务逻辑 ----

    def refresh_notes(self):
        notes = []
        if os.path.exists(self.vault_path):
            for root, dirs, files in os.walk(self.vault_path):
                for f in files:
                    if f.endswith('.md'):
                        rel_path = os.path.relpath(os.path.join(root, f), self.vault_path)
                        notes.append(rel_path.replace('\\', '/'))
        notes.sort()
        self.note_combo['values'] = notes
        if notes:
            self.note_combo.current(0)

    def paste_image(self, event=None):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showwarning("提示", "剪贴板中没有图片，请先截图（Win+Shift+S）")
                return
            temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_paste.png')
            img.save(temp_path, 'PNG')
            self.current_image = temp_path
            self.show_preview(temp_path)
        except Exception as e:
            messagebox.showwarning("提示", f"粘贴失败: {str(e)}")

    def set_window_state(self, state):
        """切换窗口状态并调整大小"""
        if state in self.state_sizes:
            self.root.geometry(self.state_sizes[state])
            self.root.update_idletasks()

    def show_preview(self, image_path):
        try:
            from PIL import Image, ImageTk, ImageOps
            import threading

            def load():
                img = Image.open(image_path)
                max_width, max_height = 1400, 800
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                img = ImageOps.expand(img, border=2, fill='#ddd')
                self.photo = ImageTk.PhotoImage(img)
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                self.preview_canvas.config(scrollregion=(0, 0, img.width, img.height))
                self.ocr_btn.config(state=tk.NORMAL)
                self.result_text.delete(1.0, tk.END)
                self.ocr_text = ""
                self.summary_text = ""
                self.summarize_btn.config(state=tk.DISABLED, text="🤖 AI 总结")
                self.save_btn.config(state=tk.DISABLED)
                self.discard_btn.config(state=tk.DISABLED)
                # 切换到「有图未识别」状态
                self.set_window_state("preview")

            threading.Thread(target=load, daemon=True).start()
        except Exception as e:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                400, 140, text=f"预览失败: {str(e)}",
                font=(FONT_FAMILY, 12), fill=COLORS["danger"],
            )

    def load_image_file(self):
        filepath = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"),
                       ("所有文件", "*.*")]
        )
        if filepath:
            self.current_image = filepath
            self.show_preview(filepath)

    def preprocess_image(self, image_path):
        from PIL import Image, ImageEnhance, ImageFilter
        img = Image.open(image_path)
        if img.mode != 'L':
            img = img.convert('L')
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        img = img.filter(ImageFilter.SHARPEN)
        preprocessed_path = image_path.replace('.png', '_preprocessed.png').replace('.jpg', '_preprocessed.png')
        img.save(preprocessed_path, 'PNG')
        return preprocessed_path

    def do_ocr(self):
        if not self.current_image or not OCR_AVAILABLE:
            if not OCR_AVAILABLE:
                messagebox.showerror("错误", "RapidOCR 未安装")
            return

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "🔍 正在识别中...\n\n")
        self.result_text.update()

        try:
            preprocessed_path = self.preprocess_image(self.current_image)
            result, elapse = OCR_ENGINE(preprocessed_path)

            if result:
                self.ocr_text = "\n".join([item[1] for item in result])
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, "✅ OCR 识别完成\n\n")
                self.result_text.insert(tk.END, "─" * 50 + "\n\n")
                self.result_text.insert(tk.END, self.ocr_text)
                self.result_text.insert(tk.END, "\n\n" + "─" * 50)
                if isinstance(elapse, (list, tuple)):
                    elapse_str = f"{elapse[0]:.2f}" if elapse else "N/A"
                else:
                    elapse_str = f"{elapse:.2f}"
                self.result_text.insert(tk.END, f"\n⏱️ 识别耗时: {elapse_str}秒")
                self.save_btn.config(state=tk.NORMAL)
                self.discard_btn.config(state=tk.NORMAL)
                # 字数超过阈值且API已配置 → 启用总结按钮
                text_len = len(self.ocr_text.replace('\n', '').replace(' ', ''))
                api_key = self.summarize_cfg.get("api_key", "").strip()
                api_configured = api_key and api_key != "YOUR_API_KEY_HERE"
                if (self.summarize_cfg.get("enabled", True)
                        and text_len >= self.summarize_cfg.get("threshold", 500)
                        and api_configured):
                    self.summarize_btn.config(state=tk.NORMAL)
                    self.result_text.insert(tk.END, f"\n\n💡 识别到 {text_len} 字（≥{self.summarize_cfg['threshold']}），可点击「🤖 AI 总结」提炼要点")
                elif self.summarize_cfg.get("enabled", True) and text_len >= self.summarize_cfg.get("threshold", 500):
                    # 字数够但 API 未配置，显示提示
                    _, status_text = get_api_key_status()
                    self.result_text.insert(tk.END, f"\n\n⚠️ 识别到 {text_len} 字，但 {status_text}")
                # 切换到「已识别」状态
                self.set_window_state("recognized")
            else:
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, "❌ 未识别到文字\n\n请确保图片清晰，包含可识别的文字内容。")
                self.save_btn.config(state=tk.DISABLED)
                self.discard_btn.config(state=tk.DISABLED)
                self.summarize_btn.config(state=tk.DISABLED, text="🤖 AI 总结")
                # 保持在 preview 状态
        except Exception as e:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"❌ OCR 识别失败:\n\n{str(e)}")
            self.save_btn.config(state=tk.DISABLED)
            self.discard_btn.config(state=tk.DISABLED)
            self.summarize_btn.config(state=tk.DISABLED, text="🤖 AI 总结")

    def format_for_obsidian(self, text, source_file=None):
        filename = os.path.basename(source_file) if source_file else "截图"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = text.strip().split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        cleaned_text = '\n'.join(cleaned_lines)
        formatted = f"\n---\n**📷 OCR 识别** ({timestamp})\n**来源**: `{filename}`\n\n{cleaned_text}"
        if self.summary_text and not self.summary_text.startswith("❌"):
            formatted += f"\n\n> **🤖 AI 总结**: {self.summary_text}"
        formatted += "\n"
        return formatted.strip()

    def save_to_obsidian(self):
        if not self.ocr_text:
            messagebox.showwarning("提示", "没有可保存的内容")
            return
        target_note = self.note_combo.get()
        if not target_note:
            messagebox.showwarning("提示", "请选择目标笔记")
            return
        note_path = os.path.join(self.vault_path, target_note)
        content = self.format_for_obsidian(self.ocr_text, self.current_image)
        try:
            with open(note_path, 'a', encoding='utf-8') as f:
                f.write("\n" + "-" * 60 + "\n")
                f.write(content + "\n")
            messagebox.showinfo("成功", f"✅ 已存入:\n{target_note}")
            self.clear_all()
        except Exception as e:
            messagebox.showerror("保存失败", str(e))

    def do_summarize(self):
        """调用 AI API 总结 OCR 文本"""
        if not self.ocr_text:
            messagebox.showwarning("提示", "没有可总结的内容")
            return
        self.summarize_btn.config(state=tk.DISABLED, text="⏳ 总结中...")
        self.root.update()

        def _call():
            try:
                import requests
                cfg = self.summarize_cfg
                prompt = cfg["prompt"].replace("{text}", self.ocr_text)
                resp = requests.post(
                    f"{cfg['api_base']}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {cfg['api_key']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": cfg["model"],
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    },
                    timeout=60
                )
                resp.raise_for_status()
                data = resp.json()
                self.summary_text = data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                self.summary_text = f"❌ 总结失败: {str(e)}"

            # 回到主线程更新 UI
            def _update():
                self.result_text.insert(tk.END, "\n\n" + "─" * 50)
                self.result_text.insert(tk.END, f"\n🤖 AI 总结:\n\n{self.summary_text}\n")
                self.summarize_btn.config(state=tk.NORMAL, text="🤖 AI 总结")
            self.root.after(0, _update)

        threading.Thread(target=_call, daemon=True).start()

    def discard_result(self):
        if messagebox.askyesno("确认", "确定丢弃当前识别结果吗？"):
            self.clear_all()

    def clear_all(self):
        self.ocr_text = ""
        self.summary_text = ""
        self.current_image = None
        self.result_text.delete(1.0, tk.END)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(
            400, 140,
            text="尚未粘贴截图\n\n请按 Ctrl+V 粘贴截图\n或点击下方按钮加载图片",
            font=(FONT_FAMILY, 12), fill=COLORS["muted"], justify=tk.CENTER,
        )
        self.preview_canvas.config(scrollregion=(0, 0, 800, 300))
        self.ocr_btn.config(state=tk.DISABLED)
        self.summarize_btn.config(state=tk.DISABLED, text="🤖 AI 总结")
        self.save_btn.config(state=tk.DISABLED)
        self.discard_btn.config(state=tk.DISABLED)
        # 回到初始紧凑状态
        self.set_window_state("idle")


def main():
    if not OCR_AVAILABLE:
        print("⚠️ RapidOCR 未安装，正在安装...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install",
                        "rapidocr_onnxruntime", "-i",
                        "https://pypi.tuna.tsinghua.edu.cn/simple"],
                       check=True)
        from rapidocr_onnxruntime import RapidOCR
        globals()['OCR_ENGINE'] = RapidOCR()
        globals()['OCR_AVAILABLE'] = True

    root = tk.Tk()
    app = OcrGuiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
