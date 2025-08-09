# -*- coding: utf-8 -*-
import streamlit as st
import datetime
import sxtwl
from lunarcalendar import Converter, Solar, Lunar

# ----------------- 基础干支数据 -----------------
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

def zhi_next(zhi):
    return dizhi[(dizhi.index(zhi) + 1) % 12]

def zhi_prev(zhi):
    return dizhi[(dizhi.index(zhi) - 1) % 12]

def ganzhi_list():
    result = []
    for i in range(60):
        tg = tiangan[i % 10]
        dz = dizhi[i % 12]
        result.append(tg + dz)
    return result

def year_ganzhi_map(start=1900, end=2100):
    gzs = ganzhi_list()
    base_year = 1984  # 甲子年起点
    year_map = {}
    for year in range(start, end + 1):
        index = (year - base_year) % 60
        year_map[year] = gzs[index]
    return year_map

def calc_jixiong(gz):
    tg = gz[0]
    dz = gz[1]
    results = {"吉": [], "凶": []}
    tg_he = gan_he.get(tg, "")
    dz_he = zhi_he.get(dz, "")
    tg_ch = gan_chong.get(tg, "")
    dz_ch = zhi_chong.get(dz, "")
    if tg_he and dz_he:
        shuang_he = tg_he + dz_he
        jin_yi = tg_he + zhi_next(dz_he)
        results["吉"].extend([shuang_he, jin_yi])
    if tg_ch and dz_ch:
        shuang_ch = tg_ch + dz_ch
        tui_yi = tg_ch + zhi_prev(dz_ch)
        results["凶"].extend([shuang_ch, tui_yi])
    return results

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

# ------------------ 立春和八字推算 ------------------

def get_li_chun_date(year):
    """返回指定年份立春的阳历日期"""
    cal = sxtwl.fromSolar(year, 1, 1)
    for solar in cal.getJieQiList():
        if solar["jieQi"] == 3:  # 立春节气编号
            return datetime.date(solar["year"], solar["month"], solar["day"])
    return datetime.date(year, 2, 4)

def get_year_ganzhi_li_chun(year, month, day):
    li_chun = get_li_chun_date(year)
    birth_date = datetime.date(year, month, day)
    adjusted_year = year if birth_date >= li_chun else year - 1
    index = (adjusted_year - 4) % 60
    return tiangan[index % 10] + dizhi[index % 12]

def get_month_ganzhi_li_chun(year, month, day):
    li_chun = get_li_chun_date(year)
    birth_date = datetime.date(year, month, day)
    solar = Solar(year, month, day)
    lunar = Converter.Solar2Lunar(solar)
    lunar_month = lunar.month
    li_chun_lunar = Converter.Solar2Lunar(Solar(li_chun.year, li_chun.month, li_chun.day))
    li_chun_lunar_month = li_chun_lunar.month
    month_offset = (lunar_month - li_chun_lunar_month) % 12
    year_gz = get_year_ganzhi_li_chun(year, month, day)
    tg_year = year_gz[0]
    tg_year_index = tiangan.index(tg_year)
    tg_index = (tg_year_index * 2 + month_offset + 2) % 10
    dz_index = (2 + month_offset) % 12
    return tiangan[tg_index] + dizhi[dz_index]

