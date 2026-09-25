# Design System

출처: [Tremor UI Kit (Community)](https://www.figma.com/design/rVEzg3je6tdFUuqypyZUjw/Tremor-UI-Kit--Community---Community-?node-id=659-3081)

| 페이지 | 노드 |
|---|---|
| 01 · Foundation / Typography | `659:3081` |
| 02 · Foundation / Colours · Light & Dark | `726:10510` |
| 03 · Foundation / Shadow | `727:11969` (스타일 `tremor-card` · `tremor-dropdown` · `tremor-input`) |
| 21 · Component / Button | `682:3457` (Primary) · `682:3458` (Secondary) |
| 22 · Component / Card | `681:16358` |
| 23 · Component / Text Input | `681:15723` |
| 25 · Component / Select | `201:4141` · `698:3766` |
| 91 · Utility / Divider | `693:4408` |

이 문서에는 위 노드에서 확인된 값만 적었다. Figma에 없는 값을 구현에서 정한 경우는 맨 아래 **구현 결정** 섹션에 따로 적었다.

## 폰트

| 용도 | 폰트 |
|---|---|
| 기본 UI 텍스트 | **Inter** |

## 텍스트 스타일

값은 Figma 노드의 실제 속성 기준이다. 줄 높이가 `Auto`인 스타일은 Figma가 렌더링한 높이를 괄호 안에 적었다. 자간은 모두 `0`이다.

| 스타일 | 크기 | 굵기 | 줄 높이 | 라이트 색상 | 다크 색상 |
|---|---|---|---|---|---|
| `Tremor/Metric` | 30px | 600 (Semi Bold) | Auto (≈36.3px) | `#374151` | `#E5E7EB` |
| `Tremor/Title` | 18px | 500 (Medium) | 28px | `#374151` | `#E5E7EB` |
| `Tremor/Subtitle` | 16px | 500 (Medium) | Auto (≈19.4px) | `#9CA3AF` | `#4B5563` |
| `Tremor/Text` | 14px | 400 (Regular) | 20px | `#6B7280` | `#6B7280` |
| `Tremor/Text-Bold` | 14px | 700 (Bold) | Auto (≈16.9px) | `#6B7280` | `#6B7280` |
| `Tremor/Text-Italic` | 14px | 400, Italic | Auto (≈16.9px) | `#6B7280` | `#6B7280` |
| `Tremor/Label` | 12px | 400 (Regular) | Auto (≈14.5px) | `#6B7280` | `#6B7280` |
| `Tremor/Text-medium` | 14px | 500 (Medium) | 20px | — | — |
| `Tremor/Text-Semibold` | 14px | 600 (Semi Bold) | 20px | — | — |

- `Tremor/Label`은 다크 모드 샘플에서 `Text-chart`라는 이름으로 쓰였다. 차트 라벨에도 이 스타일을 쓴다.
- 모든 텍스트는 왼쪽 정렬이다.
- `Text-medium`은 버튼 라벨에 쓰인다. `Text-medium`·`Text-Semibold`는 Typography 페이지 샘플에 없어 모드별 색상이 정해져 있지 않다 (사용하는 컴포넌트의 색상을 따른다).

### Figma 스타일 설명(Tailwind 클래스)

각 스타일에 적힌 설명이다. 설명과 노드 실제 값이 다른 경우 표에 표시했다.

| 스타일 | Figma 설명 | 노드 실제 값과 차이 |
|---|---|---|
| `Tremor/Metric` | `text-gray-700 text-3xl font-semibold` | 없음 |
| `Tremor/Title` | `text-gray-700 text-lg font-medium` | 없음 |
| `Tremor/Subtitle` | `text-gray-400 text-base font-normal` | 설명은 `font-normal`(400), 노드는 500 |
| `Tremor/Text` | `text-gray-500 text-sm font-normal` | 없음 |
| `Tremor/Text-Bold` | `text-inherit text-sm font-semibold` | 설명은 `font-semibold`(600), 노드는 700 |
| `Tremor/Text-Italic` | `italic text-inherit text-sm` | 없음 |
| `Tremor/Label` | (설명 없음) | — |
| `Tremor/Text-medium` · `Tremor/Text-Semibold` | (설명 없음) | — |

> 설명과 실제 값이 다른 두 스타일(Subtitle, Text-Bold)은 구현 전에 어느 쪽을 따를지 정해야 한다.

## 배경 색상

| 모드 | 배경 |
|---|---|
| 라이트 | `#FFFFFF` |
| 다크 | `#111827` |

## 텍스트 색상 요약

| 역할 | 라이트 | 다크 | 사용 스타일 |
|---|---|---|---|
| 강조 텍스트 | `#374151` (gray-700) | `#E5E7EB` | Metric, Title |
| 보조 텍스트 | `#9CA3AF` (gray-400) | `#4B5563` | Subtitle |
| 본문 텍스트 | `#6B7280` (gray-500) | `#6B7280` | Text, Text-Bold, Text-Italic, Label |

괄호 안 Tailwind 색상 이름은 Figma 스타일 설명에 적힌 것이다. 다크 모드 색상에는 Figma에 이름이 없어 HEX만 적었다.

## 컴포넌트 색상

Colours 페이지는 Tailwind 색상 계열마다 500 단계 하나만 보여 준다. 아래는 컴포넌트에 실제로 쓰인 색상만 모은 것이다 (모두 라이트 모드 — 컴포넌트의 다크 모드 값은 Figma에 없다).

| 역할 | 값 | 쓰인 곳 |
|---|---|---|
| Primary | `#3B82F6` (blue-500) | Primary 버튼 배경, Secondary 버튼 테두리·글자 |
| Primary (Disabled) | `#60A5FA` | Disabled 버튼 배경(Primary), 테두리·글자(Secondary) |
| Surface | `#FFFFFF` | 카드, 입력창, 셀렉트, 드롭다운 항목 배경 |
| Surface (Muted) | `#F9FAFB` | 카드 안 플레이스홀더 영역 |
| Surface (Disabled) | `#F3F4F6` | Disabled 입력창 배경 |
| Border | `#E5E7EB` | 카드·입력창·셀렉트·드롭다운 테두리 |
| Border (Placeholder) | `#9CA3AF` | 카드 안 플레이스홀더 점선 테두리 |
| Divider | `#F3F4F6` | 구분선 |
| Error | `#EF4444` (red-500) | 입력창 Error 테두리·아이콘 |
| Metric (Card) | `#111827` | `Card + Metric`의 수치 텍스트 (Metric 스타일 기본색 `#374151`과 다름) |

## 모서리 (Border Radius)

| 요소 | 값 |
|---|---|
| 버튼, 입력창, 카드 | 8px |
| 셀렉트, 드롭다운 목록 | 6px |
| 카드 안 플레이스홀더 | 10px |
| 구분선 | 2px |

## 그림자 (Effect 스타일)

| 스타일 | 값 (CSS 표기) | 쓰인 곳 |
|---|---|---|
| `tremor-input` | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | 입력창, 셀렉트, 버튼 |
| `tremor-card` | `0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)` | 카드 |
| `tremor-dropdown` | `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` | 셀렉트 드롭다운 목록 |

## 간격 (Padding / Gap)

| 요소 | 패딩 (상 우 하 좌) | 내부 간격 | 크기 |
|---|---|---|---|
| 버튼 (md) | 8 16 8 16 | 아이콘–라벨 6px | 높이 36px |
| 입력창 | 8 12 8 12 | 8px | 높이 36px |
| 셀렉트 | 8 10 8 12 | 10px | 높이 36px |
| 드롭다운 항목 | 10 12 10 12 | 10px | 높이 40px |
| 카드 | 24 24 24 24 | 헤더–본문 16px | — |
| 구분선 | `mt-6 mb-6` (24px) 또는 `m-0` | — | 두께 1px |

테두리 두께는 모두 1px이다.

## 컴포넌트

### Button

| 종류 | Default | Disabled |
|---|---|---|
| Primary | 배경 `#3B82F6`, 글자 `#FFFFFF` | 배경 `#60A5FA`, 글자 `#FFFFFF` |
| Secondary | 테두리 `#3B82F6`, 글자 `#3B82F6`, 배경 없음 | 테두리·글자 `#60A5FA` |

공통: 라벨 `Text-medium`(14px / 500 / 20px), 모서리 8px, 그림자 `tremor-input`. Figma에는 Default·Disabled 상태만 있고 Hover·Active 상태는 없다.

### Text Input

| 상태 | 배경 | 테두리 | 글자 |
|---|---|---|---|
| Default (placeholder) | `#FFFFFF` | `#E5E7EB` | `#6B7280` |
| Active (값 입력됨) | `#FFFFFF` | `#E5E7EB` | `#374151` |
| Disabled | `#F3F4F6` | `#E5E7EB` | `#9CA3AF` |
| Error | `#FFFFFF` | `#EF4444` | `#374151` + 오류 아이콘 `#EF4444` |

공통: 글자 `Text` 스타일(14px), 모서리 8px, 그림자 `tremor-input`. Figma의 Active 상태는 테두리 색이 바뀌지 않는다 (포커스 링 없음).

### Select

닫힘/열림 모두 배경 `#FFFFFF`, 테두리 `#E5E7EB`, 모서리 6px, 그림자 `tremor-input`, 선택값 글자 `#374151`. 드롭다운 목록은 그림자 `tremor-dropdown`, 항목 배경 `#FFFFFF`, 항목 사이 테두리 `#E5E7EB`, 항목 아이콘 `#9CA3AF`.

### Card

배경 `#FFFFFF`, 테두리 `#E5E7EB`, 모서리 8px, 그림자 `tremor-card`, 패딩 24px.

| 변형 | 헤더 |
|---|---|
| `Card + Title` | 제목 `Title`(`#374151`) + 부제 `Text`(`#6B7280`), 헤더–본문 간격 16px |
| `Card + Metric` | 제목 `Text`(`#6B7280`) + 수치 `Metric`(`#111827`), 헤더–본문 간격 16px |
| `Card` | 헤더 없음 |

### Divider

색 `#F3F4F6`, 두께 1px, 모서리 2px. 위아래 여백은 24px(`mt-6 mb-6`) 또는 0.

## 구현 결정 (Figma 미정의)

Figma에 값이 없어 구현에서 정한 항목이다. 새 색상 값은 만들지 않고 위에서 확인된 값만 조합했다.

| 항목 | 결정 | 근거 |
|---|---|---|
| 버튼 Hover | 그림자를 `tremor-input` → `tremor-card`로 높임. Secondary는 배경 `#F9FAFB` | Figma에 Hover 상태 없음. 떠오르는 효과를 기존 그림자 스타일로 표현 |
| 버튼 Active(누름) | 그림자 제거 | 위와 같음 |
| 입력창·셀렉트 Focus | 테두리 `#3B82F6` (Primary) | Figma Active 상태는 테두리 변화 없음. 키보드 접근성을 위해 포커스 표시가 필요 |
| 파일 업로더 | 배경 `#F9FAFB`, 점선 테두리 `#9CA3AF`, 모서리 8px, 패딩 24px. Hover·Focus 시 테두리 `#3B82F6` | Figma에 업로더 컴포넌트 없음. `Card` 플레이스홀더(점선 영역) 스타일을 차용 |
| 다크 모드 컴포넌트 | 폰트·Primary·모서리·그림자·간격만 적용하고 배경·테두리 색은 Streamlit 다크 테마 기본값 사용 | 컴포넌트의 다크 모드 색상이 Figma에 없음 |
| 페이지 레이아웃 | 본문 최대 너비 1200px, 여백 상 64px(Streamlit 툴바 높이 확보) · 좌우 24px · 하 48px. 640px 이하에서는 좌우 16px, 카드 패딩 16px | Figma에 페이지 레이아웃 없음. 간격은 카드 패딩(24px) 기준 |
| 요소 간 간격 | 카드·위젯 사이 16px (카드 헤더–본문 간격과 동일), 헤더 아래 추가 8px | Card 헤더–본문 간격 16px 차용 |
| 해시태그 | `Text-Bold` 스타일, 가로 12px · 세로 6px 간격으로 줄바꿈 배치 | Figma에 해시태그 컴포넌트 없음 |
| 안내(Tip) 박스 | 배경 `#F9FAFB`, 테두리 `#E5E7EB`, 모서리 8px, 패딩 8 12, 글자 `Text` 스타일 ("Tip" 라벨은 500 · `#374151`) | Figma에 안내 컴포넌트 없음. Surface(Muted)·Border 색과 입력창 패딩을 차용 |
