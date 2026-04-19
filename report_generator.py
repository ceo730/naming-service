"""
바른이름연구소 작명 보고서 생성기 v3
- 순수 줄글(산문) 형식 보고서
- 바른이름연구소 전문가 문체
- 사주 분석 → 이름별 상세 → 최종 비교
"""

import os
import re
import time
import openai
import json
from datetime import date
from saju_engine import calculate_sipsin, calculate_daeun, SIPSIN_TRAITS
from name_generator import SURNAME_HANJA_CANON

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-4o"

if not OPENAI_API_KEY:
    import logging
    logging.getLogger(__name__).warning("OPENAI_API_KEY가 설정되지 않았습니다. 보고서 생성이 실패합니다.")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ─── 안정적 API 호출 (재시도 + 딜레이) ───
_last_call_time = 0

def _call_with_retry(system_prompt, user_prompt, max_tokens, min_length=200, max_retries=3,
                     validator=None):
    """GPT 호출 + 응답이 너무 짧거나 validator 실패 시 자동 재시도, 호출 간 최소 3초 간격.

    validator: Optional callable (content: str) -> (ok: bool, reason: str).
               False 반환 시 재시도. 반환된 reason은 재시도 프롬프트에 섞여 교정 유도.
    """
    global _last_call_time
    content = ''
    last_validator_reason = ''
    for attempt in range(max_retries):
        # 호출 간 최소 3초 간격
        elapsed = time.time() - _last_call_time
        if elapsed < 3:
            time.sleep(3 - elapsed)
        _last_call_time = time.time()

        # 재시도 시에는 validator 피드백을 user_prompt에 덧붙여 교정 유도
        attempt_user_prompt = user_prompt
        if attempt > 0 and last_validator_reason:
            attempt_user_prompt = (
                user_prompt
                + '\n\n【이전 응답 교정 필요 — 반드시 반영】\n'
                + last_validator_reason
                + '\n위 지적을 정확히 반영하여 본문을 다시 작성하십시오.'
            )

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": attempt_user_prompt}
                ],
                temperature=0.7,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ''
            is_refusal = content.startswith('죄송') or content.startswith('요청하신') or '작성할 수 없' in content
            if len(content) < min_length or is_refusal:
                last_validator_reason = ''
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                continue
            if validator is not None:
                ok, reason = validator(content)
                if not ok:
                    last_validator_reason = reason
                    if attempt < max_retries - 1:
                        time.sleep(2 * (attempt + 1))
                    continue
            return content
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise
    return content  # 마지막 시도 결과 반환 (일부 결함 있는 보고서가 완전 실패보다 낫다)


# ─── 한자 화이트리스트 생성 헬퍼 ───

# 본문에서 항상 허용되는 명리학 핵심 한자
_CORE_HANJA = set(
    '五行用神喜神相生相剋日干月令原局大運天干地支陰陽十神比肩劫財食神傷官偏財正財偏官'
    '正官偏印正印四柱命理藏干沖刑格局身强身弱神殺合破害劫年月日時干支八字'
    # 오행·천간·지지
    '木火土金水甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥'
    # 자주 쓰이는 분석 용어
    '順逆生剋制化旺相休囚死胎養長生沐浴冠帶臨官帝旺衰病墓絶'
)


def _collect_saju_hanja(saju_result):
    """사주팔자 원국의 천간·지지 한자 수집"""
    chars = set()
    for p_name in ['year_pillar', 'month_pillar', 'day_pillar', 'hour_pillar']:
        p = saju_result.get(p_name)
        if p:
            chars.add(p.get('stem', ''))
            chars.add(p.get('branch', ''))
    return {c for c in chars if c}


def _collect_name_hanja(name_info):
    """후보 이름 한자 수집"""
    chars = set()
    for c in name_info.get('chars', []):
        h = c.get('hanja', '')
        if h:
            chars.add(h)
    return chars


def _build_allowed_hanja_block(saju_result, form_data=None, names=None):
    """본문 허용 한자 블록을 사용자 프롬프트용으로 구성.
    names가 list면 여러 후보 한자를 모두 허용. dict면 단일 후보.
    """
    allowed = set(_CORE_HANJA)
    allowed |= _collect_saju_hanja(saju_result)
    if form_data:
        sur_hanja = form_data.get('surname_hanja', '') or ''
        if not sur_hanja:
            sur_hanja = SURNAME_HANJA_CANON.get(form_data.get('surname', ''), '')
        allowed |= set(sur_hanja)
        cur = form_data.get('current_name_hanja', '') or ''
        allowed |= set(cur)
    if names:
        if isinstance(names, dict):
            allowed |= _collect_name_hanja(names)
        else:
            for n in names:
                allowed |= _collect_name_hanja(n)
    allowed = sorted(c for c in allowed if c and '\u4e00' <= c <= '\u9fff')
    return (
        '\n【본문 사용 가능 한자】\n'
        '아래 한자 외에는 본문에 절대 등장시키지 마십시오. 비슷한 모양의 다른 글자로 대체하면 안 됩니다.\n'
        + ' '.join(allowed)
        + '\n'
    )


def _find_forbidden_hanja(content, allowed_set):
    """본문에서 허용 집합에 없는 한자 찾기. 중복 제거 후 최대 10개 반환."""
    used = set(re.findall(r'[\u4e00-\u9fff]', content))
    illegal = used - allowed_set
    return sorted(illegal)[:10]


