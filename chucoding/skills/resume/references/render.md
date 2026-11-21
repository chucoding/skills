# PDF 제작과 검증

원본 HTML을 고치고 headless Chrome으로 PDF를 다시 뽑는다. PDF를 직접 고치지 않는다.

## 1. 원본 구조

- `resume.html`, `portfolio.html`, `common.css` 세 파일이다. 글꼴은 Pretendard(지원 회사 글꼴로 바꿨으면 그 글꼴, SKILL.md 1절), 쪽은 A4다.
- 쪽마다 `.page { height: 297mm; overflow: hidden; }`이다. **넘친 내용은 쪽이 늘지 않고 조용히 잘린다.** 그래서 고칠 때마다 마지막 줄 위치를 확인한다.
- 링크는 `<a href>`로 넣어야 PDF에 링크로 남는다.

## 2. 고치는 순서

1. 고칠 HTML과 바탕화면의 현재 PDF를 스크래치패드 `backup/`에 시각을 붙여 복사한다. 4절에서 쪽수와 링크 수를 "이전과 같음"으로 비교하는 기준이 이 PDF 백업이다. 바탕화면에 PDF가 아직 없는 첫 제작이면 PDF 백업과 이전 비교를 건너뛴다.
2. 문장은 Python으로 바꾼다. 바꿀 문자열이 정확히 한 번 나오는지 먼저 확인한다.

   ```python
   s = open(p, encoding='utf-8').read()
   assert s.count(a) == 1, (a, s.count(a))
   s = s.replace(a, b)
   open(p, 'w', encoding='utf-8').write(s)
   ```

3. 줄 수가 바뀔 수 있는 변경은 먼저 스크래치패드 `trial/`의 사본에 적용해 렌더하고, 줄 수와 여백을 사용자에게 보여 준 뒤 원본에 반영한다.

## 3. 렌더

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-pdf-header-footer \
  --user-data-dir=<스크래치패드>/chrome-profile \
  --print-to-pdf=<스크래치패드>/render/<이름>.pdf \
  "file://<원본 폴더>/resume.html"
```

- `--user-data-dir`을 따로 주어 사용자의 Chrome 프로필과 섞이지 않게 한다.
- 결과를 바로 바탕화면에 쓰지 않는다. 스크래치패드에 뽑아 검증한 뒤 복사한다.

## 4. 검증

PyMuPDF가 필요하면 스크래치패드에 venv를 만들어 설치하고 `-I`로 실행한다. 확인할 것은 아래와 같다.

| 항목 | 기준 |
|------|------|
| 쪽수 | 이력서와 포트폴리오 모두 이전과 같음 |
| 잘림 | 각 쪽 마지막 본문 줄의 아래 끝이 쪽 번호(footer) 줄 위에 있고(gap이 0보다 큼), `footer 못 찾음`과 `footer 줄에 본문 겹침` 출력이 없음. 여백을 pt로 보고 |
| 줄 수 | 고친 문단이 시안에서 보여 준 줄 수와 같음 |
| 링크 | 쪽별 링크 수가 이전과 같음 |
| 숨은 텍스트 | 지운 문장이나 옛 내용이 텍스트 레이어에 0건 |
| 이전 회사 흔적 | 다른 회사 원본으로 시작했으면 이전 지원 회사 이름이 HTML과 텍스트 레이어에 0건(재직 이력 자리는 제외), 이전 브랜드에서 온 색(hex, `rgb()`, `hsl()`)이 HTML과 CSS에 0건(SKILL.md 1절) |
| 글꼴 | 지원 회사 글꼴로 바꿨으면 `page.get_fonts()`의 글꼴 이름이 그 글꼴과 같음 |

```python
import fitz, sys
doc = fitz.open(sys.argv[1])
FOOT_LABEL = sys.argv[2]   # .foot 왼쪽 문서 이름
print('pages', doc.page_count)
for i, page in enumerate(doc):
    H = page.rect.height
    lines = [(l['bbox'][1], l['bbox'][3], ''.join(s['text'] for s in l['spans']).strip())
             for b in page.get_text('dict')['blocks'] for l in b.get('lines', [])]
    lines = [l for l in lines if l[2]]
    # footer는 위치가 아니라 쪽 번호 줄로 찾는다
    num = [l for l in lines if l[2] == str(i + 1) and l[0] > H - 60]
    if not num:
        print(i + 1, 'footer 못 찾음 — 쪽 번호 형식이나 위치를 확인하고 이미지로 직접 본다')
        continue
    foot_top = min(l[0] for l in num)
    # footer 줄은 쪽 번호와 문서 이름(FOOT_LABEL)뿐. 같은 높이에 그 밖의 글이 있으면 본문이 겹친 것
    foot_row = [l for l in lines if abs(l[0] - foot_top) < 2]
    extra = [l for l in foot_row if l[2] not in (str(i + 1), FOOT_LABEL)]
    body = [l for l in lines if l not in foot_row or l in extra]
    last = max(body, key=lambda l: l[1]) if body else (0, 0, '')
    print(i + 1, 'gap', round(foot_top - last[1], 1), 'links', len(page.get_links()), '|', last[2][:20],
          '| footer 줄에 본문 겹침: ' + ', '.join(l[2][:20] for l in extra) if extra else '')
