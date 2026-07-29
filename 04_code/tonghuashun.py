# -*- coding:utf-8 -*-
from iFinDPy import *

# ========= 配置区：填写你的iFinD登录账号密码 =========
user = "yxwgy037"
pwd = "124228Xf"
# ==================================================

# 登录iFinD接口
login_status = THS_iFinDLogin(user, pwd)
if login_status == 0:
    print("✅ iFinD接口登录成功！")
else:
    print(f"❌登录失败，错误码：{login_status}")

# ---------------------- 第一条：单只股票（注意：直接传参，不加 codes= 等关键字）
res1 = THS_HQ(
    "688041.SH,688256.SH",
    "open,close,changeRatio,volume,amount",
    'CPS:3,baseDate:2019-01-01',
    '2019-01-01',
    '2026-07-01'
)
df1 = res1.data
print("====第一组股票数据====")
print(df1.head())

# ---------------------- 第二条：多只批量股票
res2 = THS_HQ(
    "000988.SZ,002049.SZ,002281.SZ,300308.SZ,300394.SZ,300474.SZ,300502.SZ,603019.SH,688008.SH",
    "open,close,changeRatio,volume,amount",
    'CPS:3,baseDate:2019-01-01',
    '2019-01-01',
    '2026-07-01'
)
df2 = res2.data
print("\n====第二组批量股票数据====")
print(df2.head())

# 可选：直接导出CSV保存到本地
df2.to_csv("股票日线数据.csv", encoding="utf-8-sig", index=False)