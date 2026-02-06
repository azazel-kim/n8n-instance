# n8n Trend Research Automation System - Development Specification
# n8n 트렌드 리서치 자동화 시스템 - 개발 명세서

---

## Document Overview | 문서 개요

This document provides complete development specifications for building an n8n-based automated trend research system with Human-in-the-Loop feedback capabilities. The system supports two operational modes (Image/Text) and continues research iterations until user satisfaction.

본 문서는 Human-in-the-Loop 피드백 기능을 갖춘 n8n 기반 자동 트렌드 리서치 시스템 구축을 위한 전체 개발 명세서입니다. 시스템은 두 가지 운영 모드(이미지/텍스트)를 지원하며 사용자가 만족할 때까지 리서치를 반복 수행합니다.

---

# PART 1: ENGLISH DEVELOPMENT PROMPT

## 🔷 MASTER PROMPT FOR AI DEVELOPMENT AGENT

```
=================================================================
ROLE: n8n Workflow Development Engineer
PROJECT: Automated Trend Research System with Human-in-the-Loop
TARGET PLATFORM: n8n (Self-hosted or Cloud)
=================================================================

## MISSION STATEMENT

Build a complete n8n workflow that automates trend research for design images and technical content. The system must:
1. Accept user research requests via webhook/chat
2. Generate intelligent search queries using LLM
3. Collect and filter relevant content (images or text)
4. Present results to user via messaging platform
5. Loop until user approval, then archive to database

## TECHNICAL REQUIREMENTS

### Required Integrations
- LLM Provider: OpenAI GPT-4o API (primary) or Anthropic Claude 3.5 Sonnet
- Search API: Serper.dev (Google Search + Image Search)
- Messaging: Slack (primary) or Telegram Bot API
- Database: Notion API
- Optional: Browserless.io for deep web scraping

### Environment Variables to Configure
```json
{
  "OPENAI_API_KEY": "sk-...",
  "SERPER_API_KEY": "...",
  "SLACK_BOT_TOKEN": "xoxb-...",
  "SLACK_CHANNEL_ID": "C...",
  "NOTION_API_KEY": "secret_...",
  "NOTION_DATABASE_ID": "..."
}
```

## WORKFLOW ARCHITECTURE

### Node Structure (Build in this exact order)

#### PHASE 1: INPUT HANDLING

**Node 1: Webhook Trigger**
- Type: Webhook
- Method: POST
- Path: /research-trigger
- Authentication: Header Auth (optional)
- Expected Payload Schema:
```json
{
  "topic": "string (required) - Research subject",
  "reference_url": "string (optional) - Reference image/page URL",
  "mode": "string (required) - 'image' or 'text'",
  "feedback": "string (optional) - Previous iteration feedback",
  "session_id": "string (optional) - For continuing sessions"
}
```

**Node 2: Input Validator**
- Type: Code (JavaScript)
- Purpose: Validate and normalize input
- Logic:
```javascript
const input = $input.first().json;

// Validate required fields
if (!input.topic || !input.mode) {
  throw new Error('Missing required fields: topic and mode');
}

// Normalize mode
const normalizedMode = input.mode.toLowerCase().trim();
if (!['image', 'text'].includes(normalizedMode)) {
  throw new Error('Invalid mode. Must be "image" or "text"');
}

// Generate session ID if not provided
const sessionId = input.session_id || `session_${Date.now()}`;

return {
  topic: input.topic.trim(),
  referenceUrl: input.reference_url || null,
  mode: normalizedMode,
  feedback: input.feedback || null,
  sessionId: sessionId,
  timestamp: new Date().toISOString(),
  isNewSession: !input.session_id
};
```

#### PHASE 2: AI QUERY GENERATION

**Node 3: LLM Query Generator**
- Type: OpenAI Chat Model (or Anthropic Claude)
- Model: gpt-4o
- System Prompt:
```
You are an expert trend researcher specializing in design and technology analysis.

Your task: Generate optimized search queries based on the user's topic and mode.

## Output Format (JSON only, no markdown):
{
  "primary_queries": ["query1", "query2", "query3"],
  "secondary_queries": ["query4", "query5"],
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "search_filters": {
    "date_range": "past_month" | "past_year" | "any",
    "content_type": "specific type if applicable"
  },
  "analysis_focus": "Brief description of what to look for"
}

## Mode-Specific Instructions:

### IMAGE MODE:
- Generate queries for visual design research
- Include English AND Korean variations
- Focus on: CMF (Color, Material, Finish), form factor, UI/UX patterns
- Target platforms: Behance, Dribbble, Pinterest concepts
- Example queries: "portable fan industrial design 2024", "휴대용 선풍기 디자인 트렌드"

