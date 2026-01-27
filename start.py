#!/usr/bin/env python3
"""
交易决策系统 - 统一启动脚本

功能:
- ✅ 定时任务 (每5分钟自动执行分析)
- ✅ API接口 (支持手动触发分析)
- ✅ 只需要启动一个服务

使用方法:
    python start.py

API接口:
    http://localhost:8000/health - 健康检查
    http://localhost:8000/api/v1/analyze - 触发分析
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from trading_decision_system.integrated_service import IntegratedService


async def main():
    """启动整合服务"""
    service = IntegratedService()
    await service.start(api_port=8000)


if __name__ == "__main__":
    print("="*80)
    print("交易决策系统 - 整合服务")
    print("="*80)
    print()
    print("功能:")
    print("  • 定时任务 (每5分钟自动执行分析)")
    print("  • API接口 (支持手动触发分析)")
    print()
    print("API接口:")
    print("  http://localhost:8000/health - 健康检查")
    print("  http://localhost:8000/api/v1/analyze - 触发分析")
    print()
    print("按 Ctrl+C 停止服务")
    print("="*80)
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"\n服务运行失败: {e}")
        sys.exit(1)
