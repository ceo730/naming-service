"""
바른이름연구소 작명 서비스 - Flask 웹 애플리케이션
"""

from flask import Flask, render_template, request, jsonify, Response
import json
import traceback

from saju_engine import calculate_saju, format_saju_summary, calculate_sipsin, calculate_daeun
from name_generator import generate_names, get_surname_strokes
from report_generator import generate_full_report, generate_report_streaming

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """이름 생성 + 보고서 생성 API"""
    try:
        data = request.get_json()

        # 필수 데이터 파싱
        surname = data.get('surname', '').strip()
        gender = data.get('gender', '남')
        birth_date = data.get('birth_date', '')
        birth_time = data.get('birth_time', '')
        request_type = data.get('request_type', '신생아 작명')

        if not surname or not birth_date:
            return jsonify({'error': '성씨와 생년월일은 필수입니다.'}), 400

        # 생년월일 파싱 및 검증
        parts = birth_date.split('-')
        if len(parts) != 3:
            return jsonify({'error': '생년월일 형식이 올바르지 않습니다. (YYYY-MM-DD)'}), 400
        birth_year = int(parts[0])
        birth_month = int(parts[1])
        birth_day = int(parts[2])
        if not (1900 <= birth_year <= 2100 and 1 <= birth_month <= 12 and 1 <= birth_day <= 31):
            return jsonify({'error': '생년월일 값이 유효하지 않습니다.'}), 400

        # 출생시간 파싱
        birth_hour = None
        birth_minute = 0
        if birth_time and birth_time != '모름':
            time_parts = birth_time.split(':')
            birth_hour = int(time_parts[0])
            if len(time_parts) > 1:
                birth_minute = int(time_parts[1])

        # 1. 사주 계산
        saju_result = calculate_saju(birth_year, birth_month, birth_day, birth_hour, birth_minute)

        # 2. 사주 요약
        saju_summary = format_saju_summary(saju_result)

        # 십신/대운 계산
        sipsin_result = calculate_sipsin(saju_result)
        daeun_result = calculate_daeun(saju_result, gender, birth_year, birth_month, birth_day)

        # 3. 선호도 설정
        preferences = {
            'name_length': int(data.get('name_length', 2)),
            'desired_image': data.get('desired_image', []),
            'preferred_style': ', '.join(data.get('preferred_style', [])) if isinstance(data.get('preferred_style'), list) else data.get('preferred_style', '한자 이름'),
            'avoid_feeling': data.get('avoid_feeling', ''),
            'dollimja': data.get('dollimja', ''),
            'birth_year': birth_year,
            'request_type': request_type,
        }

        # 4. 이름 생성
        names = generate_names(
            surname=surname,
            gender=gender,
            saju_result=saju_result,
            preferences=preferences,
            count=3
        )

        if not names:
            return jsonify({'error': '조건에 맞는 이름을 생성할 수 없습니다. 조건을 완화해 주세요.'}), 400

        # 5. 폼 데이터 정리 (보고서용)
        form_data = {
            'surname': surname,
            'gender': gender,
            'birth_date': birth_date,
            'birth_time': birth_time or '미상',
            'request_type': request_type,
            'considerations': ', '.join(data.get('considerations', [])) or '없음',
            'desired_image': ', '.join(data.get('desired_image', [])) or '없음',
            'preferred_style': ', '.join(data.get('preferred_style', [])) if isinstance(data.get('preferred_style'), list) else data.get('preferred_style', '없음'),
            'avoid_feeling': data.get('avoid_feeling', '없음'),
            'birth_place': data.get('birth_place', ''),
            'current_name': data.get('current_name', ''),
            'rename_reason': data.get('rename_reason', ''),
        }

        # 6. 이름 결과 반환 (보고서 전에 빠르게)
        names_response = []
        for n in names:
            names_response.append({
                'hangul': n['hangul'],
                'hanja': ' '.join([c['hanja'] for c in n['chars']]),
                'chars': [{
                    'hanja': c['hanja'],
                    'hangul': c['hangul'],
                    'meaning': c.get('meaning', ''),
                    'strokes': c.get('strokes', 0),
                    'ohaeng': c.get('ohaeng', ''),
                    'jawon_ohaeng': c.get('jawon_ohaeng', c.get('ohaeng', '')),
                } for c in n['chars']],
                'ohaeng_composition': n['ohaeng_composition'],
                'eumyang': n.get('eumyang', []),
                'suri': {
                    'won': {'value': n['suri']['won']['value'], 'ohaeng': n['suri']['won']['ohaeng'], 'rating': n['suri']['won']['rating'][0]},
                    'hyeong': {'value': n['suri']['hyeong']['value'], 'ohaeng': n['suri']['hyeong']['ohaeng'], 'rating': n['suri']['hyeong']['rating'][0]},
                    'yi': {'value': n['suri']['yi']['value'], 'ohaeng': n['suri']['yi']['ohaeng'], 'rating': n['suri']['yi']['rating'][0]},
                    'jeong': {'value': n['suri']['jeong']['value'], 'ohaeng': n['suri']['jeong']['ohaeng'], 'rating': n['suri']['jeong']['rating'][0]},
                    'grade': n['suri']['grade'],
                },
                'phonetic_score': n.get('phonetic_score', 0),
                'total_score': round(n.get('total_score', 0), 1),
                'meaning_summary': n.get('meaning_summary', ''),
                'eumryeong_score': n.get('eumryeong_score', 0),
                'eumryeong_detail': n.get('eumryeong_detail', ''),
                'eumryeong_flow': n.get('eumryeong_flow', ''),
                'jawon_score': n.get('jawon_score', 0),
                'jawon_detail': n.get('jawon_detail', ''),
                'jawon_flow': n.get('jawon_flow', ''),
                'chung_warnings': n.get('chung_warnings', []),
                'hyeong_warnings': n.get('hyeong_warnings', []),
                'eumyang_strokes': n.get('eumyang_strokes', []),
                'multi_reading_warnings': n.get('multi_reading_warnings', []),
            })

        return jsonify({
            'success': True,
            'saju_summary': saju_summary,
            'saju_result': serialize_saju(saju_result, sipsin_result, daeun_result),
            'names': names_response,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'오류가 발생했습니다: {str(e)}'}), 500