### TEXT MODE:
- Generate queries for technical/market research
- Include academic and industry sources
- Focus on: Technology specs, market analysis, patents, research papers
- Target: Tech blogs, academic papers, industry reports
- Example queries: "portable fan motor technology innovation", "BLDC motor miniaturization research"

## If feedback is provided:
Analyze the feedback and adjust queries to address user concerns.
Example: If feedback says "too colorful", add "minimalist", "monochrome", "clean design" to queries.
```

- User Message Template:
```
Topic: {{$node["Input Validator"].json.topic}}
Mode: {{$node["Input Validator"].json.mode}}
Reference URL: {{$node["Input Validator"].json.referenceUrl || "None provided"}}
Previous Feedback: {{$node["Input Validator"].json.feedback || "None - this is a new search"}}

Generate optimized search queries for this research task.
```

**Node 4: Parse LLM Response**
- Type: Code (JavaScript)
- Purpose: Extract and validate JSON from LLM response
```javascript
const response = $input.first().json.message.content;

// Handle potential markdown code blocks
let jsonStr = response;
if (response.includes('```json')) {
  jsonStr = response.split('```json')[1].split('```')[0];
} else if (response.includes('```')) {
  jsonStr = response.split('```')[1].split('```')[0];
}

try {
  const parsed = JSON.parse(jsonStr.trim());
  return {
    queries: [...(parsed.primary_queries || []), ...(parsed.secondary_queries || [])],
    keywords: parsed.keywords || [],
    searchFilters: parsed.search_filters || {},
    analysisFocus: parsed.analysis_focus || ''
  };
} catch (e) {
  // Fallback: extract any quoted strings as queries
  const fallbackQueries = response.match(/"([^"]+)"/g)?.map(q => q.replace(/"/g, '')) || [];
  return {
    queries: fallbackQueries.length > 0 ? fallbackQueries : [$input.first().json.topic],
    keywords: [],
    searchFilters: {},
    analysisFocus: ''
  };
}
```

#### PHASE 3: MODE ROUTING

**Node 5: Mode Switch**
- Type: Switch
- Mode: Rules
- Routing Rules:
  - Output 0 (Image): `{{$node["Input Validator"].json.mode}}` equals `image`
  - Output 1 (Text): `{{$node["Input Validator"].json.mode}}` equals `text`

#### PHASE 4A: IMAGE MODE EXECUTION

**Node 6A: Serper Image Search**
- Type: HTTP Request (Loop over queries)
- Method: POST
- URL: https://google.serper.dev/images
- Headers:
  - X-API-KEY: {{$env.SERPER_API_KEY}}
  - Content-Type: application/json
- Body:
```json
{
  "q": "{{$json.query}}",
  "num": 20,
  "gl": "us",
  "hl": "en"
}
```
- Execute for each query in the queries array

**Node 7A: Aggregate Image Results**
- Type: Code (JavaScript)
```javascript
const allItems = $input.all();
const uniqueImages = new Map();

for (const item of allItems) {
  const images = item.json.images || [];
  for (const img of images) {
    // Deduplicate by image URL
    if (!uniqueImages.has(img.imageUrl)) {
      uniqueImages.set(img.imageUrl, {
        imageUrl: img.imageUrl,
        thumbnailUrl: img.thumbnailUrl || img.imageUrl,
        title: img.title || 'Untitled',
        source: img.source || 'Unknown',
        sourceUrl: img.link || '',
        width: img.imageWidth || 0,
        height: img.imageHeight || 0
      });
    }
  }
}

// Filter: minimum resolution 400x400
const filtered = Array.from(uniqueImages.values())
  .filter(img => img.width >= 400 && img.height >= 400)
  .slice(0, 30); // Limit to top 30

return { images: filtered, totalFound: uniqueImages.size, filteredCount: filtered.length };
```

**Node 8A: Vision Analysis (Optional but Recommended)**
- Type: OpenAI Chat Model
- Model: gpt-4o
- Purpose: Analyze collected images for design patterns
- System Prompt:
```
You are a design trend analyst. Analyze the provided image URLs and identify:
1. Common design patterns and themes
2. Color palette trends
3. Material and finish trends
4. Form factor patterns
5. Key differentiating features