def _find_bad_suri_mentions(content, suri):
    """본문에서 '원격 N', '형격 N' 같은 숫자 언급이 실제 값과 다른 경우 검출.
    또한 금지된 '숫자 포함 획수 언급'도 플래그.
    """
    issues = []
    label_map = {'원격': suri['won']['value'], '형격': suri['hyeong']['value'],
                 '이격': suri['yi']['value'], '정격': suri['jeong']['value']}
    for label, correct_val in label_map.items():
        for m in re.finditer(rf'{label}[은는가이의도]?\s*[가-힣]{{0,3}}?\s*(\d+)', content):
            n = int(m.group(1))
            if n != correct_val:
                issues.append(f"본문의 '{label} {n}'은 실제 값 {correct_val}과 다릅니다")
    if len(re.findall(r'\d+\s*획', content)) > 0:
        issues.append("본문에 'N획' 형태의 획수 숫자가 등장합니다 — 구체 획수 언급은 금지입니다")
    return issues


def _find_nonexistent_branches(content, saju_result):
    """원국에 없는 지지 글자를 '원국'이라는 단어 근처에서 언급하면 검출."""
    original_branches = set()
    for p_name in ['year_pillar', 'month_pillar', 'day_pillar', 'hour_pillar']:
        p = saju_result.get(p_name)
        if p and p.get('branch'):
            original_branches.add(p['branch'])
    all_branches = set('子丑寅卯辰巳午未申酉戌亥')
    missing = all_branches - original_branches
    issues = []
    # '원국'이라는 단어 근처 ±40자 범위에 원국에 없는 지지가 등장하면 경고
    for m in re.finditer(r'원국', content):
        start = max(0, m.start() - 40)
        end = min(len(content), m.end() + 40)
        window = content[start:end]
        for mb in missing:
            if mb in window:
                issues.append(f"'원국'이라는 단어 근처에서 원국에 없는 지지 '{mb}'가 언급되었습니다")
                break
    return issues


def _make_name_validator(saju_result, name_info, form_data):
    """후보 이름 분석 섹션용 종합 검증기."""
    allowed = set(_CORE_HANJA)
    allowed |= _collect_saju_hanja(saju_result)
    allowed |= _collect_name_hanja(name_info)
    if form_data:
        sur_h = form_data.get('surname_hanja', '') or SURNAME_HANJA_CANON.get(form_data.get('surname', ''), '')
        allowed |= set(sur_h or '')
        allowed |= set(form_data.get('current_name_hanja', '') or '')
    suri = name_info.get('suri', {})

    def _validator(content):
        reasons = []
        forbidden = _find_forbidden_hanja(content, allowed)
        if forbidden:
            reasons.append(
                f"허용 목록 밖의 한자가 본문에 등장했습니다: {' '.join(forbidden)}. "
                f"이 한자들을 제거하거나 허용 목록 내 한자로 대체하십시오."
            )
        if suri:
            reasons.extend(_find_bad_suri_mentions(content, suri))
        reasons.extend(_find_nonexistent_branches(content, saju_result))
        if reasons:
            return False, '\n'.join(f'- {r}' for r in reasons)
        return True, ''

    return _validator


def get_call_designation(form_data):
    """나이에 따라 대상을 부르는 호칭 결정"""
    birth_date = form_data.get('birth_date', '')
    request_type = form_data.get('request_type', '신생아 작명')
    current_name = form_data.get('current_name', '')
    surname = form_data.get('surname', '')

    if birth_date:
        try:
            parts = birth_date.split('-')
            birth_year = int(parts[0])
            age = date.today().year - birth_year
            if age < 10:
                return '우리 아이'
            else:
                if current_name:
                    return f'{current_name}님'
                return f'{surname}씨'
        except (ValueError, IndexError):
            pass

    if '개명' in request_type and current_name:
        return f'{current_name}님'
    return '우리 아이'


def build_saju_context(saju_result, form_data, sipsin_result=None, daeun_result=None):
    oa = saju_result['ohaeng_analysis']
    yongsin = oa['yongsin']

    pillars = []
    for p_name, p_label in [('year_pillar', '년주'), ('month_pillar', '월주'),
                             ('day_pillar', '일주'), ('hour_pillar', '시주')]:
        p = saju_result.get(p_name)
        if p:
            pillars.append(f"{p_label}: {p['ganji']}({p['ganji_kr']}) - 천간오행:{p['stem_ohaeng']} 지지오행:{p['branch_ohaeng']}")
        else:
            pillars.append(f"{p_label}: 미상")

    context = f"""
[대상자 정보]
성별: {form_data.get('gender', '미상')}
생년월일: {form_data.get('birth_date', '미상')} (양력)
출생시간: {form_data.get('birth_time', '미상')}
성씨: {form_data.get('surname', '미상')}

[사주팔자]
{chr(10).join(pillars)}

[오행 분포]
木(목): {oa['count']['木']}개 / 火(화): {oa['count']['火']}개 / 土(토): {oa['count']['土']}개 / 金(금): {oa['count']['金']}개 / 水(수): {oa['count']['水']}개

[일간] {oa['ilgan']}({oa['ilgan_kr']}) - {oa['ilgan_ohaeng']}({oa['ilgan_ohaeng_kr']}) | 강약: {yongsin['strength_desc']}
[용신] {yongsin['yongsin']}({yongsin['yongsin_kr']}) | [희신] {yongsin.get('huisin', '')}({yongsin.get('huisin_kr', '')})
[부족오행] {', '.join([f"{m}({oa['yongsin']['missing_ohaeng_kr'][i]})" for i, m in enumerate(yongsin['missing_ohaeng'])])}

[고객 요청]
신청유형: {form_data.get('request_type', '신생아 작명')}
중요 고려사항: {form_data.get('considerations', '없음')}
원하는 이미지: {form_data.get('desired_image', '없음')}
피하고 싶은 느낌: {form_data.get('avoid_feeling', '없음')}
"""
    if sipsin_result:
        context += build_sipsin_context(sipsin_result)
    if daeun_result:
        context += build_daeun_context(daeun_result)

    return context


