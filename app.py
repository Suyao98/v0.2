# -*- coding: utf-8 -*-
"""
Streamlit 八字排盘（完整单文件）
- 月份手动输入（数字）
- 出生时分精确到分钟，支持“时辰未知”
- 日柱使用锚点法（anchor）计算（1984-01-01 甲午）
- 时柱默认使用你提供的五鼠遁规则；可启用 sxtwl（若安装）做对比或覆盖
- 恢复并使用吉凶计算（天干地支合/冲、双合进一/双冲退一）
"""
import datetime
from datetime import date, timedelta
import streamlit as st

# 尝试导入 sxtwl（兼容不同实现），但不依赖于它的特定类名
try:
    import sxtwl
    HAVE_SXTWL = True
except Exception:
    sxtwl = None
    HAVE_SXTWL = False

# ---------- 干支基础数据 ----------
tiangan = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
dizhi = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
GZS_LIST = [tiangan[i%10] + dizhi[i%12] for i in range(60)]

# 天干合（五合）
gan_he = {"甲":"己","己":"甲","乙":"庚","庚":"乙","丙":"辛","辛":"丙","丁":"壬","壬":"丁","戊":"癸","癸":"戊"}
# 仅四冲（用户要求，去掉戊己）
gan_chong = {"甲":"庚","庚":"甲","乙":"辛","辛":"乙","丙":"壬","壬":"丙","丁":"癸","癸":"丁"}
# 地支合（六合）
zhi_he = {"子":"丑","丑":"子","寅":"亥","亥":"寅","卯":"戌","戌":"卯","辰":"酉","酉":"辰","巳":"申","申":"巳","午":"未","未":"午"}
# 地支冲（对冲）
zhi_chong = {dz: dizhi[(i+6)%12] for i, dz in enumerate(dizhi)}

def zhi_next(z): return dizhi[(dizhi.index(z)+1)%12]
def zhi_prev(z): return dizhi[(dizhi.index(z)-1)%12]

def year_ganzhi_map(start=1900, end=2100):
    base_year = 1984
    return {y: GZS_LIST[(y-base_year)%60] for y in range(start, end+1)}

# ---------- 吉凶计算（保持你原规则） ----------
def calc_jixiong(gz):
    if not gz or len(gz) < 2:
        return {"吉": [], "凶": []}
    tg, dz = gz[0], gz[1]
    res = {"吉": [], "凶": []}
    tg_he = gan_he.get(tg, ""); dz_he = zhi_he.get(dz, "")
    tg_ch = gan_chong.get(tg, ""); dz_ch = zhi_chong.get(dz, "")
    if tg_he and dz_he:
        res["吉"].append(tg_he + dz_he)
        res["吉"].append(tg_he + zhi_next(dz_he))
    if tg_ch and dz_ch:
        res["凶"].append(tg_ch + dz_ch)
        res["凶"].append(tg_ch + zhi_prev(dz_ch))
    return res

def analyze_bazi(nianzhu, yuezhu, rizhu, shizhu):
    pillars = [p for p in (nianzhu, yuezhu, rizhu) if p]
    if shizhu and str(shizhu).strip() and str(shizhu).strip() != "不知道":
        pillars.append(shizhu)
    all_ji = []
    all_xiong = []
    for p in pillars:
        r = calc_jixiong(p)
        all_ji.extend(r["吉"]); all_xiong.extend(r["凶"])
    # 去重但保序
    seen = set()
    ji = []
    for s in all_ji:
        if s not in seen:
            seen.add(s); ji.append(s)
    seen = set()
    xiong = []
    for s in all_xiong:
        if s not in seen:
            seen.add(s); xiong.append(s)
    return ji, xiong

# ---------- 日柱（锚点法） ----------
ANCHOR_DATE = date(1984,1,1)
ANCHOR_GZ = "甲午"
ANCHOR_INDEX = GZS_LIST.index(ANCHOR_GZ)

def day_ganzhi_by_anchor(y, m, d, hour=None, minute=None):
    # 23:00 及以后归入次日
    if hour is not None and hour >= 23:
        target = date(y,m,d) + timedelta(days=1)
    else:
        target = date(y,m,d)
    delta = (target - ANCHOR_DATE).days
    idx = (ANCHOR_INDEX + delta) % 60
    return GZS_LIST[idx]

