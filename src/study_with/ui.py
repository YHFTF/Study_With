# ui.py
import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QSpinBox, QFormLayout, 
                             QFrame, QCheckBox, QTextEdit, QMessageBox, QHBoxLayout,
                             QScrollArea, QGridLayout, QProgressBar, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QMouseEvent, QPixmap, QImage, QPainter, QPen, QBrush, QColor
from datetime import datetime
from .rank_themes import get_main_window_style, get_pip_style, get_theme, get_default_style, get_default_pip_style, RANK_THEMES
from .web_effects import add_sparkle_effect, hex_to_qcolor

def _resources_dir() -> Path:
    """리소스 디렉토리 반환"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "resources"
    # ui.py는 src/study_with/ui.py에 있으므로 parent만 사용
    return Path(__file__).resolve().parent / "resources"

def resource_path(*relative_parts: str) -> str:
    """리소스 파일 경로 반환"""
    return str(_resources_dir().joinpath(*relative_parts))

# ========================================================
# PIP 모드 전용 미니 창
# ========================================================
class PipUI(QWidget):
    def __init__(self):
        super().__init__()
        # 1. 창 설정: 테두리 없음, 항상 위에, 도구 창 스타일(작업표시줄에 안 뜸)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # 배경 투명 설정 가능하게
        self.setFixedSize(220, 100) # 작고 고정된 크기
        
        # 마우스 드래그를 위한 변수
        self.old_pos = None
        self.current_rank = "BRONZE"  # 기본 등급
        self.simple_mode = False  # 심플 모드 상태

        self.init_ui()

    def init_ui(self):
        # 메인 컨테이너 (둥근 모서리 배경용)
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 220, 100)
        self.update_rank_style("BRONZE", simple_mode=False)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(10, 5, 10, 5)

        # 2. 상단: 상태 표시 + 복귀 버튼
        header_layout = QHBoxLayout()
        self.status_label = QLabel("🔥 집중 중")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #D08770;")
        
        self.return_btn = QPushButton("↖복귀")
        self.return_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.return_btn.setFixedSize(50, 25)
        self.return_btn.setStyleSheet("""
            QPushButton { background-color: #4C566A; color: white; border-radius: 5px; font-size: 11px; border: none;}
            QPushButton:hover { background-color: #5E81AC; }
        """)
        
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.return_btn)
        layout.addLayout(header_layout)

        # 3. 하단: 타이머 시간
        self.timer_label = QLabel("39:55")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 36px; font-weight: bold; margin-top: -5px;")
        layout.addWidget(self.timer_label)
    
    def update_rank_style(self, rank: str, simple_mode: bool = False):
        """등급에 따라 PIP 모드 스타일 업데이트"""
        try:
            self.current_rank = rank
            self.simple_mode = simple_mode
            
            if simple_mode:
                # 심플 모드일 때는 기본 스타일 사용
                self.container.setStyleSheet(get_default_pip_style())
                if hasattr(self, 'timer_label') and self.timer_label:
                    self.timer_label.setStyleSheet(
                        "font-size: 36px; font-weight: bold; margin-top: -5px; color: #ECEFF4;"
                    )
            else:
                # 티어별 스타일 사용
                theme = get_theme(rank)
                self.container.setStyleSheet(get_pip_style(rank))
                # 타이머 라벨 색상도 업데이트
                if hasattr(self, 'timer_label') and self.timer_label:
                    self.timer_label.setStyleSheet(
                        f"font-size: 36px; font-weight: bold; margin-top: -5px; "
                        f"color: {theme['accent_color']}; "
                        f"text-shadow: 0 0 3px {theme['accent_color']};"
                    )
        except Exception as e:
            # PIP UI는 로그 핸들러가 없으므로 print 사용
            print(f"PIP 스타일 업데이트 오류: {e}")
            import traceback
            traceback.print_exc()

    # --- [필수] 창 드래그 이동 기능 ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.old_pos = None

# ========================================================
# 등급 진행 바 위젯
# ========================================================
class RankProgressBar(QWidget):
    """등급 진행을 시각적으로 표시하는 커스텀 위젯"""
    def __init__(self, current_rank: str, next_rank: str, current_score: int, next_threshold: int, parent=None):
        super().__init__(parent)
        self.current_rank = current_rank
        self.next_rank = next_rank
        self.current_score = current_score
        self.next_threshold = next_threshold
        self.setMinimumHeight(140)  # 남은 점수 표시를 위해 높이 증가
        self.setMinimumWidth(400)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # 등급 순서 정의
        rank_order = ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER", "LEGEND"]
        
        try:
            current_idx = rank_order.index(self.current_rank)
            next_idx = rank_order.index(self.next_rank) if self.next_rank and self.next_rank in rank_order else current_idx + 1
        except ValueError:
            current_idx = 0
            next_idx = 1
        
        # 표시할 등급 범위 결정 (현재 등급부터 다음 등급까지)
        if next_idx > current_idx:
            display_ranks = rank_order[current_idx:next_idx + 1]
        else:
            display_ranks = [self.current_rank, self.next_rank] if self.next_rank else [self.current_rank]
        
        num_ranks = len(display_ranks)
        if num_ranks < 2:
            num_ranks = 2
        
        # 진행 바 설정
        bar_y = height // 2 + 10  # 중앙에서 약간 아래로 조정
        bar_height = 3
        bar_margin = 60
        bar_width = width - 2 * bar_margin
        
        # 진행 바 배경 (어두운 회색)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#2E3440")))
        painter.drawRoundedRect(bar_margin, bar_y - bar_height // 2, bar_width, bar_height, 2, 2)
        
        # 현재 등급 색상
        current_theme = get_theme(self.current_rank)
        current_color = QColor(current_theme['accent_color'])
        
        # 다음 등급 색상
        if self.next_rank:
            next_theme = get_theme(self.next_rank)
            next_color = QColor(next_theme['accent_color'])
        else:
            next_color = QColor("#7DD3FC")  # 기본 파란색
        
        # 진행도 계산
        if self.next_threshold and self.next_threshold > self.current_score:
            # 이전 등급의 임계값 찾기
            prev_threshold = 0
            if current_idx > 0:
                prev_rank = rank_order[current_idx - 1]
                thresholds = {
                    "BRONZE": 0,
                    "SILVER": 100,
                    "GOLD": 300,
                    "PLATINUM": 600,
                    "DIAMOND": 1000,
                    "MASTER": 2000,
                    "GRANDMASTER": 4000,
                    "CHALLENGER": 8000,
                    "LEGEND": 15000
                }
                prev_threshold = thresholds.get(prev_rank, 0)
            
            progress = (self.current_score - prev_threshold) / (self.next_threshold - prev_threshold)
            progress = max(0, min(1, progress))
        else:
            progress = 1.0
        
        # 진행 바 그리기 (현재 등급 색상)
        if progress > 0:
            progress_width = int(bar_width * progress)
            painter.setBrush(QBrush(current_color))
            painter.drawRoundedRect(bar_margin, bar_y - bar_height // 2, progress_width, bar_height, 2, 2)
        
        # 남은 점수 표시 (진행 바 위 중앙, 배경 없이)
        if self.next_threshold and self.next_threshold > self.current_score:
            points_needed = self.next_threshold - self.current_score
            points_text = f"{points_needed:,}점 남음"
            
            # 텍스트 크기 계산
            painter.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            text_rect = painter.fontMetrics().boundingRect(points_text)
            text_x = (width - text_rect.width()) // 2
            text_y = bar_y - bar_height // 2 - 15  # 삼각형과의 간격 조정
            
            # 텍스트만 그리기 (배경 없음, 다음 등급 색상)
            painter.setPen(QPen(next_color, 1))
            painter.drawText(text_x, text_y, points_text)
        
        # 등급 포인트 그리기
        point_radius = 12
        for i, rank in enumerate(display_ranks):
            x = bar_margin + int((bar_width / (num_ranks - 1)) * i) if num_ranks > 1 else bar_margin + bar_width // 2
            
            theme = get_theme(rank)
            rank_color = QColor(theme['accent_color'])
            
            # 현재 등급인지 확인
            is_current = (rank == self.current_rank)
            is_next = (rank == self.next_rank and rank != self.current_rank)
            
            # 원 그리기
            if is_current:
                # 현재 등급: 채워진 원 (금색)
                painter.setBrush(QBrush(current_color))
                painter.setPen(QPen(current_color, 2))
                painter.drawEllipse(x - point_radius, bar_y - point_radius, point_radius * 2, point_radius * 2)
                
                # 체크마크 그리기
                painter.setPen(QPen(QColor("#ECEFF4"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                check_size = 8
                painter.drawLine(x - check_size // 2, bar_y, x - check_size // 4, bar_y + check_size // 2)
                painter.drawLine(x - check_size // 4, bar_y + check_size // 2, x + check_size // 2, bar_y - check_size // 2)
                
                # 진행 바를 가리키는 삼각형 표시 (원 위쪽에 위치, 아래를 가리킴)
                triangle_size = 6
                triangle_points = [
                    QPoint(x, bar_y - point_radius),  # 삼각형의 꼭짓점 (아래를 가리킴)
                    QPoint(x - triangle_size, bar_y - point_radius - triangle_size),  # 왼쪽 위
                    QPoint(x + triangle_size, bar_y - point_radius - triangle_size)  # 오른쪽 위
                ]
                # 삼각형 채우기
                painter.setBrush(QBrush(current_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(triangle_points)
                # 삼각형 테두리 (얇은 테두리로 구분)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#ECEFF4"), 1))
                painter.drawPolygon(triangle_points)
                
            elif is_next:
                # 다음 등급: 파란색 테두리 원 (글로우 효과)
                glow_radius = point_radius + 4
                painter.setPen(Qt.PenStyle.NoPen)
                # 글로우 효과 (반투명 외곽)
                glow_color = QColor(next_color)
                glow_color.setAlpha(100)
                painter.setBrush(QBrush(glow_color))
                painter.drawEllipse(x - glow_radius, bar_y - glow_radius, glow_radius * 2, glow_radius * 2)
                
                # 메인 원 (흰색 중심, 파란색 테두리)
                painter.setBrush(QBrush(QColor("#ECEFF4")))
                painter.setPen(QPen(next_color, 3))
                painter.drawEllipse(x - point_radius, bar_y - point_radius, point_radius * 2, point_radius * 2)
                
            else:
                # 도달한 등급: 금색 테두리 원
                painter.setBrush(QBrush(QColor("#ECEFF4")))
                painter.setPen(QPen(current_color, 2))
                painter.drawEllipse(x - point_radius, bar_y - point_radius, point_radius * 2, point_radius * 2)
            
            # 등급 이름 표시
            rank_name = theme['name']
            painter.setPen(QPen(rank_color if is_next else current_color, 1))
            painter.setFont(QFont("Malgun Gothic", 10))
            text_rect = painter.fontMetrics().boundingRect(rank_name)
            # 등급 이름을 정확히 중앙 정렬
            text_x = x - text_rect.width() // 2
            text_y = bar_y + point_radius + 20
            painter.drawText(text_x, text_y, rank_name)

# ========================================================
# 통계 창
# ========================================================
class StatsWindow(QMainWindow):
    def __init__(self, session_manager, progression=None, log_handler=None):
        super().__init__()
        self.session_manager = session_manager
        self.progression = progression
        self.log_handler = log_handler  # 로그 핸들러 콜백
        self.setWindowTitle("통계 및 등급")
        self.setGeometry(150, 150, 600, 700)  # 너비 증가로 좌우 스크롤바 방지
        self.simple_mode = False  # 심플 모드 상태 초기화
        self._rank_sparkles = []
        
        # 실제 등급을 먼저 가져와서 설정
        try:
            stats = self.session_manager.get_statistics()
            self.current_rank = stats.get('rank', 'BRONZE')
        except Exception:
            self.current_rank = "BRONZE"
        
        self.update_window_style()
        self.init_ui()
        self.update_statistics()
    
    def log(self, message: str, msg_type: str = "INFO"):
        """로그 출력 (프로그램 내부 로그 모드로)"""
        if self.log_handler:
            self.log_handler(message, msg_type)
        else:
            print(f"[{msg_type}] {message}")
    
    def _get_next_rank_threshold(self, current_rank: str) -> int:
        """다음 등급까지 필요한 점수 반환"""
        thresholds = {
            "BRONZE": 100,
            "SILVER": 300,
            "GOLD": 600,
            "PLATINUM": 1000,
            "DIAMOND": 2000,
            "MASTER": 4000,
            "GRANDMASTER": 8000,
            "CHALLENGER": 15000,
            "LEGEND": None  # 최고 등급
        }
        return thresholds.get(current_rank)
    
    def _get_next_rank_name(self, current_rank: str) -> str:
        """다음 등급 이름 반환"""
        next_ranks = {
            "BRONZE": "실버",
            "SILVER": "골드",
            "GOLD": "플래티넘",
            "PLATINUM": "다이아몬드",
            "DIAMOND": "마스터",
            "MASTER": "그랜드마스터",
            "GRANDMASTER": "챌린저",
            "CHALLENGER": "레전드",
            "LEGEND": None
        }
        return next_ranks.get(current_rank, "")
    
    def update_window_style(self):
        """등급에 따라 창 스타일 업데이트 (포인트 색상만 변경)"""
        theme = get_theme(self.current_rank)
        self.setStyleSheet(f"""
            QMainWindow {{ 
                background-color: #2E3440;
            }}
            QLabel {{ 
                color: #ECEFF4; 
            }}
            QPushButton {{ 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme['accent_color']}, stop:1 {theme['border_color']});
                color: #2E3440; 
                padding: 8px; 
                border-radius: 5px; 
                border: 2px solid {theme['border_color']};
                font-weight: bold;
            }}
            QPushButton:hover {{ 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme['border_color']}, stop:1 {theme['accent_color']});
            }}
            QFrame {{ 
                background-color: rgba(59, 66, 82, 180); 
                border: 2px solid {theme['accent_color']};
                border-radius: 10px; 
                padding: 15px; 
                margin: 5px;
            }}
        """)
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 제목
        self.title_label = QLabel("통계 및 등급")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #88C0D0; margin: 10px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # 스크롤 영역 (스크롤바 숨김)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 좌우 스크롤바 숨김
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # 상하 스크롤바 숨김
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_widget.setLayout(scroll_layout)
        
        # 등급 표시 프레임
        self.rank_frame = QFrame()
        self.rank_frame.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #4C566A, stop:1 #3B4252); 
                border-radius: 15px; 
                padding: 20px; 
                margin: 10px;
            }
        """)
        rank_layout = QVBoxLayout()
        rank_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 전체 레이아웃 중앙 정렬
        rank_layout.setSpacing(10)  # 요소 간 간격
        self.rank_frame.setLayout(rank_layout)
        
        # 등급 이미지 라벨
        self.rank_image_label = QLabel()
        self.rank_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.rank_image_label.setFixedSize(200, 200)  # 크기 증가
        self.rank_image_label.setStyleSheet("background: transparent;")
        self.rank_image_label.setScaledContents(True)  # 이미지가 라벨 크기에 맞게 조정
        rank_layout.addWidget(self.rank_image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 티어 이름과 점수를 한 줄에 표시
        rank_info_layout = QHBoxLayout()
        rank_info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rank_label = QLabel("브론즈")
        self.rank_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #D08770;")
        self.rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.score_label = QLabel("0점")
        self.score_label.setStyleSheet("font-size: 20px; color: #ECEFF4; margin-left: 10px;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stage_label = QLabel("스테이지 1")
        self.stage_label.setStyleSheet("font-size: 18px; color: #A3BE8C; margin-left: 10px;")
        self.stage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        rank_info_layout.addWidget(self.rank_label)
        rank_info_layout.addWidget(self.score_label)
        rank_info_layout.addWidget(self.stage_label)
        rank_layout.addLayout(rank_info_layout)
        
        # 등급 진행 바
        self.rank_progress_bar = RankProgressBar("BRONZE", "SILVER", 0, 100)
        self.rank_progress_bar.setStyleSheet("background: transparent;")
        rank_layout.addWidget(self.rank_progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 점수 획득 방법 기준표
        score_info_text = "점수 획득 방법:\n• 집중 시간 1분 = 1점\n• 완료한 세션 1회 = 10점\n• 연속 일수 보너스 = 연속 일수 * 5점"
        self.rank_table_label = QLabel(score_info_text)
        self.rank_table_label.setStyleSheet("font-size: 11px; color: #81A1C1; margin-top: 10px; line-height: 1.5;")
        self.rank_table_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rank_table_label.setWordWrap(True)  # 긴 텍스트 줄바꿈
        rank_layout.addWidget(self.rank_table_label)
        
        scroll_layout.addWidget(self.rank_frame)
        
        # 통계 프레임
        stats_frame = QFrame()
        stats_layout = QGridLayout()
        stats_frame.setLayout(stats_layout)
        
        # 통계 라벨들
        self.total_sessions_label = QLabel("총 세션: 0회")
        self.total_focus_time_label = QLabel("총 집중 시간: 0시간")
        self.total_cycles_label = QLabel("완료한 사이클: 0회")
        self.completed_sessions_label = QLabel("완료한 세션: 0회")
        self.current_streak_label = QLabel("현재 연속 일수: 0일")
        self.longest_streak_label = QLabel("최장 연속 일수: 0일")
        
        stats_layout.addWidget(self.total_sessions_label, 0, 0)
        stats_layout.addWidget(self.total_focus_time_label, 0, 1)
        stats_layout.addWidget(self.total_cycles_label, 1, 0)
        stats_layout.addWidget(self.completed_sessions_label, 1, 1)
        stats_layout.addWidget(self.current_streak_label, 2, 0)
        stats_layout.addWidget(self.longest_streak_label, 2, 1)
        
        scroll_layout.addWidget(stats_frame)
        
        # 최근 세션 프레임
        recent_frame = QFrame()
        recent_layout = QVBoxLayout()
        recent_frame.setLayout(recent_layout)
        
        recent_title = QLabel("📝 최근 세션 기록")
        recent_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #88C0D0; margin-bottom: 10px;")
        recent_layout.addWidget(recent_title)
        
        self.recent_sessions_label = QTextEdit()
        self.recent_sessions_label.setReadOnly(True)
        self.recent_sessions_label.setStyleSheet("""
            QTextEdit { 
                background-color: #242933; 
                color: #ECEFF4; 
                border: 1px solid #4C566A; 
                border-radius: 5px; 
                padding: 10px; 
                font-size: 12px;
            }
        """)
        self.recent_sessions_label.setMaximumHeight(200)
        recent_layout.addWidget(self.recent_sessions_label)
        
        scroll_layout.addWidget(recent_frame)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # 새로고침 버튼
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.update_statistics)
        layout.addWidget(refresh_btn)
    
    def update_statistics(self):
        """통계 정보 업데이트"""
        try:
            stats = self.session_manager.get_statistics()
            self.log(f"통계 조회: 등급={stats.get('rank_display', 'N/A')}, 점수={stats.get('total_score', 0)}점", "INFO")
            
            # 등급 및 점수
            rank_code = stats.get('rank', 'BRONZE')
            if rank_code != self.current_rank:
                self.log(f"등급 변경: {self.current_rank} → {rank_code}", "INFO")
                self.current_rank = rank_code
                self.update_window_style()
        except Exception as e:
            self.log(f"통계 조회 오류: {e}", "ERROR")
            return
        
        theme = get_theme(rank_code)
        rank_display = stats['rank_display']
        
        # 제목 업데이트 (이모지 제거)
        self.title_label.setText(f"통계 및 등급 - {rank_display}")
        self.title_label.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {theme['accent_color']}; margin: 10px; "
            f"text-shadow: 0 0 3px {theme['accent_color']};"
        )
        
        # 등급 프레임 스타일 업데이트 (포인트 색상만)
        self.rank_frame.setStyleSheet(f"""
            QFrame {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #4C566A, stop:1 #3B4252);
                border: 3px solid {theme['accent_color']};
                border-radius: 15px; 
                padding: 20px; 
                margin: 10px;
            }}
        """)
        
        # 등급 이미지 업데이트
        try:
            image_file = theme.get("image", "bronze.webp")
            image_path = resource_path("images", image_file)
            
            # 파일 존재 확인
            if not os.path.exists(image_path):
                self.log(f"⚠️ 이미지 파일을 찾을 수 없습니다: {image_path}", "WARNING")
                # 절대 경로도 출력
                abs_path = os.path.abspath(image_path)
                self.log(f"   절대 경로: {abs_path}", "INFO")
                self.log(f"   리소스 디렉토리: {_resources_dir()}", "INFO")
                self.rank_image_label.clear()
                return
            
            # webp 형식 지원을 위해 Pillow 사용
            try:
                from PIL import Image
                from PIL.ImageQt import ImageQt
                
                # PIL로 이미지 로드
                pil_image = Image.open(image_path)
                # RGBA 모드로 변환 (투명도 지원)
                if pil_image.mode != 'RGBA':
                    pil_image = pil_image.convert('RGBA')
                
                # QImage로 변환
                qimage = ImageQt(pil_image)
                pixmap = QPixmap.fromImage(qimage)
                
                if not pixmap.isNull():
                    # 이미지를 200x200 크기로 조정 (라벨 크기에 맞춤)
                    scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.rank_image_label.setPixmap(scaled_pixmap)
                    self.rank_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    self.log(f"✅ 이미지 로드 성공: {image_file}", "SUCCESS")
                else:
                    self.log(f"❌ QPixmap 변환 실패: {image_path}", "ERROR")
                    self.rank_image_label.clear()
            except ImportError as ie:
                # Pillow가 없으면 기본 QPixmap 사용 (webp는 지원 안 될 수 있음)
                self.log(f"⚠️ Pillow가 설치되지 않음: {ie}", "WARNING")
                self.log("   pip install Pillow 를 실행하세요", "INFO")
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.rank_image_label.setPixmap(scaled_pixmap)
                    self.rank_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                    self.log(f"✅ 기본 로더로 이미지 로드 성공: {image_file}", "SUCCESS")
                else:
                    self.log(f"❌ 이미지 로드 실패 (webp 형식은 Pillow 필요): {image_path}", "ERROR")
                    self.rank_image_label.clear()
            except Exception as img_error:
                self.log(f"❌ 이미지 처리 오류: {img_error}", "ERROR")
                import traceback
                traceback.print_exc()
                self.rank_image_label.clear()
        except Exception as e:
            self.log(f"❌ 등급 이미지 로드 오류: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            self.rank_image_label.clear()
        
        # 티어 이름과 점수를 한 줄에 표시
        self.rank_label.setText(rank_display)  # 이모지 제거
        self.rank_label.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {theme['accent_color']}; "
            f"text-shadow: 0 0 5px {theme['accent_color']};"
        )
        self.score_label.setText(f"{stats['total_score']:,}점")
        self.score_label.setStyleSheet(f"font-size: 20px; color: #ECEFF4; margin-left: 10px;")

        # 스테이지 표시 (progression 있으면 사용)
        stage_text = "스테이지 정보 없음"
        try:
            if self.progression:
                snap = self.progression.snapshot()
                stage_text = f"스테이지 {snap.get('stage', 1)}"
        except Exception as e:
            self.log(f"스테이지 표시 오류: {e}", "WARNING")
        self.stage_label.setText(stage_text)
        
        # 티어별 반짝이는 효과 적용 (심플 모드가 아닐 때만)
        try:
            # 기존 효과 제거
            if hasattr(self, '_rank_sparkles') and self._rank_sparkles:
                for eff in self._rank_sparkles:
                    try:
                        eff.stop()
                    except Exception:
                        pass
            self._rank_sparkles = []
            if hasattr(self, '_rank_label_sparkle'):
                self._rank_label_sparkle.stop()
            
            # 심플 모드가 아닐 때만 반짝이는 효과 적용
            if not self.simple_mode:
                # 티어 색상으로 QColor 생성 (더 밝게)
                sparkle_color = hex_to_qcolor(theme['accent_color'], alpha=255)

                # 스테이지에 따라 애니메이션 강도 조절 (색상은 티어 유지)
                stage_level = 1
                try:
                    if self.progression:
                        stage_level = int(self.progression.snapshot().get("stage", 1))
                except Exception:
                    stage_level = 1
                stage_level = max(1, min(stage_level, 50))
                # 강도 계산
                img_min = 15 + stage_level // 2
                img_max = 30 + stage_level
                img_duration = max(900, 1600 - stage_level * 12)
                lbl_min = 8 + stage_level // 3
                lbl_max = 18 + stage_level // 1
                lbl_duration = max(1000, 1800 - stage_level * 10)
                
                # 티어 이미지에 한 개의 스파클 효과 적용 (원래 로직으로 회귀)
                eff = add_sparkle_effect(
                    self.rank_image_label,
                    sparkle_color,
                    min_blur=img_min,
                    max_blur=img_max,
                    duration=img_duration,
                    auto_start=True
                )
                self._rank_sparkles.append(eff)
                
                # 티어 라벨에 반짝이는 효과 (더 약한 효과)
                label_color = hex_to_qcolor(theme['accent_color'], alpha=200)
                self._rank_label_sparkle = add_sparkle_effect(
                    self.rank_label,
                    label_color,
                    min_blur=lbl_min,
                    max_blur=lbl_max,
                    duration=lbl_duration,
                    auto_start=True
                )
        except Exception as sparkle_error:
            # 반짝이는 효과 실패해도 계속 진행
            if hasattr(self, 'log'):
                self.log(f"반짝이는 효과 적용 오류: {sparkle_error}", "WARNING")
        
        # 다음 등급까지 남은 점수 계산 및 진행 바 업데이트
        current_score = stats['total_score']
        next_rank_threshold = self._get_next_rank_threshold(rank_code)
        next_rank_code = None
        if next_rank_threshold:
            next_rank_name = self._get_next_rank_name(rank_code)
            # 다음 등급 코드 찾기
            rank_order = ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER", "LEGEND"]
            try:
                current_idx = rank_order.index(rank_code)
                if current_idx < len(rank_order) - 1:
                    next_rank_code = rank_order[current_idx + 1]
            except ValueError:
                pass
        
        # 진행 바 업데이트
        if hasattr(self, 'rank_progress_bar'):
            if next_rank_code:
                self.rank_progress_bar.current_rank = rank_code
                self.rank_progress_bar.next_rank = next_rank_code
                self.rank_progress_bar.current_score = current_score
                self.rank_progress_bar.next_threshold = next_rank_threshold
            else:
                # 최고 등급인 경우
                self.rank_progress_bar.current_rank = rank_code
                self.rank_progress_bar.next_rank = None
                self.rank_progress_bar.current_score = current_score
                self.rank_progress_bar.next_threshold = None
            self.rank_progress_bar.update()  # 다시 그리기
        
        # 점수 획득 방법 기준표 업데이트
        score_info_text = "점수 획득 방법:\n• 집중 시간 1분 = 1점\n• 완료한 세션 1회 = 10점\n• 연속 일수 보너스 = 연속 일수 × 5점"
        self.rank_table_label.setText(score_info_text)
        self.rank_table_label.setStyleSheet("font-size: 11px; color: #81A1C1; margin-top: 10px; line-height: 1.5;")
        
        # 통계 정보
        self.total_sessions_label.setText(f"총 세션: {stats['total_sessions']}회")
        self.total_focus_time_label.setText(f"총 집중 시간: {stats['total_focus_hours']:.1f}시간")
        self.total_cycles_label.setText(f"완료한 사이클: {stats['total_cycles']}회")
        self.completed_sessions_label.setText(f"완료한 세션: {stats['completed_sessions']}회")
        self.current_streak_label.setText(f"현재 연속 일수: {stats['current_streak']}일")
        self.longest_streak_label.setText(f"최장 연속 일수: {stats['longest_streak']}일")
        
        # 최근 세션 기록
        recent_sessions = self.session_manager.get_recent_sessions(5)
        if recent_sessions:
            text = ""
            for session in recent_sessions:
                start_time = datetime.fromisoformat(session.get('start_time', ''))
                date_str = start_time.strftime("%Y-%m-%d %H:%M")
                focus_min = session.get('total_focus_minutes', 0)
                cycles = session.get('completed_cycles', 0)
                total_cycles = session.get('total_cycles', 0)
                status = "✅ 완료" if cycles == total_cycles else "⏸️ 중단"
                text += f"<b>{date_str}</b> - {focus_min}분 집중, {cycles}/{total_cycles} 사이클 {status}<br>"
            self.recent_sessions_label.setHtml(text)
        else:
            self.recent_sessions_label.setText("아직 세션 기록이 없습니다.")


# ========================================================
# 진행도/전투/상점 전용 창
# ========================================================
class BattleShopWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("전투 & 상점")
        self.setGeometry(180, 180, 520, 620)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        central.setLayout(layout)

        title = QLabel("🎮 진행도 / 상점 / 전투")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #88C0D0;")
        layout.addWidget(title)

        # 상태 라벨
        self.points_label = QLabel("포인트: 0p")
        self.scrolls_label = QLabel("강화 스크롤: 0장")
        self.stage_label = QLabel("스테이지: 1")
        self.power_label = QLabel("총 전투력: 0")
        self.next_req_label = QLabel("다음 스테이지 요구: 0")
        for lbl in [self.points_label, self.scrolls_label, self.stage_label, self.power_label, self.next_req_label]:
            lbl.setStyleSheet("color: #D8DEE9; font-size: 13px;")
            layout.addWidget(lbl)

        # 스크롤 구매
        buy_layout = QHBoxLayout()
        self.scroll_qty_input = QSpinBox()
        self.scroll_qty_input.setRange(1, 50)
        self.scroll_qty_input.setValue(1)
        self.scroll_qty_input.setSuffix(" 장")
        self.buy_scroll_btn = QPushButton("스크롤 구매 (40p)")
        self.buy_scroll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buy_layout.addWidget(self.scroll_qty_input)
        buy_layout.addWidget(self.buy_scroll_btn)
        layout.addLayout(buy_layout)

        # 강화 버튼
        enhance_layout = QGridLayout()
        enhance_layout.setSpacing(8)
        self.enhance_book_btn = QPushButton("책 강화")
        self.enhance_pencil_btn = QPushButton("연필 강화")
        self.enhance_laptop_btn = QPushButton("노트북 강화")
        for btn in [self.enhance_book_btn, self.enhance_pencil_btn, self.enhance_laptop_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # 장비 레이블 (강화 단계 표시)
        self.book_label = QLabel("책 +0")
        self.pencil_label = QLabel("연필 +0")
        self.laptop_label = QLabel("노트북 +0")
        for lbl in [self.book_label, self.pencil_label, self.laptop_label]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(46)
            lbl.setStyleSheet("background-color: #3B4252; color: #ECEFF4; border: 1px solid #4C566A; border-radius: 6px;")

        enhance_layout.addWidget(self.book_label, 0, 0)
        enhance_layout.addWidget(self.pencil_label, 0, 1)
        enhance_layout.addWidget(self.laptop_label, 0, 2)
        enhance_layout.addWidget(self.enhance_book_btn, 1, 0)
        enhance_layout.addWidget(self.enhance_pencil_btn, 1, 1)
        enhance_layout.addWidget(self.enhance_laptop_btn, 1, 2)
        layout.addLayout(enhance_layout)

        # 전투 영역
        battle_header = QLabel("⚔️ 스테이지 전투 (10타 수동 입력)")
        battle_header.setStyleSheet("font-weight: bold; color: #EBCB8B;")
        layout.addWidget(battle_header)

        self.damage_label = QLabel("")
        self.damage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.damage_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #BF616A;")
        layout.addWidget(self.damage_label)

        self.hp_bar = QProgressBar()
        self.hp_bar.setTextVisible(False)
        self.hp_bar.setFixedHeight(16)
        self.hp_bar.setRange(0, 100)
        self.hp_bar.setValue(100)
        self.hp_bar.setStyleSheet("""
            QProgressBar {
                background-color: #3B4252;
                border: 1px solid #4C566A;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #A3BE8C;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.hp_bar)

        self.remaining_hp_label = QLabel("남은 HP: 준비 중")
        self.remaining_hp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.remaining_hp_label.setStyleSheet("color: #ECEFF4; font-size: 12px;")
        layout.addWidget(self.remaining_hp_label)

        self.stage_attack_btn = QPushButton("한 번 타격")
        self.stage_attack_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.stage_attack_btn)

        # 테스트 모드: 포인트 지급
        test_layout = QHBoxLayout()
        self.test_points_input = QSpinBox()
        self.test_points_input.setRange(1, 100000)
        self.test_points_input.setValue(100)
        self.test_points_input.setSuffix(" p")
        self.add_points_btn = QPushButton("포인트 지급")
        self.add_points_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_points_btn.setEnabled(False)
        test_layout.addWidget(self.test_points_input)
        test_layout.addWidget(self.add_points_btn)
        layout.addLayout(test_layout)

        self.battle_log = QTextEdit()
        self.battle_log.setReadOnly(True)
        self.battle_log.setStyleSheet("background-color: #242933; color: #ECEFF4; border: 1px solid #4C566A; border-radius: 5px;")
        self.battle_log.setMaximumHeight(200)
        layout.addWidget(self.battle_log)

        layout.addStretch()
        self._sparkles = {}

        # 전체 오버레이 이펙트
        self.overlay = QLabel(self)
        self.overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overlay.setStyleSheet("background: rgba(0,0,0,0.6); color: white; font-size: 32px; font-weight: bold;")
        self.overlay.hide()
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.overlay_effect = QGraphicsOpacityEffect(self.overlay)
        self.overlay.setGraphicsEffect(self.overlay_effect)
        self.overlay_anim = QPropertyAnimation(self.overlay_effect, b"opacity", self)
        self.overlay_anim.setDuration(1400)  # 살짝 더 길게 표시
        self.overlay_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def update_state(self, snap: dict):
        self.points_label.setText(f"포인트: {snap.get('points', 0)}p")
        self.scrolls_label.setText(f"강화 스크롤: {snap.get('scrolls', 0)}장")
        self.stage_label.setText(f"스테이지: {snap.get('stage', 1)}")
        self.power_label.setText(f"총 전투력: {snap.get('total_power', 0)}")
        self.next_req_label.setText(f"다음 스테이지 요구: {snap.get('next_stage_requirement', 0)}")

    def set_remaining_hp(self, remaining: float, hp: float, hits_used: int, limit: int):
        try:
            if hp <= 0:
                self.hp_bar.setRange(0, 1)
                self.hp_bar.setValue(0)
            else:
                scale = 10
                self.hp_bar.setRange(0, int(hp * scale))
                self.hp_bar.setValue(max(0, int(remaining * scale)))
            self.remaining_hp_label.setText(f"남은 HP: {max(0, round(remaining,1))} / {hp} (타격 {hits_used}/{limit})")
        except Exception:
            self.remaining_hp_label.setText("남은 HP: -")

    def show_damage(self, dmg: float, remaining: float, finished: bool, success: bool):
        color = "#A3BE8C" if success else "#EBCB8B"
        self.damage_label.setText(f"-{dmg}")
        self.damage_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        self.remaining_hp_label.setText(f"남은 HP: {max(0, round(remaining, 1))}")
        # 잠깐 표시 후 흐려짐
        QTimer.singleShot(700, lambda: self.damage_label.setText("" if finished else self.damage_label.text()))

    def append_battle_log(self, text: str):
        self.battle_log.append(text)
        scrollbar = self.battle_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_battle_log_colored(self, text: str, color: str):
        self.battle_log.append(f"<span style='color:{color}'>{text}</span>")
        scrollbar = self.battle_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_battle_log(self):
        self.battle_log.clear()

    def set_test_mode(self, enabled: bool):
        self.add_points_btn.setEnabled(enabled)
        self.test_points_input.setEnabled(enabled)
        self.add_points_btn.setVisible(enabled)
        self.test_points_input.setVisible(enabled)

    def play_enhance_effect(self, kind: str):
        """
        kind: success | fail | down
        """
        colors = {
            "success": ("#16A34A", "✨ 강화 성공!"),
            "fail": ("#EF4444", "❌ 실패"),
            "down": ("#F59E0B", "⚠️ 하락"),
        }
        color, text = colors.get(kind, ("#81A1C1", ""))
        self.overlay.setText(text)
        self.overlay.setStyleSheet(
            f"background: rgba(0,0,0,0.5); color: {color}; font-size: 32px; font-weight: bold;"
        )
        self.overlay.raise_()
        self.overlay.setGeometry(self.rect())
        self.overlay.show()
        self.overlay_effect.setOpacity(0.0)
        self.overlay_anim.stop()
        self.overlay_anim.setStartValue(1.0)
        self.overlay_anim.setEndValue(0.0)
        self.overlay_anim.finished.connect(self.overlay.hide)
        self.overlay_anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "overlay"):
            self.overlay.setGeometry(self.rect())

    def update_equipment(self, snap: dict):
        inv = snap.get("inventory", {})
        mapping = [
            ("book", self.book_label, "책"),
            ("pencil", self.pencil_label, "연필"),
            ("laptop", self.laptop_label, "노트북"),
        ]
        for slot, lbl, name in mapping:
            data = inv.get(slot, {})
            level = data.get("level", 0)
            power = data.get("power", 0)
            lbl.setText(f"{name} +{level} (PWR {power})")
            color = "#81A1C1"
            if level >= 8:
                color = "#F472B6"
            elif level >= 5:
                color = "#FBBF24"
            elif level >= 2:
                color = "#A3BE8C"
            lbl.setStyleSheet(
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #3B4252, stop:1 #2E3440);"
                f"color: #ECEFF4; border: 2px solid {color}; border-radius: 8px; padding: 4px;"
                f"font-weight: bold;"
            )
            # 반짝이 효과 강도 레벨별
            if slot in self._sparkles and self._sparkles[slot]:
                try:
                    self._sparkles[slot].stop()
                except Exception:
                    pass
            sparkle_color = hex_to_qcolor(color, alpha=200)
            blur_min = 10 + level * 2
            blur_max = 25 + level * 3
            duration = max(800, 1500 - level * 50)
            try:
                self._sparkles[slot] = add_sparkle_effect(
                    lbl,
                    sparkle_color,
                    min_blur=blur_min,
                    max_blur=blur_max,
                    duration=duration,
                    auto_start=True,
                )
            except Exception:
                self._sparkles[slot] = None
# ========================================================
# 메인 UI 클래스
# ========================================================
class StudyWithUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study With - Focus Timer")
        self.setGeometry(100, 100, 450, 750)
        self.current_rank = "BRONZE"  # 기본 등급
        self.simple_mode = False  # 심플 모드 상태
        self.setStyleSheet(self.get_style())
        self.init_ui()
    
    def update_rank_style(self, rank: str):
        """등급에 따라 메인 창 스타일 업데이트"""
        try:
            self.current_rank = rank
            # 심플 모드일 때는 기본 스타일 사용
            if self.simple_mode:
                self.setStyleSheet(get_default_style())
            else:
                self.setStyleSheet(get_main_window_style(rank))
            # 제목에 등급 이모지 추가
            theme = get_theme(rank)
            if hasattr(self, 'title_label') and self.title_label:
                self.title_label.setText("Study With")  # 이모지 제거
        except Exception as e:
            # StudyWithUI는 로그 핸들러가 없으므로 print 사용 (app.py에서 처리)
            print(f"스타일 업데이트 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_simple_mode(self, state):
        """심플 모드 토글"""
        self.simple_mode = (state == 2)  # 2 = Qt.CheckState.Checked
        # 현재 등급에 따라 스타일 업데이트
        self.update_rank_style(self.current_rank)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # 1. 헤더 (제목 + PIP 버튼)
        header_layout = QHBoxLayout()
        
        # [수정됨] 제목은 한 번만 추가
        self.title_label = QLabel("Study With")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_label)

        self.pip_btn = QPushButton("📺 PIP 모드")
        self.pip_btn.setObjectName("PipBtn")
        self.pip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pip_btn.setToolTip("작은 화면으로 전환")
        self.pip_btn.setFixedHeight(30) 
        header_layout.addWidget(self.pip_btn)

        # [수정됨] 핀 버튼 제거 (PIP 모드가 그 역할을 대신함)
        # 만약 핀 버튼도 같이 쓰고 싶다면 아래 주석을 해제하세요.
        # self.pin_btn = QPushButton("📌")
        # self.pin_btn.setObjectName("PinBtn")
        # self.pin_btn.setCheckable(True)
        # self.pin_btn.setFixedSize(40, 40)
        # header_layout.addWidget(self.pin_btn)

        layout.addLayout(header_layout)

        # 2. 타이머
        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("TimerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)

        self.status_label = QLabel("준비 상태")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # 3. 설정 입력
        settings_frame = QFrame()
        settings_frame.setObjectName("SettingsFrame")
        form_layout = QFormLayout()
        
        self.focus_input = QSpinBox()
        self.focus_input.setRange(1, 180)
        self.focus_input.setValue(40)
        self.focus_input.setSuffix(" 분")

        self.break_input = QSpinBox()
        self.break_input.setRange(1, 60)
        self.break_input.setValue(20)
        self.break_input.setSuffix(" 분")

        self.cycle_input = QSpinBox()
        self.cycle_input.setRange(1, 10)
        self.cycle_input.setValue(3)
        self.cycle_input.setSuffix(" 회")

        form_layout.addRow("🔥 집중 시간:", self.focus_input)
        form_layout.addRow("☕ 휴식 시간:", self.break_input)
        form_layout.addRow("🔄 반복 횟수:", self.cycle_input)
        settings_frame.setLayout(form_layout)
        layout.addWidget(settings_frame)

        # 4. 차단 목록
        layout.addWidget(QLabel("🚫 차단할 웹사이트 (키워드 차단)"))
        self.site_input = QLineEdit()
        self.site_input.setPlaceholderText("예: youtube")
        layout.addWidget(self.site_input)

        layout.addWidget(QLabel("🚫 차단할 프로그램 (키워드 차단)"))
        self.app_input = QLineEdit()
        self.app_input.setPlaceholderText("예: KakaoTalk")
        layout.addWidget(self.app_input)

        # --- 프리셋 저장/로드 버튼 ---
        preset_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("📂 프리셋 불러오기")
        self.load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_btn.setStyleSheet("background-color: #4C566A; color: white; padding: 8px;")
        
        self.save_btn = QPushButton("💾 프리셋 저장")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("background-color: #434C5E; color: white; padding: 8px;")

        preset_layout.addWidget(self.load_btn)
        preset_layout.addWidget(self.save_btn)
        layout.addLayout(preset_layout)
        
        # 통계 버튼
        self.stats_btn = QPushButton("통계 및 등급 보기")
        self.stats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stats_btn.setStyleSheet("background-color: #5E81AC; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(self.stats_btn)

        # 진행도/전투/상점 전용 창 열기
        self.open_battle_shop_btn = QPushButton("🎮 전투·상점 창 열기")
        self.open_battle_shop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_battle_shop_btn.setStyleSheet("background-color: #4C566A; color: white; padding: 10px; font-weight: bold;")
        layout.addWidget(self.open_battle_shop_btn)

        layout.addStretch()

        # 5. 심플 모드 및 로그
        self.simple_mode_check = QCheckBox("🎨 심플 모드")
        self.simple_mode_check.setStyleSheet("color: #D8DEE9; margin-top: 10px;")
        layout.addWidget(self.simple_mode_check)
        
        self.log_check = QCheckBox("🛠️ 로그 모드 활성화")
        self.log_check.setStyleSheet("color: #D8DEE9; margin-top: 10px;")
        layout.addWidget(self.log_check)

        self.test_mode_check = QCheckBox("🧪 테스트 모드 (포인트 임의 지급)")
        self.test_mode_check.setStyleSheet("color: #EBCB8B; margin-top: 4px;")
        layout.addWidget(self.test_mode_check)

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setObjectName("LogViewer")
        self.log_viewer.setVisible(False)
        layout.addWidget(self.log_viewer)

        self.start_btn = QPushButton("세션 시작")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.start_btn)

    def append_log_ui(self, message, msg_type="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = "#ECEFF4"
        if msg_type == "ERROR": color = "#BF616A"
        elif msg_type == "SUCCESS": color = "#A3BE8C"
        elif msg_type == "WARNING": color = "#EBCB8B"
        
        self.log_viewer.append(f"<span style='color:#81A1C1'>[{timestamp}]</span> <span style='color:{color}'><b>[{msg_type}]</b> {message}</span>")
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def disable_inputs(self, disable):
        self.focus_input.setDisabled(disable)
        self.break_input.setDisabled(disable)
        self.cycle_input.setDisabled(disable)
        self.site_input.setDisabled(disable)
        self.app_input.setDisabled(disable)

    def get_style(self):
        """기본 스타일 반환 (심플 모드면 기본 스타일, 아니면 등급별 스타일)"""
        if self.simple_mode:
            return get_default_style()
        return get_main_window_style(self.current_rank)