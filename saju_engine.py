"""
사주(四柱) 계산 엔진
- 년주/월주/일주/시주 계산
- 오행 분석 및 용신 판단
"""

from datetime import date, datetime

# ─── 천간(天干) 10자 ───
CHEONGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
CHEONGAN_KR = ['갑', '을', '병', '정', '무', '기', '경', '신', '임', '계']
CHEONGAN_OHAENG = ['木', '木', '火', '火', '土', '土', '金', '金', '水', '水']
CHEONGAN_EUMYANG = ['양', '음', '양', '음', '양', '음', '양', '음', '양', '음']

# ─── 지지(地支) 12자 ───
JIJI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
JIJI_KR = ['자', '축', '인', '묘', '진', '사', '오', '미', '신', '유', '술', '해']
JIJI_OHAENG = ['水', '土', '木', '木', '土', '火', '火', '土', '金', '金', '土', '水']
JIJI_EUMYANG = ['양', '음', '양', '음', '양', '음', '양', '음', '양', '음', '양', '음']
JIJI_ANIMAL = ['쥐', '소', '호랑이', '토끼', '용', '뱀', '말', '양', '원숭이', '닭', '개', '돼지']

# ─── 지지 장간(藏干) ───
JIJI_JANGGAN = {
    '子': ['癸'],
    '丑': ['己', '癸', '辛'],
    '寅': ['甲', '丙', '戊'],
    '卯': ['乙'],
    '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '庚', '戊'],
    '午': ['丁', '己'],
    '未': ['己', '丁', '乙'],
    '申': ['庚', '壬', '戊'],
    '酉': ['辛'],
    '戌': ['戊', '辛', '丁'],
    '亥': ['壬', '甲']
}

# ─── 오행 상생/상극 ───
OHAENG_LIST = ['木', '火', '土', '金', '水']
OHAENG_KR = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
OHAENG_SANGSAENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}  # 생하는 관계
OHAENG_SANGGEUK = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}  # 극하는 관계

# ─── 지지 충(沖) 관계 ───
JIJI_CHUNG = {
    '子': '午', '午': '子', '丑': '未', '未': '丑', '寅': '申', '申': '寅',
    '卯': '酉', '酉': '卯', '辰': '戌', '戌': '辰', '巳': '亥', '亥': '巳'
}

# 지지를 부수/구성요소로 포함하는 한자 매핑 (작명에서 충 회피 대상)
JIJI_RELATED_HANJA = {
    '子': ['子', '孑', '孜', '字', '孝', '孟', '季', '孫', '學'],
    '午': ['午', '許', '杵'],
    '丑': ['丑', '紐'],
    '未': ['未', '味', '妹', '昧'],
    '寅': ['寅', '演', '瀕'],
    '申': ['申', '伸', '紳', '呻', '神'],
    '卯': ['卯', '柳', '貿'],
    '酉': ['酉', '酒', '醉', '配', '醒'],
    '辰': ['辰', '振', '晨', '辱'],
    '戌': ['戌', '成', '城', '誠', '盛'],
    '巳': ['巳', '祀', '包'],
    '亥': ['亥', '核', '該', '骸'],
}


# ─── 지지 형(刑) 관계 ───
JIJI_HYEONG = {
    '寅': ['巳', '申'],  # 무은지형 (삼형)
    '巳': ['寅', '申'],
    '申': ['寅', '巳'],
    '丑': ['戌', '未'],  # 지세지형 (삼형)
    '戌': ['丑', '未'],
    '未': ['丑', '戌'],
    '子': ['卯'],         # 무례지형
    '卯': ['子'],
    '辰': ['辰'],         # 자형
    '午': ['午'],
    '酉': ['酉'],
    '亥': ['亥'],
}


def check_chung_conflict(day_branch, hanja_list):
    """
    사주 일주 지지와 충이 되는 한자 검출
    day_branch: 일주 지지 (예: '午')
    hanja_list: 이름 한자 리스트
    Returns: 충 경고 메시지 리스트
    """
    if not day_branch or day_branch not in JIJI_CHUNG:
        return []

    chung_branch = JIJI_CHUNG[day_branch]
    conflict_chars = set(JIJI_RELATED_HANJA.get(chung_branch, [chung_branch]))

    warnings = []
    for hanja in hanja_list:
        if hanja in conflict_chars:
            warnings.append(
                f"'{hanja}'은(는) 일주 {day_branch}와 충(沖)인 {chung_branch} 관련 한자입니다"
            )
    return warnings


def check_hyeong_conflict(day_branch, hanja_list):
    """
    사주 일주 지지와 형(刑)이 되는 한자 검출
    day_branch: 일주 지지 (예: '寅')
    hanja_list: 이름 한자 리스트
    Returns: 형 경고 메시지 리스트
    """
    if not day_branch or day_branch not in JIJI_HYEONG:
        return []

    hyeong_branches = JIJI_HYEONG[day_branch]
    conflict_chars = set()
    for hb in hyeong_branches:
        conflict_chars.update(JIJI_RELATED_HANJA.get(hb, [hb]))

    warnings = []
    for hanja in hanja_list:
        if hanja in conflict_chars:
            for hb in hyeong_branches:
                related = set(JIJI_RELATED_HANJA.get(hb, [hb]))
                if hanja in related:
                    warnings.append(
                        f"'{hanja}'은(는) 일주 {day_branch}와 형(刑)인 {hb} 관련 한자입니다"
                    )
                    break
    return warnings


