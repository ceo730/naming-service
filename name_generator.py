"""
이름 생성 엔진 v2
핵심 전략: "좋은 소리(음) 먼저 → 오행 맞는 한자 매칭"
- 성별 / 출생연도(세대) 맞춤 이름 음(音) 조합
- 대법원 인명한자 DB 연동
- 불용한자 철저 필터링
- 수리오행 / 음성학 검증
"""

import sqlite3
import os
import re
import random
import logging

logger = logging.getLogger(__name__)

from saju_engine import (
    OHAENG_LIST, OHAENG_KR, OHAENG_SANGSAENG,
    calculate_suri_ohaeng, CHEONGAN_OHAENG, check_chung_conflict, check_hyeong_conflict
)

# ─── 경로 설정 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'hanja_inmyeong.db')
BULYONG_PATH = os.path.join(BASE_DIR, 'data', '불용한자_종합리스트.md')


# ─── 주요 성씨 획수 사전 (원획법 기준, hanja_inmyeong.db와 동일 체계) ───
# 대표 한자: 金李朴崔鄭姜趙尹張林韓吳徐申權黃安宋柳劉全洪高文梁孫裴白許南
#   沈盧河郭成車朱禹具閔羅陳池嚴元千房孔玄咸卞廉石宣薛馬吉延魏表明奇潘王
#   琴玉陸印孟諸毛卓鞠呂都蘇秋卜太奉皮杜甘慶賴史承尙魚殷
SURNAME_STROKES = {
    '김': 8, '이': 7, '박': 6, '최': 11, '정': 19, '강': 9, '조': 14,
    '윤': 4, '장': 11, '임': 8, '한': 17, '오': 7, '서': 10, '신': 5,
    '권': 22, '황': 12, '안': 6, '송': 7, '류': 9, '유': 15, '전': 6,
    '홍': 10, '고': 10, '문': 4, '양': 11, '손': 10, '배': 14, '백': 5,
    '허': 11, '남': 9, '심': 8, '노': 16, '하': 9, '곽': 15, '성': 7,
    '차': 7, '주': 6, '우': 9, '구': 8, '민': 14, '나': 19, '진': 16,
    '지': 7, '엄': 20, '원': 4, '천': 3, '방': 4, '공': 4, '현': 5,
    '함': 9, '변': 4, '염': 13, '석': 5, '선': 9, '설': 19, '마': 10,
    '길': 6, '연': 7, '위': 18, '표': 8, '명': 8, '기': 8, '반': 16,
    '왕': 4, '금': 13, '옥': 5, '육': 16, '인': 6, '맹': 8, '제': 16,
    '모': 4, '탁': 8, '국': 11, '여': 7, '도': 16, '소': 22, '추': 9,
    '복': 2, '태': 4, '봉': 8, '피': 5, '두': 7, '감': 5, '경': 15,
    '뢰': 16, '사': 5, '승': 8, '상': 8, '어': 11, '은': 10,
    '편': 4, '용': 16, '예': 10, '음': 16, '빈': 11, '채': 17,
}

