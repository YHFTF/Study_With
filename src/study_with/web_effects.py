"""
웹 스타일 효과를 제공하는 유틸리티 모듈
- 부드러운 애니메이션
- 그림자 효과
- 호버 트랜지션
- 페이드 인/아웃
- 티어별 반짝이는 효과
"""

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, Qt, pyqtProperty, QAbstractAnimation, QSequentialAnimationGroup
from PyQt6.QtWidgets import QWidget, QPushButton, QGraphicsDropShadowEffect, QGraphicsBlurEffect
from PyQt6.QtGui import QColor


class AnimatedButton(QPushButton):
    """호버 시 부드럽게 색상이 변하는 버튼"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._normal_color = "#4C566A"
        self._hover_color = "#5E81AC"
        self._pressed_color = "#3B4252"
        self._current_opacity = 1.0
        
        # 애니메이션 설정
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(200)  # 200ms 트랜지션
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # 초기 스타일 설정
        self._update_style()
        
    def _update_style(self):
        """현재 상태에 맞는 스타일 적용"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._normal_color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
                transition: all 0.2s ease;
            }}
            QPushButton:hover {{
                background-color: {self._hover_color};
                transform: translateY(-2px);
            }}
            QPushButton:pressed {{
                background-color: {self._pressed_color};
            }}
        """)
    
    def enterEvent(self, event):
        """마우스 진입 시"""
        super().enterEvent(event)
        self.animation.setStartValue(0.8)
        self.animation.setEndValue(1.0)
        self.animation.start()
        self._update_style()
    
    def leaveEvent(self, event):
        """마우스 떠날 때"""
        super().leaveEvent(event)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.8)
        self.animation.start()
    
    def setColors(self, normal: str, hover: str = None, pressed: str = None):
        """버튼 색상 설정"""
        self._normal_color = normal
        self._hover_color = hover or normal
        self._pressed_color = pressed or normal
        self._update_style()
    
    @pyqtProperty(float)
    def opacity(self):
        return self._current_opacity
    
    @opacity.setter
    def opacity(self, value):
        self._current_opacity = value


def add_shadow_effect(widget: QWidget, 
                     blur_radius: int = 15,
                     x_offset: int = 0,
                     y_offset: int = 5,
                     color: QColor = None) -> QGraphicsDropShadowEffect:
    """
    위젯에 그림자 효과 추가 (웹의 box-shadow와 유사)
    
    Args:
        widget: 그림자를 추가할 위젯
        blur_radius: 블러 반경 (기본 15)
        x_offset: X 오프셋 (기본 0)
        y_offset: Y 오프셋 (기본 5)
        color: 그림자 색상 (기본 반투명 검정)
    
    Returns:
        QGraphicsDropShadowEffect 객체
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setXOffset(x_offset)
    shadow.setYOffset(y_offset)
    if color is None:
        color = QColor(0, 0, 0, 80)  # 반투명 검정
    shadow.setColor(color)
    widget.setGraphicsEffect(shadow)
    return shadow


def add_glow_effect(widget: QWidget, 
                   color: QColor,
                   blur_radius: int = 20) -> QGraphicsDropShadowEffect:
    """
    위젯에 글로우 효과 추가 (웹의 text-shadow나 box-shadow glow와 유사)
    
    Args:
        widget: 글로우를 추가할 위젯
        color: 글로우 색상
        blur_radius: 블러 반경
    
    Returns:
        QGraphicsDropShadowEffect 객체
    """
    glow = QGraphicsDropShadowEffect()
    glow.setBlurRadius(blur_radius)
    glow.setXOffset(0)
    glow.setYOffset(0)
    glow.setColor(color)
    widget.setGraphicsEffect(glow)
    return glow