# ─── 절기 계산 (寿星공식 기반) ───
# 12절기 C 상수: (양력 월, 21세기 C값, 20세기 C값)
# 사주의 월 경계가 되는 12절기만 정의 (중기 제외)
_JEOLGI_C = [
    # (양력월, C_21세기, C_20세기) - 사주월 순서
    (2, 3.87, 4.6295),     # 입춘 → 寅月(1)
    (3, 5.63, 6.3826),     # 경칩 → 卯月(2)
    (4, 4.81, 5.5918),     # 청명 → 辰月(3)
    (5, 5.52, 6.318),      # 입하 → 巳月(4)
    (6, 5.678, 6.5),       # 망종 → 午月(5)
    (7, 7.108, 7.928),     # 소서 → 未月(6)
    (8, 7.5, 8.35),        # 입추 → 申月(7)
    (9, 7.646, 8.44),      # 백로 → 酉月(8)
    (10, 8.318, 9.098),    # 한로 → 戌月(9)
    (11, 7.438, 8.218),    # 입동 → 亥月(10)
    (12, 7.18, 7.9),       # 대설 → 子月(11)
    (1, 5.4055, 6.11),     # 소한 → 丑月(12)
]


def _calc_jeolgi_day(year, solar_month, c_21, c_20):
    """寿星공식으로 절기 날짜 계산 (해당 월의 일)"""
    y = year % 100
    c = c_21 if year >= 2000 else c_20
    day = int(c + 0.2422 * y - int(y / 4))
    return day


def get_jeolgi_date(year, jeolgi_index):
    """특정 년도의 절기 날짜 반환 (월, 일). jeolgi_index: 0=입춘, ..., 11=소한"""
    solar_month, c_21, c_20 = _JEOLGI_C[jeolgi_index]
    day = _calc_jeolgi_day(year, solar_month, c_21, c_20)
    return solar_month, day


