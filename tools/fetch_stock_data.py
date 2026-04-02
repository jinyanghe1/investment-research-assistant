#!/usr/bin/env python3
"""
A股个股数据获取脚本（强制yfinance数据源）

本脚本强制使用yfinance作为唯一数据源，避免使用网上搜索的过时数据。
包含完整的数据验证机制。

Usage:
    python fetch_stock_data.py --ts-code 000988.SZ
    python fetch_stock_data.py --ts-code 000988.SZ --output data/
    python fetch_stock_data.py --ts-code 000988.SZ --verify

Example:
    python fetch_stock_data.py --ts-code 000988.SZ --verify --verbose
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.data_validator import DataValidator, validate_stock_data


def get_stock_price_from_yfinance(ts_code: str) -> Dict:
    """
    从yfinance获取股价数据（强制数据源）
    
    Args:
        ts_code: 股票代码，如 '000988.SZ'
        
    Returns:
        包含股价数据的字典
    """
    import yfinance as yf
    
    ticker = yf.Ticker(ts_code)
    info = ticker.info
    
    # 获取当前股价（优先使用currentPrice，否则使用regularMarketPrice）
    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
    
    if current_price is None:
        # 尝试从历史数据获取最新价格
        hist = ticker.history(period='5d')
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
    
    # 获取总股本
    total_shares = info.get('sharesOutstanding') or info.get('impliedSharesOutstanding')
    
    # 计算市值（如果info中没有）
    # 注意: yfinance的marketCap和current_price均以股票交易币种计价
    market_cap = info.get('marketCap')
    if market_cap is None and current_price and total_shares:
        market_cap = current_price * total_shares
    
    # 转换市值为"亿"（币种与股票交易货币一致）
    currency = info.get('currency', 'CNY')
    market_cap_yi = market_cap / 1e8 if market_cap else None
    market_cap_unit = f'亿{currency}'
    
    result = {
        'ts_code': ts_code,
        'current_price': current_price,
        'currency': currency,
        'market_cap': market_cap_yi,
        'market_cap_unit': market_cap_unit,
        'total_shares': total_shares,
        'pe_ttm': info.get('trailingPE'),
        'pb': info.get('priceToBook'),
        'dividend_yield': info.get('dividendYield'),
        'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
        'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
        'company_name': info.get('longName') or info.get('shortName'),
        'sector': info.get('sector'),
        'industry': info.get('industry'),
        'fetch_time': datetime.now().isoformat(),
        'data_source': 'yfinance'
    }
    
    return result


def get_financial_data_from_yfinance(ts_code: str) -> Dict:
    """
    从yfinance获取财务数据
    
    Args:
        ts_code: 股票代码
        
    Returns:
        包含财务数据的字典
    """
    import yfinance as yf
    
    ticker = yf.Ticker(ts_code)
    
    # 获取年度财务数据
    try:
        financials = ticker.financials
        annual_revenue = None
        annual_profit = None
        
        if not financials.empty:
            # 获取最新年度数据
            latest_col = financials.columns[0]
            if 'Total Revenue' in financials.index:
                annual_revenue = financials.loc['Total Revenue', latest_col] / 1e8  # 转为亿元
            if 'Net Income' in financials.index:
                annual_profit = financials.loc['Net Income', latest_col] / 1e8
    except Exception as e:
        annual_revenue = None
        annual_profit = None
    
    # 获取季度财务数据
    try:
        quarterly = ticker.quarterly_financials
        quarterly_revenue = None
        quarterly_profit = None
        latest_quarter_date = None
        
        if not quarterly.empty:
            latest_col = quarterly.columns[0]
            latest_quarter_date = latest_col.strftime('%Y-%m-%d') if hasattr(latest_col, 'strftime') else str(latest_col)
            
            if 'Total Revenue' in quarterly.index:
                quarterly_revenue = quarterly.loc['Total Revenue', latest_col] / 1e8
            if 'Net Income' in quarterly.index:
                quarterly_profit = quarterly.loc['Net Income', latest_col] / 1e8
    except Exception as e:
        quarterly_revenue = None
        quarterly_profit = None
        latest_quarter_date = None
    
    # 获取资产负债表
    try:
        balance = ticker.balance_sheet
        total_assets = None
        total_equity = None
        
        if not balance.empty:
            latest_col = balance.columns[0]
            if 'Total Assets' in balance.index:
                total_assets = balance.loc['Total Assets', latest_col] / 1e8
            if 'Stockholders Equity' in balance.index:
                total_equity = balance.loc['Stockholders Equity', latest_col] / 1e8
    except Exception as e:
        total_assets = None
        total_equity = None
    
    result = {
        'ts_code': ts_code,
        'total_revenue': annual_revenue,
        'net_profit': annual_profit,
        'quarterly_revenue': quarterly_revenue,
        'quarterly_profit': quarterly_profit,
        'total_assets': total_assets,
        'total_equity': total_equity,
        'report_date': latest_quarter_date,
        'fetch_time': datetime.now().isoformat(),
        'data_source': 'yfinance'
    }
    
    return result


def check_annual_report_status(financial_data: Dict) -> Dict:
    """
    检查财报数据是实际发布还是预测值

    Args:
        financial_data: get_financial_data_from_yfinance 返回的财务数据字典

    Returns:
        包含报告状态信息的字典:
        - is_actual: 是否为实际发布数据
        - data_status: 'actual' | 'estimate' | 'unknown'
        - report_freshness: 'fresh' | 'stale' | 'unknown'
        - days_since_report: 距离报告日期的天数
        - warning: 警告信息（如有）
    """
    result = {
        'is_actual': True,  # 默认假设为真实数据
        'data_status': 'unknown',
        'report_freshness': 'unknown',
        'days_since_report': None,
        'warning': None
    }

    report_date = financial_data.get('report_date')
    if not report_date:
        result['warning'] = '未提供财报日期，无法判断数据性质'
        result['data_status'] = 'unknown'
        return result

    # 计算天数差
    try:
        if isinstance(report_date, str):
            report_dt = datetime.strptime(report_date, '%Y-%m-%d')
        else:
            report_dt = report_date
        days_diff = (datetime.now() - report_dt).days
        result['days_since_report'] = days_diff
    except Exception:
        result['warning'] = f'财报日期解析失败: {report_date}'
        return result

    # 判断数据新鲜度
    if days_diff <= 90:
        result['report_freshness'] = 'fresh'
        result['data_status'] = 'actual'
        result['is_actual'] = True
    elif days_diff <= 180:
        result['report_freshness'] = 'stale'
        result['warning'] = f'财报数据已{days_diff}天，可能为历史数据或预测值'
        result['data_status'] = 'estimate'
        result['is_actual'] = False
    else:
        result['report_freshness'] = 'very_stale'
        result['warning'] = f'财报数据超过{days_diff}天，极可能为预测值，请获取最新财报'
        result['data_status'] = 'estimate'
        result['is_actual'] = False

    return result


def fetch_complete_stock_data(ts_code: str, verify: bool = True) -> Tuple[Dict, bool, list]:
    """
    获取完整的股票数据（股价+财务）
    
    Args:
        ts_code: 股票代码
        verify: 是否进行数据验证
        
    Returns:
        (数据字典, 是否验证通过, 错误信息列表)
    """
    print(f"[INFO] 正在获取 {ts_code} 数据...")
    
    # 1. 获取股价数据
    try:
        price_data = get_stock_price_from_yfinance(ts_code)
        market_cap = price_data.get('market_cap')
        print(f"[INFO] 股价数据: {price_data.get('current_price')}元, "
              f"市值: {f'{market_cap:.2f}' if market_cap else 'N/A'}亿元")
    except Exception as e:
        return {}, False, [f"获取股价数据失败: {e}"]
    
    # 2. 获取财务数据
    try:
        financial_data = get_financial_data_from_yfinance(ts_code)
        total_rev = financial_data.get('total_revenue')
        net_prof = financial_data.get('net_profit')
        print(f"[INFO] 财务数据: 营收{f'{total_rev:.2f}' if total_rev else 'N/A'}亿元, "
              f"净利润{f'{net_prof:.2f}' if net_prof else 'N/A'}亿元")

        # 2.1 检查财报状态（实际 vs 预测）
        report_status = check_annual_report_status(financial_data)
        financial_data['report_status'] = report_status
        if report_status.get('warning'):
            print(f"[WARN] {report_status['warning']}")
        elif report_status.get('is_actual'):
            print(f"[INFO] 财报状态: 实际发布数据 (报告日期: {financial_data.get('report_date')})")
        else:
            print(f"[WARN] 财报状态: 可能为预测值")
    except Exception as e:
        print(f"[WARN] 获取财务数据失败: {e}")
        financial_data = {}
    
    # 3. 合并数据
    result = {
        'ts_code': ts_code,
        'price': price_data,
        'financial': financial_data,
        'fetch_time': datetime.now().isoformat(),
        'data_source': 'yfinance'
    }
    
    # 4. 数据验证
    if verify:
        validator = DataValidator()
        
        # 验证股价数据
        is_price_valid, price_errors = validator.validate_stock_price(price_data)
        
        # 验证财务数据（如果有）
        if financial_data.get('total_revenue'):
            is_fin_valid, fin_errors = validator.validate_financial_data(financial_data)
        else:
            is_fin_valid, fin_errors = True, []
        
        all_errors = price_errors + fin_errors
        is_valid = is_price_valid and is_fin_valid
        
        if not is_valid:
            print(f"[ERROR] 数据验证失败:")
            for error in all_errors:
                print(f"  - {error}")
        elif all_errors:
            print(f"[WARN] 数据警告:")
            for warning in all_errors:
                print(f"  - {warning}")
        else:
            print(f"[OK] 数据验证通过")
        
        return result, is_valid, all_errors
    
    return result, True, []


def save_to_json(data: Dict, output_dir: str, ts_code: str) -> str:
    """保存数据到JSON文件"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 清理股票代码作为文件名
    safe_code = ts_code.replace('.', '_')
    filename = f"{safe_code}_{datetime.now().strftime('%Y%m%d')}.json"
    filepath = output_path / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(filepath)


