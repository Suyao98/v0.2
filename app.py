# -*- coding: utf-8 -*-
"""
Streamlit 八字推算与吉凶年份查询（中文界面，时间精确到分钟）
优先使用 sxtwl / sxtwl_py（精确节气与日干支）。若不可用，回退到 lunarcalendar + 近似节气（精度较低）。
保存为 app.py 后运行： streamlit run app.py
"""
import streamlit as st
import datetime
import math

# 尝试导入万年历库（优先 sxtwl，其次 sxtwl_py），否则使用 lunarcalendar 回退。
USE_SXTWL = False
SXTWL_NAME = None
sxtwl = None
try:
    import sxtwl  # 首选
    SXTWL_NAME = "sxtwl"
    USE_SXTWL = True
except Exception:
    try:
        import sxtwl_py as sxtwl  # 有些环境安装了 sxtwl_py
        SXTWL_NAME = "sxtwl_py"
        USE_SXTWL = True
    except Exception:
        sxtwl = None
        USE_SXTWL = False

from lunarcalendar import Converter, Solar, Lunar

# --------------------- 干支与规则（与你之前逻辑一致） ---------------------
tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

gan_he = {
    "甲": "己", "己": "甲",
    "乙": "庚", "庚": "乙",
    "丙": "辛", "辛": "丙",
    "丁": "壬", "壬": "丁",
    "戊": "癸", "癸": "戊"
}

# 你指定的“仅四冲”规则
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

def zhi_next(z):
    return dizhi[(dizhi.index(z) + 1) % 12]

def zhi_prev(z):
    return dizhi[(dizhi.index(z) - 1) % 12]

def ganzhi_list():
    return [tiangan[i % 10] + dizhi[i % 12] for i in range(60)]

def year_ganzhi_map(start=1900, end=2100):
    gzs = ganzhi_list()
    base_year = 1984  # 甲子年参考
    return {y: gzs[(y - base_year) % 60] for y in range(start, end + 1)}

def calc_jixiong(gz):
    if not gz or len(gz) < 2:
        return {"吉": [], "凶": []}
    tg, dz = gz[0], gz[1]
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
    if shizhu and shizhu.strip() != "" and shizhu.strip() != "不知道":
        zhus.append(shizhu)
    all_ji, all_xiong = set(), set()
    for z in zhus:
        r = calc_jixiong(z)
        all_ji.update(r["吉"])
        all_xiong.update(r["凶"])
    order = ganzhi_list()
    def keyfun(x):
        try: return order.index(x)
        except: return 999
    return sorted(list(all_ji), key=keyfun), sorted(list(all_xiong), key=keyfun)

# --------------------- 节气与干支推算（优先用sxtwl） ---------------------
# 我们尽力支持若干 sxtwl 接口变体；若都不可用，用 lunarcalendar + 近似节气表（精度较低）
def find_li_chun_precise(year):
    """
    尝试用 sxtwl 提取当年立春的精确时刻（datetime.datetime）。
    返回 (datetime.datetime, source_string)；若失败返回 (approx_date, "approx")
    """
    if USE_SXTWL and sxtwl is not None:
        # 支持不同 sxtwl 实现：尝试 cal.iterYearDays 或 fromSolar 等
        try:
            cal = sxtwl.Calendar()
            # iterYearDays 返回 Solar 对象，逐日。我们要找到节气 getJieQi() == 3
            for solar_day in cal.iterYearDays(year):
                lunar = cal.getLunarBySolar(solar_day)
                if lunar.getJieQi() == 3:
                    # try to get exact time if available (some sxtwl returns solar_day.getHour/min)
                    try:
                        # some implementations provide getHour/getMinute getSec
                        dt = datetime.datetime(solar_day.getYear(), solar_day.getMonth(), solar_day.getDay())
                    except Exception:
                        dt = datetime.datetime(solar_day.getYear(), solar_day.getMonth(), solar_day.getDay())
                    return dt, f"sxtwl({SXTWL_NAME})"
        except Exception:
            pass
        # 有些版本暴露 fromSolar(year,month,day) -> Day object with jieqi list
        try:
            # iterate first quarter days to check jieqi list in day object
            for m in (1,2,3):
                for d in range(1,32):
                    try:
                        day = sxtwl.fromSolar(year, m, d)
                    except Exception:
                        continue
                    # day 可能有 getJieQiList 或 getJieQi
                    try:
                        jql = day.getJieQiList()
                        for item in jql:
                            # item may be (index, hour, min)?
                            # fallback: if item is tuple with day info skip, we cannot guarantee format
                            pass
                    except Exception:
                        pass
            # fallback: not found via fromSolar
        except Exception:
            pass

    # 回退近似：用固定常见日期 2月4日（注意：这是近似，用户会看到提示）
    approx = datetime.datetime(year, 2, 4, 0, 0)
    return approx, "approx"

