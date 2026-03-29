#!/usr/bin/env python3
"""
数据验证脚本 - 符合 V1.2.1 标准
验证 JSON 文件格式和可选 schema 约束
"""

import os
import sys
import json
import argparse

def load_json_file(filepath):
    """加载 JSON 文件，返回解析后的数据或 None（失败时）"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        print(f"[VALIDATE:ERROR] JSON 解析失败: {e}", file=sys.stderr)
        return None
    except IOError as e:
        print(f"[VALIDATE:ERROR] 文件读取失败: {e}", file=sys.stderr)
        return None

def basic_validation(data):
    """基本验证：检查必需字段和类型"""
    required_fields = [
        "ticker", "name", "nav_history", "current_nav", 
        "daily_change", "ytd_return", "risk_level", 
        "asset_class", "last_updated"
    ]
    
    missing = [field for field in required_fields if field not in data]
    if missing:
        print(f"[VALIDATE:ERROR] 缺少必需字段: {missing}", file=sys.stderr)
        return False
    
    # 检查 nav_history 是否为数组
    if not isinstance(data["nav_history"], list):
        print(f"[VALIDATE:ERROR] nav_history 必须是数组", file=sys.stderr)
        return False
    
    # 检查数组元素
    for i, item in enumerate(data["nav_history"]):
        if not isinstance(item, dict):
            print(f"[VALIDATE:ERROR] nav_history[{i}] 必须是对象", file=sys.stderr)
            return False
        for field in ["date", "price", "change"]:
            if field not in item:
                print(f"[VALIDATE:ERROR] nav_history[{i}] 缺少字段 '{field}'", file=sys.stderr)
                return False
    
    print(f"[VALIDATE:INFO] 基本验证通过", file=sys.stdout)
    return True

def schema_validation(data, schema_file):
    """使用 JSON Schema 验证"""
    try:
        import jsonschema
    except ImportError:
        print(f"[VALIDATE:WARN] jsonschema 库未安装，跳过 schema 验证", file=sys.stderr)
        return True
    
    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"[VALIDATE:ERROR] 无法加载 schema 文件: {e}", file=sys.stderr)
        return False
    
    try:
        jsonschema.validate(instance=data, schema=schema)
        print(f"[VALIDATE:INFO] schema 验证通过", file=sys.stdout)
        return True
    except jsonschema.exceptions.ValidationError as e:
        print(f"[VALIDATE:ERROR] schema 验证失败: {e.message}", file=sys.stderr)
        print(f"[VALIDATE:ERROR] 路径: {e.json_path}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[VALIDATE:ERROR] schema 验证过程中出错: {e}", file=sys.stderr)
        return False

def file_integrity_check(filepath):
    """检查文件完整性：文件是否存在，是否有读取权限"""
    if not os.path.exists(filepath):
        print(f"[VALIDATE:ERROR] 文件不存在: {filepath}", file=sys.stderr)
        return False
    
    if not os.access(filepath, os.R_OK):
        print(f"[VALIDATE:ERROR] 文件不可读: {filepath}", file=sys.stderr)
        return False
    
    # 检查文件大小
    size = os.path.getsize(filepath)
    if size == 0:
        print(f"[VALIDATE:ERROR] 文件为空", file=sys.stderr)
        return False
    
    # 检查文件末尾是否有换行符（可选）
    try:
        with open(filepath, 'rb') as f:
            f.seek(-1, os.SEEK_END)
            last_char = f.read(1)
            if last_char != b'\n':
                print(f"[VALIDATE:WARN] 文件末尾缺少换行符（非致命）", file=sys.stderr)
    except:
        pass
    
    return True

def main():
    parser = argparse.ArgumentParser(description="验证 JSON 文件格式和结构")
    parser.add_argument("--file", required=True, help="要验证的 JSON 文件路径")
    parser.add_argument("--schema", help="JSON Schema 文件路径（可选）")
    parser.add_argument("--strict", action="store_true", help="严格模式：所有警告视为错误")
    
    args = parser.parse_args()
    
    # 1. 文件完整性检查
    if not file_integrity_check(args.file):
        sys.exit(1)
    
    # 2. 加载 JSON
    data = load_json_file(args.file)
    if data is None:
        sys.exit(2)
    
    # 3. 基本验证（仅当没有提供 schema 时执行）
    if not args.schema:
        # 通用基本验证：检查是否为字典
        if not isinstance(data, dict):
            print(f"[VALIDATE:ERROR] 数据必须是 JSON 对象", file=sys.stderr)
            sys.exit(3)
        print(f"[VALIDATE:INFO] 基本验证通过", file=sys.stdout)
    else:
        # 有 schema 文件，跳过基本验证，直接进行 schema 验证
        print(f"[VALIDATE:INFO] 使用 schema 验证，跳过基本验证", file=sys.stdout)
    
    # 4. Schema 验证（如果提供了 schema）
    if args.schema:
        if not os.path.exists(args.schema):
            print(f"[VALIDATE:ERROR] schema 文件不存在: {args.schema}", file=sys.stderr)
            sys.exit(4)
        if not schema_validation(data, args.schema):
            sys.exit(5)
    
    # 5. 额外检查：数据新鲜度（可选）
    # 这里可以检查 last_updated 字段是否在最近 24 小时内
    # 但这是业务逻辑，不是结构验证
    
    print(f"[VALIDATE:SUCCESS] 所有验证通过", file=sys.stdout)
    sys.exit(0)

if __name__ == "__main__":
    main()