def build_name_context(name_info, index):
    chars_detail = []
    for c in name_info['chars']:
        jawon = c.get('jawon_ohaeng', c.get('ohaeng', ''))
        chars_detail.append(f"  {c['hanja']}({c['hangul']}): 뜻={c.get('meaning','')}, 획수={c.get('strokes',0)}, 오행={c.get('ohaeng','')}, 자원오행={jawon}")

    suri = name_info['suri']

    eumryeong_flow = name_info.get('eumryeong_flow', '')
    eumryeong_detail = name_info.get('eumryeong_detail', '')
    eumryeong_score = name_info.get('eumryeong_score', 0)

    jawon_flow = name_info.get('jawon_flow', '')
    jawon_detail = name_info.get('jawon_detail', '')
    jawon_score = name_info.get('jawon_score', 0)

    chung_warnings = name_info.get('chung_warnings', [])
    chung_str = '; '.join(chung_warnings) if chung_warnings else '없음'

    hyeong_warnings = name_info.get('hyeong_warnings', [])
    hyeong_str = '; '.join(hyeong_warnings) if hyeong_warnings else '없음'

    eumyang_strokes = name_info.get('eumyang_strokes', [])
    ey_str = '-'.join(eumyang_strokes) if eumyang_strokes else '미분석'

    context = f"""
[후보 이름 {index}]
한글: {name_info['hangul']}
한자: {' '.join([c['hanja'] for c in name_info['chars']])}

[한자 상세]
{chr(10).join(chars_detail)}

[오행 구성] {name_info['ohaeng_composition']}
[음양 구성] {' '.join(name_info.get('eumyang', []))}
[음양 획수] {ey_str}

[음령 오행(초성 오행)] {eumryeong_flow} - {eumryeong_detail} ({eumryeong_score}/100)
[자원 오행 흐름] {jawon_flow} - {jawon_detail} ({jawon_score}/100)

[수리오행]
원격: {suri['won']['value']}→{suri['won']['ohaeng']}({suri['won']['rating'][0]}) | 형격: {suri['hyeong']['value']}→{suri['hyeong']['ohaeng']}({suri['hyeong']['rating'][0]})
이격: {suri['yi']['value']}→{suri['yi']['ohaeng']}({suri['yi']['rating'][0]}) | 정격: {suri['jeong']['value']}→{suri['jeong']['ohaeng']}({suri['jeong']['rating'][0]})
수리종합: {suri['grade']}

[음성학] {name_info.get('phonetic_score', 0)}/100 ({name_info.get('phonetic_detail', '')})
[뜻 요약] {name_info.get('meaning_summary', '')}
[충(沖) 검사] {chung_str}
[형(刑) 검사] {hyeong_str}
"""
    return context


def build_sipsin_context(sipsin_result):
    """십신 분석 결과를 프롬프트 컨텍스트로 변환"""
    sc = sipsin_result['sipsin_count']
    count_str = ', '.join([f"{name}: {cnt}개" for name, cnt in sc.items()])

    prominent_str = ''
    if sipsin_result['prominent']:
        parts = []
        for name, cnt in sipsin_result['prominent']:
            traits = SIPSIN_TRAITS.get(name, {})
            parts.append(f"{name}({cnt}개) - {traits.get('keyword', '')}")
        prominent_str = ', '.join(parts)
    else:
        max_name = max(sc, key=sc.get)
        traits = SIPSIN_TRAITS.get(max_name, {})
        prominent_str = f"{max_name}({sc[max_name]}개) - {traits.get('keyword', '')}"

    lacking_str = ', '.join(sipsin_result['lacking']) if sipsin_result['lacking'] else '없음'

    detail_lines = []
    for d in sipsin_result['sipsin_detail']:
        detail_lines.append(f"  {d['position']}: {d['char']}({d['ohaeng']}) -> {d['sipsin']}")

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
            tp_mark = f" *전환점: {p['turning_reason']}"
        lines.append(f"  {p['age_start']}-{p['age_end']}세: {p['ganji']}({p['ganji_kr']}) {p['stem_ohaeng']}/{p['branch_ohaeng']}{tp_mark}")

    cp = daeun_result.get('current_period')
    if cp:
        lines.append(f"\n현재 대운(만 {daeun_result['current_age']}세): {cp['ganji']}({cp['ganji_kr']}) {cp['stem_ohaeng']}/{cp['branch_ohaeng']}")

    future = daeun_result.get('future_turning_points', [])
    if future:
        next_tp = future[0]
        lines.append(f"다음 전환점: {next_tp['age_start']}세경 - {next_tp['ganji']}({next_tp['ganji_kr']}) {next_tp['turning_reason']}")

    context = f"""
[대운(大運) 흐름]
{chr(10).join(lines)}
"""
    return context


