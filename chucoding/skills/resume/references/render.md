# PDF 제작과 검증

원본 HTML을 고치고 headless Chrome으로 PDF를 다시 뽑는다. PDF를 직접 고치지 않는다.

## 1. 원본 구조

- `resume.html`, `portfolio.html`, `common.css` 세 파일이다. 글꼴은 Pretendard, 쪽은 A4다.
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
| 잘림 | 각 쪽 마지막 텍스트 블록의 아래 끝이 쪽 번호(footer) 위에 있고, 여백을 pt로 보고 |
| 줄 수 | 고친 문단이 시안에서 보여 준 줄 수와 같음 |
| 링크 | 쪽별 링크 수가 이전과 같음 |
| 숨은 텍스트 | 지운 문장이나 옛 내용이 텍스트 레이어에 0건 |

```python
import fitz, sys
doc = fitz.open(sys.argv[1])
print('pages', doc.page_count)
for i, page in enumerate(doc):
    blocks = [b for b in page.get_text('blocks') if b[4].strip()]
    body = [b for b in blocks if b[1] < page.rect.height - 40]
    foot = [b for b in blocks if b[1] >= page.rect.height - 40]
    last = max(b[3] for b in body) if body else 0
    foot_top = min(b[1] for b in foot) if foot else page.rect.height
    print(i + 1, 'gap', round(foot_top - last, 1), 'links', len(page.get_links()))
```

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
