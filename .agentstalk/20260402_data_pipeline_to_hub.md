# Agent通信文件

## Task Status
- 状态：COMPLETED
- 优先级：P1
- 关联任务ID：TASK-2026-DATA-001
- 发送方：data-pipeline-agent
- 接收方：hub

## Payload

本次任务已完成以下数据获取脚本的创建：

### 新增文件清单

| 序号 | 文件路径 | 说明 |
|------|----------|------|
| 1 | `scripts/data-pipeline/fetch_macro_data.py` | 宏观数据获取脚本，支持GDP/CPI/PPI/PMI/M2/社会融资等指标，使用AKShare国家统计局接口 |
| 2 | `scripts/data-pipeline/fetch_stock_daily.py` | A股个股/指数日线数据获取脚本，支持沪深A股、指数（沪深300、上证50等），使用东方财富接口 |
| 3 | `scripts/data-pipeline/fetch_futures.py` | 期货数据获取脚本，支持国内期货主连（铜CU/铝AL/原油SC等）和国际期货（WTI原油CL/黄金GC/白银SI） |
| 4 | `scripts/data-pipeline/data/raw/` | 原始数据输出目录（自动创建） |

### 脚本功能说明

#### fetch_macro_data.py
- **支持指标**：GDP、CPI、PPI、PMI、M2、社会融资规模
- **数据来源**：国家统计局、中国人民银行（通过AKShare）
- **命令行参数**：
  - `--indicator` / `-i`：指标类型（必需）
  - `--region` / `-r`：地区代码，默认CN
  - `--start_date` / `-s`：开始日期
  - `--end_date` / `-e`：结束日期
  - `--output` / `-o`：输出目录，默认data/raw
- **示例**：
  ```bash
  python fetch_macro_data.py --indicator GDP --region CN --output data/raw/
  python fetch_macro_data.py --indicator CPI --region CN --start_date 202401 --end_date 202603
  ```

#### fetch_stock_daily.py
- **支持品种**：沪深A股个股、主流指数
- **数据来源**：东方财富（通过AKShare）
- **命令行参数**：
  - `--ts_code` / `-t`：股票/指数代码（必需），如 000001.SZ、600519.SH、000300.SH
  - `--start_date` / `-s`：开始日期，默认20200101
  - `--end_date` / `-e`：结束日期，默认今天
  - `--period` / `-p`：K线周期，daily/weekly/monthly
  - `--output` / `-o`：输出目录，默认data/raw
- **示例**：
  ```bash
  python fetch_stock_daily.py --ts_code 000001.SZ --start_date 20240101 --end_date 20260402
  python fetch_stock_daily.py --ts_code 000300.SH --period weekly --output data/raw/
  ```

#### fetch_futures.py
- **支持品种**：
  - 国内期货：CU(铜)、AL(铝)、AU(黄金)、AG(白银)、RB(螺纹钢)、SC(原油)、I(铁矿石)、M(豆粕)、CF(棉花)、SR(白糖)等
  - 国际期货：CL(WTI原油)、GC(黄金)、SI(白银)、HG(铜)、NG(天然气)
- **数据来源**：新浪财经、国内期货交易所（通过AKShare）
- **命令行参数**：
  - `--symbol` / `-s`：期货品种代码（必需）
  - `--exchange` / `-e`：交易所代码（必需），SHFE/DCE/CZCE/INE/CME/ICE
  - `--start_date` / `-d`：开始日期，默认20200101
  - `--end_date` / `-f`：结束日期
  - `--output` / `-o`：输出目录，默认data/raw
- **示例**：
  ```bash
  python fetch_futures.py --symbol CU --exchange SHFE --start_date 20240101 --end_date 20260402
  python fetch_futures.py --symbol GC --exchange CME --output data/raw/
  python fetch_futures.py --symbol CL --exchange CME --output data/raw/
  ```

### 技术规范

- 所有脚本支持 `--help` 参数查看完整帮助信息
- 所有脚本包含中文注释和示例说明
- 错误处理：网络错误、数据为空等异常情况均有处理
- 输出目录 `data/raw/` 会自动创建（如不存在）
- 数据输出格式：CSV（UTF-8-sig编码，Excel友好）

## Next Action

1. **数据使用Agent**：可调用上述脚本获取原始数据，输出目录为 `scripts/data-pipeline/data/raw/`
2. **数据清洗Agent**：可基于获取的CSV数据做进一步清洗和格式化
3. **分析Agent**：可将清洗后的数据用于后续的宏观分析、基本面分析等任务

## Notes

- 运行脚本前需安装依赖：`pip install akshare pandas`
- 部分接口可能因网络问题需要重试
- 国际期货数据（如CME系列）可能需要稳定的网络连接
- 数据时间范围建议不超过5年，避免接口超时