def main():
    parser = argparse.ArgumentParser(
        description='A股个股数据获取脚本（强制yfinance数据源）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python fetch_stock_data.py --ts-code 000988.SZ
    python fetch_stock_data.py --ts-code 000988.SZ --output data/ --verify
    python fetch_stock_data.py --ts-code 000988.SZ --compare 300308.SZ
        """
    )
    
    parser.add_argument('--ts-code', '-t', required=True,
                        help='股票代码，如 000988.SZ')
    parser.add_argument('--output', '-o', default='data/raw',
                        help='输出目录')
    parser.add_argument('--verify', '-v', action='store_true',
                        help='启用数据验证')
    parser.add_argument('--strict', action='store_true',
                        help='严格模式（警告视为错误）')
    parser.add_argument('--compare', '-c', nargs='+',
                        help='对比股票代码，如 300308.SZ')
    parser.add_argument('--verbose', action='store_true',
                        help='详细输出')
    
    args = parser.parse_args()
    
    # 获取主股票数据
    data, is_valid, errors = fetch_complete_stock_data(args.ts_code, verify=args.verify)
    
    if not is_valid:
        print(f"\n[ERROR] 数据获取失败，请检查股票代码或数据源")
        return 1
    
    # 获取对比股票数据
    if args.compare:
        comparison_data = {args.ts_code: data['price']}
        for code in args.compare:
            try:
                comp_data, comp_valid, _ = fetch_complete_stock_data(code, verify=False)
                if comp_valid:
                    comparison_data[code] = comp_data['price']
            except Exception as e:
                print(f"[WARN] 获取对比股票{code}失败: {e}")
        
        # 验证对比数据
        if len(comparison_data) > 1:
            validator = DataValidator()
            is_comp_valid, comp_errors = validator.validate_comparison_data(
                comparison_data, list(comparison_data.keys())
            )
            if comp_errors:
                print(f"[WARN] 对比数据警告: {comp_errors}")
    
    # 保存数据
    output_file = save_to_json(data, args.output, args.ts_code)
    print(f"\n[OK] 数据已保存: {output_file}")
    
    # 详细输出
    if args.verbose:
        print("\n详细数据:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