```

- 위 코드를 스크래치패드 `check.py`로 저장해 `<venv>/bin/python -I check.py <pdf> '<.foot 왼쪽 문구>'`로 실행한다. 문구는 원본 HTML의 `<div class="foot"><span>…</span>`에서 그대로 읽고, 이력서와 포트폴리오처럼 문서가 다르면 문서마다 그 문서의 문구를 넘긴다. 문구가 틀리면 정상 footer도 `footer 줄에 본문 겹침`으로 나온다.
- `FOOT_LABEL`은 `.foot` 왼쪽의 문서 이름(예: `'서현석 이력서'`)이다. 원본 HTML의 `.foot`는 왼쪽에 문서 이름, 오른쪽에 쪽 번호 숫자만 두고 쪽 아래 9mm에 놓이므로, 쪽 번호 줄은 쪽 아래 60pt 안에 있다. 이 구조를 바꿨으면 위 조건도 함께 고친다.
- 위치(쪽 아래 40pt)로 footer를 가르면, 넘친 본문 줄이 footer 영역으로 분류돼 gap이 양수로 나온다. 2026-11-21 컬리 이력서 시험본에서 2쪽 마지막 줄이 쪽 번호와 27pt 겹쳤는데 이 방식은 8pt 여유로 보고했다. 그래서 줄 단위로 읽고 쪽 번호 줄로 footer를 찾는다. gap이 0 이하이거나 `footer 못 찾음`, `footer 줄에 본문 겹침`이 나오면 통과가 아니다.

- 지운 문장은 `page.get_text()`에서 검색해 0건인지 본다. PDF를 직접 고쳤던 파일은 화면에 안 보이는 옛 내용이 텍스트 레이어에 남아, 채용 시스템의 텍스트 추출과 본문을 복사하는 리뷰어에게 그대로 읽힌다.
- 의존성 없이 확인하려면 macOS PDFKit을 쓴다.

  ```swift
  import PDFKit
  let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1]))!
  for i in 0..<doc.pageCount { print("=== PAGE \(i+1)"); print(doc.page(at: i)?.string ?? "") }
  ```

- 문장마다 글꼴이나 색이 다르게 찍히지 않았는지 렌더한 쪽을 이미지로 한 번 본다. 굵게 표시한 범위와 색 강조가 문장마다 들쭉날쭉하면 사용자가 지적한다.

## 5. 바탕화면 교체

- 덮어쓰기 전에 2절 1번의 PDF 백업이 있는지 확인한다. 첫 제작이라 바탕화면에 PDF가 없으면 그대로 복사한다. 바탕화면에 PDF가 있는데 백업이 없으면 덮어쓰지 않고, 그 PDF를 백업한 뒤 4절의 이전 비교를 다시 하고 나서 덮어쓴다.
- 검증을 통과하면 바탕화면의 같은 이름 PDF를 덮어쓴다. 버전 접미사 사본을 새로 만들지 않는다.
- 시험 파일과 바탕화면에 남은 다른 버전은 스크래치패드 `backup/`으로 옮긴다. 바탕화면 파일을 지우거나 옮길 때는 무엇을 옮기는지 먼저 말한다.
