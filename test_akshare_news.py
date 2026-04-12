#!/usr/bin/env python3
"""
测试Akshare新闻接口
"""

import akshare as ak
import datetime
import json

print("测试Akshare新闻接口...")
print("=" * 60)

# 测试多个Akshare新闻接口
test_cases = [
    ("news_cctv", "央视新闻"),
    ("news_lianhe", "联合早报"),
    ("news_cls", "财联社"),
    ("news_eastmoney", "东方财富"),
    ("news_sina", "新浪财经"),
    ("news_163", "网易财经"),
    ("news_sohu", "搜狐财经"),
    ("news_qq", "腾讯财经"),
    ("news_jin10", "金十数据"),
    ("news_wallstreetcn", "华尔街见闻"),
]

results = []

for func_name, description in test_cases:
    try:
        print(f"\n测试 {description} ({func_name})...")
        
        # 尝试调用函数
        if hasattr(ak, func_name):
            func = getattr(ak, func_name)
            
            # 尝试不同参数
            try:
                # 尝试无参数调用
                df = func()
            except TypeError:
                try:
                    # 尝试带日期参数
                    today = datetime.datetime.now().strftime("%Y%m%d")
                    df = func(date=today)
                except TypeError:
                    try:
                        # 尝试其他参数格式
                        df = func(symbol="news")
                    except Exception as e:
                        print(f"  ❌ 调用失败: {e}")
                        continue
            
            if df is not None and not df.empty:
                print(f"  ✅ 成功获取 {len(df)} 条新闻")
                print(f"     列名: {list(df.columns)}")
                
                # 显示前几条新闻
                for i in range(min(3, len(df))):
                    row = df.iloc[i]
                    print(f"     新闻{i+1}: {str(row)[:80]}...")
                
                results.append((func_name, description, len(df)))
            else:
                print(f"  ⚠️  无数据返回")
        else:
            print(f"  ❌ 函数不存在")
            
    except Exception as e:
        print(f"  ❌ 错误: {e}")

print("\n" + "=" * 60)
print("测试结果汇总:")
print("=" * 60)

if results:
    print(f"✅ 找到 {len(results)} 个可用的Akshare新闻接口:")
    
    for func_name, description, count in results:
        print(f"  - {description} ({func_name}): {count} 条新闻")
    
    # 推荐最佳接口
    best_result = max(results, key=lambda x: x[2])
    print(f"\n💡 推荐使用: {best_result[1]} ({best_result[0]})")
    print(f"   获取到 {best_result[2]} 条新闻")
    
    # 测试内容完整性
    print(f"\n📊 内容完整性测试:")
    try:
        if best_result[0] == "news_cctv":
            df = ak.news_cctv()
        elif best_result[0] == "news_lianhe":
            df = ak.news_lianhe()
        elif best_result[0] == "news_cls":
            df = ak.news_cls()
        else:
            func = getattr(ak, best_result[0])
            df = func()
        
        # 检查是否有内容列
        content_columns = [col for col in df.columns if '内容' in col or 'content' in col.lower() or '正文' in col]
        
        if content_columns:
            content_col = content_columns[0]
            print(f"    内容列: {content_col}")
            
            # 计算平均内容长度
            content_lengths = []
            for i in range(min(10, len(df))):
                content = str(df.iloc[i][content_col])
                if content and content != 'nan':
                    content_lengths.append(len(content))
            
            if content_lengths:
                avg_length = sum(content_lengths) / len(content_lengths)
                print(f"    平均内容长度: {avg_length:.0f} 字符")
                
                if avg_length > 50:
                    print(f"    ✅ 内容完整性达标 (>50字符)")
                else:
                    print(f"    ⚠️  内容完整性不足 (<50字符)")
            else:
                print(f"    ⚠️  未找到有效内容")
        else:
            print(f"    ⚠️  未找到内容列")
            print(f"    所有列: {list(df.columns)}")
            
    except Exception as e:
        print(f"    ❌ 内容测试失败: {e}")
        
else:
    print("❌ 未找到可用的Akshare新闻接口")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)