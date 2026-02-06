  
**n8n \+ Discord 자동화 워크플로우**

**n8n \+ Discord Automation Workflow**

Claude Code AI 에이전트용 상세 지시서

Detailed Instruction Manual for Claude Code AI Agent

문서 버전: 1.0  |  작성일: 2026-02-06  |  작성: Claude AI

물품 관리 · 음식점 잔고 관리 · Google Sheets 연동 자동화 시스템

Asset Management · Restaurant Balance Tracking · Google Sheets Integration

# **목차 (Table of Contents)**

| No | 항목 (Section) |
| :---: | ----- |
| 1 | 프로젝트 개요 (Project Overview) |
| 2 | 기술 아키텍처 (Technical Architecture) |
| 3 | 세부 기능 정의 (Detailed Feature Specifications) |
| 4 | Google Sheets 데이터 구조 (Data Structure) |
| 5 | Discord Bot 설계 (Bot Design) |
| 6 | Discord ↔ n8n 연동 방법 (Integration Methods) |
| 7 | n8n 워크플로우 설계 (Workflow Design) |
| 8 | AI 메시지 분류 설계 (AI Message Classification) |
| 9 | 관리자 기능 (Admin Features) |
| 10 | 오류 처리 및 로깅 (Error Handling & Logging) |
| 11 | 테스트 체크리스트 (Testing Checklist) |
| 12 | Claude Code 프롬프트 \- 국문 (Korean Prompt) |
| 13 | Claude Code 프롬프트 \- 영문 (English Prompt) |
| 14 | 구현 단계 로드맵 (Implementation Roadmap) |

# **1\. 프로젝트 개요 (Project Overview)**

## **1.1 프로젝트 목적 (Project Purpose)**

소규모 내부 팀(10명)의 물품 관리와 음식점 잔고 관리 업무를 Discord(디스코드) 메신저와 n8n 워크플로우를 통해 자동화하는 시스템을 구축함. 사용자들은 스마트폰/PC에서 Discord 앱의 지정된 채널에 메시지를 보내면, AI(Artificial Intelligence, 인공지능)가 메시지 내용을 분석하여 자동으로 해당 업무를 처리하고 Google Sheets(구글 시트)에 기록하며, 관리자에게 알림을 발송함.

Discord를 선택한 이유: 텔레그램 대비 한국에서 신규 가입 시 SMS 인증 비용(\~2,000원) 문제가 없고, 무료 Bot API가 제공되며, PC/모바일 모두 지원하고, 채널 구조로 업무별 분리 관리가 용이함.

## **1.2 사용자 구분 (User Roles)**

| 역할 (Role) | 인원 (Count) | 권한 (Permissions) |
| ----- | ----- | ----- |
| **관리자 (Admin)** | 1\~2명 | • 워크플로우 수정/추가 • Google Sheets 직접 수정 • 봇 명령어로 설정 변경 • 모든 알림 수신 |
| **일반 사용자 (User)** | \~10명 | • 물품 등록/폐기/위치/사용자 등록 • 음식점 잔고 보고 • 물품 조회 |

## **1.3 기술 스택 (Technology Stack)**

| 구성요소 | 기술 | 역할 |
| ----- | ----- | ----- |
| **메신저** | Discord Bot API (discord.js v14) | 사용자 입력 수신 및 알림 발송 |
| **봇 브릿지** | Discord.js \+ Node.js 봇 | Discord ↔ n8n Webhook 연결 |
| **자동화 엔진** | n8n (셋프호스팅 또는 클라우드) | 워크플로우 실행 및 관리 |
| **데이터베이스** | Google Sheets API v4 | 물품/음식점 데이터 저장 |
| **AI 분류** | OpenAI GPT-4o / Claude API | 메시지 의도 분석 및 업무 분류 |
| **QR코드** | Discord 카메라 \+ QR 인식 라이브러리 | QR코드 스캔 및 물품 식별 |
| **인프라** | Google Workspace 계정 | 인증 및 권한 관리 |

## **1.4 물품 규모 (Asset Scale)**

물품 총 수량: 최대 10개 내외 (소규모)

물품 종류: VR(Virtual Reality, 가상현실) 헤드셋, AR(Augmented Reality, 증강현실) 안경, 관련 악세서리, 일반 프린터, 3D 프린터 등 전자 기기류

QR코드 스티커: 대부분 기존 부착되어 있으며, 미부착 물품은 신규 QR 생성 후 부착

# **2\. 기술 아키텍처 (Technical Architecture)**

## **2.1 시스템 흐름도 (System Flow)**

전체 시스템은 다음과 같은 흐름으로 구성됨:

┌─────────────────┐     ┌────────────────┐     ┌────────────────┐  
│ Discord App    │ ───\> │ Discord.js Bot│ ───\> │  n8n Server    │  
│ (사용자 스마트폰)│     │ (Bridge Bot)  │     │  (Webhook)     │  
└─────────────────┘     └────────────────┘     └──────┬─────────┘  
                                                       │  
                              ┌─────────────────┼────────────────┐  
                              │                 │                │  
                       ┌─────┴─────┐  ┌─────┴─────┐  ┌────┴───────┐  
                       │ AI Engine  │  │ Google     │  │ Discord    │  
                       │ (GPT/     │  │ Sheets API │  │ Reply      │  
                       │  Claude)  │  │            │  │ (채널/DM)  │  
                       └───────────┘  └────────────┘  └────────────┘