SYSTEM_PROMPT = """당신은 정통 사주명리학에 기반한 작명 분석 보고서를 작성하는 전문가입니다.

【문체 규칙 — 도해원(導解院) 분석 문체】

이 보고서는 분석적이고 객관적인 격식체로 작성합니다. 구어체, 대화체, 1인칭 의견은 일절 사용하지 않습니다.

기본 어미: "~편입니다", "~쉽습니다", "~됩니다", "~입니다", "~있습니다"
허용 어미: "~볼 수 있습니다", "~해석됩니다", "~작용합니다", "~나타납니다"

절대 금지하는 표현:
- 1인칭: "제가", "저희가", "저희 연구소", "제가 보기에"
- 구어체: "~이거든요", "~인 셈이죠", "~더라고요", "~한번 봅시다", "~해볼게요"
- AI 안내 멘트: "살펴보겠습니다", "분석해 보겠습니다", "알아보겠습니다"
- 감성적 수식: "밝고 세련된", "조화로운 균형", "안정감 있는", "긍정적인 에너지", "호감을 주는"

【원국 데이터 중심 서술】

모든 문단은 반드시 해당 인물의 원국(原局) 데이터에서 출발해야 합니다. 추상적 설명 없이, 사주 구조의 구체적 근거를 먼저 제시하고 그로부터 해석을 이끌어냅니다.

예시: "원국의 일간 丙火는 午月에 태어나 왕성한 화기(火氣)를 지니고 있으며, 시주의 乙木이 생화(生火)하여 火의 기운이 더욱 강한 편입니다."

한자(漢字)를 본문에 적극 사용합니다. 천간·지지·오행 등은 한자를 병기하거나 한자로 먼저 쓰고 한글을 괄호 안에 넣습니다. 예: "丙火(병화)", "甲·乙 목기(木氣)", "午火(오화)"

핵심 개념이나 성향을 표현할 때는 작은따옴표로 감쌉니다. 예: '내가 책임진다', '차분히 가라앉는 시간', '안으로 삭이는 성향'

【형식 규칙】

첫째, 줄글(산문) 형식으로 쓰되, 문단마다 앞에 소제목을 답니다. 소제목은 **소제목** 형식(별표 두 개로 감싸기)으로 쓰고, 바로 다음 줄부터 줄글 문단을 이어 씁니다. 한 문단은 최소 4~6문장으로 풍성하게 구성하십시오.

둘째, 소제목은 짧은 명사구로 씁니다. 좋은 예시: "타고난 성격의 핵심", "사고방식과 판단 기준", "감정 표현과 내면 구조", "부족한 기운이 만드는 갈증", "불균형이 반복되는 패턴", "오행 분포와 용신", "자원오행의 상생 흐름". 절대 금지하는 소제목 패턴: "~이 주는 새로운 변화", "~이 열어주는 가능성", "~이 선사하는 미래", "~속에 담긴 이야기" 같은 시적이거나 문학적인 표현.

셋째, 다음 형식은 절대 사용 금지: bullet point(-, *, •), 번호 목록(1. 2. 3.), 마크다운 헤더(##, ###), 이모지, 표, 코드블록. 소제목은 오직 **소제목** 형식만 허용됩니다.

넷째, 후보 이름을 언급할 때 '이름인 ㅇㅇㅇ은/는'이라고 쓰지 마십시오. 아직 확정된 이름이 아니라 후보이므로 반드시 '이름 후보인 ㅇㅇㅇ은/는'이라고 쓰십시오.

【금지 표현 — 아래 표현 및 유사 표현은 절대 사용 금지】
"밝고 세련된 이미지", "사회적 신뢰감을 줍니다", "대인관계에서 긍정적 영향", "현대적이면서도 고전적인", "조화로운 균형", "안정감 있는 이름", "부드러우면서도 강인한", "시대를 초월하는 품격", "긍정적인 에너지", "좋은 인상을 줄 수 있습니다", "밝은 이미지를 전달", "호감을 주는 이름"
이런 건 누구에게나 붙일 수 있는 표현입니다. 이 사주의 구체적 데이터(원국 구조, 십신 분포, 대운 흐름, 오행 수치, 한자의 고유한 의미)에서 도출된 분석만 서술하십시오.

【사실 진술 금지 — 반드시 준수】

아래 데이터는 본문에 **구체적 수치·기호로 직접 기재하지 마십시오**. 사용자는 별도의 표·카드에서 정확한 값을 이미 확인합니다. 본문에서는 값의 '의미'와 '해석'만 서술합니다.

첫째, 81수리 4격의 구체적 숫자. '원격 23', '형격 16', '정격 32'와 같이 숫자를 동반한 표기는 금지합니다. 대신 '원격과 형격이 전반적으로 길수(吉數)의 흐름을 이룬다', '정격의 수리가 말년 운의 근간을 지지한다' 같이 등급·맥락 수준으로만 서술하십시오.

둘째, 한자별 획수의 숫자. '秀는 7획이며', '炫이 9획이라'와 같이 획수를 숫자로 언급하지 마십시오. 획수 배치가 음양 교차를 이루는지 등 '구조적 특성'만 서술하십시오.

셋째, 음성학의 구체 자모. '종성 ㅇ', '중성 ㅣ', '초성 ㅂ' 같이 개별 자음·모음을 직접 명시하지 마십시오. 실제 이름 분해와 어긋날 위험이 큽니다. 대신 '첫 음절에서 입술소리로 출발하여 뒷음절로 갈수록 울림이 열리는 구조' 같이 청각적 특성으로 서술하십시오.

넷째, 오행 흐름의 화살표 표기. '水→金→土' 형태의 기호 서술은 금지합니다. 대신 '성씨의 기운이 첫 글자에서 동질적으로 이어져 둘째 글자에서 다른 흐름으로 전환된다' 같은 방식으로 서술하십시오. (오행 자체의 명칭인 '水·金·土'는 사용 가능합니다.)

【원국 충실성 — 허구 금지】

사주 원국(年·月·日·時 4기둥의 천간·지지 총 8자)에 존재하지 않는 글자를 '원국에 ○○이 있다'는 식으로 서술하지 마십시오. 사용자 컨텍스트의 [사주팔자] 블록에 나열된 8자만이 원국입니다. 대운(大運)에서만 등장하는 천간·지지는 반드시 '○세 ○○ 대운에서', '과거 ○○ 대운기에는'처럼 대운 맥락으로만 언급합니다. 원국의 지지끼리의 충(沖)·형(刑)이 성립하려면 해당 두 글자가 모두 원국 8자 안에 있어야 합니다.

【오행 관계의 엄격 정의】

오행의 생극 관계를 서술할 때 다음 정의를 반드시 따르십시오.
상생(相生)은 木→火→土→金→水→木의 순서로 앞이 뒤를 생(生)하는 관계입니다. 특히 金生水는 상생이며, 水와 金을 '상극'이라 기술하면 명백한 오류입니다.
상극(相剋)은 木剋土, 土剋水, 水剋火, 火剋金, 金剋木의 다섯 관계로만 한정됩니다.
비화(比和)는 동일 오행끼리의 관계(예: 水와 水, 金과 金)에만 사용하는 용어이며, 서로 다른 오행 사이에 '비화'라는 단어를 사용하면 안 됩니다.

【한자 화이트리스트 — 엄격 적용】

본문에 등장시키는 한자는 사용자 프롬프트의 [본문 사용 가능 한자] 블록에 명시된 글자만 허용합니다. 해당 블록이 제공된 경우, 그 밖의 한자는 일반 명리학 기본 용어(五行, 用神, 喜神, 相生, 相剋, 日干, 月令, 原局, 大運, 天干, 地支, 陰陽, 十神, 比肩, 劫財, 食神, 傷官, 偏財, 正財, 偏官, 正官, 偏印, 正印, 四柱, 命理, 藏干, 沖, 刑)와 오행·천간·지지의 12개 한자(木·火·土·金·水 / 甲·乙·丙·丁·戊·己·庚·辛·壬·癸 / 子·丑·寅·卯·辰·巳·午·未·申·酉·戌·亥) 외에는 절대 사용하지 마십시오. 특히 사용자의 성씨·이름·원국 한자를 모양이 비슷한 다른 글자(예: 卞을 變으로, 池를 地로, 秀를 穗로)로 바꿔 쓰면 절대 안 됩니다.
"""


