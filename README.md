# 滴鱼简历助手 XG Resume Studio

> 📁 本地优先的个人简历管理系统：上传证书照片 / PDF / Word，自动识别**获奖情况**与**任职情况**；
> 填好资料后用四套场景化 A4 模板一键产出简历（网页预览 / 打印存 PDF / Word 下载）。
> 所有数据只存在你自己的电脑里。

![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)

<!-- 截图占位：发布前请替换为真实截图（使用示例数据拍摄，勿含个人信息）
![首页](docs/screenshots/home.png)
![简历预览](docs/screenshots/resume.png)
-->

## ✨ 特性

- **材料 → 结构化条目**：证书图片自动 OCR（支持 EXIF 方向校正、手动旋转重试），
  规则提取获奖与任职候选，弹窗勾选确认后才入库；配置大模型 API 后可一键「AI 整理」
- **重复导入检测**：同一份材料（标题+时间相同）不会被录入两次
- **四套场景模板**：求职·经典单栏 / 保研·学术强调 / 晋升·履历时间轴 / 评优·极简黑白，
  支持 6 色主题切换、三档密度、七个模块自由显隐排序；精确 A4 排版与打印规则
- **佐证文件**：每条获奖/任职可挂证书扫描件，条目删除时级联清理
- **AI 助手「小点」**：分析简历用途、改写个人简介（一键采纳）、优化条目描述
- **多账户**：轻量虚拟账户隔离家人/室友的数据，互不可见
- **手机扫码直传**：局域网内扫码，手机拍证书直接进入系统
- **数据安全**：单文件 SQLite + 每次启动自动滚动备份；API Key 仅本地存储且界面只显示掩码

## 🚀 快速开始

### Windows（推荐）

1. 安装 [Python 3.10–3.14](https://www.python.org/downloads/)（勾选 Add to PATH）
2. 双击 `滴鱼简历助手.bat` —— 首次运行会自动创建虚拟环境并安装依赖（几分钟，请勿关窗），然后打开浏览器
3. 按初始化向导完成配置即可使用

### macOS / Linux

```bash
git clone <仓库地址> resume-studio && cd resume-studio
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
# 打开 http://127.0.0.1:8000
```

### 手机扫码直传

双击 `滴鱼简历助手-局域网直传.bat`（首次需允许防火墙），手机连接同一 Wi-Fi，
扫首页二维码并输入**配对码**（启动窗口与首页二维码下方均有显示）即可拍照直传。
令牌绑定当前账户，可在首页随时重置作废。

## 🤖 配置 AI（可选）

不配置也能正常使用全部手动功能与规则提取。配置后解锁 AI 整理与小点助手：

| 服务商 | 接口地址 | 推荐模型 |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Moonshot Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Ollama（本地） | `http://127.0.0.1:11434/v1` | 你已拉取的模型 |

任何兼容 OpenAI Chat Completions 的接口均可。首页填入后点「测试连接」验证。

## 🔒 隐私说明

- 全部数据（数据库、上传文件、导出文档）仅保存在程序目录内，卸载即删除
- AI 功能关闭时，没有任何数据离开你的电脑
- AI 功能启用后，相关文本只会发送到**你自己填写**的接口商；密钥仅保存在本地数据库且界面回显掩码
- 局域网模式请在可信网络中使用；二维码链接即钥匙，可随时重置

## ❓ FAQ

- **局域网模式要配对码？** 安全设计：手机等设备首次打开需输入启动窗口/首页显示的 6 位配对码，30 天内免输，每次重启自动刷新
- **端口被占用？** `滴鱼简历助手.bat` 自动在 8000~8010 中寻找空闲端口；也可自行修改启动命令里的 `--port`
- **依赖安装慢/失败？** 默认源失败会自动改用清华镜像重试；也可手动加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`
- **识别文字很少？** 扫描件质量所限，试试「旋转重试」，或配置 AI 后点「AI 整理」
- **想彻底重置？** 关闭程序后删除整个 `data/` 文件夹，重启即回到全新状态
- **备份在哪？** `data/data_backups/` 下每次启动滚动保留最近 20 份，误操作可用其恢复

## 🗺️ 路线图

- [ ] 服务端 PDF 导出（摆脱浏览器打印）
- [ ] 多份简历版本（保研版/求职版共享底层数据）
- [ ] PyInstaller 单文件 exe 分发
- [ ] 英文界面（i18n）

## 🤝 参与贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。提交前请确保 `pytest` 与 `ruff check` 通过。

## 📮 支持与反馈

运行环境、启动报错类问题，请先阅读根目录的 **《运行环境配置说明.txt》**（含常见问题自查清单）。
仍无法解决请联系开发者：**maplelloyd@163.com**（请注明问题现象 + 报错截图）。

## 📄 许可证

[MIT](LICENSE)
