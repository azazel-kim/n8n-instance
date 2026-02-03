/**
 * HWPX Template Processor for n8n
 *
 * HWPX는 ZIP 압축된 XML 기반 포맷입니다.
 * 이 모듈은 HWPX 템플릿의 플레이스홀더를 AI 생성 콘텐츠로 대체합니다.
 *
 * 사용법:
 * 1. HWPX 템플릿에 {{필드명}} 형식의 플레이스홀더 삽입
 * 2. 이 프로세서로 플레이스홀더를 실제 콘텐츠로 대체
 */

const JSZip = require('jszip');
const { parseStringPromise, Builder } = require('xml2js');

/**
 * HWPX 템플릿을 처리하여 플레이스홀더를 대체
 * @param {Buffer} templateBuffer - HWPX 템플릿 파일 버퍼
 * @param {Object} fieldData - 대체할 필드 데이터 { fieldName: value }
 * @returns {Promise<Buffer>} - 처리된 HWPX 파일 버퍼
 */
async function processHwpxTemplate(templateBuffer, fieldData) {
  // HWPX 파일 압축 해제
  const zip = await JSZip.loadAsync(templateBuffer);

  // Contents 폴더의 section*.xml 파일들 처리
  const contentFiles = Object.keys(zip.files).filter(
    name => name.startsWith('Contents/') && name.endsWith('.xml')
  );

  for (const fileName of contentFiles) {
    const xmlContent = await zip.file(fileName).async('string');
    const processedXml = await processXmlContent(xmlContent, fieldData);
    zip.file(fileName, processedXml);
  }

  // 처리된 HWPX 파일 생성
  return await zip.generateAsync({
    type: 'nodebuffer',
    compression: 'DEFLATE',
    compressionOptions: { level: 9 }
  });
}

/**
 * XML 콘텐츠에서 플레이스홀더 대체
 * @param {string} xmlContent - XML 문자열
 * @param {Object} fieldData - 대체할 필드 데이터
 * @returns {Promise<string>} - 처리된 XML 문자열
 */
async function processXmlContent(xmlContent, fieldData) {
  // 플레이스홀더 패턴: {{필드명}}
  let processed = xmlContent;

  for (const [fieldName, value] of Object.entries(fieldData)) {
    const placeholder = `{{${fieldName}}}`;
    const escapedValue = escapeXml(String(value));
    processed = processed.split(placeholder).join(escapedValue);
  }

  return processed;
}

/**
 * XML 특수문자 이스케이프
 */
function escapeXml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/**
 * HWPX 파일에서 텍스트 추출 (템플릿 분석용)
 * @param {Buffer} hwpxBuffer - HWPX 파일 버퍼
 * @returns {Promise<Object>} - 추출된 정보
 */
async function extractHwpxInfo(hwpxBuffer) {
  const zip = await JSZip.loadAsync(hwpxBuffer);
  const result = {
    sections: [],
    placeholders: [],
    metadata: {}
  };

  // 버전 정보 추출
  if (zip.file('version.xml')) {
    const versionXml = await zip.file('version.xml').async('string');
    result.metadata.version = await parseStringPromise(versionXml);
  }

  // 섹션별 텍스트 추출
  const sectionFiles = Object.keys(zip.files)
    .filter(name => /Contents\/section\d+\.xml/.test(name))
    .sort();

  for (const fileName of sectionFiles) {
    const xmlContent = await zip.file(fileName).async('string');
    const sectionInfo = await extractSectionText(xmlContent);
    result.sections.push(sectionInfo);

    // 플레이스홀더 찾기
    const placeholderMatches = xmlContent.match(/\{\{([^}]+)\}\}/g) || [];
    result.placeholders.push(...placeholderMatches.map(p => p.slice(2, -2)));
  }

  result.placeholders = [...new Set(result.placeholders)]; // 중복 제거

  return result;
}

/**
 * 섹션 XML에서 텍스트 추출
 */
async function extractSectionText(xmlContent) {
  const parsed = await parseStringPromise(xmlContent, { explicitArray: false });
  const texts = [];

  function extractText(obj) {
    if (!obj) return;

    if (typeof obj === 'string') {
      texts.push(obj);
      return;
    }

    if (obj['hp:t']) {
      if (typeof obj['hp:t'] === 'string') {
        texts.push(obj['hp:t']);
      } else if (obj['hp:t']._) {
        texts.push(obj['hp:t']._);
      }
    }

    if (typeof obj === 'object') {
      for (const value of Object.values(obj)) {
        if (Array.isArray(value)) {
          value.forEach(extractText);
        } else {
          extractText(value);
        }
      }
    }
  }

  extractText(parsed);

  return {
    text: texts.join(' '),
    paragraphCount: (xmlContent.match(/<hp:p/g) || []).length
  };
}

/**
 * 마크다운을 HWPX XML 구조로 변환
 * @param {string} markdown - 마크다운 텍스트
 * @returns {string} - HWPX 호환 XML 단락들
 */
function markdownToHwpxParagraphs(markdown) {
  const lines = markdown.split('\n');
  const paragraphs = [];

  for (const line of lines) {
    if (!line.trim()) continue;

    let text = line;
    let style = 'Normal';

    // 헤더 처리
    if (line.startsWith('## ')) {
      text = line.slice(3);
      style = 'Heading2';
    } else if (line.startsWith('### ')) {
      text = line.slice(4);
      style = 'Heading3';
    } else if (line.startsWith('# ')) {
      text = line.slice(2);
      style = 'Heading1';
    }

    // 볼드/이탤릭 제거 (HWPX에서는 별도 처리 필요)
    text = text.replace(/\*\*(.+?)\*\*/g, '$1');
    text = text.replace(/\*(.+?)\*/g, '$1');

    paragraphs.push({
      text: escapeXml(text),
      style
    });
  }

  return paragraphs;
}

/**
 * n8n Code 노드에서 사용할 메인 함수
 * @param {Object} input - n8n 입력 데이터
 * @returns {Object} - 처리 결과
 */
async function processInN8n(input) {
  const { templateBase64, fieldData, outputFileName } = input;

  // Base64 템플릿을 버퍼로 변환
  const templateBuffer = Buffer.from(templateBase64, 'base64');

  // 템플릿 처리
  const processedBuffer = await processHwpxTemplate(templateBuffer, fieldData);

  return {
    fileName: outputFileName || 'document.hwpx',
    fileBuffer: processedBuffer.toString('base64'),
    mimeType: 'application/hwpx+zip',
    success: true
  };
}

module.exports = {
  processHwpxTemplate,
  extractHwpxInfo,
  markdownToHwpxParagraphs,
  processInN8n
};