def generate_section_intro(saju_context, form_data, call_designation='우리 아이', saju_result=None):
    """보고서 도입부 — 사주 분석과 작명 방향"""
    allowed_block = _build_allowed_hanja_block(saju_result, form_data) if saju_result else ''
    prompt = f"""다음 사주 정보를 바탕으로 작명 보고서의 도입부를 작성하십시오.

{saju_context}
{allowed_block}
【호칭 규칙】 대상을 부를 때 '{call_designation}'라고만 쓰십시오. '신생아', '대상자', '아기', '자녀' 등은 쓰지 마십시오.

아래 네 가지 내용을 분석적 격식체로 서술하십시오. 모든 문단은 원국(原局) 데이터에서 출발하고, 천간·지지·오행은 한자를 병기하십시오.

첫째, 본 보고서의 분석 체계를 서술하십시오. 사주명리학(四柱命理學), 음성학적 분석, 수리오행(數理五行), 자원오행(字源五行), 음령오행(音靈五行) 등 적용된 학문적 근거를 객관적으로 기술하십시오.

둘째, {call_designation}의 원국 구조를 정밀 진단하십시오. 일간(日干)의 오행 속성과 강약, 년주·월주·일주·시주 각 기둥의 천간(天干)과 지지(地支)가 어떤 생극제화(生剋制化) 관계를 형성하는지, 타고난 기질과 잠재력은 어떠한지 원국 한자를 직접 인용하며 분석하십시오.

셋째, 오행(五行) 분포를 분석하십시오. 木·火·土·金·水 각각의 수량과 비율, 과다한 오행과 부족한 오행이 실제 삶에서 어떤 경향으로 나타나는지, 지지 장간(藏干)까지 포함한 심층 분석을 서술하십시오.

넷째, 용신(用神)·희신(喜神) 분석과 작명 방향을 제시하십시오. 부족한 오행을 이름의 어떤 요소로 보완할 것인지, 음령오행(초성 오행)의 상생 흐름(성씨→이름 첫 글자→둘째 글자), 자원오행의 상생 구조를 학문적 근거와 함께 서술하십시오.

각 내용마다 **소제목** 형식의 소제목을 다십시오. 소제목은 짧은 명사구로(예: "원국의 구조와 기질", "오행 분포와 편중", "용신과 작명 방향"). 번호 목록, bullet point는 절대 금지입니다."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)


def generate_name_analysis(saju_context, name_context, name_index, call_designation='우리 아이',
                           daeun_result=None, saju_result=None, name_info=None, form_data=None):
    """이름 상세 분석 — 시나리오 기반 설득 구조"""
    daeun_info = ''
    if daeun_result:
        cp = daeun_result.get('current_period', {})
        future = daeun_result.get('future_turning_points', [])
        daeun_info = f"""
