from flask import Flask, jsonify
import time

app = Flask(__name__)

# 测试接口，心跳访问用
@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "time": time.time(),
        "msg": "服务正常在线"
    })

# 你的业务接口可以写在这里

if __name__ == "__main__":
    # Render固定端口配置
    app.run(host="0.0.0.0", port=10000)