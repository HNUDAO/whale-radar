# whale-radar

巨鲸异动雷达 — 监控链上巨鲸地址，大额转账或 DeFi 合约交互时通过 Telegram 推送消息。

## 文件结构

```
whale-radar/
├── main.py                  # 主循环入口
├── config.py                # 环境变量配置 + 验证
├── etherscan_client.py      # Etherscan API V2 客户端（内置限速）
├── telegram_client.py       # Telegram Bot API 客户端
├── rules.py                 # 规则判断 + JSON 加载 + 区块浏览器链接
├── storage.py               # SQLite 存储（BatchWriter 批量写入）
├── whales.json              # 监控的巨鲸地址
├── defi_contracts.json      # DeFi 合约地址
├── exchange_addresses.json  # 交易所地址（用于消息标注）
├── requirements.txt         # Python 依赖
├── Procfile                 # Railway 启动命令
├── .env.example             # 环境变量示例
├── .gitignore
└── README.md
```

## Windows 本地测试

### 1. 安装依赖

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入真实值：

```bash
cp .env.example .env
```

编辑 `.env`：

```
ETHERSCAN_API_KEY=你的Etherscan API Key
TELEGRAM_BOT_TOKEN=你的Telegram Bot Token
TELEGRAM_CHAT_ID=你的Chat ID
CHAIN_ID=1
POLL_INTERVAL=60
NATIVE_THRESHOLD=10
ERC20_THRESHOLD=100000
```

### 3. 设置环境变量

Windows PowerShell：

```powershell
Get-Content .env | ForEach-Object {
    $name, $value = $_.split('=', 2)
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}
```

或 CMD：

```cmd
for /f "tokens=1,2 delims==" %a in (.env) do set %a=%b
```

### 4. 运行

```bash
python main.py
```

程序启动后 Telegram 会收到启动通知，包含 Chain ID 和区块浏览器地址。

> **首次运行**：程序会自动获取当前最新区块号作为起点，只监控启动后的新交易，不会推送历史交易。

## GitHub 提交

```bash
git add .
git commit -m "feat: whale-radar initial implementation"
git push origin main
```

确认 `.env` 不会被提交（已在 `.gitignore` 中）。

## Railway 部署

### 1. 创建项目

- 在 Railway 中创建新项目，关联 GitHub 仓库
- 选择 `whale-radar` 仓库

### 2. 配置 Variables

在 Railway 项目的 **Variables** 页添加：

| 变量名 | 必填 | 说明 | 示例值 |
|--------|------|------|--------|
| `ETHERSCAN_API_KEY` | 是 | Etherscan API Key | `ABC...` |
| `TELEGRAM_BOT_TOKEN` | 是 | Telegram Bot Token | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | 是 | Telegram Chat ID | `-1001234567890` |
| `CHAIN_ID` | 否 | 链 ID（默认 1） | `1` |
| `POLL_INTERVAL` | 否 | 轮询间隔秒数（默认 60） | `60` |
| `NATIVE_THRESHOLD` | 否 | Native 大额阈值（默认 10） | `10` |
| `ERC20_THRESHOLD` | 否 | ERC20 大额阈值（默认 100000） | `100000` |
| `DATA_DIR` | 否 | SQLite 目录（默认 .） | `/app/data` |

### 3. 配置 Volume

- 在 Railway 中添加 **Volume**
- **Mount path**: `/app/data`
- SQLite 数据库持久化在 `/app/data/radar.sqlite3`

> 未配置 Volume 时程序仍可运行，但重启后已处理的交易记录会丢失，可能导致重复推送。

### 4. Start Command

```
python main.py
```

## 支持的链

通过 `CHAIN_ID` 环境变量配置，自动匹配区块浏览器：

| 链 | CHAIN_ID | 浏览器 |
|----|----------|--------|
| Ethereum | 1 | etherscan.io |
| Polygon | 137 | polygonscan.com |
| BSC | 56 | bscscan.com |
| Arbitrum | 42161 | arbiscan.io |
| Optimism | 10 | optimistic.etherscan.io |
| Avalanche | 43114 | snowtrace.io |
| Base | 8453 | basescan.org |

