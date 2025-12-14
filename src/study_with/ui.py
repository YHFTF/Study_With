# ui.py
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QSpinBox, QFormLayout, 
                             QFrame, QCheckBox, QTextEdit, QMessageBox, QHBoxLayout)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QMouseEvent
from datetime import datetime

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

        self.init_ui()

    def init_ui(self):
        # 메인 컨테이너 (둥근 모서리 배경용)
        container = QFrame(self)
        container.setGeometry(0, 0, 220, 100)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(46, 52, 64, 240); /* 약간 투명한 어두운 배경 */
                border-radius: 15px;
                border: 2px solid #4C566A;
            }
            QLabel { color: #ECEFF4; font-family: 'Segoe UI', sans-serif; border: none; background: transparent; }
        """)
        
        layout = QVBoxLayout(container)
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
# 메인 UI 클래스
# ========================================================
class StudyWithUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study With - Focus Timer")
        self.setGeometry(100, 100, 450, 750)
        self.setStyleSheet(self.get_style())
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # 1. 헤더 (제목 + PIP 버튼)
        header_layout = QHBoxLayout()
        
        # [수정됨] 제목은 한 번만 추가
        title_label = QLabel("Study With")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)

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

        layout.addStretch()

        # 5. 로그 및 버튼
        self.log_check = QCheckBox("🛠️ 로그 모드 활성화")
        self.log_check.setStyleSheet("color: #D8DEE9; margin-top: 10px;")
        layout.addWidget(self.log_check)

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
        return """
        /* [수정됨] 폰트 지정. 없으면 시스템 기본값 */
        * {
            font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            font-size: 14px;
        }

        QMainWindow { background-color: #2E3440; }
        
        QLabel { 
            color: #ECEFF4; 
        }

        #TitleLabel { 
            font-size: 24px; 
            font-weight: bold; 
            margin-top: 10px; 
            color: #88C0D0; 
        }
        
        #TimerLabel { font-size: 70px; font-weight: bold; color: #ECEFF4; margin: 10px 0; }
        #StatusLabel { font-size: 18px; margin-bottom: 20px; }
        QFrame#SettingsFrame { background-color: #3B4252; border-radius: 10px; padding: 10px; margin: 10px; }
        
        QLineEdit, QSpinBox { 
            background-color: #4C566A; 
            color: white; 
            border: 1px solid #434C5E; 
            padding: 5px; 
            border-radius: 5px; 
        }
        
        QCheckBox { color: #ECEFF4; spacing: 5px; }
        
        QTextEdit#LogViewer { 
            background-color: #242933; 
            color: #ECEFF4; 
            border: 1px solid #4C566A; 
            border-radius: 5px; 
            padding: 5px; 
            font-family: 'Consolas', monospace; 
            font-size: 12px; 
        }
        
        QPushButton#StartBtn { background-color: #5E81AC; color: white; font-size: 18px; font-weight: bold; padding: 15px; border-radius: 10px; margin: 10px; }
        QPushButton#StartBtn:hover { background-color: #81A1C1; }
        
        QPushButton#PipBtn { 
            background-color: #4C566A; 
            border: 1px solid #5E81AC; 
            border-radius: 5px; 
            color: #ECEFF4;
            padding: 5px 10px;
            font-size: 12px;
        }
        QPushButton#PipBtn:hover { background-color: #5E81AC; }
        """