# 작명 보고서 프리미엄 업그레이드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 작명 보고서를 5섹션→8섹션으로 확대하고, 십신/대운 분석, 시나리오 기반 선택 구조, 이름 사용 가이드를 추가하여 프리미엄 가치를 높인다.

**Architecture:** saju_engine.py에 십신(十神)/대운(大運) 계산 로직을 추가하고, report_generator.py의 GPT 프롬프트를 개인화 데이터 기반으로 전면 개편하며, pdf_generator.py에 대운 타임라인 시각화와 새 섹션 레이아웃을 추가한다. app.py와 index.html은 새 데이터 흐름을 연결한다.

**Tech Stack:** Python 3, Flask, OpenAI GPT-4o, fpdf2, SQLite

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `saju_engine.py` | Modify (add ~200 lines) | 십신 계산, 대운 계산 함수 추가 |
| `report_generator.py` | Modify (major rewrite ~400 lines) | 시스템 프롬프트 강화, 3개 신규 섹션, 2개 개편 섹션, 컨텍스트 빌더 |
| `pdf_generator.py` | Modify (add ~120 lines) | 대운 타임라인, 새 챕터 구조, 사용 가이드 레이아웃 |
| `app.py` | Modify (~30 lines) | 십신/대운 데이터 연결, serialize 확장 |
| `templates/index.html` | Modify (~20 lines) | 새 섹션 타입 SSE 핸들링 |

---

### Task 1: 십신(十神) 계산 엔진

**Files:**
- Modify: `saju_engine.py` (파일 끝에 추가)

- [ ] **Step 1: 십신 판별 헬퍼 함수 추가**

`saju_engine.py` 파일 끝(`calculate_suri_ohaeng` 함수 아래)에 다음 코드를 추가:

```python
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
```

- [ ] **Step 2: 십신 전체 분석 함수 추가**

Step 1 코드 바로 아래에 이어서 추가:

```python
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
```

- [ ] **Step 3: 수동 검증**

Python REPL에서 검증:
```bash
cd /c/Users/onsta/naming-service && python -c "
from saju_engine import calculate_saju, calculate_sipsin
r = calculate_saju(1990, 5, 15, 14, 0)
s = calculate_sipsin(r)
print('십신 분포:', s['sipsin_count'])
print('두드러진:', s['prominent'])
print('부족:', s['lacking'])
print('성격:', s['personality_traits'][:1])
"
```
Expected: 십신 분포 딕셔너리 출력, 에러 없음

- [ ] **Step 4: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add saju_engine.py
git commit -m "feat: add sipsin (ten gods) calculation engine"
```

---

### Task 2: 대운(大運) 계산 엔진

**Files:**
- Modify: `saju_engine.py` (Task 1 코드 아래에 추가)

- [ ] **Step 1: 대운 계산 함수 추가**

`saju_engine.py`의 `calculate_sipsin()` 함수 아래에 다음을 추가:

```python
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
    # 월주의 절기 인덱스 찾기
    saju_month = get_saju_month(birth_year, birth_month, birth_day)

    if direction == '순행':
        # 다음 절기까지 일수
        next_jeolgi_idx = saju_month % 12  # 다음 절기 인덱스
        next_jeolgi_solar_month, next_jeolgi_day = get_jeolgi_date(birth_year, next_jeolgi_idx)
        # 다음 절기 날짜가 현재 월보다 이전이면 내년
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
```

- [ ] **Step 2: 수동 검증**

```bash
cd /c/Users/onsta/naming-service && python -c "
from saju_engine import calculate_saju, calculate_daeun
r = calculate_saju(1990, 5, 15, 14, 0)
d = calculate_daeun(r, '남', 1990, 5, 15)
print('방향:', d['direction'], '시작나이:', d['start_age'])
print('현재대운:', d['current_period']['ganji'], d['current_period']['ganji_kr'])
for p in d['periods']:
    tp = ' ★전환점: ' + p['turning_reason'] if p['is_turning_point'] else ''
    print(f'  {p[\"age_start\"]}-{p[\"age_end\"]}세: {p[\"ganji\"]}({p[\"ganji_kr\"]}) {p[\"stem_ohaeng\"]}/{p[\"branch_ohaeng\"]}{tp}')
"
```
Expected: 8개 대운 기간 출력, 전환점 표시, 에러 없음

- [ ] **Step 3: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add saju_engine.py
git commit -m "feat: add daeun (major luck cycles) calculation engine"
```

---

### Task 3: 시스템 프롬프트 강화 + 컨텍스트 빌더

**Files:**
- Modify: `report_generator.py`

- [ ] **Step 1: import 추가 및 시스템 프롬프트 교체**

`report_generator.py` 상단 import 영역에 추가:
```python
from saju_engine import calculate_sipsin, calculate_daeun
```

기존 `SYSTEM_PROMPT` 변수를 다음으로 **전체 교체**:

