# -*- coding:utf-8 -*-
import streamlit as st
import datetime
from lunarcalendar import Converter, Solar, Lunar

# 天干地支基础数据
tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

gan_he = {
    "甲": "己", "己": "甲",
    "乙": "庚", "庚": "乙",
    "丙": "辛", "辛": "丙",
    "丁": "壬", "壬": "丁",
    "戊": "癸", "癸": "戊"
}

gan_chong = {
    "甲": "庚", "庚": "甲",
    "乙": "辛", "辛": "乙",
    "丙": "壬", "壬": "丙",
    "丁": "癸", "癸": "丁"
}

zhi_he = {
    "子": "丑", "丑": "子",
    "寅": "亥", "亥": "寅",
    "卯": "戌", "戌": "卯",
    "辰": "酉", "酉": "辰",
    "巳": "申", "申": "巳",
    "午": "未", "未": "午"
}

zhi_chong = {dz: dizhi[(i + 6) % 12] for i, dz in enumerate(dizhi)}

def zhi_next(zhi_):
    return dizhi[(dizhi.index(zhi_) + 1) % 12]

def zhi_prev(zhi_):
    return dizhi[(dizhi.index(zhi_) - 1) % 12]

def ganzhi_list():
    return [tiangan[i % 10] + dizhi[i % 12] for i in range(60)]

def year_ganzhi_map(start=1900, end=2100):
    gzs = ganzhi_list()
    base_year = 1984  # 甲子年
    return {y: gzs[(y - base_year) % 60] for y in range(start, end + 1)}

# 立春换年
def get_year_ganzhi_li_chun(y, m, d):
    # 立春一般是2月4日，简化用2/4
    birth = datetime.date(y, m, d)
    lichun = datetime.date(y, 2, 4)
    year_for_gz = y if birth >= lichun else y - 1
    gzs = ganzhi_list()
    index = (year_for_gz - 1984) % 60
    return gzs[index]

# 月柱计算，寅月起月，正月为寅月
def get_month_ganzhi_li_chun(year, month, day):
    solar = Solar(year, month, day)
    lunar = Converter.Solar2Lunar(solar)
    # 计算立春节气对应农历月份
    lichun = datetime.date(year, 2, 4)
    lunar_lichun = Converter.Solar2Lunar(Solar(lichun.year, lichun.month, lichun.day))
    month_diff = (lunar.month - lunar_lichun.month) % 12
    # 月干从年干得，月支从寅起算
    year_gz = get_year_ganzhi_li_chun(year, month, day)
    tg_index = tiangan.index(year_gz[0])
    # 月干 = (年干*2 + 月差 + 2) %10
    tg_month_index = (tg_index * 2 + month_diff + 2) % 10
    dz_month_index = (2 + month_diff) % 12  # 寅=2
    return tiangan[tg_month_index] + dizhi[dz_month_index]

# 日柱用1900-01-31甲子日为起点计数
def get_day_ganzhi(year, month, day):
    base_date = datetime.date(1900, 1, 31)
    cur_date = datetime.date(year, month, day)
    diff_days = (cur_date - base_date).days
    gzs = ganzhi_list()
    return gzs[diff_days % 60]