# ---------- 月柱（手动输入优先 / 否则近似节气分月 + 五虎遁） ----------
# 五虎遁起始天干（寅月起点）
def month_stem_by_fihu_dun(year_tg, month_branch):
    if year_tg in ("甲","己"): start = "丙"
    elif year_tg in ("乙","庚"): start = "戊"
    elif year_tg in ("丙","辛"): start = "庚"
    elif year_tg in ("丁","壬"): start = "壬"
    elif year_tg in ("戊","癸"): start = "甲"
    else: start = "丙"
    start_idx = tiangan.index(start)
    offset = (dizhi.index(month_branch) - dizhi.index("寅")) % 12
    stem_idx = (start_idx + offset) % 10
    return tiangan[stem_idx] + month_branch

APPROX_JIEQI = {
    "立春": (2,4), "惊蛰": (3,6), "清明": (4,5), "立夏": (5,6),
    "芒种": (6,6), "小暑": (7,7), "立秋": (8,7), "白露": (9,7),
    "寒露": (10,8), "立冬": (11,7), "大雪": (12,7), "小寒": (1,6)
}
def get_month_branch_approx(year, month, day):
    bd = date(year, month, day)
    keys = ["立春","惊蛰","清明","立夏","芒种","小暑","立秋","白露","寒露","立冬","大雪","小寒"]
    seq=[]
    for k in keys:
        m,d = APPROX_JIEQI[k]
        yr = year if not (k=="小寒" and m==1) else year+1
        seq.append((k, date(yr,m,d)))
    for i in range(len(seq)):
        s = seq[i][1]
        e = seq[i+1][1] if i+1 < len(seq) else seq[0][1].replace(year=seq[0][1].year+1)
        if s <= bd < e:
            return ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"][i]
    return dizhi[(month+10)%12]

# ---------- 时柱（分钟精确） 五鼠遁规则 ----------
# 时辰地支区间（采用说明中的区间）
# 子时：23:00-00:59, 丑:01:00-02:59, 寅:03:00-04:59 ... 以此类推
def get_hour_branch_by_minute(hour, minute):
    if hour is None:
        return None
    tot = hour*60 + (minute or 0)
    # 子时：23:00-23:59 and 0:00-0:59 => we map these to index 0
    if tot >= 23*60 or tot < 1*60:
        return "子", 0
    # else compute ((tot - 60) // 120) -> 0..11 mapping to 丑..亥? We'll just build boundaries:
    intervals = [
        (1*60, 3*60, "丑"),
        (3*60, 5*60, "寅"),
        (5*60, 7*60, "卯"),
        (7*60, 9*60, "辰"),
        (9*60, 11*60, "巳"),
        (11*60, 13*60, "午"),
        (13*60, 15*60, "未"),
        (15*60, 17*60, "申"),
        (17*60, 19*60, "酉"),
        (19*60, 21*60, "戌"),
        (21*60, 23*60, "亥"),
    ]
    for i, (s,e,name) in enumerate(intervals):
        if s <= tot < e:
            return name, i+1  # i+1 because 0 reserved for 子
    return "子", 0

def time_ganzhi_by_rule(day_gz, hour, minute):
    if hour is None:
        return "不知道"
    branch, idx = get_hour_branch_by_minute(hour, minute)
    # day_gz is like '丙午', day_gan = day_gz[0]
    day_gan = day_gz[0]
    # 起始映射（五鼠遁）
    if day_gan in ("甲","己"): start = tiangan.index("甲")
    elif day_gan in ("乙","庚"): start = tiangan.index("丙")
    elif day_gan in ("丙","辛"): start = tiangan.index("戊")
    elif day_gan in ("丁","壬"): start = tiangan.index("庚")
    elif day_gan in ("戊","癸"): start = tiangan.index("壬")
    else: start = 0
    tg_idx = (start + idx) % 10
    return tiangan[tg_idx] + branch