```python
SYSTEM_PROMPT = """당신은 본 바른이름연구소의 대한민국 최고 작명 전문가이자 명리학 석학입니다. 수천 가문의 이름을 지어왔고, 사주명리학·음성학·성명학에 대한 깊은 학문적 소양과 현장 경험을 겸비하고 있습니다.

【절대 준수 사항 — 이 규칙을 어기면 보고서 전체가 무효입니다】

첫째, 줄글(산문) 형식으로 작성하되, 각 문단 앞에 반드시 소제목을 붙이십시오. 소제목은 **소제목** 형식(별표 두 개로 감싸기)으로 작성하고, 바로 다음 줄부터 해당 내용을 줄글 문단으로 서술하십시오. 소제목은 짧고 담백한 명사구로 쓰십시오(예: "사주의 흐름", "오행의 균형", "이름의 첫인상", "발음과 소리결", "한자에 담긴 뜻"). 문학적이거나 과장된 표현은 피하고, 책의 목차처럼 직관적으로 쓰십시오. 한 문단은 최소 4~6문장으로 풍성하게 구성하십시오.

둘째, 다음 형식은 절대 사용하지 마십시오: bullet point(-, *, •), 번호 목록(1. 2. 3.), 마크다운 헤더(##, ###), 이모지, 표, 코드블록. 소제목은 오직 **소제목** 형식만 허용됩니다.

셋째, 본 바른이름연구소의 노련한 작명 전문가로서 따뜻하면서도 권위 있는 어조로 쓰십시오. 고객에게 직접 말씀드리는 느낌으로, 존댓말(~입니다, ~합니다)을 사용하되, "저희 연구소에서 수많은 사주를 분석해왔지만" 같은 경험에서 우러나오는 확신이 자연스럽게 묻어나게 쓰십시오.

넷째, 추상적이고 뻔한 표현 대신 구체적이고 실질적인 분석을 풍부하게 서술하십시오. 사주의 어떤 글자가 어떤 작용을 하는지, 오행이 왜 그렇게 흐르는지를 세밀하게 풀어쓰십시오.

다섯째, 보고서의 주어는 항상 '본 바른이름연구소'입니다. '필자', '제가', '나는' 등 개인을 주어로 쓰지 마십시오. '본 바른이름연구소에서는', '저희 연구소에서는', '저희가' 등 기관 주어를 사용하십시오.

여섯째, 후보 이름을 언급할 때 '이름인 ㅇㅇㅇ은/는'이라고 쓰지 마십시오. 아직 확정된 이름이 아니라 후보이므로 반드시 '이름 후보인 ㅇㅇㅇ은/는'이라고 쓰십시오.

【금지 표현 — 아래 표현 및 유사 표현은 절대 사용 금지】
절대 사용하지 말아야 할 표현들: "밝고 세련된 이미지", "사회적 신뢰감을 줍니다", "대인관계에서 긍정적 영향", "현대적이면서도 고전적인", "조화로운 균형", "안정감 있는 이름", "부드러우면서도 강인한", "시대를 초월하는 품격", "긍정적인 에너지", "좋은 인상을 줄 수 있습니다", "밝은 이미지를 전달", "호감을 주는 이름"
이러한 누구에게나 붙일 수 있는 범용적·추상적 표현은 전문성을 해칩니다. 대신 이 사주의 구체적 데이터(십신 분포, 대운 흐름, 오행 수치, 한자의 고유한 의미)에서 도출된 고유한 분석만 서술하십시오. 모든 문장이 "이 사주에만 해당하는 이야기"여야 합니다.
"""
```

- [ ] **Step 2: 십신/대운 컨텍스트 빌더 추가**

`build_name_context()` 함수 아래, `SYSTEM_PROMPT` 위(또는 아래)에 다음 두 함수를 추가:

```python
def build_sipsin_context(sipsin_result):
    """십신 분석 결과를 프롬프트 컨텍스트로 변환"""
    sc = sipsin_result['sipsin_count']
    count_str = ', '.join([f"{name}: {cnt}개" for name, cnt in sc.items()])

    prominent_str = ''
    if sipsin_result['prominent']:
        parts = []
        for name, cnt in sipsin_result['prominent']:
            traits = SIPSIN_TRAITS.get(name, {})
            parts.append(f"{name}({cnt}개) — {traits.get('keyword', '')}")
        prominent_str = ', '.join(parts)
    else:
        max_name = max(sc, key=sc.get)
        traits = SIPSIN_TRAITS.get(max_name, {})
        prominent_str = f"{max_name}({sc[max_name]}개) — {traits.get('keyword', '')}"

    lacking_str = ', '.join(sipsin_result['lacking']) if sipsin_result['lacking'] else '없음'

    detail_lines = []
    for d in sipsin_result['sipsin_detail']:
        detail_lines.append(f"  {d['position']}: {d['char']}({d['ohaeng']}) → {d['sipsin']}")

    context = f"""
[십신(十神) 분석]
분포: {count_str}
두드러진 십신: {prominent_str}
부족한 십신: {lacking_str}

[십신 상세 배치]
{chr(10).join(detail_lines)}

[십신 기반 성격 키워드]
{chr(10).join(['  ' + t for t in sipsin_result['personality_traits']])}

[대인관계 패턴]
  {sipsin_result['relationship_pattern']}

[직업 적성]
  {', '.join(sipsin_result['career_aptitude'])}
"""
    return context


def build_daeun_context(daeun_result):
    """대운 분석 결과를 프롬프트 컨텍스트로 변환"""
    lines = [f"대운방향: {daeun_result['direction']} / 시작나이: {daeun_result['start_age']}세"]

    for p in daeun_result['periods']:
        tp_mark = ''
        if p['is_turning_point']:
            tp_mark = f" ★전환점: {p['turning_reason']}"
        lines.append(f"  {p['age_start']}-{p['age_end']}세: {p['ganji']}({p['ganji_kr']}) {p['stem_ohaeng']}/{p['branch_ohaeng']}{tp_mark}")

    cp = daeun_result.get('current_period')
    if cp:
        lines.append(f"\n현재 대운(만 {daeun_result['current_age']}세): {cp['ganji']}({cp['ganji_kr']}) {cp['stem_ohaeng']}/{cp['branch_ohaeng']}")

    future = daeun_result.get('future_turning_points', [])
    if future:
        next_tp = future[0]
        lines.append(f"다음 전환점: {next_tp['age_start']}세경 — {next_tp['ganji']}({next_tp['ganji_kr']}) {next_tp['turning_reason']}")

    context = f"""
[대운(大運) 흐름]
{chr(10).join(lines)}
"""
    return context
```

- [ ] **Step 3: build_saju_context 확장**

기존 `build_saju_context()` 함수의 맨 끝 `return context` 바로 위에서, context 변수에 십신/대운 요약을 추가하도록 수정한다. 기존 함수 시그니처를 변경:

기존:
```python
def build_saju_context(saju_result, form_data):
```

새로:
```python
def build_saju_context(saju_result, form_data, sipsin_result=None, daeun_result=None):
```

그리고 기존 `return context` 바로 위에 다음을 추가:

```python
    if sipsin_result:
        context += build_sipsin_context(sipsin_result)
    if daeun_result:
        context += build_daeun_context(daeun_result)
```

- [ ] **Step 4: 수동 검증**

```bash
cd /c/Users/onsta/naming-service && python -c "
from saju_engine import calculate_saju, calculate_sipsin, calculate_daeun
from report_generator import build_saju_context, build_sipsin_context, build_daeun_context
r = calculate_saju(1990, 5, 15, 14, 0)
s = calculate_sipsin(r)
d = calculate_daeun(r, '남', 1990, 5, 15)
form = {'gender': '남', 'birth_date': '1990-05-15', 'birth_time': '14:00', 'surname': '변',
        'request_type': '개명', 'considerations': '없음', 'desired_image': '없음', 'avoid_feeling': '없음'}
ctx = build_saju_context(r, form, s, d)
print(ctx[:500])
print('...')
print(ctx[-300:])
"
```
Expected: 기존 사주 컨텍스트 + 십신 분석 + 대운 흐름이 모두 포함된 텍스트 출력

