import sys
import os
import json
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QScrollArea, QWidget,
                             QMessageBox, QTextEdit, QSplitter, QSpinBox, 
                             QCheckBox, QProgressBar, QGroupBox, QGridLayout,
                             QSlider, QFrame, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot, QSize
from PyQt5.QtGui import QFont, QColor, QPixmap, QPainter, QPen, QBrush
import subprocess

class ThumbnailExtractorThread(QThread):
    """썸네일 추출을 백그라운드에서 처리하는 스레드"""
    thumbnail_ready = pyqtSignal(str, QPixmap)  # 파일명, 썸네일
    
    def __init__(self, file_list, thumbnail_size=(160, 120)):
        super().__init__()
        self.file_list = file_list
        self.thumbnail_size = thumbnail_size
        self.current_path = ""
        
    def set_path(self, path):
        self.current_path = path
    
    def run(self):
        """썸네일 추출 실행"""
        for file_info in self.file_list:
            file_name = file_info['name']
            file_path = os.path.join(self.current_path, file_name)
            
            if os.path.exists(file_path):
                thumbnail = self.extract_thumbnail(file_path)
                if thumbnail:
                    self.thumbnail_ready.emit(file_name, thumbnail)
    
    def extract_thumbnail(self, video_path):
        """비디오 파일에서 3x3 그리드 썸네일 추출 (퍼센트 기반)"""
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            
            # 먼저 영상 길이 간단히 확인
            duration = self.get_simple_duration(video_path)
            if duration <= 0:
                print(f"영상 길이 확인 실패, 기본값 사용: {video_path}")
                duration = 1200  # 20분으로 가정 (네트워크 파일은 보통 김)
            
            # 우선 간단한 프레임들부터 시도 (0%, 25%, 50%, 75% - 4개만)
            simple_percentages = [0.0, 0.25, 0.5, 0.75]
            frame_pixmaps = []
            
            print(f"네트워크 파일 처리 중: {video_path}")
            
            # 먼저 간단한 4개 프레임으로 시도
            for i, percent in enumerate(simple_percentages):
                time_sec = duration * percent
                temp_frame = os.path.join(temp_dir, f"simple_frame_{os.getpid()}_{i}.jpg")
                
                try:
                    # 최대한 빠른 추출을 위한 명령
                    cmd = [
                        'ffmpeg', 
                        '-ss', str(time_sec),
                        '-i', video_path,
                        '-vframes', '1',
                        '-q:v', '8',  # 최저 품질로 빠르게
                        '-s', '53x40',
                        '-f', 'image2',
                        '-y',
                        temp_frame
                    ]
                    
                    print(f"프레임 {percent*100:.0f}% 추출 시도...")
                    
                    # 네트워크 드라이브용 긴 타임아웃
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    
                    if os.path.exists(temp_frame):
                        pixmap = QPixmap(temp_frame)
                        if not pixmap.isNull():
                            frame_pixmaps.append(pixmap)
                            print(f"프레임 {percent*100:.0f}% 성공!")
                        else:
                            frame_pixmaps.append(None)
                        os.unlink(temp_frame)
                    else:
                        frame_pixmaps.append(None)
                        
                except Exception as frame_error:
                    print(f"프레임 {i} ({percent*100:.0f}%) 추출 실패: {frame_error}")
                    frame_pixmaps.append(None)
                    
                # 하나라도 성공하면 다음으로 진행
                if any(p is not None for p in frame_pixmaps):
                    print("기본 프레임 추출 성공, 추가 프레임 시도...")
            
            # 기본 4개에 추가로 5개 더 시도 (총 9개가 되도록)
            if any(p is not None for p in frame_pixmaps):
                additional_percentages = [0.1, 0.2, 0.6, 0.8, 0.9]
                
                for i, percent in enumerate(additional_percentages):
                    time_sec = duration * percent
                    temp_frame = os.path.join(temp_dir, f"add_frame_{os.getpid()}_{i}.jpg")
                    
                    try:
                        cmd = [
                            'ffmpeg', 
                            '-ss', str(time_sec),
                            '-i', video_path,
                            '-vframes', '1',
                            '-q:v', '8',
                            '-s', '53x40',
                            '-f', 'image2',
                            '-y',
                            temp_frame
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                        
                        if os.path.exists(temp_frame):
                            pixmap = QPixmap(temp_frame)
                            if not pixmap.isNull():
                                # 적절한 위치에 삽입
                                if percent == 0.1:
                                    frame_pixmaps.insert(1, pixmap)
                                elif percent == 0.2:
                                    frame_pixmaps.insert(2, pixmap)
                                else:
                                    frame_pixmaps.append(pixmap)
                            os.unlink(temp_frame)
                            
                    except Exception:
                        pass  # 추가 프레임은 실패해도 무시
            
            # 3x3 격자 썸네일 생성
            return self.create_3x3_grid_thumbnail(frame_pixmaps)
                
        except Exception as e:
            print(f"3x3 그리드 썸네일 추출 실패: {video_path}, 오류: {e}")
            
        return self.create_placeholder_thumbnail()
    
    def get_simple_duration(self, video_path):
        """영상 길이 간단히 확인 (초 단위) - 네트워크 드라이브 최적화"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', 
                '-print_format', 'compact',
                '-show_entries', 'format=duration',
                video_path
            ]
            
            # 네트워크 드라이브용 긴 타임아웃
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                # format|duration=123.456 형태에서 숫자 추출
                for line in result.stdout.strip().split('\n'):
                    if 'duration=' in line:
                        duration_str = line.split('duration=')[1].split('|')[0]
                        duration = float(duration_str)
                        print(f"영상 길이: {duration:.1f}초 ({duration/60:.1f}분)")
                        return duration
            
        except Exception as e:
            print(f"간단 영상 길이 확인 실패: {video_path}, 오류: {e}")
            
        return 0
    
    def create_3x3_grid_thumbnail(self, frame_pixmaps):
        """사용 가능한 프레임들로 3x3 격자 배치 (적응형)"""
        try:
            # 3x3 격자 설정
            grid_size = 3
            frame_width = self.thumbnail_size[0] // grid_size
            frame_height = self.thumbnail_size[1] // grid_size
            
            # 최종 이미지 생성
            final_pixmap = QPixmap(self.thumbnail_size[0], self.thumbnail_size[1])
            final_pixmap.fill(QColor(35, 35, 35))  # 어두운 배경
            
            painter = QPainter(final_pixmap)
            
            # 실제 성공한 프레임 수에 따라 퍼센트 계산
            valid_frames = [p for p in frame_pixmaps if p is not None and not p.isNull()]
            total_valid = len(valid_frames)
            
            print(f"유효한 프레임 수: {total_valid}/{len(frame_pixmaps)}")
            
            # 9개 그리드 셀에 배치
            valid_index = 0
            for i in range(9):  # 3x3 = 9개
                row = i // grid_size
                col = i % grid_size
                    
                x = col * frame_width
                y = row * frame_height
                
                # 경계선을 위한 여백
                margin = 1
                inner_width = frame_width - (margin * 2)
                inner_height = frame_height - (margin * 2)
                
                # 실제 프레임이 있으면 표시
                if i < len(frame_pixmaps) and frame_pixmaps[i] and not frame_pixmaps[i].isNull():
                    # 실제 프레임 표시
                    scaled_frame = frame_pixmaps[i].scaled(
                        inner_width, inner_height,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    
                    # 중앙 배치
                    center_x = x + margin + (inner_width - scaled_frame.width()) // 2
                    center_y = y + margin + (inner_height - scaled_frame.height()) // 2
                    
                    painter.drawPixmap(center_x, center_y, scaled_frame)
                    
                    # 프레임 순서 표시 (퍼센트 대신)
                    painter.setPen(QPen(QColor(255, 255, 255, 200)))
                    font = painter.font()
                    font.setPixelSize(8)
                    font.setBold(True)
                    painter.setFont(font)
                    painter.drawText(x + 2, y + 10, f"#{i+1}")
                    
                else:
                    # 플레이스홀더 표시
                    painter.fillRect(x + margin, y + margin, inner_width, inner_height, QColor(55, 55, 55))
                    painter.setPen(QPen(QColor(120, 120, 120)))
                    painter.drawText(x + margin, y + margin, inner_width, inner_height, Qt.AlignCenter, "?")
                
                # 격자 경계선
                painter.setPen(QPen(QColor(70, 70, 70), 1))
                painter.drawRect(x, y, frame_width, frame_height)
            
            painter.end()
            
            # 최소 1개 프레임이라도 있으면 성공
            if total_valid > 0:
                print(f"썸네일 그리드 생성 완료 ({total_valid}개 프레임)")
                return final_pixmap
            else:
                print("유효한 프레임이 없어 플레이스홀더 반환")
                return self.create_placeholder_thumbnail()
            
        except Exception as e:
            print(f"3x3 격자 썸네일 생성 실패: {e}")
            return self.create_placeholder_thumbnail()

    def create_simple_grid_thumbnail(self, frame_pixmaps):
        """4개 프레임을 2x2 격자로 빠르게 배치 (호환성 유지)"""
        try:
            # 2x2 격자 설정
            grid_size = 2
            frame_width = self.thumbnail_size[0] // grid_size
            frame_height = self.thumbnail_size[1] // grid_size
            
            # 최종 이미지 생성
            final_pixmap = QPixmap(self.thumbnail_size[0], self.thumbnail_size[1])
            final_pixmap.fill(QColor(40, 40, 40))  # 어두운 배경
            
            painter = QPainter(final_pixmap)
            
            # 2x2 격자에 프레임 배치
            positions = [(0, 0), (1, 0), (0, 1), (1, 1)]  # (col, row)
            
            for i, (col, row) in enumerate(positions):
                if i >= len(frame_pixmaps):
                    break
                    
                x = col * frame_width
                y = row * frame_height
                
                # 경계선을 위한 여백
                margin = 1
                inner_width = frame_width - (margin * 2)
                inner_height = frame_height - (margin * 2)
                
                if frame_pixmaps[i] and not frame_pixmaps[i].isNull():
                    # 실제 프레임 표시
                    scaled_frame = frame_pixmaps[i].scaled(
                        inner_width, inner_height,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    
                    # 중앙 배치
                    center_x = x + margin + (inner_width - scaled_frame.width()) // 2
                    center_y = y + margin + (inner_height - scaled_frame.height()) // 2
                    
                    painter.drawPixmap(center_x, center_y, scaled_frame)
                else:
                    # 플레이스홀더 표시
                    painter.fillRect(x + margin, y + margin, inner_width, inner_height, QColor(60, 60, 60))
                    painter.setPen(QPen(QColor(120, 120, 120)))
                    painter.drawText(x + margin, y + margin, inner_width, inner_height, Qt.AlignCenter, "?")
                
                # 격자 경계선
                painter.setPen(QPen(QColor(80, 80, 80), 1))
                painter.drawRect(x, y, frame_width, frame_height)
            
            painter.end()
            return final_pixmap
            
        except Exception as e:
            print(f"간단 격자 썸네일 생성 실패: {e}")
            return self.create_placeholder_thumbnail()
    
    def create_placeholder_thumbnail(self):
        """플레이스홀더 썸네일 생성"""
        pixmap = QPixmap(self.thumbnail_size[0], self.thumbnail_size[1])
        pixmap.fill(QColor(64, 64, 64))
        
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(128, 128, 128), 2))
        painter.drawRect(10, 10, self.thumbnail_size[0]-20, self.thumbnail_size[1]-20)
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "미리보기\n없음")
        painter.end()
        
        return pixmap

class VideoThumbnailWidget(QWidget):
    """개별 비디오 썸네일 위젯"""
    selection_changed = pyqtSignal(str, bool)  # 파일명, 선택상태
    preview_requested = pyqtSignal(str)  # 미리보기 요청
    
    def __init__(self, file_info, formatted_size):
        super().__init__()
        self.file_info = file_info
        self.file_name = file_info['name']
        self.file_size = file_info['size']
        self.formatted_size = formatted_size
        self.is_selected = False
        self.thumbnail_pixmap = None
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.request_preview)
        
        self.setFixedSize(180, 160)
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """UI 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # 썸네일 영역
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(160, 120)
        self.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background-color: #f0f0f0;")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("로딩중...")
        layout.addWidget(self.thumbnail_label)
        
        # 메타데이터 오버레이
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # 체크박스
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self.on_selection_changed)
        info_layout.addWidget(self.checkbox)
        
        # 파일 정보
        info_text = f"{self.formatted_size}"
        self.info_label = QLabel(info_text)
        self.info_label.setStyleSheet("font-size: 10px; color: #666;")
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # 파일명 (짧게 표시)
        display_name = self.file_name
        if len(display_name) > 20:
            display_name = display_name[:17] + "..."
        
        self.name_label = QLabel(display_name)
        self.name_label.setStyleSheet("font-size: 9px; font-weight: bold;")
        self.name_label.setToolTip(self.file_name)  # 전체 이름은 툴팁으로
        layout.addWidget(self.name_label)
        
    def set_thumbnail(self, pixmap):
        """썸네일 설정"""
        self.thumbnail_pixmap = pixmap
        self.thumbnail_label.setPixmap(pixmap)
        self.thumbnail_label.setText("")
        
    def on_selection_changed(self, state):
        """선택 상태 변경"""
        self.is_selected = (state == Qt.Checked)
        self.update_style()
        self.selection_changed.emit(self.file_name, self.is_selected)
        
    def update_style(self):
        """선택 상태에 따른 스타일 업데이트"""
        if self.is_selected:
            self.setStyleSheet("""
                VideoThumbnailWidget {
                    background-color: #e3f2fd;
                    border: 2px solid #2196f3;
                    border-radius: 5px;
                }
            """)
        else:
            self.setStyleSheet("""
                VideoThumbnailWidget {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                }
                VideoThumbnailWidget:hover {
                    background-color: #f5f5f5;
                    border: 1px solid #999;
                }
            """)
    
    def enterEvent(self, event):
        """마우스 진입시 미리보기 타이머 시작"""
        super().enterEvent(event)
        self.hover_timer.start(1000)  # 1초 후 미리보기
        
    def leaveEvent(self, event):
        """마우스 떠날시 타이머 취소"""
        super().leaveEvent(event)
        self.hover_timer.stop()
        
    def request_preview(self):
        """미리보기 요청"""
        self.preview_requested.emit(self.file_name)
        
    def set_selected(self, selected):
        """외부에서 선택 상태 설정"""
        self.checkbox.setChecked(selected)