⚠ **Telegram과의 핵심 차이: n8n에 Discord 메시지 수신 Trigger가 내장되어 있지 않으므로, Discord.js Bridge Bot이 필수적으로 필요함.**

💡 **대안: n8n Community Node(n8n-nodes-discord-trigger-new v0.10.11)를 설치하면 Bridge Bot 없이도 가능. 섹션 6에서 상세 설명.**

## **2.2 핵심 컴포넌트 설명 (Core Components)**

| 컴포넌트 | 설명 | 기술 상세 |
| ----- | ----- | ----- |
| **Discord Bot** | 서버 채널의 메시지를 수신하고 봇이 응답을 발송하는 역할 | Discord Developer Portal에서 생성 Privileged Gateway Intents 활성화 Message Content Intent 필수 |
| **Bridge Bot (Node.js)** | Discord 메시지를 n8n Webhook으로 전달하는 중간 브릿지 | discord.js v14 \+ axios PM2로 상시 실행 messageCreate 이벤트 감지 |
| **n8n Webhook** | Bridge Bot에서 받은 데이터로 워크플로우 실행 | Webhook Trigger 노드 사용 POST 방식으로 JSON 수신 |
| **AI 분류 엔진** | 받은 메시지의 의도를 분석하여 업무 유형 분류 | OpenAI GPT-4o 또는 Claude API JSON 형식으로 분류 결과 반환 |
| **Google Sheets** | 데이터 저장소. 물품, 히스토리, 음식점 잔고 관리 | Google Sheets API v4 Service Account 인증 |
| **Discord Action Node** | n8n에서 Discord 채널에 메시지 발송 | n8n 내장 Discord 노드 사용 채널/DM 발송 모두 지원 |

## **2.3 통신 흐름 상세 (Communication Flow Detail)**

1단계: 사용자가 Discord 서버의 지정 채널에 메시지(텍스트 또는 사진+텍스트) 전송

2단계: Discord.js Bridge Bot이 messageCreate 이벤트를 감지하여 n8n Webhook URL로 HTTP POST 요청 발송

3단계: n8n Webhook Trigger가 데이터를 수신하고 AI 엔진을 호출하여 메시지 내용 분석 및 업무 유형 분류

4단계: 분류된 업무 유형에 따라 해당 Sub-workflow 분기(Switch 노드) 실행

5단계: Google Sheets API를 통해 해당 시트에 데이터 기록/수정

6단계: n8n Discord Action 노드로 처리 결과를 채널에 확인 메시지 발송 \+ 관리자 DM(Direct Message) 알림

# **3\. 세부 기능 정의 (Detailed Feature Specifications)**

## **3.1 기능 1: 물품 관리 (Asset Management)**

물품의 전체 수명주기(Lifecycle)를 관리하는 핵심 기능. QR코드를 기반으로 물품을 식별하고, 등록부터 폐기까지의 모든 이력을 추적함.

### **3.1.1 신규 등록 (New Registration)**

| 항목 | 상세 내용 |
| ----- | ----- |
| **트리거 (Trigger)** | 사용자가 QR코드 사진 \+ "등록" 키워드를 포함한 메시지 전송 |
| **입력 형식 (Input)** | \[QR 사진 첨부\] 등록 VR헤드셋 Meta Quest 3 위치: 3층 회의실 A 사용자: 홍길동 |
| **처리 로직 (Logic)** | 1\. 첨부파일(attachment)에서 QR 사진 URL 추출 2\. QR 디코드 API로 물품 ID 추출 3\. AI가 메시지에서 물품명, 위치, 사용자 파싱 4\. Google Sheets '물품목록' 시트에 새 행 추가 5\. '물품히스토리' 시트에 등록 이력 기록 6\. 관리자에게 DM 알림 발송 |
| **출력 (Output)** | ✓ 채널에 등록 완료 메시지 ✓ 관리자 DM 알림 |

### **3.1.2 폐기 등록 (Disposal Registration)**

| 항목 | 상세 내용 |
| ----- | ----- |
| **트리거** | QR 사진 \+ "폐기" 키워드 전송 |
| **처리 로직** | 1\. QR에서 물품 ID 추출 2\. 물품목록에서 상태를 '폐기'로 변경 3\. 폐기 사유와 날짜를 히스토리에 기록 4\. 관리자 DM 알림 |

### **3.1.3 위치 정보 업데이트 (Location Update)**

| 항목 | 상세 내용 |
| ----- | ----- |
| **트리거** | QR 사진 \+ "위치" 또는 "이동" 키워드 |
| **처리 로직** | 1\. QR에서 물품 ID 추출 2\. 물품목록에서 현재위치 컬럼 업데이트 3\. 히스토리에 위치 변경 기록 4\. 관리자 DM 알림 |

### **3.1.4 사용자 변경 (User Assignment Update)**