[현재 대운] {cp.get('ganji', '')}({cp.get('ganji_kr', '')}) {cp.get('stem_ohaeng', '')}/{cp.get('branch_ohaeng', '')}
[향후 전환점] {future[0]['age_start'] if future else '없음'}세경"""

    allowed_block = ''
    if saju_result and name_info:
        allowed_block = _build_allowed_hanja_block(saju_result, form_data, names=name_info)

    prompt = f"""다음 사주 정보와 이름 후보를 바탕으로 해당 이름의 상세 분석을 작성하십시오.

{saju_context}

{name_context}
{daeun_info}
{allowed_block}
【호칭 규칙】 대상을 부를 때 '{call_designation}'라고만 쓰십시오.
【이름 후보 호칭 규칙】 후보 이름은 반드시 '이름 후보인 ㅇㅇㅇ은/는'으로 쓰십시오.

아래 내용을 분석적 격식체로 서술하십시오. 모든 문단은 원국 데이터와 이름의 구체적 구성 요소에서 출발하십시오.

첫째, 이 이름이 원국의 부족한 오행을 어떻게 보완하는지 분석하십시오. 자원오행과 음령오행 각각의 상생 구조를 한자와 함께 서술하고, 이 보완이 {call_designation}의 성격 경향, 대인 관계, 직업적 측면에서 어떤 변화로 이어질 수 있는지 구체적으로 기술하십시오.

둘째, 현재 대운(大運) 및 향후 전환기와 이 이름의 오행 구성이 어떤 관계를 형성하는지 분석하십시오. 대운의 천간·지지 오행과 이름의 오행이 어떻게 작용하는지, 전환기에 이 이름의 오행이 어떤 역할을 할 수 있는지 서술하십시오.

셋째, 음성학적 분석을 서술하십시오. 초성·중성·종성의 조합이 만드는 음가(音價)의 특성, 성씨와의 발음 연결, 청각적 인상을 음성학적 관점에서 분석하십시오.

넷째, 한자(漢字) 자의(字意) 분석을 서술하십시오. 각 글자의 본래 뜻, 자원(字源), 고전에서의 용례, 두 글자가 결합했을 때의 의미 구조를 상세히 기술하십시오.

다섯째, 이 이름이 원국 구조에 대해 갖는 고유한 적합성을 분석하십시오. 수리오행, 음양 배치, 충·형 관계 등을 종합하여 이 이름만의 특징적 강점을 서술하십시오.

각 내용마다 **소제목** 형식의 소제목을 다십시오. 소제목은 짧은 명사구로(예: "선정 근거와 오행 보완", "음성학적 특성", "한자의 자의 분석"). 번호 목록, bullet point, 이모지는 절대 금지입니다."""

    validator = None
    if saju_result and name_info:
        validator = _make_name_validator(saju_result, name_info, form_data or {})
    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=8000, min_length=500, validator=validator)


def generate_final_comparison(saju_context, all_names_context, call_designation='우리 아이', daeun_result=None,
                              saju_result=None, names=None, form_data=None):
    """최종 비교·추천 — 선택 압박 구조"""
    daeun_info = ''
    if daeun_result:
        cp = daeun_result.get('current_period', {})
        daeun_info = f"\n[현재 대운] {cp.get('ganji', '')}({cp.get('ganji_kr', '')}) — 이 시기에 가장 필요한 오행 보완을 고려하여 추천하십시오."

    allowed_block = ''
    if saju_result and names:
        allowed_block = _build_allowed_hanja_block(saju_result, form_data, names=names)

    prompt = f"""다음 사주 정보와 3개 후보 이름을 바탕으로 최종 비교 분석을 작성하십시오.

{saju_context}

{all_names_context}
{daeun_info}
{allowed_block}
【호칭 규칙】 대상을 부를 때 '{call_designation}'라고만 쓰십시오.
【이름 후보 호칭 규칙】 후보 이름은 반드시 '이름 후보인 ㅇㅇㅇ은/는'으로 쓰십시오.

세 후보 이름을 원국 구조에 대한 적합도를 기준으로 비교 분석하십시오.

