"""등급별 테마 및 스타일 정의"""
from typing import Dict

# 폰트 이름 (app.py에서 설정됨)
_custom_font_name: str = ""

def set_custom_font_name(font_name: str) -> None:
    """커스텀 폰트 이름 설정 (app.py에서 호출)"""
    global _custom_font_name
    _custom_font_name = font_name

def get_custom_font_name() -> str:
    """로드된 커스텀 폰트 이름 반환"""
    return _custom_font_name

# 등급별 테마 정의
RANK_THEMES: Dict[str, Dict[str, str]] = {
    "BRONZE": {
        "name": "브론즈",
        "bg_color": "#2E3440",  # 기본 어두운 배경
        "accent_color": "#A67C52",  # 부드러운 브론즈 색상 (더 어둡고 부드러움)
        "border_color": "#8B6F47",
        "text_color": "#ECEFF4",
        "title_color": "#A67C52",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(166, 124, 82, 200)",  # 브론즈 투명 배경
        "pip_border": "#8B6F47",
        "emoji": "🥉",
        "image": "bronze.webp"
    },
    "SILVER": {
        "name": "실버",
        "bg_color": "#2E3440",
        "accent_color": "#9CA3AF",  # 부드러운 실버 색상 (더 어둡고 부드러움)
        "border_color": "#6B7280",
        "text_color": "#ECEFF4",
        "title_color": "#9CA3AF",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4C566A, stop:1 #3B4252)",
        "pip_bg": "rgba(156, 163, 175, 200)",
        "pip_border": "#6B7280",
        "emoji": "🥈",
        "image": "sliver.webp"  # 파일명 오타 반영
    },
    "GOLD": {
        "name": "골드",
        "bg_color": "#2E3440",  # 기본 배경 유지
        "accent_color": "#D4AF37",  # 부드러운 골드 색상 (더 어둡고 부드러움)
        "border_color": "#B8941F",
        "text_color": "#ECEFF4",
        "title_color": "#D4AF37",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(212, 175, 55, 200)",
        "pip_border": "#B8941F",
        "emoji": "🥇",
        "image": "gold.webp"
    },
    "PLATINUM": {
        "name": "플래티넘",
        "bg_color": "#2E3440",  # 기본 배경 유지
        "accent_color": "#B8B6B4",  # 부드러운 플래티넘 색상 (더 어둡고 부드러움)
        "border_color": "#9A9896",
        "text_color": "#ECEFF4",
        "title_color": "#B8B6B4",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(184, 182, 180, 200)",
        "pip_border": "#9A9896",
        "emoji": "💎",
        "image": "platinum.webp"
    },
    "DIAMOND": {
        "name": "다이아몬드",
        "bg_color": "#2E3440",  # 기본 배경 유지
        "accent_color": "#7DD3FC",  # 부드러운 다이아몬드 색상 (더 어둡고 부드러움)
        "border_color": "#38BDF8",
        "text_color": "#ECEFF4",
        "title_color": "#7DD3FC",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(125, 211, 252, 200)",
        "pip_border": "#38BDF8",
        "emoji": "💠",
        "image": "diamond.webp"
    },
    "MASTER": {
        "name": "마스터",
        "bg_color": "#2E3440",  # 기본 배경 유지
        "accent_color": "#A78BFA",  # 부드러운 보라색 (더 밝고 부드러움)
        "border_color": "#8B5CF6",
        "text_color": "#ECEFF4",
        "title_color": "#A78BFA",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(167, 139, 250, 200)",
        "pip_border": "#8B5CF6",
        "emoji": "👑",
        "image": "master.webp"
    },
    "GRANDMASTER": {
        "name": "그랜드마스터",
        "bg_color": "#2E3440",  # 기본 배경 유지
        "accent_color": "#F87171",  # 부드러운 빨간색 (더 밝고 부드러움)
        "border_color": "#EF4444",
        "text_color": "#ECEFF4",
        "title_color": "#F87171",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(248, 113, 113, 200)",
        "pip_border": "#EF4444",
        "emoji": "🔥",
        "image": "grandmaster.webp"
    },
    "CHALLENGER": {
        "name": "챌린저",
        "bg_color": "#2E3440",  # 기본 배경 유지
        "accent_color": "#FB923C",  # 부드러운 오렌지색 (더 밝고 부드러움)
        "border_color": "#F97316",
        "text_color": "#ECEFF4",
        "title_color": "#FB923C",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(251, 146, 60, 200)",
        "pip_border": "#F97316",
        "emoji": "⚡",
        "image": "challenger.webp"
    },
    "LEGEND": {
        "name": "레전드",
        "bg_color": "#2E3440",  # 기본 배경 유지
        "accent_color": "#FCD34D",  # 부드러운 골드 (더 밝고 부드러움)
        "border_color": "#FBBF24",  # 부드러운 골드 테두리
        "text_color": "#ECEFF4",
        "title_color": "#FCD34D",
        "gradient": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B4252, stop:1 #2E3440)",
        "pip_bg": "rgba(252, 211, 77, 200)",
        "pip_border": "#FBBF24",
        "emoji": "🌟",
        "image": "challenger.webp"  # 레전드 이미지가 없으면 챌린저 이미지 사용
    }
}

