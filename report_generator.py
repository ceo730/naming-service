"""
바른이름연구소 작명 보고서 생성기 v3
- 순수 줄글(산문) 형식 보고서
- 바른이름연구소 전문가 문체
- 사주 분석 → 이름별 상세 → 최종 비교
"""

import os
import time
import openai
import json
from datetime import date
from saju_engine import calculate_sipsin, calculate_daeun, SIPSIN_TRAITS

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-4o"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ─── 안정적 API 호출 (재시도 + 딜레이) ───
_last_call_time = 0

def _call_with_retry(system_prompt, user_prompt, max_tokens, min_length=200, max_retries=3):
    """GPT 호출 + 응답이 너무 짧으면 자동 재시도, 호출 간 최소 3초 간격"""
    global _last_call_time
    for attempt in range(max_retries):
        # 호출 간 최소 3초 간격
        elapsed = time.time() - _last_call_time
        if elapsed < 3:
            time.sleep(3 - elapsed)
        _last_call_time = time.time()

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content or ''
            # 정상 응답인지 확인 (충분히 길고 거부 아님)
            is_refusal = content.startswith('죄송') or content.startswith('요청하신') or '작성할 수 없' in content
            if len(content) >= min_length and not is_refusal:
                return content
            # 너무 짧거나 거부 응답이면 재시도
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise
    return content  # 마지막 시도 결과 반환


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


def generate_section_intro(saju_context, form_data, call_designation='우리 아이'):
    """보고서 도입부 — 사주 분석과 작명 방향"""
    prompt = f"""다음 사주 정보를 바탕으로 작명 보고서의 도입부를 작성해주세요.

{saju_context}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '신생아', '대상자', '아기', '자녀' 등의 표현은 절대 사용하지 마십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 말고 '본 바른이름연구소에서는', '저희 연구소에서는' 등 기관 주어를 사용하십시오.

아래 네 가지 주제를 빠짐없이 다루되, 소제목이나 번호 없이 자연스럽게 이어지는 줄글(산문)로 작성하십시오. 각 주제를 충분히 상세하게 서술하여 전문적이고 풍성한 보고서를 만들어 주십시오.

첫 번째 주제는 이 보고서가 어떤 과정을 거쳐 이름을 선별했는지에 대한 안내입니다. 사주명리학, 음성학, 수리학, 자원오행, 음령오행 등 적용한 학문적 기반을 본 연구소의 경험과 함께 자연스럽게 소개해 주십시오.

두 번째 주제는 사주팔자의 핵심 진단입니다. 일간(日干)의 특성과 성향, 각 주(柱)의 의미와 상호작용, {call_designation}의 타고난 기질과 잠재력, 장점과 보완이 필요한 부분을 상세히 분석해 주십시오.

세 번째 주제는 오행 분포의 불균형 분석입니다. 木火土金水 각각의 분포를 살피고, 과다하거나 부족한 오행이 삶에 미치는 구체적 영향, 장간(藏干)까지 고려한 심층 분석, 음양의 조화를 진단해 주십시오.

네 번째 주제는 이름으로 보완해야 할 방향입니다. 용신과 희신을 구체적으로 설명하고, 이름에 담아야 할 오행의 방향을 제시하십시오. 특히 음령 오행(초성 오행)이 성씨에서 이름 첫 글자, 이름 둘째 글자로 상생의 흐름을 이루어야 하는 이유와 전략, 한자 자원 오행의 상생 흐름도 함께 설명해 주십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오. 번호 목록, bullet point는 절대 사용하지 마십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)


def generate_name_analysis(saju_context, name_context, name_index, call_designation='우리 아이'):
    """이름 상세 분석 — 순수 산문 형식"""
    prompt = f"""다음 사주 정보와 이름 후보를 바탕으로 이 이름에 대한 상세 분석을 작성해주세요.

{saju_context}