Provide a structured JSON summary.
```

#### PHASE 4B: TEXT MODE EXECUTION

**Node 6B: Serper Web Search**
- Type: HTTP Request (Loop over queries)
- Method: POST
- URL: https://google.serper.dev/search
- Headers:
  - X-API-KEY: {{$env.SERPER_API_KEY}}
  - Content-Type: application/json
- Body:
```json
{
  "q": "{{$json.query}}",
  "num": 10,
  "gl": "us",
  "hl": "en"
}
```

**Node 7B: Aggregate & Scrape Text Results**
- Type: Code (JavaScript) + HTTP Request nodes
```javascript
const allItems = $input.all();
const uniqueResults = new Map();

for (const item of allItems) {
  const organic = item.json.organic || [];
  for (const result of organic) {
    if (!uniqueResults.has(result.link)) {
      uniqueResults.set(result.link, {
        title: result.title,
        url: result.link,
        snippet: result.snippet,
        date: result.date || null,
        source: new URL(result.link).hostname
      });
    }
  }
}

return { results: Array.from(uniqueResults.values()).slice(0, 15) };
```

**Node 8B: Content Scraper**
- Type: HTTP Request (Loop over top 5 URLs)
- Purpose: Fetch full article content
- Configuration:
  - Method: GET
  - URL: {{$json.url}}
  - Response Format: String
- Note: Use n8n's HTML Extract node or Browserless.io for complex pages

**Node 9B: Text Summarization**
- Type: OpenAI Chat Model
- Model: gpt-4o
- System Prompt:
```
You are a research analyst. Summarize the provided content focusing on:
1. Key technological innovations
2. Market trends and statistics
3. Expert opinions and predictions
4. Actionable insights

Provide a structured summary with bullet points for each source.
Format as JSON with structure:
{
  "executive_summary": "2-3 sentence overview",
  "key_findings": ["finding1", "finding2", ...],
  "sources_summary": [
    {"source": "name", "key_points": ["point1", "point2"]}
  ],
  "recommended_deep_dives": ["topic1", "topic2"]
}
```

#### PHASE 5: RESULTS FORMATTING

**Node 10: Format Results for User**
- Type: Code (JavaScript)
- Purpose: Create user-friendly message
```javascript
const inputData = $node["Input Validator"].json;
const mode = inputData.mode;

let message = `🔍 **Research Results: ${inputData.topic}**\n`;
message += `📋 Session: ${inputData.sessionId}\n`;
message += `⏰ ${new Date().toLocaleString()}\n\n`;

if (mode === 'image') {
  const imageData = $node["Aggregate Image Results"].json;
  message += `📸 **Image Mode Results**\n`;
  message += `Found ${imageData.totalFound} images, showing top ${imageData.filteredCount}\n\n`;
  
  // Create thumbnail grid (for Slack blocks)
  const thumbnails = imageData.images.slice(0, 12).map((img, i) => ({
    type: 'image',
    image_url: img.thumbnailUrl,
    alt_text: img.title
  }));
  
  return {
    message: message,
    thumbnails: thumbnails,
    fullData: imageData,
    mode: mode
  };
} else {
  const textData = $node["Text Summarization"].json;
  message += `📝 **Text Mode Results**\n\n`;
  message += `**Executive Summary:**\n${textData.executive_summary}\n\n`;
  message += `**Key Findings:**\n`;
  textData.key_findings.forEach((f, i) => {
    message += `${i + 1}. ${f}\n`;
  });
  
  return {
    message: message,
    summaryData: textData,
    mode: mode
  };
}
```

#### PHASE 6: USER FEEDBACK LOOP

**Node 11: Send to Slack**
- Type: Slack
- Operation: Send Message (Block Kit)
- Channel: {{$env.SLACK_CHANNEL_ID}}
- Blocks:
```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "{{$json.message}}"
      }
    },
    {
      "type": "actions",
      "block_id": "research_actions_{{$node[\"Input Validator\"].json.sessionId}}",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "✅ Approve & Save"},
          "style": "primary",
          "action_id": "approve",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        },
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "🔄 Refine Search"},
          "action_id": "refine",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        },
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "🔀 Change Direction"},
          "action_id": "redirect",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        },
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "❌ Cancel"},
          "style": "danger",
          "action_id": "cancel",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        }
      ]
    }
  ]
}
```

**Node 12: Wait for User Response**
- Type: Wait
- Resume: On Webhook Call
- Webhook URL: Use n8n's built-in resume webhook
- Timeout: 30 minutes (optional)

**Node 13: Process User Feedback**
- Type: Switch
- Property: {{$json.action}}
- Routes:
  - `approve` → Node 14 (Save to Notion)
  - `refine` → Node 15 (Request Refinement Details) → Loop back to Node 3
  - `redirect` → Node 16 (Request New Direction) → Loop back to Node 3
  - `cancel` → Node 17 (Send Cancellation Message)

**Node 14: Save to Notion**
- Type: Notion
- Operation: Create Database Item
- Database ID: {{$env.NOTION_DATABASE_ID}}
- Properties:
```json
{
  "Title": {
    "title": [{"text": {"content": "[{{$now.format('YYYY-MM-DD')}}] {{$node[\"Input Validator\"].json.topic}}"}}]
  },
  "Type": {
    "select": {"name": "{{$node[\"Input Validator\"].json.mode === 'image' ? 'Design' : 'Tech'}}"}
  },
  "Status": {
    "select": {"name": "Completed"}
  },
  "Session ID": {
    "rich_text": [{"text": {"content": "{{$node[\"Input Validator\"].json.sessionId}}"}}]
  }
}
```
- Children (Page Content): Include full results as blocks

**Node 15: Request Refinement**
- Type: Slack
- Send message asking for specific feedback
- Wait for text response
- Pass feedback to webhook trigger for new iteration

#### PHASE 7: COMPLETION

**Node 17: Send Completion Message**
- Type: Slack
- Message: "✅ Research saved to Notion. Session {{sessionId}} completed."

## ERROR HANDLING REQUIREMENTS

1. **API Rate Limits**: Implement exponential backoff for Serper and OpenAI calls
2. **Invalid Responses**: Add try-catch blocks in Code nodes with fallback logic
3. **Timeout Handling**: Send timeout notification if user doesn't respond in 30 minutes
4. **Scraping Failures**: Skip failed URLs, continue with available content

## TESTING CHECKLIST

□ Test Image Mode with topic: "wireless earbuds design 2024"
□ Test Text Mode with topic: "AI chip technology trends"
□ Test feedback loop: Refine → Approve flow
□ Test feedback loop: Redirect → New search flow
□ Verify Notion database entries are correctly formatted
□ Test error handling with invalid API keys
□ Test timeout behavior

## DEPLOYMENT NOTES

1. Set all environment variables in n8n credentials
2. Configure Slack app with necessary OAuth scopes:
   - chat:write
   - chat:write.public
   - channels:read
3. Enable Notion integration and share database with integration
4. Set up webhook URL in Slack app for interactive components
```

