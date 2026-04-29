# -*- coding: utf-8 -*-
"""
截图 OCR 转 Obsidian 笔记工具
使用 RapidOCR（PaddleOCR 轻板，纯 Python，无外部依赖）
功能：截图 → OCR识别 → 追加到Obsidian笔记
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from rapidocr_onnxruntime import RapidOCR


class OCRToNote:
    def __init__(self, obsidian_vault: str):
        """
        初始化 OCR 工具

        Args:
            obsidian_vault: Obsidian 笔记库根目录
        """
        self.vault_path = Path(obsidian_vault)
        if not self.vault_path.exists():
            raise ValueError(f"笔记库不存在: {obsidian_vault}")

        # 初始化 RapidOCR
        print("正在加载 OCR 模型...")
        self.ocr = RapidOCR()
        print("OCR 模型加载完成")

    def list_notes(self, folder: str = None) -> list:
        """
        列出笔记库中的所有 .md 文件

        Args:
            folder: 子文件夹名称（可选）

        Returns:
            笔记文件路径列表
        """
        if folder:
            search_path = self.vault_path / folder
        else:
            search_path = self.vault_path

        notes = list(search_path.rglob("*.md"))
        return sorted(notes, key=lambda x: x.stat().st_mtime, reverse=True)

    def ocr_image(self, image_path: str) -> str:
        """
        对图片进行 OCR 识别

        Args:
            image_path: 图片路径

        Returns:
            识别出的文本（Markdown 格式）
        """
        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        print(f"正在识别: {img_path.name}")

        # 执行 OCR
        result, elapse = self.ocr(str(img_path))

        if result is None or len(result) == 0:
            return ""

        # 提取文字（result 是 [[box], text, confidence] 的列表）
        lines = []
        for item in result:
            if len(item) >= 2:
                text = str(item[1])  # 识别的文字
                lines.append(text)

        # 合并为文本
        text = '\n'.join(lines)

        # 添加来源信息
        header = f"\n\n---\n**📷 OCR 识别** ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n**来源**: `{img_path.name}`\n\n"

        return header + text

    def append_to_note(self, note_path: str, content: str) -> bool:
        """
        追加内容到笔记

        Args:
            note_path: 笔记路径
            content: 要追加的内容

        Returns:
            是否成功
        """
        note = Path(note_path)
        if not note.exists():
            print(f"笔记不存在: {note_path}")
            return False

        try:
            # 追加写入
            with open(note, 'a', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已追加到: {note.name}")
            return True
        except Exception as e:
            print(f"写入失败: {e}")
            return False

    def interactive_mode(self, image_path: str = None):
        """
        交互模式：选择图片 → 选择笔记 → 追加
        """
        print("\n" + "="*50)
        print("  截图 OCR 转 Obsidian 笔记")
        print("="*50)

        # 1. 选择图片
        if image_path:
            img_path = image_path
        else:
            print("\n请输入图片路径（或拖拽截图到此处）:")
            img_path = input("> ").strip().strip('"').strip("'")

        if not Path(img_path).exists():
            print(f"❌ 图片不存在: {img_path}")
            return

        # 2. OCR 识别
        ocr_text = self.ocr_image(img_path)
        if not ocr_text:
            print("❌ 未识别到文字")
            return

        print("\n" + "-"*40)
        print("识别结果预览:")
        print("-"*40)
        preview = ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text
        print(preview)
        print("-"*40)

        # 3. 列出笔记供选择
        print("\n正在扫描笔记库...")
        notes = self.list_notes()

        if not notes:
            print("❌ 未找到笔记文件")
            return

        print(f"\n找到 {len(notes)} 个笔记（按修改时间排序）:\n")
        for i, note in enumerate(notes[:20], 1):  # 只显示最近20个
            rel_path = note.relative_to(self.vault_path)
            print(f"  [{i:2d}] {rel_path}")

        if len(notes) > 20:
            print(f"  ... 还有 {len(notes) - 20} 个笔记")

        # 4. 选择目标笔记
        print("\n请选择目标笔记编号（或输入笔记路径）:")
        choice = input("> ").strip()

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(notes):
                target_note = notes[idx]
            else:
                print("❌ 编号超出范围")
                return
        else:
            # 当作路径处理
            target_note = self.vault_path / choice
            if not target_note.exists():
                print(f"❌ 笔记不存在: {choice}")
                return

        # 5. 确认追加
        print(f"\n将追加到: {target_note.relative_to(self.vault_path)}")
        print("确认追加？(y/n):")
        confirm = input("> ").strip().lower()

        if confirm == 'y':
            self.append_to_note(str(target_note), ocr_text)
        else:
            print("已取消")


def main():
    parser = argparse.ArgumentParser(description="截图 OCR 转 Obsidian 笔记")
    parser.add_argument("--vault", "-v", help="Obsidian 笔记库路径")
    parser.add_argument("--image", "-i", help="图片路径")
    parser.add_argument("--note", "-n", help="目标笔记路径（相对路径）")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有笔记")

    args = parser.parse_args()

    # 默认笔记库路径
    vault_path = args.vault or r"D:\12081\Documents\PCO"

    try:
        ocr_tool = OCRToNote(vault_path)

        if args.list:
            # 列出笔记
            notes = ocr_tool.list_notes()
            print(f"\n笔记库: {vault_path}")
            print(f"共 {len(notes)} 个笔记:\n")
            for note in notes:
                rel_path = note.relative_to(ocr_tool.vault_path)
                print(f"  {rel_path}")
        elif args.image and args.note:
            # 命令行模式：直接处理
            ocr_text = ocr_tool.ocr_image(args.image)
            note_path = ocr_tool.vault_path / args.note
            ocr_tool.append_to_note(str(note_path), ocr_text)
        else:
            # 交互模式
            ocr_tool.interactive_mode(args.image)

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