| 항목 | 상세 내용 |
| ----- | ----- |
| **트리거** | QR 사진 \+ "사용자" 또는 "배정" 키워드 |
| **처리 로직** | 1\. QR에서 물품 ID 추출 2\. 물품목록에서 현재사용자 컬럼 업데이트 3\. 히스토리에 사용자 변경 기록 4\. 관리자 DM 알림 |

### **3.1.5 물품 조회 (Asset Inquiry)**

| 항목 | 상세 내용 |
| ----- | ----- |
| **트리거** | QR 사진 \+ "확인"/"조회" 키워드, 또는 물품명으로 조회 |
| **출력** | 물품명, 현재 위치, 현재 사용자, 상태, 최근 사용 이력 3건 등을 Discord 채널 메시지로 반환 |

 

## **3.2 기능 2: 음식점 잔고 관리 (Restaurant Balance Management)**

거래 음식점별 잔고(balance)를 관리하는 기능. 사용자가 식당 이름과 잔고를 적어 보내면 AI가 자동으로 감지하고 처리함.

| 항목 | 상세 내용 |
| ----- | ----- |
| **트리거** | "미스터피자 잔고 15만원" 또는 "김밥천국 230,000원 남음" 등 자연어 메시지 |
| **AI 감지 로직** | AI가 메시지에서 다음을 파싱: • 업무 유형: 'restaurant\_balance' • 음식점명: 추출된 식당 이름 • 금액: 추출된 잔고 금액 (숫자만) |
| **처리 로직** | 1\. '음식점잔고' 시트에서 해당 식당 행 검색 2\. 잔고 컬럼 업데이트 3\. 업데이트 날짜/시간/처리자 기록 4\. 식당이 목록에 없으면 확인 요청 5\. 관리자 DM 알림 |
| **알림 내용** | "✅ 음식점 잔고 업데이트" 식당: 미스터피자 변경 전: 200,000원 → 변경 후: 150,000원 처리자: @홍길동 | 일시: 2026-02-06 14:30 |

 

## **3.3 기능 3: Google Sheets 충돌 감지 (Conflict Detection)**

Google Sheets 원본을 권한자가 직접 수정했을 경우, 자동화 시스템과의 충돌을 감지하여 관리자에게 알려주는 기능.

| 항목 | 상세 내용 |
| ----- | ----- |
| **감지 방식** | 1\. n8n Schedule Trigger로 5분마다 시트 스냅샷 생성 2\. 이전 스냅샷과 비교하여 변경사항 감지 3\. 자동화 시스템이 아닌 외부 변경시 알림 |
| **구현 방법** | 자동화 시스템이 기록할 때 특정 컬럼에 '시스템' 표시를 남기고, 이 표시가 없는 변경은 수동 수정으로 판단 |
| **알림 내용** | "⚠️ Google Sheets 수동 수정 감지" 시트: 물품목록 | 변경된 셀: B3 변경 전: VR헤드셋 A → 변경 후: VR헤드셋 B |

# **4\. Google Sheets 데이터 구조 (Data Structure)**

하나의 Google Sheets 파일 내에 여러 시트(탭)를 생성하여 데이터를 관리함.

## **4.1 시트 1: AssetList (물품목록)**

현재 등록된 모든 물품의 최신 상태 관리 마스터 시트.

컬럼: No, 물품ID, 물품명, 카테고리, 상태, 현재위치, 현재사용자, 등록일, 최종수정일, 수정출처, 비고

## **4.2 시트 2: AssetHistory (물품히스토리)**

물품의 모든 변경 이력을 시간순으로 기록. 삭제하지 않고 계속 추가만 함.

컬럼: 날짜시간, 물품ID, 액션(신규등록/폐기/위치변경/사용자변경/조회), 처리자, 상세내용, 이전값, 변경값

## **4.3 시트 3: RestaurantBalance (음식점잔고)**

컬럼: 식당명, 현재잔고, 최종업데이트일시, 처리자, 이전잔고, 비고

## **4.4 시트 4: SystemLog (시스템로그)**

모든 시스템 처리 로그를 기록. 디버깅과 운영 모니터링에 사용.

컬럼: 날짜시간, Discord사용자, 업무유형, 처리결과, 원본메시지, AI분류결과, 오류내용

## **4.5 시트 5: Config (설정)**

시스템 설정값 관리 시트. 관리자가 직접 수정 가능.

| 설정키 | 값 (예시) | 설명 |
| ----- | ----- | ----- |
| **ADMIN\_DISCORD\_IDS** | 123456789, 987654321 | 관리자 Discord User ID 목록 |
| **WORK\_CHANNEL\_ID** | 1234567890123456 | 업무 채널 ID (단일 채널) |
| **CONFLICT\_CHECK\_MIN** | 5 | 충돌 검사 주기 (분) |
| **AI\_MODEL** | gpt-4o | 사용할 AI 모델 |
| **N8N\_WEBHOOK\_URL** | https://n8n.example.com/webhook/xxx | n8n Webhook URL |

# **5\. Discord Bot 설계 (Bot Design)**

## **5.1 Discord 서버 구조 (Server Structure)**