def fade_in(widget: QWidget, duration: int = 300):
    """
    위젯을 페이드 인 애니메이션으로 표시
    
    Args:
        widget: 애니메이션할 위젯
        duration: 애니메이션 지속 시간 (ms)
    """
    widget.setGraphicsEffect(None)  # 기존 효과 제거
    animation = QPropertyAnimation(widget, b"windowOpacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.start()
    widget.show()


def fade_out(widget: QWidget, duration: int = 300, hide_after: bool = True):
    """
    위젯을 페이드 아웃 애니메이션으로 숨김
    
    Args:
        widget: 애니메이션할 위젯
        duration: 애니메이션 지속 시간 (ms)
        hide_after: 애니메이션 후 위젯 숨김 여부
    """
    animation = QPropertyAnimation(widget, b"windowOpacity")
    animation.setDuration(duration)
    animation.setStartValue(1.0)
    animation.setEndValue(0.0)
    animation.setEasingCurve(QEasingCurve.Type.InCubic)
    
    if hide_after:
        animation.finished.connect(lambda: widget.hide())
    
    animation.start()


def slide_in(widget: QWidget, 
            direction: str = "right",
            duration: int = 300):
    """
    위젯을 슬라이드 인 애니메이션으로 표시
    
    Args:
        widget: 애니메이션할 위젯
        direction: 슬라이드 방향 ("left", "right", "top", "bottom")
        duration: 애니메이션 지속 시간 (ms)
    """
    parent = widget.parent()
    if parent is None:
        return
    
    # 초기 위치 설정
    start_pos = widget.pos()
    if direction == "right":
        widget.move(parent.width(), start_pos.y())
    elif direction == "left":
        widget.move(-widget.width(), start_pos.y())
    elif direction == "top":
        widget.move(start_pos.x(), -widget.height())
    elif direction == "bottom":
        widget.move(start_pos.x(), parent.height())
    
    # 애니메이션
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(widget.pos())
    animation.setEndValue(start_pos)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.start()
    widget.show()


def add_hover_scale(widget: QWidget, scale_factor: float = 1.05):
    """
    호버 시 위젯이 살짝 확대되는 효과
    
    Args:
        widget: 효과를 추가할 위젯
        scale_factor: 확대 비율 (기본 1.05 = 5% 확대)
    """
    original_style = widget.styleSheet()
    
    def enter_event(e):
        widget.setStyleSheet(original_style + f"""
            {widget.__class__.__name__} {{
                transform: scale({scale_factor});
            }}
        """)
        QWidget.enterEvent(widget, e)
    
    def leave_event(e):
        widget.setStyleSheet(original_style)
        QWidget.leaveEvent(widget, e)
    
    widget.enterEvent = enter_event
    widget.leaveEvent = leave_event


def create_web_style_button(text: str,
                           normal_color: str = "#4C566A",
                           hover_color: str = "#5E81AC",
                           pressed_color: str = "#3B4252",
                           with_shadow: bool = True) -> QPushButton:
    """
    웹 스타일의 버튼 생성 (그림자, 호버 효과 포함)
    
    Args:
        text: 버튼 텍스트
        normal_color: 기본 색상
        hover_color: 호버 색상
        pressed_color: 눌렀을 때 색상
        with_shadow: 그림자 효과 사용 여부
    
    Returns:
        스타일이 적용된 QPushButton
    """
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    
    # 웹 스타일 CSS
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {normal_color};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
        }}
        QPushButton:pressed {{
            background-color: {pressed_color};
        }}
    """)
    
    if with_shadow:
        add_shadow_effect(btn, blur_radius=10, y_offset=3)
    
    return btn


class SparkleEffect:
    """
    티어별 반짝이는 효과 클래스
    글로우 효과를 펄스 애니메이션으로 만들어 반짝이는 효과를 제공
    """
    def __init__(self, widget: QWidget, color: QColor, 
                 min_blur: int = 10, max_blur: int = 30,
                 duration: int = 1500):
        """
        Args:
            widget: 효과를 적용할 위젯
            color: 반짝이는 색상 (티어별 accent_color)
            min_blur: 최소 블러 반경
            max_blur: 최대 블러 반경
            duration: 한 사이클 애니메이션 시간 (ms)
        """
        self.widget = widget
        self.color = color
        self.min_blur = min_blur
        self.max_blur = max_blur
        self.duration = duration
        
        # 글로우 효과 생성
        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setXOffset(0)
        self.glow_effect.setYOffset(0)
        self.glow_effect.setColor(color)
        self.glow_effect.setBlurRadius(min_blur)
        widget.setGraphicsEffect(self.glow_effect)
        
        # 블러 반경 애니메이션 (양방향 반복)
        self.blur_animation = QPropertyAnimation(self.glow_effect, b"blurRadius")
        self.blur_animation.setDuration(duration)
        self.blur_animation.setStartValue(min_blur)
        self.blur_animation.setEndValue(max_blur)
        self.blur_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        # 양방향 반복: min -> max -> min -> max ...
        # PyQt6에서는 -1이 무한 반복을 의미
        self.blur_animation.setLoopCount(-1)
        
        # 색상 알파 애니메이션 (더 부드러운 반짝임)
        self._alpha = color.alpha()
        
    def start(self):
        """반짝이는 효과 시작"""
        # 양방향 애니메이션을 위해 애니메이션 그룹 사용
        # 순차 애니메이션 그룹 생성 (양방향 반복)
        if not hasattr(self, '_animation_group') or self._animation_group is None:
            self._animation_group = QSequentialAnimationGroup()
            
            # min -> max 애니메이션
            forward = QPropertyAnimation(self.glow_effect, b"blurRadius")
            forward.setDuration(self.duration)
            forward.setStartValue(self.min_blur)
            forward.setEndValue(self.max_blur)
            forward.setEasingCurve(QEasingCurve.Type.InOutSine)
            
            # max -> min 애니메이션
            backward = QPropertyAnimation(self.glow_effect, b"blurRadius")
            backward.setDuration(self.duration)
            backward.setStartValue(self.max_blur)
            backward.setEndValue(self.min_blur)
            backward.setEasingCurve(QEasingCurve.Type.InOutSine)
            
            self._animation_group.addAnimation(forward)
            self._animation_group.addAnimation(backward)
            # PyQt6에서는 -1이 무한 반복을 의미
            self._animation_group.setLoopCount(-1)
        
        if not self._animation_group.state() == QAbstractAnimation.State.Running:
            self._animation_group.start()
        
    def stop(self):
        """반짝이는 효과 중지"""
        if hasattr(self, '_animation_group'):
            self._animation_group.stop()
        if hasattr(self, 'blur_animation'):
            self.blur_animation.stop()
        self.glow_effect.setBlurRadius(self.min_blur)
        
    def set_intensity(self, intensity: float):
        """
        반짝이는 강도 조절 (0.0 ~ 1.0)
        
        Args:
            intensity: 반짝이는 강도 (0.0 = 약함, 1.0 = 강함)
        """
        intensity = max(0.0, min(1.0, intensity))
        new_min = int(self.min_blur * (0.5 + intensity * 0.5))
        new_max = int(self.max_blur * (0.5 + intensity * 0.5))
        self.min_blur = new_min
        self.max_blur = new_max
        self.blur_animation.setStartValue(new_min)
        self.blur_animation.setEndValue(new_max)


def add_sparkle_effect(widget: QWidget, 
                       color: QColor,
                       min_blur: int = 10,
                       max_blur: int = 30,
                       duration: int = 1500,
                       auto_start: bool = True) -> SparkleEffect:
    """
    위젯에 티어별 반짝이는 효과 추가
    
    Args:
        widget: 효과를 적용할 위젯
        color: 반짝이는 색상 (티어별 accent_color)
        min_blur: 최소 블러 반경 (기본 10)
        max_blur: 최대 블러 반경 (기본 30)
        duration: 한 사이클 애니메이션 시간 (ms, 기본 1500)
        auto_start: 자동으로 시작할지 여부 (기본 True)
    
    Returns:
        SparkleEffect 객체 (start/stop 제어 가능)
    
    Example:
        from study_with.web_effects import add_sparkle_effect
        from study_with.rank_themes import get_theme
        from PyQt6.QtGui import QColor
        
        theme = get_theme("DIAMOND")
        color = QColor(theme['accent_color'])
        sparkle = add_sparkle_effect(self.rank_image_label, color)
    """
    sparkle = SparkleEffect(widget, color, min_blur, max_blur, duration)
    if auto_start:
        sparkle.start()
    return sparkle


def hex_to_qcolor(hex_color: str, alpha: int = 255) -> QColor:
    """
    헥스 색상 문자열을 QColor로 변환
    
    Args:
        hex_color: "#RRGGBB" 또는 "#RGB" 형식의 색상
        alpha: 알파값 (0-255, 기본 255)
    
    Returns:
        QColor 객체
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    elif len(hex_color) == 3:
        r = int(hex_color[0] * 2, 16)
        g = int(hex_color[1] * 2, 16)
        b = int(hex_color[2] * 2, 16)
    else:
        r, g, b = 255, 255, 255  # 기본값
    
    return QColor(r, g, b, alpha)
