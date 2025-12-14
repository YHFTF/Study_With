# 웹 스타일 효과 가이드

PyQt6에서 웹처럼 부드러운 애니메이션과 효과를 추가하는 방법입니다.

## 사용 가능한 효과들

### 1. 그림자 효과 (Box Shadow)
```python
from study_with.web_effects import add_shadow_effect

# 버튼에 그림자 추가
add_shadow_effect(self.start_btn, blur_radius=15, y_offset=5)
```

### 2. 글로우 효과 (Glow)
```python
from study_with.web_effects import add_glow_effect
from PyQt6.QtGui import QColor

# 라벨에 글로우 효과 추가
glow_color = QColor(88, 192, 208, 150)  # #58C0D0 with alpha
add_glow_effect(self.timer_label, glow_color, blur_radius=20)
```

### 3. 페이드 인/아웃
```python
from study_with.web_effects import fade_in, fade_out

# 위젯을 부드럽게 나타내기
fade_in(self.stats_window, duration=300)

# 위젯을 부드럽게 숨기기
fade_out(self.stats_window, duration=300)
```

### 4. 슬라이드 애니메이션
```python
from study_with.web_effects import slide_in

# 오른쪽에서 슬라이드 인
slide_in(self.stats_window, direction="right", duration=300)
```

### 5. 웹 스타일 버튼 생성
```python
from study_with.web_effects import create_web_style_button

# 그림자와 호버 효과가 있는 버튼
btn = create_web_style_button(
    "세션 시작",
    normal_color="#4C566A",
    hover_color="#5E81AC",
    with_shadow=True
)
```

## UI에 적용하는 예제

### 예제 1: 기존 버튼에 효과 추가

`ui.py`의 `init_ui` 메서드에서:

```python
from study_with.web_effects import add_shadow_effect, add_glow_effect
from PyQt6.QtGui import QColor

# 세션 시작 버튼에 그림자 추가
add_shadow_effect(self.start_btn, blur_radius=12, y_offset=4)

# 통계 버튼에 그림자 추가
add_shadow_effect(self.stats_btn, blur_radius=10, y_offset=3)

# 타이머 라벨에 글로우 효과 (등급별 색상)
if not self.simple_mode:
    theme = get_theme(self.current_rank)
    glow_color = QColor(*hex_to_rgb(theme['accent_color']), 120)
    add_glow_effect(self.timer_label, glow_color)
```

### 예제 2: 통계 창에 페이드 효과

`app.py`에서 통계 창을 열 때:

```python
from study_with.web_effects import fade_in

def show_stats(self):
    if not self.stats_window.isVisible():
        fade_in(self.stats_window, duration=300)
    self.stats_window.show()
```

### 예제 3: 버튼 스타일 개선

기존 버튼 스타일을 웹 스타일로 변경:

```python
# 기존 코드
self.start_btn.setStyleSheet("background-color: #4C566A; color: white; padding: 8px;")

# 웹 스타일로 변경
self.start_btn.setStyleSheet("""
    QPushButton {
        background-color: #4C566A;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #5E81AC;
        transform: translateY(-2px);
    }
    QPushButton:pressed {
        background-color: #3B4252;
    }
""")
add_shadow_effect(self.start_btn, blur_radius=10, y_offset=3)
```

## 고급 효과

### 호버 시 확대 효과
```python
from study_with.web_effects import add_hover_scale

# 버튼에 호버 시 5% 확대 효과
add_hover_scale(self.start_btn, scale_factor=1.05)
```

### 애니메이션 버튼
```python
from study_with.web_effects import AnimatedButton

# 부드러운 색상 전환 애니메이션이 있는 버튼
btn = AnimatedButton("세션 시작")
btn.setColors(normal="#4C566A", hover="#5E81AC", pressed="#3B4252")
```

## 성능 고려사항

1. **애니메이션 지속 시간**: 200-300ms가 가장 자연스럽습니다
2. **그림자 효과**: 너무 많은 위젯에 적용하면 성능 저하 가능
3. **애니메이션 동시 실행**: 동시에 너무 많은 애니메이션을 실행하지 마세요

## 브라우저 호환성과 유사성

- `add_shadow_effect` = CSS `box-shadow`
- `add_glow_effect` = CSS `text-shadow` 또는 `box-shadow` with glow
- `fade_in/fade_out` = CSS `opacity` + `transition`
- `slide_in` = CSS `transform: translateX/Y` + `transition`
- `AnimatedButton` = CSS `:hover` + `transition`

## 실제 적용 예제

`ui.py`에 다음을 추가하면 모든 버튼에 웹 스타일 효과가 적용됩니다:

```python
def _apply_web_effects(self):
    """모든 버튼에 웹 스타일 효과 적용"""
    from study_with.web_effects import add_shadow_effect
    
    buttons = [
        self.start_btn,
        self.stats_btn,
        self.load_btn,
        self.save_btn,
    ]
    
    for btn in buttons:
        if btn:
            add_shadow_effect(btn, blur_radius=10, y_offset=3)
```

그리고 `init_ui` 메서드 끝에 호출:
```python
self._apply_web_effects()
```

## 티어별 반짝이는 효과

### 자동 적용
통계 창에서 티어 이미지와 라벨에 자동으로 반짝이는 효과가 적용됩니다. 각 티어의 색상에 맞춰 부드럽게 반짝입니다.

### 수동 적용
```python
from study_with.web_effects import add_sparkle_effect, hex_to_qcolor
from study_with.rank_themes import get_theme

# 티어별 색상 가져오기
theme = get_theme("DIAMOND")
color = hex_to_qcolor(theme['accent_color'], alpha=200)

# 반짝이는 효과 추가
sparkle = add_sparkle_effect(
    self.rank_image_label,
    color,
    min_blur=15,      # 최소 블러 반경
    max_blur=35,      # 최대 블러 반경
    duration=1500,    # 한 사이클 시간 (ms)
    auto_start=True   # 자동 시작
)

# 효과 제어
sparkle.stop()       # 중지
sparkle.start()      # 시작
sparkle.set_intensity(0.5)  # 강도 조절 (0.0 ~ 1.0)
```

### 티어별 효과 설정
- **BRONZE**: 부드러운 브론즈 색상으로 반짝임
- **SILVER**: 실버 색상으로 반짝임
- **GOLD**: 골드 색상으로 반짝임
- **PLATINUM**: 플래티넘 색상으로 반짝임
- **DIAMOND**: 다이아몬드 색상으로 반짝임 (더 강한 효과)
- **MASTER**: 보라색으로 반짝임
- **GRANDMASTER**: 빨간색으로 반짝임
- **CHALLENGER**: 오렌지색으로 반짝임
- **LEGEND**: 골드 색상으로 반짝임 (가장 강한 효과)

### 심플 모드
심플 모드가 활성화되면 반짝이는 효과가 자동으로 비활성화됩니다.
