# ui.py
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QSpinBox, QFormLayout, 
                             QFrame, QCheckBox, QTextEdit, QMessageBox,QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime

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

        # 1. 헤더
        header_layout = QHBoxLayout()
        
        # 1. 제목 라벨
        title_label = QLabel("Study With")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)

        # 2. 항상 위에 고정 버튼 (핀 아이콘)
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setObjectName("PinBtn")
        self.pin_btn.setCheckable(True) # 눌린 상태 유지 가능하게 설정
        self.pin_btn.setFixedSize(40, 40) # 정사각형 작은 버튼
        self.pin_btn.setToolTip("창을 맨 앞에 고정")
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(self.pin_btn)

        # 헤더 레이아웃을 메인 레이아웃에 추가
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

        # --- [NEW] 프리셋 저장/로드 버튼 ---
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
        # --------------------------------

        layout.addStretch()
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

    # UI 관련 기능 (로그 표시, 입력창 잠금 등)은 여기에 둡니다.
    def append_log_ui(self, message, msg_type="INFO"):
        """로그 텍스트를 화면에 추가하는 UI 메서드"""
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
            /* [NEW] 전체 폰트 일괄 적용 (원하는 폰트 이름으로 변경 가능) */
            * {
                font-family: ;
                font-size: 14px;
            }

            QMainWindow { background-color: #2E3440; }
            
            /* QLabel에서 font-family를 따로 지정하지 않으면 위에서 설정한 전체 폰트를 따릅니다. */
            QLabel { 
                color: #ECEFF4; 
                /* font-family: 'Segoe UI', sans-serif;  <-- 이 줄을 지우거나 주석 처리하면 전체 폰트를 따라갑니다. */
            }

            #TitleLabel { 
                font-size: 24px; 
                font-weight: bold; 
                margin-top: 10px; 
                color: #88C0D0; 
                /* font-family: 'Impact'; <-- 제목만 다른 폰트를 쓰고 싶다면 여기서 지정 */
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
                /* font-family: 'Consolas'; <-- 입력창만 고정폭 글꼴을 쓰고 싶다면 지정 */
            }
            
            QCheckBox { color: #ECEFF4; spacing: 5px; }
            
            QTextEdit#LogViewer { 
                background-color: #242933; 
                color: #ECEFF4; 
                border: 1px solid #4C566A; 
                border-radius: 5px; 
                padding: 5px; 
                font-family: 'Consolas', monospace; /* 로그창은 고정폭 글꼴 추천 */
                font-size: 12px; 
            }
            
            QPushButton#StartBtn { background-color: #5E81AC; color: white; font-size: 18px; font-weight: bold; padding: 15px; border-radius: 10px; margin: 10px; }
            QPushButton#StartBtn:hover { background-color: #81A1C1; }
            
            QPushButton#PinBtn { 
                background-color: transparent; 
                border: 2px solid #4C566A; 
                border-radius: 20px; 
                font-size: 16px;
                color: #4C566A; 
            }
            QPushButton#PinBtn:checked { 
                background-color: #EBCB8B; 
                border: 2px solid #EBCB8B; 
                color: #2E3440;
            }
            """