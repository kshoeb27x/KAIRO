' ============================================================
' Start_JARVIS.vbs — Hidden launcher (no console window)
' ============================================================
' This VBScript launches Start_JARVIS.bat silently so that
' JARVIS runs in the background without a visible terminal.
' ============================================================

Dim WshShell, scriptDir, batPath

Set WshShell = CreateObject("WScript.Shell")

' Resolve the directory this VBS lives in
scriptDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
batPath = scriptDir & "\Start_JARVIS.bat"

' Run hidden (0 = hidden window), False = don't wait for completion
WshShell.Run Chr(34) & batPath & Chr(34), 0, False

Set WshShell = Nothing
