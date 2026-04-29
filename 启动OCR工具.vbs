Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run """C:\Users\12081\AppData\Local\Programs\Python\Python313\pythonw.exe"" ocr_gui.py", 0, False
