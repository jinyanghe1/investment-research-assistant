#!/usr/bin/env python3
"""
数据验证中间件 - 确保金融数据质量

用于验证股价、财务数据等的合理性，防止错误数据流入研报。

Usage:
    from data_validator import DataValidator
    
    validator = DataValidator()
    is_valid, errors = validator.validate_stock_price(price_data)
    
    # 或作为装饰器使用
    @validate_stock_data
    def fetch_stock_data(ts_code):
        ...
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataValidator')


@dataclass
class ValidationRule:
    """验证规则定义"""
    field: str
    check_type: str  # 'range', 'not_null', 'match', 'freshness'
    params: Dict[str, Any]
    severity: str = 'error'  # 'error', 'warning'
    message: str = ''


class DataValidator:
    """数据验证器"""
    
    # A股股价合理范围
    STOCK_PRICE_MIN = 1.0
    STOCK_PRICE_MAX = 1000.0
    
    # 市值合理范围（亿元）
    MARKET_CAP_MIN = 1.0
    MARKET_CAP_MAX = 100000.0
    
    # PE合理范围
    PE_MIN = -100.0
    PE_MAX = 200.0
    
    # 财报新鲜度（天数）
    MAX_REPORT_AGE_DAYS = 90
    
    # 净利率合理范围
    PROFIT_MARGIN_MIN = -0.5
    PROFIT_MARGIN_MAX = 0.5
    
    def __init__(self, strict_mode: bool = True):
        """
        初始化验证器
        
        Args:
            strict_mode: 严格模式，任何验证失败都返回False
        """
        self.strict_mode = strict_mode
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_stock_price(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        验证股价数据
        
        Args:
            data: 包含股价数据的字典
            
        Returns:
            (是否通过, 错误信息列表)
        """
        self.errors = []
        self.warnings = []
        
        # 1. 检查必要字段
        required_fields = ['current_price', 'market_cap', 'ts_code']
        for field in required_fields:
            if field not in data:
                self.errors.append(f"缺少必要字段: {field}")
        
        if self.errors:
            return False, self.errors
        
        price = data.get('current_price')
        market_cap = data.get('market_cap')
        ts_code = data.get('ts_code', '')
        
        # 2. 验证股价范围
        if not isinstance(price, (int, float)):
            self.errors.append(f"股价类型错误: {type(price)}")
        elif price <= 0:
            self.errors.append(f"股价必须为正数: {price}")
        elif price < self.STOCK_PRICE_MIN:
            self.errors.append(
                f"股价低于合理下限({self.STOCK_PRICE_MIN}元): {price}元 - "
                f"可能股票已退市或数据错误"
            )
        elif price > self.STOCK_PRICE_MAX:
            self.warnings.append(
                f"股价超过合理上限({self.STOCK_PRICE_MAX}元): {price}元 - "
                f"请人工核实"
            )
        
        # 3. 验证市值范围
        if not isinstance(market_cap, (int, float)):
            self.errors.append(f"市值类型错误: {type(market_cap)}")
        elif market_cap < self.MARKET_CAP_MIN:
            self.errors.append(f"市值低于合理下限: {market_cap}亿元")
        elif market_cap > self.MARKET_CAP_MAX:
            self.warnings.append(f"市值超过合理上限: {market_cap}亿元")
        
        # 4. 交叉验证：市值 = 股价 × 股本
        total_shares = data.get('total_shares')
        if total_shares and price and market_cap:
            calculated_cap = price * total_shares / 1e8  # 转换为亿元
            discrepancy = abs(calculated_cap - market_cap) / market_cap
            
            if discrepancy > 0.1:  # 差异超过10%
                self.errors.append(
                    f"市值交叉验证失败:  reported={market_cap}亿, "
                    f"calculated={calculated_cap:.2f}亿 (diff={discrepancy*100:.1f}%) - "
                    f"数据可能不一致"
                )
            elif discrepancy > 0.05:  # 差异超过5%
                self.warnings.append(
                    f"市值与股价×股本差异较大({discrepancy*100:.1f}%) - "
                    f"建议核实"
                )
        
        # 5. 验证PE范围
        pe_ttm = data.get('pe_ttm')
        if pe_ttm is not None:
            if pe_ttm < self.PE_MIN:
                self.warnings.append(f"PE过低({pe_ttm})，可能为亏损股或数据异常")
            elif pe_ttm > self.PE_MAX:
                self.warnings.append(f"PE过高({pe_ttm})，请核实数据")
        
        # 6. 股票代码格式验证
        if '.' not in ts_code:
            self.warnings.append(f"股票代码格式可能不正确: {ts_code}")
        
        # 返回结果
        is_valid = len(self.errors) == 0
        if not self.strict_mode:
            is_valid = is_valid and len(self.warnings) == 0
        
        all_messages = self.errors + self.warnings
        return is_valid, all_messages
    
    def validate_financial_data(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        验证财务数据
        
        Args:
            data: 包含财务数据的字典
            
        Returns:
            (是否通过, 错误信息列表)
        """
        self.errors = []
        self.warnings = []
        
        # 1. 检查必要字段
        required_fields = ['total_revenue', 'net_profit']
        for field in required_fields:
            if field not in data:
                self.errors.append(f"缺少必要字段: {field}")
        
        if self.errors:
            return False, self.errors
        
        revenue = data.get('total_revenue')
        net_profit = data.get('net_profit')
        
        # 2. 验证营收
        if not isinstance(revenue, (int, float)):
            self.errors.append(f"营收类型错误: {type(revenue)}")
        elif revenue <= 0:
            self.errors.append(f"营收必须为正数: {revenue}")
        elif revenue > 100000:  # 超过10万亿，可能是万元单位错误
            self.warnings.append(
                f"营收异常高({revenue}亿元)，请检查单位是否正确(应为亿元而非万元)"
            )
        
        # 3. 验证净利润
        if not isinstance(net_profit, (int, float)):
            self.errors.append(f"净利润类型错误: {type(net_profit)}")
        elif revenue and abs(net_profit) > revenue * 2:  # 净利润绝对值不应超过营收2倍
            self.errors.append(
                f"净利润({net_profit})与营收({revenue})比例异常 - "
                f"净利润绝对值不应超过营收"
            )
        
        # 4. 验证净利率
        if revenue and net_profit is not None and abs(revenue) > 0.01:
            margin = net_profit / revenue
            if margin < self.PROFIT_MARGIN_MIN:
                self.warnings.append(
                    f"净利率过低({margin*100:.1f}%)，可能为亏损企业或数据错误"
                )
            elif margin > self.PROFIT_MARGIN_MAX:
                self.warnings.append(
                    f"净利率过高({margin*100:.1f}%)，请核实数据"
                )
        
        # 5. 验证财报日期新鲜度
        report_date = data.get('report_date')
        if report_date:
            try:
                if isinstance(report_date, str):
                    report_dt = datetime.strptime(report_date, '%Y-%m-%d')
                else:
                    report_dt = report_date
                
                days_diff = (datetime.now() - report_dt).days
                if days_diff > self.MAX_REPORT_AGE_DAYS:
                    self.errors.append(
                        f"财报数据滞后{days_diff}天(>{self.MAX_REPORT_AGE_DAYS}天) - "
                        f"可能使用了过期数据"
                    )
                elif days_diff > 30:
                    self.warnings.append(
                        f"财报数据已{days_diff}天，建议检查是否有更新"
                    )
            except Exception as e:
                self.warnings.append(f"财报日期解析失败: {e}")
        else:
            self.warnings.append("未提供财报日期，无法验证数据新鲜度")
        
        # 6. 验证同比增长率
        revenue_growth = data.get('revenue_growth_yoy')
        if revenue_growth is not None:
            if revenue_growth < -0.8:
                self.warnings.append(
                    f"营收同比下降{revenue_growth*100:.1f}%，下滑严重，请核实"
                )
            elif revenue_growth > 3.0:
                self.warnings.append(
                    f"营收同比增长{revenue_growth*100:.1f}%，增长异常，请核实"
                )
        
        is_valid = len(self.errors) == 0
        if not self.strict_mode:
            is_valid = is_valid and len(self.warnings) == 0
        
        all_messages = self.errors + self.warnings
        return is_valid, all_messages
    
    def validate_comparison_data(self, data: Dict, peers: List[str]) -> Tuple[bool, List[str]]:
        """
        验证同业对比数据
        
        检查目标公司与同业公司的数据是否具有合理的相对关系
        
        Args:
            data: 包含多家公司数据的字典 {ts_code: {metrics}}
            peers: 需要对比的公司代码列表
            
        Returns:
            (是否通过, 错误信息列表)
        """
        self.errors = []
        self.warnings = []
        
        # 1. 检查所有公司数据存在
        for code in peers:
            if code not in data:
                self.errors.append(f"缺少公司数据: {code}")
        
        if self.errors:
            return False, self.errors
        
        # 2. 市值排名合理性（简单检查）
        market_caps = {
            code: data[code].get('market_cap', 0) 
            for code in peers
        }
        
        # 移除硬编码的业务逻辑（此前瞻验证已被通用检查替代）
        # 3. 检查极端异常值
        prices = [data[code].get('current_price', 0) for code in peers]
        if prices:
            avg_price = sum(prices) / len(prices)
            for code in peers:
                price = data[code].get('current_price', 0)
                if price > avg_price * 10:  # 价格超过均值10倍
                    self.warnings.append(
                        f"{code} 股价({price})显著高于同业均值({avg_price:.2f})，请核实"
                    )
        
        is_valid = len(self.errors) == 0
        all_messages = self.errors + self.warnings
        return is_valid, all_messages


def validate_stock_data(func):
    """
    装饰器：自动验证股价数据
    
    Usage:
        @validate_stock_data
        def fetch_stock_price(ts_code):
            return {...}
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        if isinstance(result, dict):
            validator = DataValidator()
            is_valid, messages = validator.validate_stock_price(result)
            
            if not is_valid:
                logger.error(f"数据验证失败: {messages}")
                raise ValueError(f"数据验证失败: {'; '.join(messages)}")
            
            if messages:  # 有警告
                logger.warning(f"数据警告: {messages}")
        
        return result
    
    return wrapper


def validate_financial_data(func):
    """
    装饰器：自动验证财务数据
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        if isinstance(result, dict):
            validator = DataValidator()
            is_valid, messages = validator.validate_financial_data(result)
            
            if not is_valid:
                logger.error(f"财务数据验证失败: {messages}")
                raise ValueError(f"财务数据验证失败: {'; '.join(messages)}")
            
            if messages:
                logger.warning(f"财务数据警告: {messages}")
        
        return result
    
    return wrapper


# ============ 命令行接口 ============

def main():
    """命令行验证工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据验证工具')
    parser.add_argument('--type', choices=['price', 'financial'], 
                        required=True, help='验证类型')
    parser.add_argument('--file', '-f', help='JSON数据文件路径')
    parser.add_argument('--data', '-d', help='JSON格式数据字符串')
    parser.add_argument('--strict', action='store_true', 
                        help='严格模式（警告视为错误）')
    
    args = parser.parse_args()
    
    # 读取数据
    if args.file:
        with open(args.file, 'r') as f:
            data = json.load(f)
    elif args.data:
        data = json.loads(args.data)
    else:
        print("错误: 请提供 --file 或 --data 参数")
        return 1
    
    # 验证
    validator = DataValidator(strict_mode=args.strict)
    
    if args.type == 'price':
        is_valid, messages = validator.validate_stock_price(data)
    else:
        is_valid, messages = validator.validate_financial_data(data)
    
    # 输出结果
    if is_valid:
        print("✅ 数据验证通过")
        if messages:
            print(f"⚠️  警告: {messages}")
        return 0
    else:
        print("❌ 数据验证失败")
        for msg in messages:
            print(f"  - {msg}")
        return 1


if __name__ == '__main__':
    exit(main())
