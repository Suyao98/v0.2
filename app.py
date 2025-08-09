# -*- coding: utf-8 -*-
import streamlit as st
import datetime
import sxtwl            # 需要能安装的 sxtwl/wheel
from lunarcalendar import Converter, Solar, Lunar

# ---------------- 基础：天干地支与规则 ----------------
tiangan = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
dizhi = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]

# 天干合（五合）
gan_he = {"甲":"己","己":"甲","乙":"庚","庚":"乙","丙":"辛","辛":"丙","丁":"壬","壬":"丁","戊":"癸","癸":"戊"}
# 天干冲（你之前指定的四冲）
gan_chong = {"甲":"庚","庚":"甲","乙":"辛","辛":"乙","丙":"壬","壬":"丙","丁":"癸","癸":"丁"}

# 地支合（六合）
zhi_he = {"子":"丑","丑":"子","寅":"亥","亥":"寅","卯":"戌","戌":"卯","辰":"酉","酉":"辰","巳":"申","申":"巳","午":"未","未":"午"}
# 地支冲（对冲，间隔6）
zhi_chong = {dz: dizhi[(i+6)%12] for i,dz in enumerate(dizhi)}

def zhi_next(z):
    return dizhi[(dizhi.index(z)+1)%12]
def zhi_prev(z):
    return dizhi[(dizhi.index(z)-1)%12]

def ganzhi_list():
    return [tiangan[i%10] + dizhi[i%12] for i in range(60)]

def year_ganzhi_map(start=1900, end=2100):
    gzs = ganzhi_list()
    base = 1984  # 甲子年参考
    return {y: gzs[(y-base)%60] for y in range(start, end+1)}

# ---------- 吉凶规则（不变） ----------
def calc_jixiong(gz):
    # gz: 两字，如 "乙卯"
    if not gz or len(gz) < 2:
        return {"吉": [], "凶": []}
    tg = gz[0]; dz = gz[1]
    res = {"吉": [], "凶": []}
    tg_he = gan_he.get(tg, "")
    dz_he = zhi_he.get(dz, "")
    tg_ch = gan_chong.get(tg, "")
    dz_ch = zhi_chong.get(dz, "")
    if tg_he and dz_he:
        shuang_he = tg_he + dz_he
        jin_yi = tg_he + zhi_next(dz_he)
        res["吉"].extend([shuang_he, jin_yi])
    if tg_ch and dz_ch:
        shuang_ch = tg_ch + dz_ch
        tui_yi = tg_ch + zhi_prev(dz_ch)
        res["凶"].extend([shuang_ch, tui_yi])
    return res

def analyze_bazi(nianzhu, yuezhu, rizhu, shizhu):
    zhus = [nianzhu, yuezhu, rizhu]
    if shizhu and shizhu.strip() != "" and shizhu.strip() != "不知道":
        zhus.append(shizhu)
    all_ji = set(); all_xiong = set()
    for z in zhus:
        r = calc_jixiong(z)
        all_ji.update(r["吉"])
        all_xiong.update(r["凶"])
    # 返回（按甲子序排序的列表）
    order = ganzhi_list()
    def sort_key(x):
        try:
            return order.index(x)
        except:
            return 999
    return sorted(list(all_ji), key=sort_key), sorted(list(all_xiong), key=sort_key)

# ---------- 立春 & 节气（用 sxtwl 精确节气） ----------
def get_li_chun_date(year):
    """
    用 sxtwl 的 Calendar/iterYearDays 风格接口查找当年立春的阳历日期（精确到日）。
    兼容 sxtwl 各版本：使用 cal.iterYearDays(year) 并用 getLunarBySolar() 判断节气编号。
    """
    cal = sxtwl.Calendar()
    for solar_day in cal.iterYearDays(year):  # 返回 Solar 对象（含年/月/日）
        lunar = cal.getLunarBySolar(solar_day)
        if lunar.getJieQi() == 3:  # 3 = 立春
            return datetime.date(solar_day.getYear(), solar_day.getMonth(), solar_day.getDay())
    # 兜底
    return datetime.date(year, 2, 4)

def get_year_gz_by_li_chun(year, month, day):
    # 以立春为年界
    li = get_li_chun_date(year)
    bd = datetime.date(year, month, day)
    adj_year = year if bd >= li else year - 1
    gzs = ganzhi_list()
    base = 1984
    return gzs[(adj_year - base) % 60]

