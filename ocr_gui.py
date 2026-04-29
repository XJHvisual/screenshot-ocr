#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图 OCR 转 Obsidian 笔记 - GUI 版本
功能：粘贴截图 → OCR 识别 → 预览笔记 → 确认存入
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
from datetime import datetime
import re

# 笔记库路径
VAULT_PATH = r"D:\12081\Documents\PCO"

# OCR 工具
try:
    from rapidocr_onnxruntime import RapidOCR
    OCR_ENGINE = RapidOCR()
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("RapidOCR 未安装，请运行: pip install rapidocr_onnxruntime")


class OcrGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("截图 OCR 转笔记")
        self.root.geometry("900x700")
        self.root.configure(bg="#f5f5f5")
        
        # OCR 结果
        self.ocr_text = ""
        self.current_image = None
        
        # 笔记库路径
        self.vault_path = VAULT_PATH
        
        self.setup_ui()
        
        # 绑定 Ctrl+V 粘贴
        self.root.bind('<Control-v>', self.paste_image)
        self.root.bind('<Control-V>', self.paste_image)
        
    def setup_ui(self):
        # 顶部说明
        top_frame = tk.Frame(self.root, bg="#f5f5f5", pady=10)
        top_frame.pack(fill=tk.X, padx=20)
        
        tk.Label(top_frame, text="📷 截图 OCR 转 Obsidian 笔记", 
                font=("Microsoft YaHei", 16, "bold"), 
                bg="#f5f5f5", fg="#333").pack()
        
        tk.Label(top_frame, text="按 Ctrl+V 粘贴截图，或点击下方按钮选择图片文件", 
                font=("Microsoft YaHei", 10), bg="#f5f5f5", fg="#666").pack()
        
        # 截图预览区域
        preview_frame = tk.LabelFrame(self.root, text="📸 截图预览", 
                                     font=("Microsoft YaHei", 11), padx=10, pady=10)
        preview_frame.pack(fill=tk.BOTH, expand=False, padx=20, pady=10)
        
        # 创建带滚动条的预览区域
        preview_container = tk.Frame(preview_frame, bg="#e0e0e0")
        preview_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Canvas 用于显示大图（支持滚动）
        self.preview_canvas = tk.Canvas(preview_container, bg="#e0e0e0", 
                                        highlightthickness=0,
                                        width=800, height=300)
        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        vscrollbar = tk.Scrollbar(preview_container, orient=tk.VERTICAL, 
                                  command=self.preview_canvas.yview)
        vscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        hscrollbar = tk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, 
                                  command=self.preview_canvas.xview)
        hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.preview_canvas.configure(yscrollcommand=vscrollbar.set,
                                      xscrollcommand=hscrollbar.set)
        
        # 在 Canvas 中创建图片显示区域
        self.preview_canvas.create_text(
            350, 150, text="尚未粘贴截图\n\n请按 Ctrl+V 粘贴截图\n或点击下方按钮加载图片",
            font=("Microsoft YaHei", 12), fill="#888", justify=tk.CENTER
        )
        
        # 按钮行
        btn_frame = tk.Frame(self.root, bg="#f5f5f5")
        btn_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.ocr_btn = tk.Button(btn_frame, text="🔍 开始 OCR 识别", 
                                 command=self.do_ocr, state=tk.DISABLED,
                                 font=("Microsoft YaHei", 11), 
                                 bg="#4CAF50", fg="white", padx=15, pady=8,
                                 cursor="hand2")
        self.ocr_btn.pack(side=tk.LEFT, padx=5)
        
        self.load_btn = tk.Button(btn_frame, text="📁 加载图片文件", 
                                 command=self.load_image_file,
                                 font=("Microsoft YaHei", 11), 
                                 bg="#2196F3", fg="white", padx=15, pady=8,
                                 cursor="hand2")
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = tk.Button(btn_frame, text="🗑️ 清空", 
                                  command=self.clear_all,
                                  font=("Microsoft YaHei", 11), 
                                  bg="#9E9E9E", fg="white", padx=15, pady=8,
                                  cursor="hand2")
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # OCR 结果预览
        result_frame = tk.LabelFrame(self.root, text="📝 OCR 识别结果", 
                                    font=("Microsoft YaHei", 11), padx=10, pady=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 添加滚动条
        scroll_y = tk.Scrollbar(result_frame)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_text = tk.Text(result_frame, font=("Consolas", 11),
                                   yscrollcommand=scroll_y.set,
                                   wrap=tk.WORD, padx=10, pady=10,
                                   bg="#fff", fg="#333")
        self.result_text.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.result_text.yview)
        
        # 底部操作区
        bottom_frame = tk.Frame(self.root, bg="#f5f5f5", pady=15)
        bottom_frame.pack(fill=tk.X, padx=20)
        
        # 目标笔记选择
        tk.Label(bottom_frame, text="📚 目标笔记:", 
                font=("Microsoft YaHei", 11), bg="#f5f5f5").pack(side=tk.LEFT, padx=5)
        
        self.note_combo = ttk.Combobox(bottom_frame, width=35, 
                                       font=("Microsoft YaHei", 10))
        self.note_combo.pack(side=tk.LEFT, padx=5)
        self.refresh_notes()
        
        refresh_btn = tk.Button(bottom_frame, text="🔄 刷新笔记列表", 
                               command=self.refresh_notes,
                               font=("Microsoft YaHei", 10),
                               bg="#FF9800", fg="white", padx=10, pady=5,
                               cursor="hand2")
        refresh_btn.pack(side=tk.LEFT, padx=10)
        
        # 保存按钮
        self.save_btn = tk.Button(bottom_frame, text="💾 存入 Obsidian", 
                                 command=self.save_to_obsidian, state=tk.DISABLED,
                                 font=("Microsoft YaHei", 12, "bold"), 
                                 bg="#4CAF50", fg="white", padx=20, pady=8,
                                 cursor="hand2")
        self.save_btn.pack(side=tk.RIGHT, padx=5)
        
        self.discard_btn = tk.Button(bottom_frame, text="❌ 丢弃", 
                                    command=self.discard_result, state=tk.DISABLED,
                                    font=("Microsoft YaHei", 11), 
                                    bg="#f44336", fg="white", padx=15, pady=8,
                                    cursor="hand2")
        self.discard_btn.pack(side=tk.RIGHT, padx=5)
        
    def refresh_notes(self):
        """刷新笔记列表"""
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
        """从剪贴板粘贴图片"""
        try:
            from PIL import ImageGrab
            
            # 用 Pillow 的 ImageGrab 直接抓剪贴板图片
            img = ImageGrab.grabclipboard()
            
            if img is None:
                messagebox.showwarning("\u63d0\u793a", "\u526a\u8d34\u677f\u4e2d\u6ca1\u6709\u56fe\u7247\uff0c\u8bf7\u5148\u622a\u56fe\uff08Win+Shift+S\uff09")
                return
            
            # 保存临时文件
            temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_paste.png')
            img.save(temp_path, 'PNG')
            print(f"\u5df2\u4fdd\u5b58\u4e34\u65f6\u56fe\u7247: {temp_path}")
            
            self.current_image = temp_path
            self.show_preview(temp_path)
            
        except Exception as e:
            messagebox.showwarning("\u63d0\u793a", f"\u7c98\u8d34\u5931\u8d25: {str(e)}")
            
    def show_preview(self, image_path):
        """显示图片预览"""
        try:
            from PIL import Image, ImageTk, ImageOps
            import threading
            
            # 异步加载避免卡顿
            def load():
                img = Image.open(image_path)
                
                # 限制最大尺寸，但保持比例
                max_width, max_height = 1400, 800
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # 添加边框
                img = ImageOps.expand(img, border=2, fill='#ccc')
                
                self.photo = ImageTk.PhotoImage(img)
                
                # 清空 Canvas
                self.preview_canvas.delete("all")
                
                # 显示图片
                self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                
                # 调整 Canvas 滚动区域
                self.preview_canvas.config(scrollregion=(0, 0, img.width, img.height))
                
                # 启用 OCR 按钮
                self.ocr_btn.config(state=tk.NORMAL)
                
                # 清除旧结果
                self.result_text.delete(1.0, tk.END)
                self.ocr_text = ""
                self.save_btn.config(state=tk.DISABLED)
                self.discard_btn.config(state=tk.DISABLED)
            
            threading.Thread(target=load, daemon=True).start()
            
        except Exception as e:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(
                350, 150, text=f"预览失败: {str(e)}",
                font=("Microsoft YaHei", 12), fill="#f44336"
            )
            
    def load_image_file(self):
        """加载本地图片文件"""
        filepath = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), 
                      ("所有文件", "*.*")]
        )
        if filepath:
            self.current_image = filepath
            self.show_preview(filepath)
            
    def preprocess_image(self, image_path):
        """预处理图片提升 OCR 准确率"""
        from PIL import Image, ImageEnhance, ImageFilter
        import os
        
        img = Image.open(image_path)
        
        # 转为灰度
        if img.mode != 'L':
            img = img.convert('L')
        
        # 自适应对比度增强
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # 轻微锐化
        img = img.filter(ImageFilter.SHARPEN)
        
        # 保存临时预处理图
        preprocessed_path = image_path.replace('.png', '_preprocessed.png').replace('.jpg', '_preprocessed.png')
        img.save(preprocessed_path, 'PNG')
        return preprocessed_path
        
    def do_ocr(self):
        """执行 OCR 识别"""
        if not self.current_image or not OCR_AVAILABLE:
            if not OCR_AVAILABLE:
                messagebox.showerror("错误", "RapidOCR 未安装")
            return
            
        # 显示进度
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "🔍 正在识别中...\n\n")
        self.result_text.update()
        
        try:
            # 预处理图片
            preprocessed_path = self.preprocess_image(self.current_image)
            result, elapse = OCR_ENGINE(preprocessed_path)
            
            if result:
                # 合并识别结果
                self.ocr_text = "\n".join([item[1] for item in result])
                
                # 显示结果
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, "✅ OCR 识别完成\n\n" + "="*50 + "\n\n")
                self.result_text.insert(tk.END, self.ocr_text)
                self.result_text.insert(tk.END, "\n\n" + "="*50)
                # elapse 可能是 list，处理一下
                if isinstance(elapse, (list, tuple)):
                    elapse_str = f"{elapse[0]:.2f}" if elapse else "N/A"
                else:
                    elapse_str = f"{elapse:.2f}"
                self.result_text.insert(tk.END, f"\n⏱️ 识别耗时: {elapse_str}秒")
                
                # 启用保存按钮
                self.save_btn.config(state=tk.NORMAL)
                self.discard_btn.config(state=tk.NORMAL)
                
            else:
                self.result_text.delete(1.0, tk.END)
                self.result_text.insert(tk.END, "❌ 未识别到文字\n\n请确保图片清晰，包含可识别的文字内容。")
                self.save_btn.config(state=tk.DISABLED)
                self.discard_btn.config(state=tk.DISABLED)
                
        except Exception as e:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"❌ OCR 识别失败:\n\n{str(e)}")
            self.save_btn.config(state=tk.DISABLED)
            self.discard_btn.config(state=tk.DISABLED)
            
    def format_for_obsidian(self, text, source_file=None):
        """格式化为 Obsidian 笔记格式"""
        # 获取文件名
        filename = os.path.basename(source_file) if source_file else "截图"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 清理文本：移除多余空白
        lines = text.strip().split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        cleaned_text = '\n'.join(cleaned_lines)
        
        # 格式化为 Obsidian 块
        formatted = f"""
---
**📷 OCR 识别** ({timestamp})
**来源**: `{filename}`

{cleaned_text}
"""
        return formatted.strip()
        
    def save_to_obsidian(self):
        """保存到 Obsidian"""
        if not self.ocr_text:
            messagebox.showwarning("提示", "没有可保存的内容")
            return
            
        target_note = self.note_combo.get()
        if not target_note:
            messagebox.showwarning("提示", "请选择目标笔记")
            return
            
        note_path = os.path.join(self.vault_path, target_note)
        
        # 格式化内容
        content = self.format_for_obsidian(self.ocr_text, self.current_image)
        
        try:
            # 追加到笔记
            with open(note_path, 'a', encoding='utf-8') as f:
                f.write("\n" + "-"*60 + "\n")
                f.write(content + "\n")
            
            messagebox.showinfo("成功", f"✅ 已存入:\n{target_note}")
            
            # 清空并准备下一次
            self.clear_all()
            
        except Exception as e:
            messagebox.showerror("保存失败", str(e))
            
    def discard_result(self):
        """丢弃结果"""
        if messagebox.askyesno("确认", "确定丢弃当前识别结果吗？"):
            self.clear_all()
            
    def clear_all(self):
        """清空所有"""
        self.ocr_text = ""
        self.current_image = None
        self.result_text.delete(1.0, tk.END)
        
        # 清空 Canvas 预览区
        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(
            400, 150, text="尚未粘贴截图\n\n请按 Ctrl+V 粘贴截图\n或点击下方按钮加载图片",
            font=("Microsoft YaHei", 12), fill="#888", justify=tk.CENTER
        )
        self.preview_canvas.config(scrollregion=(0, 0, 800, 300))
        self.ocr_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.discard_btn.config(state=tk.DISABLED)


def main():
    # 检查依赖
    if not OCR_AVAILABLE:
        print("⚠️ RapidOCR 未安装，正在安装...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", 
                       "rapidocr_onnxruntime", "-i", 
                       "https://pypi.tuna.tsinghua.edu.cn/simple"],
                      check=True)
        # 重新导入
        from rapidocr_onnxruntime import RapidOCR
        globals()['OCR_ENGINE'] = RapidOCR()
        globals()['OCR_AVAILABLE'] = True
    
    # 剪贴板图片使用 Pillow ImageGrab，无需 pywin32
    
    # 创建 GUI
    root = tk.Tk()
    app = OcrGuiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