- [ ] **Step 5: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add report_generator.py
git commit -m "feat: enhance system prompt with banned phrases, add sipsin/daeun context builders"
```

---

### Task 4: 신규 섹션 생성기 3개 (성격진단, 인생흐름, 사용가이드)

**Files:**
- Modify: `report_generator.py` (기존 `generate_final_comparison()` 함수 아래에 추가)

- [ ] **Step 1: 성격 심층 진단 섹션 생성기**

`generate_final_comparison()` 아래에 추가:

```python
def generate_section_personality(saju_context, sipsin_result, call_designation='우리 아이'):
    """섹션 2: 성격 심층 진단 — 십신 기반 개인화 분석"""
    sc = sipsin_result['sipsin_count']
    prominent = sipsin_result['prominent']
    lacking = sipsin_result['lacking']

    # 두드러진 십신 정보를 프롬프트에 직접 주입
    prominent_info = ''
    if prominent:
        for name, cnt in prominent:
            traits_data = SIPSIN_TRAITS.get(name, {})
            prominent_info += f"\n- {name}이(가) {cnt}개로 두드러짐: 키워드 '{traits_data.get('keyword', '')}'"
            prominent_info += f"\n  성격 경향: {'; '.join(traits_data.get('traits', [])[:2])}"
    else:
        max_name = max(sc, key=sc.get)
        traits_data = SIPSIN_TRAITS.get(max_name, {})
        prominent_info = f"\n- {max_name}이(가) {sc[max_name]}개로 가장 많음: 키워드 '{traits_data.get('keyword', '')}'"

    lacking_info = ''
    if lacking:
        lacking_details = []
        for name in lacking[:3]:
            traits_data = SIPSIN_TRAITS.get(name, {})
            lacking_details.append(f"{name}({traits_data.get('keyword', '')})")
        lacking_info = f"부족한 십신: {', '.join(lacking_details)}"

    prompt = f"""{saju_context}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 마십시오.

다음은 {call_designation}의 십신(十神) 분석 결과입니다:
{prominent_info}
{lacking_info}

이 데이터를 바탕으로 {call_designation}의 성격을 심층 진단하는 보고서 섹션을 작성하십시오.

【필수 포함 내용 — 빠짐없이 서술】

첫째, 이 사주에서 가장 두드러진 십신을 근거로 {call_designation}의 핵심 성격 특성 3가지를 서술하십시오. 각 특성이 일상에서 어떻게 발현되는지 구체적인 상황 예시를 반드시 포함하십시오. 예를 들어 "회의에서 자신의 의견을 먼저 제시하기보다 다른 사람의 이야기를 끝까지 들은 후 핵심을 정리하는 스타일"처럼 구체적이어야 합니다.

둘째, {call_designation}이 대인관계에서 보이는 전형적인 관계 패턴 2가지를 서술하십시오. 친구, 연인, 직장동료 등 구체적 관계 유형별로 다르게 나타나는 양상을 포함하십시오.

셋째, {call_designation}의 사주가 특히 강점을 보이는 직업 영역 3가지와 그 이유를 십신 구조에 근거하여 분석하십시오. 단순 나열이 아니라 "왜 이 사주가 이 분야에 적합한지"를 논리적으로 풀어쓰십시오.

넷째, 부족한 십신으로 인해 보완이 필요한 영역을 서술하고, 이것이 이름 선택에 어떤 방향을 제시하는지 연결하십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)
```

- [ ] **Step 2: 인생 흐름 예측 섹션 생성기**

Step 1 코드 바로 아래에 추가:

```python
def generate_section_life_flow(saju_context, daeun_result, call_designation='우리 아이'):
    """섹션 3: 인생 흐름 예측 — 대운 기반 과거 맞추기 + 미래 전환점"""
    current_age = daeun_result['current_age']
    current_period = daeun_result.get('current_period')
    past_turning = daeun_result.get('past_turning_points', [])
    future_turning = daeun_result.get('future_turning_points', [])

    # 대운 흐름 요약을 프롬프트에 직접 주입
    daeun_timeline = ''
    for p in daeun_result['periods']:
        marker = ''
        if p['is_turning_point']:
            marker = f' [전환점: {p["turning_reason"]}]'
        if current_period and p['index'] == current_period['index']:
            marker += ' ← 현재'
        daeun_timeline += f"\n  {p['age_start']}-{p['age_end']}세: {p['ganji']}({p['ganji_kr']}) 오행={p['stem_ohaeng']}/{p['branch_ohaeng']}{marker}"

    past_events = ''
    if past_turning:
        for pt in past_turning:
            past_events += f"\n  - {pt['age_start']}세 전후: {pt['turning_reason']}"
    else:
        past_events = '\n  (과거 대운에서 뚜렷한 전환점 없음 — 비교적 안정적 흐름)'

    future_events = ''
    if future_turning:
        for ft in future_turning[:3]:
            future_events += f"\n  - {ft['age_start']}세경: {ft['turning_reason']}"
    else:
        future_events = '\n  (향후 대운이 안정적 흐름을 보임)'

    prompt = f"""{saju_context}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 마십시오.

다음은 {call_designation}의 대운(大運) 분석 결과입니다:
방향: {daeun_result['direction']} / 시작나이: {daeun_result['start_age']}세 / 현재 나이: {current_age}세

[대운 타임라인]{daeun_timeline}

[과거 주요 전환점]{past_events}

[미래 주요 전환점]{future_events}

이 데이터를 바탕으로 {call_designation}의 인생 흐름을 예측하는 보고서 섹션을 작성하십시오.

【필수 포함 내용 — 빠짐없이 서술】

첫째, 대운의 전체적 흐름을 개관하십시오. {daeun_result['direction']} 대운이 어떤 의미를 갖는지, 전체 인생의 큰 그림을 그려주십시오.

둘째, 과거 전환점에 대해 서술하십시오. "{call_designation}께서 {past_turning[0]['age_start'] if past_turning else ''}세 전후로 중요한 변화나 전환이 있었을 가능성이 높습니다"와 같이, 대운의 오행 변화가 사주 원국과 어떻게 작용하여 변화를 가져왔는지 구체적으로 분석하십시오. 과거 전환점이 없으면 안정적 흐름의 의미를 설명하십시오.

셋째, 현재 대운의 의미를 깊이 있게 분석하십시오. 지금 시기에 어떤 에너지가 작용하고 있으며, 현재의 고민이나 상황과 어떻게 연결되는지 서술하십시오.