def get_theme(rank: str) -> Dict[str, str]:
    """등급에 해당하는 테마 반환"""
    return RANK_THEMES.get(rank, RANK_THEMES["BRONZE"])

def get_default_style() -> str:
    """기본 스타일 반환 (심플 모드용)"""
    font_name = get_custom_font_name()
    font_family = f"'{font_name}', " if font_name else ""
    return f"""
        * {{
            font-family: {font_family}'Malgun Gothic', 'Segoe UI', sans-serif;
            font-size: 14px;
        }}

        QMainWindow {{ 
            background-color: #2E3440;
        }}
        
        QLabel {{ 
            color: #ECEFF4; 
        }}

        #TitleLabel {{ 
            font-size: 24px; 
            font-weight: bold; 
            margin-top: 10px; 
            color: #88C0D0; 
        }}
        
        #TimerLabel {{ 
            font-size: 70px; 
            font-weight: bold; 
            color: #ECEFF4; 
            margin: 10px 0; 
        }}
        
        #StatusLabel {{ 
            font-size: 18px; 
            margin-bottom: 20px; 
            color: #ECEFF4;
        }}
        
        QFrame#SettingsFrame {{ 
            background-color: rgba(59, 66, 82, 180); 
            border: 2px solid #4C566A;
            border-radius: 10px; 
            padding: 10px; 
            margin: 10px; 
        }}
        
        QLineEdit, QSpinBox {{ 
            background-color: rgba(76, 86, 106, 200); 
            color: white; 
            border: 2px solid #4C566A; 
            padding: 5px; 
            border-radius: 5px; 
        }}
        
        QLineEdit:focus, QSpinBox:focus {{
            border: 2px solid #5E81AC;
            background-color: rgba(76, 86, 106, 250);
        }}
        
        /* QSpinBox 위아래 버튼 스타일 */
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: rgba(94, 129, 172, 200);
            border: none;
            border-radius: 3px;
            width: 20px;
            min-width: 20px;
            max-width: 20px;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: rgba(129, 161, 193, 250);
        }}
        
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
            background-color: rgba(76, 86, 106, 250);
        }}
        
        QSpinBox::up-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #ECEFF4;
            width: 0px;
            height: 0px;
            margin-left: 2px;
            margin-right: 2px;
        }}
        
        QSpinBox::up-arrow:hover {{
            border-bottom: 5px solid #88C0D0;
        }}
        
        QSpinBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #ECEFF4;
            width: 0px;
            height: 0px;
            margin-left: 2px;
            margin-right: 2px;
        }}
        
        QSpinBox::down-arrow:hover {{
            border-top: 5px solid #88C0D0;
        }}
        
        QCheckBox {{ 
            color: #ECEFF4; 
            spacing: 5px; 
        }}
        
        QTextEdit#LogViewer {{
            background-color: #242933; 
            color: #ECEFF4; 
            border: 2px solid #4C566A; 
            border-radius: 5px; 
            padding: 5px; 
            font-family: {font_family}'Consolas', monospace; 
            font-size: 12px; 
        }}
        
        QPushButton#StartBtn {{ 
            background-color: #5E81AC; 
            color: white; 
            font-size: 18px; 
            font-weight: bold; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 10px; 
        }}
        QPushButton#StartBtn:hover {{ 
            background-color: #81A1C1; 
        }}
        
        QPushButton#PipBtn {{ 
            background-color: #4C566A; 
            border: 1px solid #5E81AC; 
            border-radius: 5px; 
            color: #ECEFF4;
            padding: 5px 10px;
            font-size: 12px;
        }}
        QPushButton#PipBtn:hover {{ 
            background-color: #5E81AC; 
        }}
    """

