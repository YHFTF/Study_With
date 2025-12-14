from __future__ import annotations

import ctypes
import os
import platform
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil
from PyQt6.QtCore import QThread, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox

from .ui import PipUI, StudyWithUI
from .session_manager import SessionManager
from .rank_themes import get_theme

# 클라우드 로그인/동기화
from .cloud_client import CloudClient, CloudError

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


def _get_config_dir() -> Path:
    """설정 파일 저장 디렉토리 반환"""
    system = platform.system()
    if system == "Windows":
        base = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        config_dir = base / "StudyWith" / "config"
    elif system == "Darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "StudyWith" / "config"
    else:
        base = Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
        config_dir = base / "study-with" / "config"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _get_last_preset_file() -> Path:
    """마지막 프리셋 경로 저장 파일 반환"""
    return _get_config_dir() / "last_preset.txt"


def save_last_preset_path(preset_path: str) -> None:
    """마지막 로딩한 프리셋 경로 저장"""
    try:
        last_preset_file = _get_last_preset_file()
        with open(last_preset_file, 'w', encoding='utf-8') as f:
            f.write(preset_path)
    except Exception as e:
        print(f"마지막 프리셋 경로 저장 실패: {e}")


def load_last_preset_path() -> Optional[str]:
    """마지막 로딩한 프리셋 경로 불러오기"""
    try:
        last_preset_file = _get_last_preset_file()
        if last_preset_file.exists():
            with open(last_preset_file, 'r', encoding='utf-8') as f:
                path = f.read().strip()
                # 파일이 존재하는지 확인
                if path and Path(path).exists():
                    return path
    except Exception as e:
        print(f"마지막 프리셋 경로 불러오기 실패: {e}")
    return None

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
        return False

    script = os.path.abspath(sys.argv[0])
    params = " ".join([script] + sys.argv[1:])
    try:
        # 관리자 권한으로 재실행
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        # ShellExecuteW가 성공하면 32보다 큰 값 반환
        if result > 32:
            # 새 프로세스가 시작되었으므로 현재 프로세스 종료
            sys.exit(0)
        else:
            # 사용자가 취소했거나 실패한 경우
            return False
    except Exception as e:
        print(f"관리자 권한 승격 오류: {e}")
        return False

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
        
        # 세션 기록 관리 (먼저 초기화)
        try:
            self.session_manager = SessionManager()
        except Exception as e:
            print(f"세션 매니저 초기화 오류: {e}")
            import traceback
            traceback.print_exc()
            # 기본값으로 계속 진행
            self.session_manager = None
        
        # PIP 창 초기화 (세션 매니저 이후)
        try:
            self.pip_window = PipUI()
        except Exception as e:
            print(f"PIP 창 초기화 오류: {e}")
            import traceback
            traceback.print_exc()
            self.pip_window = None
        
        self.is_pip_mode = False
        self.blocker_thread = None
        self.session_start_time = None
        self.total_focus_seconds = 0  # 이번 세션의 총 집중 시간(초)
        self.focus_duration = 0  # 집중 시간 설정값(분)
        self.break_duration = 0  # 휴식 시간 설정값(분)
        
        # API 서버 즉시 시작 (확장 프로그램 통신용)
        self.api_server = ApiServerThread()
        self.api_server.start()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        # ★ UI 이벤트 연결 (버튼 클릭 등)
        self.start_btn.clicked.connect(self.toggle_session)
        self.save_btn.clicked.connect(self.save_preset)
        self.load_btn.clicked.connect(lambda: self.load_preset())  # 명시적으로 파라미터 없이 호출
        self.log_check.stateChanged.connect(self.toggle_log_mode)
        self.simple_mode_check.stateChanged.connect(self.toggle_simple_mode)  # 심플 모드 체크박스 연결

        self.pip_btn.clicked.connect(self.switch_to_pip)
        if self.pip_window is not None:
            self.pip_window.return_btn.clicked.connect(self.return_from_pip)
        
        # 통계 창 초기화
        try:
            if self.session_manager is not None:
                from .ui import StatsWindow
                # 로그 핸들러를 전달하여 통계 창에서도 로그가 표시되도록 함
                self.stats_window = StatsWindow(self.session_manager, log_handler=self.handle_log)
                self.stats_btn.clicked.connect(self.show_stats)
            else:
                self.stats_window = None
                print("세션 매니저가 없어 통계 창을 초기화할 수 없습니다.")
        except Exception as e:
            print(f"통계 창 초기화 오류: {e}")
            import traceback
            traceback.print_exc()
            self.stats_window = None
        
        # 초기 등급 적용 (예외 처리)
        try:
            self.update_ui_rank()
        except Exception as e:
            print(f"등급 스타일 적용 오류: {e}")
            # 기본 스타일 유지

        # 프리셋 저장 위치 (현업식: OS별 user-data 폴더, 단 기존 block_list가 있으면 그대로 사용)
        preset_dir = _default_preset_dir()
        _ensure_default_preset(preset_dir)
        self.preset_dir = str(preset_dir)

        # ------------------------------
        # 클라우드(로그인/프리셋/레벨) 초기화
        # ------------------------------
        self.cloud = CloudClient()
        try:
            # UI에 저장된 설정 반영
            if hasattr(self, "cloud_server_input"):
                self.cloud_server_input.setText(self.cloud.base_url)
            if hasattr(self, "cloud_username_input"):
                self.cloud_username_input.setText(self.cloud.auth.username)
            self._update_cloud_status()
        except Exception:
            pass

        # 버튼 연결
        try:
            self.cloud_login_btn.clicked.connect(self.cloud_login)
            self.cloud_register_btn.clicked.connect(self.cloud_register)
            self.cloud_logout_btn.clicked.connect(self.cloud_logout)
            self.cloud_sync_btn.clicked.connect(self.cloud_sync)
        except Exception:
            # UI가 없는 환경에서도 앱이 뜨도록 조용히 무시
            pass

        # 이전에 로딩했던 프리셋 자동 로딩
        last_preset = load_last_preset_path()
        if last_preset:
            try:
                self.load_preset(last_preset)
                self.handle_log(f"📂 이전 프리셋 자동 로드: {os.path.basename(last_preset)}", "INFO")
            except Exception as e:
                print(f"이전 프리셋 자동 로딩 실패: {e}")

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

        self._cloud_task = None

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
        if self.pip_window is None:
            QMessageBox.warning(self, "오류", "PIP 창을 초기화할 수 없습니다.")
            return
        
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
        if self.pip_window is not None:
            self.pip_window.hide() # PIP 창 숨김
        self.show() # 메인 창 표시
        self.handle_log("🖥️ 메인 모드로 복귀했습니다.", "INFO")
    
    def show_stats(self):
        """통계 창 표시"""
        self.stats_window.update_statistics()
        self.stats_window.show()
        self.stats_window.raise_()
        self.stats_window.activateWindow()
    
    def update_ui_rank(self):
        """현재 등급에 따라 UI 스타일 업데이트"""
        try:
            if not hasattr(self, 'session_manager') or self.session_manager is None:
                return
            
            stats = self.session_manager.get_statistics()
            rank = stats.get("rank", "BRONZE")
            
            # 메인 창 스타일 업데이트
            self.update_rank_style(rank)
            
            # PIP 창 스타일 업데이트
            if hasattr(self, 'pip_window') and self.pip_window:
                self.pip_window.update_rank_style(rank)
        except Exception as e:
            print(f"등급 업데이트 오류: {e}")
            import traceback
            traceback.print_exc()

    def sync_pip_ui(self):
        """현재 상태(시간, 모드)를 PIP 창 라벨에 복사합니다."""
        if self.pip_window is None:
            return
        
        try:
            self.pip_window.timer_label.setText(self.timer_label.text())
            self.pip_window.status_label.setText(self.status_label.text())
            
            # 등급에 따른 테마 가져오기
            if self.session_manager is None:
                theme = get_theme("BRONZE")
            else:
                stats = self.session_manager.get_statistics()
                rank = stats.get("rank", "BRONZE")
                theme = get_theme(rank)
            
            # 상태에 따라 색상 동기화 (등급 테마 반영)
            if self.current_state == "FOCUS":
                 self.pip_window.status_label.setStyleSheet(
                     f"font-weight: bold; font-size: 14px; color: {theme['accent_color']};"
                 )
            elif self.current_state == "BREAK":
                 self.pip_window.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #A3BE8C;")
            else:
                 self.pip_window.status_label.setStyleSheet(
                     f"font-weight: bold; font-size: 14px; color: {theme['text_color']};"
                 )
        except Exception as e:
            print(f"PIP UI 동기화 오류: {e}")

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
    def load_preset(self, preset_path: Optional[str] = None):
        """
        프리셋 불러오기
        
        Args:
            preset_path: 불러올 프리셋 파일 경로 (None이면 파일 대화상자 표시)
        """
        # 파일 경로가 제공되지 않으면 파일 대화상자 열기
        if preset_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "프리셋 불러오기", 
                self.preset_dir, 
                "Text Files (*.txt)"
            )
        else:
            file_path = preset_path

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
                
                # 마지막 프리셋 경로 저장
                save_last_preset_path(file_path)
                
                self.handle_log(f"📂 프리셋 로드 완료: {os.path.basename(file_path)}", "INFO")
                
            except Exception as e:
                if preset_path is None:  # 사용자가 직접 선택한 경우에만 오류 메시지 표시
                    QMessageBox.critical(self, "오류", f"불러오기 실패: {e}")
                else:
                    # 자동 로딩 실패는 조용히 처리
                    print(f"자동 프리셋 로딩 실패: {e}")
        
    # --- 로직 메서드 구현 ---
    
    def toggle_log_mode(self, state):
        self.log_mode = (state == 2)
        self.log_viewer.setVisible(self.log_mode)

    def handle_log(self, message, msg_type="INFO"):
        """로그 발생 시 처리"""
        if self.log_mode:
            self.append_log_ui(message, msg_type)

    # ------------------------------
    # 클라우드(로그인/동기화)
    # ------------------------------
    def _update_cloud_status(self, extra: str = "") -> None:
        try:
            if not hasattr(self, "cloud_status_label"):
                return
            if self.cloud.is_logged_in():
                user = self.cloud.auth.username or "unknown"
                text = f"☁️ 클라우드: 로그인됨 ({user})"
            else:
                text = "☁️ 클라우드: 로그인 안 됨"
            if extra:
                text += f" - {extra}"
            self.cloud_status_label.setText(text)
        except Exception:
            pass

    class _CloudTaskThread(QThread):
        done = pyqtSignal(object)
        failed = pyqtSignal(str)

        def __init__(self, fn):
            super().__init__()
            self._fn = fn

        def run(self):
            try:
                res = self._fn()
                self.done.emit(res)
            except Exception as e:
                self.failed.emit(str(e))

    def _start_cloud_task(self, label: str, fn, on_done=None) -> None:
        if getattr(self, "_cloud_task", None) is not None and self._cloud_task.isRunning():
            self.handle_log("클라우드 작업이 이미 진행 중입니다.", "WARNING")
            return

        self._update_cloud_status(label)
        try:
            self.cloud_sync_btn.setDisabled(True)
            self.cloud_login_btn.setDisabled(True)
            self.cloud_register_btn.setDisabled(True)
            self.cloud_logout_btn.setDisabled(True)
        except Exception:
            pass

        t = self._CloudTaskThread(fn)
        self._cloud_task = t

        def _finish_ui():
            try:
                self.cloud_sync_btn.setDisabled(False)
                self.cloud_login_btn.setDisabled(False)
                self.cloud_register_btn.setDisabled(False)
                self.cloud_logout_btn.setDisabled(False)
            except Exception:
                pass
            self._update_cloud_status()

        def _ok(res):
            _finish_ui()
            if on_done:
                try:
                    on_done(res)
                except Exception as e:
                    self.handle_log(f"클라우드 처리 후 콜백 오류: {e}", "ERROR")

        def _fail(msg):
            _finish_ui()
            self.handle_log(f"클라우드 오류: {msg}", "ERROR")
            try:
                QMessageBox.warning(self, "클라우드 오류", msg)
            except Exception:
                pass

        t.done.connect(_ok)
        t.failed.connect(_fail)
        t.start()

    def _cloud_apply_inputs(self) -> None:
        base_url = ""
        try:
            base_url = self.cloud_server_input.text().strip()
        except Exception:
            pass
        if base_url:
            self.cloud.set_base_url(base_url)

    def cloud_login(self) -> None:
        self._cloud_apply_inputs()
        try:
            username = self.cloud_username_input.text().strip()
            password = self.cloud_password_input.text()
        except Exception:
            username, password = "", ""

        def _fn():
            return self.cloud.login(username, password)

        def _done(_res):
            self.handle_log("☁️ 로그인 완료", "SUCCESS")
            self._update_cloud_status()

        self._start_cloud_task("로그인 중...", _fn, _done)

    def cloud_register(self) -> None:
        self._cloud_apply_inputs()
        try:
            username = self.cloud_username_input.text().strip()
            password = self.cloud_password_input.text()
        except Exception:
            username, password = "", ""

        def _fn():
            return self.cloud.register(username, password)

        def _done(_res):
            self.handle_log("☁️ 회원가입/로그인 완료", "SUCCESS")
            self._update_cloud_status()

        self._start_cloud_task("회원가입 중...", _fn, _done)

    def cloud_logout(self) -> None:
        self.cloud.logout()
        self._update_cloud_status("로그아웃됨")
        self.handle_log("☁️ 로그아웃 완료", "INFO")

    def cloud_sync(self) -> None:
        self._cloud_apply_inputs()

        def _fn():
            # 1) 프리셋 동기화
            uploaded, downloaded = self.cloud.sync_presets_dir(self.preset_dir)

            # 2) 유저 레벨(통계) 업로드
            total_score = 0
            rank = "BRONZE"
            try:
                if self.session_manager is not None:
                    stats = self.session_manager.get_statistics()
                    total_score = int(stats.get("total_score", 0))
                    rank = str(stats.get("rank", "BRONZE"))
            except Exception:
                pass
            prof = self.cloud.upload_profile(total_score=total_score, rank=rank)
            return {"uploaded": uploaded, "downloaded": downloaded, "profile": prof}

        def _done(res):
            up = res.get("uploaded", 0)
            down = res.get("downloaded", 0)
            self.handle_log(f"☁️ 동기화 완료: 업로드 {up}개 / 다운로드 {down}개", "SUCCESS")
            try:
                QMessageBox.information(self, "동기화 완료", f"업로드 {up}개, 다운로드 {down}개 완료")
            except Exception:
                pass

        self._start_cloud_task("동기화 중...", _fn, _done)

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
            self.session_start_time = datetime.now()
            self.total_focus_seconds = 0
            self.focus_duration = self.focus_input.value()
            self.break_duration = self.break_input.value()
            
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
        
        # 세션 기록 저장
        if self.session_start_time and self.session_manager is not None:
            try:
                end_time = datetime.now()
                total_focus_minutes = self.total_focus_seconds // 60
                completed_cycles = self.current_cycle - 1 if self.current_state == "FOCUS" else self.current_cycle
                
                self.session_manager.add_session(
                    start_time=self.session_start_time,
                    end_time=end_time,
                    total_focus_minutes=total_focus_minutes,
                    total_cycles=self.total_cycles,
                    completed_cycles=completed_cycles,
                    focus_duration=self.focus_duration,
                    break_duration=self.break_duration
                )
                self.session_start_time = None
                self.total_focus_seconds = 0
                
                # 통계 및 등급 업데이트
                if hasattr(self, 'stats_window') and self.stats_window:
                    self.stats_window.update_statistics()
                self.update_ui_rank()
            except Exception as e:
                print(f"세션 저장 오류: {e}")
                import traceback
                traceback.print_exc()

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
            if self.is_pip_mode and self.pip_window is not None:
                try:
                    self.pip_window.timer_label.setText(time_str)
                except Exception as e:
                    print(f"PIP 타이머 업데이트 오류: {e}")

            if self.time_left > 0:
                self.time_left -= 1
                # 집중 모드일 때만 집중 시간 카운트
                if self.current_state == "FOCUS":
                    self.total_focus_seconds += 1
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
        
        # 세션 기록 저장 (stop_session에서 처리되지만, 완료된 사이클 수를 정확히 반영)
        if self.session_start_time and self.session_manager is not None:
            try:
                end_time = datetime.now()
                total_focus_minutes = self.total_focus_seconds // 60
                
                self.session_manager.add_session(
                    start_time=self.session_start_time,
                    end_time=end_time,
                    total_focus_minutes=total_focus_minutes,
                    total_cycles=self.total_cycles,
                    completed_cycles=self.total_cycles,  # 모든 사이클 완료
                    focus_duration=self.focus_duration,
                    break_duration=self.break_duration
                )
                self.session_start_time = None
                self.total_focus_seconds = 0
                
                # 통계 및 등급 업데이트
                if hasattr(self, 'stats_window') and self.stats_window:
                    self.stats_window.update_statistics()
                self.update_ui_rank()
            except Exception as e:
                print(f"세션 저장 오류: {e}")
                import traceback
                traceback.print_exc()
        
        self.stop_session()
        
        # 통계 표시
        try:
            if self.session_manager is not None:
                stats = self.session_manager.get_statistics()
                theme = get_theme(stats.get("rank", "BRONZE"))
                message = f"모든 집중 세션을 완료했습니다! 🎉\n\n"
                message += f"현재 등급: {theme['emoji']} {stats['rank_display']} {theme['emoji']}\n"
                message += f"총 점수: {stats['total_score']:,}점\n"
                message += f"총 집중 시간: {stats['total_focus_hours']:.1f}시간"
            else:
                message = "모든 집중 세션을 완료했습니다! 🎉"
            QMessageBox.information(self, "완료", message)
        except Exception as e:
            print(f"완료 메시지 표시 오류: {e}")
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
    # 주의: run_as_admin()이 호출되면 현재 프로세스가 종료되고 새 프로세스가 시작됨
    if platform.system() == "Windows" and not is_admin():
        try:
            run_as_admin()
            # run_as_admin()이 성공하면 여기 도달하지 않음 (sys.exit 호출됨)
            # 하지만 실패하면 계속 진행
        except Exception as e:
            print(f"관리자 권한 승격 실패: {e}")
            # 관리자 권한 없이 계속 진행 (일부 기능 제한될 수 있음)

    try:
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
    except Exception as e:
        print(f"애플리케이션 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        # 오류 발생 시에도 콘솔 창을 다시 보여서 오류 메시지 확인 가능하게
        if platform.system() == "Windows":
            try:
                kernel32 = ctypes.windll.kernel32
                user32 = ctypes.windll.user32
                hwnd = kernel32.GetConsoleWindow()
                if hwnd:
                    user32.ShowWindow(hwnd, 1)  # 1 = SW_SHOW
            except:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()