# -*- coding: utf-8 -*-
"""
Streamlit 单文件：八字推算（立春分年、节气分月/手动月支）、日柱用锚点法（anchor），时精确到分钟
保持原有吉凶规则（天干合/冲、地支合/冲、双合进一/双冲退一）
"""
import datetime
from datetime import date, timedelta
import streamlit as st

# 试探导入 sxtwl（若已正确安装可提高节气与干支精度）
try:
    import sxtwl
    HAVE_SXTWL = True
except Exception:
    sxtwl = None
    HAVE_SXTWL = False

# ------------------ 基础干支与规则（与您保持一致） ------------------
tiangan = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
dizhi = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

# 天干合（五合）
gan_he = {"甲":"己","己":"甲","乙":"庚","庚":"乙","丙":"辛","辛":"丙","丁":"壬","壬":"丁","戊":"癸","癸":"戊"}

# 仅四冲（你确认过，删掉戊己）
gan_chong = {"甲":"庚","庚":"甲","乙":"辛","辛":"乙","丙":"壬","壬":"丙","丁":"癸","癸":"丁"}

# 地支合（六合）
zhi_he = {"子":"丑","丑":"子","寅":"亥","亥":"寅","卯":"戌","戌":"卯","辰":"酉","酉":"辰","巳":"申","申":"巳","午":"未","未":"午"}

# 地支冲（对冲，间隔6）
zhi_chong = {dz: dizhi[(i+6)%12] for i,dz in enumerate(dizhi)}

def zhi_next(z): return dizhi[(dizhi.index(z)+1)%12]
def zhi_prev(z): return dizhi[(dizhi.index(z)-1)%12]

# 六十甲子表
def ganzhi_list():
    return [tiangan[i%10] + dizhi[i%12] for i in range(60)]
GZS_LIST = ganzhi_list()

# 年份到干支映射（用于查找年份）
def year_ganzhi_map(start=1900, end=2100):
    gzs = GZS_LIST
    base_year = 1984  # 1984 甲子年为基准
    return {y: gzs[(y - base_year) % 60] for y in range(start, end+1)}

# 吉凶计算（保持你原逻辑）
def calc_jixiong(gz):
    if not gz or len(gz)<2: return {"吉":[], "凶":[]}
    tg, dz = gz[0], gz[1]
    res = {"吉":[], "凶":[]}
    tg_he = gan_he.get(tg,""); dz_he = zhi_he.get(dz,"")
    tg_ch = gan_chong.get(tg,""); dz_ch = zhi_chong.get(dz,"")
    if tg_he and dz_he:
        res["吉"].append(tg_he + dz_he)
        res["吉"].append(tg_he + zhi_next(dz_he))
    if tg_ch and dz_ch:
        res["凶"].append(tg_ch + dz_ch)
        res["凶"].append(tg_ch + zhi_prev(dz_ch))
    return res

def analyze_bazi(nianzhu, yuezhu, rizhu, shizhu):
    pillars = [p for p in (nianzhu, yuezhu, rizhu) if p]
    if shizhu and str(shizhu).strip() and str(shizhu).strip()!="不知道":
        pillars.append(shizhu)
    all_ji=[]; all_xiong=[]
    for p in pillars:
        r = calc_jixiong(p)
        all_ji.extend(r["吉"]); all_xiong.extend(r["凶"])
    # 去重并保持顺序
    def uniq(seq):
        seen=set(); out=[]
        for s in seq:
            if s not in seen:
                seen.add(s); out.append(s)
        return out
    return uniq(all_ji), uniq(all_xiong)

# ------------------ 日柱：锚点法（anchor） ------------------
ANCHOR_DATE = date(1984,1,1)   # 你给定的锚点
ANCHOR_GZ = "甲午"
ANCHOR_IDX = GZS_LIST.index(ANCHOR_GZ)

def day_ganzhi_by_anchor(y, m, d, hour=None, minute=None):
    """
    使用锚点法：以 1984-01-01 (甲午) 为基点，按天数差计算目标日期日干支。
    若时间在 23:00 及以后（含23:00），按次日计算（你提供的规则）。
    """
    # 处理日界线：23:00 及以后归入次日
    if hour is not None and hour >= 23:
        target = date(y,m,d) + timedelta(days=1)
    else:
        target = date(y,m,d)
    delta_days = (target - ANCHOR_DATE).days
    idx = (ANCHOR_IDX + delta_days) % 60
    return GZS_LIST[idx]

