#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
엑셀(.xls) 여러 개에서 단어 데이터를 추출하여 JSON으로 저장하는 스크립트

조건:
- 허용 구성 단위: '단어'
- 허용 품사: '명사'
- 각 단어는 다음 키 중 존재하는 것만 포함:
    ["고유어 여부", "발음", "뜻풀이", "용례", "전문 분야"]
- 단어 정규식 처리:
    - 괄호 및 괄호 안의 내용 제거
    - '-' 삭제
    - '^' → ' ' (띄어쓰기)
    - 처리 후 한 글자인 단어 삭제
- 동일 표기의 여러 단어 허용 (표기별 리스트로 저장)
- 입력: ./input_xls 폴더의 모든 .xls
- 출력: ./output/words.json
- 후처리: 각 표기의 모든 엔트리에 "이음 수" 추가
  · 정의: 해당 표기의 마지막 음절과 그 두음법칙 변환 음절로 시작하는
          다른 표기들의 개수(자기 자신 제외)
"""

import os
import re
import json
import pandas as pd
from typing import Dict, List, Any

# -------------------------------------------------------------------------
# 설정
# -------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input_xls")
OUTPUT_PATH = os.path.join(BASE_DIR, "output", "words.json")

ALLOWED_UNIT = "단어"
ALLOWED_POS = "명사"
VALID_KEYS = ["고유어 여부", "발음", "뜻풀이", "용례", "전문 분야"]

# -------------------------------------------------------------------------
# 한글 유니코드 분해/합성 유틸
# -------------------------------------------------------------------------
HANGUL_BASE = 0xAC00
CHOS = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
JUNGS = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
JONGS = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

CHO_N = 2   # ㄴ
CHO_R = 5   # ㄹ
CHO_Yieung = 11 # ㅇ

# ㄴ/ㄹ이 단어 첫머리에 올 때 'ㅇ'으로 떨어지는 모음군(ㅣ계열·y계열·ㅖ·ㅒ·ㅟ·(보수적으로)ㅢ)
IY_JUNG_IDX = {20, 2, 6, 12, 17, 7, 16, 3, 19}

def is_hangul_syllable(ch: str) -> bool:
    if not ch:
        return False
    o = ord(ch)
    return 0xAC00 <= o <= 0xD7A3

def decompose(ch: str):
    if not is_hangul_syllable(ch):
        return None
    code = ord(ch) - HANGUL_BASE
    cho = code // 588
    jung = (code % 588) // 28
    jong = code % 28
    return cho, jung, jong

def compose(cho: int, jung: int, jong: int) -> str:
    return chr(HANGUL_BASE + cho * 588 + jung * 28 + jong)

def dueum_transform(syll: str) -> str | None:
    """
    두음법칙 변환:
      - 초성 ㄴ: 모음이 IY_JUNG_IDX에 속하면 ㅇ으로 변환, 그 외 변화 없음
      - 초성 ㄹ: 모음이 IY_JUNG_IDX에 속하면 ㅇ, 아니면 ㄴ으로 변환
      - 그 외 초성은 변환 없음
    반환값: 변환된 음절(문자) 또는 None
    """
    d = decompose(syll)
    if d is None:
        return None
    cho, jung, jong = d
    if cho == CHO_N:
        if jung in IY_JUNG_IDX:
            return compose(CHO_Yieung, jung, jong)  # 여/요/유/이/야/예/윗류 등
        return None
    if cho == CHO_R:
        if jung in IY_JUNG_IDX:
            return compose(CHO_Yieung, jung, jong)  # 려/료/류/례/리/랴/률 등 → 여/요/유/예/이/야/율
        return compose(CHO_N, jung, jong)       # 라/래/로/루/르/뢰... → 나/내/노/누/느/뇌
    return None

# -------------------------------------------------------------------------
# 텍스트 정제
# -------------------------------------------------------------------------
def clean_word(word: str) -> str:
    """괄호 제거, '-' 삭제, '^' → 공백 치환"""
    if not isinstance(word, str):
        return ""
    word = re.sub(r"\([^)]*\)|\[[^\]]*\]|＜[^＞]*＞|〈[^〉]*〉", "", word)
    word = word.replace("-", "").replace("^", " ")
    return word.strip()

def normalize_pos(value: str) -> str:
    """품사 문자열에서 괄호 등 제거"""
    if not isinstance(value, str):
        return ""
    cleaned = re.sub(r"[「」\[\]\(\)<>]", "", value)
    return cleaned.strip()

def clean_field_value(key: str, value: Any) -> str:
    """특정 필드별 정제 로직 적용"""
    if not isinstance(value, str):
        return str(value).strip()
    text = value.strip()
    if key == "전문 분야":
        inner = re.findall(r"『([^』]+)』", text)
        if inner:
            text = inner[-1]
        else:
            text = re.sub(r"[「」『』\[\]\(\)<>0-9]", "", text).strip()
    return text

# -------------------------------------------------------------------------
# XLS 파싱
# -------------------------------------------------------------------------
def extract_from_xls(filepath: str) -> Dict[str, List[Dict[str, Any]]]:
    """단일 XLS 파일에서 조건에 맞는 단어 데이터 추출"""
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"[경고] {filepath} 읽기 실패: {e}")
        return {}

    result: Dict[str, List[Dict[str, Any]]] = {}
    cols = df.columns.tolist()
    if not ("구성 단위" in cols and "품사" in cols and "어휘" in cols):
        print(f"[무시] {os.path.basename(filepath)}: 필수 열 누락")
        return {}

    for _, row in df.iterrows():
        unit = str(row.get("구성 단위", "")).strip()
        pos = normalize_pos(str(row.get("품사", "")))
        if unit != ALLOWED_UNIT or pos != ALLOWED_POS:
            continue

        raw_word = str(row.get("어휘", "")).strip()
        word = clean_word(raw_word)
        if len(word) <= 1:
            continue

        entry: Dict[str, Any] = {}
        for key in VALID_KEYS:
            val = row.get(key, None)
            if isinstance(val, float) and pd.isna(val):
                continue
            if val not in (None, "", "nan", "NaN"):
                entry[key] = clean_field_value(key, str(val))

        result.setdefault(word, []).append(entry or {})

    return result

def merge_dicts(main_dict: Dict[str, List[Dict[str, Any]]],
                new_dict: Dict[str, List[Dict[str, Any]]]) -> None:
    """여러 파일 데이터를 병합"""
    for k, v in new_dict.items():
        main_dict.setdefault(k, []).extend(v)

# -------------------------------------------------------------------------
# 후처리: 이음 수 계산 (두음법칙 포함)
# -------------------------------------------------------------------------
def first_syllable(word: str) -> str:
    return word[0] if word else ""

def last_syllable(word: str) -> str:
    return word[-1] if word else ""

def add_link_count(words_dict: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    각 표기의 모든 엔트리에 '이음 수' 필드 추가.
    집계 기준:
      T = {마지막 음절, 두음 변환 음절(if any)}
      count = Σ(해당 음절로 시작하는 표기 수) - [자기 자신이 T 중 하나로 시작하면 1]
    """
    keys = list(words_dict.keys())

    # 첫 음절별 개수 맵
    start_count: Dict[str, int] = {}
    first_map: Dict[str, List[str]] = {}
    for w in keys:
        fs = first_syllable(w)
        start_count[fs] = start_count.get(fs, 0) + 1
        first_map.setdefault(fs, []).append(w)

    for w in keys:
        ls = last_syllable(w)
        candidates = {ls}
        if is_hangul_syllable(ls):
            dueum = dueum_transform(ls)
            if dueum:
                candidates.add(dueum)

        # 총합
        total = sum(start_count.get(c, 0) for c in candidates)
        # 자기 자신 제외: 자기 첫 음절이 후보에 포함되면 1 제외
        if first_syllable(w) in candidates:
            total -= 1

        for entry in words_dict[w]:
            entry["이음 수"] = int(total)

# -------------------------------------------------------------------------
# 메인 실행
# -------------------------------------------------------------------------
def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    xls_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".xls")]

    if not xls_files:
        print(f"[오류] {INPUT_DIR} 폴더에 .xls 파일이 없습니다.")
        return

    all_words: Dict[str, List[Dict[str, Any]]] = {}
    for filename in xls_files:
        path = os.path.join(INPUT_DIR, filename)
        print(f"[처리 중] {filename}")
        data = extract_from_xls(path)
        merge_dicts(all_words, data)

    # 이음 수 계산
    add_link_count(all_words)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_words, f, ensure_ascii=False, indent=2)

    print(f"[완료] 총 {len(all_words)}개의 어휘를 {OUTPUT_PATH}에 저장했습니다.")

if __name__ == "__main__":
    main()