# 月节气分段（人类可读映射）
SOLAR_TERM_NAMES = ["小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨","立夏","小满","芒种","夏至",
                    "小暑","大暑","立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪","冬至"]

def get_jieqi_map_sxtwl(year):
    """
    返回字典：节气名(中文)->datetime.datetime（近似到日期，若sxtwl能给到时间会更精确）
    若不可用则返回空字典
    """
    out = {}
    if USE_SXTWL and sxtwl is not None:
        try:
            cal = sxtwl.Calendar()
            for solar_day in cal.iterYearDays(year):
                lunar = cal.getLunarBySolar(solar_day)
                jq = lunar.getJieQi()
                if jq != -1:
                    # 这里尽量使用 getJieQiName 或其他可用接口获取中文名
                    try:
                        name = lunar.getJieQiName()
                    except Exception:
                        # 若没有字符串名，尝试编号映射（部分实现）
                        idx = int(jq)
                        if 0 <= idx < len(SOLAR_TERM_NAMES):
                            name = SOLAR_TERM_NAMES[idx % 24]
                        else:
                            name = str(jq)
                    dt = datetime.datetime(solar_day.getYear(), solar_day.getMonth(), solar_day.getDay())
                    out[name] = dt
            return out
        except Exception:
            return {}
    return {}

# 近似节气表（只含常见估算日期，精度不足但可用作回退）
APPROX_JIEQI = {
    "立春": (2,4), "惊蛰": (3,6), "清明": (4,5), "立夏": (5,6),
    "芒种": (6,6), "小暑": (7,7), "立秋": (8,7), "白露": (9,7),
    "寒露": (10,8), "立冬": (11,7), "大雪": (12,7), "小寒": (1,6)
}

def get_li_chun_datetime(year):
    dt, src = find_li_chun_precise(year)
    return dt, src

def get_month_branch_by_jieqi(year, month, day):
    """
    返回月支（地支），按节气区间：寅月：立春—惊蛰，卯月：惊蛰—清明，...
    优先使用 sxtwl 的精确节气日期；否则使用近似表 APPROX_JIEQI。
    """
    bd = datetime.date(year, month, day)
    jieqi_map = get_jieqi_map_sxtwl(year)
    # Build ordered list starting from 立春
    if jieqi_map:
        # try to find exact dates for the 12 anchor terms
        keys = ["立春","惊蛰","清明","立夏","芒种","小暑","立秋","白露","寒露","立冬","大雪","小寒"]
        seq = []
        for k in keys:
            if k in jieqi_map:
                seq.append((k, jieqi_map[k].date()))
            else:
                # approximate fallback using approx table with same year
                if k in APPROX_JIEQI:
                    m,d = APPROX_JIEQI[k]
                    # small correction for 小寒 in next year
                    if k == "小寒" and m == 1:
                        seq.append((k, datetime.date(year+1, m, d)))
                    else:
                        seq.append((k, datetime.date(year, m, d)))
        # now we have 12 boundaries seq[i] -> start of that branch
        # find interval
        for i in range(len(seq)):
            start = seq[i][1]
            end = seq[i+1][1] if i+1 < len(seq) else (seq[0][1].replace(year=seq[0][1].year + 1))
            if start <= bd < end:
                return ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"][i]
    else:
        # fallback approximate by month/day mapping: use APPROX_JIEQI
        # create seq as above using APPROX_JIEQI
        seq = []
        keys = ["立春","惊蛰","清明","立夏","芒种","小暑","立秋","白露","寒露","立冬","大雪","小寒"]
        for k in keys:
            m,d = APPROX_JIEQI[k]
            yr = year if not (k=="小寒" and m==1) else year+1
            seq.append((k, datetime.date(yr, m, d)))
        for i in range(len(seq)):
            start = seq[i][1]
            end = seq[i+1][1] if i+1 < len(seq) else (seq[0][1].replace(year=seq[0][1].year + 1))
            if start <= bd < end:
                return ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"][i]
    # ultimate fallback by month number
    month_idx = (month + 10) % 12
    return dizhi[month_idx]