# 月柱按节气分月（寅月为正月）
# 月支对应区间从你提供的节气表（立春—惊蛰 -> 寅月 ...）
# 我们用 sxtwl 查各节气点并映射
MONTH_SEGMENTS = [
    ("立春","惊蛰","寅"),
    ("惊蛰","清明","卯"),
    ("清明","立夏","辰"),
    ("立夏","芒种","巳"),
    ("芒种","小暑","午"),
    ("小暑","立秋","未"),
    ("立秋","白露","申"),
    ("白露","寒露","酉"),
    ("寒露","立冬","戌"),
    ("立冬","大雪","亥"),
    ("大雪","小寒","子"),
    ("小寒","立春","丑")
]
# 节气名称 => sxtwl 编号（jieQi编号可能依实现不同）
# 下面使用常见编号映射（如sxtwl中：小寒、立春等有固定编号）
# 为保险起见我们使用 cal.getJieQiName() 对比字符串（若不可用则 fallback）
# 使用辅助：给定日期，找它落在哪个节气区间内

def build_jieqi_map_for_year(year):
    cal = sxtwl.Calendar()
    points = {}
    # 遍历一年，收集所有节气日期（取到节气名字）
    for solar_day in cal.iterYearDays(year):
        lunar = cal.getLunarBySolar(solar_day)
        jq = lunar.getJieQi()
        if jq != -1:
            # 尝试获取节气名（有的 sxtwl 版本用 getJieQiName/ getJieQiString 等）
            try:
                name = lunar.getJieQiName()
            except:
                # fallback: map number->name minimal mapping (部分实现可能不提供)
                name = str(jq)
            points[name] = datetime.date(solar_day.getYear(), solar_day.getMonth(), solar_day.getDay())
    return points

