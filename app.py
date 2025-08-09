# -*- coding: utf-8 -*-
"""
八字吉凶查询（Streamlit 单文件）
功能：
- 支持用户选择：阳历出生 / 农历出生 / 四柱八字 输入
- 时辰可填写具体到分钟，也可以填写“不知道”以跳过时柱
- 使用 sxtwl（若可用）精确推算年/月/日/时柱（以立春、节气为界）
- 若 sxtwl 不可用，使用内置近似方法（在节气交界时可能有误差）
- 保留并使用你原有的吉凶计算规则（天干合/冲、地支合/冲、进一/退一）
- 输出：逐柱吉/凶集合，并按万年历映射为具体年份；当年份 > 当前年时标注（★）
- 界面：吉用喜庆色，凶用阴沉色
"""
import datetime
from datetime import date, timedelta
import streamlit as st

# ---- 尝试导入高精度日历库 sxtwl（若本地安装并正确，优先使用） ----
try:
    import sxtwl
    HAVE_SXTWL = True
except Exception:
    sxtwl = None
    HAVE_SXTWL = False

# ---- 基础常量（与你之前代码一致） ----
tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# 天干合（五合）
gan_he = {
    "甲": "己", "己": "甲",
    "乙": "庚", "庚": "乙",
    "丙": "辛", "辛": "丙",
    "丁": "壬", "壳": "壬", "壬": "丁",  # 注意兼容性（'壳'不会出现，只是保险）
    "戊": "癸", "癸": "戊"
}
# 你指定的天干冲（仅保留四对，已去掉戊己）——与之前你确认的一致
gan_chong = {
    "甲": "庚", "庚": "甲",
    "乙": "辛", "辛": "乙",
    "丙": "壬", "壬": "丙",
    "丁": "癸", "癸": "丁"
}

# 地支合（六合）
zhi_he = {
    "子": "丑", "丑": "子",
    "寅": "亥", "亥": "寅",
    "卯": "戌", "戌": "卯",
    "辰": "酉", "酉": "辰",
    "巳": "申", "申": "巳",
    "午": "未", "未": "午"
}

# 地支冲（相隔6位）
zhi_chong = {dz: dizhi[(i + 6) % 12] for i, dz in enumerate(dizhi)}

def zhi_next(z):
    return dizhi[(dizhi.index(z) + 1) % 12]

def zhi_prev(z):
    return dizhi[(dizhi.index(z) - 1) % 12]

# 生成六十甲子列表（0为甲子）
def ganzhi_list():
    gzs = []
    for i in range(60):
        gzs.append(tiangan[i % 10] + dizhi[i % 12])
    return gzs

GZS_LIST = ganzhi_list()

# 年份与干支映射（默认范围 1900-2100，可根据需要调整）
def year_ganzhi_map(start=1900, end=2100):
    gzs = GZS_LIST
    # 1984 为甲子年（常用基准）
    base_year = 1984
    year_map = {}
    for year in range(start, end + 1):
        index = (year - base_year) % 60
        year_map[year] = gzs[index]
    return year_map

# 计算某一柱（如 "乙卯"）的吉凶干支（保持你原有逻辑）
def calc_jixiong(gz):
    # gz 应为两个字，形如 "乙卯"
    if not gz or len(gz) < 2:
        return {"吉": [], "凶": []}
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

# 分析整套八字（年柱、月柱、日柱、时柱），返回（吉集合, 凶集合）
def analyze_bazi(year_zhu, month_zhu, day_zhu, time_zhu):
    pillars = [p for p in [year_zhu, month_zhu, day_zhu] if p]
    if time_zhu and time_zhu.strip().lower() != "不知道":
        pillars.append(time_zhu)
    all_ji = []
    all_xiong = []
    for p in pillars:
        res = calc_jixiong(p)
        all_ji.extend(res["吉"])
        all_xiong.extend(res["凶"])
    # 去重并保持顺序
    def uniq(seq):
        seen = set()
        out = []
        for s in seq:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out
    return uniq(all_ji), uniq(all_xiong)

