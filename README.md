# whale-radar

巨鲸异动雷达 — 监控链上地址，大额转账 / DeFi 交互 / 交易所充提，通过 Telegram 推送。

## 项目结构

```
whale-radar/
├── src/                  # Python 源码
│   ├── main.py
│   ├── config.py
│   ├── etherscan_client.py
│   ├── telegram_client.py
│   ├── rules.py
│   └── storage.py
├── data/                 # JSON 配置
│   ├── whales.json
│   ├── defi_contracts.json
│   ├── exchange_addresses.json
│   └── token_thresholds.json
├── scripts/              # 辅助脚本
│   └── update_whales.py
├── Procfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 快速开始

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # 填入真实值
python src/main.py --show-config
python src/main.py --test-telegram
python src/main.py
```

程序自动读取 `.env`，无需手动 export 或安装 python-dotenv。

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--show-config` | 打印遮蔽后的配置并退出 |
| `--test-telegram` | 发送测试消息并退出 |
| `--dry-run-once` | 轮询一轮打印告警，不发送 Telegram |

## 环境变量

必填：

| 变量 | 说明 |
|------|------|
| `ETHERSCAN_API_KEY` | Etherscan API Key |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |

可选（自动匹配主流链）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHAIN_ID` | `1` | 链 ID |
| `CHAIN_NAME` | 自动 | 链名称 |
| `NATIVE_SYMBOL` | 自动 | ETH / BNB / MATIC 等 |
| `NATIVE_DECIMALS` | `18` | Native 精度 |
| `EXPLORER_BASE` | 自动 | 区块浏览器 URL |
| `POLL_INTERVAL` | `60` | 轮询间隔（秒） |
| `NATIVE_THRESHOLD` | `10` | Native 大额阈值 |
| `ERC20_THRESHOLD` | `100000` | ERC20 默认阈值 |
| `DATA_DIR` | `.` | SQLite 目录 |
| `DRY_RUN` | `false` | 只打印不发送 Telegram |

自动匹配：Ethereum / BSC / Polygon / Arbitrum / Optimism / Avalanche / Base。

## Railway 部署

1. 创建项目，关联 `HNUDAO/whale-radar`
2. Service Type 选 **Worker**（Procfile 已配 `worker: python src/main.py`）
3. Variables 添加 3 个必填 + `DATA_DIR=/app/data`
4. Volume 挂载到 `/app/data`

## 告警类型

| 类型 | 条件 |
|------|------|
| Native Transfer | 金额 >= `NATIVE_THRESHOLD` |
| ERC20 Transfer | 金额 >= token 阈值 |
| DeFi Interaction | 目标在 `defi_contracts.json` 中 |
| Exchange Deposit | whale → 交易所，金额 >= `NATIVE_THRESHOLD` |
| Exchange Withdrawal | 交易所 → whale，金额 >= `NATIVE_THRESHOLD` |

各类告警独立 tx_key 去重，同一笔交易可同时触发多种告警。

## 配置文件

`data/` 目录下：

| 文件 | 说明 |
|------|------|
| `whales.json` | 监控地址（手动维护，不放高频热钱包） |
| `exchange_addresses.json` | 交易所地址（`{addr: {name, type}}`，兼容 `{addresses: [...]}`） |
| `defi_contracts.json` | DeFi 合约（支持按 chain_id 分组） |
| `token_thresholds.json` | 按 token 设置阈值（如 `USDT: 100000`），覆盖全局 `ERC20_THRESHOLD` |

## 容错机制

- 首次运行从最新区块开始，不推送历史交易
- 单地址查询失败不影响其他地址
- 查询失败时不推进 last_block
- Etherscan API 内置 250ms 限速 + 分页（100 条/页，最多 20 页）
- `DRY_RUN=true` 时只打印不发送

## 可选脚本

```bash
ETHERSCAN_API_KEY=xxx python scripts/update_whales.py
```

获取 top ETH holders（需 Etherscan PRO 权限）。权限不足时会提示，不影响主程序。
