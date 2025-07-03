"""
FFmpeg 자동 다운로드 및 관리 모듈

사용자가 첫 실행시 ffmpeg가 없으면 다운로드 여부를 묻고,
거절하면 ffmpeg 기능을 비활성화하는 스마트 매니저
"""

import os
import sys
import json
import platform
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

class FFmpegDownloadDialog(QDialog):
    """FFmpeg 다운로드 확인 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFmpeg 설치 필요")
        self.setModal(True)
        self.setFixedSize(500, 300)
        self.result_choice = None
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title = QLabel("🎬 비주얼 선별 기능을 위한 FFmpeg 설치")
        title.setFont(QFont("", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 설명
        description = QLabel("""
<b>비주얼 선별 도우미</b>에서 영상 썸네일을 생성하려면 FFmpeg가 필요합니다.

<b>📦 자동 설치 옵션:</b>
• 현재 운영체제에 맞는 FFmpeg를 자동으로 다운로드
• 약 50-80MB 크기 (인터넷 연결 필요)
• 프로그램 폴더에만 설치 (시스템 변경 없음)

<b>🚫 건너뛰기 옵션:</b>
• FFmpeg 기능 없이 프로그램 사용
• 비주얼 선별 기능은 비활성화됨
• 나중에 설정에서 다시 설치 가능
        """)
        description.setWordWrap(True)
        description.setStyleSheet("color: #333; line-height: 1.4;")
        layout.addWidget(description)
        
        # 버튼
        button_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("📥 자동 설치")
        self.install_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.install_btn.clicked.connect(self.accept_install)
        
        self.skip_btn = QPushButton("⏭️ 건너뛰기")
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.skip_btn.clicked.connect(self.reject_install)
        
        button_layout.addWidget(self.install_btn)
        button_layout.addWidget(self.skip_btn)
        layout.addLayout(button_layout)
        
        # 하단 정보
        info = QLabel("💡 FFmpeg는 영상 처리를 위한 오픈소스 라이브러리입니다")
        info.setStyleSheet("color: #666; font-size: 10px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
    def accept_install(self):
        self.result_choice = "install"
        self.accept()
        
    def reject_install(self):
        self.result_choice = "skip"
        self.reject()

class FFmpegDownloadThread(QThread):
    """FFmpeg 다운로드 스레드"""
    
    progress_updated = pyqtSignal(int)  # 진행률
    status_updated = pyqtSignal(str)    # 상태 메시지
    download_finished = pyqtSignal(bool, str)  # 성공여부, 메시지
    
    def __init__(self, download_url, extract_path):
        super().__init__()
        self.download_url = download_url
        self.extract_path = extract_path
        
    def run(self):
        try:
            self.status_updated.emit("다운로드 중...")
            
            # 임시 파일 경로
            temp_file = os.path.join(self.extract_path, "ffmpeg_temp.zip")
            os.makedirs(self.extract_path, exist_ok=True)
            
            # 다운로드
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    progress = (block_num * block_size / total_size) * 70  # 70%까지는 다운로드
                    self.progress_updated.emit(int(progress))
            
            urllib.request.urlretrieve(self.download_url, temp_file, progress_hook)
            
            self.status_updated.emit("압축 해제 중...")
            self.progress_updated.emit(75)
            
            # 압축 해제
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(self.extract_path)
            
            self.progress_updated.emit(90)
            
            # 임시 파일 정리
            os.remove(temp_file)
            
            self.progress_updated.emit(100)
            self.status_updated.emit("설치 완료!")
            
            self.download_finished.emit(True, "FFmpeg 설치가 완료되었습니다!")
            
        except Exception as e:
            self.download_finished.emit(False, f"설치 실패: {str(e)}")

class FFmpegProgressDialog(QDialog):
    """FFmpeg 다운로드 진행 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FFmpeg 설치 중...")
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("준비 중...")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

