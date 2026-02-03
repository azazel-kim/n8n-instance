# HWP 문서 자동화 서비스

n8n 워크플로우와 연동하여 한글(HWP) 문서를 자동으로 생성하는 서비스입니다.

## 아키텍처

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   n8n 워크플로우  │────▶│  HWP Service   │────▶│   한글 프로그램  │
│   (웹 폼 입력)   │     │  (FastAPI)     │     │   (pyhwpx)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   Claude AI    │     │   HWP/HWPX     │
│  (문서 내용 생성) │     │   템플릿 처리   │
└─────────────────┘     └─────────────────┘
```

## 파일 구조

```
hwp-service/
├── hwp_service.py      # FastAPI 서버 (pyhwpx 기반)
├── hwpx-processor.js   # HWPX XML 처리 모듈 (Node.js)
├── requirements.txt    # Python 의존성
└── README.md          # 이 문서
```

## 설치 방법

### 1. Python 환경 설정

```bash
cd workflows/hwp-service
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. 한글 프로그램 요구사항

- **한컴오피스 한글** 설치 필요 (2010 이상 권장)
- Windows 운영체제 필수 (pyhwpx는 COM 자동화 사용)

### 3. 서비스 실행

```bash
python hwp_service.py
```

서비스가 `http://localhost:8765`에서 실행됩니다.

## API 엔드포인트

### 상태 확인
```
GET /
```

### 템플릿 목록
```
GET /templates
```

### IRB 문서 생성
```
POST /irb/generate
Content-Type: application/json

{
  "document_type": "연구계획서",
  "research_title": "연구 제목",
  "researcher_name": "연구자 이름",
  "researcher_affiliation": "소속",
  "research_purpose": "연구 목적",
  "research_method": "연구 방법",
  "participant_count": 30,
  "expected_duration": "약 30분"
}
```

### 일반 템플릿 처리
```
POST /process
Content-Type: application/json

{
  "template_path": "템플릿 경로",
  "fields": {
    "필드명1": "값1",
    "필드명2": "값2"
  }
}
```

### 파일 다운로드
```
GET /download/{filename}
```

## n8n 워크플로우 연동

### 방법 1: HTTP Request 노드 사용

1. **HTTP Request** 노드 추가
2. **Method**: POST
3. **URL**: `http://localhost:8765/irb/generate`
4. **Body Type**: JSON
5. **JSON Body**: IRB 요청 데이터

### 방법 2: 워크플로우 Import

`irb-document-generator.json` 파일을 n8n에 import하면 전체 워크플로우가 설정됩니다.

## HWP 템플릿 준비

### 누름틀 필드 사용 (권장)

한글 프로그램에서 **입력 > 누름틀**을 사용하여 필드를 정의합니다:

1. 한글에서 템플릿 문서 열기
2. 필드 위치에 커서 놓기
3. **입력 > 누름틀 > 일반** 선택
4. **필드 이름** 입력 (예: `연구과제명`, `연구자`)
5. 저장

### 플레이스홀더 사용

`{{필드명}}` 형식으로 텍스트 입력 후, 찾기/바꾸기로 대체합니다.

## HWPX 직접 처리 (크로스 플랫폼)

한글 프로그램 없이 HWPX 파일을 처리하려면 `hwpx-processor.js` 모듈을 사용합니다:

```javascript
const { processHwpxTemplate } = require('./hwpx-processor');

// 템플릿 파일을 버퍼로 읽기
const templateBuffer = fs.readFileSync('template.hwpx');

// 필드 데이터 준비
const fields = {
  '연구과제명': '실제 연구 제목',
  '연구자': '홍길동'
};

// 처리
const resultBuffer = await processHwpxTemplate(templateBuffer, fields);

// 저장
fs.writeFileSync('output.hwpx', resultBuffer);
```

### n8n Code 노드에서 사용

```javascript
const JSZip = require('jszip');

// HWPX 파일 처리 (간략화)
const templateBase64 = $input.first().json.templateFile;
const templateBuffer = Buffer.from(templateBase64, 'base64');

const zip = await JSZip.loadAsync(templateBuffer);
const sectionXml = await zip.file('Contents/section0.xml').async('string');

// 플레이스홀더 대체
let processed = sectionXml;
for (const [key, value] of Object.entries($input.first().json.fields)) {
  processed = processed.split(`{{${key}}}`).join(value);
}

zip.file('Contents/section0.xml', processed);

const outputBuffer = await zip.generateAsync({ type: 'base64' });

return { hwpxFile: outputBuffer };
```

## 문제 해결

### pyhwpx 설치 오류

```
pip install pywin32
pip install pyhwpx
```

### 한글 프로그램 연결 실패

1. 한글 프로그램이 설치되어 있는지 확인
2. 관리자 권한으로 Python 실행
3. 다른 한글 인스턴스가 실행 중이면 종료

### HWPX 파일 처리 오류

- HWPX는 한글 2014 이상에서 지원
- 기존 HWP 파일은 한글에서 HWPX로 다른 이름으로 저장 필요

## 참고 자료

- [pyhwpx 공식 문서](https://wikidocs.net/book/8956)
- [HWPX 포맷 구조](https://tech.hancom.com/hwpxformat/)
- [한컴디벨로퍼 포럼](https://forum.developer.hancom.com/)

## 라이선스

이 프로젝트는 연구/교육 목적으로 자유롭게 사용할 수 있습니다.