넷째, 향후 전환점과 기회를 예측하십시오. 다가올 대운의 오행이 사주에 어떤 변화를 가져올지, 어떤 준비가 필요한지 구체적으로 안내하십시오.

다섯째, 이러한 인생 흐름에서 이름이 갖는 의미를 연결하십시오. 좋은 이름이 대운의 부정적 영향을 완화하고 긍정적 영향을 증폭시킬 수 있다는 점을 자연스럽게 풀어쓰십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)
```

- [ ] **Step 3: 이름 사용 가이드 섹션 생성기**

Step 2 코드 바로 아래에 추가:

```python
def generate_section_usage_guide(saju_context, daeun_result, recommended_name, call_designation='우리 아이'):
    """섹션 8: 이름 사용 가이드 — 프리미엄 의식(ritual) 연출"""
    current_period = daeun_result.get('current_period', {})
    future_turning = daeun_result.get('future_turning_points', [])

    next_good_period = ''
    for p in daeun_result['periods']:
        if p['age_start'] > daeun_result['current_age'] and not p.get('turning_reason', '').startswith('기신'):
            next_good_period = f"{p['age_start']}세({p['ganji']} {p['ganji_kr']})"
            break

    prompt = f"""{saju_context}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 마십시오.

최종 추천된 이름은 '{recommended_name}'입니다.
현재 대운: {current_period.get('ganji', '')}({current_period.get('ganji_kr', '')}) {current_period.get('stem_ohaeng', '')}/{current_period.get('branch_ohaeng', '')}
향후 좋은 시기: {next_good_period}

이 이름을 실제로 사용하기 시작할 때 필요한 종합 가이드를 작성하십시오. 이 섹션은 고객이 이름 변경 후 실제로 참고할 실용적 안내서입니다.

【필수 포함 내용 — 빠짐없이 서술】

첫째, 개명 최적 시기를 안내하십시오. 현재 대운과 향후 대운의 흐름을 고려하여 이름 변경에 가장 적합한 시기를 제안하고, 그 이유를 사주학적으로 설명하십시오. 계절, 월, 요일 등 구체적 시기까지 안내하십시오.

둘째, 이름 첫 사용 의식을 안내하십시오. 새 이름으로 처음 서명하는 순간의 의미, 공적 문서 변경 순서(주민등록→운전면허→여권→은행 등), 첫 사용 시 마음가짐을 서술하십시오.

셋째, 주변 알림 전략을 안내하십시오. 가족 → 가까운 지인 → 직장/학교 → 공적 관계 순으로 새 이름을 알리는 구체적 방법과 타이밍을 제안하십시오.

넷째, 이 사주에서 특별히 피해야 할 금기사항을 안내하십시오. 부족한 오행이나 충(沖) 관계를 고려한 방위, 색상, 습관 등 실생활에서 주의할 점을 구체적으로 서술하십시오.

다섯째, 이름 변경 후 변화 흐름을 예측하십시오. 30일 후, 3개월 후, 1년 후, 3년 후 각각 어떤 변화를 기대할 수 있는지 단계별로 서술하십시오. 막연한 "좋아질 것"이 아니라, 오행 보완 효과가 구체적으로 어떻게 발현되는지 풀어쓰십시오.

여섯째, 이름의 에너지를 극대화하는 생활 습관을 3가지 이상 제안하십시오. 이름에 담긴 오행과 연결하여, 색상 활용, 방위 활용, 계절별 주의점 등 실천 가능한 조언을 제시하십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=8000, min_length=500)
```

- [ ] **Step 4: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add report_generator.py
git commit -m "feat: add personality, life-flow, and usage-guide section generators"
```

---

### Task 5: 기존 섹션 시나리오 구조 개편

**Files:**
- Modify: `report_generator.py` — `generate_name_analysis()`, `generate_final_comparison()` 함수 교체

- [ ] **Step 1: 이름 분석 함수를 시나리오 구조로 교체**

`generate_name_analysis()` 함수의 prompt 변수를 통째로 교체. 기존 함수를 찾아서 prompt 부분만 바꾼다:

```python
def generate_name_analysis(saju_context, name_context, name_index, call_designation='우리 아이', daeun_result=None):
    """이름 상세 분석 — 시나리오 기반 설득 구조"""
    daeun_info = ''
    if daeun_result:
        cp = daeun_result.get('current_period', {})
        future = daeun_result.get('future_turning_points', [])
        daeun_info = f"""
[현재 대운] {cp.get('ganji', '')}({cp.get('ganji_kr', '')}) {cp.get('stem_ohaeng', '')}/{cp.get('branch_ohaeng', '')}
[향후 전환점] {future[0]['age_start'] if future else '없음'}세경"""

    prompt = f"""다음 사주 정보와 이름 후보를 바탕으로 이 이름에 대한 상세 분석을 작성해주세요.

{saju_context}

{name_context}
{daeun_info}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 마십시오.
【이름 후보 호칭 규칙】 후보 이름을 언급할 때 절대로 '이름인 ㅇㅇㅇ은/는'이라고 쓰지 마십시오. 반드시 '이름 후보인 ㅇㅇㅇ은/는'이라고 쓰십시오.

이 이름에 대해 아래 구조로 분석을 작성하십시오. 이 구조는 고객이 "이 이름을 꼭 선택해야겠다"고 느끼도록 설계된 시나리오 기반 설득 구조입니다.

【필수 포함 내용 — 빠짐없이 서술, 시나리오 구조로】

첫째, 이 이름과 함께할 구체적 미래상을 그리십시오. 이 이름의 오행 보완 효과가 {call_designation}의 사주에서 구체적으로 어떤 변화를 가져오는지, 성격·대인관계·직업 영역에서 각각 어떤 긍정적 시나리오가 펼쳐지는지 서술하십시오. "이 이름을 쓰게 되면 ~한 상황에서 ~하게 될 것입니다"와 같은 미래 시제 서술을 포함하십시오.

둘째, 이 이름이 가져올 구체적 변화 시나리오를 대운과 연계하여 서술하십시오. 현재 대운에서 이 이름이 어떤 시너지를 발휘하는지, 향후 전환점에서 이 이름의 오행이 어떤 보호 역할을 하는지 구체적으로 분석하십시오.

셋째, 발음의 특성과 소리의 질감을 분석하십시오. 초성·중성·종성 조합이 만드는 음성학적 효과, 부르기 편한 이유, 기억에 남는 소리의 특징을 구체적으로 풀어쓰십시오.

