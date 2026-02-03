"""
HWP Document Service for n8n
pyhwpx를 사용한 한글 문서 자동화 API 서버

요구사항:
- Windows OS
- 한글 프로그램 설치 (한컴오피스)
- Python 3.8+

설치:
pip install fastapi uvicorn pyhwpx python-multipart
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import os
import tempfile
import shutil
from datetime import datetime
import json
import asyncio
from pathlib import Path

# pyhwpx import (Windows + 한글 설치 필요)
try:
    from pyhwpx import Hwp
    HWP_AVAILABLE = True
except ImportError:
    HWP_AVAILABLE = False
    print("⚠️ pyhwpx not available. Install with: pip install pyhwpx")

app = FastAPI(
    title="HWP Document Service",
    description="한글(HWP) 문서 자동화 API for n8n",
    version="1.0.0"
)

# 임시 파일 저장 경로
TEMP_DIR = Path(tempfile.gettempdir()) / "hwp_service"
TEMP_DIR.mkdir(exist_ok=True)

# 템플릿 저장 경로
TEMPLATE_DIR = Path("W:/1_DXP_Projects/14_Automation/n8n/02_IRB")


class DocumentRequest(BaseModel):
    """문서 생성 요청"""
    template_path: str
    fields: Dict[str, Any]
    output_filename: Optional[str] = None


class FieldMapping(BaseModel):
    """필드 매핑 정보"""
    field_name: str
    hwp_field_name: str  # 한글 누름틀 필드명
    value: str


class IRBDocumentRequest(BaseModel):
    """IRB 문서 생성 요청"""
    document_type: str  # 서식 종류 (연구계획서, 동의서 등)
    research_title: str  # 연구과제명
    researcher_name: str  # 연구자명
    researcher_affiliation: str  # 소속
    research_purpose: str  # 연구 목적
    research_method: str  # 연구 방법
    participant_count: int  # 연구대상자 수
    expected_duration: str  # 예상 소요 시간
    additional_info: Optional[Dict[str, str]] = None


class HWPService:
    """한글 문서 처리 서비스"""

    def __init__(self):
        self.hwp = None

    def _init_hwp(self, visible: bool = False):
        """한글 인스턴스 초기화"""
        if not HWP_AVAILABLE:
            raise HTTPException(
                status_code=500,
                detail="pyhwpx가 설치되지 않았거나 한글 프로그램이 없습니다."
            )
        self.hwp = Hwp(visible=visible)
        return self.hwp

    def _close_hwp(self):
        """한글 인스턴스 종료"""
        if self.hwp:
            try:
                self.hwp.quit()
            except Exception:
                pass
            self.hwp = None

    async def process_template(
        self,
        template_path: str,
        fields: Dict[str, str],
        output_path: str
    ) -> str:
        """
        템플릿 파일을 열고 필드를 채운 후 저장

        Args:
            template_path: 템플릿 파일 경로
            fields: 필드명-값 딕셔너리
            output_path: 출력 파일 경로

        Returns:
            생성된 파일 경로
        """
        try:
            hwp = self._init_hwp(visible=False)

            # 템플릿 열기
            hwp.open(template_path)

            # 필드 채우기 (누름틀 필드 사용)
            for field_name, value in fields.items():
                try:
                    # put_field_text: 누름틀에 텍스트 삽입
                    hwp.put_field_text(field_name, value)
                except Exception as e:
                    print(f"필드 '{field_name}' 처리 실패: {e}")
                    # 대체 방법: 텍스트 찾기/바꾸기
                    self._replace_placeholder(hwp, f"{{{{{field_name}}}}}", value)

            # 저장
            hwp.save_as(output_path)

            return output_path

        finally:
            self._close_hwp()

    def _replace_placeholder(self, hwp, placeholder: str, value: str):
        """텍스트 찾기/바꾸기로 플레이스홀더 대체"""
        try:
            hwp.find_replace(placeholder, value)
        except Exception as e:
            print(f"플레이스홀더 '{placeholder}' 대체 실패: {e}")

    async def fill_irb_document(
        self,
        request: IRBDocumentRequest,
        output_dir: str
    ) -> Dict[str, str]:
        """
        IRB 문서 세트 생성

        Args:
            request: IRB 문서 요청 정보
            output_dir: 출력 디렉토리

        Returns:
            생성된 파일들의 경로 딕셔너리
        """
        # 문서 유형별 템플릿 매핑
        template_mapping = {
            "연구계획서": "[서식02_세부내역]_연구계획서_KUIRB. 202305.hwp",
            "연구참여설명서": "[서식03-1]_연구참여_설명서(인간대상 연구)_KUIRB. 202404.hwpx",
            "동의서": "[서식03-2]_연구참여_동의서_KUIRB. 202404.hwp",
            "개인정보동의서": "[서식20]_개인정보 처리(수집이용제공) 동의서 KUIRB. 202409.hwpx",
            "연구윤리서약서": "[서식14]_연구윤리_준수_서약서_KUIRB. 202305.hwp",
            "이해상충서약서": "[서식31]_이해상충공개서약서(연구자용)_KUIRB. 202305.hwp"
        }

        # 공통 필드 데이터
        common_fields = {
            "연구과제명": request.research_title,
            "연구자": request.researcher_name,
            "소속": request.researcher_affiliation,
            "연구목적": request.research_purpose,
            "연구방법": request.research_method,
            "연구대상자수": str(request.participant_count),
            "소요시간": request.expected_duration,
            "작성일": datetime.now().strftime("%Y년 %m월 %d일")
        }

        if request.additional_info:
            common_fields.update(request.additional_info)

        # 요청된 문서 유형 처리
        generated_files = {}

        if request.document_type == "전체":
            doc_types = template_mapping.keys()
        else:
            doc_types = [request.document_type]

        for doc_type in doc_types:
            if doc_type not in template_mapping:
                continue

            template_name = template_mapping[doc_type]
            template_path = self._find_template(template_name)

            if not template_path:
                print(f"템플릿을 찾을 수 없음: {template_name}")
                continue

            # 출력 파일명 생성
            safe_title = request.research_title[:20].replace("/", "_").replace("\\", "_")
            output_filename = f"{doc_type}_{safe_title}_{datetime.now().strftime('%Y%m%d')}"

            # 확장자 유지
            ext = Path(template_path).suffix
            output_path = os.path.join(output_dir, f"{output_filename}{ext}")

            try:
                await self.process_template(template_path, common_fields, output_path)
                generated_files[doc_type] = output_path
            except Exception as e:
                print(f"{doc_type} 생성 실패: {e}")

        return generated_files

    def _find_template(self, template_name: str) -> Optional[str]:
        """템플릿 파일 찾기"""
        # 여러 위치에서 템플릿 검색
        search_paths = [
            TEMPLATE_DIR / "김민채 IRB" / template_name,
            TEMPLATE_DIR / "김민채 IRB" / "서식작성 가이드" / f"서식작성 가이드 {template_name}",
            TEMPLATE_DIR / "연구실 IRB (참고용)" / template_name
        ]

        for path in search_paths:
            if path.exists():
                return str(path)

        # 와일드카드 검색
        for folder in TEMPLATE_DIR.rglob("*"):
            if folder.is_file() and template_name in folder.name:
                return str(folder)

        return None

    async def extract_fields(self, file_path: str) -> List[str]:
        """문서에서 누름틀 필드명 추출"""
        try:
            hwp = self._init_hwp(visible=False)
            hwp.open(file_path)

            # 필드 목록 가져오기
            fields = hwp.get_field_list()
            return fields if fields else []

        finally:
            self._close_hwp()


# 서비스 인스턴스
hwp_service = HWPService()


@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "HWP Document Service",
        "status": "running",
        "hwp_available": HWP_AVAILABLE,
        "template_dir": str(TEMPLATE_DIR)
    }


@app.get("/templates")
async def list_templates():
    """사용 가능한 템플릿 목록"""
    templates = []
    for ext in ["*.hwp", "*.hwpx"]:
        for file in TEMPLATE_DIR.rglob(ext):
            templates.append({
                "name": file.name,
                "path": str(file),
                "size": file.stat().st_size,
                "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
    return {"templates": templates, "count": len(templates)}


@app.post("/process")
async def process_document(request: DocumentRequest):
    """
    템플릿 기반 문서 생성

    - template_path: 템플릿 파일 경로
    - fields: 필드명-값 딕셔너리
    - output_filename: 출력 파일명 (선택)
    """
    if not HWP_AVAILABLE:
        raise HTTPException(status_code=500, detail="HWP service not available")

    # 출력 경로 설정
    if request.output_filename:
        output_path = TEMP_DIR / request.output_filename
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = Path(request.template_path).suffix
        output_path = TEMP_DIR / f"document_{timestamp}{ext}"

    try:
        result_path = await hwp_service.process_template(
            request.template_path,
            request.fields,
            str(output_path)
        )

        return {
            "success": True,
            "file_path": result_path,
            "download_url": f"/download/{output_path.name}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/irb/generate")
async def generate_irb_documents(request: IRBDocumentRequest):
    """
    IRB 문서 세트 자동 생성

    document_type 옵션:
    - 연구계획서
    - 연구참여설명서
    - 동의서
    - 개인정보동의서
    - 연구윤리서약서
    - 이해상충서약서
    - 전체 (모든 문서 생성)
    """
    if not HWP_AVAILABLE:
        raise HTTPException(status_code=500, detail="HWP service not available")

    # 출력 디렉토리 생성
    output_dir = TEMP_DIR / f"irb_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(exist_ok=True)

    try:
        generated_files = await hwp_service.fill_irb_document(request, str(output_dir))

        return {
            "success": True,
            "generated_files": {
                doc_type: {
                    "path": path,
                    "download_url": f"/download/{Path(path).name}"
                }
                for doc_type, path in generated_files.items()
            },
            "output_directory": str(output_dir)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """생성된 파일 다운로드"""
    file_path = TEMP_DIR / filename

    # 하위 디렉토리에서도 검색
    if not file_path.exists():
        for f in TEMP_DIR.rglob(filename):
            file_path = f
            break

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )


@app.post("/extract-fields")
async def extract_fields(file: UploadFile = File(...)):
    """문서에서 필드(누름틀) 목록 추출"""
    if not HWP_AVAILABLE:
        raise HTTPException(status_code=500, detail="HWP service not available")

    # 임시 파일로 저장
    temp_path = TEMP_DIR / file.filename
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        fields = await hwp_service.extract_fields(str(temp_path))
        return {"fields": fields, "count": len(fields)}
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.delete("/cleanup")
async def cleanup_temp_files():
    """임시 파일 정리"""
    count = 0
    for item in TEMP_DIR.iterdir():
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
            count += 1
        except Exception:
            pass

    return {"cleaned": count}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting HWP Document Service...")
    print(f"📁 Template directory: {TEMPLATE_DIR}")
    print(f"📂 Temp directory: {TEMP_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8765)