# ---------- sxtwl 兼容性包装（尽力尝试多种api） ----------
def try_sxtwl_from_solar(y,m,d):
    """尝试用 sxtwl 提取 dayobj（返回 None 则不可用）"""
    if not HAVE_SXTWL:
        return None
    # 尝试常见接口 fromSolar
    try:
        if hasattr(sxtwl, "fromSolar"):
            return sxtwl.fromSolar(int(y), int(m), int(d))
    except Exception:
        pass
    # 尝试 Calendar().getLunarBySolar 或 getDayBySolar
    try:
        if hasattr(sxtwl, "Calendar"):
            cal = sxtwl.Calendar()
            # some sxtwl have iterYearDays or getDayBySolar
            if hasattr(cal, "getDayBySolar"):
                try:
                    return cal.getDayBySolar(sxtwl.Solar(int(y), int(m), int(d)))
                except Exception:
                    pass
            if hasattr(cal, "getLunarBySolar"):
                try:
                    return cal.getLunarBySolar(sxtwl.Solar(int(y), int(m), int(d)))
                except Exception:
                    pass
    except Exception:
        pass
    return None

def extract_gz_from_dayobj_day(dayobj):
    """从 dayobj 尝试提取 year/month/day gz（返回 tuple 或 (None,None,None)）"""
    if dayobj is None:
        return None, None, None
    # 尝试 getYearGZ/getMonthGZ/getDayGZ
    def get_gz(fn):
        try:
            val = fn()
            # val 有可能是对象有 .tg/.dz，也可能是 tuple/list
            if hasattr(val, "tg") and hasattr(val, "dz"):
                return tiangan[int(val.tg)] + dizhi[int(val.dz)]
            elif isinstance(val, (list,tuple)) and len(val) >= 2:
                return tiangan[int(val[0])] + dizhi[int(val[1])]
        except Exception:
            pass
        return None
    yg = get_gz(getattr(dayobj, "getYearGZ", lambda: None))
    mg = get_gz(getattr(dayobj, "getMonthGZ", lambda: None))
    dg = get_gz(getattr(dayobj, "getDayGZ", lambda: None))
    return yg, mg, dg

def extract_hour_from_dayobj(dayobj, hour):
    """尝试从 dayobj 中提取时柱，返回字符串或 None"""
    if dayobj is None:
        return None
    # 尝试 dayobj.getHourGZ(hour)
    try:
        if hasattr(dayobj, "getHourGZ"):
            val = dayobj.getHourGZ(int(hour))
            if hasattr(val, "tg") and hasattr(val, "dz"):
                return tiangan[int(val.tg)] + dizhi[int(val.dz)]
            elif isinstance(val, (list,tuple)) and len(val) >=2:
                return tiangan[int(val[0])] + dizhi[int(val[1])]
    except Exception:
        pass
    # 尝试 sxtwl.getShiGz (some libs)
    try:
        if hasattr(sxtwl, "getShiGz"):
            # need day_tg index
            try:
                daygz = extract_gz_from_dayobj_day(dayobj)[2]
                if daygz:
                    day_tg_idx = tiangan.index(daygz[0])
                    val = sxtwl.getShiGz(day_tg_idx, int(hour))
                    if hasattr(val, "tg") and hasattr(val, "dz"):
                        return tiangan[int(val.tg)] + dizhi[int(val.dz)]
                    elif isinstance(val, (list,tuple)) and len(val)>=2:
                        return tiangan[int(val[0])] + dizhi[int(val[1])]
            except Exception:
                pass
    except Exception:
        pass
    return None

