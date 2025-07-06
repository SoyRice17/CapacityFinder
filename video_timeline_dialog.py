#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import re
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QLabel, QPushButton, QLineEdit,
                             QMessageBox, QScrollArea, QFrame, QSizePolicy,
                             QWidget, QToolTip)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QIcon, QPainter, QPen, QColor

class VideoTimelineDialog(QDialog):
    def __init__(self, capacity_finder, parent=None):
        super().__init__(parent)
        self.capacity_finder = capacity_finder
        self.current_path = capacity_finder.current_path
        self.all_files = []  # 모든 파일 정보 저장
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_tooltip)
        self.hover_position = None
        self.hover_file_name = None
        
        self.setWindowTitle("🎬 영상 타임라인 뷰어")
        self.setGeometry(200, 200, 1200, 800)
        self.setModal(False)
        
        self.setup_ui()
        self.load_all_files()
        
    def setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 헤더 정보
        header_layout = QHBoxLayout()
        
        # 타이틀
        title_label = QLabel("🎬 영상 타임라인 (최신순)")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        header_layout.addWidget(title_label)
        
        # 새로고침 버튼
        refresh_button = QPushButton("🔄 새로고침")
        refresh_button.clicked.connect(self.load_all_files)
        refresh_button.setMinimumHeight(35)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        header_layout.addWidget(refresh_button)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 현재 경로 표시
        self.path_label = QLabel(f"📁 현재 경로: {self.current_path}")
        self.path_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.path_label)
        
        # 파일 리스트
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_list.setMouseTracking(True)
        self.file_list.mouseMoveEvent = self.on_mouse_move
        self.file_list.leaveEvent = self.on_mouse_leave
        
        # 리스트 스타일 설정
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: white;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
                min-height: 40px;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        layout.addWidget(self.file_list)
        
        # 하단 정보
        self.info_label = QLabel("파일을 불러오는 중...")
        self.info_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #34495e;
                color: white;
                border-radius: 5px;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.info_label)
        
    def load_all_files(self):
        """모든 파일을 로드하고 시간순으로 정렬"""
        if not self.current_path or not os.path.exists(self.current_path):
            self.info_label.setText("❌ 유효하지 않은 경로입니다.")
            return
            
        self.all_files = []
        self.file_list.clear()
        
        try:
            # 모든 파일 가져오기
            all_files_raw = []
            for file_name in os.listdir(self.current_path):
                file_path = os.path.join(self.current_path, file_name)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    file_date = self.extract_date_from_filename(file_name)
                    
                    all_files_raw.append({
                        'name': file_name,
                        'path': file_path,
                        'size': file_size,
                        'date': file_date,
                        'date_str': file_date.strftime('%Y-%m-%d %H:%M:%S') if file_date else '날짜 없음'
                    })
            
            # 날짜순으로 정렬 (최신이 먼저)
            # 타임존 정보 제거하여 정렬
            all_files_raw.sort(key=lambda x: x['date'].replace(tzinfo=None) if x['date'] else datetime.min, reverse=True)
            self.all_files = all_files_raw
            
            # 리스트에 추가
            for file_info in self.all_files:
                self.add_file_to_list(file_info)
                
            # 정보 업데이트
            total_count = len(self.all_files)
            total_size = sum(f['size'] for f in self.all_files)
            self.info_label.setText(f"📊 총 {total_count}개 파일 | 총 용량: {self.format_file_size(total_size)} | 더블클릭: 재생 | 호버링: 썸네일")
            
        except Exception as e:
            self.info_label.setText(f"❌ 파일 로드 오류: {str(e)}")
            
    def add_file_to_list(self, file_info):
        """파일을 리스트에 추가"""
        item = QListWidgetItem()
        
        # 파일명과 정보를 포함한 텍스트 생성
        file_name = file_info['name']
        file_size = self.format_file_size(file_info['size'])
        date_str = file_info['date_str']
        
        # 채널명 추출
        channel_name = self.capacity_finder.file_name_handle(file_name)
        channel_display = f"[{channel_name}]" if channel_name else "[알 수 없음]"
        
        # 표시 텍스트
        display_text = f"{channel_display} {file_name}\n📅 {date_str} | 📦 {file_size}"
        
        item.setText(display_text)
        item.setData(Qt.UserRole, file_info)  # 파일 정보 저장
        
        # 최근 파일 강조
        if file_info['date']:
            try:
                # 타임존 정보 제거하여 비교
                file_date_naive = file_info['date'].replace(tzinfo=None)
                now_naive = datetime.now()
                days_diff = (now_naive - file_date_naive).days
                if days_diff < 7:
                    item.setIcon(QIcon("🔥"))  # 최근 파일 표시
            except Exception as e:
                print(f"날짜 비교 오류: {e}")
                # 오류 발생 시 그냥 넘어감
            
        self.file_list.addItem(item)
        
    def on_item_double_clicked(self, item):
        """파일 더블클릭 시 영상 재생"""
        file_info = item.data(Qt.UserRole)
        if not file_info:
            return
            
        file_path = file_info['path']
        
        try:
            # 운영체제별 기본 플레이어로 실행
            if sys.platform.startswith('win'):
                os.startfile(file_path)
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
                
            print(f"영상 재생: {file_info['name']}")
            
        except Exception as e:
            QMessageBox.warning(self, "재생 오류", f"영상을 재생할 수 없습니다:\n{str(e)}")
            
    def on_mouse_move(self, event):
        """마우스 이동 시 호버링 처리"""
        # 원래 mouseMoveEvent 호출
        QListWidget.mouseMoveEvent(self.file_list, event)
        
        # 아이템 위에 마우스가 있는지 확인
        item = self.file_list.itemAt(event.pos())
        if item:
            file_info = item.data(Qt.UserRole)
            if file_info:
                self.hover_position = event.globalPos()
                self.hover_file_name = file_info['name']
                
                # 타이머 시작 (500ms 후 툴팁 표시)
                self.tooltip_timer.start(500)
        else:
            self.tooltip_timer.stop()
            QToolTip.hideText()
            
    def on_mouse_leave(self, event):
        """마우스가 리스트를 벗어날 때"""
        QListWidget.leaveEvent(self.file_list, event)
        self.tooltip_timer.stop()
        QToolTip.hideText()
        
    def show_tooltip(self):
        """썸네일 툴팁 표시"""
        if not self.hover_file_name or not self.hover_position:
            return
            
        # 썸네일 경로 생성 (메모리 규칙 사용)
        thumbnail_path = self.get_thumbnail_path(self.hover_file_name)
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            # 썸네일 이미지 로드
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                # 크기 조정 (최대 300x300)
                scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # 임시 라벨 생성 (툴팁용)
                tooltip_label = QLabel()
                tooltip_label.setPixmap(scaled_pixmap)
                tooltip_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #3498db;
                        border-radius: 8px;
                        padding: 4px;
                        background-color: white;
                    }
                """)
                
                # 툴팁 표시
                QToolTip.showText(self.hover_position, "", self, tooltip_label.rect())
                
                # 커스텀 툴팁으로 이미지 표시
                self.show_custom_tooltip(scaled_pixmap)
        else:
            # 썸네일이 없는 경우 파일 정보 표시
            file_info = f"📁 {self.hover_file_name}\n🖼️ 썸네일 없음"
            QToolTip.showText(self.hover_position, file_info)
            
    def show_custom_tooltip(self, pixmap):
        """커스텀 이미지 툴팁 표시"""
        # 간단한 툴팁 텍스트로 대체 (PyQt5 한계)
        file_info = f"📁 {self.hover_file_name}\n🖼️ 썸네일 로드됨"
        QToolTip.showText(self.hover_position, file_info)
        
    def get_thumbnail_path(self, file_name):
        """파일명으로부터 썸네일 경로 생성"""
        if not self.current_path:
            return None
            
        try:
            # 현재 경로: \\MYCLOUDEX2ULTRA\Private\capturegem
            # 썸네일 경로: \\MYCLOUDEX2ULTRA\Private\metadata\{파일명_확장자제거}\image_grid_large.jpg
            
            # 확장자 제거
            file_name_without_ext = os.path.splitext(file_name)[0]
            
            # 부모 디렉토리 가져오기
            parent_dir = os.path.dirname(self.current_path)
            
            # metadata 폴더 경로
            metadata_dir = os.path.join(parent_dir, "metadata")
            
            # 썸네일 파일 경로
            thumbnail_path = os.path.join(metadata_dir, file_name_without_ext, "image_grid_large.jpg")
            
            return thumbnail_path
            
        except Exception as e:
            print(f"썸네일 경로 생성 오류: {e}")
            return None
            
    def extract_date_from_filename(self, file_name):
        """파일명에서 날짜 추출 (CapacityFinder와 동일한 로직)"""
        try:
            # 날짜 패턴 (2025-06-26T15_09_46+09_00 형식)
            date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}[+-]\d{2}_\d{2}')
            date_match = date_pattern.search(file_name)
            if date_match:
                date_str = date_match.group()
                # 2025-06-26T15_09_46+09_00 -> datetime 변환
                file_date = datetime.fromisoformat(date_str.replace('_', ':'))
                return file_date
        except Exception as e:
            print(f"날짜 추출 오류: {file_name}, 에러: {e}")
        return None
        
    def format_file_size(self, size_mb):
        """파일 크기 포맷팅"""
        if size_mb >= 1024:
            return f"{size_mb/1024:.2f} GB"
        else:
            return f"{size_mb:.2f} MB" 