넷째, 각 한자의 본뜻과 역사적 용례, 고전에서의 의미를 풍부하게 풀어쓰고, 두 글자가 합쳐졌을 때의 시너지를 서술하십시오.

다섯째, 이 이름만의 고유한 강점을 서술하십시오. 다른 후보 이름에는 없는, 이 이름만이 가진 차별화 포인트가 무엇인지 명확히 제시하십시오.

여섯째, 이 이름을 선택하지 않았을 때 놓치게 되는 것을 자연스럽게 서술하십시오. 강압적이지 않되, 이 이름이 제공하는 가치를 놓치는 것이 아쉽다는 뉘앙스를 전달하십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오. 번호 목록, bullet point, 이모지는 절대 사용하지 마십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=8000, min_length=500)
```

- [ ] **Step 2: 최종 비교 함수를 선택 압박 구조로 교체**

`generate_final_comparison()` 함수를 교체:

```python
def generate_final_comparison(saju_context, all_names_context, call_designation='우리 아이', daeun_result=None):
    """최종 비교·추천 — 선택 압박 구조"""
    daeun_info = ''
    if daeun_result:
        cp = daeun_result.get('current_period', {})
        daeun_info = f"\n[현재 대운] {cp.get('ganji', '')}({cp.get('ganji_kr', '')}) — 이 시기에 가장 필요한 오행 보완을 고려하여 추천하십시오."

    prompt = f"""다음 사주 정보와 3개 후보 이름을 바탕으로 최종 비교 분석을 작성하세요.

{saju_context}

{all_names_context}
{daeun_info}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 마십시오.
【이름 후보 호칭 규칙】 후보 이름을 언급할 때 반드시 '이름 후보인 ㅇㅇㅇ은/는'이라고 쓰십시오.

세 이름을 종합적으로 비교하여 최종 추천을 제시하되, 다음 구조를 따르십시오.

【필수 포함 내용 — 선택 시나리오 구조】

첫째, 각 이름을 선택했을 때의 미래 시나리오를 대비하여 서술하십시오. "첫 번째 후보를 선택하면... 두 번째 후보를 선택하면... 세 번째 후보를 선택하면..."의 구조로, 각 이름이 가져올 삶의 방향이 어떻게 달라지는지 구체적으로 비교하십시오.

둘째, 사주 보완력을 객관적으로 비교하십시오. 용신·희신 반영도, 오행 균형 기여도, 음령 오행 상생 흐름, 자원 오행 상생 흐름, 충(沖)·형(刑) 여부를 종합적으로 비교하여 순위를 매기십시오.

셋째, 수리오행과 음성학 관점에서 세 이름의 안정성을 비교하십시오.

넷째, {call_designation}의 사주를 고려했을 때 최종 선택 시 가장 우선해야 할 기준 2가지를 제시하고, 그 기준에 따라 왜 특정 이름이 최선인지 논리적으로 설득하십시오.

다섯째, 최종 추천에서 감정적 임팩트를 담아 마무리하십시오. "이 이름이 {call_designation}의 삶에 가져올 변화를 생각하면, 저희 연구소에서는..."과 같이, 전문가로서의 확신과 따뜻한 권유가 느껴지는 문장으로 마무리하십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오. 번호 목록, bullet point, 이모지는 절대 사용하지 마십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)
```

- [ ] **Step 3: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add report_generator.py
git commit -m "feat: restructure name analysis to scenario-based persuasion, add selection pressure to comparison"
```

---

### Task 6: 보고서 오케스트레이션 업데이트 (5→8섹션)

**Files:**
- Modify: `report_generator.py` — `generate_full_report()`, `generate_report_streaming()` 함수 교체

- [ ] **Step 1: generate_full_report 교체**

기존 `generate_full_report()` 함수를 통째로 교체:

```python
def generate_full_report(saju_result, names, form_data):
    """전체 보고서 생성 (8회 API 호출)"""
    # 사전 계산
    gender = form_data.get('gender', '남')
    birth_date = form_data.get('birth_date', '')
    parts = birth_date.split('-')
    birth_year, birth_month, birth_day = int(parts[0]), int(parts[1]), int(parts[2])

    sipsin_result = calculate_sipsin(saju_result)
    daeun_result = calculate_daeun(saju_result, gender, birth_year, birth_month, birth_day)

    saju_context = build_saju_context(saju_result, form_data, sipsin_result, daeun_result)
    call_designation = get_call_designation(form_data)

    report = {'sections': [], 'status': 'generating', 'progress': 0,
              'call_designation': call_designation,
              'sipsin_result': sipsin_result, 'daeun_result': daeun_result}

    # 섹션 1: 사주 분석 도입부
    report['progress'] = 5
    intro = generate_section_intro(saju_context, form_data, call_designation)
    report['sections'].append({
        'title': '사주 분석 및 작명 방향',
        'content': intro,
        'type': 'intro'
    })

    # 섹션 2: 성격 심층 진단
    report['progress'] = 15
    personality = generate_section_personality(saju_context, sipsin_result, call_designation)
    report['sections'].append({
        'title': '성격 심층 진단',
        'content': personality,
        'type': 'personality'
    })

    # 섹션 3: 인생 흐름 예측
    report['progress'] = 25
    life_flow = generate_section_life_flow(saju_context, daeun_result, call_designation)
    report['sections'].append({
        'title': '인생 흐름 예측',
        'content': life_flow,
        'type': 'life_flow'
    })

    # 섹션 4~6: 이름별 시나리오 분석
    all_names_context = ""
    for i, name in enumerate(names):
        name_context = build_name_context(name, i + 1)
        all_names_context += name_context + "\n"

        analysis = generate_name_analysis(saju_context, name_context, i + 1, call_designation, daeun_result)
        report['sections'].append({
            'title': f"후보 이름 {i + 1}: {name['hangul']}",
            'content': analysis,
            'type': 'name_analysis',
            'name_info': {
                'hangul': name['hangul'],
                'hanja': ' '.join([c['hanja'] for c in name['chars']]),
                'meaning': name.get('meaning_summary', ''),
                'ohaeng': name['ohaeng_composition'],
                'eumyang': ' '.join(name.get('eumyang', [])),
                'eumryeong_flow': name.get('eumryeong_flow', ''),
                'jawon_flow': name.get('jawon_flow', ''),
            }
        })
        report['progress'] = 25 + (i + 1) * 15

    # 섹션 7: 최종 비교·추천
    report['progress'] = 80
    comparison = generate_final_comparison(saju_context, all_names_context, call_designation, daeun_result)
    report['sections'].append({
        'title': '최종 추천 및 선택 가이드',
        'content': comparison,
        'type': 'comparison'
    })

    # 섹션 8: 이름 사용 가이드
    report['progress'] = 90
    # 추천 이름 추출 (마지막 비교에서 첫 번째 이름을 기본 추천으로)
    recommended_name = names[0]['hangul'] if names else ''
    usage_guide = generate_section_usage_guide(saju_context, daeun_result, recommended_name, call_designation)
    report['sections'].append({
        'title': '이름 사용 가이드',
        'content': usage_guide,
        'type': 'usage_guide'
    })

    report['status'] = 'complete'
    report['progress'] = 100
    return report
```

- [ ] **Step 2: generate_report_streaming 교체**

기존 `generate_report_streaming()` 함수를 통째로 교체:

```python
def generate_report_streaming(saju_result, names, form_data):
    """스트리밍 보고서 생성 (제너레이터) — 8섹션"""
    # 사전 계산
    gender = form_data.get('gender', '남')
    birth_date = form_data.get('birth_date', '')
    parts = birth_date.split('-')
    birth_year, birth_month, birth_day = int(parts[0]), int(parts[1]), int(parts[2])

    sipsin_result = calculate_sipsin(saju_result)
    daeun_result = calculate_daeun(saju_result, gender, birth_year, birth_month, birth_day)

    saju_context = build_saju_context(saju_result, form_data, sipsin_result, daeun_result)
    call_designation = get_call_designation(form_data)

    # 섹션 1: 사주 분석 도입부
    yield {'type': 'progress', 'progress': 5, 'message': '사주 분석 보고서 작성 중...'}
    intro = generate_section_intro(saju_context, form_data, call_designation)
    yield {
        'type': 'section', 'progress': 12,
        'section': {'title': '사주 분석 및 작명 방향', 'content': intro, 'section_type': 'intro'}
    }

    # 섹션 2: 성격 심층 진단
    yield {'type': 'progress', 'progress': 12, 'message': '성격 심층 진단 분석 중...'}
    personality = generate_section_personality(saju_context, sipsin_result, call_designation)
    yield {
        'type': 'section', 'progress': 25,
        'section': {'title': '성격 심층 진단', 'content': personality, 'section_type': 'personality'}
    }

    # 섹션 3: 인생 흐름 예측
    yield {'type': 'progress', 'progress': 25, 'message': '인생 흐름 예측 분석 중...'}
    life_flow = generate_section_life_flow(saju_context, daeun_result, call_designation)
    yield {
        'type': 'section', 'progress': 35,
        'section': {'title': '인생 흐름 예측', 'content': life_flow, 'section_type': 'life_flow'}
    }

    # 섹션 4~6: 이름별 시나리오 분석
    all_names_context = ""
    for i, name in enumerate(names):
        yield {'type': 'progress', 'progress': 35 + i * 15, 'message': f'후보 이름 {i+1} "{name["hangul"]}" 분석 중...'}

        name_context = build_name_context(name, i + 1)
        all_names_context += name_context + "\n"
        analysis = generate_name_analysis(saju_context, name_context, i + 1, call_designation, daeun_result)

        name_card = {
            'hangul': name['hangul'],
            'hanja': ' '.join([c['hanja'] for c in name['chars']]),
            'hanja_detail': [{'hanja': c['hanja'], 'hangul': c['hangul'], 'meaning': c.get('meaning', ''),
                              'strokes': c.get('strokes', 0), 'ohaeng': c.get('ohaeng', '')} for c in name['chars']],
            'ohaeng': name['ohaeng_composition'],
            'eumyang': ' '.join(name.get('eumyang', [])),
            'eumryeong_flow': name.get('eumryeong_flow', ''),
            'jawon_flow': name.get('jawon_flow', ''),
        }

        yield {
            'type': 'section', 'progress': 35 + (i + 1) * 15,
            'section': {'title': f'후보 이름 {i + 1}: {name["hangul"]}', 'content': analysis,
                        'section_type': 'name_analysis', 'name_card': name_card}
        }

    # 섹션 7: 최종 비교·추천
    yield {'type': 'progress', 'progress': 82, 'message': '최종 비교 분석 작성 중...'}
    comparison = generate_final_comparison(saju_context, all_names_context, call_designation, daeun_result)
    yield {
        'type': 'section', 'progress': 90,
        'section': {'title': '최종 추천 및 선택 가이드', 'content': comparison, 'section_type': 'comparison'}
    }

    # 섹션 8: 이름 사용 가이드
    yield {'type': 'progress', 'progress': 90, 'message': '이름 사용 가이드 작성 중...'}
    recommended_name = names[0]['hangul'] if names else ''
    usage_guide = generate_section_usage_guide(saju_context, daeun_result, recommended_name, call_designation)
    yield {
        'type': 'section', 'progress': 100,
        'section': {'title': '이름 사용 가이드', 'content': usage_guide, 'section_type': 'usage_guide'}
    }

    yield {'type': 'complete', 'progress': 100, 'message': '보고서 생성 완료!'}
```

- [ ] **Step 3: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add report_generator.py
git commit -m "feat: update report orchestration from 5 to 8 sections"
```

---

### Task 7: PDF 대운 타임라인 + 새 섹션 지원

**Files:**
- Modify: `pdf_generator.py`

- [ ] **Step 1: 대운 타임라인 시각화 메서드 추가**

`NamingReportPDF` 클래스의 `add_name_card()` 메서드 아래에 새 메서드를 추가:

```python
    # ═══════════════════════════════════════
    # 대운 타임라인 시각화
    # ═══════════════════════════════════════
    def add_daeun_timeline(self, daeun_result):
        """대운 흐름을 타임라인 바 차트로 시각화"""
        if not daeun_result or not daeun_result.get('periods'):
            return

        self._add_body_page()
        y = BODY_TOP + 8

        # 제목
        self.set_y(y)
        self.set_font('Gothic', 'B', 16)
        self.set_text_color(*C_TITLE)
        self.cell(0, 10, '대운(大運) 흐름도', align='C')
        y += 18

        # 구분선
        self.set_draw_color(180, 160, 130)
        self.set_line_width(0.4)
        self.line(60, y, 150, y)
        y += 8

        # 기본 정보
        self.set_y(y)
        self.set_font('Gothic', '', 10)
        self.set_text_color(*C_BODY)
        self.cell(0, 7, f"대운 방향: {daeun_result['direction']}  |  시작 나이: {daeun_result['start_age']}세  |  현재 나이: {daeun_result['current_age']}세", align='C')
        y += 14

        # 타임라인 바 차트
        bar_x = 35
        bar_w = 140
        bar_h = 18
        periods = daeun_result['periods']
        current_idx = None
        current_period = daeun_result.get('current_period')
        if current_period:
            current_idx = current_period.get('index')

        for i, p in enumerate(periods):
            # 배경 바
            ohaeng = p['stem_ohaeng']
            color = C_OHAENG.get(ohaeng, C_BODY)

            # 현재 대운 강조
            if current_idx is not None and i == current_idx:
                self.set_draw_color(200, 50, 50)
                self.set_line_width(0.8)
                self.rect(bar_x - 1, y - 1, bar_w + 2, bar_h + 2)
                self.set_line_width(0.2)

            # 바 배경
            self.set_fill_color(*(c + (255 - c) * 7 // 10 for c in color))  # 연한 버전
            self.rect(bar_x, y, bar_w, bar_h, 'F')

            # 전환점 마커
            if p['is_turning_point']:
                self.set_fill_color(255, 215, 0)
                self.rect(bar_x, y, 4, bar_h, 'F')

            # 텍스트: 나이 범위
            self.set_xy(bar_x + 6, y + 2)
            self.set_font('Gothic', 'B', 9)
            self.set_text_color(*C_BODY)
            self.cell(25, 7, f"{p['age_start']}-{p['age_end']}세")

            # 간지
            self.set_font('Gothic', 'B', 11)
            self.set_text_color(*color)
            self.cell(30, 7, f"{p['ganji']}({p['ganji_kr']})")

            # 오행
            self.set_font('Gothic', '', 9)
            self.set_text_color(*C_BODY)
            ohaeng_text = f"{p['stem_ohaeng']}/{p['branch_ohaeng']}"
            self.cell(20, 7, ohaeng_text)

            # 전환점 설명
            if p['is_turning_point'] and p['turning_reason']:
                self.set_font('Gothic', '', 8)
                self.set_text_color(180, 50, 50)
                reason_short = p['turning_reason'][:25] + '...' if len(p['turning_reason']) > 25 else p['turning_reason']
                self.cell(0, 7, reason_short)

            # 현재 대운 표시
            if current_idx is not None and i == current_idx:
                self.set_xy(bar_x + bar_w - 25, y + bar_h - 9)
                self.set_font('Gothic', 'B', 8)
                self.set_text_color(200, 50, 50)
                self.cell(20, 7, '현재', align='R')

            y += bar_h + 3

            # 페이지 넘침 방지
            if y > PH - BODY_BOTTOM - 20:
                break

        # 범례
        y += 5
        if y < PH - BODY_BOTTOM - 15:
            self.set_y(y)
            self.set_font('Gothic', '', 8)
            self.set_text_color(*C_HEADER)
            self.set_x(bar_x)
            self.cell(0, 5, '■ 금색 표시 = 전환점  |  빨간 테두리 = 현재 대운')
```

- [ ] **Step 2: create_naming_report_pdf 함수를 8섹션 구조로 교체**

기존 `create_naming_report_pdf()` 함수를 통째로 교체:

```python
def create_naming_report_pdf(saju_result, names, report, form_data, output_path):
    """
    완성된 보고서 데이터를 받아 디자인 에셋 기반 PDF 생성 — 8섹션 구조

    Args:
        saju_result: 사주 계산 결과
        names: 생성된 이름 리스트
        report: generate_full_report() 반환값
        form_data: 폼 입력 데이터
        output_path: 저장 경로
    """
    pdf = NamingReportPDF()

    # ── 1. 앞표지 ──
    pdf.add_cover()

    # ── 2. 목차 ──
    pdf.add_toc(names)

    # ── 3. 0장 주의사항 (고정 9페이지) ──
    pdf.add_static_pages()

    # ── 대운/십신 데이터 추출 ──
    daeun_result = report.get('daeun_result')

    # ── 4. 보고서 본문 (8섹션) ──
    sections = report.get('sections', [])
    # 챕터 오프닝 이미지 매핑 (8챕터 → 5개 이미지 재활용)
    chapter_opening_map = {
        'intro': 1,
        'personality': 2,
        'life_flow': 3,
        'name_analysis_1': 4,
        'name_analysis_2': 5,
        'name_analysis_3': 3,
        'comparison': 4,
        'usage_guide': 5,
    }

    name_analysis_count = 0

    for sec in sections:
        sec_type = sec.get('type', '')
        content = sec.get('content', '')
        name_info = sec.get('name_info')

        if sec_type == 'intro':
            pdf.add_chapter_opening(chapter_opening_map['intro'])
            pdf.add_saju_info(saju_result, form_data)
            pdf.write_prose(content)

        elif sec_type == 'personality':
            pdf.add_chapter_opening(chapter_opening_map['personality'])
            pdf.write_prose(content)

        elif sec_type == 'life_flow':
            pdf.add_chapter_opening(chapter_opening_map['life_flow'])
            if daeun_result:
                pdf.add_daeun_timeline(daeun_result)
            pdf.write_prose(content)

        elif sec_type == 'name_analysis':
            name_analysis_count += 1
            ch_key = f'name_analysis_{name_analysis_count}'
            ch_img_idx = chapter_opening_map.get(ch_key, 4)
            pdf.add_chapter_opening(ch_img_idx)

            if name_info:
                card = {
                    'hangul': name_info.get('hangul', ''),
                    'hanja': name_info.get('hanja', ''),
                    'ohaeng': name_info.get('ohaeng', ''),
                    'eumryeong_flow': name_info.get('eumryeong_flow', ''),
                    'jawon_flow': name_info.get('jawon_flow', ''),
                    'eumyang': name_info.get('eumyang', ''),
                }
                pdf.add_name_card(card, names)

            pdf.write_prose(content)

        elif sec_type == 'comparison':
            pdf.add_chapter_opening(chapter_opening_map['comparison'])
            pdf.write_prose(content)

        elif sec_type == 'usage_guide':
            pdf.add_chapter_opening(chapter_opening_map['usage_guide'])
            pdf.write_prose(content)

    # ── 5. 뒷표지 ──
    pdf.add_back_cover()

    # ── 저장 ──
    pdf.output(output_path)
    return output_path
```

- [ ] **Step 3: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add pdf_generator.py
git commit -m "feat: add daeun timeline visualization, update PDF to 8-section structure"
```

---

### Task 8: 앱 통합 + 프론트엔드 업데이트

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`

- [ ] **Step 1: app.py에 십신/대운 import 추가**

`app.py` 상단 import 영역 수정. 기존:
```python
from saju_engine import calculate_saju, format_saju_summary
```
새로:
```python
from saju_engine import calculate_saju, format_saju_summary, calculate_sipsin, calculate_daeun
```

- [ ] **Step 2: serialize_saju 함수에 십신/대운 추가**

`app.py`의 `serialize_saju()` 함수 끝에 십신/대운 데이터를 추가로 포함하도록 수정. 함수 시그니처 변경:

기존:
```python
def serialize_saju(saju_result):
```
새로:
```python
def serialize_saju(saju_result, sipsin_result=None, daeun_result=None):
```

기존 함수의 `return result` 바로 위에 추가:

```python
    if sipsin_result:
        result['sipsin'] = {
            'sipsin_count': sipsin_result['sipsin_count'],
            'prominent': sipsin_result['prominent'],
            'lacking': sipsin_result['lacking'],
        }
    if daeun_result:
        result['daeun'] = {
            'direction': daeun_result['direction'],
            'start_age': daeun_result['start_age'],
            'current_age': daeun_result['current_age'],
            'periods': [{
                'age_start': p['age_start'],
                'age_end': p['age_end'],
                'ganji': p['ganji'],
                'ganji_kr': p['ganji_kr'],
                'stem_ohaeng': p['stem_ohaeng'],
                'branch_ohaeng': p['branch_ohaeng'],
                'is_turning_point': p['is_turning_point'],
                'turning_reason': p['turning_reason'],
            } for p in daeun_result['periods']],
        }
```

- [ ] **Step 3: api_generate에서 십신/대운 계산 추가**

`app.py`의 `api_generate()` 함수에서 사주 계산 직후에 십신/대운도 계산:

`saju_summary = format_saju_summary(saju_result)` 줄 아래에 추가:

```python
        # 십신/대운 계산
        sipsin_result = calculate_sipsin(saju_result)
        daeun_result = calculate_daeun(saju_result, gender, birth_year, birth_month, birth_day)
```

그리고 `return jsonify` 부분에서 `serialize_saju` 호출을 수정:

기존:
```python
            'saju_result': serialize_saju(saju_result),
```
새로:
```python
            'saju_result': serialize_saju(saju_result, sipsin_result, daeun_result),
```

- [ ] **Step 4: index.html 프론트엔드 — 새 섹션 타입 지원**

`templates/index.html`의 SSE 핸들러에서 새로운 섹션 타입도 기존과 동일하게 처리되므로 (title과 content를 그대로 렌더링), 프론트엔드 변경은 최소화.

보고서 영역의 푸터 텍스트만 업데이트. 기존:
```html
<p>AI 사주명리 기반 프리미엄 작명 서비스</p>
```
새로 (두 곳 모두 — SSE 핸들러의 complete 이벤트와 renderReport 함수):
```html
<p>AI 사주명리·십신·대운 기반 프리미엄 작명 서비스</p>
```

- [ ] **Step 5: 수동 통합 테스트**

```bash
cd /c/Users/onsta/naming-service && python -c "
from saju_engine import calculate_saju, calculate_sipsin, calculate_daeun
from report_generator import build_saju_context
r = calculate_saju(2024, 3, 15, 10, 0)
s = calculate_sipsin(r)
d = calculate_daeun(r, '남', 2024, 3, 15)
form = {'gender': '남', 'birth_date': '2024-03-15', 'birth_time': '10:00', 'surname': '김',
        'request_type': '신생아 작명', 'considerations': '없음', 'desired_image': '없음', 'avoid_feeling': '없음'}
ctx = build_saju_context(r, form, s, d)
print('Context length:', len(ctx))
print('십신 prominent:', s['prominent'])
print('대운 periods:', len(d['periods']))
print('Integration OK')
"
```
Expected: "Integration OK" 출력, 에러 없음

- [ ] **Step 6: 커밋**

```bash
cd /c/Users/onsta/naming-service
git add app.py templates/index.html
git commit -m "feat: integrate sipsin/daeun into API responses and frontend"
```

---

## Self-Review Checklist

1. **Spec coverage:**
   - 십신 계산 → Task 1 ✓
   - 대운 계산 → Task 2 ✓
   - 시스템 프롬프트 금지 표현 → Task 3 ✓
   - 컨텍스트 빌더 → Task 3 ✓
   - 성격 심층 진단 → Task 4 ✓
   - 인생 흐름 예측 → Task 4 ✓
   - 이름 사용 가이드 → Task 4 ✓
   - 이름 분석 시나리오 구조 → Task 5 ✓
   - 최종 비교 선택 압박 → Task 5 ✓
   - 오케스트레이션 5→8 → Task 6 ✓
   - PDF 대운 타임라인 → Task 7 ✓
   - PDF 8섹션 구조 → Task 7 ✓
   - 앱 통합 → Task 8 ✓

2. **Placeholder scan:** 모든 코드가 완전하게 작성됨. TBD/TODO 없음.

3. **Type consistency:**
   - `sipsin_result` 구조: Task 1에서 정의, Task 3/4/6/8에서 동일하게 참조
   - `daeun_result` 구조: Task 2에서 정의, Task 3/4/5/6/7/8에서 동일하게 참조
   - `calculate_sipsin` / `calculate_daeun` 함수명: 모든 import/호출에서 일관
   - `build_sipsin_context` / `build_daeun_context` 함수명: 모든 참조에서 일관
   - `generate_section_personality` / `generate_section_life_flow` / `generate_section_usage_guide`: 정의와 호출 일관
   - `SIPSIN_TRAITS` 딕셔너리: Task 1에서 정의, Task 3/4에서 참조 — report_generator.py에서는 saju_engine에서 import해야 함

4. **발견된 이슈 및 수정:**
   - **이슈**: Task 3의 `build_sipsin_context()`에서 `SIPSIN_TRAITS`를 참조하는데, 이 상수는 `saju_engine.py`에 정의됨. report_generator.py에서 import 필요.
   - **수정**: Task 3 Step 1의 import 문을 다음으로 수정:
     ```python
     from saju_engine import calculate_sipsin, calculate_daeun, SIPSIN_TRAITS
     ```
