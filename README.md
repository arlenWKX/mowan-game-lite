# 魔丸小游戏 - 轻量版

基于 Flask + Vue.js 的轻量版魔丸游戏系统。

## 特性

- 🎮 完整的魔丸游戏规则实现
- 👥 2-5人在线对战
- 🔐 JWT 身份认证
- 🏠 房间管理系统
- 📊 排行榜功能
- 📱 响应式设计，支持移动端和桌面端
- 💻 离线模式（新手教学）

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端将在 http://localhost:5000 启动

### 前端部署

前端为纯静态文件，可直接部署：

```bash
# 使用 Python 简单服务器
cd frontend
python -m http.server 8080

# 或使用 nginx/apache 等
```

访问 http://localhost:8080 即可

## 默认账号

- 管理员: `admin` / `admin123`

## 技术栈

- **后端**: Python + Flask + SQLite
- **前端**: Vue.js 3 + 原生 CSS
- **认证**: JWT