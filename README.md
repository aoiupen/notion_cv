# 이력서 자동화 툴 (PySide6 기반)

이 프로젝트는 노션(Notion)에서 작성한 이력서를 자동으로 추출, 번역(Claude API), 펼치기, PDF 변환까지 지원하는 데스크탑 애플리케이션입니다. PySide6 기반의 GUI를 제공합니다.

---

## 주요 기능

1. **노션 이력서 추출**: 노션 API를 통해 이력서 데이터를 불러옵니다.
2. **번역**: Claude API를 이용해 한글 이력서의 일부 또는 전체를 영어로 번역합니다.
3. **이력서 펼치기**: 리스트/갤러리 형태로 이력서 내용을 펼쳐서 확인할 수 있습니다.
4. **PDF 변환**: 펼쳐진 이력서를 PDF로 저장할 수 있습니다.
5. **새 페이지 시작 규칙 선택**: 드롭박스(콤보박스)로 페이지 구분 규칙을 선택할 수 있습니다.
6. **환경변수 관리**: .env 파일을 통해 API 키 등 민감 정보를 안전하게 관리합니다.

---

## 폴더 및 파일 구조

```
notion_cv/
├── main.py                    # 메인 진입점
├── config.py                  # 환경설정
├── core_engine.py            # Notion 엔진
├── html2pdf_engine.py        # PDF 변환 엔진  
├── translate_engine.py       # 번역 엔진
├── portfolio_style.css       # 스타일시트
├── requirements.txt          # 의존성
├── ui/
│   ├── main_window.py        # 메인 윈도우 (View)
│   └── widgets.py           # 커스텀 위젯들
├── viewmodels/
│   └── main_viewmodel.py    # 메인 뷰모델 (ViewModel)
├── utils/
│   ├── helpers.py           # 헬퍼 함수들
│   └── notion_parser.py     # Notion 파싱
├── .gitignore
├── .python-version
└── README.md                # 환경변수 파일 (직접 생성 필요)
```

---

## 설치 및 실행 방법

1. **필수 패키지 설치**

```bash
pip install -r requirements.txt
```

2. **.env 파일 생성**

프로젝트 루트에 `.env` 파일을 생성하고 아래와 같이 작성하세요:

```
NOTION_API_KEY=여기에_노션_API_키_입력
CLAUDE_API_KEY=여기에_클로드_API_키_입력
```

3. **실행**

```bash
python main.py
```

---

## 주요 사용법

- 프로그램 실행 후, "새 페이지 시작 규칙"을 드롭박스에서 선택합니다.
- "이력서 자동화 시작" 버튼을 누르면, 선택한 규칙에 따라 이력서 추출, 번역, 펼치기, PDF 변환이 순차적으로 진행됩니다.
- 각 기능별 세부 구현은 `mainsub/` 폴더의 파일에서 관리합니다.

---

## 참고 및 주의사항

- 노션 API, Claude API 키는 외부에 노출되지 않도록 `.env` 파일로만 관리하세요.
- 노션 이력서 페이지 ID 등은 코드 내에서 직접 지정하거나, 추후 UI에서 입력받도록 확장할 수 있습니다.
- PDF 변환 레이아웃, 번역 품질 등은 추가 개발로 개선할 수 있습니다.

---

## 문의

- 개선 요청, 버그 제보 등은 이 저장소 이슈로 남겨주세요.
