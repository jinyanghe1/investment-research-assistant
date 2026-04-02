#!/usr/bin/env python3
"""
期货数据获取脚本

获取国内期货主连合约和国际期货数据
支持：铜、铝、原油、黄金、农产品等

Usage:
    python fetch_futures.py --symbol CU --exchange SHFE --start_date 20240101 --end_date 20260402
    python fetch_futures.py --symbol CL --exchange CME --output data/raw/

Example:
    python fetch_futures.py --symbol CU --exchange SHFE --start_date 20240101 --end_date 20260402
    python fetch_futures.py --symbol SC --exchange INE --output data/raw/
    python fetch_futures.py --symbol GC --exchange CME --output data/raw/
    python fetch_futures.py --symbol A --exchange DCE --output data/raw/
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# 期货品种代码映射
FUTURES_CODES = {
    # 国内期货 - 上海期货交易所 (SHFE)
    'CU': {'name': '铜', 'exchange': 'SHFE'},
    'AL': {'name': '铝', 'exchange': 'SHFE'},
    'ZN': {'name': '锌', 'exchange': 'SHFE'},
    'PB': {'name': '铅', 'exchange': 'SHFE'},
    'NI': {'name': '镍', 'exchange': 'SHFE'},
    'SN': {'name': '锡', 'exchange': 'SHFE'},
    'AU': {'name': '黄金', 'exchange': 'SHFE'},
    'AG': {'name': '白银', 'exchange': 'SHFE'},
    'RB': {'name': '螺纹钢', 'exchange': 'SHFE'},
    'HC': {'name': '热卷', 'exchange': 'SHFE'},
    'RU': {'name': '橡胶', 'exchange': 'SHFE'},
    'FU': {'name': '燃油', 'exchange': 'SHFE'},
    'BU': {'name': '沥青', 'exchange': 'SHFE'},
    'SPB': {'name': '热卷', 'exchange': 'SHFE'},

    # 国内期货 - 大连商品交易所 (DCE)
    'I': {'name': '铁矿石', 'exchange': 'DCE'},
    'J': {'name': '焦炭', 'exchange': 'DCE'},
    'JM': {'name': '焦煤', 'exchange': 'DCE'},
    'M': {'name': '豆粕', 'exchange': 'DCE'},
    'Y': {'name': '豆油', 'exchange': 'DCE'},
    'A': {'name': '大豆', 'exchange': 'DCE'},
    'B': {'name': '豆一', 'exchange': 'DCE'},
    'L': {'name': '塑料', 'exchange': 'DCE'},
    'PP': {'name': '聚丙烯', 'exchange': 'DCE'},
    'V': {'name': 'PVC', 'exchange': 'DCE'},
    'C': {'name': '玉米', 'exchange': 'DCE'},
    'CS': {'name': '淀粉', 'exchange': 'DCE'},
    'EG': {'name': '乙二醇', 'exchange': 'DCE'},
    'EB': {'name': '苯乙烯', 'exchange': 'DCE'},

    # 国内期货 - 郑州商品交易所 (CZCE)
    'CF': {'name': '棉花', 'exchange': 'CZCE'},
    'SR': {'name': '白糖', 'exchange': 'CZCE'},
    'RI': {'name': '早籼稻', 'exchange': 'CZCE'},
    'WH': {'name': '强麦', 'exchange': 'CZCE'},
    'PM': {'name': '普麦', 'exchange': 'CZCE'},
    'OI': {'name': '菜油', 'exchange': 'CZCE'},
    'RM': {'name': '菜粕', 'exchange': 'CZCE'},
    'RS': {'name': '菜籽', 'exchange': 'CZCE'},
    'TA': {'name': 'PTA', 'exchange': 'CZCE'},
    'ME': {'name': '甲醇', 'exchange': 'CZCE'},
    'FG': {'name': '玻璃', 'exchange': 'CZCE'},
    'ZC': {'name': '动力煤', 'exchange': 'CZCE'},
    'JR': {'name': '粳稻', 'exchange': 'CZCE'},
    'LR': {'name': '晚籼稻', 'exchange': 'CZCE'},
    'SF': {'name': '硅铁', 'exchange': 'CZCE'},
    'SM': {'name': '锰硅', 'exchange': 'CZCE'},

    # 国内期货 - 上海国际能源交易中心 (INE)
    'SC': {'name': '原油', 'exchange': 'INE'},
    'NR': {'name': '20号胶', 'exchange': 'INE'},
    'LU': {'name': '低硫燃料油', 'exchange': 'INE'},

    # 国际期货 - CME (芝加哥商品交易所)
    'CL': {'name': 'WTI原油', 'exchange': 'CME'},
    'GC': {'name': '黄金', 'exchange': 'CME'},
    'SI': {'name': '白银', 'exchange': 'CME'},
    'HG': {'name': '铜', 'exchange': 'CME'},
    'NG': {'name': '天然气', 'exchange': 'CME'},
    'ZS': {'name': '大豆', 'exchange': 'CME'},
    'ZC_C': {'name': '玉米', 'exchange': 'CME'},  # 避免与CZCE的ZC冲突
    'ZW': {'name': '小麦', 'exchange': 'CME'},

    # 国际期货 - ICE (洲际交易所)
    'BRENT': {'name': '布伦特原油', 'exchange': 'ICE'},
}


def setup_args():
    parser = argparse.ArgumentParser(
        description='获取国内外期货数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fetch_futures.py --symbol CU --exchange SHFE --start_date 20240101 --end_date 20260402
  python fetch_futures.py --symbol SC --exchange INE --output data/raw/
  python fetch_futures.py --symbol GC --exchange CME --output data/raw/
  python fetch_futures.py --symbol CL --exchange CME --output data/raw/

支持的品种代码: CU(铜), AL(铝), AU(黄金), AG(白银), RB(螺纹钢),
               SC(原油), I(铁矿石), M(豆粕), CF(棉花), SR(白糖)
        """
    )
    parser.add_argument('--symbol', '-s', required=True,
                        help='期货品种代码，如 CU, AL, AU, SC, CL, GC')
    parser.add_argument('--exchange', '-e', required=True,
                        choices=['SHFE', 'DCE', 'CZCE', 'INE', 'CME', 'ICE'],
                        help='交易所代码')
    parser.add_argument('--start_date', '-d', default='20200101',
                        help='开始日期 YYYYMMDD')
    parser.add_argument('--end_date', '-f', default=None,
                        help='结束日期 YYYYMMDD')
    parser.add_argument('--output', '-o', default='data/raw',
                        help='输出目录')
    return parser.parse_args()