---

# PART 2: 국문 개발 프롬프트

## 🔷 AI 개발 에이전트용 마스터 프롬프트

```
=================================================================
역할: n8n 워크플로우 개발 엔지니어
프로젝트: Human-in-the-Loop 자동 트렌드 리서치 시스템
대상 플랫폼: n8n (Self-hosted 또는 Cloud)
=================================================================

## 미션 정의

디자인 이미지 및 기술 콘텐츠에 대한 트렌드 리서치를 자동화하는 완전한 n8n 워크플로우를 구축하라.
시스템 필수 요건:
1. Webhook/채팅을 통해 사용자 리서치 요청 수신
2. LLM을 활용한 지능형 검색 쿼리 생성
3. 관련 콘텐츠(이미지 또는 텍스트) 수집 및 필터링
4. 메시징 플랫폼을 통해 사용자에게 결과 제시
5. 사용자 승인까지 반복 후 데이터베이스에 아카이브

## 기술 요구사항

### 필수 통합 서비스
- LLM 제공자: OpenAI GPT-4o API (주력) 또는 Anthropic Claude 3.5 Sonnet
- 검색 API: Serper.dev (Google 검색 + 이미지 검색)
- 메시징: Slack (주력) 또는 Telegram Bot API
- 데이터베이스: Notion API
- 선택사항: Browserless.io (심층 웹 스크래핑용)

### 설정할 환경 변수
```json
{
  "OPENAI_API_KEY": "sk-...",
  "SERPER_API_KEY": "...",
  "SLACK_BOT_TOKEN": "xoxb-...",
  "SLACK_CHANNEL_ID": "C...",
  "NOTION_API_KEY": "secret_...",
  "NOTION_DATABASE_ID": "..."
}
```

## 워크플로우 아키텍처

### 노드 구조 (정확히 이 순서대로 구축)

#### 1단계: 입력 처리

**노드 1: Webhook 트리거**
- 유형: Webhook
- 메서드: POST
- 경로: /research-trigger
- 인증: Header Auth (선택)
- 예상 페이로드 스키마:
```json
{
  "topic": "string (필수) - 리서치 주제",
  "reference_url": "string (선택) - 참조 이미지/페이지 URL",
  "mode": "string (필수) - 'image' 또는 'text'",
  "feedback": "string (선택) - 이전 반복 피드백",
  "session_id": "string (선택) - 세션 지속용"
}
```

**노드 2: 입력 검증기**
- 유형: Code (JavaScript)
- 목적: 입력 검증 및 정규화
- 로직:
```javascript
const input = $input.first().json;