첫째, 각 이름이 원국의 오행 편중을 어떤 방식으로 보완하는지 비교하십시오. 이름별로 자원오행·음령오행의 상생 구조가 어떻게 다르고, 그 차이가 {call_designation}의 삶에서 어떤 경향의 차이로 나타날 수 있는지 서술하십시오.

둘째, 사주 보완력을 객관적으로 비교하십시오. 용신·희신 반영도, 오행 균형, 음령오행 상생, 자원오행 상생, 충(沖)·형(刑) 여부를 종합하여 순위를 매기십시오.

셋째, 수리오행(數理五行)과 음성학적 안정성을 기준으로 세 이름을 비교 분석하십시오.

넷째, {call_designation}의 원국 구조를 고려했을 때 작명에서 가장 중요한 기준 2가지를 제시하고, 그 기준에 비추어 최적의 이름이 무엇인지 논리적으로 서술하십시오.

다섯째, 최종 추천 이름이 {call_designation}의 원국에서 부족한 기운을 어떻게 보완하며, 향후 대운 흐름에서 어떤 역할을 할 수 있는지를 종합하여 마무리하십시오.

각 내용마다 **소제목** 형식의 소제목을 다십시오. 소제목은 짧은 명사구로(예: "세 후보의 오행 보완 비교", "종합 순위와 추천"). 번호 목록, bullet point, 이모지는 절대 금지입니다."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)


def generate_section_personality(saju_context, sipsin_result, call_designation='우리 아이'):
    """섹션 2: 성격 심층 진단 — 십신 기반 개인화 분석"""
    sc = sipsin_result['sipsin_count']
    prominent = sipsin_result['prominent']
    lacking = sipsin_result['lacking']

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

【호칭 규칙】 대상을 부를 때 '{call_designation}'라고만 쓰십시오.

다음은 {call_designation}의 십신(十神) 분석 결과입니다:
{prominent_info}
{lacking_info}

위 데이터를 바탕으로 {call_designation}의 성격 구조를 분석적 격식체로 서술하십시오. 모든 분석은 원국의 십신 배치에서 출발하며, 한자를 병기하십시오.

첫째, 두드러진 십신을 근거로 {call_designation}의 핵심 성격 구조를 분석하십시오. 각 십신이 원국에서 어떤 위치에 있으며, 그것이 일상의 판단 방식, 행동 양식, 감정 처리에서 어떤 경향으로 나타나는지 구체적으로 서술하십시오.

둘째, {call_designation}의 대인관계 패턴을 십신 구조에서 도출하십시오. 비겁(比劫), 식상(食傷), 재성(財星), 관성(官星), 인성(印星) 각각의 분포가 친밀한 관계, 사회적 관계에서 어떤 양상으로 나타나는지 분석하십시오.

셋째, 원국의 십신 구조에서 적합한 직업 영역을 도출하십시오. 단순 나열이 아니라, 해당 십신이 왜 그 직업 영역과 부합하는지 명리학적 근거를 서술하십시오.

넷째, 부족한 십신이 만드는 기운의 결핍을 분석하고, 이것이 작명 방향에 어떤 시사점을 주는지 연결하십시오.

각 내용마다 **소제목** 형식의 소제목을 다십시오. 소제목은 짧은 명사구로(예: "타고난 성격의 핵심", "대인관계의 구조적 특징", "부족한 기운과 작명 방향"). 번호 목록, bullet point는 절대 금지입니다."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)


def generate_section_life_flow(saju_context, daeun_result, call_designation='우리 아이'):
    """섹션 3: 인생 흐름 예측 — 대운 기반 과거 맞추기 + 미래 전환점"""
    current_age = daeun_result['current_age']
    current_period = daeun_result.get('current_period')
    past_turning = daeun_result.get('past_turning_points', [])
    future_turning = daeun_result.get('future_turning_points', [])

    daeun_timeline = ''
    for p in daeun_result['periods']:
        marker = ''
        if p['is_turning_point']:
            marker = f' [전환점: {p["turning_reason"]}]'
        if current_period and p['index'] == current_period['index']:
            marker += ' <- 현재'
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

【호칭 규칙】 대상을 부를 때 '{call_designation}'라고만 부르세요.

다음은 {call_designation}의 대운(大運) 분석 결과입니다:
방향: {daeun_result['direction']} / 시작나이: {daeun_result['start_age']}세 / 현재 나이: {current_age}세

[대운 타임라인]{daeun_timeline}

[과거 주요 전환점]{past_events}

[미래 주요 전환점]{future_events}

위 데이터를 바탕으로 {call_designation}의 대운 흐름을 분석적 격식체로 서술하십시오. 모든 분석은 원국과 대운의 천간·지지 상호작용에서 출발하며, 한자를 병기하십시오.

첫째, 대운의 전체 흐름을 서술하십시오. {daeun_result['direction']} 대운의 명리학적 의미, 원국과의 관계, 인생 전반에 걸친 기운의 흐름을 분석하십시오.

둘째, 과거 대운의 전환점을 분석하십시오. 대운의 오행 변화가 원국의 구조와 어떤 생극(生剋) 관계를 형성했으며, 그것이 어떤 삶의 경향으로 나타났을 수 있는지 서술하십시오.

