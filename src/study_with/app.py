from __future__ import annotations

import ctypes
import os
import platform
import random
import shutil
import sys
import time
from pathlib import Path

import psutil
from PyQt6.QtCore import QThread, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .ui import PipUI, StudyWithUI

# Flask 관련 (확장 프로그램 연동용)
from flask import Flask, jsonify
from flask_cors import CORS

def _resources_dir() -> Path:
    """
    Return the directory containing packaged resources.

    - Dev: <repo>/src/study_with/resources
    - PyInstaller: <_MEIPASS>/resources (when collected as data)
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "resources"
    return Path(__file__).resolve().parent / "resources"


def resource_path(*relative_parts: str) -> str:
    """Build an absolute path to a resource file."""
    return str(_resources_dir().joinpath(*relative_parts))


def _default_preset_dir() -> Path:
    # Backward-compat: if a legacy ./block_list exists, keep using it.
    legacy = Path.cwd() / "block_list"
    if legacy.exists():
        legacy.mkdir(parents=True, exist_ok=True)
        return legacy

    override = os.getenv("STUDY_WITH_PRESET_DIR")
    if override:
        p = Path(override).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        preset_dir = base / "StudyWith" / "presets"
    elif system == "Darwin":
        preset_dir = Path.home() / "Library" / "Application Support" / "StudyWith" / "presets"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
        preset_dir = base / "study-with" / "presets"

    preset_dir.mkdir(parents=True, exist_ok=True)
    return preset_dir


def _ensure_default_preset(preset_dir: Path) -> None:
    """Copy the bundled Default preset if the directory is empty."""
    try:
        has_any_txt = any(p.suffix.lower() == ".txt" for p in preset_dir.iterdir() if p.is_file())
    except Exception:
        return

    if has_any_txt:
        return

    bundled = Path(resource_path("presets", "Default.txt"))
    if bundled.exists():
        try:
            shutil.copy2(bundled, preset_dir / "Default.txt")
        except Exception:
            pass

# ---------------------------------------------------------
# [로직 1] 관리자 권한 체크
# ---------------------------------------------------------
def is_admin():
    system = platform.system()
    if system == "Windows":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    # POSIX: root == 0
    try:
        return os.geteuid() == 0  # type: ignore[attr-defined]
    except Exception:
        return False

def run_as_admin():
    # Only Windows supports ShellExecute "runas" here.
    if platform.system() != "Windows":
        return

    script = os.path.abspath(sys.argv[0])
    params = " ".join([script] + sys.argv[1:])
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)
    except Exception:
        pass

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
    blocked_signal = pyqtSignal(str)  # 차단 발생 시 프로그램 이름 전달

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
                                self.blocked_signal.emit(proc_name)  # 차단 발생 시그널 전송
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
        self.pip_window = PipUI()
        self.is_pip_mode = False
        self.blocker_thread = None
        
        # API 서버 즉시 시작 (확장 프로그램 통신용)
        self.api_server = ApiServerThread()
        self.api_server.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        # ★ UI 이벤트 연결 (버튼 클릭 등)
        self.start_btn.clicked.connect(self.toggle_session)
        self.save_btn.clicked.connect(self.save_preset)
        self.load_btn.clicked.connect(self.load_preset)
        self.log_check.stateChanged.connect(self.toggle_log_mode)

        self.pip_btn.clicked.connect(self.switch_to_pip)
        self.pip_window.return_btn.clicked.connect(self.return_from_pip)

        # 프리셋 저장 위치 (현업식: OS별 user-data 폴더, 단 기존 block_list가 있으면 그대로 사용)
        preset_dir = _default_preset_dir()
        _ensure_default_preset(preset_dir)
        self.preset_dir = str(preset_dir)

        #사운드 플레이어 설정
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0) # 볼륨 100% (0.0 ~ 1.0)
        
        # 격려 메시지 리스트
        self.encouragement_messages = [
            "잘하고 있어요! 집중력을 유지하고 계세요! 💪",
            "훌륭해요! 방해 요소를 차단하고 계시네요! 🌟",
            "좋아요! 이렇게 계속 집중하시면 목표를 달성할 수 있어요! ✨",
            "멋져요! 집중하는 모습이 정말 대단합니다! 🎯",
            "화이팅! 작은 선택이 큰 성과를 만들어냅니다! 🚀",
            "대단해요! 집중력을 지키는 당신이 멋집니다! ⭐",
            "잘하고 계세요! 이 순간의 노력이 미래를 만듭니다! 🌈",
            "훌륭한 선택이에요! 집중하는 시간이 소중합니다! 💎",
            "좋아요! 방해 요소를 멀리하고 목표에 집중하세요! 🎪",
            "멋진 모습이에요! 계속 이렇게 집중하시면 성공할 거예요! 🏆",
            "화이팅! 지금의 노력이 당신을 더 강하게 만듭니다! 💫",
            "잘하고 있어요! 집중하는 시간이 당신의 자산입니다! 🌟"
        ]

    def play_sound(self, file_name):
        """번들된 sounds 리소스의 mp3 파일을 재생합니다."""
        try:
            sound_path = resource_path("sounds", file_name)
            
            if os.path.exists(sound_path):
                self.player.setSource(QUrl.fromLocalFile(sound_path))
                self.player.play()
                self.handle_log(f"🔊 사운드 재생됨: {file_name}", "INFO")
            else:
                self.handle_log(f"⚠️ 사운드 파일 없음: {file_name}", "WARNING")
        except Exception as e:
            self.handle_log(f"⚠️ 사운드 재생 오류: {e}", "ERROR")

    def switch_to_pip(self):
        """메인 창을 숨기고 PIP 창을 보여줍니다."""
        self.is_pip_mode = True
        self.hide() # 메인 창 숨김
        
        # 현재 상태를 PIP 창에 동기화하고 보여줌
        self.sync_pip_ui()
        # 메인창의 위치 근처에 띄우기 (선택사항)
        self.pip_window.move(self.x() + 50, self.y() + 50)
        self.pip_window.show() # PIP 창 표시
        self.handle_log("📺 PIP 모드로 전환되었습니다.", "INFO")

    def return_from_pip(self):
        """PIP 창을 숨기고 메인 창을 보여줍니다."""
        self.is_pip_mode = False
        self.pip_window.hide() # PIP 창 숨김
        self.show() # 메인 창 표시
        self.handle_log("🖥️ 메인 모드로 복귀했습니다.", "INFO")

    def sync_pip_ui(self):
        """현재 상태(시간, 모드)를 PIP 창 라벨에 복사합니다."""
        self.pip_window.timer_label.setText(self.timer_label.text())
        self.pip_window.status_label.setText(self.status_label.text())
        # 상태에 따라 색상 동기화
        if self.current_state == "FOCUS":
             self.pip_window.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #D08770;")
        elif self.current_state == "BREAK":
             self.pip_window.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #A3BE8C;")
        else:
             self.pip_window.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ECEFF4;")

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
            self.blocker_thread.blocked_signal.connect(self.show_encouragement_message)
            self.blocker_thread.start()
        self.handle_log("🛡️ 차단 기능이 활성화되었습니다.", "INFO")
    
    def show_encouragement_message(self, proc_name):
        """차단 발생 시 격려 메시지를 랜덤으로 표시합니다."""
        message = random.choice(self.encouragement_messages)
        title = f"🚫 프로그램 차단됨: {proc_name}"
        QMessageBox.information(self, title, message)

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

        self.status_label.setStyleSheet("color: #ECEFF4;")
        if self.is_pip_mode: self.sync_pip_ui()

        self.handle_log("세션이 중지되었습니다.", "WARNING")

    def enter_focus_mode(self):
        self.current_state = "FOCUS"
        self.time_left = self.focus_input.value() * 60
        self.status_label.setText(f"🔥 집중 중 ({self.current_cycle}/{self.total_cycles})")
        self.status_label.setStyleSheet("color: #D08770; font-weight: bold;")

        if self.is_pip_mode: self.sync_pip_ui()

        self.enable_blocking()
        self.timer.start(1000)
        self.handle_log(f"🔥 집중 모드 시작 (Cycle {self.current_cycle})", "INFO")

    def enter_break_mode(self):
        self.current_state = "BREAK"
        self.time_left = self.break_input.value() * 60
        self.status_label.setText(f"☕ 휴식 시간 ({self.current_cycle}/{self.total_cycles})")
        self.status_label.setStyleSheet("color: #A3BE8C; font-weight: bold;")

        if self.is_pip_mode: self.sync_pip_ui()

        self.disable_blocking()
        self.timer.start(1000)
        self.handle_log(f"☕ 휴식 모드 시작 (Cycle {self.current_cycle})", "INFO")

    def update_timer(self):
            minutes = self.time_left // 60
            seconds = self.time_left % 60
            time_str = f"{minutes:02}:{seconds:02}"
            
            # [중요] 메인 창과 PIP 창 모두 시간 업데이트
            self.timer_label.setText(time_str)
            if self.is_pip_mode:
                self.pip_window.timer_label.setText(time_str)

            if self.time_left > 0:
                self.time_left -= 1
            else:
                self.timer.stop()
                if self.current_state == "FOCUS":
                    self.play_sound("focus_end.mp3")
                    if self.current_cycle >= self.total_cycles:
                        self.finish_all_sessions()
                    else:
                        self.enter_break_mode()
                elif self.current_state == "BREAK":
                    self.play_sound("break_end.mp3")
                    self.current_cycle += 1
                    self.enter_focus_mode()

    def finish_all_sessions(self):
        self.handle_log("모든 세션 완료!", "SUCCESS")
        self.stop_session()
        QMessageBox.information(self, "완료", "모든 집중 세션을 완료했습니다! 🎉")

def main() -> None:
    # Windows에서 콘솔 창 숨기기
    if platform.system() == "Windows":
        import ctypes
        # 콘솔 창 숨기기
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
    
    # Windows에서만 관리자 권한 승격 시도 (Linux/macOS는 여기서 자동 승격 불가)
    if platform.system() == "Windows" and not is_admin():
        run_as_admin()

    app = QApplication(sys.argv)

    font_file = resource_path("font.ttf")
    font_id = QFontDatabase.addApplicationFont(font_file)
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(font_family, 10))
        print(f"폰트 로드 성공: {font_family}")
    else:
        print("폰트 파일을 찾을 수 없거나 로드 실패 (기본 폰트 사용)")

    window = StudyWithLogic()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()