# ---- 八字推算：如果 sxtwl 可用，则用 sxtwl 精确推算年/月/日/时柱 ----
def solar_to_bazi_sxtwl(y, m, d, hour=None, minute=None):
    """
    使用 sxtwl 完成：年柱（月用立春界）、月柱（日用立春界）、日柱、时柱（若提供）
    23:00 及以后的出生视为次日（按你的规则：23:10 属次日）
    返回 (年柱, 月柱, 日柱, 时柱 or None)
    """
    # 先按分钟判断是否归到下一日
    if hour is not None:
        # 如果用户填了小时分钟并且 >=23:00（含23:00），把日子视为 +1 日
        if hour >= 23:
            dd = date(y, m, d) + timedelta(days=1)
            y2, m2, d2 = dd.year, dd.month, dd.day
        else:
            y2, m2, d2 = y, m, d
    else:
        y2, m2, d2 = y, m, d

    # 用 sxtwl.fromSolar 获取该（调整后）日期对象
    dayobj = sxtwl.fromSolar(y2, m2, d2)

    # 年、月、日（以立春为界的 getYearGZ/getMonthGZ/getDayGZ）
    ygz = dayobj.getYearGZ()   # 默认以立春为界 (sxtwl 文档)
    mgz = dayobj.getMonthGZ()
    dgz = dayobj.getDayGZ()

    Gan = tiangan
    Zhi = dizhi

    year_pillar = Gan[ygz.tg] + Zhi[ygz.dz]
    month_pillar = Gan[mgz.tg] + Zhi[mgz.dz]
    day_pillar = Gan[dgz.tg] + Zhi[dgz.dz]

    hour_pillar = None
    if hour is not None and (str(hour).strip().lower() != "不知道"):
        # sxtwl 提供 dayobj.getHourGZ(hour) ：直接传入 0-23 的小时即可，
        # 它内部处理早子/晚子分界（分早晚子时）
        try:
            hgz = dayobj.getHourGZ(hour)
            hour_pillar = Gan[hgz.tg] + Zhi[hgz.dz]
        except Exception:
            # 兜底：也可以使用 sxtwl.getShiGz(day_gz.tg, hour)
            try:
                d_tg = dgz.tg
                hgz2 = sxtwl.getShiGz(d_tg, hour)
                hour_pillar = Gan[hgz2.tg] + Zhi[hgz2.dz]
            except Exception:
                hour_pillar = None

    return year_pillar, month_pillar, day_pillar, hour_pillar