def get_surname_strokes(surname):
    strokes = SURNAME_STROKES.get(surname)
    if strokes is None:
        logger.warning(f"미등록 성씨 '{surname}': 획수를 DB에서 조회합니다")
        # DB에서 동명 한자 중 가장 일반적인 획수로 폴백
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT total_strokes FROM hanja WHERE hangul=? ORDER BY total_strokes LIMIT 1",
                (surname,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
        except Exception:
            pass
        finally:
            if conn:
                conn.close()
        logger.warning(f"미등록 성씨 '{surname}': DB에도 없어 기본값 8 사용")
        return 8
    return strokes


# ═══════════════════════════════════════════════════════
# 불용한자
# ═══════════════════════════════════════════════════════
def load_bulyong_hanja():
    bulyong_set = set()
    if not os.path.exists(BULYONG_PATH):
        return bulyong_set
    with open(BULYONG_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'\|\s*([一-鿿㐀-䶿])\s*\|'
    for hanja in re.findall(pattern, content):
        bulyong_set.add(hanja)
    return bulyong_set

BULYONG_SET = load_bulyong_hanja()


# ═══════════════════════════════════════════════════════
# 세대별 · 성별 이름 음(音) 패턴
# ═══════════════════════════════════════════════════════

# 2020년대생 신생아
NAME_PATTERNS_BABY_MALE = [
    ('시', '우'), ('하', '준'), ('도', '윤'), ('서', '준'), ('은', '우'),
    ('이', '준'), ('지', '호'), ('시', '윤'), ('주', '원'), ('하', '율'),
    ('지', '안'), ('건', '우'), ('현', '우'), ('유', '준'), ('민', '준'),
    ('은', '찬'), ('이', '찬'), ('지', '원'), ('수', '호'), ('태', '윤'),
    ('준', '혁'), ('승', '현'), ('도', '현'), ('예', '준'), ('연', '우'),
    ('시', '현'), ('규', '민'), ('정', '우'), ('윤', '호'), ('채', '민'),
    ('서', '윤'), ('준', '서'), ('지', '한'), ('우', '진'), ('현', '준'),
    ('시', '준'), ('도', '준'), ('하', '진'), ('재', '윤'), ('민', '호'),
    ('서', '진'), ('승', '우'), ('지', '윤'), ('유', '찬'), ('태', '준'),
    ('하', '민'), ('건', '호'), ('준', '우'), ('윤', '서'), ('현', '서'),
]

NAME_PATTERNS_BABY_FEMALE = [
    ('서', '아'), ('하', '윤'), ('지', '유'), ('서', '윤'), ('지', '안'),
    ('하', '은'), ('서', '연'), ('수', '아'), ('지', '아'), ('다', '은'),
    ('아', '린'), ('채', '원'), ('윤', '서'), ('예', '린'), ('소', '율'),
    ('나', '은'), ('하', '린'), ('시', '은'), ('유', '나'), ('이', '서'),
    ('다', '인'), ('예', '나'), ('지', '윤'), ('수', '빈'), ('민', '서'),
    ('채', '은'), ('소', '윤'), ('가', '은'), ('하', '연'), ('예', '서'),
    ('서', '현'), ('하', '율'), ('지', '수'), ('수', '연'), ('채', '아'),
    ('윤', '아'), ('소', '은'), ('예', '은'), ('나', '윤'), ('서', '은'),
    ('하', '영'), ('지', '은'), ('다', '윤'), ('수', '현'), ('민', '아'),
    ('예', '원'), ('소', '현'), ('채', '린'), ('유', '진'), ('시', '아'),
]

# 1990~2010년대생 (개명 대상)
NAME_PATTERNS_YOUNG_MALE = [
    ('민', '준'), ('서', '준'), ('지', '훈'), ('현', '우'), ('승', '민'),
    ('도', '현'), ('준', '영'), ('지', '성'), ('태', '현'), ('성', '민'),
    ('재', '혁'), ('정', '민'), ('건', '호'), ('민', '수'), ('동', '현'),
    ('상', '현'), ('재', '민'), ('준', '호'), ('시', '영'), ('지', '원'),
    ('승', '현'), ('현', '진'), ('도', '영'), ('우', '진'), ('태', '민'),
    ('준', '수'), ('재', '원'), ('서', '현'), ('한', '결'), ('지', '환'),
]

NAME_PATTERNS_YOUNG_FEMALE = [
    ('수', '진'), ('지', '연'), ('민', '지'), ('예', '진'), ('서', '영'),
    ('하', '나'), ('유', '진'), ('수', '빈'), ('지', '현'), ('혜', '원'),
    ('소', '영'), ('은', '지'), ('민', '서'), ('유', '나'), ('채', '원'),
    ('지', '은'), ('서', '현'), ('예', '원'), ('다', '영'), ('지', '수'),
    ('소', '연'), ('수', '현'), ('민', '영'), ('하', '영'), ('예', '지'),
    ('윤', '아'), ('소', '희'), ('가', '영'), ('서', '연'), ('나', '연'),
]

# 1960~1980년대생 (개명 대상)
NAME_PATTERNS_MIDDLE_MALE = [
    ('정', '호'), ('승', '현'), ('재', '혁'), ('도', '현'), ('현', '수'),
    ('태', '호'), ('우', '성'), ('지', '환'), ('민', '혁'), ('성', '호'),
    ('상', '원'), ('건', '영'), ('영', '수'), ('준', '호'), ('재', '원'),
    ('한', '수'), ('승', '호'), ('재', '영'), ('동', '수'), ('지', '훈'),
]

NAME_PATTERNS_MIDDLE_FEMALE = [
    ('수', '현'), ('지', '연'), ('은', '영'), ('서', '영'), ('혜', '진'),
    ('미', '영'), ('지', '현'), ('소', '영'), ('혜', '원'), ('수', '진'),
    ('은', '수'), ('민', '정'), ('수', '연'), ('유', '진'), ('하', '영'),
    ('예', '진'), ('서', '연'), ('지', '수'), ('나', '영'), ('채', '원'),
]


def get_name_patterns(gender, birth_year, request_type='신생아 작명'):
    """성별 + 세대에 맞는 이름 패턴 반환"""
    if request_type == '개명':
        if birth_year >= 1990:
            return NAME_PATTERNS_YOUNG_MALE if gender == '남' else NAME_PATTERNS_YOUNG_FEMALE
        else:
            return NAME_PATTERNS_MIDDLE_MALE if gender == '남' else NAME_PATTERNS_MIDDLE_FEMALE

    # 신생아 작명
    if birth_year >= 2015:
        return NAME_PATTERNS_BABY_MALE if gender == '남' else NAME_PATTERNS_BABY_FEMALE
    elif birth_year >= 1990:
        return NAME_PATTERNS_YOUNG_MALE if gender == '남' else NAME_PATTERNS_YOUNG_FEMALE
    else:
        return NAME_PATTERNS_MIDDLE_MALE if gender == '남' else NAME_PATTERNS_MIDDLE_FEMALE


# ═══════════════════════════════════════════════════════
# 한글 음성학 분석
# ═══════════════════════════════════════════════════════

CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
           'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

# ─── 초성 오행 (음령 오행) 매핑 ───
CHOSUNG_OHAENG = {
    'ㄱ': '木', 'ㅋ': '木', 'ㄲ': '木',
    'ㄴ': '火', 'ㄷ': '火', 'ㅌ': '火', 'ㄹ': '火', 'ㄸ': '火',
    'ㅇ': '土', 'ㅎ': '土',
    'ㅅ': '金', 'ㅈ': '金', 'ㅊ': '金', 'ㅆ': '金', 'ㅉ': '金',
    'ㅁ': '水', 'ㅂ': '水', 'ㅍ': '水', 'ㅃ': '水',
}

# ─── 오행 상생/상극 관계 (음령 오행 평가용) ───
OHAENG_SANGSAENG_SET = {('木', '火'), ('火', '土'), ('土', '金'), ('金', '水'), ('水', '木')}
OHAENG_SANGGEUK_SET = {('木', '金'), ('金', '木'), ('木', '土'), ('土', '木'),
                       ('火', '水'), ('水', '火'), ('火', '金'), ('金', '火'),
                       ('土', '水'), ('水', '土')}
JUNGSUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ',
            'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
JONGSUNG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ',
            'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
            'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
YANG_VOWELS = {'ㅏ', 'ㅗ', 'ㅑ', 'ㅛ', 'ㅘ', 'ㅙ', 'ㅚ'}
EUM_VOWELS = {'ㅓ', 'ㅜ', 'ㅕ', 'ㅠ', 'ㅝ', 'ㅞ', 'ㅟ'}


def decompose_hangul(char):
    if not ('가' <= char <= '힣'):
        return None
    code = ord(char) - 0xAC00
    return CHOSUNG[code // (21 * 28)], JUNGSUNG[(code % (21 * 28)) // 28], JONGSUNG[code % 28]


def get_vowel_type(vowel):
    if vowel in YANG_VOWELS: return '양'
    if vowel in EUM_VOWELS: return '음'
    return '중'


def evaluate_phonetics(surname, name_chars):
    """음성학 평가 (0~100)"""
    full_name = surname + ''.join(name_chars)
    decomposed = [decompose_hangul(c) for c in full_name]
    decomposed = [d for d in decomposed if d]
    if not decomposed:
        return 50, "분석 불가"

    score = 70
    details = []

    # 1. 모음조화
    vtypes = [get_vowel_type(d[1]) for d in decomposed]
    yang_c = vtypes.count('양')
    eum_c = vtypes.count('음')
    if yang_c > 0 and eum_c > 0 and abs(yang_c - eum_c) <= 1:
        score += 10
        details.append("음양 모음 조화 우수")
    elif (yang_c > 0 and eum_c == 0) or (eum_c > 0 and yang_c == 0):
        score += 5
        details.append("모음 통일감")

    # 2. 초성 다양성
    chos = [d[0] for d in decomposed]
    if len(set(chos)) == len(chos):
        score += 10
        details.append("초성 모두 다름")
    if len(chos) > 1 and chos[0] == chos[1]:
        score -= 10
        details.append("성-이름 초성 동일")

    # 3. 연음/자음 충돌
    for i in range(len(decomposed) - 1):
        jong = decomposed[i][2]
        next_cho = decomposed[i + 1][0]
        if jong and next_cho == 'ㅇ':
            score += 3
        elif jong and jong == next_cho:
            score -= 5

    # 4. 종성 리듬
    jongs = [bool(d[2]) for d in decomposed]
    if len(jongs) >= 3:
        if jongs == [True, False, True] or jongs == [False, True, False]:
            score += 5
        if jongs == [True, True, True]:
            score -= 5

    return max(0, min(100, score)), '; '.join(details) if details else "표준적 발음"


# ═══════════════════════════════════════════════════════
# 음령 오행 (초성 오행 상생 흐름) 평가
# ═══════════════════════════════════════════════════════

def get_chosung_ohaeng(char):
    """한글 글자의 초성 오행 반환"""
    d = decompose_hangul(char)
    if d:
        return CHOSUNG_OHAENG.get(d[0], '土')
    return '土'


# 겹받침 → 첫 자음 매핑
_COMPOUND_JONGSUNG_FIRST = {
    'ㄳ': 'ㄱ', 'ㄵ': 'ㄴ', 'ㄶ': 'ㄴ', 'ㄺ': 'ㄹ', 'ㄻ': 'ㄹ',
    'ㄼ': 'ㄹ', 'ㄽ': 'ㄹ', 'ㄾ': 'ㄹ', 'ㄿ': 'ㄹ', 'ㅀ': 'ㄹ', 'ㅄ': 'ㅂ',
}


def get_jongsung_ohaeng(char):
    """한글 글자의 종성(받침) 오행 반환. 받침 없으면 None."""
    d = decompose_hangul(char)
    if not d or not d[2]:
        return None
    jong = d[2]
    if jong in CHOSUNG_OHAENG:
        return CHOSUNG_OHAENG[jong]
    first = _COMPOUND_JONGSUNG_FIRST.get(jong)
    if first:
        return CHOSUNG_OHAENG.get(first, '土')
    return '土'


def _evaluate_ohaeng_chain(ohaengs):
    """오행 체인 평가 (내부 헬퍼). Returns (score, details_list)"""
    score = 60
    details = []
    pair_scores = []

    for i in range(len(ohaengs) - 1):
        a, b = ohaengs[i], ohaengs[i + 1]
        pair = (a, b)
        reverse_pair = (b, a)

        if pair in OHAENG_SANGSAENG_SET and reverse_pair not in OHAENG_SANGSAENG_SET:
            pair_scores.append(20)
            details.append(f"{a}→{b} 상생")
        elif reverse_pair in OHAENG_SANGSAENG_SET and pair not in OHAENG_SANGSAENG_SET:
            pair_scores.append(10)
            details.append(f"{a}→{b} 역생")
        elif a == b:
            pair_scores.append(5)
            details.append(f"{a}={b} 비화")
        elif pair in OHAENG_SANGGEUK_SET:
            pair_scores.append(-20)
            details.append(f"{a}↔{b} 상극")
        else:
            pair_scores.append(0)

    score += sum(pair_scores)

    if all(ps == 20 for ps in pair_scores) and len(pair_scores) >= 2:
        score += 10
        details.append("완벽 상생 흐름")

    return max(0, min(100, score)), details


def evaluate_eumryeong_ohaeng(surname, name_chars):
    """
    음령 오행 평가 (0~100)
    성→이름1→이름2 초성 오행 상생 관계 평가
    종성 경로도 함께 고려하여 더 좋은 경로 선택
    """
    name_ohaengs = [get_chosung_ohaeng(c) for c in name_chars]

    # 초성 경로
    cho_ohaeng = get_chosung_ohaeng(surname)
    cho_chain = [cho_ohaeng] + name_ohaengs
    cho_score, cho_details = _evaluate_ohaeng_chain(cho_chain)

    # 종성 경로 (받침이 있는 경우)
    jong_ohaeng = get_jongsung_ohaeng(surname)
    if jong_ohaeng and jong_ohaeng != cho_ohaeng:
        jong_chain = [jong_ohaeng] + name_ohaengs
        jong_score, jong_details = _evaluate_ohaeng_chain(jong_chain)

        if jong_score > cho_score:
            flow_str = '→'.join(jong_chain)
            detail_str = f"{flow_str} (종성경로: {'; '.join(jong_details)})" if jong_details else f"{flow_str} (종성경로)"
            return jong_score, detail_str, flow_str

    # 초성 경로 사용
    flow_str = '→'.join(cho_chain)
    detail_str = f"{flow_str} ({'; '.join(cho_details)})" if cho_details else flow_str
    return cho_score, detail_str, flow_str


def sort_patterns_by_eumryeong(patterns, surname):
    """
    성씨 초성/종성 오행 기준으로 상생 패턴 우선 정렬
    같은 점수 내에서는 랜덤 셔플 (다양성 유지)
    """
    surname_cho_ohaeng = get_chosung_ohaeng(surname)
    surname_jong_ohaeng = get_jongsung_ohaeng(surname)

    def _pair_score(start_oh, target_oh):
        if (start_oh, target_oh) in OHAENG_SANGSAENG_SET:
            return 20
        elif (target_oh, start_oh) in OHAENG_SANGSAENG_SET:
            return 10
        elif start_oh == target_oh:
            return 5
        elif (start_oh, target_oh) in OHAENG_SANGGEUK_SET:
            return -20
        return 0

    def pattern_score(pattern):
        r1, r2 = pattern
        r1_oh = get_chosung_ohaeng(r1)
        r2_oh = get_chosung_ohaeng(r2)

        # 초성 경로
        cho_score = _pair_score(surname_cho_ohaeng, r1_oh) + _pair_score(r1_oh, r2_oh)

        # 종성 경로 (있으면 더 좋은 쪽 선택)
        if surname_jong_ohaeng and surname_jong_ohaeng != surname_cho_ohaeng:
            jong_score = _pair_score(surname_jong_ohaeng, r1_oh) + _pair_score(r1_oh, r2_oh)
            return max(cho_score, jong_score)

        return cho_score

    # 점수별로 그룹화 후 그룹 내 셔플
    scored = [(p, pattern_score(p)) for p in patterns]
    random.shuffle(scored)  # 먼저 셔플 → 같은 점수 내 랜덤성 보장
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, s in scored]


# ═══════════════════════════════════════════════════════
# 한자 DB 조회
# ═══════════════════════════════════════════════════════

# 나쁜 의미 키워드
NEGATIVE_MEANINGS = [
    '다할', '마칠', '그칠', '죽', '어두울', '슬플', '근심', '시들', '무너',
    '떨어', '빠질', '끊을', '망할', '나무이름', '풀이름', '고을이름',
    '물이름', '산이름', '별이름', '짐승', '벌레', '제사이름',
    '병들', '아플', '더러울', '가난', '천할', '미칠',
]

# 좋은 의미 키워드
POSITIVE_MEANINGS = [
    '밝', '빛', '맑', '아름', '클', '넓', '높', '슬기', '지혜',
    '어질', '바를', '글', '배울', '도울', '다스릴', '이을',
    '빼어날', '수풀', '우러를', '기를', '뛰어날', '고울',
    '편안', '굳셀', '빛날', '은혜', '상서',
    '이룰', '재주', '밝힐', '공경', '기쁨', '풍성', '새벽',
    '옳을', '곧을', '깊을', '넉넉', '후할', '도탑',
    '젖을', '윤택', '구슬', '보배', '옥',
    '붓', '노래', '시', '문장',
]

# ═══ 작명에서 가장 널리 쓰이는 대표 한자 (음별) ═══
# 이 한자들은 대폭 가산점을 받아 우선 선택됨
WELL_KNOWN_HANJA = {
    '준': ['俊', '浚', '峻', '駿'],
    '현': ['賢', '炫', '玹', '鉉', '顯'],
    '민': ['敏', '旻', '珉', '玟', '民'],
    '서': ['瑞', '書'],
    '우': ['宇', '佑', '祐', '羽'],
    '진': ['振', '晉', '眞', '珍', '辰'],
    '시': ['時', '施', '詩'],
    '도': ['道', '度'],
    '윤': ['潤', '允', '倫', '胤'],
    '재': ['載', '在', '才', '宰'],
    '한': ['翰', '漢', '瀚'],
    '호': ['浩', '皓', '豪', '鎬', '昊'],
    '태': ['泰', '太'],
    '영': ['映', '泳', '永', '瑛', '英'],
    '수': ['秀', '修', '洙', '壽'],
    '원': ['源', '遠', '瑗', '園'],
    '석': ['碩', '錫', '晳'],
    '지': ['智', '志', '知', '芝'],
    '건': ['健', '建', '乾'],
    '승': ['承', '升', '昇', '勝'],
    '혁': ['赫', '爀'],
    '찬': ['燦', '璨', '讚'],
    '연': ['然', '延', '淵', '妍', '衍'],
    '규': ['奎', '圭', '珪'],
    '하': ['夏', '河', '荷', '賀', '霞'],
    '은': ['恩', '殷', '銀'],
    '유': ['裕', '瑜', '柔', '唯'],
    '아': ['雅', '娥'],
    '예': ['藝', '禮', '睿', '譽'],
    '소': ['素', '昭', '紹', '韶'],
    '다': ['多'],
    '채': ['彩', '采'],
    '나': ['娜'],
    '린': ['璘'],
    '경': ['景', '慶', '京', '敬', '卿'],
    '혜': ['慧', '惠', '蕙'],
    '보': ['輔', '普', '保'],
    '율': ['律'],
    '빈': ['彬', '斌', '賓'],
    '가': ['嘉', '佳', '珂'],
    '세': ['世'],
    '정': ['正', '靜', '晶', '廷', '貞'],
    '성': ['成', '誠', '星', '聖'],
    '동': ['棟', '東'],
    '상': ['尙', '相', '祥', '翔'],
    '인': ['仁', '寅'],
    '희': ['熙', '禧', '曦'],
    '훈': ['勳', '薰'],
    '환': ['桓', '煥', '歡'],
    '결': ['潔'],
    '안': ['安', '晏'],
}


# ═══ 주요 성씨 자원 오행 매핑 ═══
# 종합가이드라인 기준 자원오행 (강희자전 부수 기반)
# '-' 표기된 성씨는 부수가 명확하지 않아 발음오행(초성 오행)으로 폴백
SURNAME_JAWON_OHAENG = {
    '김': '金', '이': '木', '박': '木', '최': '土', '정': '土',
    '강': '土', '조': '火', '윤': '火', '장': '木', '임': '木',
    '한': '土', '오': '土', '서': '金', '신': '土', '홍': '水',
    '권': '木', '황': '土', '안': '土', '송': '木', '류': '木',
    '유': '金', '전': '金', '고': '木', '문': '火', '양': '木',
    '손': '金', '배': '火', '백': '金', '허': '金', '남': '火',
    '심': '水', '노': '火', '하': '水', '곽': '土', '성': '金',
    '차': '火', '주': '木', '우': '土', '구': '金', '민': '木',
    '나': '木', '진': '土', '지': '水', '엄': '土', '원': '木',
    '천': '金', '방': '土', '공': '木', '현': '水', '함': '土',
    '변': '水', '염': '火', '석': '土', '선': '土', '설': '木',
    '마': '火', '길': '土', '연': '火', '위': '土', '표': '火',
    '명': '火', '기': '木', '반': '水', '왕': '土', '금': '金',
    '옥': '土', '육': '土', '인': '金', '맹': '水', '제': '金',
    '모': '水', '탁': '火', '국': '木', '여': '火', '도': '土',
    '소': '木', '추': '木', '복': '水', '태': '火', '봉': '火',
    '피': '水', '두': '木', '감': '木', '경': '火', '뢰': '金',
    '사': '金', '승': '火', '상': '金', '어': '水', '은': '金',
    '편': '木', '용': '土', '예': '木', '음': '土', '빈': '木', '채': '木',
}


def get_surname_jawon_ohaeng(surname):
    """성씨의 자원 오행 반환 (미등록 시 초성 오행 폴백)"""
    return SURNAME_JAWON_OHAENG.get(surname, get_chosung_ohaeng(surname))


# ═══ 다음자(동음이의자) 리스트 ═══
MULTI_READING_HANJA = {
    '令': ['영', '령'], '樂': ['악', '낙', '요', '락'], '率': ['솔', '율', '률'],
    '易': ['이', '역'], '切': ['절', '체'], '更': ['경', '갱'],
    '降': ['강', '항'], '數': ['수', '삭'], '省': ['성', '생'],
    '車': ['차', '거'], '說': ['설', '세', '열'], '惡': ['악', '오'],
    '度': ['도', '탁'], '參': ['참', '삼'], '行': ['행', '항'],
    '便': ['편', '변'], '復': ['복', '부'], '相': ['상', '서'],
    '見': ['견', '현'], '長': ['장', '창'],
}


def check_multi_reading(hanja_char):
    """다음자(동음이의자) 여부 확인. 해당 시 경고 메시지 반환"""
    if hanja_char in MULTI_READING_HANJA:
        readings = MULTI_READING_HANJA[hanja_char]
        return f"{hanja_char}은(는) 다음자로 {'/'.join(readings)}로 읽힐 수 있습니다"
    return None


def evaluate_jawon_ohaeng_flow(surname, name_chars_info):
    """
    자원 오행 상생 흐름 평가 (0~100)
    성씨 자원오행→이름1 자원오행→이름2 자원오행 상생 흐름
    """
    surname_jawon = get_surname_jawon_ohaeng(surname)
    ohaengs = [surname_jawon]

    for c in name_chars_info:
        # jawon_ohaeng 우선, 없으면 ohaeng 폴백
        jo = c.get('jawon_ohaeng') or c.get('ohaeng', '土')
        ohaengs.append(jo)

    score = 60
    details = []
    pair_scores = []

    for i in range(len(ohaengs) - 1):
        a, b = ohaengs[i], ohaengs[i + 1]
        pair = (a, b)
        reverse_pair = (b, a)

        if pair in OHAENG_SANGSAENG_SET and reverse_pair not in OHAENG_SANGSAENG_SET:
            pair_scores.append(20)
            details.append(f"{a}→{b} 상생")
        elif reverse_pair in OHAENG_SANGSAENG_SET and pair not in OHAENG_SANGSAENG_SET:
            pair_scores.append(10)
            details.append(f"{a}→{b} 역생")
        elif a == b:
            pair_scores.append(5)
            details.append(f"{a}={b} 비화")
        elif pair in OHAENG_SANGGEUK_SET:
            pair_scores.append(-20)
            details.append(f"{a}↔{b} 상극")
        else:
            pair_scores.append(0)

    score += sum(pair_scores)

    if all(ps == 20 for ps in pair_scores) and len(pair_scores) >= 2:
        score += 10
        details.append("완벽 상생 흐름")

    flow_str = '→'.join(ohaengs)
    detail_str = f"{flow_str} ({'; '.join(details)})" if details else flow_str

    return max(0, min(100, score)), detail_str, flow_str


def evaluate_eumyang_strokes(surname_strokes, name_chars):
    """
    음양 획수 배치 평가
    홀수=양, 짝수=음, 교차 배치(양-음-양, 음-양-음)가 이상적
    Returns: 보너스 점수 (-5 ~ +5)
    """
    strokes = [surname_strokes] + [c['strokes'] for c in name_chars]
    eumyangs = ['양' if s % 2 == 1 else '음' for s in strokes]

    if len(eumyangs) < 2:
        return 0, eumyangs

    alternating = all(eumyangs[i] != eumyangs[i - 1] for i in range(1, len(eumyangs)))
    all_same = all(ey == eumyangs[0] for ey in eumyangs)

    if alternating:
        return 5, eumyangs   # 완벽 교차
    elif all_same:
        return -5, eumyangs  # 전부 동일 (나쁨)
    else:
        return 0, eumyangs   # 부분 교차


def find_hanja_for_reading(reading_kr, ohaeng_list=None, min_strokes=3, max_strokes=20):
    """특정 음(한글)에 대해 한자 후보 조회 + 점수 매기기"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        query = """
            SELECT h.hanja, h.hangul, h.meaning, h.total_strokes, h.ohaeng, h.jawon_ohaeng
            FROM hanja h
            WHERE (h.hangul = ? OR h.hangul LIKE ? OR h.hangul LIKE ? OR h.hangul LIKE ?)
            AND h.total_strokes BETWEEN ? AND ?
            AND h.meaning IS NOT NULL AND h.meaning != ''
        """
        params = [reading_kr, f'{reading_kr},%', f'%,{reading_kr}', f'%,{reading_kr},%',
                  min_strokes, max_strokes]

        if ohaeng_list:
            placeholders = ','.join(['?' for _ in ohaeng_list])
            query += f" AND h.ohaeng IN ({placeholders})"
            params.extend(ohaeng_list)

        cursor.execute(query, params)
        results = cursor.fetchall()
    finally:
        conn.close()

    candidates = []
    for row in results:
        hanja_char, hangul_raw, meaning, strokes, ohaeng, jawon_ohaeng = row

        # 불용한자 제외
        if hanja_char in BULYONG_SET:
            continue

        # 정확한 음 매칭
        readings = [r.strip() for r in hangul_raw.split(',')]
        if reading_kr not in readings:
            continue

        # 나쁜 의미 제외
        if any(neg in meaning for neg in NEGATIVE_MEANINGS):
            continue

        # 점수 계산
        score = 30

        # ★ 대표 한자 대폭 가산 (작명에서 널리 알려진 글자)
        well_known_list = WELL_KNOWN_HANJA.get(reading_kr, [])
        if hanja_char in well_known_list:
            score += 50  # 대표 한자 최우선

        # 좋은 뜻 보너스
        pos_count = sum(1 for kw in POSITIVE_MEANINGS if kw in meaning)
        score += min(pos_count * 12, 30)

        # 획수 적정 범위 (4~16획 이상적)
        if 6 <= strokes <= 14:
            score += 10
        elif 4 <= strokes <= 5 or 15 <= strokes <= 16:
            score += 5
        elif strokes > 20:
            score -= 10

        # 의미 길이 (구체적일수록 좋음)
        if len(meaning) >= 4:
            score += 5

        # 다음자 경고
        multi_warning = check_multi_reading(hanja_char)

        candidates.append({
            'hanja': hanja_char,
            'hangul': reading_kr,
            'meaning': meaning,
            'strokes': strokes,
            'ohaeng': ohaeng,
            'jawon_ohaeng': jawon_ohaeng or ohaeng,  # jawon_ohaeng 없으면 ohaeng 폴백
            'score': max(1, score),
            'multi_reading_warning': multi_warning,
        })

    # 점수순 정렬
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates


# 한자 후보 캐시 (최대 500 항목)
_hanja_cache = {}
_HANJA_CACHE_MAX = 500

def get_best_hanja(reading_kr, ohaeng_list):
    """읽기+오행 조합에 대한 최적 한자 (캐시 사용)"""
    cache_key = (reading_kr, tuple(ohaeng_list))
    if cache_key not in _hanja_cache:
        if len(_hanja_cache) >= _HANJA_CACHE_MAX:
            _hanja_cache.clear()
        _hanja_cache[cache_key] = find_hanja_for_reading(reading_kr, ohaeng_list)
    return _hanja_cache[cache_key]


# ═══════════════════════════════════════════════════════
# 이름 생성 메인 로직
# ═══════════════════════════════════════════════════════

def generate_names(surname, gender, saju_result, preferences=None, count=3):
    """
    이름 후보 생성 (v2: 소리 먼저 → 한자 매칭)
    """
    if preferences is None:
        preferences = {}

    oa = saju_result['ohaeng_analysis']
    yongsin = oa['yongsin']
    needed = yongsin['needed_ohaeng']  # 필요 오행 (최대 3개)
    surname_strokes = get_surname_strokes(surname)

    # 출생연도 추출 (birth_date에서)
    birth_year = preferences.get('birth_year', 2024)
    request_type = preferences.get('request_type', '신생아 작명')
    name_length = int(preferences.get('name_length', 2))

    # 세대+성별 맞춤 이름 패턴
    patterns = get_name_patterns(gender, birth_year, request_type)

    # 오행 조합: 엄격 → 유연 순서 (오행 매칭은 점수 보너스로 반영)
    ohaeng_combos = []
    if len(needed) >= 2:
        ohaeng_combos = [
            ([needed[0]], [needed[1]], True),   # 둘 다 오행 매칭
            ([needed[1]], [needed[0]], True),
            ([needed[0]], [needed[0]], True),
            (needed[:2], needed[:2], True),
            ([needed[0]], None, False),          # 한쪽만 매칭
            (None, [needed[0]], False),
            (None, None, False),                 # 오행 무관 (한자 품질 우선)
        ]
    elif len(needed) == 1:
        ohaeng_combos = [
            ([needed[0]], [needed[0]], True),
            ([needed[0]], None, False),
            (None, [needed[0]], False),
            (None, None, False),
        ]
    else:
        ohaeng_combos = [(None, None, False)]

    # 일주 지지 (충 검사용)
    day_branch = saju_result.get('day_pillar', {}).get('branch', '')

    # 후보 수집
    name_candidates = []

    # 음령 오행 기준 패턴 정렬 (상생 패턴 우선)
    sorted_patterns = sort_patterns_by_eumryeong(patterns, surname)

    for r1, r2 in sorted_patterns:
        if name_length == 1:
            r2 = None

        for oh_combo in ohaeng_combos:
            oh1, oh2, is_strict = oh_combo[0], oh_combo[1], oh_combo[2]

            # 첫째 글자 한자 후보
            hanja1_list = get_best_hanja(r1, oh1) if oh1 else find_hanja_for_reading(r1)
            if not hanja1_list:
                continue

            if name_length == 1:
                for h1 in hanja1_list[:5]:
                    suri = calculate_suri_ohaeng(surname_strokes, h1['strokes'])
                    if suri['total_score'] < 50:
                        continue
                    # 수리 개별 격에 흉이 하나라도 있으면 제외
                    has_hyung = any(suri[k]['rating'][0] == '흉' for k in ['won', 'hyeong', 'yi', 'jeong'])
                    if has_hyung:
                        continue
                    ph_score, ph_detail = evaluate_phonetics(surname, [h1['hangul']])
                    eumryeong_score, eumryeong_detail, eumryeong_flow = evaluate_eumryeong_ohaeng(surname, [h1['hangul']])
                    jawon_score, jawon_detail, jawon_flow = evaluate_jawon_ohaeng_flow(surname, [h1])
                    oh_bonus = 8 if (oh1 and h1['ohaeng'] in oh1) else 0
                    chung_warnings = check_chung_conflict(day_branch, [h1['hanja']])
                    chung_penalty = -15 * len(chung_warnings)
                    hyeong_warnings = check_hyeong_conflict(day_branch, [h1['hanja']])
                    hyeong_penalty = -10 * len(hyeong_warnings)
                    ey_bonus, ey_pattern = evaluate_eumyang_strokes(surname_strokes, [h1])
                    total = (
                        h1['score'] * 0.25 +
                        suri['total_score'] * 0.25 +
                        ph_score * 0.15 +
                        eumryeong_score * 0.20 +
                        jawon_score * 0.15 +
                        oh_bonus + chung_penalty + hyeong_penalty + ey_bonus
                    )
                    name_candidates.append(_build_candidate(
                        surname, [h1], suri, ph_score, ph_detail, total,
                        eumryeong_score, eumryeong_detail, eumryeong_flow,
                        jawon_score, jawon_detail, jawon_flow,
                        chung_warnings, hyeong_warnings, ey_pattern
                    ))
                continue

            # 둘째 글자 한자 후보
            hanja2_list = get_best_hanja(r2, oh2) if oh2 else find_hanja_for_reading(r2)
            if not hanja2_list:
                continue

            # 상위 조합 시도
            for h1 in hanja1_list[:5]:
                for h2 in hanja2_list[:5]:
                    if h1['hanja'] == h2['hanja']:
                        continue

                    # 수리오행 검증
                    suri = calculate_suri_ohaeng(surname_strokes, h1['strokes'], h2['strokes'])
                    if suri['total_score'] < 50:
                        continue
                    # 수리 개별 격에 흉이 하나라도 있으면 제외
                    has_hyung = any(suri[k]['rating'][0] == '흉' for k in ['won', 'hyeong', 'yi', 'jeong'])
                    if has_hyung:
                        continue

                    # 음성학 검증
                    ph_score, ph_detail = evaluate_phonetics(surname, [h1['hangul'], h2['hangul']])
                    if ph_score < 60:
                        continue

                    # 음령 오행 평가
                    eumryeong_score, eumryeong_detail, eumryeong_flow = evaluate_eumryeong_ohaeng(
                        surname, [h1['hangul'], h2['hangul']]
                    )

                    # 자원 오행 흐름 평가
                    jawon_score, jawon_detail, jawon_flow = evaluate_jawon_ohaeng_flow(
                        surname, [h1, h2]
                    )

                    # 충(沖) 검사
                    chung_warnings = check_chung_conflict(day_branch, [h1['hanja'], h2['hanja']])
                    chung_penalty = -15 * len(chung_warnings)

                    # 형(刑) 검사
                    hyeong_warnings = check_hyeong_conflict(day_branch, [h1['hanja'], h2['hanja']])
                    hyeong_penalty = -10 * len(hyeong_warnings)

                    # 음양 획수 배치
                    ey_bonus, ey_pattern = evaluate_eumyang_strokes(surname_strokes, [h1, h2])

                    # 오행 매칭 보너스 (용신/희신 오행과 맞으면 가산)
                    oh_bonus = 0
                    if needed:
                        if h1['ohaeng'] in needed:
                            oh_bonus += 5
                        if h2['ohaeng'] in needed:
                            oh_bonus += 5

                    # 점수 공식:
                    # h1(0.15) + h2(0.15) + suri(0.20) + phonetics(0.15)
                    # + eumryeong(0.20) + jawon_flow(0.15)
                    # + oh_bonus + chung_penalty + hyeong_penalty + ey_bonus
                    total = (
                        h1['score'] * 0.15 +
                        h2['score'] * 0.15 +
                        suri['total_score'] * 0.20 +
                        ph_score * 0.15 +
                        eumryeong_score * 0.20 +
                        jawon_score * 0.15 +
                        oh_bonus + chung_penalty + hyeong_penalty + ey_bonus
                    )

                    name_candidates.append(_build_candidate(
                        surname, [h1, h2], suri, ph_score, ph_detail, total,
                        eumryeong_score, eumryeong_detail, eumryeong_flow,
                        jawon_score, jawon_detail, jawon_flow, chung_warnings,
                        hyeong_warnings, ey_pattern
                    ))

    # 정렬 + 다양성 선택
    name_candidates.sort(key=lambda x: x['total_score'], reverse=True)
    selected = _select_diverse(name_candidates, count)

    # 후처리
    for i, name in enumerate(selected):
        name['rank'] = i + 1
        name['eumyang'] = _get_eumyang(surname, name)
        name['meaning_summary'] = _get_meaning_summary(name)

    return selected


def _build_candidate(surname, chars, suri, ph_score, ph_detail, total,
                     eumryeong_score=0, eumryeong_detail='', eumryeong_flow='',
                     jawon_score=0, jawon_detail='', jawon_flow='',
                     chung_warnings=None, hyeong_warnings=None,
                     eumyang_strokes=None):
    hangul_name = surname + ''.join(c['hangul'] for c in chars)
    ohaeng_comp = '+'.join(c['ohaeng'] for c in chars)
    # 다음자 경고 수집
    multi_warnings = []
    for c in chars:
        w = c.get('multi_reading_warning')
        if w:
            multi_warnings.append(w)
    return {
        'hangul': hangul_name,
        'hanja': ' '.join(c['hanja'] for c in chars),
        'hanja_full': hangul_name,
        'chars': chars,
        'suri': suri,
        'phonetic_score': ph_score,
        'phonetic_detail': ph_detail,
        'total_score': total,
        'ohaeng_composition': ohaeng_comp,
        'eumryeong_score': eumryeong_score,
        'eumryeong_detail': eumryeong_detail,
        'eumryeong_flow': eumryeong_flow,
        'jawon_score': jawon_score,
        'jawon_detail': jawon_detail,
        'jawon_flow': jawon_flow,
        'chung_warnings': chung_warnings or [],
        'hyeong_warnings': hyeong_warnings or [],
        'eumyang_strokes': eumyang_strokes or [],
        'multi_reading_warnings': multi_warnings,
    }


def _select_diverse(candidates, count):
    """최대 다양성 보장 선택 - 첫음 + 끝음 중복 방지"""
    selected = []
    used_hangul_names = set()
    used_first_reading = set()
    used_second_reading = set()
    used_char_sets = []  # 글자 조합 중복 방지 (순서만 다른 경우)

    def _chars_overlap(chars):
        """이미 선택된 이름과 글자 구성이 겹치는지 확인"""
        char_set = set(c['hangul'] for c in chars)
        for prev_set in used_char_sets:
            if char_set == prev_set:
                return True
        return False

    # Pass 1: 엄격 - 첫음 AND 끝음 모두 달라야 함
    for cand in candidates:
        if len(selected) >= count:
            break
        hangul = cand['hangul']
        chars = cand['chars']
        r1 = chars[0]['hangul']
        r2 = chars[1]['hangul'] if len(chars) > 1 else ''

        if hangul in used_hangul_names:
            continue
        if r1 in used_first_reading:
            continue
        if r2 and r2 in used_second_reading:
            continue
        if _chars_overlap(chars):
            continue

        selected.append(cand)
        used_hangul_names.add(hangul)
        used_first_reading.add(r1)
        if r2:
            used_second_reading.add(r2)
        used_char_sets.append(set(c['hangul'] for c in chars))

    # Pass 2: 완화 - 끝음만 달라도 허용
    if len(selected) < count:
        for cand in candidates:
            if len(selected) >= count:
                break
            hangul = cand['hangul']
            chars = cand['chars']
            r2 = chars[1]['hangul'] if len(chars) > 1 else ''

            if hangul in used_hangul_names:
                continue
            if r2 and r2 in used_second_reading:
                continue
            if _chars_overlap(chars):
                continue

            selected.append(cand)
            used_hangul_names.add(hangul)
            if r2:
                used_second_reading.add(r2)
            used_char_sets.append(set(c['hangul'] for c in chars))

    # Pass 3: 최후 - 이름만 다르면 허용
    if len(selected) < count:
        for cand in candidates:
            if len(selected) >= count:
                break
            if cand['hangul'] not in used_hangul_names:
                selected.append(cand)
                used_hangul_names.add(cand['hangul'])

    return selected


def _get_eumyang(surname, name_info):
    full = surname + ''.join(c['hangul'] for c in name_info['chars'])
    result = []
    for ch in full:
        d = decompose_hangul(ch)
        if d:
            result.append(get_vowel_type(d[1]))
    return result


def _get_meaning_summary(name_info):
    parts = []
    for c in name_info['chars']:
        m = c.get('meaning', '')
        parts.append(f"{c['hanja']}({c['hangul']}): {m}" if m else f"{c['hanja']}({c['hangul']})")
    return ' / '.join(parts)


def lookup_hanja_detail(hanja_char):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hanja, hangul, meaning, total_strokes, ohaeng, jawon_ohaeng
            FROM hanja WHERE hanja = ?
        """, (hanja_char,))
        row = cursor.fetchone()
        if row:
            return {
                'hanja': row[0], 'hangul': row[1], 'meaning': row[2],
                'strokes': row[3], 'ohaeng': row[4], 'jawon_ohaeng': row[5],
            }
        return None
    finally:
        conn.close()