모든 업무를 단일 채널에서 처리하는 간결한 구조로 구성함. 봇의 응답과 관리자 알림이 모두 동일 채널에서 이루어지며, 관리자 전용 알림은 DM(Direct Message)으로 발송됨.

| 채널명 | 용도 |
| ----- | ----- |
| **\#업무 (또는 \#work)** | • 모든 사용자가 업무 메시지를 입력하는 유일한 채널 • 봇의 처리 결과 응답도 이 채널에 표시 • 시스템 알림, 충돌 감지 알림도 이 채널에 표시 • 관리자 전용 알림은 DM으로 별도 발송 |

💡 **단일 채널 구조의 장점: 설정이 간단하고, 사용자가 채널을 헷갈릴 필요 없음. 향후 필요시 채널을 추가하여 분리 가능.**

## **5.2 봇 생성 및 설정 (Bot Setup)**

Discord Developer Portal(https://discord.com/developers/applications)에서 봇을 생성하고 설정함.

| 설정 항목 | 상세 |
| ----- | ----- |
| **Application 생성** | New Application 클릭 → 이름 입력 (TeamAssetBot) |
| **Bot 생성** | Bot 탭 → Add Bot |
| **Bot Token** | Reset Token → 토큰 복사하여 안전하게 보관 |
| **Privileged Gateway Intents** | MESSAGE CONTENT INTENT: 활성화 (필수) SERVER MEMBERS INTENT: 활성화 (권장) |
| **OAuth2 초대 URL** | OAuth2 → URL Generator Scopes: bot, applications.commands Bot Permissions: Read Messages, Send Messages, Attach Files, Read Message History, Use Slash Commands |
| **서버 초대** | 생성된 URL을 브라우저에서 열어 Discord 서버에 봇 초대 |

## **5.3 메시지 형식 가이드 (Message Format Guide)**

사용자들은 자연어로 입력하면 되며, AI가 자동으로 의도를 파악함.

| 업무 유형 | 입력 예시 | 비고 |
| ----- | ----- | ----- |
| **물품 신규등록** | \[QR사진 첨부\] \+ "등록 VR헤드셋 이름 위치 사용자" | QR사진 필수 |
| **물품 폐기** | \[QR사진\] \+ "폐기 고장으로 폐기" | QR사진 필수 |
| **위치 변경** | \[QR사진\] \+ "위치 2층 연구실로 이동" | QR사진 필수 |
| **사용자 변경** | \[QR사진\] \+ "사용자 김철수로 변경" | QR사진 필수 |
| **물품 조회** | \[QR사진\] \+ "확인" 또는 "물품명 조회" | QR 또는 텍스트만 |
| **음식점 잔고** | "미스터피자 15만원" 또는 "김밥 230000원" | 텍스트만 |
| **도움말** | \!help 또는 /help | 사용 가이드 표시 |

## **5.4 Slash Commands (슬래시 명령어)**

Discord의 Slash Command 기능을 활용하여 관리자 명령어를 구현할 수 있음:

| 명령어 | 기능 | 권한 |
| ----- | ----- | ----- |
| **/help** | 사용 가이드 표시 | 모든 사용자 |
| **/status** | 시스템 상태 확인 | 관리자 |
| **/list** | 전체 물품 목록 조회 | 모든 사용자 |
| **/restaurants** | 전체 음식점 잔고 조회 | 모든 사용자 |
| **/config \[key\] \[value\]** | 설정값 변경 | 관리자 |

# **6\. Discord ↔ n8n 연동 방법 (Integration Methods)**

Discord에서 n8n으로 메시지를 전달하는 2가지 방법이 있음. 프로젝트 상황에 따라 선택:

## **6.1 방법 A: Discord.js Bridge Bot (권장)**

별도의 Node.js 봇을 서버에서 실행하여 Discord 메시지를 n8n Webhook으로 전달하는 방식.

| 항목 | 상세 |
| ----- | ----- |
| **장점** | • 완전한 제어 및 커스터마이징 가능 • 첨부파일(attachment) 처리 유연 • Slash Command 직접 처리 가능 • 외부 의존성 없이 안정적 운영 |
| **단점** | • 별도 Node.js 서버 필요 • PM2 등으로 프로세스 관리 필요 |
| **필요 패키지** | discord.js v14, axios, dotenv |
| **실행 방법** | PM2 (Process Manager 2)로 상시 실행 |

**Bridge Bot 핵심 코드 구조:**

// bridge-bot.js \- Discord → n8n Webhook Bridge  
const { Client, GatewayIntentBits } \= require('discord.js');  
const axios \= require('axios');  
require('dotenv').config();

const client \= new Client({  
  intents: \[  
    GatewayIntentBits.Guilds,  
    GatewayIntentBits.GuildMessages,  
    GatewayIntentBits.MessageContent  
  \]  
});

client.on('messageCreate', async (message) \=\> {  
  if (message.author.bot) return; // 봇 메시지 무시  
  if (message.channelId \!== process.env.WORK\_CHANNEL\_ID) return;

  const payload \= {  
    messageId: message.id,  
    content: message.content,  
    authorId: message.author.id,  
    authorName: message.author.username,  
    channelId: message.channelId,  
    timestamp: message.createdTimestamp,  
    attachments: message.attachments.map(a \=\> ({  
      url: a.url,  
      name: a.name,  
      contentType: a.contentType,  
      size: a.size  
    }))  
  };

  try {  
    const response \= await axios.post(  
      process.env.N8N\_WEBHOOK\_URL,  
      payload,  
      { timeout: 30000 }  
    );

    // n8n에서 반환된 결과를 Discord 채널에 발송  
    if (response.data?.reply) {  
      await message.reply(response.data.reply);  
    }  
  } catch (error) {  
    console.error('n8n webhook error:', error.message);  
    await message.reply('❌ 처리 중 오류가 발생했습니다.');  
  }  
});

client.login(process.env.DISCORD\_BOT\_TOKEN);

 

## **6.2 방법 B: n8n Community Node (간편)**

n8n에 Discord Trigger 커뮤니티 노드를 설치하여 Bridge Bot 없이 직접 연동하는 방식.

| 항목 | 상세 |
| ----- | ----- |
| **패키지명** | n8n-nodes-discord-trigger-new (v0.10.11) |
| **설치 방법** | n8n Settings → Community Nodes → 패키지명 검색 후 Install |
| **장점** | • Bridge Bot 별도 구축 불필요 • n8n UI에서 직접 설정 • 2025년 n8n 버전과 호환 확인됨 |
| **단점** | • 커뮤니티 유지보수 의존성 • 업데이트 지연 가능성 • 첨부파일 처리 제한 가능성 |
| **필수 설정** | Discord App Client ID Discord Bot Token Message Content Intent 활성화 |

⚠ **권장사항: 안정성과 첨부파일(QR 사진) 처리의 유연성을 위해 방법 A(Bridge Bot)를 권장함. 방법 B는 신속한 프로토타입 구축 시 활용 가능.**

# **7\. n8n 워크플로우 설계 (Workflow Design)**

## **7.1 워크플로우 목록 (Workflow List)**

| No | 워크플로우명 | 기능 | 트리거 | 빈도 |
| :---: | ----- | ----- | ----- | ----- |
| 1 | **Main Message Router** | 메시지 수신 → AI 분류 → 업무 분기 | Webhook Trigger | 실시간 |
| 2 | **Asset Registration** | 물품 신규등록 처리 | Sub-workflow | 요청시 |
| 3 | **Asset Update** | 물품 폐기/위치/사용자 변경 | Sub-workflow | 요청시 |
| 4 | **Asset Inquiry** | 물품 조회 및 결과 반환 | Sub-workflow | 요청시 |
| 5 | **Restaurant Balance** | 음식점 잔고 업데이트 | Sub-workflow | 요청시 |
| 6 | **Conflict Detector** | Google Sheets 변경 감지 | Schedule (5분) | 주기적 |
| 7 | **Admin Commands** | 관리자 Slash Command 처리 | Webhook | 요청시 |
| 8 | **Error Handler** | 오류 처리 및 알림 | Error Trigger | 오류시 |

## **7.2 메인 라우터 워크플로우 (Main Router Detail)**

\[Webhook Trigger\] (POST from Bridge Bot)  
       │  
       │ JSON: { content, authorId, authorName, attachments\[\] }  
       ▼  
\[IF: attachments.length \> 0 ?\]  
       ├─ Yes ──\> \[HTTP Request: QR Decode API\]  
       │                      │  
       │ No                   ▼  
       └───────\> \[Merge: text \+ QR data\]  
                              │  
                              ▼  
              \[AI Agent / HTTP Request to OpenAI/Claude\]  
                System Prompt: 업무 분류 지침  
                Input: 메시지 \+ QR 데이터  
                Output: JSON { task\_type, confidence, params }  
                              │  
                              ▼  
              \[IF: confidence \>= 0.8 ?\]  
                ├─ Yes ─\> \[Switch: task\_type\]  
                │          ├─ asset\_register   → Sub-WF  
                │          ├─ asset\_dispose    → Sub-WF  
                │          ├─ asset\_location   → Sub-WF  
                │          ├─ asset\_user       → Sub-WF  
                │          ├─ asset\_inquiry    → Sub-WF  
                │          ├─ restaurant       → Sub-WF  
                │          └─ unknown          → "이해불가"  
                └─ No ──\> \[Respond: 확인요청 메시지\]

\[Respond to Webhook\] → Bridge Bot이 Discord에 응답 발송

## **7.3 Webhook ↔ Discord 응답 처리 (Response Flow)**

n8n Webhook의 'Respond to Webhook' 노드를 사용하여 Bridge Bot에게 응답을 반환하면, Bridge Bot이 Discord 채널에 메시지를 발송함.

응답 JSON 형식:

{  
  "reply": "✅ VR헤드셋 Meta Quest 3 등록 완료\!",  
  "adminNotify": "새 물품 등록: Meta Quest 3 / @홍길동",  
  "success": true  
}  
Bridge Bot은 reply를 채널에 발송하고, adminNotify가 있으면 관리자 DM으로 발송.

# **8\. AI 메시지 분류 설계 (AI Message Classification)**

시스템의 핵심은 AI가 자연어 메시지를 분석하여 어떤 업무를 수행해야 하는지 정확하게 분류하는 것임.

## **8.1 AI System Prompt**

You are a message classifier for a team asset management system.  
Analyze the user message and classify it into one of these task types.

TASK TYPES:  
\- asset\_register: New asset registration  
    (keywords: 등록, 신규, register, new)  
\- asset\_dispose: Asset disposal  
    (keywords: 폐기, 버림, dispose, discard)  
\- asset\_location: Location update  
    (keywords: 위치, 이동, 옮김, location, move)  
\- asset\_user: User assignment  
    (keywords: 사용자, 배정, 담당, assign, user)  
\- asset\_inquiry: Asset inquiry  
    (keywords: 확인, 조회, 상태, check, inquiry, status)  
\- restaurant\_balance: Restaurant balance  
    (keywords: 잔고, 식당, 음식점, 만원, 원, balance)  
\- unknown: Cannot determine intent

RESPOND IN JSON FORMAT ONLY:  
{  
  "task\_type": "asset\_register",  
  "confidence": 0.95,  
  "params": {  
    "asset\_name": "Meta Quest 3",  
    "category": "VR헤드셋",  
    "location": "3층 회의실A",  
    "user": "홍길동",  
    "qr\_data": "AST-001",  
    "restaurant\_name": null,  
    "amount": null,  
    "reason": null  
  }  
}

## **8.2 분류 신뢰도 처리 (Confidence Handling)**

| 신뢰도 범위 | 처리 방법 | 예시 |
| ----- | ----- | ----- |
| **0.8 이상** | 자동 처리 후 결과 알림 | "등록 VR헤드셋 Quest3 3층" → 자동 등록 |
| **0.5 \~ 0.8** | 사용자에게 확인 요청 후 처리 | "퀸스트 가져와" → "물품 조회가 맞나요?" |
| **0.5 미만** | 이해 불가 \+ 가이드 안내 | "오늘 날씨 좋다" → "업무를 파악할 수 없습니다" |

# **9\. 관리자 기능 (Admin Features)**

관리자는 시스템의 기능을 언제든지 추가하거나 수정할 수 있는 구조여야 함.

## **9.1 관리자 인증 (Admin Authentication)**

Discord User ID를 기반으로 관리자를 식별함. Config 시트의 ADMIN\_DISCORD\_IDS 필드에 등록된 ID만 관리자 명령어 사용 가능.

단일 채널 구조이므로, 관리자 전용 알림(시스템 오류, 충돌 감지 등)은 Discord DM(Direct Message)으로 발송됨. Bridge Bot이 관리자 Discord User ID로 직접 DM을 발송하는 방식.

## **9.2 기능 확장성 (Extensibility)**

관리자가 새로운 업무 유형을 추가하려면:

1\. n8n 에디터에서 새로운 Sub-workflow 생성

2\. Main Router의 Switch 노드에 새 분기 추가

3\. AI 시스템 프롬프트에 새 task\_type 추가

4\. Google Sheets에 필요한 시트/컬럼 추가

이 모든 과정은 코드 수정 없이 n8n UI에서 직관적으로 가능함.

# **10\. 오류 처리 및 로깅 (Error Handling & Logging)**

| 오류 유형 | 처리 방법 | 알림 대상 |
| ----- | ----- | ----- |
| **QR 인식 실패** | 사용자에게 재촬영 요청 메시지 발송 | 채널 응답 |
| **AI 분류 실패** | unknown으로 처리, 사용 가이드 안내 | 채널 응답 |
| **Google Sheets API 오류** | 재시도 3회 후 실패시 관리자 알림 | 관리자 DM |
| **중복 등록 시도** | 이미 등록된 물품임을 알림 | 채널 응답 |
| **Discord API 오류** | 재시도 \+ SystemLog에 기록 | 관리자 DM |
| **Bridge Bot 연결 끊김** | PM2 자동 재시작 \+ 관리자 알림 | 관리자 DM |
| **n8n 워크플로우 오류** | Error Trigger로 포착, 관리자 알림 | 관리자 DM |

# **11\. 테스트 체크리스트 (Testing Checklist)**

| No | 테스트 항목 | 예상 결과 | 상태 | 비고 |
| :---: | ----- | ----- | :---: | ----- |
| 1 | Bridge Bot 실행 및 Discord 연결 | Bot이 온라인 상태로 표시됨 | □ |  |
| 2 | \#업무-처리 채널에 텍스트 입력 | n8n Webhook이 호출되고 AI 분류 실행됨 | □ |  |
| 3 | QR코드 사진 \+ 등록 메시지 | Google Sheets에 새 물품 등록됨 | □ |  |
| 4 | QR코드 사진 \+ 폐기 메시지 | 물품 상태가 '폐기'로 변경됨 | □ |  |
| 5 | QR코드 사진 \+ 위치 변경 메시지 | 위치 컬럼이 업데이트됨 | □ |  |
| 6 | 음식점 잔고 메시지 전송 | 해당 식당 잔고가 업데이트됨 | □ |  |
| 7 | Google Sheets 수동 수정 | 충돌 감지 알림 발송됨 | □ |  |
| 8 | /help 명령어 실행 | 사용 가이드가 표시됨 | □ |  |
| 9 | 관리자 명령어 (비관리자) | 권한 없음 메시지 표시 | □ |  |
| 10 | 알 수 없는 메시지 전송 | 이해 불가 응답 \+ 가이드 안내 | □ |  |
| 11 | Bridge Bot 재시작 후 정상 작동 | 메시지 수신 및 처리 정상 동작 | □ |  |

# **12\. Claude Code 프롬프트 \- 국문 (Korean Prompt)**

⚠ **아래 프롬프트를 Claude Code에 그대로 붙여넣어 사용할 것**

 

\#\# 프로젝트 개요

너는 n8n 워크플로우 자동화 전문 개발자야.  
Discord 봇을 통해 10명 내부 팀의 물품 관리와 음식점 잔고 관리를  
자동화하는 n8n 워크플로우 시스템을 구축해야 함.

\#\# 기술 스택

\- 메신저: Discord Bot API (discord.js v14)  
\- 브릿지 봇: Node.js (discord.js \+ axios) \- Discord ↔ n8n Webhook 연결  
\- 워크플로우: n8n (셋프호스팅 또는 클라우드)  
\- 데이터베이스: Google Sheets API v4  
\- AI: OpenAI GPT-4o 또는 Claude API (메시지 분류용)  
\- QR 인식: Discord 첨부파일(attachment) \+ QR 디코드 API

\#\# ⚠️ 중요: Telegram과의 차이점

n8n에는 Discord 메시지 수신 Trigger가 내장되어 있지 않음.  
따라서 Discord.js 기반의 Bridge Bot을 반드시 구축해야 함.  
Bridge Bot은 Discord의 messageCreate 이벤트를 감지하여  
n8n Webhook URL로 HTTP POST 요청을 보냄.

\#\# 구현 순서

\#\#\# 1단계: Discord Bot 및 Bridge Bot 구축

1-1. Discord Developer Portal에서 Application 및 Bot 생성  
  \- Application 이름: TeamAssetBot  
  \- Bot 생성 후 Token 발급  
  \- Privileged Gateway Intents:  
    \* MESSAGE CONTENT INTENT: 활성화 (필수)  
    \* SERVER MEMBERS INTENT: 활성화 (권장)  
  \- OAuth2 URL 생성:  
    \* Scopes: bot, applications.commands  
    \* Permissions: Read Messages, Send Messages,  
      Attach Files, Read Message History,  
      Use Slash Commands

1-2. Bridge Bot 코드 작성 (bridge-bot.js)  
  \- discord.js v14, axios, dotenv 설치  
  \- messageCreate 이벤트 감지  
  \- 지정된 채널(WORK\_CHANNEL\_ID)의 메시지만 처리  
  \- 봇 메시지는 무시 (message.author.bot \=== true)  
  \- 첨부파일(attachment) URL 추출 포함  
  \- n8n Webhook으로 POST 전송 payload:  
    { content, authorId, authorName, channelId,  
      timestamp, attachments: \[{ url, name, contentType }\] }  
  \- n8n의 응답(response.data.reply)을 동일 채널에 발송  
  \- 관리자 알림이 있으면 관리자 DM으로 발송

1-3. PM2로 Bridge Bot 상시 실행 설정  
  \- npm install \-g pm2  
  \- pm2 start bridge-bot.js \--name discord-bridge  
  \- pm2 startup && pm2 save

1-4. Discord 서버 채널 구성 (단일 채널)  
  \- \#업무: 모든 사용자 입력 \+ 봇 응답 \+ 시스템 알림  
  \- 관리자 전용 알림은 DM으로 발송

\#\#\# 2단계: n8n 워크플로우 구축

2-1. 메인 라우터 워크플로우 (Main Message Router)  
  \- Webhook Trigger 노드 (POST, JSON Body)  
  \- IF 노드: attachments.length \> 0 확인  
  \- HTTP Request 노드: QR 디코드 API 호출  
    (첨부파일 URL을 QR 디코드 서비스에 전송)  
  \- Merge 노드: 텍스트 \+ QR 데이터 합침  
  \- HTTP Request 노드: OpenAI/Claude API 호출  
    \* System Prompt: 업무 분류 지침  
    \* User Message: 사용자 메시지 \+ QR 데이터  
    \* 응답 형식: JSON { task\_type, confidence, params }  
  \- JSON Parse 노드: AI 응답 파싱  
  \- IF 노드: confidence \>= 0.8 확인  
    \* 미만시: 확인 요청 메시지 반환  
  \- Switch 노드: task\_type에 따른 분기  
    \* asset\_register → Sub-WF: Asset Registration  
    \* asset\_dispose / asset\_location / asset\_user  
      → Sub-WF: Asset Update (type 파라미터)  
    \* asset\_inquiry → Sub-WF: Asset Inquiry  
    \* restaurant\_balance → Sub-WF: Restaurant Balance  
    \* unknown → 이해 불가 응답 반환  
  \- Respond to Webhook 노드: Bridge Bot에게 JSON 반환  
    { reply: "처리결과", adminNotify: "관리자알림", success: true }

2-2. Sub-workflow: Asset Registration (물품 등록)  
  \- Google Sheets 노드: AssetList에서 기존 물품 ID 검색  
    \* 중복시 중복 알림 반환  
  \- Google Sheets 노드: AssetList에 새 행 추가  
    \* 컬럼: 물품ID, 물품명, 카테고리, 상태('사용중'),  
      현재위치, 현재사용자, 등록일, 수정출처('시스템')  
  \- Google Sheets 노드: AssetHistory에 등록 이력 추가  
  \- 결과 반환: 등록 완료 메시지

2-3. Sub-workflow: Asset Update (물품 수정)  
  \- 입력: type (dispose/location/user), params  
  \- Google Sheets: 물품ID로 AssetList에서 해당 행 검색  
  \- type에 따라 해당 컬럼 업데이트  
  \- AssetHistory에 변경 이력 추가  
  \- 결과 반환: 변경 완료 메시지

2-4. Sub-workflow: Asset Inquiry (물품 조회)  
  \- Google Sheets: 물품ID 또는 물품명으로 AssetList 검색  
  \- Google Sheets: AssetHistory에서 최근 3건 이력 검색  
  \- 결과 반환: 물품 정보 \+ 최근 이력

2-5. Sub-workflow: Restaurant Balance (음식점 잔고)  
  \- Google Sheets: 식당명으로 RestaurantBalance 검색  
  \- 기존 잔고 저장 → 새 잔고로 업데이트  
  \- 식당이 없으면 확인 요청 또는 새로 추가  
  \- 결과 반환: 잔고 변경 알림

2-6. Conflict Detector (충돌 감지)  
  \- Schedule Trigger: 5분마다 실행  
  \- Google Sheets: 모든 시트 데이터 읽기  
  \- 이전 스냅샷과 비교 (내부 변수 또는 별도 시트 활용)  
  \- '수정출처' 컬럼이 '시스템'이 아닌 변경 감지시  
  \- Discord Action 노드: \#업무 채널에 알림 \+ 관리자 DM 발송

\#\#\# 3단계: Google Sheets 설정

3-1. Google Sheets 파일 생성  
  \- 시트 5개 생성:  
    AssetList, AssetHistory, RestaurantBalance,  
    SystemLog, Config  
  \- 각 시트의 헤더(컬럼명) 설정

3-2. Google Cloud Console에서 Service Account 생성  
  \- Google Sheets API v4 활성화  
  \- Service Account 키(JSON) 발급  
  \- 해당 Sheets에 Service Account 이메일 공유 권한 부여

3-3. n8n에 Google Sheets Credential 등록  
  \- Service Account JSON 키 입력

\#\#\# 4단계: 테스트 및 배포

4-1. 단위 테스트  
  \- Bridge Bot 실행 후 Discord 메시지 → n8n Webhook 전달 확인  
  \- QR 코드 사진 첨부 → QR 데이터 추출 확인  
  \- AI 분류 결과 확인 (confidence, task\_type)  
  \- Google Sheets 읽기/쓰기 확인

4-2. 통합 테스트  
  \- 물품 등록 → 조회 → 위치변경 → 폐기 전체 흐름  
  \- 음식점 잔고 업데이트 흐름  
  \- 충돌 감지 흐름  
  \- 오류 시나리오 테스트

# **13\. Claude Code 프롬프트 \- 영문 (English Prompt)**

⚠ **Paste the prompt below directly into Claude Code**

 

# **14\. 구현 단계 로드맵 (Implementation Roadmap)**

| 단계 | 작업 항목 | 세부 내용 | 예상 소요 | 선행조건 |
| :---: | ----- | ----- | :---: | ----- |
| **1** | **Discord Bot 생성** | Developer Portal에서 App/Bot 생성 및 설정 | 30분 | 없음 |
| **2** | **Bridge Bot 개발** | discord.js \+ axios 브릿지 봇 코드 작성 | 2시간 | 1단계 |
| **3** | **Discord 서버 구성** | 채널 생성, Role 설정, 봇 초대 | 30분 | 1단계 |
| **4** | **Google Sheets 설정** | 시트 생성, Service Account, n8n 연동 | 1시간 | 없음 |
| **5** | **n8n Main Router** | Webhook \+ AI분류 \+ Switch 워크플로우 | 3시간 | 2,4단계 |
| **6** | **물품 관리 WF** | 등록/폐기/위치/사용자/조회 Sub-WF | 3시간 | 5단계 |
| **7** | **음식점 잔고 WF** | 음식점 잔고 업데이트 Sub-WF | 1시간 | 5단계 |
| **8** | **충돌 감지 WF** | Schedule Trigger \+ 변경 감지 \+ 알림 | 2시간 | 4단계 |
| **9** | **오류 처리** | Error Handler WF \+ Bridge Bot 오류 처리 | 1시간 | 5단계 |
| **10** | **테스트 및 배포** | 통합 테스트 \+ 사용자 가이드 작성 | 2시간 | 전체 |

**총 예상 소요 시간: 약 16시간 (2일 기준)**

 

**\--- 문서 끝 (End of Document) \---**