// 필수 필드 검증
if (!input.topic || !input.mode) {
  throw new Error('필수 필드 누락: topic과 mode는 필수입니다');
}

// 모드 정규화
const normalizedMode = input.mode.toLowerCase().trim();
if (!['image', 'text'].includes(normalizedMode)) {
  throw new Error('잘못된 mode. "image" 또는 "text"여야 합니다');
}

// 세션 ID 생성 (미제공 시)
const sessionId = input.session_id || `session_${Date.now()}`;

return {
  topic: input.topic.trim(),
  referenceUrl: input.reference_url || null,
  mode: normalizedMode,
  feedback: input.feedback || null,
  sessionId: sessionId,
  timestamp: new Date().toISOString(),
  isNewSession: !input.session_id
};
```

#### 2단계: AI 쿼리 생성

**노드 3: LLM 쿼리 생성기**
- 유형: OpenAI Chat Model (또는 Anthropic Claude)
- 모델: gpt-4o
- 시스템 프롬프트:
```
당신은 디자인 및 기술 분석 전문 트렌드 리서처입니다.

작업: 사용자의 주제와 모드에 기반하여 최적화된 검색 쿼리를 생성하세요.

## 출력 형식 (JSON만, 마크다운 금지):
{
  "primary_queries": ["쿼리1", "쿼리2", "쿼리3"],
  "secondary_queries": ["쿼리4", "쿼리5"],
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "search_filters": {
    "date_range": "past_month" | "past_year" | "any",
    "content_type": "해당 시 특정 유형"
  },
  "analysis_focus": "찾아야 할 내용에 대한 간략한 설명"
}

## 모드별 지침:

### 이미지 모드 (IMAGE MODE):
- 시각적 디자인 리서치용 쿼리 생성
- 영어 AND 한국어 변형 포함
- 초점: CMF (Color, Material, Finish), 폼팩터, UI/UX 패턴
- 대상 플랫폼: Behance, Dribbble, Pinterest 컨셉
- 쿼리 예시: "portable fan industrial design 2024", "휴대용 선풍기 디자인 트렌드"

### 텍스트 모드 (TEXT MODE):
- 기술/시장 리서치용 쿼리 생성
- 학술 및 산업 소스 포함
- 초점: 기술 스펙, 시장 분석, 특허, 연구 논문
- 대상: 기술 블로그, 학술 논문, 산업 보고서
- 쿼리 예시: "portable fan motor technology innovation", "BLDC 모터 소형화 연구"

## 피드백이 제공된 경우:
피드백을 분석하고 사용자 우려사항을 반영하여 쿼리를 조정하세요.
예시: 피드백이 "너무 화려해"라면, "minimalist", "monochrome", "clean design" 키워드 추가
```

- 사용자 메시지 템플릿:
```
주제: {{$node["Input Validator"].json.topic}}
모드: {{$node["Input Validator"].json.mode}}
참조 URL: {{$node["Input Validator"].json.referenceUrl || "제공되지 않음"}}
이전 피드백: {{$node["Input Validator"].json.feedback || "없음 - 신규 검색"}}

이 리서치 작업을 위한 최적화된 검색 쿼리를 생성하세요.
```

**노드 4: LLM 응답 파싱**
- 유형: Code (JavaScript)
- 목적: LLM 응답에서 JSON 추출 및 검증
```javascript
const response = $input.first().json.message.content;

// 마크다운 코드 블록 처리
let jsonStr = response;
if (response.includes('```json')) {
  jsonStr = response.split('```json')[1].split('```')[0];
} else if (response.includes('```')) {
  jsonStr = response.split('```')[1].split('```')[0];
}