# 时柱计算（2小时为一地支），日干决定时干
def get_time_ganzhi(day_gz, hour):
    if hour < 0 or hour > 23:
        return "不知道"
    dz_index = ((hour + 1) // 2) % 12
    dz = dizhi[dz_index]
    tg_day_index = tiangan.index(day_gz[0])
    tg_time_index = (tg_day_index * 2 + dz_index) % 10
    tg = tiangan[tg_time_index]
    return tg + dz

def calc_jixiong(gz):
    tg = gz[0]
    dz = gz[1]
    res = {"吉": [], "凶": []}
    tg_he = gan_he.get(tg, "")
    dz_he = zhi_he.get(dz, "")
    tg_ch = gan_chong.get(tg, "")
    dz_ch = zhi_chong.get(dz, "")
    if tg_he and dz_he:
        res["吉"].append(tg_he + dz_he)
        res["吉"].append(tg_he + zhi_next(dz_he))
    if tg_ch and dz_ch:
        res["凶"].append(tg_ch + dz_ch)
        res["凶"].append(tg_ch + zhi_prev(dz_ch))
    return res

def analyze_bazi(nianzhu, yuezhu, rizhu, shizhu):
    zhus = [nianzhu, yuezhu, rizhu]
    if shizhu and shizhu != "不知道":
        zhus.append(shizhu)
    all_ji = set()
    all_xiong = set()
    for zhu in zhus:
        res = calc_jixiong(zhu)
        all_ji.update(res["吉"])
        all_xiong.update(res["凶"])
    return sorted(all_ji), sorted(all_xiong)

def show_result(ji_list, xiong_list):
    current_year = datetime.datetime.now().year
    st.subheader("🎉 吉年")
    for gz in ji_list:
        years = [y for y, gz_y in year_ganzhi_map().items() if gz_y == gz]
        if years:
            year_strs = []
            for y in sorted(years):
                if y >= current_year:
                    year_strs.append(f"<span style='color:#d6336c;font-weight:bold'>{gz}{y}年★</span>")
                else:
                    year_strs.append(f"{gz}{y}年")
            st.markdown(f"{gz}: {', '.join(year_strs)}", unsafe_allow_html=True)

    st.subheader("☠️ 凶年")
    for gz in xiong_list:
        years = [y for y, gz_y in year_ganzhi_map().items() if gz_y == gz]
        if years:
            year_strs = []
            for y in sorted(years):
                if y >= current_year:
                    year_strs.append(f"<span style='color:#333333;font-weight:bold'>{gz}{y}年★</span>")
                else:
                    year_strs.append(f"{gz}{y}年")
            st.markdown(f"{gz}: {', '.join(year_strs)}", unsafe_allow_html=True)

# -------- 主界面 --------
st.title("八字吉凶年份查询")

input_mode = st.radio("请选择输入方式", ["阳历生日", "农历生日", "四柱八字"])

if input_mode == "阳历生日":
    birth_date = st.date_input("请选择阳历出生日期", min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2100, 12, 31))
    birth_hour = st.slider("请选择出生时辰（0-23时，未知请选-1）", -1, 23, -1)
    if st.button("开始推算八字并查询"):
        hour = birth_hour if birth_hour >= 0 else -1
        nianzhu = get_year_ganzhi_li_chun(birth_date.year, birth_date.month, birth_date.day)
        yuezhu = get_month_ganzhi_li_chun(birth_date.year, birth_date.month, birth_date.day)
        rizhu = get_day_ganzhi(birth_date.year, birth_date.month, birth_date.day)
        shizhu = get_time_ganzhi(rizhu, hour) if hour >= 0 else "不知道"
        st.write(f"推算八字：年柱 {nianzhu}，月柱 {yuezhu}，日柱 {rizhu}，时柱 {shizhu}")
        ji_list, xiong_list = analyze_bazi(nianzhu, yuezhu, rizhu, shizhu)
        show_result(ji_list, xiong_list)

elif input_mode == "农历生日":
    lunar_year = st.number_input("农历年", min_value=1900, max_value=2100, value=1990)
    lunar_month = st.number_input("农历月", min_value=1, max_value=12, value=1)
    lunar_day = st.number_input("农历日", min_value=1, max_value=30, value=1)
    birth_hour = st.slider("请选择出生时辰（0-23时，未知请选-1）", -1, 23, -1)
    if st.button("开始推算八字并查询"):
        try:
            lunar = Lunar(lunar_year, lunar_month, lunar_day, False)
            solar = Converter.Lunar2Solar(lunar)
            year, month, day = solar.year, solar.month, solar.day
            hour = birth_hour if birth_hour >= 0 else -1
            nianzhu = get_year_ganzhi_li_chun(year, month, day)
            yuezhu = get_month_ganzhi_li_chun(year, month, day)
            rizhu = get_day_ganzhi(year, month, day)
            shizhu = get_time_ganzhi(rizhu, hour) if hour >= 0 else "不知道"
            st.write(f"推算八字：年柱 {nianzhu}，月柱 {yuezhu}，日柱 {rizhu}，时柱 {shizhu}")
            ji_list, xiong_list = analyze_bazi(nianzhu, yuezhu, rizhu, shizhu)
            show_result(ji_list, xiong_list)
        except Exception as e:
            st.error(f"计算失败: {e}")

else:  # 四柱八字输入
    year_zhu = st.text_input("请输入年柱（如甲子）")
    month_zhu = st.text_input("请输入月柱（如乙丑）")
    day_zhu = st.text_input("请输入日柱（如丙寅）")
    time_zhu = st.text_input("请输入时柱（如不知道）", value="不知道")
    if st.button("查询吉凶年份"):
        if not (year_zhu and month_zhu and day_zhu):
            st.error("年柱、月柱、日柱为必填项")
        else:
            try:
                ji_list, xiong_list = analyze_bazi(year_zhu.strip(), month_zhu.strip(), day_zhu.strip(), time_zhu.strip())
                show_result(ji_list, xiong_list)
            except Exception as e:
                st.error(f"计算失败: {e}")
