#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QProgressBar, QFrame, QScrollArea,
                             QWidget, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class ModelDecisionDialog(QDialog):
    """모델별 결정을 위한 팝업 다이얼로그"""
    
    def __init__(self, decision_data, current_path, parent=None):
        super().__init__(parent)
        self.decision_data = decision_data  # 결정할 모델 리스트
        self.current_path = current_path    # 파일 경로
        self.current_index = 0
        self.decisions = {}  # {username: 'keep'/'delete'/'skip'}
        self.total_savings = 0
        
        self.setup_ui()
        self.show_current_model()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("📋 모델 정리 도우미")
        self.setGeometry(200, 200, 800, 650)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 제목 라벨
        title_label = QLabel("🎯 용량 큰 순서로 모델을 검토하여 정리하세요")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; padding: 10px; background-color: #ecf0f1; border-radius: 5px;")
        layout.addWidget(title_label)
        
        # 진행률 표시
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        
        # 모델 정보 영역
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Box)
        info_frame.setStyleSheet("QFrame { border: 2px solid #95a5a6; border-radius: 8px; padding: 10px; }")
        info_layout = QVBoxLayout(info_frame)
        
        self.model_name_label = QLabel()
        self.model_name_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; padding: 5px;")
        
        self.model_stats_label = QLabel()
        self.model_stats_label.setStyleSheet("font-size: 14px; color: #7f8c8d; padding: 5px;")
        
        info_layout.addWidget(self.model_name_label)
        info_layout.addWidget(self.model_stats_label)
        layout.addWidget(info_frame)
        
        # 샘플 파일 영역 (스크롤 가능)
        sample_header = QLabel("📁 대표 파일들 (더블클릭하면 파일이 열립니다):")
        sample_header.setStyleSheet("font-weight: bold; color: #34495e; font-size: 13px;")
        layout.addWidget(sample_header)
        
        self.sample_area = QScrollArea()
        self.sample_widget = QWidget()
        self.sample_layout = QVBoxLayout(self.sample_widget)
        self.sample_area.setWidget(self.sample_widget)
        self.sample_area.setWidgetResizable(True)
        self.sample_area.setMaximumHeight(200)
        self.sample_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.sample_area)
        
        # 결정 버튼들
        decision_label = QLabel("💭 이 모델을 어떻게 처리하시겠습니까?")
        decision_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 14px; margin-top: 10px;")
        layout.addWidget(decision_label)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.delete_button = QPushButton("🗑️ 삭제 (D)")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.delete_button.setShortcut('D')
        self.delete_button.clicked.connect(lambda: self.make_decision('delete'))
        
        self.keep_button = QPushButton("✅ 유지 (K)")
        self.keep_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.keep_button.setShortcut('K')
        self.keep_button.clicked.connect(lambda: self.make_decision('keep'))
        
        self.skip_button = QPushButton("⏭️ 나중에 (S)")
        self.skip_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        self.skip_button.setShortcut('S')
        self.skip_button.clicked.connect(lambda: self.make_decision('skip'))
        
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.keep_button)
        button_layout.addWidget(self.skip_button)
        layout.addLayout(button_layout)
        
        # 네비게이션 버튼들
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)
        
        self.prev_button = QPushButton("◀️ 이전")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover:enabled {
                background-color: #7f8c8d;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.prev_button.clicked.connect(self.go_previous)
        
        self.next_button = QPushButton("다음 ▶️")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover:enabled {
                background-color: #7f8c8d;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.next_button.clicked.connect(self.go_next)
        
        self.finish_button = QPushButton("🏁 완료")
        self.finish_button.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        self.finish_button.clicked.connect(self.finish_decisions)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.finish_button)
        layout.addLayout(nav_layout)
        
        # 현재 절약 용량 표시
        self.savings_label = QLabel("💾 현재까지 절약 예상: 0MB")
        self.savings_label.setStyleSheet("""
            font-weight: bold; 
            color: #27ae60; 
            font-size: 14px; 
            padding: 10px; 
            background-color: #d5f4e6; 
            border-radius: 5px;
        """)
        layout.addWidget(self.savings_label)
    
    def show_current_model(self):
        """현재 모델 정보 표시"""
        if self.current_index >= len(self.decision_data):
            self.finish_decisions()
            return
        
        current = self.decision_data[self.current_index]
        
        # 진행률 업데이트
        progress = (self.current_index + 1) / len(self.decision_data) * 100
        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(f"진행: {self.current_index + 1}/{len(self.decision_data)} 모델")
        
        # 모델 정보
        self.model_name_label.setText(f"📊 {current['username']}")
        stats_text = (f"📁 {current['file_count']}개 파일 | "
                     f"💾 {self.format_file_size(current['total_size'])} | "
                     f"💰 삭제시 절약: {self.format_file_size(current['potential_savings'])}")
        self.model_stats_label.setText(stats_text)
        
        # 샘플 파일들 표시
        self.clear_sample_files()
        for file_info in current['sample_files']:
            file_label = ClickableLabel(f"📄 {file_info['name']} ({self.format_file_size(file_info['size'])})")
            file_label.setStyleSheet("""
                padding: 8px; 
                background-color: #ecf0f1; 
                margin: 2px; 
                border-radius: 5px;
                border: 1px solid #bdc3c7;
            """)
            file_label.setWordWrap(True)
            
            # 파일 더블클릭 이벤트
            file_path = os.path.join(self.current_path, file_info['name']) if self.current_path else None
            file_label.mouseDoubleClickEvent = lambda event, path=file_path: self.open_file(path)
            
            self.sample_layout.addWidget(file_label)
        
        # 버튼 상태 업데이트
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.decision_data) - 1)
    
    def open_file(self, file_path):
        """파일 열기"""
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "파일 없음", f"파일을 찾을 수 없습니다:\n{file_path}")
            return
        
        try:
            if sys.platform.startswith('win'):  # Windows
                os.startfile(file_path)
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
            print(f"파일 열기: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "파일 열기 오류", f"파일을 열 수 없습니다:\n{str(e)}")
    
    def make_decision(self, decision):
        """결정 내리기"""
        current = self.decision_data[self.current_index]
        
        # 이전 결정이 있었다면 절약 용량에서 제거
        if current['username'] in self.decisions:
            if self.decisions[current['username']] == 'delete':
                self.total_savings -= current['potential_savings']
        
        # 새로운 결정 저장
        self.decisions[current['username']] = decision
        
        # 절약 용량 계산
        if decision == 'delete':
            self.total_savings += current['potential_savings']
        
        self.savings_label.setText(f"💾 현재까지 절약 예상: {self.format_file_size(self.total_savings)}")
        
        # 다음 모델로
        if self.current_index < len(self.decision_data) - 1:
            self.current_index += 1
            self.show_current_model()
        else:
            self.finish_decisions()
    
    def go_previous(self):
        """이전 모델로"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_model()
    
    def go_next(self):
        """다음 모델로 (결정 없이)"""
        if self.current_index < len(self.decision_data) - 1:
            self.current_index += 1
            self.show_current_model()
    
    def clear_sample_files(self):
        """샘플 파일 영역 클리어"""
        while self.sample_layout.count():
            child = self.sample_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def finish_decisions(self):
        """결정 완료"""
        delete_count = len([d for d in self.decisions.values() if d == 'delete'])
        keep_count = len([d for d in self.decisions.values() if d == 'keep'])
        skip_count = len([d for d in self.decisions.values() if d == 'skip'])
        
        if delete_count == 0:
            QMessageBox.information(self, "완료", "삭제할 모델이 선택되지 않았습니다.")
        else:
            msg = QMessageBox()
            msg.setWindowTitle("결정 완료")
            msg.setText(f"""
📊 결정 결과:
🗑️ 삭제: {delete_count}개 모델
✅ 유지: {keep_count}개 모델  
⏭️ 나중에: {skip_count}개 모델

💾 총 절약 예상: {self.format_file_size(self.total_savings)}

실제 삭제를 진행하시겠습니까?
            """)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            
            if msg.exec_() == QMessageBox.Yes:
                self.accept()
                return
        
        # 취소 또는 삭제할 것이 없는 경우
        self.reject()
    
    def get_decisions(self):
        """결정 결과 반환"""
        return self.decisions, self.total_savings
    
    def format_file_size(self, size_mb):
        """파일 크기 포맷팅"""
        if size_mb >= 1024:
            return f"{size_mb/1024:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"


class ClickableLabel(QLabel):
    """클릭 가능한 라벨"""
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("""
            QLabel:hover {
                background-color: #d6eaf8;
                cursor: pointer;
            }
        """) 