try {
  const parsed = JSON.parse(jsonStr.trim());
  return {
    queries: [...(parsed.primary_queries || []), ...(parsed.secondary_queries || [])],
    keywords: parsed.keywords || [],
    searchFilters: parsed.search_filters || {},
    analysisFocus: parsed.analysis_focus || ''
  };
} catch (e) {
  // 폴백: 따옴표로 둘러싸인 문자열을 쿼리로 추출
  const fallbackQueries = response.match(/"([^"]+)"/g)?.map(q => q.replace(/"/g, '')) || [];
  return {
    queries: fallbackQueries.length > 0 ? fallbackQueries : [$input.first().json.topic],
    keywords: [],
    searchFilters: {},
    analysisFocus: ''
  };
}
```

#### 3단계: 모드 라우팅

**노드 5: 모드 스위치**
- 유형: Switch
- 모드: Rules
- 라우팅 규칙:
  - 출력 0 (이미지): `{{$node["Input Validator"].json.mode}}` equals `image`
  - 출력 1 (텍스트): `{{$node["Input Validator"].json.mode}}` equals `text`

#### 4A단계: 이미지 모드 실행

**노드 6A: Serper 이미지 검색**
- 유형: HTTP Request (쿼리별 루프)
- 메서드: POST
- URL: https://google.serper.dev/images
- 헤더:
  - X-API-KEY: {{$env.SERPER_API_KEY}}
  - Content-Type: application/json
- 본문:
```json
{
  "q": "{{$json.query}}",
  "num": 20,
  "gl": "kr",
  "hl": "ko"
}
```

**노드 7A: 이미지 결과 집계**
- 유형: Code (JavaScript)
```javascript
const allItems = $input.all();
const uniqueImages = new Map();

for (const item of allItems) {
  const images = item.json.images || [];
  for (const img of images) {
    // 이미지 URL로 중복 제거
    if (!uniqueImages.has(img.imageUrl)) {
      uniqueImages.set(img.imageUrl, {
        imageUrl: img.imageUrl,
        thumbnailUrl: img.thumbnailUrl || img.imageUrl,
        title: img.title || '제목 없음',
        source: img.source || '출처 불명',
        sourceUrl: img.link || '',
        width: img.imageWidth || 0,
        height: img.imageHeight || 0
      });
    }
  }
}

// 필터: 최소 해상도 400x400
const filtered = Array.from(uniqueImages.values())
  .filter(img => img.width >= 400 && img.height >= 400)
  .slice(0, 30); // 상위 30개로 제한

return { images: filtered, totalFound: uniqueImages.size, filteredCount: filtered.length };
```

**노드 8A: Vision 분석 (선택사항이나 권장)**
- 유형: OpenAI Chat Model
- 모델: gpt-4o
- 목적: 수집된 이미지의 디자인 패턴 분석
- 시스템 프롬프트:
```
당신은 디자인 트렌드 분석가입니다. 제공된 이미지 URL을 분석하여 다음을 식별하세요:
1. 공통 디자인 패턴 및 테마
2. 컬러 팔레트 트렌드
3. 재질 및 마감 트렌드
4. 폼팩터 패턴
5. 핵심 차별화 특징

구조화된 JSON 요약을 제공하세요.
```

#### 4B단계: 텍스트 모드 실행

**노드 6B: Serper 웹 검색**
- 유형: HTTP Request (쿼리별 루프)
- 메서드: POST
- URL: https://google.serper.dev/search
- 헤더:
  - X-API-KEY: {{$env.SERPER_API_KEY}}
  - Content-Type: application/json
- 본문:
```json
{
  "q": "{{$json.query}}",
  "num": 10,
  "gl": "kr",
  "hl": "ko"
}
```

**노드 7B: 텍스트 결과 집계 및 스크래핑**
- 유형: Code (JavaScript) + HTTP Request 노드
```javascript
const allItems = $input.all();
const uniqueResults = new Map();

for (const item of allItems) {
  const organic = item.json.organic || [];
  for (const result of organic) {
    if (!uniqueResults.has(result.link)) {
      uniqueResults.set(result.link, {
        title: result.title,
        url: result.link,
        snippet: result.snippet,
        date: result.date || null,
        source: new URL(result.link).hostname
      });
    }
  }
}

return { results: Array.from(uniqueResults.values()).slice(0, 15) };
```

**노드 8B: 콘텐츠 스크래퍼**
- 유형: HTTP Request (상위 5개 URL에 루프)
- 목적: 전체 기사 콘텐츠 가져오기
- 설정:
  - 메서드: GET
  - URL: {{$json.url}}
  - 응답 형식: String
- 참고: 복잡한 페이지는 n8n의 HTML Extract 노드 또는 Browserless.io 사용

**노드 9B: 텍스트 요약**
- 유형: OpenAI Chat Model
- 모델: gpt-4o
- 시스템 프롬프트:
```
당신은 리서치 분석가입니다. 제공된 콘텐츠를 다음에 초점을 맞춰 요약하세요:
1. 핵심 기술 혁신
2. 시장 트렌드 및 통계
3. 전문가 의견 및 예측
4. 실행 가능한 인사이트

