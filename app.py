import streamlit as st
import datetime

try:
    import sxtwl
    HAS_SXTWL = True
except ImportError:
    HAS_SXTWL = False

# 干支表
gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 日干推时干口诀表
hour_gan_start = {
    "甲": 0, "己": 0,  # 甲己还加甲
    "乙": 2, "庚": 2,  # 乙庚丙作初
    "丙": 4, "辛": 4,  # 丙辛从戊起
    "丁": 6, "壬": 6,  # 丁壬庚子居
    "戊": 8, "癸": 8   # 戊癸何方发
}

# 时辰对应表
hour_zhi_map = [
    ("子", 23, 1),
    ("丑", 1, 3),
    ("寅", 3, 5),
    ("卯", 5, 7),
    ("辰", 7, 9),
    ("巳", 9, 11),
    ("午", 11, 13),
    ("未", 13, 15),
    ("申", 15, 17),
    ("酉", 17, 19),
    ("戌", 19, 21),
    ("亥", 21, 23)
]

def get_hour_zhi(hour):
    for z, start, end in hour_zhi_map:
        if start <= hour < end or (start == 23 and hour >= 23) or (end == 1 and hour < 1):
            return z
    return "子"

def calc_hour_pillar_by_rule(rigan, hour):
    """按规则推算时柱"""
    hour_zhi = get_hour_zhi(hour)
    gan_start_index = hour_gan_start[rigan]
    zhi_index = zhi.index(hour_zhi)
    gan_index = (gan_start_index + zhi_index) % 10
    return gan[gan_index] + hour_zhi

def get_bazi_by_sxtwl(year, month, day, hour):
    """使用 sxtwl 计算八字"""
    lunar = sxtwl.Lunar()
    day_data = lunar.getDayBySolar(year, month, day)
    yTG = day_data.getYearGZ()
    mTG = day_data.getMonthGZ()
    dTG = day_data.getDayGZ()
    hTG = lunar.getHourGZ(year, month, day, hour)

    year_gz = gan[yTG.tg] + zhi[yTG.dz]
    month_gz = gan[mTG.tg] + zhi[mTG.dz]
    day_gz = gan[dTG.tg] + zhi[dTG.dz]
    hour_gz = gan[hTG.tg] + zhi[hTG.dz]

    return year_gz, month_gz, day_gz, hour_gz

st.title("在线八字排盘（网页版 Streamlit）")

# 用户输入
year = st.number_input("出生年份", min_value=1900, max_value=2100, value=1990)
month = st.number_input("出生月份", min_value=1, max_value=12, value=5)
day = st.number_input("出生日期", min_value=1, max_value=31, value=18)
hour = st.number_input("出生小时（24小时制）", min_value=0, max_value=23, value=8)

method = st.radio("计算方式", ["规则计算", "sxtwl计算（需要安装sxtwl）"])

if st.button("计算八字"):
    try:
        if method == "sxtwl计算（需要安装sxtwl）":
            if not HAS_SXTWL:
                st.error("当前环境未安装 sxtwl，请选择规则计算")
            else:
                year_gz, month_gz, day_gz, hour_gz = get_bazi_by_sxtwl(year, month, day, hour)
                st.success(f"八字：{year_gz} {month_gz} {day_gz} {hour_gz}")
        else:
            # 规则计算
            if not HAS_SXTWL:
                # 规则计算需要先通过 sxtwl 获取年、月、日柱
                st.error("规则计算需要先用 sxtwl 获取年月日柱，目前未安装 sxtwl 无法完成。")
            else:
                y, m, d, h_sxtwl = get_bazi_by_sxtwl(year, month, day, hour)
                hour_gz = calc_hour_pillar_by_rule(d[0], hour)  # 用规则计算时柱
                st.success(f"八字：{y} {m} {d} {hour_gz}")
    except Exception as e:
        st.error(f"计算出错：{e}")