def get_bazi_from_solar_li_chun(year, month, day, hour):
    nianzhu = get_year_ganzhi_li_chun(year, month, day)
    yuezhu = get_month_ganzhi_li_chun(year, month, day)
    base_date = datetime.date(1900, 1, 31)
    cur_date = datetime.date(year, month, day)
    delta_days = (cur_date - base_date).days
    r_index = delta_days % 60
    rizhu = tiangan[r_index % 10] + dizhi[r_index % 12]
    shi_dizhi_list = dizhi
    shi_index = ((hour + 1) // 2) % 12
    dz_shi = shi_dizhi_list[shi_index]
    tg_day = rizhu[0]
    tg_day_index = tiangan.index(tg_day)
    tg_shi_index = (tg_day_index * 2 + shi_index) % 10
    shizhu = tiangan[tg_shi_index] + dz_shi
    return nianzhu, yuezhu, rizhu, shizhu

# -------------------- 结果展示 ---------------------

def show_result(ji_list, xiong_list):
    current_year = datetime.datetime.now().year
    st.subheader("🎉 吉年")
    for gz in ji_list:
        years = [y for y, gz_y in year_ganzhi_map().items() if gz_y == gz]
        if years:
            year_strs = []
            for y in sorted(years):
                if y >= current_year:
                    year_strs.append(f"<b style='color:red'>{gz}{y}年★</b>")
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
                    year_strs.append(f"<b style='color:#333'>{gz}{y}年★</b>")
                else:
                    year_strs.append(f"{gz}{y}年")
            st.markdown(f"{gz}: {', '.join(year_strs)}", unsafe_allow_html=True)

# ---------------------- 主界面 ----------------------

st.title("八字吉凶年份查询")

input_mode = st.radio("请选择输入方式", ["阳历生日（立春换年）", "农历生日", "四柱八字"])

if input_mode == "阳历生日（立春换年）":
    birth_date = st.date_input("请选择阳历出生日期", min_value=datetime.date(1900, 1, 1))
    birth_hour = st.slider("请选择出生时辰（0-23时，未知请选-1）", -1, 23, -1)
    if st.button("开始推算八字并查询吉凶"):
        try:
            hour = birth_hour if birth_hour >= 0 else 0
            nianzhu, yuezhu, rizhu, shizhu = get_bazi_from_solar_li_chun(
                birth_date.year, birth_date.month, birth_date.day, hour
            )
            if birth_hour == -1:
                shizhu = "不知道"
            st.write(f"推算八字：年柱 {nianzhu}，月柱 {yuezhu}，日柱 {rizhu}，时柱 {shizhu}")
            ji_list, xiong_list = analyze_bazi(nianzhu, yuezhu, rizhu, shizhu)
            show_result(ji_list, xiong_list)
        except Exception as e:
            st.error(f"计算出错：{e}")

elif input_mode == "农历生日":
    lunar_year = st.number_input("农历年", min_value=1900, max_value=2100, value=1990)
    lunar_month = st.number_input("农历月（1-12）", min_value=1, max_value=12, value=1)
    lunar_day = st.number_input("农历日（1-30）", min_value=1, max_value=30, value=1)
    birth_hour = st.slider("请选择出生时辰（0-23时，未知请选-1）", -1, 23, -1)
    if st.button("开始推算八字并查询吉凶"):
        try:
            hour = birth_hour if birth_hour >= 0 else 0
            # 先转阳历再用立春法推算，农历转阳历
            solar = Converter.Lunar2Solar(Lunar(lunar_year, lunar_month, lunar_day, False))
            nianzhu, yuezhu, rizhu, shizhu = get_bazi_from_solar_li_chun(
                solar.year, solar.month, solar.day, hour
            )
            if birth_hour == -1:
                shizhu = "不知道"
            st.write(f"推算八字：年柱 {nianzhu}，月柱 {yuezhu}，日柱 {rizhu}，时柱 {shizhu}")
            ji_list, xiong_list = analyze_bazi(nianzhu, yuezhu, rizhu, shizhu)
            show_result(ji_list, xiong_list)
        except Exception as e:
            st.error(f"计算出错：{e}")

else:  # 四柱八字直接输入
    year_zhu = st.text_input("请输入年柱（如 甲子）")
    month_zhu = st.text_input("请输入月柱（如 乙丑）")
    day_zhu = st.text_input("请输入日柱（如 丙寅）")
    time_zhu = st.text_input("请输入时柱（如 不知道）", value="不知道")
    if st.button("查询吉凶年份"):
        if not (year_zhu and month_zhu and day_zhu):
            st.error("年柱、月柱、日柱必须填写")
        else:
            try:
                ji_list, xiong_list = analyze_bazi(year_zhu.strip(), month_zhu.strip(), day_zhu.strip(), time_zhu.strip())
                show_result(ji_list, xiong_list)
            except Exception as e:
                st.error(f"计算出错：{e}")