각 소스에 대해 불릿 포인트가 있는 구조화된 요약을 제공하세요.
다음 구조의 JSON으로 형식화:
{
  "executive_summary": "2-3문장 개요",
  "key_findings": ["발견1", "발견2", ...],
  "sources_summary": [
    {"source": "이름", "key_points": ["포인트1", "포인트2"]}
  ],
  "recommended_deep_dives": ["주제1", "주제2"]
}
```

#### 5단계: 결과 포매팅

**노드 10: 사용자용 결과 포맷**
- 유형: Code (JavaScript)
- 목적: 사용자 친화적 메시지 생성
```javascript
const inputData = $node["Input Validator"].json;
const mode = inputData.mode;

let message = `🔍 **리서치 결과: ${inputData.topic}**\n`;
message += `📋 세션: ${inputData.sessionId}\n`;
message += `⏰ ${new Date().toLocaleString('ko-KR')}\n\n`;

if (mode === 'image') {
  const imageData = $node["Aggregate Image Results"].json;
  message += `📸 **이미지 모드 결과**\n`;
  message += `총 ${imageData.totalFound}개 발견, 상위 ${imageData.filteredCount}개 표시\n\n`;
  
  // 썸네일 그리드 생성 (Slack 블록용)
  const thumbnails = imageData.images.slice(0, 12).map((img, i) => ({
    type: 'image',
    image_url: img.thumbnailUrl,
    alt_text: img.title
  }));
  
  return {
    message: message,
    thumbnails: thumbnails,
    fullData: imageData,
    mode: mode
  };
} else {
  const textData = $node["Text Summarization"].json;
  message += `📝 **텍스트 모드 결과**\n\n`;
  message += `**핵심 요약:**\n${textData.executive_summary}\n\n`;
  message += `**주요 발견:**\n`;
  textData.key_findings.forEach((f, i) => {
    message += `${i + 1}. ${f}\n`;
  });
  
  return {
    message: message,
    summaryData: textData,
    mode: mode
  };
}
```

#### 6단계: 사용자 피드백 루프

**노드 11: Slack 전송**
- 유형: Slack
- 작업: Send Message (Block Kit)
- 채널: {{$env.SLACK_CHANNEL_ID}}
- 블록:
```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "{{$json.message}}"
      }
    },
    {
      "type": "actions",
      "block_id": "research_actions_{{$node[\"Input Validator\"].json.sessionId}}",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "✅ 승인 & 저장"},
          "style": "primary",
          "action_id": "approve",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        },
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "🔄 검색 정제"},
          "action_id": "refine",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        },
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "🔀 방향 전환"},
          "action_id": "redirect",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        },
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "❌ 취소"},
          "style": "danger",
          "action_id": "cancel",
          "value": "{{$node[\"Input Validator\"].json.sessionId}}"
        }
      ]
    }
  ]
}
```

**노드 12: 사용자 응답 대기**
- 유형: Wait
- 재개: On Webhook Call
- Webhook URL: n8n 내장 재개 웹훅 사용
- 타임아웃: 30분 (선택)

**노드 13: 사용자 피드백 처리**
- 유형: Switch
- 속성: {{$json.action}}
- 라우트:
  - `approve` → 노드 14 (Notion 저장)
  - `refine` → 노드 15 (정제 세부사항 요청) → 노드 3으로 루프백
  - `redirect` → 노드 16 (새 방향 요청) → 노드 3으로 루프백
  - `cancel` → 노드 17 (취소 메시지 전송)

**노드 14: Notion 저장**
- 유형: Notion
- 작업: Create Database Item
- 데이터베이스 ID: {{$env.NOTION_DATABASE_ID}}
- 속성:
```json
{
  "Title": {
    "title": [{"text": {"content": "[{{$now.format('YYYY-MM-DD')}}] {{$node[\"Input Validator\"].json.topic}}"}}]
  },
  "Type": {
    "select": {"name": "{{$node[\"Input Validator\"].json.mode === 'image' ? '디자인' : '기술'}}"}
  },
  "Status": {
    "select": {"name": "완료"}
  },
  "Session ID": {
    "rich_text": [{"text": {"content": "{{$node[\"Input Validator\"].json.sessionId}}"}}]
  }
}
```
- Children (페이지 콘텐츠): 전체 결과를 블록으로 포함

**노드 15: 정제 요청**
- 유형: Slack
- 구체적인 피드백 요청 메시지 전송
- 텍스트 응답 대기
- 피드백을 웹훅 트리거에 전달하여 새 반복 시작

#### 7단계: 완료

**노드 17: 완료 메시지 전송**
- 유형: Slack
- 메시지: "✅ 리서치가 Notion에 저장되었습니다. 세션 {{sessionId}} 완료."

## 오류 처리 요구사항

1. **API 속도 제한**: Serper 및 OpenAI 호출에 지수 백오프 구현
2. **잘못된 응답**: Code 노드에 폴백 로직과 함께 try-catch 블록 추가
3. **타임아웃 처리**: 사용자가 30분 내 응답하지 않으면 타임아웃 알림 전송
4. **스크래핑 실패**: 실패한 URL 건너뛰고 사용 가능한 콘텐츠로 계속 진행

## 테스트 체크리스트

□ 이미지 모드 테스트 (주제: "무선 이어폰 디자인 2024")
□ 텍스트 모드 테스트 (주제: "AI 칩 기술 트렌드")
□ 피드백 루프 테스트: 정제 → 승인 흐름
□ 피드백 루프 테스트: 방향 전환 → 새 검색 흐름
□ Notion 데이터베이스 항목 형식 검증
□ 잘못된 API 키로 오류 처리 테스트
□ 타임아웃 동작 테스트

## 배포 참고사항

1. n8n 자격 증명에 모든 환경 변수 설정
2. 필요한 OAuth 스코프로 Slack 앱 구성:
   - chat:write
   - chat:write.public
   - channels:read
3. Notion 통합 활성화 및 통합과 데이터베이스 공유
4. 대화형 컴포넌트용 Slack 앱에 웹훅 URL 설정
```

