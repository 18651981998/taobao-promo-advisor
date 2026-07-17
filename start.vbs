Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
thisDir = fso.GetParentFolderName(WScript.ScriptFullName)
pyPath = "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
port = 8123

If Not fso.FileExists(pyPath) Then
    MsgBox "找不到 Python：" & pyPath & vbCrLf & "请检查 .workbuddy 是否安装", vbCritical, "启动失败"
    WScript.Quit
End If
If Not fso.FileExists(chromePath) Then
    MsgBox "未检测到 Google Chrome。" & vbCrLf & "360浏览器会导致页面卡加载，请安装 Chrome 后使用。", vbCritical, "启动失败"
    WScript.Quit
End If

' 启动后台服务（0 = 隐藏窗口，不阻塞）
cmd = """ & pyPath & "" "" & thisDir & "\promo_server.py""
ws.Run cmd, 0, False

WScript.Sleep 2500

' 用 Chrome 打开本地工具
ws.Run """ & chromePath & "" "http://127.0.0.1:" & port & "/"", 1, False