def get_month_gz_by_jieqi(year, month, day):
    # 我们先尝试用 sxtwl 找当年主要节气的日期（取到立春、惊蛰、清明...）
    cal = sxtwl.Calendar()
    # 建立节气按日的有序表：用 iterYearDays 来收集节气事件（保序）
    segs = []
    for solar_day in cal.iterYearDays(year):
        lunar = cal.getLunarBySolar(solar_day)
        jq = lunar.getJieQi()
        if jq != -1:
            # 取名字（某些版本支持）
            try:
                name = lunar.getJieQiName()
            except:
                name = str(jq)
            segs.append((name, datetime.date(solar_day.getYear(), solar_day.getMonth(), solar_day.getDay())))
    # 我们需要一个稳定的 mapping，从立春开始按 MONTH_SEGMENTS 顺序确定每段的起止日
    # 为通用性：找出立春日期，然后依次查找后续节气（按年份内出现顺序）
    # 找立春位置：
    idx_li = None
    for i,(n,d) in enumerate(segs):
        # 尝试匹配"立春"或编号3
        if n == "立春" or n == "Li Chun" or n == "lichun" or "3" in str(n):
            idx_li = i
            break
    if idx_li is None:
        # fallback 直接用常规：立春 2月4日
        li_date = datetime.date(year,2,4)
    else:
        li_date = segs[idx_li][1]
    bd = datetime.date(year, month, day)
    # 从立春日期依次判断 bd 在哪一个节气区间内
    # 先收集节气界点从立春开始的12个节气
    boundaries = []
    # We need the sequence: 立春, 惊蛰, 清明, 立夏, 芒种, 小暑, 立秋, 白露, 寒露, 立冬, 大雪, 小寒, (再到立春)
    # We'll try to find these names in segs in order after li_date
    names_target = ["立春","惊蛰","清明","立夏","芒种","小暑","立秋","白露","寒露","立冬","大雪","小寒"]
    # build a list of (name,date) in order starting from li_date
    ordered = []
    for name,date in segs:
        if date >= li_date:
            ordered.append((name,date))
    # if not enough, append next year's early segs by scanning next year as well
    if len(ordered) < 12:
        for solar_day in cal.iterYearDays(year+1):
            lunar = cal.getLunarBySolar(solar_day)
            jq = lunar.getJieQi()
            if jq != -1:
                try:
                    name = lunar.getJieQiName()
                except:
                    name = str(jq)
                ordered.append((name, datetime.date(solar_day.getYear(), solar_day.getMonth(), solar_day.getDay())))
            if len(ordered) >= 24:
                break
    # now try to pick the target sequence in ordered by matching target names in order
    seq_dates = []
    oi = 0
    for tgt in names_target:
        found = False
        while oi < len(ordered):
            nm,dt = ordered[oi]
            oi += 1
            if nm == tgt or tgt in str(nm):
                seq_dates.append((tgt,dt))
                found = True
                break
        if not found:
            # fallback approximate: use expected approximate dates if name not matched
            # we compute approximate by fixed solar approximate table (coarse)
            approx_map = {
                "立春": datetime.date(year,2,4), "惊蛰": datetime.date(year,3,6),
                "清明": datetime.date(year,4,5), "立夏": datetime.date(year,5,6),
                "芒种": datetime.date(year,6,6), "小暑": datetime.date(year,7,7),
                "立秋": datetime.date(year,8,7), "白露": datetime.date(year,9,7),
                "寒露": datetime.date(year,10,8), "立冬": datetime.date(year,11,7),
                "大雪": datetime.date(year,12,7), "小寒": datetime.date(year,1,6)
            }
            seq_dates.append((tgt, approx_map.get(tgt, datetime.date(year,1,1))))
    # Now seq_dates holds 12 boundaries. Determine which interval bd falls into.
    # intervals: [立春, 惊蛰), [惊蛰, 清明), ..., [小寒, next 立春)
    intervals = []
    for i in range(len(seq_dates)):
        start = seq_dates[i][1]
        if i+1 < len(seq_dates):
            end = seq_dates[i+1][1]
        else:
            # next year立春
            end = seq_dates[0][1].replace(year=seq_dates[0][1].year + 1)
        dz = MONTH_SEGMENTS[i][2]  # the mapped branch
        intervals.append((start,end,dz))
    # find interval where bd in [start, end)
    for start,end,dz in intervals:
        if start <= bd < end:
            branch = dz
            break
    else:
        # fallback: if not matched (edge cases), choose based on month approximate
        branch = dizhi[(month+10)%12]  # crude fallback
    # now compute month stem (五虎遁)
    year_gz = get_year_gz_by_li_chun(year, month, day)
    yg = year_gz[0]
    yg_group = None
    if yg in ("甲","己"):
        yg_group = 0  # 启丙
    elif yg in ("乙","庚"):
        yg_group = 1  # 启戊
    elif yg in ("丙","辛"):
        yg_group = 2  # 启庚
    elif yg in ("丁","壬"):
        yg_group = 3  # 启壬
    elif yg in ("戊","癸"):
        yg_group = 4  # 启甲
    # find month offset (0 for 寅月)
    branch_index = dizhi.index(branch)
    month_offset = (branch_index - dizhi.index("寅")) % 12
    # month stem start map per group (index of first stem for 寅月)
    start_stem_map = [tiangan.index("丙"), tiangan.index("戊"), tiangan.index("庚"), tiangan.index("壬"), tiangan.index("甲")]
    stem_index = (start_stem_map[yg_group] + month_offset) % 10
    month_gz = tiangan[stem_index] + branch
    return month_gz

# ---------- 日柱、时柱 ----------
def get_day_ganzhi_by_table(year, month, day, hour):
    # 使用公认的甲子日基准 1900-01-31 为 甲子日
    base = datetime.date(1900,1,31)
    cur = datetime.date(year,month,day)
    delta = (cur - base).days
    gz = ganzhi_list()[delta % 60]
    # 日界线规则：23:00 起属于次日（即 23:00+ 为次日），实现时会在主流程中判断
    return gz