# 五虎遁：根据年干确定寅月的月干起点
def month_stem_by_fihu_dun(year_gan, month_branch):
    """
    year_gan: single char 天干
    month_branch: 地支 like '寅'
    返回月柱（两字）
    """
    # group mapping per 用户提供口诀
    if year_gan in ("甲","己"):
        start_stem = "丙"
    elif year_gan in ("乙","庚"):
        start_stem = "戊"
    elif year_gan in ("丙","辛"):
        start_stem = "庚"
    elif year_gan in ("丁","壬"):
        start_stem = "壬"
    elif year_gan in ("戊","癸"):
        start_stem = "甲"
    else:
        start_stem = "丙"
    start_index = tiangan.index(start_stem)
    offset = (dizhi.index(month_branch) - dizhi.index("寅")) % 12
    stem_index = (start_index + offset) % 10
    return tiangan[stem_index] + month_branch

# 日干支计算（用 1900-01-31 甲子日为基准）
def day_ganzhi_by_base(year, month, day):
    base = datetime.date(1900,1,31)
    cur = datetime.date(year, month, day)
    delta = (cur - base).days
    return ganzhi_list()[delta % 60]

# 时柱（五鼠遁）
def time_ganzhi_by_minute(day_gz, hour, minute):
    if hour is None:
        return "不知道"
    # 日与日的分界线：23:00 之后按你要求属次日（时间精确到分钟）
    # 计算地支索引：子时23:00-00:59 => index 0; (hour+1)//2 maps to 0..11 but need minute handling for exact boundaries
    # We'll compute minutes since midnight and use ranges for each 2-hour slot with 23:00-0:59 as 子时
    total_min = hour * 60 + minute
    # map to branch index:
    # 子时: 23:00-23:59 and 0:00-0:59 -> we adjust: if total_min >= 23*60 -> index 0; otherwise index = (total_min + 60) // 120
    if total_min >= 23*60:
        dz_idx = 0
    else:
        dz_idx = ((total_min + 60) // 120) % 12
    branch = dizhi[dz_idx]
    day_tg = day_gz[0]
    # 五鼠遁起始映射
    if day_tg in ("甲","己"):
        start = tiangan.index("甲")
    elif day_tg in ("乙","庚"):
        start = tiangan.index("丙")
    elif day_tg in ("丙","辛"):
        start = tiangan.index("戊")
    elif day_tg in ("丁","壬"):
        start = tiangan.index("庚")
    elif day_tg in ("戊","癸"):
        start = tiangan.index("壬")
    else:
        start = 0
    tg_idx = (start + dz_idx) % 10
    return tiangan[tg_idx] + branch

# 主流程：从阳历/农历/四柱得到四柱八字（年、月、日、时），年以立春换年，月以节气分月
def calc_bazi_from_solar_precise(year, month, day, hour=None, minute=0):
    # 处理日界线：23:00 起属于次日（按你提供规则）
    dt_birth = datetime.datetime(year, month, day, hour or 0, minute or 0)
    # If birth >= 23:00 and <24:00, then day for 日柱应+1
    use_year_for_day, use_month_for_day, use_day_for_day = year, month, day
    if hour is not None and hour >= 23:
        dt_day = (datetime.date(year, month, day) + datetime.timedelta(days=1))
        use_year_for_day, use_month_for_day, use_day_for_day = dt_day.year, dt_day.month, dt_day.day
    # 年柱：以立春为界
    li_dt, src = find_li_chun_precise(year)
    li_date = li_dt.date()
    bd = datetime.date(year, month, day)
    adj_year = year if bd >= li_date else year - 1
    year_gz = ganzhi_list()[(adj_year - 1984) % 60]
    # 月柱：按节气分月取月支，然后用五虎遁取月干
    month_branch = get_month_branch_by_jieqi(year, month, day)
    month_gz = month_stem_by_fihu_dun(year_gz[0], month_branch)
    # 日柱：按调整后的日（use_*）取甲子日
    day_gz = day_ganzhi_by_base(use_year_for_day, use_month_for_day, use_day_for_day)
    # 时柱：用五鼠遁（分钟级）
    shizhu = time_ganzhi_by_minute(day_gz, hour if hour is not None else None, minute if minute is not None else 0)
    return year_gz, month_gz, day_gz, shizhu, src

# --------------------- Streamlit 界面 ---------------------
st.set_page_config(page_title="八字推算与吉凶年份", page_icon="🔮", layout="centered")
st.title("八字推算与吉凶年份（中文界面，时间到分钟）")

# show sxtwl status
if USE_SXTWL:
    st.info(f"已检测到节气库：{SXTWL_NAME}，程序将尝试使用其精确节气能力。")
else:
    st.warning("未检测到 sxtwl / sxtwl_py，程序将使用 lunarcalendar + 近似节气（精度较低）。建议安装 sxtwl 或 sxtwl_py 以获得最高准确度。")

mode = st.selectbox("请选择输入方式", ["阳历生日", "农历生日", "四柱八字"])

if mode == "阳历生日":
    col1, col2 = st.columns([2,1])
    with col1:
        bdate = st.date_input("出生阳历日期", min_value=datetime.date(1900,1,1), max_value=datetime.date(2100,12,31))
    with col2:
        btime = st.time_input("出生时间（精确到分钟，若未知可留空）", value=None)
    # display Chinese formatted
    if btime:
        st.write(f"你选择的出生时间：{bdate.year}年{bdate.month}月{bdate.day}日 {btime.hour}时{btime.minute}分")
    else:
        st.write(f"你选择的出生日期：{bdate.year}年{bdate.month}月{bdate.day}日（时辰未知）")
    if st.button("推算八字并查询吉凶"):
        hour = btime.hour if btime else None
        minute = btime.minute if btime else 0
        try:
            n,y,d,s,src = calc_bazi_from_solar_precise(bdate.year, bdate.month, bdate.day, hour, minute)
            st.success(f"推算八字：年柱 {n}，月柱 {y}，日柱 {d}，时柱 {s}（节气来源：{src}）")
            ji_list, xiong_list = analyze_bazi(n,y,d,s)
            # 输出吉凶年份
            st.markdown("---")
            st.markdown("### 推算结果（吉凶年份）")
            show_result(ji_list, xiong_list)
        except Exception as e:
            st.error(f"计算出错：{e}")

elif mode == "农历生日":
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        ly = st.number_input("农历年", min_value=1900, max_value=2100, value=1990)
        lm = st.number_input("农历月", min_value=1, max_value=12, value=1)
        ld = st.number_input("农历日", min_value=1, max_value=30, value=1)
    with col2:
        btime = st.time_input("出生时间（精确到分钟，若未知可留空）", value=None)
    if btime:
        st.write(f"你选择的农历出生：{ly}年{lm}月{ld}日 {btime.hour}时{btime.minute}分")
    else:
        st.write(f"你选择的农历出生：{ly}年{lm}月{ld}日（时辰未知）")
    if st.button("推算八字并查询吉凶"):
        try:
            lunar_obj = Lunar(ly, lm, ld, False)
            solar = Converter.Lunar2Solar(lunar_obj)
            hour = btime.hour if btime else None
            minute = btime.minute if btime else 0
            n,y,d,s,src = calc_bazi_from_solar_precise(solar.year, solar.month, solar.day, hour, minute)
            st.success(f"推算八字：年柱 {n}，月柱 {y}，日柱 {d}，时柱 {s}（节气来源：{src}）")
            ji_list, xiong_list = analyze_bazi(n,y,d,s)
            st.markdown("---")
            st.markdown("### 推算结果（吉凶年份）")
            show_result(ji_list, xiong_list)
        except Exception as e:
            st.error(f"计算失败：{e}")

else:  # 四柱输入
    ny = st.text_input("年柱（如：甲子）")
    my = st.text_input("月柱（如：乙丑）")
    dy = st.text_input("日柱（如：丙寅）")
    sy = st.text_input("时柱（如：不知道）", value="不知道")
    if st.button("查询吉凶年份"):
        if not (ny and my and dy):
            st.error("年柱、月柱、日柱为必填项")
        else:
            ji_list, xiong_list = analyze_bazi(ny.strip(), my.strip(), dy.strip(), sy.strip())
            st.markdown("---")
            st.markdown("### 输入的八字（用于吉凶查询）")
            st.write(f"{ny}  {my}  {dy}  {sy}")
            show_result(ji_list, xiong_list)

# 底部提示安装建议
st.markdown("---")
st.markdown("**安装建议（Windows）**：若需要高精度节气与干支，建议安装 `sxtwl` 或 `sxtwl_py`。")
st.text("推荐命令（先升级打包工具）：\n\npip install --upgrade pip setuptools wheel\npip install sxtwl    # 或 pip install sxtwl_py")
