import sys
print("Python:", sys.executable)
try:
    import win32clipboard
    print("win32clipboard OK")
except ImportError as e:
    print("win32clipboard FAIL:", e)

try:
    from PIL import Image
    print("Pillow OK")
except ImportError as e:
    print("Pillow FAIL:", e)