셋째, 현재 대운을 정밀 분석하십시오. 현재 대운의 천간·지지가 원국의 일간 및 각 기둥과 어떤 관계를 맺고 있으며, {call_designation}이 현재 겪고 있을 수 있는 기운의 특성을 서술하십시오.

넷째, 향후 대운 전환점과 그에 따른 기운의 변화를 분석하십시오. 어떤 오행이 유입되며, 원국과 어떤 상호작용이 예상되는지 구체적으로 서술하십시오.

다섯째, 대운 흐름에서 이름의 오행이 갖는 기능을 서술하십시오. 불리한 대운기에 이름의 오행이 어떤 완충 역할을 하고, 유리한 대운기에 어떤 상승 작용을 할 수 있는지 명리학적 근거와 함께 기술하십시오.

각 내용마다 **소제목** 형식의 소제목을 다십시오. 소제목은 짧은 명사구로(예: "대운의 전체 흐름", "현재 대운의 기운", "향후 전환점과 대비"). 번호 목록, bullet point는 절대 금지입니다."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)


def generate_section_usage_guide(saju_context, daeun_result, recommended_name, call_designation='우리 아이'):
    """섹션 8: 이름 사용 가이드 — 프리미엄 의식(ritual) 연출"""
    current_period = daeun_result.get('current_period', {})

    next_good_period = ''
    for p in daeun_result['periods']:
        if p['age_start'] > daeun_result['current_age'] and not p.get('turning_reason', '').startswith('기신'):
            next_good_period = f"{p['age_start']}세({p['ganji']} {p['ganji_kr']})"
            break

    prompt = f"""{saju_context}

【호칭 규칙】 대상을 부를 때 '{call_designation}'라고만 부르세요.

최종 추천된 이름은 '{recommended_name}'입니다.
현재 대운: {current_period.get('ganji', '')}({current_period.get('ganji_kr', '')}) {current_period.get('stem_ohaeng', '')}/{current_period.get('branch_ohaeng', '')}
향후 좋은 시기: {next_good_period}

이 이름의 실제 사용에 관한 실용적 안내를 분석적 격식체로 작성하십시오. 모든 권고는 원국 구조와 대운 흐름에서 도출된 명리학적 근거에 기반하십시오.

첫째, 개명 또는 이름 사용의 최적 시기를 서술하십시오. 현재 대운의 천간·지지와 원국의 관계를 고려하여, 적합한 시기를 계절·월·요일 수준까지 구체적으로 제시하고 그 명리학적 근거를 기술하십시오.

둘째, 새 이름의 최초 사용 절차를 안내하십시오. 첫 서명의 명리학적 의미, 공적 문서 변경 순서(주민등록→면허→여권→금융기관), 그 과정에서 유의할 사항을 서술하십시오.

셋째, 주변에 새 이름을 알리는 순서와 방법을 서술하십시오. 가족→지인→직장→공적 관계 순의 합리적 근거를 기술하십시오.

넷째, 원국의 오행 편중 및 충(沖)·형(刑) 관계를 고려한 생활상의 유의 사항을 서술하십시오. 방위, 색상, 생활 습관 등에서 부족한 오행을 보완하거나 충 관계를 피하는 구체적 방법을 기술하십시오.

다섯째, 이름 변경 후 오행 보완의 효과가 나타나는 시간적 경과를 서술하십시오. 1개월, 3개월, 1년, 3년 단위로 오행 보완이 어떤 영역에서 어떤 형태로 나타날 수 있는지 구체적으로 기술하십시오.

여섯째, 이름에 담긴 오행의 기운을 일상에서 강화하는 실천 방법을 3가지 이상 제시하십시오. 색상 활용, 방위, 계절별 주의점 등을 이름의 오행 구성과 연결하여 서술하십시오.

각 내용마다 **소제목** 형식의 소제목을 다십시오. 소제목은 짧은 명사구로(예: "개명의 최적 시기", "공적 문서 변경 순서", "오행 강화를 위한 생활 습관"). 번호 목록, bullet point는 절대 금지입니다."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=8000, min_length=500)


def generate_full_report(saju_result, names, form_data):
    """전체 보고서 생성 (8회 API 호출)"""
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
    intro = generate_section_intro(saju_context, form_data, call_designation, saju_result=saju_result)
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

        analysis = generate_name_analysis(saju_context, name_context, i + 1, call_designation, daeun_result,
                                          saju_result=saju_result, name_info=name, form_data=form_data)
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
    comparison = generate_final_comparison(saju_context, all_names_context, call_designation, daeun_result,
                                           saju_result=saju_result, names=names, form_data=form_data)
    report['sections'].append({
        'title': '최종 추천 및 선택 가이드',
        'content': comparison,
        'type': 'comparison'
    })

    # 섹션 8: 이름 사용 가이드
    report['progress'] = 90
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


def generate_report_streaming(saju_result, names, form_data):
    """스트리밍 보고서 생성 (제너레이터) — 8섹션"""
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
    intro = generate_section_intro(saju_context, form_data, call_designation, saju_result=saju_result)
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
        analysis = generate_name_analysis(saju_context, name_context, i + 1, call_designation, daeun_result,
                                          saju_result=saju_result, name_info=name, form_data=form_data)

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
    comparison = generate_final_comparison(saju_context, all_names_context, call_designation, daeun_result,
                                           saju_result=saju_result, names=names, form_data=form_data)
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