def get_futures_data(symbol: str, exchange: str, start_date: str = None, end_date: str = None) -> dict:
    """
    获取期货数据

    Parameters:
        symbol: 品种代码
        exchange: 交易所代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        dict: 包含 data 和 info
    """
    try:
        import akshare as ak
    except ImportError:
        print("[ERROR] 请先安装 akshare: pip install akshare")
        sys.exit(1)

    result = {'data': None, 'symbol': symbol, 'exchange': exchange}
    info = FUTURES_CODES.get(symbol, {'name': symbol, 'exchange': exchange})
    result['name'] = info['name']

    try:
        if exchange in ['SHFE', 'DCE', 'CZCE', 'INE']:
            # 国内期货
            if symbol == 'SC':
                # 原油（INE）
                result['data'] = ak.futures_zh_main_sina(symbol=symbol)
            elif symbol in ['CU', 'AL', 'ZN', 'PB', 'NI', 'SN', 'AU', 'AG', 'RB', 'HC', 'RU', 'FU', 'BU']:
                # SHFE
                result['data'] = ak.futures_zh_main_sina(symbol=symbol)
            elif symbol in ['I', 'J', 'JM', 'M', 'Y', 'A', 'B', 'L', 'PP', 'V', 'C', 'CS', 'EG', 'EB']:
                # DCE
                result['data'] = ak.futures_zh_main_sina(symbol=symbol)
            elif symbol in ['CF', 'SR', 'RI', 'WH', 'PM', 'OI', 'RM', 'RS', 'TA', 'ME', 'FG', 'ZC', 'JR', 'LR', 'SF', 'SM']:
                # CZCE
                result['data'] = ak.futures_zh_main_sina(symbol=symbol)
            elif symbol == 'NR' or symbol == 'LU':
                # INE
                result['data'] = ak.futures_zh_main_sina(symbol=symbol)
            else:
                result['data'] = ak.futures_zh_main_sina(symbol=symbol)

        elif exchange in ['CME', 'ICE']:
            # 国际期货
            if symbol == 'CL':
                result['data'] = ak.futures_global_west_crude_oil()
            elif symbol == 'GC':
                result['data'] = ak.futures_global_gold()
            elif symbol == 'SI':
                result['data'] = ak.futures_global_silver()
            elif symbol == 'HG':
                result['data'] = ak.futures_global_copper()
            elif symbol == 'NG':
                result['data'] = ak.futures_global_natural_gas()
            elif symbol == 'ZS':
                result['data'] = ak.futures_global_soybean()
            else:
                print(f"[WARN] 暂不支持的品种: {symbol}, 将尝试通用接口")
                result['data'] = ak.futures_zh_main_sina(symbol=symbol)

        print(f"[OK] 获取 {symbol}({info['name']}) {exchange} 数据成功")
        return result

    except Exception as e:
        print(f"[ERROR] 获取 {symbol} {exchange} 数据失败: {e}")
        return result


def save_to_csv(data, symbol: str, exchange: str, output_dir: str) -> str:
    """保存期货数据到CSV"""
    if data is None or data.empty:
        print(f"[WARN] 数据为空，跳过保存")
        return None

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d')
    filename = f"{timestamp}_{exchange}_{symbol}_futures.csv"
    filepath = os.path.join(output_dir, filename)

    try:
        data.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"[OK] 数据已保存: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] 保存数据失败: {e}")
        return None


def main():
    args = setup_args()

    if args.end_date is None:
        args.end_date = datetime.now().strftime('%Y%m%d')

    print(f"[INFO] 获取期货数据: {args.symbol} ({args.exchange})")
    print(f"[INFO] 时间范围: {args.start_date} ~ {args.end_date}")

    result = get_futures_data(args.symbol, args.exchange, args.start_date, args.end_date)

    if result['data'] is not None:
        filepath = save_to_csv(result['data'], args.symbol, args.exchange, args.output)
        if filepath:
            print(f"[INFO] 完成!")
            return 0

    print("[WARN] 未获取到数据")
    return 1


if __name__ == '__main__':
    sys.exit(main())