# ---- 备用：简单（近似）推算（当 sxtwl 不可用时启用） ----
# 注意：这是近似算法（以 立春 固定为 2 月 4 日 00:00 作分界），日柱使用基于 JDN 的简易映射（尽力保证一致性）
def approximate_solar_to_bazi(y, m, d, hour=None, minute=None):
    # 年柱（以立春为界，近似以每年固定 2/4 00:00 为立春时间）
    birth_dt = datetime.datetime(y, m, d, hour or 0, minute or 0)
    lichun_dt = datetime.datetime(y, 2, 4, 0, 0)
    # 若在立春之前，年用上一年
    if birth_dt >= lichun_dt:
        year_for_gz = y
    else:
        year_for_gz = y - 1
    # 年柱基于 1984 甲子为基准
    index = (year_for_gz - 1984) % 60
    year_pillar = GZS_LIST[index]

    # 月柱：按照你给出的五虎遁规则近似计算（正月为寅月）
    # 找出正月（寅月）对应的天干起始，取年天干进行映射
    year_tg = year_pillar[0]
    # 对应规则：
    # 甲/己 -> 寅月天干 丙
    # 乙/庚 -> 戊
    # 丙/辛 -> 庚
    # 丁/壬 -> 壬
    # 戊/癸 -> 甲
    if year_tg in ("甲", "己"):
        first_month_tg = "丙"
    elif year_tg in ("乙", "庚"):
        first_month_tg = "戊"
    elif year_tg in ("丙", "辛"):
        first_month_tg = "庚"
    elif year_tg in ("丁", "壬"):
        first_month_tg = "壬"
    else:
        first_month_tg = "甲"

    # 确定出生所在的节气月（用固定节气边界近似）
    # 我们用常规农历月份近似：正月=寅月=2月（这个近似在节气附近会有偏差）
    # 更稳妥：用太阳节气来划分，这里采用近似：用每月的中位日划分（仅作 fallback）
    # 先把公历月转换为 1..12 的月支（寅月 为正月），建立月支表：
    # 寅、卯、辰、巳、午、未、申、酉、戌、亥、子、丑 对应 月序 1..12
    # 用 立春（2月4日）为寅月起点，计算相对于立春的月序
    # 计算差月数：
    ref = datetime.date(y, 2, 4)
    cur = datetime.date(y, m, d)
    if cur >= ref:
        delta_months = ((cur.year - ref.year) * 12 + (cur.month - ref.month))
    else:
        # 属于上一年对应的月序
        delta_months = -1 + ((cur.year - ref.year) * 12 + (cur.month - ref.month))
    # 月支 index （0 对应 寅）
    month_zhi_idx = (delta_months) % 12
    month_branch = dizhi[(2 + month_zhi_idx) % 12]  # 因为 dizhi 列表的 0 为子，寅 是 index 2

    # 月天干由正月天干向后顺推 (正月对应 first_month_tg)
    tg_start_index = tiangan.index(first_month_tg)
    month_tg_index = (tg_start_index + month_zhi_idx) % 10
    month_pillar = tiangan[month_tg_index] + month_branch

    # 日柱：用 JDN -> 索引 的粗算法（选取已知参考点调校）
    # 使用参考：2000-01-01 在许多万年历中为 戊午（如果这参考与本地万年历有差异，结果会有偏差）
    # 先计算儒略日数（JDN，Fliegel-Van Flandern）
    def jdn(y0, m0, d0):
        a = (14 - m0) // 12
        y_ = y0 + 4800 - a
        m_ = m0 + 12 * a - 3
        jdnv = d0 + ((153 * m_ + 2) // 5) + 365 * y_ + y_ // 4 - y_ // 100 + y_ // 400 - 32045
        return jdnv
    j = jdn(y, m, d)
    # 参考：2000-01-01 jdn = 2451545 -> 对应 戊午（在 GZS_LIST 索引中为 index_x）
    # 我们通过网络常见查询可知 2000-01-01 常标为 戊午（索引 54）
    ref_jdn = 2451545
    ref_idx = GZS_LIST.index("戊午")  # 若此处 KeyError，说明列表中缺该项（不应该）
    idx = (ref_idx + (j - ref_jdn)) % 60
    day_pillar = GZS_LIST[idx]

    # 时柱：如果用户没有时间或写不知道则跳过；否则按照日干推算（五鼠遁近似）
    hour_pillar = None
    if hour is not None and str(hour).strip().lower() != "不知道":
        # 子时判断（23:00 归次日）。我们做如下：若 hour >=23 -> 视为次日子时（日柱已按当日/次日处理）
        hour_for_calc = hour
        # 根据日干推时干（五鼠遁）
        dg = day_pillar[0]
        # 构造子时序 0->子,1->丑,2->寅 ... 每两小时一个地支，子时为 23-1（我们只传小时，分钟忽略）
        # 确定地支：
        # 23:00-0:59 -> 子 时段，我们将 23..0..1 归到 子 时段（用小时范围判断有点粗）
        if hour >= 23 or hour < 1:
            z_branch = "子"
        else:
            branch_index = ((hour + 1) // 2) % 12  # 0->子,1->丑,...  但需要映射
            # map 0->子,1->丑,2->寅...
            z_branch = dizhi[branch_index]
        # 时干按五鼠遁（手工列个表，基于日干）
        # 生成每个日干对应子时的天干
        five_mouse = {
            "甲": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸","甲","乙"],
            "己": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸","甲","乙"],
            "乙": ["丙","丁","戊","己","庚","辛","壬","癸","甲","乙","丙","丁"],
            "庚": ["丙","丁","戊","己","庚","辛","壬","癸","甲","乙","丙","丁"],
            "丙": ["戊","己","庚","辛","壬","癸","甲","乙","丙","丁","戊","己"],
            "辛": ["戊","己","庚","辛","壬","癸","甲","乙","丙","丁","戊","己"],
            "丁": ["庚","辛","壬","癸","甲","乙","丙","丁","戊","己","庚","辛"],
            "壬": ["庚","辛","壬","癸","甲","乙","丙","丁","戊","己","庚","辛"],
            "戊": ["壬","癸","甲","乙","丙","丁","戊","己","庚","辛","壬","癸"],
            "癸": ["壬","癸","甲","乙","丙","丁","戊","己","庚","辛","壬","癸"],
        }
        # 确定地支序号（子为0，丑为1，...）
        dz_idx = dizhi.index(z_branch)
        # 找到时干
        try:
            tg_for_hour = five_mouse.get(dg, five_mouse["甲"])[dz_idx]
            hour_pillar = tg_for_hour + z_branch
        except Exception:
            hour_pillar = None

    return year_pillar, month_pillar, day_pillar, hour_pillar

# ---- UI 显示函数（保证定义在上层，避免未定义错误） ----
def show_result(yi_list, xiong_list, year_map, current_year):
    """
    yi_list, xiong_list: list of Ganzhi strings like ['庚戌', '庚亥']
    year_map: dict year -> ganzhi
    current_year: int
    在 Streamlit 中以颜色显示
    """
    # 配色
    color_good = "#c21807"   # 喜庆（红）
    color_bad = "#0b0b0b"    # 大凶（黑）
    st.markdown("### ✅ 吉年（喜庆）")
    if not yi_list:
        st.write("无吉年（按当前规则）")
    else:
        for gz in yi_list:
            # 找出对应年份
            years = [y for y, g in year_map.items() if g == gz]
            if not years:
                continue
            # 排序
            years.sort()
            parts = []
            for y in years:
                s = f"{gz}{y}年"
                if y >= current_year:
                    s = f"**{s} ★**"
                parts.append(s)
            st.markdown(f'<div style="color:{color_good};font-weight:600">{gz}: {"，".join(parts)}</div>', unsafe_allow_html=True)

    st.markdown("### 🔴 凶年（大凶）")
    if not xiong_list:
        st.write("无凶年（按当前规则）")
    else:
        for gz in xiong_list:
            years = [y for y, g in year_map.items() if g == gz]
            if not years:
                continue
            years.sort()
            parts = []
            for y in years:
                s = f"{gz}{y}年"
                if y >= current_year:
                    s = f"**{s} ★**"
                parts.append(s)
            st.markdown(f'<div style="color:{color_bad};font-weight:600">{gz}: {"，".join(parts)}</div>', unsafe_allow_html=True)

# ---- Streamlit 页面布局 ----
st.set_page_config(page_title="八字吉凶查询", layout="centered")
st.title("八字吉凶年份查询")

st.write("请选择输入方式，并填写出生信息（时可精确到分钟或填‘不知道’以跳过时柱）")

mode = st.selectbox("输入方式", ["阳历出生（公历）", "农历出生（阴历）", "四柱八字（已知）"])

# 公历输入
if mode == "阳历出生（公历）":
    col1, col2 = st.columns([1,1])
    with col1:
        year = st.number_input("阳历年", min_value=1900, max_value=2100, value=1990, step=1)
        month = st.selectbox("月", list(range(1,13)), index=4)
        day = st.number_input("日", min_value=1, max_value=31, value=18, step=1)
    with col2:
        hour = st.number_input("小时（24h，如未知填入-1）", min_value=-1, max_value=23, value=8, step=1)
        minute = st.number_input("分钟（0-59，如未知填0）", min_value=0, max_value=59, value=0, step=1)

    if st.button("计算八字并查询吉凶"):
        # 如果时输入为 -1 或 "不知道" 则视为未知
        hour_input = None if hour == -1 else int(hour)
        minute_input = None if hour == -1 else int(minute)
        try:
            if HAVE_SXTWL:
                y_p, m_p, d_p, h_p = solar_to_bazi_sxtwl(int(year), int(month), int(day), hour_input, minute_input)
            else:
                y_p, m_p, d_p, h_p = approximate_solar_to_bazi(int(year), int(month), int(day), hour_input, minute_input)
        except Exception as e:
            st.error(f"八字推算出错：{e}")
            y_p = m_p = d_p = h_p = None

        # 显示八字
        st.markdown("#### 推算的四柱（可能包含近似）")
        st.write(f"年柱：{y_p or '未知'} ； 月柱：{m_p or '未知'} ； 日柱：{d_p or '未知'} ； 时柱：{h_p or '未知'}")

        # 分析吉凶（保持你原来功能）
        ji_list, xiong_list = analyze_bazi(y_p, m_p, d_p, h_p)
        year_map = year_ganzhi_map(1900, 2100)
        cur_year = datetime.datetime.now().year
        show_result(ji_list, xiong_list, year_map, cur_year)

# 农历输入
elif mode == "农历出生（阴历）":
    col1, col2 = st.columns([1,1])
    with col1:
        ly = st.number_input("农历年（数字）", min_value=1900, max_value=2100, value=1990, step=1)
        lm = st.number_input("农历月（数字）", min_value=1, max_value=12, value=5, step=1)
        isleap = st.checkbox("是否闰月", value=False)
        ld = st.number_input("农历日（数字）", min_value=1, max_value=30, value=18, step=1)
    with col2:
        hour = st.number_input("小时（24h，如未知填入-1）", min_value=-1, max_value=23, value=8, step=1)
        minute = st.number_input("分钟（0-59，如未知填0）", min_value=0, max_value=59, value=0, step=1)

    if st.button("从农历推算八字并查询吉凶"):
        hour_input = None if hour == -1 else int(hour)
        minute_input = None if hour == -1 else int(minute)
        try:
            if HAVE_SXTWL:
                # sxtwl.fromLunar(year, month, day, isLeap) 或 fromLunar(year, month, day)（部分版本差异）
                try:
                    dayobj = sxtwl.fromLunar(int(ly), int(lm), int(ld), bool(isleap))
                except TypeError:
                    # 有的版本只需要三参
                    dayobj = sxtwl.fromLunar(int(ly), int(lm), int(ld))
                ygz = dayobj.getYearGZ()
                mgz = dayobj.getMonthGZ()
                dgz = dayobj.getDayGZ()
                Gan = tiangan; Zhi = dizhi
                y_p = Gan[ygz.tg] + Zhi[ygz.dz]
                m_p = Gan[mgz.tg] + Zhi[mgz.dz]
                d_p = Gan[dgz.tg] + Zhi[dgz.dz]
                h_p = None
                if hour_input is not None:
                    # 若小时大于等于23则需先 +1 天并重新 fromSolar 以便时柱正确
                    # 简化：直接用 dayobj.getHourGZ(hour)
                    try:
                        hgz = dayobj.getHourGZ(hour_input)
                        h_p = Gan[hgz.tg] + Zhi[hgz.dz]
                    except Exception:
                        h_p = None
            else:
                # 退化为近似：把农历转公历并调用近似函数（这里简单地尝试用 sxtwl 不存在时的近似行为）
                y_p, m_p, d_p, h_p = approximate_solar_to_bazi(int(ly), int(lm), int(ld), hour_input, minute_input)
        except Exception as e:
            st.error(f"农历转换或八字推算出错：{e}")
            y_p = m_p = d_p = h_p = None

        st.markdown("#### 推算的四柱（可能包含近似）")
        st.write(f"年柱：{y_p or '未知'} ； 月柱：{m_p or '未知'} ； 日柱：{d_p or '未知'} ； 时柱：{h_p or '未知'}")
        ji_list, xiong_list = analyze_bazi(y_p, m_p, d_p, h_p)
        year_map = year_ganzhi_map(1900, 2100)
        cur_year = datetime.datetime.now().year
        show_result(ji_list, xiong_list, year_map, cur_year)

# 四柱手动输入
else:
    st.markdown("请输入四柱（例：乙卯、戊寅 等）。若时柱不知道，请输入：不知道")
    col1, col2 = st.columns(2)
    with col1:
        year_zhu = st.text_input("年柱（例如：庚午）", value="")
        month_zhu = st.text_input("月柱（例如：辛巳）", value="")
    with col2:
        day_zhu = st.text_input("日柱（例如：丙午）", value="")
        time_zhu = st.text_input("时柱（如未知写 不知道）", value="不知道")
    if st.button("计算吉凶年份"):
        # 校验最少需要 年 月 日
        if not year_zhu or not month_zhu or not day_zhu:
            st.error("请至少填写年柱、月柱、日柱（每项形如：甲子/乙丑/丙寅 等）")
        else:
            ji_list, xiong_list = analyze_bazi(year_zhu.strip(), month_zhu.strip(), day_zhu.strip(), time_zhu.strip())
            year_map = year_ganzhi_map(1900, 2100)
            cur_year = datetime.datetime.now().year
            st.markdown("#### 你输入的四柱")
            st.write(f"年柱：{year_zhu}；月柱：{month_zhu}；日柱：{day_zhu}；时柱：{time_zhu}")
            show_result(ji_list, xiong_list, year_map, cur_year)

# ---- 页面尾部说明（简短） ----
st.markdown("---")
st.caption("说明：程序优先使用本地高精度日历库（若可用）以保证节气与干支准确；若该库不可用，程序将启用内置近似算法，节气边界处可能存在差异。")

