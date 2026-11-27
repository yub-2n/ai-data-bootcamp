/*
 * cases_data.js — 9구역(사례 탭) 실제 값. 예시 데이터 아님.
 * 옮긴 곳: outputs/qual/사례뷰어_선정.csv (2026-11-04 16:20 뽑음, 선정 기준 docs/사례뷰어_선정기준.md, 코드 outputs/qual/사례뷰어_선정.py)
 * 옮긴 방법: CSV를 파이썬 csv 모듈로 읽어 옮김. 빈칸은 null, cited·replaced는 정수, difficulty_index는 소수. 숫자는 고치거나 계산하지 않음.
 * 키 이름 = 파일 이름, 열 이름 = 파일 첫 줄 그대로. 행 12건.
 * clause_text 처리(2026-11-04 팀 확정, 이 파일을 만들 때 적용. 화면 코드는 자르지 않음):
 *   - 인용문은 바꾸지 않고 자르기만 함. 예외: 보험사 이름을 "○○"으로 가림(제2021-23호).
 *   - 문장 끝 기준 최대 3문장, 300자 이내까지만 남기고 뒤에 " … 이하 생략"을 붙임. 원문이 3문장·300자 안이면 그대로(표시 없음).
 *   - 첫 문장 하나가 300자를 넘으면 300자에서 자르고 " … 이하 생략".
 *   - 문장 끝 = 한글 뒤의 "다."(뒤가 공백·줄바꿈·끝·닫는 따옴표/괄호, 또는 여는 괄호 "(" — 2026-11-04 추가) 또는 줄·글 끝의 "다". "가. 나. 다." 목록 기호는 문장 끝 아님.
 *   - 전문은 이 파일에 남기지 않음(원문: outputs/qual/사례뷰어_선정.csv).
 * truncated(0/1): CSV에 없는 열. 이 파일을 만들 때 붙임. 1 = 위 규칙으로 잘라 " … 이하 생략"을 붙인 사례. 화면의 "조항 일부만 표시" 표시는 이 값으로만 정한다.
 * 화면은 case_key, issue_type_R1, cited, clause_text, difficulty_index, truncated만 쓴다.
 * 원문 링크 없음. 출처 표기는 "금융감독원 분쟁조정결정례 제<case_key>호".
 */