---

# PART 3: QUICK REFERENCE CARDS

## 🔷 Workflow Node Map (Visual Reference)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        n8n RESEARCH AUTOMATION FLOW                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1. Webhook] ──► [2. Validator] ──► [3. LLM Query Gen] ──► [4. Parser] │
│                                                                          │
│                              ▼                                           │
│                        [5. Mode Switch]                                  │
│                         /           \                                    │
│                        ▼             ▼                                   │
│              [6A. Image Search]  [6B. Web Search]                        │
│                    ▼                   ▼                                 │
│              [7A. Aggregate]     [7B. Aggregate]                         │
│                    ▼                   ▼                                 │
│              [8A. Vision AI]     [8B. Scraper]                           │
│                    \                   /                                 │
│                     \                 /                                  │
│                      ▼               ▼                                   │
│                     [9B. Summarize (text only)]                          │
│                              ▼                                           │
│                    [10. Format Results]                                  │
│                              ▼                                           │
│                    [11. Send to Slack]                                   │
│                              ▼                                           │
│                    [12. Wait for Response]                               │
│                              ▼                                           │
│                    [13. Process Feedback]                                │
│                    /     |      |      \                                 │
│                   ▼      ▼      ▼       ▼                                │
│             [Approve] [Refine] [Redirect] [Cancel]                       │
│                 │        │        │          │                           │
│                 ▼        └────┬───┘          ▼                           │
│            [14. Save         │         [17. End]                         │
│             to Notion]       │                                           │
│                 │            ▼                                           │
│                 │      [Loop to Node 3]                                  │
│                 ▼                                                        │
│            [17. Complete]                                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🔷 API Endpoints Quick Reference

| Service | Endpoint | Method | Auth Header |
|---------|----------|--------|-------------|
| Serper Images | `https://google.serper.dev/images` | POST | X-API-KEY |
| Serper Search | `https://google.serper.dev/search` | POST | X-API-KEY |
| OpenAI Chat | `https://api.openai.com/v1/chat/completions` | POST | Authorization: Bearer |
| Notion Create | `https://api.notion.com/v1/pages` | POST | Authorization: Bearer |
| Slack Post | `https://slack.com/api/chat.postMessage` | POST | Authorization: Bearer |

## 🔷 Environment Variables Checklist

```bash
# Required
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...

# Optional
BROWSERLESS_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
```

---

# PART 4: IMPLEMENTATION TIMELINE

## Suggested Development Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Core Setup | 2-3 hours | Webhook, Validator, LLM nodes |
| Phase 2: Image Pipeline | 2-3 hours | Serper image search, aggregation |
| Phase 3: Text Pipeline | 2-3 hours | Web search, scraping, summarization |
| Phase 4: Feedback Loop | 3-4 hours | Slack integration, wait nodes, routing |
| Phase 5: Storage | 1-2 hours | Notion integration |
| Phase 6: Testing & Polish | 2-3 hours | Error handling, edge cases |

**Total Estimated Time: 12-18 hours**

---

*Document Version: 1.0*
*Last Updated: 2026-02-05*
*Prepared for: n8n Workflow Development*
