"""
바른이름연구소 — 작명 보고서 PDF 생성기 v2
디자인 에셋 기반 (이미지 템플릿 오버레이)
"""

import os
import re
from fpdf import FPDF

# ─── 디자인 에셋 경로 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

# ─── A4 크기 ───
PW = 210  # page width mm
PH = 297  # page height mm

# ─── 내지 텍스트 영역 ───
BODY_LEFT = 30
BODY_RIGHT = 30
BODY_TOP = 22
BODY_BOTTOM = 35
BODY_W = PW - BODY_LEFT - BODY_RIGHT  # 150mm

# ─── 색상 ───
C_BODY = (50, 50, 50)
C_TITLE = (70, 50, 35)
C_SUBTITLE = (110, 90, 70)
C_HEADER = (140, 130, 120)
C_OHAENG = {
    '木': (76, 153, 76),
    '火': (204, 85, 85),
    '土': (170, 145, 80),
    '金': (130, 130, 160),
    '水': (70, 130, 180),
}


def _asset(name):
    return os.path.join(ASSETS_DIR, name)


class NamingReportPDF(FPDF):
    """바른이름연구소 작명 보고서 — 디자인 에셋 기반"""

    def __init__(self):
        super().__init__()
        self._page_type = 'none'  # 'body', 'cover', 'chapter', 'static'
        self._prose_mode = False  # write_prose 중 자동 페이지 넘김용
        self.set_auto_page_break(auto=False)
        self._setup_fonts()

    def _setup_fonts(self):
        import platform
        if platform.system() == 'Windows':
            font_dir = r'C:\Windows\Fonts'
            self.add_font('Gothic', '', os.path.join(font_dir, 'malgun.ttf'))
            self.add_font('Gothic', 'B', os.path.join(font_dir, 'malgunbd.ttf'))
        else:
            fonts_dir = os.path.join(BASE_DIR, 'fonts')
            self.add_font('Gothic', '', os.path.join(fonts_dir, 'NanumGothic-Regular.ttf'))
            self.add_font('Gothic', 'B', os.path.join(fonts_dir, 'NanumGothic-Bold.ttf'))

    def header(self):
        if self._prose_mode:
            self._page_type = 'body'
            self.image(_asset('내지.png'), 0, 0, PW, PH)
            self.set_y(BODY_TOP + 10)

    def footer(self):
        if self._page_type == 'body':
            self.set_y(-25)
            self.set_font('Gothic', '', 8)
            self.set_text_color(*C_HEADER)
            self.cell(0, 5, str(self.page_no()), align='C')

    # ─── 배경 이미지로 페이지 추가 ───
    def _add_bg_page(self, img_name, page_type='static'):
        self._page_type = page_type
        self.add_page()
        self.image(_asset(img_name), 0, 0, PW, PH)

    # ─── 내지 배경으로 본문 페이지 시작 ───
    def _add_body_page(self):
        self._page_type = 'body'
        self.add_page()
        self.image(_asset('내지.png'), 0, 0, PW, PH)
        self.set_y(BODY_TOP)

    # ═══════════════════════════════════════
    # 1. 표지
    # ═══════════════════════════════════════
    def add_cover(self):
        self._page_type = 'cover'
        self.add_page()
        self.image(_asset('앞표지.png'), 0, 0, PW, PH)

    # ═══════════════════════════════════════
    # 2. 목차 (동적 이름 오버레이)
    # ═══════════════════════════════════════
    def add_toc(self, names):
        self._add_bg_page('목차.png')

    # ═══════════════════════════════════════
    # 3. 고정 페이지들 (0장: 주의사항)
    # ═══════════════════════════════════════
    def add_static_pages(self):
        for pg in ['1.png', '2.png', '3.png', '4.png', '5.png', '6.png', '7.png', '8.png', '9.png']:
            self._add_bg_page(pg)

    # ═══════════════════════════════════════
    # 4. 챕터 오프닝
    # ═══════════════════════════════════════
    def add_chapter_opening(self, chapter_index):
        """chapter_index: 1~5"""
        img = f'챕터오프닝_{chapter_index:02d}.png'
        self._add_bg_page(img, 'chapter')

    # ═══════════════════════════════════════
    # 5. 사주 정보 페이지 (내지 배경 위에)
    # ═══════════════════════════════════════
    def add_saju_info(self, saju_result, form_data):
        self._add_body_page()

        y = BODY_TOP + 8

        # 제목
        self.set_y(y)
        self.set_font('Gothic', 'B', 16)
        self.set_text_color(*C_TITLE)
        self.cell(0, 10, '사주팔자 구성', align='C')
        y += 18

        # 구분선
        self.set_draw_color(180, 160, 130)
        self.set_line_width(0.4)
        self.line(70, y, 140, y)
        y += 10

        # 기본 정보
        info = [
            ('성씨', form_data.get('surname', '')),
            ('성별', form_data.get('gender', '')),
            ('생년월일', form_data.get('birth_date', '') + ' (양력)'),
            ('출생시간', form_data.get('birth_time', '미상')),
        ]
        for label, value in info:
            self.set_y(y)
            self.set_x(55)
            self.set_font('Gothic', '', 10)
            self.set_text_color(*C_SUBTITLE)
            self.cell(30, 7, label, align='R')
            self.cell(8, 7, '')
            self.set_font('Gothic', 'B', 10)
            self.set_text_color(*C_BODY)
            self.cell(60, 7, value)
            y += 8

        y += 10

        # 사주 테이블
        pillar_labels = ['시주', '일주', '월주', '년주']
        pillar_keys = ['hour_pillar', 'day_pillar', 'month_pillar', 'year_pillar']
        table_x = 40
        col_w = 32.5
        row_h = 16

        # 헤더
        self.set_fill_color(100, 75, 55)
        self.set_text_color(255, 255, 255)
        self.set_font('Gothic', 'B', 10)
        for i, label in enumerate(pillar_labels):
            self.set_xy(table_x + i * col_w, y)
            self.cell(col_w, 10, label, border=1, align='C', fill=True)
        y += 10

        # 천간
        self.set_fill_color(248, 244, 238)
        for i, key in enumerate(pillar_keys):
            p = saju_result.get(key)
            self.set_xy(table_x + i * col_w, y)
            if p:
                txt = f"{p['stem']}({p['stem_kr']})"
                self.set_text_color(*C_OHAENG.get(p['stem_ohaeng'], C_BODY))
            else:
                txt = '미상'
                self.set_text_color(*C_BODY)
            self.set_font('Gothic', 'B', 12)
            self.cell(col_w, row_h, txt, border=1, align='C', fill=True)
        y += row_h

        # 지지
        for i, key in enumerate(pillar_keys):
            p = saju_result.get(key)
            self.set_xy(table_x + i * col_w, y)
            if p:
                txt = f"{p['branch']}({p['branch_kr']})"
                self.set_text_color(*C_OHAENG.get(p['branch_ohaeng'], C_BODY))
            else:
                txt = '미상'
                self.set_text_color(*C_BODY)
            self.set_font('Gothic', 'B', 12)
            self.cell(col_w, row_h, txt, border=1, align='C', fill=True)
        y += row_h + 12

        # 오행 분포 바 차트
        oa = saju_result['ohaeng_analysis']
        self.set_font('Gothic', 'B', 12)
        self.set_text_color(*C_TITLE)
        self.set_y(y)
        self.cell(0, 8, '오행 분포', align='C')
        y += 12

        ohaeng_items = [('木(목)', '木'), ('火(화)', '火'), ('土(토)', '土'), ('金(금)', '金'), ('水(수)', '水')]
        max_cnt = max(oa['count'].values()) if max(oa['count'].values()) > 0 else 1
        bar_max = 65

        for name, key in ohaeng_items:
            cnt = oa['count'][key]
            bar_w = max((cnt / max_cnt) * bar_max, 2) if cnt > 0 else 2
            self.set_xy(45, y)
            self.set_font('Gothic', '', 10)
            self.set_text_color(*C_BODY)
            self.cell(28, 7, name, align='R')
            bar_y = y + 1
            self.set_fill_color(*C_OHAENG[key])
            self.rect(78, bar_y, bar_w, 5, 'F')
            self.set_xy(78 + bar_w + 3, y)
            self.set_font('Gothic', 'B', 10)
            self.set_text_color(*C_OHAENG[key])
            self.cell(10, 7, str(cnt))
            y += 8

        y += 8

        # 용신 정보
        yongsin = oa['yongsin']
        self.set_font('Gothic', '', 10)
        self.set_text_color(*C_BODY)

        self.set_y(y)
        il_text = f"일간: {oa['ilgan']}({oa['ilgan_kr']}) {oa['ilgan_ohaeng']}({oa['ilgan_ohaeng_kr']})  |  강약: {yongsin['strength_desc']}"
        self.cell(0, 7, il_text, align='C')
        y += 8

        self.set_y(y)
        yong_text = f"용신: {yongsin['yongsin']}({yongsin['yongsin_kr']})  |  희신: {yongsin.get('huisin', '')}({yongsin.get('huisin_kr', '')})"
        self.cell(0, 7, yong_text, align='C')
        y += 8

        self.set_y(y)
        missing = ', '.join([f"{m}({oa['yongsin']['missing_ohaeng_kr'][i]})"
                             for i, m in enumerate(yongsin['missing_ohaeng'])])
        self.cell(0, 7, f"부족 오행: {missing}", align='C')

    # ═══════════════════════════════════════
    # 6. 이름 카드 (내지 배경 위에)
    # ═══════════════════════════════════════
    def add_name_card(self, name_info, name_data):
        self._add_body_page()

        y = BODY_TOP + 10

        hangul = name_info.get('hangul', '')
        hanja = name_info.get('hanja', '')

        # 이름 한글
        self.set_y(y)
        self.set_font('Gothic', 'B', 28)
        self.set_text_color(*C_TITLE)
        self.cell(0, 16, hangul, align='C')
        y += 20

        # 한자
        self.set_y(y)
        self.set_font('Gothic', '', 13)
        self.set_text_color(*C_SUBTITLE)
        self.cell(0, 8, hanja, align='C')
        y += 12

        # 구분선
        self.set_draw_color(180, 160, 130)
        self.set_line_width(0.4)
        self.line(60, y, 150, y)
        y += 10

        # 오행 정보
        info_items = []
        if name_info.get('ohaeng'):
            info_items.append(('오행 구성', name_info['ohaeng']))
        if name_info.get('eumryeong_flow'):
            info_items.append(('음령 오행', name_info['eumryeong_flow']))
        if name_info.get('jawon_flow'):
            info_items.append(('자원 오행', name_info['jawon_flow']))
        if name_info.get('eumyang'):
            info_items.append(('음양', name_info['eumyang']))

        for label, value in info_items:
            self.set_y(y)
            self.set_x(48)
            self.set_font('Gothic', '', 10)
            self.set_text_color(*C_SUBTITLE)
            self.cell(30, 7, label, align='R')
            self.cell(8, 7, '')
            self.set_font('Gothic', 'B', 10)
            self.set_text_color(*C_BODY)
            self.cell(70, 7, str(value))
            y += 8

        y += 6

        # 한자 상세
        self.set_draw_color(210, 200, 185)
        self.set_line_width(0.2)
        self.line(BODY_LEFT, y, PW - BODY_RIGHT, y)
        y += 8

        chars = []
        for n in name_data:
            if n['hangul'] == hangul:
                chars = n['chars']
                break

        for c in chars:
            self.set_xy(BODY_LEFT + 12, y)
            self.set_font('Gothic', 'B', 18)
            self.set_text_color(*C_TITLE)
            self.cell(18, 12, c.get('hanja', ''))
            self.set_font('Gothic', '', 10)
            self.set_text_color(*C_BODY)
            detail = f"{c.get('hangul', '')}  |  {c.get('meaning', '')}  |  {c.get('strokes', 0)}획  |  {c.get('ohaeng', '')}"
            self.cell(0, 12, detail)
            y += 14

        # 수리오행
        suri = None
        for n in name_data:
            if n['hangul'] == hangul:
                suri = n.get('suri')
                break

        if suri:
            y += 6
            self.set_draw_color(210, 200, 185)
            self.line(BODY_LEFT, y, PW - BODY_RIGHT, y)
            y += 8

            self.set_y(y)
            self.set_font('Gothic', 'B', 11)
            self.set_text_color(*C_TITLE)
            self.cell(0, 7, '수리오행', align='C')
            y += 10

            self.set_font('Gothic', '', 9.5)
            self.set_text_color(*C_BODY)

            suri_items = [
                ('원격', suri['won']),
                ('형격', suri['hyeong']),
                ('이격', suri['yi']),
                ('정격', suri['jeong']),
            ]
            for label, s in suri_items:
                self.set_y(y)
                txt = f"{label}: {s['value']} → {s['ohaeng']} ({s['rating'][0]})"
                self.cell(0, 6, txt, align='C')
                y += 7

            self.set_y(y)
            self.set_font('Gothic', 'B', 10)
            self.cell(0, 7, f"수리종합: {suri['grade']}", align='C')

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
            self.set_fill_color(*(c + (255 - c) * 7 // 10 for c in color))
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

    # ═══════════════════════════════════════
    # 7. 산문 본문 출력 (내지 배경)
    # ═══════════════════════════════════════
    def write_prose(self, text):
        if not text:
            return

        FONT_SIZE = 14
        LINE_H = 10.0
        PARA_GAP = 14.0
        SUBTITLE_GAP = 16.0
        SUBTITLE_AFTER = 6.0
        MAX_PARA_PER_PAGE = 2

        # 불필요한 마크다운 제거 (볼드 **...** 는 보존)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\-\*\•]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+[\.\)]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'---+', '', text)

        # 문단 분리
        raw_paragraphs = re.split(r'\n\s*\n', text)

        # 각 문단을 (subtitle, body) 튜플로 파싱
        elements = []
        for para in raw_paragraphs:
            para = para.strip()
            if not para or len(para) < 3:
                continue

            m = re.match(r'^\*\*(.+?)\*\*\s*(.*)', para, re.DOTALL)
            if m:
                subtitle = m.group(1).strip()
                body = m.group(2).strip()
                if body:
                    body = re.sub(r'\n', ' ', body)
                    body = re.sub(r'\s+', ' ', body).strip()
                    body = re.sub(r'\*\*(.*?)\*\*', r'\1', body)
                    body = re.sub(r'\*(.*?)\*', r'\1', body)
                    elements.append(('subtitle_para', subtitle, body))
                else:
                    elements.append(('subtitle_only', subtitle, ''))
            else:
                body = re.sub(r'\n', ' ', para)
                body = re.sub(r'\s+', ' ', body).strip()
                body = re.sub(r'\*\*(.*?)\*\*', r'\1', body)
                body = re.sub(r'\*(.*?)\*', r'\1', body)
                if len(body) < 5:
                    continue
                elements.append(('body', '', body))

        # 소제목+본문을 하나의 블록으로 병합
        blocks = []
        i = 0
        while i < len(elements):
            kind, sub, body = elements[i]
            if kind == 'subtitle_only' and i + 1 < len(elements):
                next_kind, _, next_body = elements[i + 1]
                if next_kind == 'body' and next_body:
                    blocks.append((sub, next_body))
                    i += 2
                    continue
                else:
                    blocks.append((sub, ''))
                    i += 1
            elif kind == 'subtitle_para':
                blocks.append((sub, body))
                i += 1
            else:
                blocks.append(('', body))
                i += 1

        # ── 렌더링 (자동 페이지 넘김 활성화) ──
        self._prose_mode = True
        self.set_auto_page_break(auto=True, margin=BODY_BOTTOM + 10)
        old_l_margin = self.l_margin
        self.l_margin = BODY_LEFT

        para_on_page = 0
        first_block = True

        for subtitle, body in blocks:
            # 새 페이지 시작 조건: 첫 블록 또는 2문단 초과
            if first_block or para_on_page >= MAX_PARA_PER_PAGE:
                self.add_page()  # header()가 내지 배경+Y 세팅
                para_on_page = 0
                first_block = False

            page_before = self.page

            # 소제목 렌더링 (볼드)
            if subtitle:
                if para_on_page > 0:
                    self.ln(SUBTITLE_GAP)
                self.set_font('Gothic', 'B', FONT_SIZE)
                self.set_text_color(*C_TITLE)
                self.set_x(BODY_LEFT)
                self.multi_cell(w=BODY_W, h=LINE_H, text=subtitle, align='L')
                self.ln(SUBTITLE_AFTER)

            # 본문 렌더링
            if body:
                self.set_font('Gothic', '', FONT_SIZE)
                self.set_text_color(*C_BODY)
                self.set_x(BODY_LEFT)
                self.multi_cell(w=BODY_W, h=LINE_H, text='   ' + body, align='L')
                self.ln(PARA_GAP)

            # 문단 카운트 — 자동 페이지 넘김이 발생했으면 리셋
            if self.page != page_before:
                para_on_page = 1
            else:
                para_on_page += 1

        # 복원
        self._prose_mode = False
        self.set_auto_page_break(auto=False)
        self.l_margin = old_l_margin

    # ═══════════════════════════════════════
    # 8. 뒷표지
    # ═══════════════════════════════════════
    def add_back_cover(self):
        self._page_type = 'cover'
        self.add_page()
        self.image(_asset('뒷표지.png'), 0, 0, PW, PH)


def create_naming_report_pdf(saju_result, names, report, form_data, output_path):
    """
    완성된 보고서 데이터를 받아 디자인 에셋 기반 PDF 생성 — 8섹션 구조
    """
    pdf = NamingReportPDF()

    # ── 1. 앞표지 ──
    pdf.add_cover()

    # ── 2. 목차 ──
    pdf.add_toc(names)

    # ── 3. 0장 주의사항 (고정 9페이지) ──
    pdf.add_static_pages()

    # ── 대운 데이터 추출 ──
    daeun_result = report.get('daeun_result')

    # ── 4. 보고서 본문 (8섹션) ──
    sections = report.get('sections', [])
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