class VisualSelectionDialog(QDialog):
    def __init__(self, capacity_finder, current_path, parent=None):
        super().__init__(parent)
        self.capacity_finder = capacity_finder
        self.current_path = current_path
        self.selection_result = None
        self.current_files = []
        self.thumbnail_widgets = {}  # {파일명: 위젯}
        self.selected_files = set()
        self.thumbnail_extractor = None
        
        self.setWindowTitle("비주얼 영상 선별 도우미")
        self.setGeometry(100, 100, 1200, 800)
        self.setModal(True)
        
        self.init_ui()
        self.load_users()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 상단 컨트롤 패널
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # 메인 분할기
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # 썸네일 그리드 영역
        thumbnail_area = self.create_thumbnail_area()
        main_splitter.addWidget(thumbnail_area)
        
        # 실시간 대시보드
        dashboard = self.create_dashboard()
        main_splitter.addWidget(dashboard)
        
        # 비율 설정 (썸네일:대시보드 = 3:1)
        main_splitter.setSizes([900, 300])
        
        # 하단 실행 버튼들
        button_layout = self.create_action_buttons()
        layout.addLayout(button_layout)
        
    def create_control_panel(self):
        """상단 컨트롤 패널 생성"""
        panel = QGroupBox("필터 및 컨트롤")
        panel.setMaximumHeight(60)  # 높이 제한
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)  # 패딩 줄이기
        
        # 사용자 선택
        layout.addWidget(QLabel("사용자:"))
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(150)
        self.user_combo.setMaximumHeight(25)
        self.user_combo.currentTextChanged.connect(self.on_user_changed)
        layout.addWidget(self.user_combo)
        
        # 크기 필터
        layout.addWidget(QLabel("최소 크기:"))
        self.size_filter_spin = QSpinBox()
        self.size_filter_spin.setRange(0, 10000)
        self.size_filter_spin.setValue(0)
        self.size_filter_spin.setSuffix(" MB")
        self.size_filter_spin.setMaximumHeight(25)
        self.size_filter_spin.valueChanged.connect(self.apply_filters)
        layout.addWidget(self.size_filter_spin)
        
        # 로드 버튼
        self.load_button = QPushButton("📁 파일 로드")
        self.load_button.clicked.connect(self.load_files)
        self.load_button.setEnabled(False)
        self.load_button.setMaximumHeight(25)
        layout.addWidget(self.load_button)
        
        # 빠른 선택
        layout.addWidget(QLabel("|"))
        self.select_all_btn = QPushButton("전체 선택")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.setMaximumHeight(25)
        layout.addWidget(self.select_all_btn)
        
        self.clear_all_btn = QPushButton("전체 해제")
        self.clear_all_btn.clicked.connect(self.clear_all)
        self.clear_all_btn.setEnabled(False)
        self.clear_all_btn.setMaximumHeight(25)
        layout.addWidget(self.clear_all_btn)
        
        layout.addStretch()
        return panel
        
    def create_thumbnail_area(self):
        """썸네일 그리드 영역 생성"""
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 썸네일 컨테이너
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QGridLayout(self.thumbnail_container)
        self.thumbnail_layout.setSpacing(10)
        
        scroll_area.setWidget(self.thumbnail_container)
        return scroll_area
        
    def create_dashboard(self):
        """실시간 대시보드 생성"""
        dashboard = QGroupBox("실시간 통계")
        layout = QVBoxLayout(dashboard)
        
        # 진행률
        self.progress_label = QLabel("진행률: 0/0 (0%)")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 통계 정보
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(200)
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        # 미리보기 영역
        preview_group = QGroupBox("빠른 미리보기")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("파일 위에 마우스를 올려보세요")
        self.preview_label.setFixedSize(240, 180)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        self.preview_info_label = QLabel("")
        self.preview_info_label.setStyleSheet("font-size: 11px; color: #666;")
        preview_layout.addWidget(self.preview_info_label)
        
        layout.addWidget(preview_group)
        layout.addStretch()
        
        return dashboard
        
    def create_action_buttons(self):
        """하단 실행 버튼들 생성"""
        layout = QHBoxLayout()
        
        self.execute_button = QPushButton("선별 실행 (선택된 것만 유지)")
        self.execute_button.clicked.connect(self.accept)
        self.execute_button.setEnabled(False)
        self.execute_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover:enabled {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        layout.addStretch()
        layout.addWidget(self.execute_button)
        layout.addWidget(cancel_button)
        
        return layout
        
    def load_users(self):
        """사용자 목록 로드"""
        if not self.capacity_finder:
            return
            
        users = self.capacity_finder.get_available_users()
        self.user_combo.clear()
        
        if users:
            self.user_combo.addItems(sorted(users))
            self.load_button.setEnabled(True)
        else:
            self.user_combo.addItem("사용 가능한 사용자 없음")
            self.load_button.setEnabled(False)
    
    def on_user_changed(self):
        """사용자 선택 변경시"""
        self.clear_thumbnails()
        self.update_stats()
        
    def load_files(self):
        """선택된 사용자의 파일 로드"""
        username = self.user_combo.currentText()
        if not username or username == "사용 가능한 사용자 없음":
            return
        
        if username not in self.capacity_finder.dic_files:
            QMessageBox.warning(self, "오류", f"사용자 '{username}'의 데이터를 찾을 수 없습니다.")
            return
        
        # 파일 리스트 가져오기
        user_data = self.capacity_finder.dic_files[username]
        self.current_files = user_data['files'].copy()
        
        # 필터 적용
        self.apply_filters()
        
    def apply_filters(self):
        """필터 적용"""
        if not self.current_files:
            return
            
        # 크기 필터
        min_size = self.size_filter_spin.value()
        filtered_files = [f for f in self.current_files if f['size'] >= min_size]
        
        # 썸네일 생성
        self.create_thumbnails(filtered_files)
        
    def create_thumbnails(self, files):
        """썸네일 위젯들 생성"""
        self.clear_thumbnails()
        
        if not files:
            return
            
        # 썸네일 위젯 생성
        for i, file_info in enumerate(files):
            formatted_size = self.format_file_size(file_info['size'])
            widget = VideoThumbnailWidget(file_info, formatted_size)
            
            # 신호 연결
            widget.selection_changed.connect(self.on_selection_changed)
            widget.preview_requested.connect(self.show_preview)
            
            # 그리드에 배치 (5열)
            row = i // 5
            col = i % 5
            self.thumbnail_layout.addWidget(widget, row, col)
            
            self.thumbnail_widgets[file_info['name']] = widget
        
        # 썸네일 추출 시작
        self.start_thumbnail_extraction(files)
        
        # 버튼 활성화
        self.select_all_btn.setEnabled(True)
        self.clear_all_btn.setEnabled(True)
        self.execute_button.setEnabled(True)
        
        self.update_stats()
        
    def start_thumbnail_extraction(self, files):
        """썸네일 추출 시작"""
        if self.thumbnail_extractor and self.thumbnail_extractor.isRunning():
            self.thumbnail_extractor.quit()
            self.thumbnail_extractor.wait()
            
        self.thumbnail_extractor = ThumbnailExtractorThread(files)
        self.thumbnail_extractor.set_path(self.current_path)
        self.thumbnail_extractor.thumbnail_ready.connect(self.on_thumbnail_ready)
        self.thumbnail_extractor.start()
        
    @pyqtSlot(str, QPixmap)
    def on_thumbnail_ready(self, file_name, thumbnail):
        """썸네일이 준비되었을 때"""
        if file_name in self.thumbnail_widgets:
            self.thumbnail_widgets[file_name].set_thumbnail(thumbnail)
            
    def clear_thumbnails(self):
        """모든 썸네일 제거"""
        for widget in self.thumbnail_widgets.values():
            widget.deleteLater()
        self.thumbnail_widgets.clear()
        self.selected_files.clear()
        
        # 썸네일 추출 중단
        if self.thumbnail_extractor and self.thumbnail_extractor.isRunning():
            self.thumbnail_extractor.quit()
            self.thumbnail_extractor.wait()
            
    def on_selection_changed(self, file_name, is_selected):
        """선택 상태 변경 처리"""
        if is_selected:
            self.selected_files.add(file_name)
        else:
            self.selected_files.discard(file_name)
            
        self.update_stats()
        
    def show_preview(self, file_name):
        """빠른 미리보기 표시"""
        if file_name in self.thumbnail_widgets:
            widget = self.thumbnail_widgets[file_name]
            file_info = widget.file_info
            
            # 썸네일을 미리보기에 표시
            if widget.thumbnail_pixmap:
                scaled_pixmap = widget.thumbnail_pixmap.scaled(240, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText(f"미리보기\n{file_name}")
                
            # 파일 정보 표시
            info_text = f"파일: {file_name}\n"
            info_text += f"크기: {self.format_file_size(file_info['size'])}"
            self.preview_info_label.setText(info_text)
            
    def select_all(self):
        """모든 파일 선택"""
        for widget in self.thumbnail_widgets.values():
            widget.set_selected(True)
            
    def clear_all(self):
        """모든 선택 해제"""
        for widget in self.thumbnail_widgets.values():
            widget.set_selected(False)
            
    def update_stats(self):
        """통계 업데이트"""
        total_files = len(self.thumbnail_widgets)
        selected_count = len(self.selected_files)
        
        # 진행률 업데이트
        if total_files > 0:
            progress = (selected_count / total_files) * 100
            self.progress_bar.setValue(int(progress))
            self.progress_label.setText(f"선택: {selected_count}/{total_files} ({progress:.1f}%)")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("선택: 0/0 (0%)")
            
        # 통계 텍스트 업데이트
        if self.thumbnail_widgets:
            selected_size = 0
            total_size = 0
            
            for file_name, widget in self.thumbnail_widgets.items():
                file_size = widget.file_info['size']
                total_size += file_size
                
                if file_name in self.selected_files:
                    selected_size += file_size
                    
            unselected_size = total_size - selected_size
            unselected_count = total_files - selected_count
            
            stats = f"📊 비주얼 선별 통계\n\n"
            stats += f"📁 전체 파일: {total_files}개\n"
            stats += f"💾 전체 용량: {self.format_file_size(total_size)}\n\n"
            
            stats += f"✅ 선택된 파일: {selected_count}개\n"
            stats += f"💾 유지할 용량: {self.format_file_size(selected_size)}\n\n"
            
            stats += f"🗑️ 삭제 예정: {unselected_count}개\n"
            stats += f"💽 절약될 용량: {self.format_file_size(unselected_size)}\n\n"
            
            if total_size > 0:
                efficiency = (unselected_size / total_size) * 100
                stats += f"📈 공간 효율성: {efficiency:.1f}% 절약"
                
            self.stats_text.setPlainText(stats)
        else:
            self.stats_text.setPlainText("파일을 로드해주세요.")
            
    def format_file_size(self, size_mb):
        """파일 사이즈 포맷팅"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
            
    def get_result(self):
        """선별 결과 반환"""
        if not self.thumbnail_widgets:
            return None
            
        files_to_keep = []
        files_to_delete = []
        
        for file_name, widget in self.thumbnail_widgets.items():
            file_info = widget.file_info
            
            if file_name in self.selected_files:
                files_to_keep.append(file_info)
            else:
                files_to_delete.append(file_info)
                
        total_savings = sum(f['size'] for f in files_to_delete)
        
        self.selection_result = {
            'files_to_keep': files_to_keep,
            'files_to_delete': files_to_delete,
            'total_savings': total_savings,
            'username': self.user_combo.currentText()
        }
        
        return self.selection_result 