def get_time_ganzhi_by_wu_shu_dun(day_gz, hour):
    # hour: 0-23; 若未知或 -1 返回 "不知道"
    if hour is None or hour < 0 or hour > 23:
        return "不知道"
    # 地支按2小时分：子 23-0..1, 取映射 (hour + 1)//2
    dz_idx = ((hour + 1) // 2) % 12
    dz = dizhi[dz_idx]
    # 五鼠遁计算时干：按日干分组
    day_tg = day_gz[0]
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
    return tiangan[tg_idx] + dz

# ---------- 八字推算主流程 ----------
def calc_bazi_from_solar(year, month, day, hour):
    # 先处理日界线：23:00-23:59 属次日（按你提供规则）
    # 如果出生时间在 23:00~23:59，则日柱为次日
    if hour is not None and hour >= 23:
        d_for_day = datetime.date(year, month, day) + datetime.timedelta(days=1)
        y2,m2,d2 = d_for_day.year, d_for_day.month, d_for_day.day
    else:
        y2,m2,d2 = year,month,day
    # 年柱按立春换年
    nianzhu = get_year_gz_by_li_chun(year, month, day)
    # 月柱按节气分月（寅月起）
    yuezhu = get_month_gz_by_jieqi(year, month, day)
    # 日柱
    rizhu = get_day_ganzhi_by_table(y2,m2,d2,hour)
    # 时柱
    shizhu = get_time_ganzhi_by_wu_shu_dun(rizhu, hour)
    return nianzhu, yuezhu, rizhu, shizhu

# ---------- 显示与 UI ----------
def show_result(ji_list, xiong_list):
    current = datetime.datetime.now().year
    st.subheader("🎉 吉年（红色为吉，当前及以后年份加★）")
    ygmap = year_ganzhi_map(1900,2100)
    for gz in ji_list:
        years = [y for y,g in ygmap.items() if g == gz]
        if years:
            parts = []
            for y in sorted(years):
                if y >= current:
                    parts.append(f"<span style='color:#d6336c;font-weight:bold'>{gz}{y}年★</span>")
                else:
                    parts.append(f"{gz}{y}年")
            st.markdown(", ".join(parts), unsafe_allow_html=True)
    st.subheader("☠️ 凶年（暗色为凶，当前及以后年份加★）")
    for gz in xiong_list:
        years = [y for y,g in ygmap.items() if g == gz]
        if years:
            parts = []
            for y in sorted(years):
                if y >= current:
                    parts.append(f"<span style='color:#333;font-weight:bold'>{gz}{y}年★</span>")
                else:
                    parts.append(f"{gz}{y}年")
            st.markdown(", ".join(parts), unsafe_allow_html=True)

# ---------- Streamlit 界面 ----------
st.title("八字推算（立春分年 + 节气分月）并输出吉凶年份")

mode = st.radio("选择输入方式", ["阳历生日", "农历生日", "四柱八字"])

if mode == "阳历生日":
    bdate = st.date_input("出生阳历日期", min_value=datetime.date(1900,1,1), max_value=datetime.date(2100,12,31))
    bhour = st.slider("出生小时（整点，0-23；未知请选 -1）", -1, 23, -1)
    if st.button("推算八字并查询"):
        hour = bhour if bhour >=0 else None
        try:
            n,y,m,s = calc_bazi_from_solar(bdate.year, bdate.month, bdate.day, hour)
            st.write(f"八字：{n}年 {y}月 {m}日 {s}时")
            ji,x = analyze_bazi(n,y,m,s)
            show_result(ji,x)
        except Exception as e:
            st.error(f"计算出错：{e}")

elif mode == "农历生日":
    ly = st.number_input("农历年", min_value=1900, max_value=2100, value=1990)
    lm = st.number_input("农历月", min_value=1, max_value=12, value=1)
    ld = st.number_input("农历日", min_value=1, max_value=30, value=1)
    bhour = st.slider("出生小时（未知请选 -1）", -1, 23, -1)
    if st.button("推算八字并查询"):
        try:
            lunar = Lunar(ly, lm, ld, False)
            solar = Converter.Lunar2Solar(lunar)
            hour = bhour if bhour>=0 else None
            n,y,m,s = calc_bazi_from_solar(solar.year, solar.month, solar.day, hour)
            st.write(f"八字：{n}年 {y}月 {m}日 {s}时")
            ji,x = analyze_bazi(n,y,m,s)
            show_result(ji,x)
        except Exception as e:
            st.error(f"计算出错：{e}")

else:  # 四柱输入
    ny = st.text_input("年柱（如 甲子）")
    my = st.text_input("月柱（如 乙丑）")
    dy = st.text_input("日柱（如 丙寅）")
    sy = st.text_input("时柱（如 不知道）", value="不知道")
    if st.button("查询"):
        if not (ny and my and dy):
            st.error("年/月/日柱必须填写")
        else:
            ji,x = analyze_bazi(ny.strip(), my.strip(), dy.strip(), sy.strip())
            st.write(f"八字：{ny} {my} {dy} {sy}")
            show_result(ji,x)
