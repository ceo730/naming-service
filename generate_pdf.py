"""바른이름연구소 — 작명 보고서 PDF 생성 실행기"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from saju_engine import calculate_saju
from name_generator import generate_names
from report_generator import generate_full_report
from pdf_generator import create_naming_report_pdf

# ── 대상 정보 ──
surname = '김'
gender = '남'
birth_year, birth_month, birth_day = 2024, 3, 15
birth_hour = 10
birth_minute = 30

print('[1/4] 사주 계산 중...')
saju_result = calculate_saju(birth_year, birth_month, birth_day, birth_hour, birth_minute)

preferences = {
    'name_length': 2,
    'desired_image': ['지혜로운', '밝은'],
    'preferred_style': '한자 이름',
    'avoid_feeling': '',
    'dollimja': '',
    'birth_year': birth_year,
    'request_type': '신생아 작명',
}

print('[2/4] 이름 생성 중...')
names = generate_names(surname=surname, gender=gender, saju_result=saju_result, preferences=preferences, count=3)
for n in names:
    print(f'  {n["hangul"]} ({" ".join(c["hanja"] for c in n["chars"])}) - {n.get("total_score",0):.1f}점')

form_data = {
    'surname': surname,
    'gender': gender,
    'birth_date': f'{birth_year}-{birth_month:02d}-{birth_day:02d}',
    'birth_time': f'{birth_hour}:{birth_minute:02d}',
    'request_type': '신생아 작명',
    'considerations': '없음',
    'desired_image': '지혜로운, 밝은',
    'preferred_style': '한자 이름',
    'avoid_feeling': '없음',
}

print('[3/4] 보고서 생성 중 (AI 분석, 약 1~2분 소요)...')
report = generate_full_report(saju_result, names, form_data)

sections = report.get('sections', [])
total_chars = sum(len(s.get('content', '')) for s in sections)
print(f'  보고서 완성: {len(sections)}개 섹션, 총 {total_chars:,}자')

print('[4/4] PDF 생성 중...')
output_path = os.path.join(r'C:\Users\onsta\Desktop', f'작명보고서_{surname}_{birth_year}{birth_month:02d}{birth_day:02d}_v4.pdf')
create_naming_report_pdf(saju_result, names, report, form_data, output_path)

file_size = os.path.getsize(output_path)
print(f'\nPDF 저장 완료!')
print(f'  경로: {output_path}')
print(f'  크기: {file_size/1024:.1f} KB')