# ------------------ 月柱（节气优先 / 可手动指定月支） ------------------
# 五虎遁：年干决定寅月起始天干
def month_stem_by_fihu_dun(year_tg, month_branch):
    if year_tg in ("甲","己"): start_stem="丙"
    elif year_tg in ("乙","庚"): start_stem="戊"
    elif year_tg in ("丙","辛"): start_stem="庚"
    elif year_tg in ("丁","壬"): start_stem="壬"
    elif year_tg in ("戊","癸"): start_stem="甲"
    else: start_stem="丙"
    start_idx = tiangan.index(start_stem)
    offset = (dizhi.index(month_branch) - dizhi.index("寅")) % 12
    stem_idx = (start_idx + offset) % 10
    return tiangan[stem_idx] + month_branch

# 近似节气边界表（回退使用）
APPROX_JIEQI = {
    "立春": (2,4), "惊蛰": (3,6), "清明": (4,5), "立夏": (5,6),
    "芒种": (6,6), "小暑": (7,7), "立秋": (8,7), "白露": (9,7),
    "寒露": (10,8), "立冬": (11,7), "大雪": (12,7), "小寒": (1,6)
}

def get_month_branch_approx(year, month, day):
    """回退：以近似节气表判断月支（立春—惊蛰=寅月...）"""
    bd = date(year, month, day)
    keys = ["立春","惊蛰","清明","立夏","芒种","小暑","立秋","白露","寒露","立冬","大雪","小寒"]
    seq=[]
    for k in keys:
        m,d = APPROX_JIEQI[k]
        yr = year if not (k=="小寒" and m==1) else year+1
        seq.append((k, date(yr,m,d)))
    for i in range(len(seq)):
        s = seq[i][1]; e = seq[i+1][1] if i+1<len(seq) else seq[0][1].replace(year=seq[0][1].year+1)
        if s <= bd < e:
            return ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"][i]
    # fallback by month
    return dizhi[(month+10)%12]

# ------------------ 时柱（分钟精确） 五鼠遁 ------------------
def time_ganzhi_by_minute(day_gz, hour, minute):
    if hour is None or hour<0: return "不知道"
    total_min = hour*60 + (minute or 0)
    # 子时: 23:00-23:59 & 0:00-0:59
    if total_min >= 23*60:
        dz_idx = 0
    else:
        dz_idx = ((total_min + 60)//120) % 12
    branch = dizhi[dz_idx]
    day_tg = day_gz[0]
    if day_tg in ("甲","己"): start = tiangan.index("甲")
    elif day_tg in ("乙","庚"): start = tiangan.index("丙")
    elif day_tg in ("丙","辛"): start = tiangan.index("戊")
    elif day_tg in ("丁","壬"): start = tiangan.index("庚")
    elif day_tg in ("戊","癸"): start = tiangan.index("壬")
    else: start = 0
    tg_idx = (start + dz_idx) % 10
    return tiangan[tg_idx] + branch

# ------------------ 合并推算主流程 ------------------
def calc_bazi_from_solar(year, month, day, hour=None, minute=0, manual_month_branch=None):
    """
    返回 (年柱, 月柱, 日柱, 时柱, source_info)
    - 年柱：使用 sxtwl（若可用）按立春规则或近似 2/4 划分
    - 月柱：若 manual_month_branch 提供（'寅','卯'...），用五虎遁计算；否则 sxtwl monthGZ（若可用）或近似
    - 日柱：**使用锚点法**（你提供的算法）
    - 时柱：五鼠遁（分钟精确）
    """
    source = []
    # 年柱：尽量用 sxtwl.fromSolar -> getYearGZ；否则近似（以 立春 2/4 分界）
    year_p = None; month_p = None; day_p = None; hour_p = None
    if HAVE_SXTWL:
        try:
            dayobj = sxtwl.fromSolar(int(year), int(month), int(day))
            ygz = dayobj.getYearGZ(); mgz = dayobj.getMonthGZ(); dgz = dayobj.getDayGZ()
            year_p = tiangan[ygz.tg] + dizhi[ygz.dz]
            # 如果用户手动指定 month branch，我们会用五虎遁，用 sxtwl 仅作为参考
            if manual_month_branch:
                month_p = month_stem_by_fihu_dun(year_p[0], manual_month_branch)
            else:
                month_p = tiangan[mgz.tg] + dizhi[mgz.dz]
            day_sxtwl = tiangan[dgz.tg] + dizhi[dgz.dz]
            source.append("sxtwl")
        except Exception:
            year_p = None
    if year_p is None:
        # 近似年柱（立春固定 2/4）
        birth_dt = datetime.datetime(year, month, day, hour or 0, minute or 0)
        lichun = datetime.datetime(year,2,4,0,0)
        year_for = year if birth_dt >= lichun else year-1
        year_p = GZS_LIST[(year_for - 1984) % 60]
        source.append("approx-year")

        if manual_month_branch:
            month_p = month_stem_by_fihu_dun(year_p[0], manual_month_branch)
        else:
            month_branch = get_month_branch_approx(year, month, day)
            month_p = month_stem_by_fihu_dun(year_p[0], month_branch)
        day_sxtwl = None

    # 日柱：用锚点法（你提供的算法）
    day_p = day_ganzhi_by_anchor(year, month, day, hour, minute)

    # 时柱：五鼠遁分钟精确
    hour_p = None
    if hour is not None and hour >= 0:
        hour_p = time_ganzhi_by_minute(day_p, hour, minute or 0)

    # 如果 sxtwl 可用，比较 sxtwl 的日柱（仅作对比提示，不覆盖锚点结果）
    sxtwl_day = None
    if HAVE_SXTWL:
        try:
            # if dayobj exists from earlier, use its dayGZ; else try to create
            if 'dayobj' not in locals():
                dayobj = sxtwl.fromSolar(int(year), int(month), int(day))
            dgz2 = dayobj.getDayGZ()
            sxtwl_day = tiangan[dgz2.tg] + dizhi[dgz2.dz]
        except Exception:
            sxtwl_day = None

    source_info = ", ".join(source)
    return year_p, month_p, day_p, hour_p, sxtwl_day, source_info

# ------------------ 美化输出（吉/凶） ------------------
def show_result_beauty(ji_list, xiong_list, year_map, current_year):
    # nicer colors & boxed layout
    color_good = "#0b6623"   # 深绿
    color_bad = "#8B0000"    # 暗红
    # 吉年
    st.markdown("## 🎉 吉年")
    if not ji_list:
        st.info("无可列举的吉年（按当前规则）")
    else:
        for gz in ji_list:
            years = [y for y,g in year_map.items() if g == gz]
            if not years: continue
            years.sort()
            parts = []
            for y in years:
                s = f"{gz}{y}年"
                if y >= current_year:
                    s = f"<b>{s} ★</b>"
                parts.append(s)
            html = f"<div style='border-left:4px solid {color_good};padding:8px;margin:6px 0;background:#f7fff7'>{gz}: {'，'.join(parts)}</div>"
            st.markdown(html, unsafe_allow_html=True)
    # 凶年
    st.markdown("## ☠️ 凶年")
    if not xiong_list:
        st.info("无可列举的凶年（按当前规则）")
    else:
        for gz in xiong_list:
            years = [y for y,g in year_map.items() if g == gz]
            if not years: continue
            years.sort()
            parts=[]
            for y in years:
                s = f"{gz}{y}年"
                if y >= current_year:
                    s = f"<b>{s} ★</b>"
                parts.append(s)
            html = f"<div style='border-left:4px solid {color_bad};padding:8px;margin:6px 0;background:#fff7f7'>{gz}: {'，'.join(parts)}</div>"
            st.markdown(html, unsafe_allow_html=True)

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="八字推算 - 精准（锚点日法）", layout="centered")
st.title("八字推算与吉凶年份（中文界面）")

