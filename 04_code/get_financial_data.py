# -*- coding: utf-8 -*-
from iFinDPy import *
import pandas as pd
import json

# 1. 登录同花顺 iFinD 账号
username = "yxwgy037"
password = "124228Xf"

ths_login = THS_iFinDLogin(username, password)
if ths_login != 0:
    print(f"❌ 登录失败，错误码: {ths_login}")
else:
    print("✅ 登录成功！")

    # 2. 定义提取参数
    codes = '000977.SZ,000988.SZ,000997.SZ,002049.SZ,002065.SZ,002131.SZ,002230.SZ,002236.SZ,002253.SZ,002281.SZ,002368.SZ,002371.SZ,002405.SZ,002415.SZ,002439.SZ,002463.SZ,002607.SZ,002777.SZ,300020.SZ,300033.SZ,300036.SZ,300058.SZ,300075.SZ,300078.SZ,300168.SZ,300170.SZ,300188.SZ,300223.SZ,300229.SZ,300253.SZ,300308.SZ,300365.SZ,300394.SZ,300451.SZ,300474.SZ,300476.SZ,300496.SZ,300502.SZ,300624.SZ,300634.SZ,300781.SZ,300785.SZ,600183.SH,600410.SH,600556.SH,600570.SH,603019.SH,603160.SH,603986.SH,688008.SH,688012.SH,688023.SH,688041.SH,688088.SH,688111.SH,688228.SH,688256.SH,688327.SH,688369.SH,688981.SH'
    indicators = 'ths_total_assets_stock;ths_asset_liab_ratio_stock;ths_np_stock;ths_revenue_stock;ths_total_liab_stock;ths_total_owner_equity_stock'
    date_params = '20190630,100;20190630;20190630,100;20190630,100;20190630,100;20190630,100'

    # 3. 调用基础数据函数 (THS_BD)
    data_result = THS_BD(codes, indicators, date_params, 'format:json')

    # 4. 检查是否报错并处理数据
    if data_result.errorcode != 0:
        print(f"❌ 数据提取失败，错误信息: {data_result.errmsg}")
    else:
        print("✅ 数据提取成功！正在解析数据...")

        raw_data = data_result.data

        # 【核心修复】如果返回的是 bytes 类型，先解码为 utf-8 字符串
        if isinstance(raw_data, bytes):
            print("   - 检测到 bytes 类型，正在进行 utf-8 解码...")
            try:
                json_str = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                print("❌ utf-8 解码失败，尝试使用 gbk 解码...")
                json_str = raw_data.decode('gbk')
        elif isinstance(raw_data, str):
            json_str = raw_data
        else:
            print(f"❌ 未知的数据类型: {type(raw_data)}")
            exit()

        # 解析 JSON 并转换为 DataFrame
        try:
            parsed_data = json.loads(json_str)
            df = pd.DataFrame(parsed_data)

            print(f"   - 成功转换为 DataFrame，行数: {len(df)}, 列数: {len(df.columns)}")
            print("\n📊 数据预览:")
            print(df.head())

            # 导出为 CSV
            save_path = 'financial_quarterly_2019Q2.csv'
            df.to_csv(save_path, index=False, encoding='utf-8-sig')
            print(f"\n💾 数据已成功保存为: {save_path}")

        except Exception as e:
            print(f"❌ JSON 解析或 DataFrame 转换失败: {e}")
            print("   - JSON 字符串前300个字符:", json_str[:300])