def get_main_window_style(rank: str) -> str:
    """메인 창 스타일 반환 (포인트 색상만 변경)"""
    theme = get_theme(rank)
    font_name = get_custom_font_name()
    font_family = f"'{font_name}', " if font_name else ""
    return f"""
        * {{
            font-family: {font_family}'Malgun Gothic', 'Segoe UI', sans-serif;
            font-size: 14px;
        }}

        QMainWindow {{ 
            background-color: #2E3440;
        }}
        
        QLabel {{ 
            color: #ECEFF4; 
        }}

        #TitleLabel {{ 
            font-size: 24px; 
            font-weight: bold; 
            margin-top: 10px; 
            color: {theme['accent_color']}; 
        }}
        
        #TimerLabel {{ 
            font-size: 70px; 
            font-weight: bold; 
            color: {theme['accent_color']}; 
            margin: 10px 0; 
            text-shadow: 0 0 5px {theme['accent_color']};
        }}
        
        #StatusLabel {{ 
            font-size: 18px; 
            margin-bottom: 20px; 
            color: #ECEFF4;
        }}
        
        QFrame#SettingsFrame {{ 
            background-color: rgba(59, 66, 82, 180); 
            border: 2px solid {theme['accent_color']};
            border-radius: 10px; 
            padding: 10px; 
            margin: 10px; 
        }}
        
        QLineEdit, QSpinBox {{ 
            background-color: rgba(76, 86, 106, 200); 
            color: white; 
            border: 2px solid #4C566A; 
            padding: 5px; 
            border-radius: 5px; 
        }}
        
        QLineEdit:focus, QSpinBox:focus {{
            border: 2px solid {theme['accent_color']};
            background-color: rgba(76, 86, 106, 250);
        }}
        
        /* QSpinBox 위아래 버튼 스타일 (티어별 색상 적용) */
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: rgba(94, 129, 172, 200);
            border: none;
            border-radius: 3px;
            width: 20px;
            min-width: 20px;
            max-width: 20px;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: {theme['accent_color']};
        }}
        
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
            background-color: {theme['border_color']};
        }}
        
        QSpinBox::up-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #ECEFF4;
            width: 0px;
            height: 0px;
            margin-left: 2px;
            margin-right: 2px;
        }}
        
        QSpinBox::up-arrow:hover {{
            border-bottom: 5px solid {theme['accent_color']};
        }}
        
        QSpinBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #ECEFF4;
            width: 0px;
            height: 0px;
            margin-left: 2px;
            margin-right: 2px;
        }}
        
        QSpinBox::down-arrow:hover {{
            border-top: 5px solid {theme['accent_color']};
        }}
        
        QCheckBox {{ 
            color: #ECEFF4; 
            spacing: 5px; 
        }}
        
        QTextEdit#LogViewer {{ 
            background-color: #242933; 
            color: #ECEFF4; 
            border: 2px solid #4C566A; 
            border-radius: 5px; 
            padding: 5px; 
            font-family: {font_family}'Consolas', monospace; 
            font-size: 12px; 
        }}
        
        QPushButton#StartBtn {{ 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme['accent_color']}, stop:1 {theme['border_color']});
            color: #2E3440; 
            font-size: 18px; 
            font-weight: bold; 
            padding: 15px; 
            border-radius: 10px; 
            margin: 10px; 
            border: 2px solid {theme['border_color']};
        }}
        QPushButton#StartBtn:hover {{ 
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme['border_color']}, stop:1 {theme['accent_color']});
        }}
        
        QPushButton#PipBtn {{ 
            background-color: rgba(76, 86, 106, 200); 
            border: 2px solid #4C566A; 
            border-radius: 5px; 
            color: #ECEFF4;
            padding: 5px 10px;
            font-size: 12px;
        }}
        QPushButton#PipBtn:hover {{ 
            background-color: {theme['accent_color']};
            color: #2E3440;
        }}
    """

def get_pip_style(rank: str) -> str:
    """PIP 모드 스타일 반환 (포인트 색상만 변경)"""
    theme = get_theme(rank)
    font_name = get_custom_font_name()
    font_family = f"'{font_name}', " if font_name else ""
    return f"""
        QFrame {{
            background-color: rgba(46, 52, 64, 240);
            border-radius: 15px;
            border: 3px solid {theme['accent_color']};
        }}
        QLabel {{ 
            color: #ECEFF4; 
            font-family: {font_family}'Segoe UI', sans-serif; 
            border: none; 
            background: transparent; 
        }}
    """

def get_default_pip_style() -> str:
    """기본 PIP 모드 스타일 반환 (심플 모드용)"""
    font_name = get_custom_font_name()
    font_family = f"'{font_name}', " if font_name else ""
    return f"""
        QFrame {{
            background-color: rgba(46, 52, 64, 240);
            border-radius: 15px;
            border: 2px solid #4C566A;
        }}
        QLabel {{ 
            color: #ECEFF4; 
            font-family: {font_family}'Segoe UI', sans-serif; 
            border: none; 
            background: transparent; 
        }}
    """