st.markdown("请选择输入方式，支持阳历/农历/四柱；可手动指定月支（若你更信任手工月支），日柱采用锚点法（1984-01-01 甲午）计算。")

mode = st.selectbox("输入方式", ["阳历生日", "农历生日", "四柱八字（手动）"])

if mode == "阳历生日":
    col1, col2 = st.columns([2,1])
    with col1:
        byear = st.number_input("出生年", min_value=1900, max_value=2100, value=1990, step=1)
        bmonth = st.selectbox("出生月（公历）", list(range(1,13)), index=4)
        bday = st.number_input("出生日", min_value=1, max_value=31, value=18, step=1)
    with col2:
        bhour = st.number_input("小时（0-23；未知填 -1）", min_value=-1, max_value=23, value=-1, step=1)
        bmin = st.number_input("分钟（0-59）", min_value=0, max_value=59, value=0, step=1)
    # 手动月支控制
    manual_month = st.checkbox("手动指定月支（地支，如：寅、卯、辰...）", value=False)
    manual_branch = None
    if manual_month:
        manual_branch = st.selectbox("请选择月支（地支）", dizhi, index=2)  # 默认寅
    if st.button("推算八字并查询吉凶"):
        hour_val = None if bhour == -1 else int(bhour)
        min_val = int(bmin) if hour_val is not None else 0
        try:
            y_p, m_p, d_p, h_p, sxtwl_day, src = calc_bazi_from_solar(int(byear), int(bmonth), int(bday), hour_val, min_val, manual_month_branch=manual_branch)
            st.markdown("### 推算结果（四柱）")
            st.write(f"年柱：{y_p} ； 月柱：{m_p} ； 日柱（锚点法）：{d_p} ； 时柱：{h_p or '不知道'}")
            if sxtwl_day:
                if sxtwl_day != d_p:
                    st.caption(f"（注：本地 sxtwl 计算得日柱为 {sxtwl_day}，程序当前以锚点法 {d_p} 为主；若你信任万年历可选择以 sxtwl 为准。）")
                else:
                    st.caption("（sxtwl 日柱与锚点法一致）")
            # 吉凶
            ji, xiong = analyze_bazi(y_p, m_p, d_p, h_p)
            ymap = year_ganzhi_map(1900,2100); cur = datetime.datetime.now().year
            show_result_beauty(ji, xiong, ymap, cur)
        except Exception as e:
            st.error(f"计算出错：{e}")