# ---------- 合并推算流程 ----------
def calc_bazi(year, month, day, hour=None, minute=None, manual_month_branch=None, use_sxtwl_for_compare=False, prefer_sxtwl=False):
    """
    返回 dict:
    {
      "year": year_pillar,
      "month": month_pillar,
      "day": day_pillar,           # 默认使用锚点法（anchor）
      "hour": hour_pillar,         # 默认使用规则（五鼠遁），但如果 prefer_sxtwl=True 且 sxtwl可用会覆盖
      "sxtwl": {"year":..., "month":..., "day":..., "hour":...}  # 若能从sxtwl提取
      "source": "anchor/approx/sxtwl"  # 简单说明
    }
    """
    res = {"year": None, "month": None, "day": None, "hour": None, "sxtwl": {}, "source": ""}
    # 1) 日柱：采用锚点法（用户要求）
    day_p = day_ganzhi_by_anchor(year, month, day, hour, minute)
    res["day"] = day_p

    # 2) 通过 sxtwl 尝试获取年/月/日/时（用于对比或覆盖）
    s_dayobj = try_sxtwl_from_solar(year, month, day)
    s_year = s_month = s_day = s_hour = None
    if s_dayobj is not None:
        yg, mg, dg = extract_gz_from_dayobj_day(s_dayobj)
        s_year, s_month, s_day = yg, mg, dg
        if hour is not None and hour >= 0:
            s_hour = extract_hour_from_dayobj(s_dayobj, hour)
        res["sxtwl"] = {"year": s_year, "month": s_month, "day": s_day, "hour": s_hour}
    # 3) 年柱、月柱：如果用户手动指定月支（地支），用五虎遁确定月柱；否则优先使用 sxtwl（若有），否则近似
    # 年柱
    if s_year:
        year_p = s_year
        res["source"] += "sxtwl_year;"
    else:
        # 近似年柱，以立春 2/4 作为边界（fallback）
        birth_dt = datetime.datetime(year, month, day, hour or 0, minute or 0)
        lichun = datetime.datetime(year, 2, 4, 0, 0)
        adj_year = year if birth_dt >= lichun else year - 1
        year_p = GZS_LIST[(adj_year - 1984) % 60]
        res["source"] += "approx_year;"
    res["year"] = year_p

    # 月柱
    if manual_month_branch:
        month_p = month_stem_by_fihu_dun(res["year"][0], manual_month_branch)
        res["source"] += "manual_month;"
    else:
        if s_month:
            month_p = s_month
            res["source"] += "sxtwl_month;"
        else:
            # 近似月支 -> 五虎遁
            mb = get_month_branch_approx(year, month, day)
            month_p = month_stem_by_fihu_dun(res["year"][0], mb)
            res["source"] += "approx_month;"
    res["month"] = month_p

    # 时柱：默认用五鼠遁规则
    hour_p_rule = None
    if hour is None or hour < 0:
        hour_p_rule = "不知道"
    else:
        hour_p_rule = time_ganzhi_by_rule(res["day"], hour, minute or 0)
    res["hour_rule"] = hour_p_rule

    # sxtwl hour available?
    hour_p_sxtwl = res["sxtwl"].get("hour") if res.get("sxtwl") else None

    # 决定最终时柱：优先规则（默认）；若 prefer_sxtwl True 并 sxtwl可用则覆盖
    if prefer_sxtwl and hour_p_sxtwl:
        res["hour"] = hour_p_sxtwl
        res["source"] += "sxtwl_hour_used;"
    else:
        res["hour"] = hour_p_rule
        res["source"] += "rule_hour_used;"

    # 日柱：我们以锚点法为主；如果 sxtwl 可用并用户要求对比，则会在界面展示
    res["sxtwl_day"] = res["sxtwl"].get("day")
    return res

# ---------- 输出：漂亮的吉凶显示 ----------
def show_result_beauty(ji_list, xiong_list):
    year_map = year_ganzhi_map(1900,2100)
    cur = datetime.datetime.now().year
    color_good = "#c21807"  # 红
    color_bad = "#333333"   # 深灰
    st.markdown("### 🎉 吉年")
    if not ji_list:
        st.info("无吉年（按当前规则）")
    else:
        for gz in ji_list:
            years = [y for y,g in year_map.items() if g == gz]
            if not years: continue
            years.sort()
            parts=[]
            for y in years:
                s = f"{gz}{y}年"
                if y >= cur:
                    s = f"**{s} ★**"
                parts.append(s)
            st.markdown(f"<div style='color:{color_good};padding:6px;border-left:4px solid {color_good};background:#fff5f5'>{gz}: {'，'.join(parts)}</div>", unsafe_allow_html=True)
    st.markdown("### ☠️ 凶年")
    if not xiong_list:
        st.info("无凶年（按当前规则）")
    else:
        for gz in xiong_list:
            years = [y for y,g in year_map.items() if g == gz]
            if not years: continue
            years.sort()
            parts=[]
            for y in years:
                s = f"{gz}{y}年"
                if y >= cur:
                    s = f"**{s} ★**"
                parts.append(s)
            st.markdown(f"<div style='color:{color_bad};padding:6px;border-left:4px solid {color_bad};background:#fbfbfb'>{gz}: {'，'.join(parts)}</div>", unsafe_allow_html=True)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="八字排盘（精确分钟、锚点日法）", layout="centered")