@app.route('/api/report', methods=['POST'])
def api_report():
    """보고서 생성 API (SSE 스트리밍)"""
    try:
        data = request.get_json()

        surname = data.get('surname', '').strip()
        gender = data.get('gender', '남')
        birth_date = data.get('birth_date', '')
        birth_time = data.get('birth_time', '')

        parts = birth_date.split('-')
        birth_year = int(parts[0])
        birth_month = int(parts[1])
        birth_day = int(parts[2])

        birth_hour = None
        birth_minute = 0
        if birth_time and birth_time != '모름':
            time_parts = birth_time.split(':')
            birth_hour = int(time_parts[0])
            if len(time_parts) > 1:
                birth_minute = int(time_parts[1])

        saju_result = calculate_saju(birth_year, birth_month, birth_day, birth_hour, birth_minute)

        # 프론트엔드에서 전달받은 이름 데이터 사용 (이미 생성된 이름)
        names_data = data.get('names', [])
        if names_data:
            names = reconstruct_names(names_data, surname, saju_result)
        else:
            preferences = {
                'name_length': int(data.get('name_length', 2)),
            }
            names = generate_names(
                surname=surname,
                gender=gender,
                saju_result=saju_result,
                preferences=preferences,
                count=3
            )

        form_data = {
            'surname': surname,
            'gender': gender,
            'birth_date': birth_date,
            'birth_time': birth_time or '미상',
            'request_type': data.get('request_type', '신생아 작명'),
            'considerations': ', '.join(data.get('considerations', [])) or '없음',
            'desired_image': ', '.join(data.get('desired_image', [])) or '없음',
            'preferred_style': ', '.join(data.get('preferred_style', [])) if isinstance(data.get('preferred_style'), list) else data.get('preferred_style', '없음'),
            'avoid_feeling': data.get('avoid_feeling', '없음'),
        }

        # 전체 보고서 생성 (동기)
        report = generate_full_report(saju_result, names, form_data)

        return jsonify({
            'success': True,
            'report': report,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'보고서 생성 중 오류: {str(e)}'}), 500


@app.route('/api/report-stream', methods=['POST'])
def api_report_stream():
    """보고서 생성 SSE 스트리밍 API"""
    data = request.get_json()

    def generate():
        try:
            surname = data.get('surname', '').strip()
            gender = data.get('gender', '남')
            birth_date = data.get('birth_date', '')
            birth_time = data.get('birth_time', '')

            parts = birth_date.split('-')
            birth_year = int(parts[0])
            birth_month = int(parts[1])
            birth_day = int(parts[2])

            birth_hour = None
            birth_minute = 0
            if birth_time and birth_time != '모름':
                time_parts = birth_time.split(':')
                birth_hour = int(time_parts[0])
                if len(time_parts) > 1:
                    birth_minute = int(time_parts[1])

            saju_result = calculate_saju(birth_year, birth_month, birth_day, birth_hour, birth_minute)

            # 이름은 이미 생성된 것 사용 (data에서 전달)
            names_data = data.get('names', [])
            if names_data:
                # 프론트엔드에서 전달받은 이름 정보로 재구성
                names = reconstruct_names(names_data, surname, saju_result)
            else:
                names = generate_names(
                    surname=surname,
                    gender=gender,
                    saju_result=saju_result,
                    count=3
                )

            form_data = {
                'surname': surname,
                'gender': gender,
                'birth_date': birth_date,
                'birth_time': birth_time or '미상',
                'request_type': data.get('request_type', '신생아 작명'),
                'considerations': ', '.join(data.get('considerations', [])) or '없음',
                'desired_image': ', '.join(data.get('desired_image', [])) or '없음',
                'preferred_style': ', '.join(data.get('preferred_style', [])) if isinstance(data.get('preferred_style'), list) else data.get('preferred_style', '없음'),
                'avoid_feeling': data.get('avoid_feeling', '없음'),
            }

            for chunk in generate_report_streaming(saju_result, names, form_data):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype='text/event-stream')


