' Easy Saving launcher: starts the app with pythonw so no console window appears.
Set sh = CreateObject("WScript.Shell")
appDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = appDir
sh.Run """" & appDir & "\.venv\Scripts\pythonw.exe"" run.py", 0, False
