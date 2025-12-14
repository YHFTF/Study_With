# main.py
import sys
import os
import time
import psutil
import platform
import ctypes
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFontDatabase, QFont

# Flask 관련 (확장 프로그램 연동용)
from flask import Flask, jsonify
from flask_cors import CORS

# ★ 분리한 UI 파일 불러오기
from ui import StudyWithUI

#PyInstaller 경로 호환 함수
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ---------------------------------------------------------
# [로직 1] 관리자 권한 체크
# ---------------------------------------------------------
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:])
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)
    except Exception: pass

# ---------------------------------------------------------
# [로직 2] 백그라운드 스레드들 (Flask API, 프로세스 차단기)
# ---------------------------------------------------------
class ApiServerThread(QThread):
    def __init__(self):
        super().__init__()
        self.app = Flask(__name__)
        CORS(self.app)
        self.port = 5000
        self.is_blocking = False
        self.block_sites = []

        @self.app.route('/status')
        def get_status():
            return jsonify({"blocking": self.is_blocking, "sites": self.block_sites})

    def run(self):
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self.app.run(port=self.port, use_reloader=False)

    def update_state(self, blocking, sites):
        self.is_blocking = blocking
        self.block_sites = sites

class BlockerWorker(QThread):
    log_signal = pyqtSignal(str, str) 

    def __init__(self, block_keywords):
        super().__init__()
        self.running = True
        # 대소문자 구분 없이 비교하기 위해 미리 소문자로 변환
        self.block_keywords = [k.lower().strip() for k in block_keywords if k.strip()]
        
        # [중요] 절대 종료하면 안 되는 시스템 필수 프로세스 목록 (화이트리스트)
        self.safe_list = [
            'windows', 'system', 'svchost.exe', 'explorer.exe', 
            'winlogon.exe', 'csrss.exe', 'services.exe', 'lsass.exe',
            'dwm.exe', 'smss.exe', 'taskmgr.exe', 'spoolsv.exe',
            'python.exe', 'pythonw.exe', 'pycharm', 'code' # 개발 도구 포함
        ]

    def run(self):
        if self.block_keywords:
            self.log_signal.emit(f"프로그램 감시 중 (키워드: {', '.join(self.block_keywords)})", "INFO")
        
        while self.running:
            if self.block_keywords:
                # 현재 실행 중인 모든 프로세스 순회
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        # 프로세스 이름 가져오기
                        proc_name = proc.info['name']
                        if not proc_name: continue
                        
                        proc_name_lower = proc_name.lower()

                        # 1. 안전 리스트에 있는 파일은 절대 건드리지 않음
                        is_safe = False
                        for safe_item in self.safe_list:
                            if safe_item in proc_name_lower:
                                is_safe = True
                                break
                        if is_safe:
                            continue

                        # 2. 차단 키워드가 프로세스 이름에 '포함'되어 있는지 확인
                        for keyword in self.block_keywords:
                            if keyword in proc_name_lower:
                                proc.kill() # 강제 종료
                                self.log_signal.emit(f"🚫 프로그램 차단됨: {proc_name} ('{keyword}' 포함)", "SUCCESS")
                                break # 한 번 죽였으면 다음 프로세스로 넘어감

                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        # 이미 종료되었거나 권한이 없는 시스템 프로세스는 무시
                        pass
                    except Exception as e:
                        # self.log_signal.emit(f"오류: {e}", "ERROR") 
                        pass
                        
            time.sleep(1) # 1초마다 검사

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# ---------------------------------------------------------
# [메인 로직] UI와 기능을 연결하는 컨트롤러
# ---------------------------------------------------------
class StudyWithLogic(StudyWithUI):
    def __init__(self):
        super().__init__() # UI 초기화 (ui.py의 init_ui 실행됨)
        
        # 상태 변수 초기화
        self.is_running = False
        self.log_mode = False
        self.current_state = "READY"
        self.time_left = 0
        self.total_cycles = 0
        self.current_cycle = 0
        self.current_sites = []
        self.current_apps = []
        
        self.blocker_thread = None
        
        # API 서버 즉시 시작 (확장 프로그램 통신용)
        self.api_server = ApiServerThread()
        self.api_server.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.pin_btn.clicked.connect(self.toggle_pin)

        # ★ UI 이벤트 연결 (버튼 클릭 등)
        self.start_btn.clicked.connect(self.toggle_session)
        self.save_btn.clicked.connect(self.save_preset)
        self.load_btn.clicked.connect(self.load_preset)
        self.log_check.stateChanged.connect(self.toggle_log_mode)

        # 시작 시 block_list 폴더가 없으면 생성
        self.preset_dir = os.path.join(os.getcwd(), "block_list")
        os.makedirs(self.preset_dir, exist_ok=True)

    # --- 프리셋 저장 기능 ---
    def save_preset(self):
        sites = self.site_input.text()
        apps = self.app_input.text()

        if not sites and not apps:
            QMessageBox.warning(self, "경고", "저장할 내용이 없습니다.")
            return

        # 파일 저장 대화상자 열기
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "프리셋 저장", 
            self.preset_dir, 
            "Text Files (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("[SITES]\n")
                    f.write(sites + "\n\n")
                    f.write("[APPS]\n")
                    f.write(apps + "\n")
                self.handle_log(f"💾 프리셋 저장 완료: {os.path.basename(file_path)}", "SUCCESS")
                QMessageBox.information(self, "성공", "프리셋이 저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"저장 실패: {e}")

    # --- 프리셋 불러오기 기능 ---
    def load_preset(self):
        # 파일 열기 대화상자 열기
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "프리셋 불러오기", 
            self.preset_dir, 
            "Text Files (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 내용 파싱 (간단한 섹션 구분)
                sites_text = ""
                apps_text = ""
                
                # [SITES] 섹션 찾기
                if "[SITES]" in content:
                    parts = content.split("[SITES]")[1].split("[APPS]")
                    sites_text = parts[0].strip()
                    if len(parts) > 1:
                        apps_text = parts[1].strip()
                elif "[APPS]" in content: # APPS만 있는 경우
                    apps_text = content.split("[APPS]")[1].strip()
                
                # UI에 반영
                self.site_input.setText(sites_text)
                self.app_input.setText(apps_text)
                
                self.handle_log(f"📂 프리셋 로드 완료: {os.path.basename(file_path)}", "INFO")
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"불러오기 실패: {e}")
        
    # --- 맨 앞 고정 기능 구현 ---
    def toggle_pin(self):
        # 버튼이 눌린 상태(Checked)인지 확인
        is_on_top = self.pin_btn.isChecked()

        # 현재 윈도우 플래그 가져오기
        current_flags = self.windowFlags()

        if is_on_top:
            # [설정] 맨 위 고정 플래그 추가
            self.setWindowFlags(current_flags | Qt.WindowType.WindowStaysOnTopHint)
            self.handle_log("📌 오버레이 모드 ON: 창이 맨 위에 고정됩니다.", "INFO")
        else:
            # [해제] 맨 위 고정 플래그 제거
            self.setWindowFlags(current_flags & ~Qt.WindowType.WindowStaysOnTopHint)
            self.handle_log("📌 오버레이 모드 OFF: 고정이 해제되었습니다.", "INFO")
        
        # ★ 중요: 플래그 변경 후에는 반드시 show()를 다시 호출해야 적용됨
        self.show()
    
    # --- 로직 메서드 구현 ---
    
    def toggle_log_mode(self, state):
        self.log_mode = (state == 2)
        self.log_viewer.setVisible(self.log_mode)

    def handle_log(self, message, msg_type="INFO"):
        """로그 발생 시 처리"""
        if self.log_mode:
            self.append_log_ui(message, msg_type)

    def toggle_session(self):
        if not self.is_running: self.start_session()
        else: self.stop_session()

    def enable_blocking(self):
        """차단 기능을 활성화합니다."""
        self.api_server.update_state(True, self.current_sites)
        
        if self.blocker_thread is None or not self.blocker_thread.isRunning():
            self.blocker_thread = BlockerWorker(self.current_apps)
            self.blocker_thread.log_signal.connect(self.handle_log)
            self.blocker_thread.start()
        self.handle_log("🛡️ 차단 기능이 활성화되었습니다.", "INFO")

    def disable_blocking(self):
        """차단 기능을 비활성화합니다."""
        self.api_server.update_state(False, [])
        
        if self.blocker_thread:
            self.blocker_thread.stop()
            self.blocker_thread = None
        self.handle_log("🔓 차단 기능이 일시 해제되었습니다.", "INFO")

    def start_session(self):
            # 1. 입력값 저장 (세션 동안 계속 쓰기 위해)
            self.current_sites = [s.strip() for s in self.site_input.text().split(',') if s.strip()]
            self.current_apps = [a.strip() for a in self.app_input.text().split(',') if a.strip()]

            # 2. 상태 초기화
            self.is_running = True
            self.current_cycle = 1
            self.total_cycles = self.cycle_input.value()
            
            self.start_btn.setText("세션 중지")
            self.start_btn.setStyleSheet("background-color: #BF616A; color: white;")
            self.disable_inputs(True)
            
            self.handle_log(f"세션 시작 (총 {self.total_cycles} 사이클)", "INFO")
            
            # 3. 바로 집중 모드로 진입
            self.enter_focus_mode()

    def stop_session(self):
        self.timer.stop()
        self.is_running = False
        self.disable_blocking()

        self.current_state = "READY"
        self.timer_label.setText("00:00")
        self.status_label.setText("준비 상태")
        self.start_btn.setText("세션 시작")
        self.start_btn.setStyleSheet("")
        self.disable_inputs(False)
        self.handle_log("세션이 중지되었습니다.", "WARNING")

    def enter_focus_mode(self):
        self.current_state = "FOCUS"
        self.time_left = self.focus_input.value() * 60
        self.status_label.setText(f"🔥 집중 중 ({self.current_cycle}/{self.total_cycles})")
        self.status_label.setStyleSheet("color: #D08770; font-weight: bold;")
        self.enable_blocking()
        self.timer.start(1000)
        self.handle_log(f"🔥 집중 모드 시작 (Cycle {self.current_cycle})", "INFO")

    def enter_break_mode(self):
        self.current_state = "BREAK"
        self.time_left = self.break_input.value() * 60
        self.status_label.setText(f"☕ 휴식 시간 ({self.current_cycle}/{self.total_cycles})")
        self.status_label.setStyleSheet("color: #A3BE8C; font-weight: bold;")
        self.disable_blocking()
        self.timer.start(1000)
        self.handle_log(f"☕ 휴식 모드 시작 (Cycle {self.current_cycle})", "INFO")

    def update_timer(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.timer_label.setText(f"{minutes:02}:{seconds:02}")

        if self.time_left > 0:
            self.time_left -= 1
        else:
            self.timer.stop()
            if self.current_state == "FOCUS":
                if self.current_cycle >= self.total_cycles:
                    self.finish_all_sessions()
                else:
                    self.enter_break_mode()
            elif self.current_state == "BREAK":
                self.current_cycle += 1
                self.enter_focus_mode()

    def finish_all_sessions(self):
        self.handle_log("모든 세션 완료!", "SUCCESS")
        self.stop_session()
        QMessageBox.information(self, "완료", "모든 집중 세션을 완료했습니다! 🎉")

if __name__ == '__main__':
    if not is_admin():
        run_as_admin()
    
    app = QApplication(sys.argv)
    font_id = QFontDatabase.addApplicationFont("font.ttf") 
    
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        # 앱 전체 기본 폰트로 설정
        app.setFont(QFont(font_family, 10)) 
        print(f"폰트 로드 성공: {font_family}")
    else:
        print("폰트 파일을 찾을 수 없거나 로드 실패 (기본 폰트 사용)")
    window = StudyWithLogic() # 로직 클래스 실행
    window.show()
    sys.exit(app.exec())