class FFmpegManager:
    """FFmpeg 자동 관리 클래스"""
    
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.ffmpeg_dir = os.path.join(self.script_dir, 'ffmpeg_bundle')
        self.config_file = os.path.join(self.script_dir, 'ffmpeg_config.json')
        self.config = self.load_config()
        
    def load_config(self):
        """설정 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        return {
            'ffmpeg_disabled': False,
            'auto_check': True,
            'last_check': None
        }
    
    def save_config(self):
        """설정 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 저장 실패: {e}")
    
    def is_ffmpeg_disabled(self):
        """FFmpeg가 비활성화되었는지 확인"""
        return self.config.get('ffmpeg_disabled', False)
    
    def disable_ffmpeg(self):
        """FFmpeg 기능 비활성화"""
        self.config['ffmpeg_disabled'] = True
        self.save_config()
    
    def enable_ffmpeg(self):
        """FFmpeg 기능 활성화"""
        self.config['ffmpeg_disabled'] = False
        self.save_config()
    
    def get_system_info(self):
        """시스템 정보 반환"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == 'windows':
            return 'windows', 'x64' if '64' in machine or 'amd64' in machine else 'x86'
        elif system == 'darwin':  # macOS
            return 'macos', 'arm64' if 'arm' in machine else 'x64'
        elif system == 'linux':
            return 'linux', 'arm64' if 'aarch64' in machine or 'arm64' in machine else 'x64'
        else:
            return 'unknown', 'unknown'
    
    def get_download_info(self):
        """OS별 다운로드 정보 반환"""
        system, arch = self.get_system_info()
        
        # BtbN/FFmpeg-Builds의 최신 릴리즈 URL들
        urls = {
            ('windows', 'x64'): 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
            ('windows', 'x86'): 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win32-gpl.zip',
            ('linux', 'x64'): 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz',
            ('linux', 'arm64'): 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz',
            ('macos', 'x64'): 'https://evermeet.cx/ffmpeg/ffmpeg-116654-g0fb26da5a6.zip',  # 대체 소스
            ('macos', 'arm64'): 'https://evermeet.cx/ffmpeg/ffmpeg-116654-g0fb26da5a6.zip'  # 대체 소스
        }
        
        return urls.get((system, arch))
    
    def check_system_ffmpeg(self):
        """시스템에 설치된 ffmpeg 확인"""
        try:
            # Windows
            result = subprocess.run(['where', 'ffmpeg'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ffmpeg', 'ffprobe'
        except:
            pass
        
        try:
            # macOS/Linux  
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ffmpeg', 'ffprobe'
        except:
            pass
        
        return None, None
    
    def check_bundled_ffmpeg(self):
        """번들된 ffmpeg 확인"""
        system, arch = self.get_system_info()
        
        if system == 'windows':
            ffmpeg_path = os.path.join(self.ffmpeg_dir, 'bin', 'ffmpeg.exe')
            ffprobe_path = os.path.join(self.ffmpeg_dir, 'bin', 'ffprobe.exe')
        else:
            ffmpeg_path = os.path.join(self.ffmpeg_dir, 'ffmpeg')
            ffprobe_path = os.path.join(self.ffmpeg_dir, 'ffprobe')
        
        if os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path):
            return ffmpeg_path, ffprobe_path
        
        return None, None
    
    def get_ffmpeg_paths(self):
        """FFmpeg 경로 반환 (번들된 것 우선)"""
        if self.is_ffmpeg_disabled():
            return None, None
        
        # 번들된 것 우선 확인
        bundled_ffmpeg, bundled_ffprobe = self.check_bundled_ffmpeg()
        if bundled_ffmpeg and bundled_ffprobe:
            return bundled_ffmpeg, bundled_ffprobe
        
        # 시스템 것 확인
        system_ffmpeg, system_ffprobe = self.check_system_ffmpeg()
        if system_ffmpeg and system_ffprobe:
            return system_ffmpeg, system_ffprobe
        
        return None, None
    
    def needs_installation(self):
        """설치가 필요한지 확인"""
        if self.is_ffmpeg_disabled():
            return False
        
        ffmpeg_path, ffprobe_path = self.get_ffmpeg_paths()
        return ffmpeg_path is None or ffprobe_path is None
    
    def show_install_dialog(self, parent=None):
        """설치 확인 다이얼로그 표시"""
        dialog = FFmpegDownloadDialog(parent)
        result = dialog.exec_()
        
        if dialog.result_choice == "install":
            return self.download_ffmpeg(parent)
        elif dialog.result_choice == "skip":
            self.disable_ffmpeg()
            return False
        
        return False
    
    def download_ffmpeg(self, parent=None):
        """FFmpeg 다운로드 및 설치"""
        download_url = self.get_download_info()
        if not download_url:
            QMessageBox.warning(parent, "지원되지 않는 시스템", 
                              "현재 시스템은 자동 설치가 지원되지 않습니다.\n수동으로 FFmpeg를 설치해주세요.")
            return False
        
        # 다운로드 진행 다이얼로그
        progress_dialog = FFmpegProgressDialog(parent)
        
        # 다운로드 스레드
        download_thread = FFmpegDownloadThread(download_url, self.ffmpeg_dir)
        download_thread.progress_updated.connect(progress_dialog.progress_bar.setValue)
        download_thread.status_updated.connect(progress_dialog.status_label.setText)
        
        success = False
        message = ""
        
        def on_download_finished(is_success, msg):
            nonlocal success, message
            success = is_success
            message = msg
            progress_dialog.accept()
        
        download_thread.download_finished.connect(on_download_finished)
        download_thread.start()
        
        progress_dialog.exec_()
        download_thread.quit()
        download_thread.wait()
        
        if success:
            self.enable_ffmpeg()
            QMessageBox.information(parent, "설치 완료", message)
        else:
            QMessageBox.critical(parent, "설치 실패", message)
        
        return success
    
    def check_and_prompt_if_needed(self, parent=None):
        """필요시 설치 확인 및 프롬프트"""
        if self.needs_installation():
            return self.show_install_dialog(parent)
        return True 