import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QTextEdit, QSplitter)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

class UserSiteComparisonDialog(QDialog):
    def __init__(self, capacity_finder, current_path, parent=None):
        super().__init__(parent)
        self.capacity_finder = capacity_finder
        self.current_path = current_path
        self.comparison_result = None
        
        self.setWindowTitle("특정 유저 사이트 비교")
        self.setGeometry(200, 200, 900, 600)
        self.setModal(True)
        
        self.init_ui()
        self.load_users()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 사용자 선택 섹션
        user_section = QHBoxLayout()
        user_section.addWidget(QLabel("사용자 선택:"))
        
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(200)
        self.user_combo.currentTextChanged.connect(self.on_user_changed)
        user_section.addWidget(self.user_combo)
        
        self.analyze_button = QPushButton("분석")
        self.analyze_button.clicked.connect(self.analyze_user_sites)
        self.analyze_button.setEnabled(False)
        user_section.addWidget(self.analyze_button)
        
        user_section.addStretch()
        layout.addLayout(user_section)
        
        # 분할기로 상단과 하단 구분
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # 비교 결과 트리 위젯
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["날짜/사이트/파일", "용량", "상태"])
        self.result_tree.setColumnWidth(0, 400)
        self.result_tree.setColumnWidth(1, 120)
        self.result_tree.setColumnWidth(2, 100)
        splitter.addWidget(self.result_tree)
        
        # 요약 정보 텍스트
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(150)
        self.summary_text.setReadOnly(True)
        font = QFont("맑은 고딕", 9)
        self.summary_text.setFont(font)
        splitter.addWidget(self.summary_text)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        self.execute_button = QPushButton("삭제 실행")
        self.execute_button.clicked.connect(self.accept)
        self.execute_button.setEnabled(False)
        self.execute_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #c0392b;
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
        
        button_layout.addStretch()
        button_layout.addWidget(self.execute_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def load_users(self):
        """사용자 목록 로드"""
        if not self.capacity_finder:
            return
            
        users = self.capacity_finder.get_available_users()
        self.user_combo.clear()
        
        if users:
            self.user_combo.addItems(sorted(users))
            self.analyze_button.setEnabled(True)
        else:
            self.user_combo.addItem("사용 가능한 사용자 없음")
            self.analyze_button.setEnabled(False)
    
    def on_user_changed(self):
        """사용자 선택 변경시"""
        self.result_tree.clear()
        self.summary_text.clear()
        self.execute_button.setEnabled(False)
        self.comparison_result = None
    
    def analyze_user_sites(self):
        """선택된 사용자의 사이트 비교 분석"""
        username = self.user_combo.currentText()
        if not username or username == "사용 가능한 사용자 없음":
            return
        
        # 분석 실행
        result = self.capacity_finder.compare_user_sites(username)
        
        if not result:
            QMessageBox.warning(self, "분석 실패", f"사용자 '{username}'의 데이터를 분석할 수 없습니다.")
            return
        
        if not result['comparison_results']:
            QMessageBox.information(self, "분석 결과", 
                                  f"사용자 '{username}'에게는 같은 날짜의 중복 사이트 파일이 없습니다.")
            return
        
        self.comparison_result = result
        self.display_results(result)
    
    def display_results(self, result):
        """분석 결과 표시"""
        self.result_tree.clear()
        
        comparison_results = result['comparison_results']
        files_to_delete = result['files_to_delete']
        total_savings = result['total_savings']
        
        # 트리에 결과 표시
        for comp_result in comparison_results:
            date = comp_result['date']
            keep_site = comp_result['keep_site']
            delete_sites = comp_result['delete_sites']
            
            # 날짜 노드 생성
            date_item = QTreeWidgetItem(self.result_tree)
            date_item.setText(0, f"📅 {date}")
            date_item.setText(1, "")
            date_item.setText(2, "")
            
            # 각 사이트 노드 생성
            for site, site_data in comp_result['sites'].items():
                site_item = QTreeWidgetItem(date_item)
                site_name = site.upper()
                site_size = self.format_file_size(site_data['total_size'])
                
                if site == keep_site:
                    site_item.setText(0, f"📦 {site_name}")
                    site_item.setText(1, site_size)
                    site_item.setText(2, "✅ 유지")
                    site_item.setBackground(2, QColor(200, 255, 200))  # 연한 초록색
                else:
                    site_item.setText(0, f"📦 {site_name}")
                    site_item.setText(1, site_size)
                    site_item.setText(2, "❌ 삭제")
                    site_item.setBackground(2, QColor(255, 200, 200))  # 연한 빨간색
                
                # 파일 노드들 생성
                for file_info in site_data['files']:
                    file_item = QTreeWidgetItem(site_item)
                    file_item.setText(0, f"📄 {file_info['name']}")
                    file_item.setText(1, self.format_file_size(file_info['size']))
                    
                    if site == keep_site:
                        file_item.setText(2, "유지")
                        file_item.setBackground(2, QColor(230, 255, 230))
                    else:
                        file_item.setText(2, "삭제")
                        file_item.setBackground(2, QColor(255, 230, 230))
        
        # 트리 확장
        self.result_tree.expandAll()
        
        # 요약 정보 표시
        summary = f"🔍 분석 결과 - 사용자: {result['username']}\n\n"
        summary += f"📊 총 {len(comparison_results)}개의 날짜에서 중복 사이트 발견\n"
        summary += f"🗑️ 삭제 대상 파일: {len(files_to_delete)}개\n"
        summary += f"💾 절약 가능한 용량: {self.format_file_size(total_savings)}\n\n"
        
        summary += "📋 세부 내용:\n"
        for comp_result in comparison_results:
            date = comp_result['date']
            keep_site = comp_result['keep_site'].upper()
            delete_sites = [s.upper() for s in comp_result['delete_sites']]
            
            summary += f"• {date}: {keep_site} 유지, {', '.join(delete_sites)} 삭제\n"
        
        if total_savings > 0:
            summary += f"\n✅ '삭제 실행' 버튼을 클릭하여 중복 파일을 정리하세요."
            self.execute_button.setEnabled(True)
        else:
            summary += f"\n❌ 삭제할 파일이 없습니다."
            self.execute_button.setEnabled(False)
        
        self.summary_text.setPlainText(summary)
    
    def format_file_size(self, size_mb):
        """파일 사이즈 포맷팅"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
    
    def get_result(self):
        """다이얼로그 결과 반환"""
        return self.comparison_result 