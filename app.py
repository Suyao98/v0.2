import streamlit as st
import datetime

# 省略之前定义的天干地支和吉凶相关函数
# 请将你的 gan_he, gan_chong, zhi_he, zhi_chong, zhi_next, zhi_prev, ganzhi_list,
# year_ganzhi_map, calc_jixiong, analyze_bazi 函数复制进来。

# 这里为了示范，假设这些函数已经定义，你需用你原有版本替换

# -------------- 八字推算辅助函数 --------------

from lunarcalendar import Converter, Solar, Lunar  # 需安装 lunarcalendar

tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

def get_bazi_from_solar(year, month, day, hour):
    solar = Solar(year, month, day)
    lunar = Converter.Solar2Lunar(solar)

    lichun = datetime.date(year, 2, 4)
    bdate = datetime.date(year, month, day)
    cyc_year = year if bdate >= lichun else year - 1

    tg_index = (cyc_year - 4) % 10
    dz_index = (cyc_year - 4) % 12
    nianzhu = tiangan[tg_index] + dizhi[dz_index]

    tg_m = (tg_index * 2 + lunar.month + 2) % 10
    yuezhu = tiangan[tg_m] + dizhi[(lunar.month + 1) % 12]

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

def get_bazi_from_lunar(year, month, day, hour):
    lunar = Lunar(year, month, day, False)
    solar = Converter.Lunar2Solar(lunar)
    return get_bazi_from_solar(solar.year, solar.month, solar.day, hour)

# -------------- Streamlit 主程序 --------------

st.title("多输入方式八字吉凶年份查询")

input_mode = st.radio("请选择输入方式", ["阳历生日", "农历生日", "四柱八字"])

if input_mode == "阳历生日":
    birth_date = st.date_input("请选择阳历出生日期")
    birth_hour = st.slider("请选择出生时辰（0-23时，未知可填-1）", -1, 23, -1)
    if st.button("开始推算八字并查询吉凶"):
        try:
            hour = birth_hour if birth_hour >= 0 else 0
            nianzhu, yuezhu, rizhu, shizhu = get_bazi_from_solar(
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
    birth_hour = st.slider("请选择出生时辰（0-23时，未知可填-1）", -1, 23, -1)
    if st.button("开始推算八字并查询吉凶"):
        try:
            hour = birth_hour if birth_hour >= 0 else 0
            nianzhu, yuezhu, rizhu, shizhu = get_bazi_from_lunar(
                lunar_year, lunar_month, lunar_day, hour
            )
            if birth_hour == -1:
                shizhu = "不知道"

            st.write(f"推算八字：年柱 {nianzhu}，月柱 {yuezhu}，日柱 {rizhu}，时柱 {shizhu}")

            ji_list, xiong_list = analyze_bazi(nianzhu, yuezhu, rizhu, shizhu)
            show_result(ji_list, xiong_list)

        except Exception as e:
            st.error(f"计算出错：{e}")

else:  # 四柱八字
    year_zhu = st.text_input("请输入年柱（如 甲子）")
    month_zhu = st.text_input("请输入月柱（如 乙丑）")
    day_zhu = st.text_input("请输入日柱（如 丙寅）")
    time_zhu = st.text_input("请输入时柱（如 不知道）", value="不知道")
    if st.button("查询吉凶年份"):
        if not (year_zhu and month_zhu and day_zhu):
            st.error("年柱、月柱、日柱必须填写")
        else:
            ji_list, xiong_list = analyze_bazi(year_zhu, month_zhu, day_zhu, time_zhu)
            show_result(ji_list, xiong_list)

# ---------- 结果展示 ----------
def show_result(ji_list, xiong_list):
    current_year = datetime.datetime.now().year

    st.subheader("🎉 吉年")
    for gz in sorted(ji_list, key=lambda x: ganzhi_list().index(x) if x in ganzhi_list() else 999):
        years = [y for y, gz_y in year_ganzhi_map().items() if gz_y == gz]
        if years:
            year_strs = []
            for y in years:
                if y >= current_year:
                    year_strs.append(f"<b>{gz}{y}年★</b>")
                else:
                    year_strs.append(f"{gz}{y}年")
            st.markdown(
                f"<span style='color:red'>{gz}: {', '.join(year_strs)}</span>",
                unsafe_allow_html=True
            )

    st.subheader("☠️ 凶年")
    for gz in sorted(xiong_list, key=lambda x: ganzhi_list().index(x) if x in ganzhi_list() else 999):
        years = [y for y, gz_y in year_ganzhi_map().items() if gz_y == gz]
        if years:
            year_strs = []
            for y in years:
                if y >= current_year:
                    year_strs.append(f"<b>{gz}{y}年★</b>")
                else:
                    year_strs.append(f"{gz}{y}年")
            st.markdown(
                f"<span style='color:#333'>{gz}: {', '.join(year_strs)}</span>",
                unsafe_allow_html=True
            )