window.DASHBOARD_CASES = {
  is_sample: false,
  source_file: "outputs/qual/사례뷰어_선정.csv",
  criteria_file: "docs/사례뷰어_선정기준.md",
  text_rule: "최대 3문장·300자, 넘으면 \" … 이하 생략\". 보험사 이름은 ○○으로 가림",
  "사례뷰어_선정": [
    {
      "case_key": "2009-32",
      "issue_type_R1": "보상범위·정의",
      "cited": 1,
      "clause_text": "○ 제4조(계약의 무효)\n보험대상자(피보험자)가 계약일로부터 제9조(제1회 보험료 및 회사의 보장개시일) 제5항에서 정한 “암보장개시일”의 전일 이전에 제14조(“암” 및 “기타피부암”의 정의 및 진단확정) 제1항에서 정한 “암”으로 진단확정 되어 있는 경우에는 계약을 무효로 하며 이미 납입한 보험료를 돌려드립니다.",
      "difficulty_index": 0.2564022239493412,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 0
    },
    {
      "case_key": "1998-36",
      "issue_type_R1": "보상범위·정의",
      "cited": 1,
      "clause_text": "이 보험에서 교통사고라 함은 가. 운행중의 교통기관(이에 적재되어 있는 것을 포함합니다)의 충돌, 접촉, 화재, 폭발, 도주 등으로 인하여 그 운행중의 교통기관에 탑승하고 있지 아니한 피보험자가 입은 불의의 사고 나. 운행중인 교통기관에 탑승하고 있는 동안 또는 승객으로서 개찰구를 갖는 교통기관의 승강장 구내(개찰구의 안쪽을 말합니다)에 있는 동안 피보험자가 입은 불의의 사고 다. 도로통행중 건조물, 공작물 등의 도괴 또는 건조물, 공작물 등으로 부터의 낙하물로 인하여 피보험자가 입은 불의의 사고를 말하며,\n 제2호에 제 1호에서 … 이하 생략",
      "difficulty_index": 0.9823076447542972,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 1
    },
    {
      "case_key": "2007-79",
      "issue_type_R1": "보상범위·정의",
      "cited": 0,
      "clause_text": "피보험자가 보험기간 중 재해로 인하여 장해등급분류표 중 제3급 내지 제6급의 장해상태가 되었을 때에는 재해장해급여금을 지급한다.",
      "difficulty_index": 0.3322540845331193,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 0
    },
    {
      "case_key": "2005-73",
      "issue_type_R1": "보상범위·정의",
      "cited": 0,
      "clause_text": "보험기간 중 책임개시일 이후에 교통재해 이외의 재해를 직접적인 원인으로 사망하였을 때에는 일반재해사망보험금을 지급한다",
      "difficulty_index": -0.2095986985352027,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 0
    },
    {
      "case_key": "2021-23",
      "issue_type_R1": "면책",
      "cited": 1,
      "clause_text": "① ○○은 보험의 목적이 다음의 자연재해(이하 “보상대상 자연재해”라 합니다)로 인하여 발생한 손해를 이 약관에 따라 보상하여 드립니다. 이 경우, 자연재해로 인한 손해로 인정될 수 있는 범위는 자연재해 발생일로부터 종료일(각 관련기관의 특보 해제일을 말합니다) 및 그 종료일로부터 14일 이내(이하 “손해보상대상기간” 이라 합니다)에 발생된 손해에 한합니다. 다만, 제5호(이상조류)의 경우 손해발생일로부터 30일 이내를 말합니다. … 이하 생략",
      "difficulty_index": 0.1555875153276366,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 1
    },
    {
      "case_key": "2021-18",
      "issue_type_R1": "면책",
      "cited": 1,
      "clause_text": "제11조【보험금을 지급하지 아니하는 보험사고】\n회사는 다음 중 어느 한 가지의 경우에 의하여 보험금 지급사유가 발생한 때에는 보험금을 드리지 아니합니다.\n1. 피보험자(보험대상자)가 고의로 자신을 해친 경우\n다만, 다음 각 목의 경우에는 그러하지 아니합니다. … 이하 생략",
      "difficulty_index": 1.410977669971848,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 1
    },
    {
      "case_key": "2010-103",
      "issue_type_R1": "면책",
      "cited": 0,
      "clause_text": "회사는 다른 약정이 없으면 피보험자가 직업, 직무 또는 동호회 활동목적으로 아래에 열거된 행위를 하는 동안에 생긴 손해에 대하여는 보상하여 드리지 아니합니다.",
      "difficulty_index": -0.3542717769379154,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 0
    },
    {
      "case_key": "2021-19",
      "issue_type_R1": "면책",
      "cited": 0,
      "clause_text": "제8조【보험금을 지급하지 않는 사유】회사는 다음 중 어느 한 가지로 보험금 지급사유가 발생한 때에는 보험금을 지급하지 않거나 보험료의 납입을 면제하여 드리지 않습니다.\n1. 피보험자가 고의로 자신을 해친 경우.\n다만, 피보험자가 심신상실 등으로 자유로운 의사결정을 할 수 없는 상태에서 자신을 해친 경우에는 보험금을 지급하거나 보험료의 납입을 면제하여 드립니다.\n특히 그 결과 사망에 이르게 된 경우에는 아래의 사망보험금을 지급합니다. … 이하 생략",
      "difficulty_index": 0.2490445604018936,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 1
    },
    {
      "case_key": "2016-8",
      "issue_type_R1": "고지·설명",
      "cited": 1,
      "clause_text": "◦ 제21조(약관교부 및 설명의무)  회사는 계약자가 청약할 때에 계약자에게 약관의 중요한 내용을 설명하여야 하며 청약 후에 지체없이 약관 및 계약자 보완용 청약서를 드립니다.",
      "difficulty_index": -0.1992242746040602,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 0
    },
    {
      "case_key": "2018-13",
      "issue_type_R1": "고지·설명",
      "cited": 1,
      "clause_text": "제2조 (계약의 체결 및 보험료)\n① 계약자는 다음에 정하는 보장계약과 연금계약을 동시에 체결하여야 합니다. … 이하 생략",
      "difficulty_index": -0.2746056819534132,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 1
    },
    {
      "case_key": "2010-23",
      "issue_type_R1": "고지·설명",
      "cited": 0,
      "clause_text": "제6조(보상하는 손해)회사는 피보험자(보험대상자)가 보험증권(보험가입증서)상의 보장지역 내에서 보험기간 중에 발생한 특별약관에 기재된 보험사고로 인하여 타인의 신체에 장해(이하 신체장해라 합니다)를 입히거나 타인의 재물을 망그러뜨려(이하 재물손해라 합니다) 법률적인 배상책임을 부담함으로써 입은 아래의 손해를 보상하여 드립니다.\n1.피보험자(보험대상자)가 피해자에게 지급한 법률상 손해배상금",
      "difficulty_index": -0.3617363836884243,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 0
    },
    {
      "case_key": "2005-34",
      "issue_type_R1": "고지·설명",
      "cited": 0,
      "clause_text": "보험회사는 피보험자가 여행 도중에 생긴 우연한 사고로 타인의 신체의 장해 또는 재물의 손해에 대한 법률상의 배상책임을 부담함으로써 입은 손해를 보상한다",
      "difficulty_index": -0.4620307126001147,
      "replaced": 0,
      "replace_reason": null,
      "replaced_from": null,
      "truncated": 0
    }
  ]
};