def reconstruct_names(names_data, surname, saju_result):
    """프론트엔드에서 전달받은 이름 데이터를 백엔드 형식으로 재구성"""
    from name_generator import (evaluate_phonetics, get_surname_strokes,
                                evaluate_eumryeong_ohaeng, evaluate_jawon_ohaeng_flow,
                                evaluate_eumyang_strokes)
    from saju_engine import calculate_suri_ohaeng, check_chung_conflict, check_hyeong_conflict

    names = []
    surname_strokes = get_surname_strokes(surname)
    day_branch = saju_result.get('day_pillar', {}).get('branch', '')

    for nd in names_data:
        chars = nd.get('chars', [])
        char_infos = []
        for c in chars:
            char_infos.append({
                'hanja': c.get('hanja', ''),
                'hangul': c.get('hangul', ''),
                'meaning': c.get('meaning', ''),
                'strokes': c.get('strokes', 0),
                'ohaeng': c.get('ohaeng', ''),
                'jawon_ohaeng': c.get('jawon_ohaeng', c.get('ohaeng', '')),
            })

        # 수리 재계산
        if len(char_infos) >= 2:
            suri = calculate_suri_ohaeng(surname_strokes, char_infos[0]['strokes'], char_infos[1]['strokes'])
        elif len(char_infos) == 1:
            suri = calculate_suri_ohaeng(surname_strokes, char_infos[0]['strokes'])
        else:
            suri = {'won': {}, 'hyeong': {}, 'yi': {}, 'jeong': {}, 'total_score': 0, 'grade': ''}

        hangul_chars = [c['hangul'] for c in char_infos]
        phonetic_score, phonetic_detail = evaluate_phonetics(surname, hangul_chars)

        # 음령 오행 재계산
        eumryeong_score, eumryeong_detail, eumryeong_flow = evaluate_eumryeong_ohaeng(surname, hangul_chars)

        # 자원 오행 재계산
        jawon_score, jawon_detail, jawon_flow = evaluate_jawon_ohaeng_flow(surname, char_infos)

        # 충 검사
        hanja_list = [c['hanja'] for c in char_infos]
        chung_warnings = check_chung_conflict(day_branch, hanja_list)

        # 형 검사
        hyeong_warnings = check_hyeong_conflict(day_branch, hanja_list)

        # 음양 획수
        _, eumyang_strokes = evaluate_eumyang_strokes(surname_strokes, char_infos)

        names.append({
            'hangul': nd.get('hangul', ''),
            'hanja': nd.get('hanja', ''),
            'chars': char_infos,
            'suri': suri,
            'phonetic_score': phonetic_score,
            'phonetic_detail': phonetic_detail,
            'total_score': nd.get('total_score', 0),
            'ohaeng_composition': nd.get('ohaeng_composition', ''),
            'eumyang': nd.get('eumyang', []),
            'meaning_summary': nd.get('meaning_summary', ''),
            'eumryeong_score': eumryeong_score,
            'eumryeong_detail': eumryeong_detail,
            'eumryeong_flow': eumryeong_flow,
            'jawon_score': jawon_score,
            'jawon_detail': jawon_detail,
            'jawon_flow': jawon_flow,
            'chung_warnings': chung_warnings,
            'hyeong_warnings': hyeong_warnings,
            'eumyang_strokes': eumyang_strokes,
        })

    return names


def serialize_saju(saju_result, sipsin_result=None, daeun_result=None):
    """사주 결과를 JSON 직렬화 가능한 형태로 변환"""
    result = {}
    for key in ['year_pillar', 'month_pillar', 'day_pillar', 'hour_pillar']:
        if saju_result.get(key):
            result[key] = saju_result[key]
        else:
            result[key] = None

    oa = saju_result['ohaeng_analysis']
    result['ohaeng_analysis'] = {
        'count': oa['count'],
        'janggan_count': oa['janggan_count'],
        'eumyang_count': oa['eumyang_count'],
        'ilgan': oa['ilgan'],
        'ilgan_kr': oa['ilgan_kr'],
        'ilgan_ohaeng': oa['ilgan_ohaeng'],
        'ilgan_ohaeng_kr': oa['ilgan_ohaeng_kr'],
        'yongsin': oa['yongsin'],
    }
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
    return result


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
