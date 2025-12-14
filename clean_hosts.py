# clean_hosts.py
import sys
import os
import ctypes
import platform

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)

def clean_hosts():
    if platform.system() == "Windows":
        hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
    else:
        hosts_path = "/etc/hosts"

    try:
        with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()

        # Study With 앱이 남긴 마커 찾기
        MARKER_START = "# --- STUDY WITH BLOCK START ---\n"
        MARKER_END = "# --- STUDY WITH BLOCK END ---\n"

        new_lines = []
        in_block = False
        found = False

        for line in lines:
            if MARKER_START in line:
                in_block = True
                found = True
                continue
            if MARKER_END in line:
                in_block = False
                continue
            
            if not in_block:
                new_lines.append(line)

        if found:
            with open(hosts_path, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)
            print("✅ Hosts 파일 복구 완료! 차단된 사이트들이 해제되었습니다.")
        else:
            print("ℹ️ Hosts 파일에서 'Study With' 차단 내역을 찾을 수 없습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    input("엔터 키를 누르면 종료합니다...")

if __name__ == '__main__':
    if not is_admin():
        run_as_admin()
    else:
        clean_hosts()