def calc_jdn(year, month, day):
    """줄리안 일수(Julian Day Number) 계산"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def get_saju_month(solar_year, solar_month, solar_day):
    """절기 기준 사주 월 계산 (1~12, 寅월=1). 寿星공식으로 연도별 절기일 계산."""
    # 입춘 기준 사주 년도
    ipchun_m, ipchun_d = get_jeolgi_date(solar_year, 0)  # 입춘
    if solar_month < ipchun_m or (solar_month == ipchun_m and solar_day < ipchun_d):
        adj_year = solar_year - 1
    else:
        adj_year = solar_year

    # 연도가 바뀐 경우 (1월~입춘 전): 대설~소한 경계만 판단
    if adj_year < solar_year:
        sohan_m, sohan_d = get_jeolgi_date(solar_year, 11)  # 올해 소한 (1월)
        if solar_month > sohan_m or (solar_month == sohan_m and solar_day >= sohan_d):
            return 12  # 丑月 (소한 이후 ~ 입춘 전)
        else:
            return 11  # 子月 (대설 이후 ~ 소한 전)

    # 같은 해: 대설(index=10)부터 입춘(index=0)까지 역순 검사
    for i in range(10, -1, -1):  # 10=대설(子月=11) down to 0=입춘(寅月=1)
        jm, jd = get_jeolgi_date(adj_year, i)
        if solar_month > jm or (solar_month == jm and solar_day >= jd):
            return i + 1  # 1=寅, 2=卯, ..., 11=子

    # 12월인데 대설 전 → 亥月(10), 그 외 fallback
    return 12


def get_saju_year_stem_branch(solar_year, solar_month, solar_day):
    """절기 기준 사주 년도 (입춘 전이면 전년도)"""
    ipchun_m, ipchun_d = get_jeolgi_date(solar_year, 0)
    if solar_month < ipchun_m or (solar_month == ipchun_m and solar_day < ipchun_d):
        return solar_year - 1
    return solar_year


def hour_to_branch_index(hour, minute=0):
    """시간을 지지 인덱스로 변환"""
    total_minutes = hour * 60 + minute
    if total_minutes >= 23 * 60 or total_minutes < 1 * 60:
        return 0   # 子 (23:00-01:00)
    elif total_minutes < 3 * 60:
        return 1   # 丑
    elif total_minutes < 5 * 60:
        return 2   # 寅
    elif total_minutes < 7 * 60:
        return 3   # 卯
    elif total_minutes < 9 * 60:
        return 4   # 辰
    elif total_minutes < 11 * 60:
        return 5   # 巳
    elif total_minutes < 13 * 60:
        return 6   # 午
    elif total_minutes < 15 * 60:
        return 7   # 未
    elif total_minutes < 17 * 60:
        return 8   # 申
    elif total_minutes < 19 * 60:
        return 9   # 酉
    elif total_minutes < 21 * 60:
        return 10  # 戌
    else:
        return 11  # 亥


def calculate_saju(birth_year, birth_month, birth_day, birth_hour=None, birth_minute=0):
    """
    사주팔자 계산
    Returns: dict with 년주, 월주, 일주, 시주 and 오행 분석
    """
    # ─── 년주 (Year Pillar) ───
    saju_year = get_saju_year_stem_branch(birth_year, birth_month, birth_day)
    year_ganji_idx = (saju_year - 4) % 60
    year_stem_idx = year_ganji_idx % 10
    year_branch_idx = year_ganji_idx % 12

    # ─── 월주 (Month Pillar) ───
    saju_month = get_saju_month(birth_year, birth_month, birth_day)
    # 월간 시작 인덱스 계산
    month_stem_start = ((year_stem_idx % 5) * 2 + 2) % 10
    month_stem_idx = (month_stem_start + saju_month - 1) % 10
    month_branch_idx = (saju_month + 1) % 12  # 寅(2)=1월

    # ─── 일주 (Day Pillar) ───
    jdn = calc_jdn(birth_year, birth_month, birth_day)
    day_ganji_idx = (jdn - 2451545 + 54) % 60
    day_stem_idx = day_ganji_idx % 10
    day_branch_idx = day_ganji_idx % 12

    # ─── 시주 (Hour Pillar) ───
    has_hour = birth_hour is not None
    if has_hour:
        hour_branch_idx = hour_to_branch_index(birth_hour, birth_minute)
        hour_stem_start = (day_stem_idx % 5) * 2
        hour_stem_idx = (hour_stem_start + hour_branch_idx) % 10
    else:
        hour_branch_idx = None
        hour_stem_idx = None

    # ─── 결과 구성 ───
    result = {
        'year_pillar': {
            'stem': CHEONGAN[year_stem_idx],
            'branch': JIJI[year_branch_idx],
            'stem_kr': CHEONGAN_KR[year_stem_idx],
            'branch_kr': JIJI_KR[year_branch_idx],
            'stem_ohaeng': CHEONGAN_OHAENG[year_stem_idx],
            'branch_ohaeng': JIJI_OHAENG[year_branch_idx],
            'stem_eumyang': CHEONGAN_EUMYANG[year_stem_idx],
            'branch_eumyang': JIJI_EUMYANG[year_branch_idx],
            'ganji': CHEONGAN[year_stem_idx] + JIJI[year_branch_idx],
            'ganji_kr': CHEONGAN_KR[year_stem_idx] + JIJI_KR[year_branch_idx],
            'animal': JIJI_ANIMAL[year_branch_idx],
        },
        'month_pillar': {
            'stem': CHEONGAN[month_stem_idx],
            'branch': JIJI[month_branch_idx],
            'stem_kr': CHEONGAN_KR[month_stem_idx],
            'branch_kr': JIJI_KR[month_branch_idx],
            'stem_ohaeng': CHEONGAN_OHAENG[month_stem_idx],
            'branch_ohaeng': JIJI_OHAENG[month_branch_idx],
            'stem_eumyang': CHEONGAN_EUMYANG[month_stem_idx],
            'branch_eumyang': JIJI_EUMYANG[month_branch_idx],
            'ganji': CHEONGAN[month_stem_idx] + JIJI[month_branch_idx],
            'ganji_kr': CHEONGAN_KR[month_stem_idx] + JIJI_KR[month_branch_idx],
        },
        'day_pillar': {
            'stem': CHEONGAN[day_stem_idx],
            'branch': JIJI[day_branch_idx],
            'stem_kr': CHEONGAN_KR[day_stem_idx],
            'branch_kr': JIJI_KR[day_branch_idx],
            'stem_ohaeng': CHEONGAN_OHAENG[day_stem_idx],
            'branch_ohaeng': JIJI_OHAENG[day_branch_idx],
            'stem_eumyang': CHEONGAN_EUMYANG[day_stem_idx],
            'branch_eumyang': JIJI_EUMYANG[day_branch_idx],
            'ganji': CHEONGAN[day_stem_idx] + JIJI[day_branch_idx],
            'ganji_kr': CHEONGAN_KR[day_stem_idx] + JIJI_KR[day_branch_idx],
        },
        'hour_pillar': None,
        'day_stem_idx': day_stem_idx,
    }

    if has_hour:
        result['hour_pillar'] = {
            'stem': CHEONGAN[hour_stem_idx],
            'branch': JIJI[hour_branch_idx],
            'stem_kr': CHEONGAN_KR[hour_stem_idx],
            'branch_kr': JIJI_KR[hour_branch_idx],
            'stem_ohaeng': CHEONGAN_OHAENG[hour_stem_idx],
            'branch_ohaeng': JIJI_OHAENG[hour_branch_idx],
            'stem_eumyang': CHEONGAN_EUMYANG[hour_stem_idx],
            'branch_eumyang': JIJI_EUMYANG[hour_branch_idx],
            'ganji': CHEONGAN[hour_stem_idx] + JIJI[hour_branch_idx],
            'ganji_kr': CHEONGAN_KR[hour_stem_idx] + JIJI_KR[hour_branch_idx],
        }

    # ─── 오행 분석 ───
    ohaeng_count = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    eumyang_count = {'양': 0, '음': 0}

    pillars = ['year_pillar', 'month_pillar', 'day_pillar']
    if has_hour:
        pillars.append('hour_pillar')

    for p_name in pillars:
        p = result[p_name]
        ohaeng_count[p['stem_ohaeng']] += 1
        ohaeng_count[p['branch_ohaeng']] += 1
        eumyang_count[p['stem_eumyang']] += 1
        eumyang_count[p['branch_eumyang']] += 1

    # 장간 분석
    janggan_ohaeng = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}
    for p_name in pillars:
        p = result[p_name]
        branch = p['branch']
        for jg_stem in JIJI_JANGGAN.get(branch, []):
            jg_idx = CHEONGAN.index(jg_stem)
            janggan_ohaeng[CHEONGAN_OHAENG[jg_idx]] += 1

    # ─── 일간(日干) 분석 ───
    ilgan = CHEONGAN[day_stem_idx]
    ilgan_ohaeng = CHEONGAN_OHAENG[day_stem_idx]

    # ─── 용신(用神) 판단 ───
    yongsin_info = determine_yongsin(ilgan_ohaeng, ohaeng_count, janggan_ohaeng)

    result['ohaeng_analysis'] = {
        'count': ohaeng_count,
        'janggan_count': janggan_ohaeng,
        'eumyang_count': eumyang_count,
        'ilgan': ilgan,
        'ilgan_kr': CHEONGAN_KR[day_stem_idx],
        'ilgan_ohaeng': ilgan_ohaeng,
        'ilgan_ohaeng_kr': OHAENG_KR[ilgan_ohaeng],
        'yongsin': yongsin_info,
    }

    return result


def determine_yongsin(ilgan_ohaeng, ohaeng_count, janggan_count):
    """
    용신(用神) 판단 - 일간의 강약에 따라 필요한 오행 결정

    일간이 강하면: 설기(泄氣), 극(剋) 하는 오행이 용신
    일간이 약하면: 생(生), 같은 오행이 용신
    """
    # 일간의 강도 계산
    same_element = ilgan_ohaeng
    generating_element = None  # 일간을 생하는 오행
    for k, v in OHAENG_SANGSAENG.items():
        if v == ilgan_ohaeng:
            generating_element = k
            break

    # 일간 지지력 = 같은 오행 + 생해주는 오행
    support_score = ohaeng_count.get(same_element, 0) + janggan_count.get(same_element, 0)
    if generating_element:
        support_score += ohaeng_count.get(generating_element, 0) * 0.7 + janggan_count.get(generating_element, 0) * 0.5

    # 일간 억제력 = 극하는 오행 + 설기하는 오행 + 극받는 오행
    controlled_element = OHAENG_SANGSAENG[ilgan_ohaeng]  # 일간이 생하는 오행 (설기)
    controlling_element = OHAENG_SANGGEUK[ilgan_ohaeng]   # 일간이 극하는 오행
    controlled_by = None  # 일간을 극하는 오행
    for k, v in OHAENG_SANGGEUK.items():
        if v == ilgan_ohaeng:
            controlled_by = k
            break

    oppose_score = ohaeng_count.get(controlled_element, 0) + ohaeng_count.get(controlling_element, 0)
    if controlled_by:
        oppose_score += ohaeng_count.get(controlled_by, 0)

    total = sum(ohaeng_count.values())
    is_strong = support_score > total * 0.4

    # 부족한 오행 찾기
    missing = [oh for oh in OHAENG_LIST if ohaeng_count[oh] == 0]
    weakest = sorted(OHAENG_LIST, key=lambda x: ohaeng_count[x] + janggan_count.get(x, 0) * 0.5)

    if is_strong:
        # 일간이 강할 때: 설기(泄氣)하는 오행 또는 극하는 오행
        yongsin = controlled_element  # 일간이 생하는 오행 (에너지 발산)
        huisin = controlling_element  # 일간이 극하는 오행
        description = "일간이 강하여 에너지를 분산시켜주는 오행이 필요합니다"
    else:
        # 일간이 약할 때: 같은 오행 또는 생해주는 오행
        yongsin = same_element
        huisin = generating_element
        description = "일간이 약하여 힘을 보태주는 오행이 필요합니다"

    # 부족 오행을 우선 고려
    needed_ohaeng = []
    if missing:
        for m in missing:
            if m == yongsin or m == huisin:
                needed_ohaeng.insert(0, m)
            else:
                needed_ohaeng.append(m)
    if yongsin not in needed_ohaeng:
        needed_ohaeng.insert(0, yongsin)
    if huisin and huisin not in needed_ohaeng:
        needed_ohaeng.insert(1, huisin)

    return {
        'yongsin': yongsin,
        'yongsin_kr': OHAENG_KR[yongsin],
        'huisin': huisin,
        'huisin_kr': OHAENG_KR.get(huisin, ''),
        'is_strong': is_strong,
        'strength_desc': '신강(身强)' if is_strong else '신약(身弱)',
        'description': description,
        'missing_ohaeng': missing,
        'missing_ohaeng_kr': [OHAENG_KR[m] for m in missing],
        'needed_ohaeng': needed_ohaeng[:3],  # 상위 3개 필요 오행
        'needed_ohaeng_kr': [OHAENG_KR[n] for n in needed_ohaeng[:3]],
        'weakest': weakest[:2],
        'weakest_kr': [OHAENG_KR[w] for w in weakest[:2]],
    }


def format_saju_summary(saju_result):
    """사주 결과를 텍스트 요약으로 반환"""
    r = saju_result
    oa = r['ohaeng_analysis']

    lines = []
    lines.append("═══ 사주팔자(四柱八字) ═══")
    lines.append("")

    # 사주 표
    lines.append(f"  시주    일주    월주    년주")
    if r['hour_pillar']:
        lines.append(f"  {r['hour_pillar']['stem']}      {r['day_pillar']['stem']}      {r['month_pillar']['stem']}      {r['year_pillar']['stem']}")
        lines.append(f"  {r['hour_pillar']['branch']}      {r['day_pillar']['branch']}      {r['month_pillar']['branch']}      {r['year_pillar']['branch']}")
    else:
        lines.append(f"  ??      {r['day_pillar']['stem']}      {r['month_pillar']['stem']}      {r['year_pillar']['stem']}")
        lines.append(f"  ??      {r['day_pillar']['branch']}      {r['month_pillar']['branch']}      {r['year_pillar']['branch']}")

    lines.append("")
    lines.append(f"일간(日干): {oa['ilgan']}({oa['ilgan_kr']}) - 오행: {oa['ilgan_ohaeng']}({oa['ilgan_ohaeng_kr']})")
    lines.append(f"일간 강약: {oa['yongsin']['strength_desc']}")
    lines.append(f"용신(用神): {oa['yongsin']['yongsin']}({oa['yongsin']['yongsin_kr']})")
    if oa['yongsin']['huisin']:
        lines.append(f"희신(喜神): {oa['yongsin']['huisin']}({oa['yongsin']['huisin_kr']})")
    lines.append("")

    lines.append("─── 오행 분포 ───")
    for oh in OHAENG_LIST:
        count = oa['count'][oh]
        bar = '■' * count + '□' * (max(0, 4 - count))
        lines.append(f"  {oh}({OHAENG_KR[oh]}): {bar} {count}개")

    if oa['yongsin']['missing_ohaeng']:
        missing_str = ', '.join([f"{m}({OHAENG_KR[m]})" for m in oa['yongsin']['missing_ohaeng']])
        lines.append(f"\n⚠ 부족 오행: {missing_str}")

    lines.append(f"\n{oa['yongsin']['description']}")

    return '\n'.join(lines)


# ─── 81수리 길흉 테이블 ───
SURI_TABLE = {
    1: ('대길', '만물 생성의 수로 부귀영화를 누리는 최길수'),
    2: ('흉', '분리 고독의 수로 모든 일이 불여의'),
    3: ('길', '만물 발전의 수로 지혜와 재능이 뛰어남'),
    4: ('흉', '파멸부정의 수로 고난과 역경이 끊이지 않음'),
    5: ('대길', '복록장수의 수로 건강과 재물이 풍족'),
    6: ('대길', '덕후계승의 수로 안정과 발전을 이룸'),
    7: ('길', '독립독행의 수로 의지가 굳고 성공'),
    8: ('길', '발전무궁의 수로 인내와 노력의 결실'),
    9: ('흉', '빈궁단명의 수로 불안정하고 고독'),
    10: ('흉', '만사공허의 수로 공허하고 허무'),
    11: ('대길', '만물갱신의 수로 새로운 시작과 번영'),
    12: ('흉', '박약무력의 수로 의지가 약하고 좌절'),
    13: ('대길', '지모총달의 수로 뛰어난 지혜와 재능'),
    14: ('흉', '파재고독의 수로 고독과 재물 손실'),
    15: ('대길', '복덕원만의 수로 복과 덕이 넘침'),
    16: ('대길', '덕망존대의 수로 명예와 덕망이 높음'),
    17: ('길', '건달강건의 수로 의지가 강하고 성취'),
    18: ('대길', '발전무궁의 수로 확장과 성공'),
    19: ('흉', '고난수업의 수로 고통과 역경'),
    20: ('흉', '허무공허의 수로 공허하고 불안정'),
    21: ('대길', '두령독립의 수로 지도력과 독립심'),
    22: ('흉', '중절좌절의 수로 중도 좌절'),
    23: ('대길', '대승발전의 수로 큰 성공과 발전'),
    24: ('대길', '입신출세의 수로 성공과 명예'),
    25: ('길', '안정건실의 수로 착실한 발전'),
    26: ('흉', '파란변동의 수로 변화가 많고 불안정'),
    27: ('흉', '고난중절의 수로 비판과 고난'),
    28: ('흉', '파란만장의 수로 길흉이 교차'),
    29: ('대길', '지혜활달의 수로 영리하고 복록'),
    30: ('흉', '길흉반반의 수로 기복이 심함'),
    31: ('대길', '지도통솔의 수로 리더십과 성공'),
    32: ('대길', '순풍요행의 수로 행운과 기회'),
    33: ('대길', '승천봉일의 수로 융성과 번영'),
    35: ('대길', '태평성대의 수로 안정과 평화'),
    37: ('대길', '인덕통달의 수로 덕과 지혜'),
    38: ('길', '문예기예의 수로 학문과 기술'),
    39: ('대길', '부귀영화의 수로 부귀와 장수'),
    41: ('대길', '만사형통의 수로 모든 일이 순탄'),
    45: ('대길', '순풍만범의 수로 순조로운 발전'),
    47: ('대길', '출세개화의 수로 개화와 성공'),
    48: ('대길', '지략겸비의 수로 지혜와 덕'),
    52: ('길', '선견지명의 수로 통찰력'),
    57: ('길', '노력발전의 수로 꾸준한 노력의 성과'),
    61: ('길', '명리쌍전의 수로 명예와 이익'),
    63: ('길', '순성발전의 수로 순탄한 발전'),
    65: ('대길', '부귀장수의 수로 부귀와 장수'),
    67: ('길', '달성통달의 수로 목표 달성'),
    68: ('대길', '발명발달의 수로 창의와 발전'),
    73: ('길', '안정평화의 수로 평화와 안정'),
    75: ('길', '진퇴자여의 수로 나아감과 물러남이 적절'),
    81: ('대길', '만물회춘의 수로 다시 시작하는 원점의 길수'),
}

# 나머지 수리는 기본 흉수로 처리
for i in range(1, 82):
    if i not in SURI_TABLE:
        SURI_TABLE[i] = ('흉', f'{i}수리는 불안정하고 기복이 있는 수')


def get_suri_rating(number):
    """수리 길흉 판단"""
    n = number % 81
    if n == 0:
        n = 81
    return SURI_TABLE.get(n, ('흉', '불안정한 수'))


def calculate_suri_ohaeng(surname_strokes, name1_strokes, name2_strokes=None):
    """
    수리오행 계산
    2글자 이름: 원격, 형격, 이격, 정격
    1글자 이름: 간소화 계산
    """
    def strokes_to_ohaeng(n):
        last_digit = n % 10
        if last_digit in (1, 2):
            return '木'
        elif last_digit in (3, 4):
            return '火'
        elif last_digit in (5, 6):
            return '土'
        elif last_digit in (7, 8):
            return '金'
        else:  # 9, 0
            return '水'

    if name2_strokes is not None:
        # 3글자 이름 (성 + 2글자)
        won = surname_strokes + name1_strokes
        hyeong = name1_strokes + name2_strokes
        yi = surname_strokes + name2_strokes
        jeong = surname_strokes + name1_strokes + name2_strokes
    else:
        # 2글자 이름 (성 + 1글자)
        won = surname_strokes + name1_strokes
        hyeong = name1_strokes + 1  # 가상 1획 추가
        yi = surname_strokes + 1
        jeong = surname_strokes + name1_strokes

    result = {
        'won': {'value': won, 'ohaeng': strokes_to_ohaeng(won), 'rating': get_suri_rating(won)},
        'hyeong': {'value': hyeong, 'ohaeng': strokes_to_ohaeng(hyeong), 'rating': get_suri_rating(hyeong)},
        'yi': {'value': yi, 'ohaeng': strokes_to_ohaeng(yi), 'rating': get_suri_rating(yi)},
        'jeong': {'value': jeong, 'ohaeng': strokes_to_ohaeng(jeong), 'rating': get_suri_rating(jeong)},
    }

    # 수리 종합 점수
    score = 0
    for key in ['won', 'hyeong', 'yi', 'jeong']:
        rating = result[key]['rating'][0]
        if rating == '대길':
            score += 25
        elif rating == '길':
            score += 18
        else:
            score += 5

    result['total_score'] = score
    result['grade'] = '최상' if score >= 90 else '상' if score >= 70 else '중' if score >= 50 else '하'

    return result


# ─── 십신(十神) 분석 ───

SIPSIN_NAMES = ['비견', '겁재', '식신', '상관', '편재', '정재', '편관', '정관', '편인', '정인']

# 십신별 성격/적성 매핑
SIPSIN_TRAITS = {
    '비견': {
        'keyword': '독립과 자존',
        'traits': ['강한 자존심과 독립심으로 자기 주도적인 삶을 이끌어가는 성향', '동료의식이 강하여 같은 뜻을 가진 사람들과 깊은 유대를 형성', '경쟁 상황에서 물러서지 않는 끈기와 집념'],
        'relationship': '대등한 관계를 추구하며, 자신의 영역을 침범받는 것을 꺼림. 존중받는다고 느낄 때 깊은 신뢰를 보임',
        'career': ['독립 사업가', '프리랜서 전문직', '스포츠/경쟁 분야'],
    },
    '겁재': {
        'keyword': '도전과 추진력',
        'traits': ['도전적이고 과감한 추진력으로 새로운 일을 벌이는 데 주저하지 않음', '사교적이고 활동적이나 재물 관리에는 다소 무관심한 경향', '위기 상황에서 오히려 빛을 발하는 돌파력'],
        'relationship': '넓은 인맥을 형성하지만, 깊이보다 넓이를 추구하여 가까운 사람에게 소홀할 수 있음',
        'career': ['영업/마케팅', '벤처 창업', '이벤트/엔터테인먼트'],
    },
    '식신': {
        'keyword': '표현과 감각',
        'traits': ['풍부한 표현력과 예술적 감수성을 지니며, 삶의 즐거움을 추구', '음식, 예술, 문화 등 감각적 영역에서 뛰어난 안목', '여유롭고 낙천적인 성품으로 주변에 편안함을 전달'],
        'relationship': '따뜻하고 배려심이 깊어 주변 사람들에게 인기가 많으며, 갈등 상황에서 중재자 역할',
        'career': ['요리/식음료', '예술/디자인', '교육/상담'],
    },
    '상관': {
        'keyword': '창의와 비판',
        'traits': ['날카로운 관찰력과 비판적 사고력으로 기존 질서에 도전하는 혁신가 기질', '창의적 재능이 뛰어나지만, 권위에 대한 반발심이 강할 수 있음', '언변이 뛰어나고 자기표현에 거침이 없어 주목받는 존재'],
        'relationship': '솔직하고 직설적인 소통을 선호하여 오해를 받기도 하지만, 진심을 알아주는 사람에게는 깊은 충성',
        'career': ['작가/언론인', '변호사/평론가', '연구/개발 혁신'],
    },
    '편재': {
        'keyword': '활동과 재물',
        'traits': ['활동적이고 사교적이며 재물을 모으고 쓰는 순환에 능숙', '임기응변에 뛰어나고 여러 분야에 관심을 가지는 다재다능함', '현실 감각이 탁월하여 기회를 포착하는 눈이 밝음'],
        'relationship': '사교의 달인으로 다양한 계층과 쉽게 어울리지만, 한 곳에 정착하기 어려운 면이 있음',
        'career': ['투자/금융', '무역/유통', '부동산/자산관리'],
    },
    '정재': {
        'keyword': '성실과 안정',
        'traits': ['꼼꼼하고 계획적인 재물 관리 능력, 정직과 신용을 최고 가치로 여김', '안정적이고 착실한 삶을 추구하며, 급격한 변화보다 점진적 성장을 선호', '책임감이 강하고 맡은 일을 끝까지 완수하는 신뢰의 사람'],
        'relationship': '한번 맺은 인연을 오래 유지하며, 가정과 가까운 사람에 대한 헌신이 강함',
        'career': ['공무원/공기업', '회계/재무', '안정적 사업 운영'],
    },
    '편관': {
        'keyword': '권위와 결단',
        'traits': ['강한 리더십과 결단력으로 조직을 이끄는 카리스마', '정의감이 강하고 불의를 참지 못하는 강직한 성품', '목표가 명확하면 장애물을 돌파하는 추진력이 있으나, 때로 과격하거나 급한 면이 있음'],
        'relationship': '상하관계가 명확한 환경에서 능력을 발휘하며, 자신을 따르는 사람에게는 깊은 보호 의식',
        'career': ['군인/경찰/검찰', '경영자/관리직', '위기관리/컨설팅'],
    },
    '정관': {
        'keyword': '품격과 질서',
        'traits': ['예의 바르고 질서를 중시하며, 사회적 체면과 명예를 소중히 여김', '규칙과 원칙을 잘 지키는 모범적인 성품으로 신뢰를 쌓아감', '온화하면서도 단호한 면이 있어, 리더로서 존경을 받는 스타일'],
        'relationship': '격식과 예의를 갖춘 관계를 선호하며, 신뢰할 수 있는 소수와 깊은 교류',
        'career': ['법조인/행정가', '대기업 관리직', '외교/공공기관'],
    },
    '편인': {
        'keyword': '직관과 탐구',
        'traits': ['비범한 직관력과 영감으로 남들이 보지 못하는 것을 포착하는 능력', '독특한 사고방식과 비전통적 관심사로 자신만의 세계를 구축', '집중력이 깊지만 관심사가 자주 바뀌어 한 분야에 오래 머물기 어려운 면'],
        'relationship': '혼자만의 시간을 중요시하며, 마음이 통하는 소수와만 깊이 교류하는 경향',
        'career': ['연구원/학자', '점술/상담/심리학', '예술/철학 분야'],
    },
    '정인': {
        'keyword': '학문과 관대',
        'traits': ['학구적이고 지적 호기심이 풍부하여 꾸준히 배우고 성장하는 사람', '관대하고 포용력이 있어 후배나 아랫사람을 잘 이끌어주는 멘토 기질', '체면과 명분을 중시하며, 격조 높은 삶을 지향'],
        'relationship': '든든한 조력자이자 스승 같은 존재로, 주변 사람들에게 안정감을 줌',
        'career': ['교수/교사', '의사/한의사', '출판/학술 분야'],
    },
}


def _get_sipsin(ilgan_ohaeng, ilgan_eumyang, target_ohaeng, target_eumyang):
    """일간 기준으로 대상 천간/지지의 십신 판별"""
    same_ey = (ilgan_eumyang == target_eumyang)

    if ilgan_ohaeng == target_ohaeng:
        return '비견' if same_ey else '겁재'

    # 내가 생하는 오행 (식신/상관)
    if OHAENG_SANGSAENG[ilgan_ohaeng] == target_ohaeng:
        return '식신' if same_ey else '상관'

    # 내가 극하는 오행 (편재/정재)
    if OHAENG_SANGGEUK[ilgan_ohaeng] == target_ohaeng:
        return '편재' if same_ey else '정재'

    # 나를 생하는 오행 (편인/정인)
    for k, v in OHAENG_SANGSAENG.items():
        if v == ilgan_ohaeng and k == target_ohaeng:
            return '편인' if same_ey else '정인'

    # 나를 극하는 오행 (편관/정관)
    for k, v in OHAENG_SANGGEUK.items():
        if v == ilgan_ohaeng and k == target_ohaeng:
            return '편관' if same_ey else '정관'

    return '비견'  # fallback


def calculate_sipsin(saju_result):
    """
    사주 전체에 대한 십신 분석.
    일간을 기준으로 나머지 7자(천간3+지지4) + 장간에 대해 십신을 분류한다.
    """
    day_stem_idx = saju_result['day_stem_idx']
    ilgan_ohaeng = CHEONGAN_OHAENG[day_stem_idx]
    ilgan_eumyang = CHEONGAN_EUMYANG[day_stem_idx]

    sipsin_count = {name: 0 for name in SIPSIN_NAMES}
    sipsin_detail = []

    # 천간 분석 (년간, 월간, 시간 — 일간은 자기 자신이므로 제외)
    stem_positions = [
        ('year_pillar', '년간', 'stem'),
        ('month_pillar', '월간', 'stem'),
        ('hour_pillar', '시간', 'stem'),
    ]
    for pillar_key, pos_name, _ in stem_positions:
        p = saju_result.get(pillar_key)
        if not p:
            continue
        stem = p['stem']
        stem_idx = CHEONGAN.index(stem)
        t_ohaeng = CHEONGAN_OHAENG[stem_idx]
        t_eumyang = CHEONGAN_EUMYANG[stem_idx]
        sipsin = _get_sipsin(ilgan_ohaeng, ilgan_eumyang, t_ohaeng, t_eumyang)
        sipsin_count[sipsin] += 1
        sipsin_detail.append({'position': pos_name, 'char': stem, 'sipsin': sipsin, 'ohaeng': t_ohaeng})

    # 지지 분석 (년지, 월지, 일지, 시지)
    branch_positions = [
        ('year_pillar', '년지'),
        ('month_pillar', '월지'),
        ('day_pillar', '일지'),
        ('hour_pillar', '시지'),
    ]
    for pillar_key, pos_name in branch_positions:
        p = saju_result.get(pillar_key)
        if not p:
            continue
        branch = p['branch']
        branch_idx = JIJI.index(branch)
        t_ohaeng = JIJI_OHAENG[branch_idx]
        t_eumyang = JIJI_EUMYANG[branch_idx]
        sipsin = _get_sipsin(ilgan_ohaeng, ilgan_eumyang, t_ohaeng, t_eumyang)
        sipsin_count[sipsin] += 1
        sipsin_detail.append({'position': pos_name, 'char': branch, 'sipsin': sipsin, 'ohaeng': t_ohaeng})

    # 장간 분석
    janggan_sipsin = {name: 0 for name in SIPSIN_NAMES}
    pillars = ['year_pillar', 'month_pillar', 'day_pillar', 'hour_pillar']
    for pillar_key in pillars:
        p = saju_result.get(pillar_key)
        if not p:
            continue
        branch = p['branch']
        for jg_stem in JIJI_JANGGAN.get(branch, []):
            jg_idx = CHEONGAN.index(jg_stem)
            t_ohaeng = CHEONGAN_OHAENG[jg_idx]
            t_eumyang = CHEONGAN_EUMYANG[jg_idx]
            sipsin = _get_sipsin(ilgan_ohaeng, ilgan_eumyang, t_ohaeng, t_eumyang)
            janggan_sipsin[sipsin] += 1

    # 두드러진 십신 (천간+지지에서 2개 이상)
    prominent = [(name, cnt) for name, cnt in sipsin_count.items() if cnt >= 2]
    prominent.sort(key=lambda x: -x[1])

    # 부족한 십신 (천간+지지에서 0개)
    lacking = [name for name, cnt in sipsin_count.items() if cnt == 0]

    # 성격/적성 도출
    personality_traits = []
    career_aptitude = []
    relationship_pattern = ''

    if prominent:
        top_sipsin = prominent[0][0]
        traits_data = SIPSIN_TRAITS.get(top_sipsin, {})
        personality_traits = traits_data.get('traits', [])
        career_aptitude = traits_data.get('career', [])
        relationship_pattern = traits_data.get('relationship', '')
    else:
        # 가장 많은 십신 기반
        max_sipsin = max(sipsin_count, key=sipsin_count.get)
        traits_data = SIPSIN_TRAITS.get(max_sipsin, {})
        personality_traits = traits_data.get('traits', [])
        career_aptitude = traits_data.get('career', [])
        relationship_pattern = traits_data.get('relationship', '')

    return {
        'sipsin_count': sipsin_count,
        'janggan_sipsin': janggan_sipsin,
        'sipsin_detail': sipsin_detail,
        'prominent': prominent,
        'lacking': lacking,
        'personality_traits': personality_traits,
        'career_aptitude': career_aptitude,
        'relationship_pattern': relationship_pattern,
    }


# ─── 대운(大運) 계산 ───

def calculate_daeun(saju_result, gender, birth_year, birth_month, birth_day):
    """
    대운 계산 — 월주에서 순행/역행으로 10년 단위 운의 흐름.

    Args:
        saju_result: calculate_saju() 반환값
        gender: '남' or '여'
        birth_year, birth_month, birth_day: 양력 생년월일
    Returns:
        dict with direction, start_age, periods[], current_period, turning_points
    """
    # 1. 순행/역행 결정
    year_stem = saju_result['year_pillar']['stem']
    year_stem_idx = CHEONGAN.index(year_stem)
    year_eumyang = CHEONGAN_EUMYANG[year_stem_idx]

    if (gender == '남' and year_eumyang == '양') or (gender == '여' and year_eumyang == '음'):
        direction = '순행'
    else:
        direction = '역행'

    # 2. 대운 시작 나이 계산
    saju_month = get_saju_month(birth_year, birth_month, birth_day)

    if direction == '순행':
        # 다음 절기까지 일수
        next_jeolgi_idx = saju_month % 12
        next_jeolgi_solar_month, next_jeolgi_day = get_jeolgi_date(birth_year, next_jeolgi_idx)
        if next_jeolgi_solar_month < birth_month or (next_jeolgi_solar_month == birth_month and next_jeolgi_day <= birth_day):
            target_year = birth_year + 1
        else:
            target_year = birth_year
        target_jdn = calc_jdn(target_year, next_jeolgi_solar_month, next_jeolgi_day)
    else:
        # 이전 절기까지 일수
        prev_jeolgi_idx = (saju_month - 1) % 12
        prev_jeolgi_solar_month, prev_jeolgi_day = get_jeolgi_date(birth_year, prev_jeolgi_idx)
        if prev_jeolgi_solar_month > birth_month or (prev_jeolgi_solar_month == birth_month and prev_jeolgi_day >= birth_day):
            target_year = birth_year - 1
        else:
            target_year = birth_year
        target_jdn = calc_jdn(target_year, prev_jeolgi_solar_month, prev_jeolgi_day)

    birth_jdn = calc_jdn(birth_year, birth_month, birth_day)
    day_diff = abs(target_jdn - birth_jdn)
    start_age = max(1, round(day_diff / 3))

    # 3. 대운 기둥 생성 (8개 = 80년)
    month_pillar = saju_result['month_pillar']
    month_stem_idx = CHEONGAN.index(month_pillar['stem'])
    month_branch_idx = JIJI.index(month_pillar['branch'])

    step = 1 if direction == '순행' else -1

    # 용신/기신 정보
    oa = saju_result['ohaeng_analysis']
    yongsin_ohaeng = oa['yongsin']['yongsin']
    huisin_ohaeng = oa['yongsin'].get('huisin', '')

    # 사주 원국 지지 목록 (충 판별용)
    original_branches = []
    for pk in ['year_pillar', 'month_pillar', 'day_pillar', 'hour_pillar']:
        p = saju_result.get(pk)
        if p:
            original_branches.append(p['branch'])

    periods = []
    current_age = date.today().year - birth_year

    for i in range(8):
        s_idx = (month_stem_idx + step * (i + 1)) % 10
        b_idx = (month_branch_idx + step * (i + 1)) % 12
        age_start = start_age + i * 10
        age_end = age_start + 9

        stem = CHEONGAN[s_idx]
        branch = JIJI[b_idx]
        stem_ohaeng = CHEONGAN_OHAENG[s_idx]
        branch_ohaeng = JIJI_OHAENG[b_idx]

        # 전환점 판별
        is_turning_point = False
        turning_reason = ''

        # 충(沖) 체크
        chung_target = JIJI_CHUNG.get(branch, '')
        for ob in original_branches:
            if ob == chung_target:
                is_turning_point = True
                turning_reason = f'대운 {branch}({JIJI_KR[b_idx]})이 사주 원국 {ob}와 충(沖)'
                break

        # 용신 오행 체크
        if stem_ohaeng == yongsin_ohaeng or branch_ohaeng == yongsin_ohaeng:
            if not is_turning_point:
                turning_reason = f'용신 {yongsin_ohaeng}({OHAENG_KR[yongsin_ohaeng]})의 기운이 들어오는 좋은 시기'
            is_turning_point = True

        # 기신(忌神) 체크 — 용신의 반대
        gisin_ohaeng = ''
        for k, v in OHAENG_SANGGEUK.items():
            if v == yongsin_ohaeng:
                gisin_ohaeng = k
                break
        if gisin_ohaeng and (stem_ohaeng == gisin_ohaeng or branch_ohaeng == gisin_ohaeng):
            if not turning_reason:
                turning_reason = f'기신 {gisin_ohaeng}({OHAENG_KR[gisin_ohaeng]})의 기운으로 주의가 필요한 시기'
            is_turning_point = True

        period = {
            'index': i,
            'age_start': age_start,
            'age_end': age_end,
            'stem': stem,
            'branch': branch,
            'stem_kr': CHEONGAN_KR[s_idx],
            'branch_kr': JIJI_KR[b_idx],
            'stem_ohaeng': stem_ohaeng,
            'branch_ohaeng': branch_ohaeng,
            'ganji': stem + branch,
            'ganji_kr': CHEONGAN_KR[s_idx] + JIJI_KR[b_idx],
            'is_turning_point': is_turning_point,
            'turning_reason': turning_reason,
        }
        periods.append(period)

    # 현재 대운 찾기
    current_period = None
    for p in periods:
        if p['age_start'] <= current_age <= p['age_end']:
            current_period = p
            break
    if not current_period and periods:
        current_period = periods[0]

    # 과거/미래 전환점 분리
    past_turning = [p for p in periods if p['is_turning_point'] and p['age_end'] < current_age]
    future_turning = [p for p in periods if p['is_turning_point'] and p['age_start'] > current_age]

    return {
        'direction': direction,
        'start_age': start_age,
        'periods': periods,
        'current_period': current_period,
        'past_turning_points': past_turning,
        'future_turning_points': future_turning,
        'current_age': current_age,
    }