st.title("八字排盘与吉凶年份查询（中文）")

st.markdown("说明：日柱采用锚点法（1984-01-01 甲午）计算；月可手动指定地支（如你信任人工月支），时柱默认用五鼠遁规则（分钟精确）。可选用本地 sxtwl（若安装）做对比或覆盖时柱。")

mode = st.selectbox("输入方式", ["阳历生日", "农历生日", "四柱八字（手动）"])

use_sxtwl_compare = False
prefer_sxtwl_hour = False
if HAVE_SXTWL:
    use_sxtwl_compare = st.checkbox("启用本地 sxtwl（若可用）进行对比显示（不会默认覆盖结果）", value=False)
    if use_sxtwl_compare:
        prefer_sxtwl_hour = st.checkbox("当 sxtwl 与规则冲突时，是否以 sxtwl 时柱为准？（否则以规则为准）", value=False)

if mode == "阳历生日":
    col1, col2 = st.columns([2,1])
    with col1:
        byear = st.number_input("出生年", min_value=1900, max_value=2100, value=1990, step=1)
        bmonth = st.number_input("出生月（数字）", min_value=1, max_value=12, value=5, step=1)
        bday = st.number_input("出生日", min_value=1, max_value=31, value=18, step=1)
    with col2:
        unknown_time = st.checkbox("时辰未知（勾选则跳过时柱）", value=False)
        if unknown_time:
            bhour = -1
            bmin = 0
        else:
            bhour = st.number_input("小时（0-23）", min_value=0, max_value=23, value=8, step=1)
            bmin = st.number_input("分钟（0-59）", min_value=0, max_value=59, value=0, step=1)
    manual_month = st.checkbox("手动指定月支（地支），如果勾选请在下方输入", value=False)
    manual_branch = None
    if manual_month:
        manual_branch = st.text_input("请输入月支地支（单字，例如：寅、卯、辰）", value="寅")

    if st.button("推算八字并查询吉凶"):
        hour_val = None if bhour == -1 else int(bhour)
        min_val = None if bhour == -1 else int(bmin)
        try:
            result = calc_bazi(int(byear), int(bmonth), int(bday), hour=hour_val, minute=min_val,
                               manual_month_branch=manual_branch, use_sxtwl_for_compare=use_sxtwl_compare,
                               prefer_sxtwl=prefer_sxtwl_hour)
            # 展示结果
            st.markdown("## 推算结果（四柱）")
            st.write(f"年柱：{result['year']} ； 月柱：{result['month']} ； 日柱（锚点法）：{result['day']} ； 时柱：{result['hour']}")
            # 若 sxtwl 有结果并启用对比，显示对比
            if use_sxtwl_compare and result.get("sxtwl"):
                s = result["sxtwl"]
                if any(s.values()):
                    st.markdown("### sxtwl 对比结果（仅供参考）")
                    st.write(f"（sxtwl）年柱：{s.get('year') or '无'} ； 月柱：{s.get('month') or '无'} ； 日柱：{s.get('day') or '无'} ； 时柱：{s.get('hour') or '无'}")
                    if s.get("day") and s.get("day") != result["day"]:
                        st.warning(f"注：sxtwl 日柱为{s.get('day')}，但程序当前以锚点法日柱 {result['day']} 为主。")
            # 吉凶
            ji, xiong = analyze_bazi(result["year"], result["month"], result["day"], result["hour"])
            st.markdown("---")
            show_result_beauty(ji, xiong)
        except Exception as e:
            st.error(f"计算出错：{e}")