{name_context}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 말고 '본 바른이름연구소에서는', '저희 연구소에서는' 등 기관 주어를 사용하십시오.
【이름 후보 호칭 규칙】 후보 이름을 언급할 때 절대로 '이름인 ㅇㅇㅇ은/는'이라고 쓰지 마십시오. 아직 확정된 이름이 아니라 후보이므로 반드시 '이름 후보인 ㅇㅇㅇ은/는'이라고 쓰십시오. 예시: '{call_designation}의 이름 후보인 서연이는' (O), '{call_designation}의 이름인 서연이는' (X).

이 이름에 대해 아래 주제들을 모두 빠짐없이 다루되, 소제목이나 번호 없이 자연스럽게 이어지는 줄글(산문)로 작성하십시오. 전문가로서 각 주제를 깊이 있고 풍부하게 서술하여, 고객이 이름의 가치를 충분히 이해할 수 있도록 해주십시오.

이름의 첫인상과 전체적 이미지, 이 이름을 처음 들었을 때 떠오르는 느낌과 사회적 이미지로 시작하십시오. 이어서 발음의 특성과 장점을 분석하되, 초성·중성·종성의 조합이 어떤 소리의 질감을 만드는지, 부르기 편하고 기억에 남는 이유를 구체적으로 풀어쓰십시오.

이 이름이 가진 세련미와 대중성의 균형, 시대를 초월하는 클래식한 품격에 대해서도 서술하십시오. 각 한자의 본뜻과 역사적 용례, 고전에서의 의미와 현대적 재해석을 풍부하게 풀어쓰고, 두 글자가 합쳐졌을 때 어떤 시너지가 생기는지, 전체 이름이 전달하는 메시지를 서술하십시오.

사주 보완 효과에 대해서는 용신·희신과의 관계, 부족한 오행을 어떻게 보완하는지를 구체적으로 분석하십시오. 음령 오행(초성 오행) 흐름이 성씨에서 이름 첫 글자, 이름 둘째 글자로 이어지는 상생·역생·비화·상극 관계를 분석하고, 자원 오행(한자 고유 오행) 흐름도 같은 방식으로 분석하여 사주 보완과의 시너지를 서술하십시오.

이름이 {call_designation}의 성격 형성과 심리적 안정감에 미치는 영향, 대인관계와 사회적 이미지, 학업·직장·사회생활에서의 강점, 유아기부터 노년까지 생애주기별 적합성도 자연스럽게 녹여 쓰십시오.

마지막으로 이 이름의 가장 큰 장점들과 종합적 가치를 담아 마무리하십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오. 번호 목록, bullet point, 이모지는 절대 사용하지 마십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=8000, min_length=500)


def generate_final_comparison(saju_context, all_names_context, call_designation='우리 아이'):
    """최종 비교·추천 — 순수 산문 형식"""
    prompt = f"""다음 사주 정보와 3개 후보 이름을 바탕으로 최종 비교 분석을 작성하세요.

{saju_context}

{all_names_context}

【호칭 규칙】 대상을 부를 때 반드시 '{call_designation}'라고만 지칭하십시오. '필자', '제가', '나는' 등 개인을 주어로 쓰지 말고 '본 바른이름연구소에서는', '저희 연구소에서는' 등 기관 주어를 사용하십시오.
【이름 후보 호칭 규칙】 후보 이름을 언급할 때 절대로 '이름인 ㅇㅇㅇ은/는'이라고 쓰지 마십시오. 반드시 '이름 후보인 ㅇㅇㅇ은/는'이라고 쓰십시오.

세 이름을 종합적으로 비교하여 최종 추천을 제시하되, 소제목이나 번호 없이 자연스럽게 이어지는 줄글(산문)로 작성하십시오. 각 비교 항목을 구체적이고 풍부하게 서술해 주십시오.

먼저 세 이름의 수리오행, 음령 오행 흐름, 자원 오행 흐름, 발음, 한자 의미 등을 종합적으로 비교하여 안정성 측면에서 어떤 이름이 가장 뛰어난지 분석하십시오. 이어서 품격과 인상, 사회적 이미지 측면에서 세 이름을 비교하십시오.

사주 보완력 측면에서는 용신·희신 반영도, 오행 균형 기여도, 음령 오행 상생 흐름과 자원 오행 상생 흐름, 충(沖)·형(刑) 여부를 종합적으로 비교하여 {call_designation}의 사주를 가장 잘 보완하는 이름을 명확히 제시하십시오.

각 이름이 어떤 성향과 가치관, 삶의 방향에 잘 맞는지도 분석하고, {call_designation}의 사주를 고려했을 때 최종 선택 시 가장 우선해야 할 기준을 안내하십시오.

마지막에는 본 바른이름연구소의 전문가로서 종합적으로 가장 추천하는 이름을 명확히 밝히고, 그 이유를 사주, 오행, 음성학, 수리, 한자 의미 등 모든 관점에서 설득력 있게 풀어쓰십시오.

각 주제마다 반드시 **서술형 소제목** 형식의 소제목을 달고 이어서 줄글 문단을 작성하십시오. 번호 목록, bullet point, 이모지는 절대 사용하지 마십시오."""

    return _call_with_retry(SYSTEM_PROMPT, prompt, max_tokens=6000, min_length=500)


