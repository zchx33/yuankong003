from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import time, uuid, threading

app = Flask(__name__)
app.secret_key = "yuankong003_remote_control_2026"

# 内存设备池，存储安卓被控端连接
device_pool = {}
# 单人登录状态
user_session = {"login": False}

# ====================== 1.苹果iOS主控登录页面 ======================
login_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>远程中控登录</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{background:#f5f7fa;height:100vh;display:flex;align-items:center;justify-content:center}
.box{width:90%;max-width:360px;background:#fff;border-radius:16px;padding:30px;box-shadow:0 2px 12px #e0e4eb}
.title{font-size:22px;font-weight:bold;margin-bottom:24px;text-align:center;color:#222}
.input{width:100%;height:46px;border:1px solid #ddd;border-radius:10px;padding:0 14px;margin-bottom:16px;font-size:16px}
.btn{width:100%;height:48px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-size:17px;font-weight:500}
.tip{margin-top:14px;text-align:center;color:#666;font-size:14px}
</style>
</head>
<body>
<div class="box">
<div class="title">远程中控系统</div>
<form method="post" action="/login">
<input class="input" name="pwd" placeholder="输入登录密码" type="password" required>
<button class="btn" type="submit">登录中控</button>
</form>
<div class="tip">单人专属远控后台</div>
</div>
</body>
</html>
"""

# ====================== 2.苹果主控操控页面 ======================
control_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>设备操控面板</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{background:#111;color:#fff;padding:12px}
.screen{width:100%;height:70vh;background:#222;border-radius:12px;margin-bottom:12px;display:flex;align-items:center;justify-content:center;color:#aaa}
.ctrl-bar{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.btn-ctrl{height:44px;background:#2563eb;border:none;border-radius:8px;color:#fff;font-size:15px}
.logout{margin-top:12px;width:100%;height:42px;background:#dc2626;border:none;border-radius:8px;color:#fff}
.device-info{padding:10px;background:#222;border-radius:10px;margin-bottom:10px;font-size:14px}
</style>
</head>
<body>
<div class="device-info">在线设备ID：{{device_id}}</div>
<div class="screen">安卓设备画面区域</div>
<div class="ctrl-bar">
<button class="btn-ctrl" onclick="sendCmd('click')">点击屏幕</button>
<button class="btn-ctrl" onclick="sendCmd('sms')">读取短信</button>
<button class="btn-ctrl" onclick="sendCmd('back')">返回桌面</button>
</div>
<button class="logout" onclick="location.href='/logout'">退出登录</button>
<script>
function sendCmd(cmd){
fetch("/api/cmd",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({"cmd":cmd})
})
}
</script>
</body>
</html>
"""

# ====================== 3.安卓设备接入网页（浏览器打开链接页面） ======================
android_connect_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>设备接入</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{background:#0f172a;color:#fff;padding:20px;text-align:center}
.card{background:#1e293b;border-radius:14px;padding:24px;margin-top:30px}
.btn-conn{margin-top:20px;width:90%;height:50px;background:#10b981;border:none;border-radius:10px;color:#fff;font-size:16px}
</style>
</head>
<body>
<div class="card">
<h2>安卓被控端接入</h2>
<p style="margin:16px 0">点击下方按钮绑定中控服务</p>
<button class="btn-conn" onclick="connectDevice()">绑定设备</button>
</div>
<script>
function connectDevice(){
fetch("/api/device/connect")
.then(res=>res.json())
.then(data=>alert("设备绑定成功，设备ID："+data.device_id))
}
</script>
</body>
</html>
"""

# ====================== 路由接口 ======================
# 首页跳转登录
@app.route('/')
def index():
    if user_session["login"]:
        return redirect(url_for('control_panel', device_id=list(device_pool.keys())[0] if device_pool else ""))
    return redirect(url_for('login_page'))

# 登录页
@app.route('/login')
def login_page():
    return render_template_string(login_html)

# 登录提交
@app.route('/login', methods=["POST"])
def login_submit():
    pwd = request.form.get("pwd")
    # 单人固定密码，可自行修改
    if pwd == "123456":
        user_session["login"] = True
        return redirect(url_for('control_panel', device_id=list(device_pool.keys())[0] if device_pool else ""))
    return "密码错误，返回<a href='/login'>重新登录</a>"

# 主控操控面板
@app.route('/control/<device_id>')
def control_panel(device_id):
    if not user_session["login"]:
        return redirect(url_for('login_page'))
    return render_template_string(control_html, device_id=device_id)

# 安卓设备接入页面
@app.route('/android')
def android_page():
    return render_template_string(android_connect_html)

# 退出登录
@app.route('/logout')
def logout():
    user_session["login"] = False
    return redirect(url_for('login_page'))

# 设备绑定API
@app.route('/api/device/connect')
def device_connect():
    dev_id = str(uuid.uuid4())
    device_pool[dev_id] = {"status":"online","cmd":""}
    return jsonify({"code":200,"device_id":dev_id,"msg":"设备已接入"})

# 下发操控指令API
@app.route('/api/cmd', methods=["POST"])
def send_command():
    if not user_session["login"]:
        return jsonify({"code":403,"msg":"未登录"})
    data = request.get_json()
    cmd = data.get("cmd")
    if device_pool:
        dev_id = list(device_pool.keys())[0]
        device_pool[dev_id]["cmd"] = cmd
    return jsonify({"code":200,"msg":"指令下发成功"})

# 安卓APK轮询获取指令接口
@app.route('/api/device/cmd/<dev_id>')
def get_device_cmd(dev_id):
    if dev_id in device_pool:
        cmd = device_pool[dev_id]["cmd"]
        # 指令读取后清空
        device_pool[dev_id]["cmd"] = ""
        return jsonify({"code":200,"cmd":cmd})
    return jsonify({"code":404,"msg":"设备未在线"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)