elif mode == "农历生日":
    col1, col2 = st.columns([2,1])
    with col1:
        ly = st.number_input("农历年", min_value=1900, max_value=2100, value=1990, step=1)
        lm = st.number_input("农历月（数字）", min_value=1, max_value=12, value=5, step=1)
        isleap = st.checkbox("是否闰月", value=False)
        ld = st.number_input("农历日", min_value=1, max_value=30, value=18, step=1)
    with col2:
        unknown_time = st.checkbox("时辰未知（勾选则跳过时柱）", value=False)
        if unknown_time:
            bhour = -1
            bmin = 0
        else:
            bhour = st.number_input("小时（0-23）", min_value=0, max_value=23, value=8, step=1)
            bmin = st.number_input("分钟（0-59）", min_value=0, max_value=59, value=0, step=1)
    manual_month = st.checkbox("手动指定月支（地支），如果勾选请在下方输入", value=False)
    manual_branch = None
    if manual_month:
        manual_branch = st.text_input("请输入月支地支（单字，例如：寅、卯、辰）", value="寅")

    if st.button("从农历推算并查询"):
        hour_val = None if bhour == -1 else int(bhour)
        min_val = None if bhour == -1 else int(bmin)
        try:
            # 将农历转公历：优先使用 sxtwl.fromLunar（若可用），否则使用 lunarcalendar 作为后备
            solar_y = solar_m = solar_d = None
            if HAVE_SXTWL:
                try:
                    if hasattr(sxtwl, "fromLunar"):
                        try:
                            dayobj = sxtwl.fromLunar(int(ly), int(lm), int(ld), bool(isleap))
                        except TypeError:
                            dayobj = sxtwl.fromLunar(int(ly), int(lm), int(ld))
                        # try to extract solar via dayobj.getSolar() or attributes
                        try:
                            solar = getattr(dayobj, "getSolar", None)
                            if callable(solar):
                                s = dayobj.getSolar()
                                solar_y, solar_m, solar_d = s.getYear(), s.getMonth(), s.getDay()
                        except Exception:
                            solar_y = solar_m = solar_d = None
                except Exception:
                    solar_y = solar_m = solar_d = None
            if solar_y is None:
                # fallback: use lunarcalendar Converter
                from lunarcalendar import Converter, Solar, Lunar
                lunar_obj = Lunar(int(ly), int(lm), int(ld), bool(isleap))
                solar = Converter.Lunar2Solar(lunar_obj)
                solar_y, solar_m, solar_d = solar.year, solar.month, solar.day

            result = calc_bazi(solar_y, solar_m, solar_d, hour=hour_val, minute=min_val,
                               manual_month_branch=manual_branch, use_sxtwl_for_compare=use_sxtwl_compare,
                               prefer_sxtwl=prefer_sxtwl_hour)
            st.markdown("### 推算结果（四柱）")
            st.write(f"对应阳历：{solar_y}年{solar_m}月{solar_d}日")
            st.write(f"年柱：{result['year']} ； 月柱：{result['month']} ； 日柱（锚点法）：{result['day']} ； 时柱：{result['hour']}")
            if use_sxtwl_compare and result.get("sxtwl") and any(result["sxtwl"].values()):
                s = result["sxtwl"]
                st.markdown("#### sxtwl 对比（仅供参考）")
                st.write(f"（sxtwl）年：{s.get('year')}，月：{s.get('month')}，日：{s.get('day')}，时：{s.get('hour')}")
                if s.get("day") and s.get("day") != result["day"]:
                    st.warning(f"注：sxtwl 日柱为 {s.get('day')}，程序以锚点法日柱 {result['day']} 为主。")
            ji, xiong = analyze_bazi(result["year"], result["month"], result["day"], result["hour"])
            st.markdown("---")
            show_result_beauty(ji, xiong)
        except Exception as e:
            st.error(f"转换或计算出错：{e}")

else:  # 四柱手动输入
    st.markdown("请直接输入四柱（例：甲子、乙丑、丙寅）。时柱可填写“不要”或“不要时”或“不知道”以跳过。")
    ny = st.text_input("年柱（如：甲子）", value="")
    my = st.text_input("月柱（如：乙丑）", value="")
    dy = st.text_input("日柱（如：丙寅）", value="")
    sy = st.text_input("时柱（如：不知道）", value="不知道")
    if st.button("计算吉凶"):
        if not (ny and my and dy):
            st.error("请至少填写年柱、月柱、日柱")
        else:
            ji, xiong = analyze_bazi(ny.strip(), my.strip(), dy.strip(), sy.strip())
            st.markdown("### 你输入的四柱")
            st.write(f"{ny}  {my}  {dy}  {sy}")
            st.markdown("---")
            show_result_beauty(ji, xiong)

# 页脚简短提示（不包含安装建议）
st.markdown("---")
st.caption("注：程序默认以锚点日法（日柱）与五鼠遁（时柱规则）为主；若已安装并启用本地 sxtwl，会做并列对比或覆盖（取决于你的选择）。")
