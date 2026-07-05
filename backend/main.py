from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import time, uuid, threading

app = Flask(__name__)
app.secret_key = "yuankong003_remote_control_2026"

# 设备池：存储安卓被控设备
device_pool = {}

# 账号体系：主账号固定，子账号可由主账号新增
# 主账号：admin 密码 admin123
# 子账号列表
account_data = {
    "master": {
        "username": "admin",
        "password": "admin123",
        "is_master": True
    },
    "sub_accounts": {}
}

# ====================== 1.登录页面（支持主/子账号登录） ======================
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
<input class="input" name="user" placeholder="账号" required>
<input class="input" name="pwd" placeholder="密码" type="password" required>
<button class="btn" type="submit">登录中控</button>
</form>
<div class="tip">主账号：admin</div>
</div>
</body>
</html>
"""

# ====================== 2.主账号后台：子账号管理页面 ======================
admin_backend_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>主账号管理后台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{background:#f5f7fa;padding:16px}
.card{background:#fff;border-radius:14px;padding:20px;margin-bottom:16px}
.title{font-size:20px;font-weight:bold;margin-bottom:16px}
.input{width:100%;height:44px;border:1px solid #ddd;border-radius:8px;padding:0 12px;margin-bottom:12px}
.btn-add{width:100%;height:46px;background:#10b981;color:#fff;border:none;border-radius:8px;margin-bottom:16px}
.btn-del{height:38px;background:#ef4444;color:#fff;border:none;border-radius:6px;padding:0 10px}
.line{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #eee}
.nav{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:20px}
.nav-btn{height:42px;background:#2563eb;color:#fff;border:none;border-radius:8px}
</style>
</head>
<body>
<div class="nav">
<button class="nav-btn" onclick="location.href='/control'">设备操控面板</button>
<button class="nav-btn" onclick="location.href='/logout'">退出登录</button>
</div>
<div class="card">
<div class="title">新增子账号</div>
<form method="post" action="/api/add_sub">
<input class="input" name="sub_user" placeholder="子账号名称" required>
<input class="input" name="sub_pwd" placeholder="子账号密码" required>
<button class="btn-add" type="submit">创建子账号</button>
</form>
</div>
<div class="card">
<div class="title">现有子账号列表</div>
{% if subs|length == 0 %}
<p>暂无子账号</p>
{% else %}
{% for name,info in subs.items() %}
<div class="line">
<span>{{ name }}</span>
<form method="post" action="/api/del_sub">
<input hidden name="del_user" value="{{name}}">
<button class="btn-del" type="submit">删除</button>
</form>
</div>
{% endfor %}
{% endif %}
</div>
</body>
</html>
"""

# ====================== 3.设备操控面板（主/子账号共用，子账号无管理权限） ======================
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
.nav{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.nav-btn{height:40px;background:#333;border:none;border-radius:8px;color:#fff}
</style>
</head>
<body>
<div class="nav">
{% if is_master %}
<button class="nav-btn" onclick="location.href='/admin'">账号管理后台</button>
{% endif %}
<button class="nav-btn" onclick="location.href='/logout'">退出登录</button>
</div>
<div class="device-info">在线设备ID：{{device_id}}</div>
<div class="screen">安卓设备画面区域</div>
<div class="ctrl-bar">
<button class="btn-ctrl" onclick="sendCmd('click')">点击屏幕</button>
<button class="btn-ctrl" onclick="sendCmd('sms')">读取短信</button>
<button class="btn-ctrl" onclick="sendCmd('back')">返回桌面</button>
</div>
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

# ====================== 4.安卓设备接入网页 ======================
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

# ====================== 路由定义 ======================
# 首页入口（修复无设备404报错）
@app.route('/')
def index():
    # 判断是否登录
    if "login_user" not in session:
        return redirect(url_for('login_page'))
    # 已登录，判断有无设备
    if len(device_pool) > 0:
        dev_id = list(device_pool.keys())[0]
        return redirect(url_for('control_panel', device_id=dev_id))
    else:
        return """
        <html>
            <body style="text-align:center;padding:30px;font-size:18px;">
                <h3>暂无安卓被控设备在线</h3>
                <p>请用安卓设备打开接入链接绑定设备</p>
                <p>接入地址：/android</p>
                <a href="/android">前往设备接入页</a>
                <br><br>
                <a href="/logout">退出登录</a>
            </body>
        </html>
        """

# 登录页
@app.route('/login')
def login_page():
    return render_template_string(login_html)

# 登录提交接口
@app.route('/login', methods=["POST"])
def login_submit():
    user = request.form.get("user")
    pwd = request.form.get("pwd")
    # 校验主账号
    if user == account_data["master"]["username"] and pwd == account_data["master"]["password"]:
        session["login_user"] = user
        session["is_master"] = True
        return redirect(url_for('index'))
    # 校验子账号
    if user in account_data["sub_accounts"] and account_data["sub_accounts"][user]["password"] == pwd:
        session["login_user"] = user
        session["is_master"] = False
        return redirect(url_for('index'))
    return "账号或密码错误，<a href='/login'>返回登录</a>"

# 主账号管理后台
@app.route('/admin')
def admin_backend():
    # 未登录/非主账号禁止访问
    if "login_user" not in session or session["is_master"] is False:
        return redirect(url_for('login_page'))
    return render_template_string(admin_backend_html, subs=account_data["sub_accounts"])

# 新增子账号接口
@app.route('/api/add_sub', methods=["POST"])
def add_sub_account():
    if "login_user" not in session or session["is_master"] is False:
        return jsonify({"code":403,"msg":"无权限"})
    sub_user = request.form.get("sub_user")
    sub_pwd = request.form.get("sub_pwd")
    if sub_user in account_data["sub_accounts"] or sub_user == account_data["master"]["username"]:
        return "账号已存在 <a href='/admin'>返回</a>"
    account_data["sub_accounts"][sub_user] = {"password":sub_pwd}
    return redirect(url_for('admin_backend'))

# 删除子账号接口
@app.route('/api/del_sub', methods=["POST"])
def del_sub_account():
    if "login_user" not in session or session["is_master"] is False:
        return jsonify({"code":403,"msg":"无权限"})
    del_user = request.form.get("del_user")
    if del_user in account_data["sub_accounts"]:
        del account_data["sub_accounts"][del_user]
    return redirect(url_for('admin_backend'))

# 设备操控面板
@app.route('/control/<device_id>')
def control_panel(device_id):
    if "login_user" not in session:
        return redirect(url_for('login_page'))
    return render_template_string(control_html, device_id=device_id, is_master=session["is_master"])

# 安卓设备接入页面
@app.route('/android')
def android_page():
    return render_template_string(android_connect_html)

# 退出登录
@app.route('/logout')
def logout():
    session.clear()
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
    if "login_user" not in session:
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
        device_pool[dev_id]["cmd"] = ""
        return jsonify({"code":200,"cmd":cmd})
    return jsonify({"code":404,"msg":"设备未在线"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)