# 📷 Screenshot OCR to Obsidian

将截图快速 OCR 识别并存入 Obsidian 笔记库的桌面工具。

## 功能特性

- ✅ **Ctrl+V 粘贴截图** — 支持 Win+Shift+S 截图后直接粘贴
- ✅ **RapidOCR 中文识别** — 基于 ONNX Runtime，无需网络
- ✅ **图片预处理** — 自动灰度化、对比度增强、锐化
- ✅ **大图滚动预览** — 支持全屏截图完整显示
- ✅ **Obsidian 集成** — 自动扫描笔记库，追加识别结果

## 安装依赖

```bash
pip install rapidocr_onnxruntime pillow
```

## 使用方法

1. 双击 `run_gui.bat` 启动
2. 截图（Win+Shift+S）
3. 回到工具窗口，按 Ctrl+V 粘贴
4. 点击「开始 OCR 识别」
5. 选择目标笔记，点击「存入 Obsidian」

## 目录结构

```
screenshot-ocr/
├── ocr_gui.py        # GUI 主程序
├── ocr_to_note.py    # 命令行版本
├── run_gui.bat       # Windows 启动脚本
└── README.md
```

## 配置

修改 `ocr_gui.py` 顶部的 `VAULT_PATH` 为你的 Obsidian 笔记库路径：

```python
VAULT_PATH = r"D:\your\obsidian\vault"
```

## 已知限制

- OCR 准确率受限于 RapidOCR 模型，复杂排版可能漏字/错字
- 建议截图时框小一点，只框文字区域
- 识别结果可在 GUI 中手动编辑后再保存

## 技术栈

- Python 3.13
- RapidOCR (ONNX Runtime)
- Pillow (图像处理)
- Tkinter (GUI)