def generate_full_report(saju_result, names, form_data):
    """전체 보고서 생성 (5회 API 호출)"""
    saju_context = build_saju_context(saju_result, form_data)
    call_designation = get_call_designation(form_data)

    report = {'sections': [], 'status': 'generating', 'progress': 0, 'call_designation': call_designation}

    # 1단계: 도입부
    report['progress'] = 10
    intro = generate_section_intro(saju_context, form_data, call_designation)
    report['sections'].append({
        'title': '사주 분석 및 작명 방향',
        'content': intro,
        'type': 'intro'
    })
    report['progress'] = 25

    # 2~4단계: 이름별 분석
    all_names_context = ""
    for i, name in enumerate(names):
        name_context = build_name_context(name, i + 1)
        all_names_context += name_context + "\n"

        analysis = generate_name_analysis(saju_context, name_context, i + 1, call_designation)
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
        report['progress'] = 25 + (i + 1) * 20

    # 5단계: 최종 비교
    comparison = generate_final_comparison(saju_context, all_names_context, call_designation)
    report['sections'].append({
        'title': '최종 추천 및 선택 가이드',
        'content': comparison,
        'type': 'comparison'
    })

    report['status'] = 'complete'
    report['progress'] = 100
    return report


def generate_report_streaming(saju_result, names, form_data):
    """스트리밍 보고서 생성 (제너레이터)"""
    saju_context = build_saju_context(saju_result, form_data)
    call_designation = get_call_designation(form_data)

    yield {'type': 'progress', 'progress': 10, 'message': '사주 분석 보고서 작성 중...'}

    intro = generate_section_intro(saju_context, form_data, call_designation)
    yield {
        'type': 'section', 'progress': 25,
        'section': {'title': '사주 분석 및 작명 방향', 'content': intro, 'section_type': 'intro'}
    }

    all_names_context = ""
    for i, name in enumerate(names):
        yield {'type': 'progress', 'progress': 25 + i * 20, 'message': f'후보 이름 {i+1} "{name["hangul"]}" 분석 중...'}

        name_context = build_name_context(name, i + 1)
        all_names_context += name_context + "\n"
        analysis = generate_name_analysis(saju_context, name_context, i + 1, call_designation)

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
            'type': 'section', 'progress': 25 + (i + 1) * 20,
            'section': {'title': f'후보 이름 {i + 1}: {name["hangul"]}', 'content': analysis,
                        'section_type': 'name_analysis', 'name_card': name_card}
        }

    yield {'type': 'progress', 'progress': 90, 'message': '최종 비교 분석 작성 중...'}
    comparison = generate_final_comparison(saju_context, all_names_context, call_designation)
    yield {
        'type': 'section', 'progress': 100,
        'section': {'title': '최종 추천 및 선택 가이드', 'content': comparison, 'section_type': 'comparison'}
    }
    yield {'type': 'complete', 'progress': 100, 'message': '보고서 생성 완료!'}