其他链 ID 请参考 Etherscan API V2 文档。未在列表中的链默认使用 etherscan.io。

## 功能细节

### 交易检测

- **Native Transfer**：普通 ETH/native token 转账，超过 `NATIVE_THRESHOLD` 时推送
- **ERC20 Transfer**：ERC20 代币转账，超过 `ERC20_THRESHOLD` 时推送（自动处理不同 decimals）
- **DeFi Interaction**：交易目标是 `defi_contracts.json` 中的合约时推送（不限金额）

### 推送消息

消息包含：
- 事件类型（Native Transfer / ERC20 Transfer / DeFi Interaction）
- 巨鲸标签
- 金额和代币符号
- 收发地址（交易所地址自动标注 `[Exchange]`）
- 可点击的区块浏览器交易链接

### 去重与容错

- SQLite 存储 `processed_txs` 和 `last_block`，确保同一交易不重复推送
- 首次运行从最新区块开始，避免推送大量历史交易
- 单地址查询失败不影响其他地址
- `get_latest_block` 失败时跳过本轮，不会退出
- Etherscan API 调用内置 250ms 限速，避免触发免费 Key 速率限制（5 req/s）
- SQLite 写入使用 `BatchWriter` 批量提交，减少连接开销

## 自定义配置

### 添加监控地址

编辑 `whales.json`：

```json
{
    "0x...": "地址备注名"
}
```

### 添加 DeFi 合约

编辑 `defi_contracts.json`：

```json
{
    "0x...": {
        "name": "协议名称",
        "type": "DEX"
    }
}
```

### 添加交易所地址

编辑 `exchange_addresses.json`：

```json
{
    "addresses": ["0x..."]
}
```

交易所地址会在推送消息中标注 `[Exchange]`。

## 常见问题

**Q: 程序启动后没有收到 Telegram 消息？**
A: 检查 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 是否正确。确认 Bot 已被添加到目标群组/频道。

**Q: Etherscan API 返回错误？**
A: 检查 `ETHERSCAN_API_KEY` 是否有效。免费 Key 每秒最多 5 次请求，程序已内置限速。

**Q: 如何获取 Telegram Chat ID？**
A: 将 Bot 添加到群组，发送一条消息，然后访问 `https://api.telegram.org/bot<TOKEN>/getUpdates` 查看 `chat.id`。

**Q: Railway 部署后数据会丢失吗？**
A: 配置 Volume 挂载到 `/app/data` 后，SQLite 数据会持久化。未配置 Volume 时数据会在重启后丢失，可能导致重复推送。

**Q: 如何监控多条链？**
A: 部署多个 Railway 服务，每个服务使用不同的 `CHAIN_ID`。

**Q: 首次启动会推送历史交易吗？**
A: 不会。首次启动时程序自动获取当前最新区块号作为起点，只监控新产生的交易。

**Q: 日志中会出现 API Key 吗？**
A: 不会。日志中 API Key 和 Bot Token 均被遮掩为 `ABCD...WXYZ` 格式。

## 验收 Checklist

- [ ] 本地 `python main.py` 能正常启动
- [ ] 缺少必填环境变量时报错并退出
- [ ] Telegram 收到启动通知（含 Chain ID 和浏览器地址）
- [ ] 首次运行从最新区块开始，不推送历史交易
- [ ] `NATIVE_THRESHOLD=0` 测试，普通交易能触发推送
- [ ] `ERC20_THRESHOLD=0` 测试，ERC20 转账能触发推送
- [ ] `whales.json` 中的地址与 DeFi 合约交互时能触发推送
- [ ] 推送消息包含可点击的区块浏览器链接
- [ ] 交易所地址标注 `[Exchange]`
- [ ] 同一笔交易不会重复推送
- [ ] 单个地址查询失败不影响其他地址
- [ ] `get_latest_block` 失败时跳过本轮不退出
- [ ] 日志中不包含完整 API Key 或 Bot Token
- [ ] `.env` 文件未被提交到 Git
- [ ] Railway 部署成功，Volume 持久化正常