elif mode == "农历生日":
    col1, col2 = st.columns([2,1])
    with col1:
        ly = st.number_input("农历年", min_value=1900, max_value=2100, value=1990, step=1)
        lm = st.number_input("农历月（1-12）", min_value=1, max_value=12, value=5, step=1)
        isleap = st.checkbox("是否闰月", value=False)
        ld = st.number_input("农历日", min_value=1, max_value=30, value=18, step=1)
    with col2:
        bhour = st.number_input("小时（0-23；未知填 -1）", min_value=-1, max_value=23, value=-1, step=1)
        bmin = st.number_input("分钟（0-59）", min_value=0, max_value=59, value=0, step=1)
    manual_month = st.checkbox("手动指定月支（地支，如：寅、卯、辰...）", value=False)
    manual_branch = None
    if manual_month:
        manual_branch = st.selectbox("请选择月支（地支）", dizhi, index=2)
    if st.button("从农历推算并查询"):
        hour_val = None if bhour == -1 else int(bhour)
        min_val = int(bmin) if hour_val is not None else 0
        try:
            # 先把农历转阳历（使用内置算法：try sxtwl.fromLunar else use Converter fallback）
            solar_y = None
            if HAVE_SXTWL:
                try:
                    # some sxtwl.fromLunar accept 4 params (year,month,day,isLeap)
                    try:
                        sday = sxtwl.fromLunar(int(ly), int(lm), int(ld), bool(isleap))
                    except TypeError:
                        sday = sxtwl.fromLunar(int(ly), int(lm), int(ld))
                    # sday -> getSolar / getYear / getMonth / getDay maybe available
                    # Try to extract solar date
                    sy = sday.getSolar()
                    solar_y, solar_m, solar_d = sy.getYear(), sy.getMonth(), sy.getDay()
                except Exception:
                    solar_y = None
            if solar_y is None:
                # fallback: use lunarcalendar Converter
                from lunarcalendar import Converter, Solar, Lunar
                lunar_obj = Lunar(int(ly), int(lm), int(ld), bool(isleap))
                solar = Converter.Lunar2Solar(lunar_obj)
                solar_y, solar_m, solar_d = solar.year, solar.month, solar.day

            y_p, m_p, d_p, h_p, sxtwl_day, src = calc_bazi_from_solar(solar_y, solar_m, solar_d, hour_val, min_val, manual_month_branch=manual_branch)
            st.markdown("### 推算结果（四柱）")
            st.write(f"阳历对应：{solar_y}年{solar_m}月{solar_d}日")
            st.write(f"年柱：{y_p} ； 月柱：{m_p} ； 日柱（锚点法）：{d_p} ； 时柱：{h_p or '不知道'}")
            if sxtwl_day and sxtwl_day != d_p:
                st.caption(f"（sxtwl 计算的日柱为 {sxtwl_day}，程序以锚点法 {d_p} 为主）")
            ji, xiong = analyze_bazi(y_p, m_p, d_p, h_p)
            ymap = year_ganzhi_map(1900,2100); cur = datetime.datetime.now().year
            show_result_beauty(ji, xiong, ymap, cur)
        except Exception as e:
            st.error(f"转换或计算出错：{e}")

else:  # 四柱手动输入
    st.markdown("请直接输入四柱（例：甲子、乙丑、丙寅）。时柱可填写“不知道”或空以跳过。")
    ny = st.text_input("年柱（如：甲子）")
    my = st.text_input("月柱（如：乙丑）")
    dy = st.text_input("日柱（如：丙寅）")
    sy = st.text_input("时柱（如：不知道）", value="不知道")
    if st.button("查询吉凶年份"):
        if not (ny and my and dy):
            st.error("请至少填写年柱、月柱、日柱")
        else:
            ji, xiong = analyze_bazi(ny.strip(), my.strip(), dy.strip(), sy.strip())
            ymap = year_ganzhi_map(1900,2100); cur = datetime.datetime.now().year
            st.markdown("### 你输入的四柱")
            st.write(f"{ny}  {my}  {dy}  {sy}")
            show_result_beauty(ji, xiong, ymap, cur)
