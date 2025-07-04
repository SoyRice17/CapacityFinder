import sys
import os
import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QTextEdit, QSplitter, QCheckBox, QGroupBox,
                             QScrollArea, QWidget, QFrame, QTabWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

class UserSiteComparisonDialog(QDialog):
    def __init__(self, capacity_finder, current_path, parent=None):
        super().__init__(parent)
        self.capacity_finder = capacity_finder
        self.current_path = current_path
        self.comparison_result = None
        
        self.setWindowTitle("🔍 사용자 사이트 비교")
        self.setGeometry(200, 200, 1100, 750)
        self.setModal(True)
        
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 탭 1: 단일 사용자 비교
        self.setup_single_user_tab()
        
        # 탭 2: 그룹 비교
        self.setup_group_comparison_tab()
        
        # 공통 버튼 레이아웃
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
        
    def setup_single_user_tab(self):
        """단일 사용자 비교 탭 설정"""
        single_tab = QWidget()
        self.tab_widget.addTab(single_tab, "📱 단일 사용자 비교")
        
        layout = QVBoxLayout(single_tab)
        
        # 설명 라벨
        desc_label = QLabel("💡 같은 사용자명으로 여러 사이트에 있는 중복 파일을 찾습니다")
        desc_label.setStyleSheet("""
            QLabel {
                background-color: #e8f4fd;
                border: 1px solid #bee5eb;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                color: #0c5460;
            }
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 사용자 선택
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("사용자:"))
        
        self.single_user_combo = QComboBox()
        self.single_user_combo.setMinimumWidth(250)
        self.single_user_combo.currentTextChanged.connect(self.on_single_user_changed)
        user_layout.addWidget(self.single_user_combo)
        
        self.single_compare_button = QPushButton("🔍 비교 실행")
        self.single_compare_button.clicked.connect(self.compare_single_user)
        self.single_compare_button.setEnabled(False)
        self.single_compare_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        user_layout.addWidget(self.single_compare_button)
        user_layout.addStretch()
        
        layout.addLayout(user_layout)
        
        # 결과 표시
        self.setup_single_results(layout)
        
        # 사용자 목록 로드
        self.load_single_users()
        
    def setup_group_comparison_tab(self):
        """그룹 비교 탭 설정"""
        group_tab = QWidget()
        self.tab_widget.addTab(group_tab, "👥 그룹 비교 (닉네임 변경)")
        
        layout = QVBoxLayout(group_tab)
        
        # 그룹 기능 변수들
        self.selected_users = []
        self.similar_user_checkboxes = {}
        
        # 설명 라벨
        desc_label = QLabel("💡 같은 인물의 다른 닉네임들을 그룹으로 묶어서 사이트별 중복 파일을 찾습니다")
        desc_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                color: #856404;
            }
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # 메인 사용자 선택 섹션
        main_user_group = QGroupBox("1️⃣ 메인 사용자 선택")
        main_user_layout = QHBoxLayout(main_user_group)
        
        main_user_layout.addWidget(QLabel("기준 사용자:"))
        
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(250)
        self.user_combo.currentTextChanged.connect(self.on_user_changed)
        main_user_layout.addWidget(self.user_combo)
        
        self.find_similar_button = QPushButton("🔍 유사 닉네임 찾기")
        self.find_similar_button.clicked.connect(self.find_similar_users)
        self.find_similar_button.setEnabled(False)
        self.find_similar_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        main_user_layout.addWidget(self.find_similar_button)
        
        main_user_layout.addStretch()
        layout.addWidget(main_user_group)
        
        # 유사 사용자 선택 섹션
        similar_user_group = QGroupBox("2️⃣ 유사 사용자 선택 (같은 인물의 다른 닉네임)")
        similar_user_layout = QVBoxLayout(similar_user_group)
        
        # 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setMaximumHeight(150)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #f8f9fa;
            }
        """)
        
        self.similar_users_widget = QWidget()
        self.similar_users_layout = QVBoxLayout(self.similar_users_widget)
        scroll_area.setWidget(self.similar_users_widget)
        
        self.no_similar_label = QLabel("메인 사용자를 선택하고 '유사 닉네임 찾기'를 클릭하세요")
        self.no_similar_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 20px;")
        self.no_similar_label.setAlignment(Qt.AlignCenter)
        self.similar_users_layout.addWidget(self.no_similar_label)
        
        similar_user_layout.addWidget(scroll_area)
        
        # 선택된 그룹 표시
        group_info_layout = QHBoxLayout()
        self.group_info_label = QLabel("선택된 그룹: 없음")
        self.group_info_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        group_info_layout.addWidget(self.group_info_label)
        
        self.analyze_button = QPushButton("📊 그룹 분석 실행")
        self.analyze_button.clicked.connect(self.analyze_user_group)
        self.analyze_button.setEnabled(False)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        group_info_layout.addWidget(self.analyze_button)
        
        similar_user_layout.addLayout(group_info_layout)
        layout.addWidget(similar_user_group)
        
        # 그룹 결과 표시
        self.setup_group_results(layout)
        
        # 그룹 사용자 목록 로드
        self.load_group_users()
        
    def setup_single_results(self, layout):
        """단일 사용자 결과 영역 설정"""
        # 분할기로 상단과 하단 구분
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # 비교 결과 트리 위젯
        self.single_result_tree = QTreeWidget()
        self.single_result_tree.setHeaderLabels(["날짜/사이트/파일", "용량", "상태"])
        self.single_result_tree.setColumnWidth(0, 400)
        self.single_result_tree.setColumnWidth(1, 120)
        self.single_result_tree.setColumnWidth(2, 100)
        splitter.addWidget(self.single_result_tree)
        
        # 요약 정보 텍스트
        self.single_summary_text = QTextEdit()
        self.single_summary_text.setMaximumHeight(150)
        self.single_summary_text.setReadOnly(True)
        font = QFont("맑은 고딕", 9)
        self.single_summary_text.setFont(font)
        splitter.addWidget(self.single_summary_text)
        
    def setup_group_results(self, layout):
        """그룹 결과 영역 설정"""
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
    
    def load_single_users(self):
        """단일 사용자 목록 로드"""
        if not self.capacity_finder:
            return
            
        users = self.capacity_finder.get_available_users()
        self.single_user_combo.clear()
        
        if users:
            self.single_user_combo.addItems(sorted(users))
            self.single_compare_button.setEnabled(True)
        else:
            self.single_user_combo.addItem("사용 가능한 사용자 없음")
            self.single_compare_button.setEnabled(False)
    
    def load_group_users(self):
        """그룹 사용자 목록 로드"""
        if not self.capacity_finder:
            return
            
        users = self.capacity_finder.get_available_users()
        self.user_combo.clear()
        
        if users:
            self.user_combo.addItems(sorted(users))
            self.find_similar_button.setEnabled(True)
        else:
            self.user_combo.addItem("사용 가능한 사용자 없음")
            self.find_similar_button.setEnabled(False)
    
    def on_single_user_changed(self):
        """단일 사용자 선택 변경시"""
        self.single_result_tree.clear()
        self.single_summary_text.clear()
        if hasattr(self, 'execute_button'):  # 버튼이 생성된 후에만 호출
            self.execute_button.setEnabled(False)
        self.comparison_result = None
        
        current_user = self.single_user_combo.currentText()
        self.single_compare_button.setEnabled(bool(current_user and current_user != "사용 가능한 사용자 없음"))
    
    def compare_single_user(self):
        """단일 사용자 비교 실행"""
        user = self.single_user_combo.currentText()
        if not user or user == "사용 가능한 사용자 없음":
            return
            
        try:
            # 단일 사용자 비교 실행
            result = self.capacity_finder.compare_user_sites(user)
            self.comparison_result = result
            
            if result and 'results' in result:
                self.display_single_results(result)
                if hasattr(self, 'execute_button'):
                    self.execute_button.setEnabled(True)
            else:
                QMessageBox.information(self, "정보", f"사용자 '{user}'에 대한 중복 파일이 없습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"비교 중 오류 발생: {str(e)}")
    
    def display_single_results(self, result):
        """단일 사용자 결과 표시"""
        self.single_result_tree.clear()
        
        if not result or 'results' not in result:
            return
            
        total_deletable_size = 0
        total_deletable_count = 0
        site_stats = {}
        
        # 날짜별로 그룹화
        date_groups = {}
        for file_data in result['results']:
            date = file_data['date']
            if date not in date_groups:
                date_groups[date] = []
            date_groups[date].append(file_data)
        
        # 날짜별로 트리 구성
        for date in sorted(date_groups.keys(), reverse=True):
            date_item = QTreeWidgetItem(self.single_result_tree)
            date_item.setText(0, f"📅 {date}")
            date_item.setExpanded(True)
            
            # 사이트별로 그룹화
            site_groups = {}
            for file_data in date_groups[date]:
                for site_info in file_data['sites']:
                    site = site_info['site']
                    if site not in site_groups:
                        site_groups[site] = []
                    site_groups[site].append({
                        'filename': file_data['filename'],
                        'size': file_data['size'],
                        'path': site_info['path'],
                        'deletable': site_info.get('deletable', False)
                    })
            
            # 사이트별로 표시
            for site in sorted(site_groups.keys()):
                site_item = QTreeWidgetItem(date_item)
                site_count = len(site_groups[site])
                site_item.setText(0, f"🌐 {site} ({site_count}개 파일)")
                site_item.setExpanded(True)
                
                if site not in site_stats:
                    site_stats[site] = {'total': 0, 'deletable': 0, 'size': 0}
                
                # 파일별로 표시
                for file_info in site_groups[site]:
                    file_item = QTreeWidgetItem(site_item)
                    file_item.setText(0, f"📄 {file_info['filename']}")
                    file_item.setText(1, self.format_file_size(file_info['size']))
                    
                    site_stats[site]['total'] += 1
                    
                    if file_info['deletable']:
                        file_item.setText(2, "삭제 대상")
                        file_item.setBackground(2, QColor(255, 200, 200))
                        total_deletable_count += 1
                        total_deletable_size += file_info['size']
                        site_stats[site]['deletable'] += 1
                        site_stats[site]['size'] += file_info['size']
                    else:
                        file_item.setText(2, "보존")
                        file_item.setBackground(2, QColor(200, 255, 200))
        
        # 요약 정보 표시
        summary_lines = []
        summary_lines.append("=== 📊 단일 사용자 비교 결과 요약 ===\n")
        summary_lines.append(f"🔍 대상 사용자: {self.single_user_combo.currentText()}")
        summary_lines.append(f"📁 삭제 가능한 파일: {total_deletable_count}개")
        summary_lines.append(f"💾 절약 가능한 용량: {self.format_file_size(total_deletable_size)}\n")
        
        if site_stats:
            summary_lines.append("📈 사이트별 통계:")
            for site, stats in site_stats.items():
                if stats['deletable'] > 0:
                    summary_lines.append(f"  🌐 {site}: {stats['deletable']}/{stats['total']}개 삭제 예정 ({self.format_file_size(stats['size'])})")
        
        self.single_summary_text.setPlainText('\n'.join(summary_lines))
    
    def on_user_changed(self):
        """그룹 사용자 선택 변경시"""
        self.result_tree.clear()
        self.summary_text.clear()
        if hasattr(self, 'execute_button'):  # 버튼이 생성된 후에만 호출
            self.execute_button.setEnabled(False)
        self.comparison_result = None
        self.selected_users = []
        
        # 유사 사용자 영역 초기화
        self.clear_similar_users()
        self.update_group_selection()
        
        # 찾기 버튼 활성화
        current_user = self.user_combo.currentText()
        self.find_similar_button.setEnabled(bool(current_user and current_user != "사용 가능한 사용자 없음"))
    
    def clear_similar_users(self):
        """유사 사용자 목록 클리어"""
        # 기존 체크박스들 제거
        for checkbox in self.similar_user_checkboxes.values():
            checkbox.deleteLater()
        self.similar_user_checkboxes.clear()
        
        # 기본 메시지 표시
        self.no_similar_label.setText("메인 사용자를 선택하고 '유사 닉네임 찾기'를 클릭하세요")
        self.no_similar_label.setVisible(True)
    
    def find_similar_users(self):
        """유사한 사용자명 찾기"""
        main_user = self.user_combo.currentText()
        if not main_user or main_user == "사용 가능한 사용자 없음":
            return
            
        # 모든 사용자 목록 가져오기
        all_users = self.capacity_finder.get_available_users()
        if not all_users:
            return
            
        # 유사한 사용자 찾기
        similar_users = []
        for user in all_users:
            if user != main_user and self.is_similar_username(main_user, user):
                similar_users.append(user)
        
        # 결과 표시
        self.display_similar_users(main_user, similar_users)
    
    def is_similar_username(self, user1, user2):
        """두 사용자명이 유사한지 판단"""
        # 1. 대소문자 무시하고 비교
        if user1.lower() == user2.lower():
            return True
            
        # 2. 특수문자, 숫자 제거하고 비교
        clean1 = re.sub(r'[^a-zA-Z가-힣]', '', user1).lower()
        clean2 = re.sub(r'[^a-zA-Z가-힣]', '', user2).lower()
        if clean1 and clean2 and clean1 == clean2:
            return True
            
        # 3. 부분 포함 관계 확인 (더 긴 문자열에서 짧은 문자열 포함)
        if len(user1) >= 3 and len(user2) >= 3:
            shorter = user1 if len(user1) < len(user2) else user2
            longer = user2 if len(user1) < len(user2) else user1
            if shorter.lower() in longer.lower():
                return True
        
        # 4. Levenshtein distance로 유사도 확인 (80% 이상)
        max_len = max(len(user1), len(user2))
        if max_len > 0:
            distance = self.levenshtein_distance(user1.lower(), user2.lower())
            similarity = (max_len - distance) / max_len
            if similarity >= 0.8:
                return True
                
        return False
    
    def levenshtein_distance(self, s1, s2):
        """Levenshtein distance 계산"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def display_similar_users(self, main_user, similar_users):
        """유사 사용자 표시"""
        # 기존 체크박스들 제거
        self.clear_similar_users()
        
        if not similar_users:
            self.no_similar_label.setText(f"'{main_user}'와 유사한 닉네임을 찾을 수 없습니다.")
            self.no_similar_label.setVisible(True)
            return
        
        self.no_similar_label.setVisible(False)
        
        # 메인 사용자는 기본으로 선택됨
        main_checkbox = QCheckBox(f"👑 {main_user} (메인)")
        main_checkbox.setChecked(True)
        main_checkbox.setEnabled(False)  # 메인 사용자는 항상 선택됨
        main_checkbox.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.similar_users_layout.addWidget(main_checkbox)
        self.similar_user_checkboxes[main_user] = main_checkbox
        
        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #bdc3c7;")
        self.similar_users_layout.addWidget(separator)
        
        # 유사 사용자들
        for user in sorted(similar_users):
            checkbox = QCheckBox(f"👤 {user}")
            checkbox.stateChanged.connect(self.on_similar_user_checked)
            checkbox.setStyleSheet("color: #34495e;")
            self.similar_users_layout.addWidget(checkbox)
            self.similar_user_checkboxes[user] = checkbox
        
        # 초기 선택 업데이트
        self.update_group_selection()
    
    def on_similar_user_checked(self):
        """유사 사용자 체크박스 상태 변경"""
        self.update_group_selection()
    
    def update_group_selection(self):
        """그룹 선택 상태 업데이트"""
        # 선택된 사용자들 수집
        self.selected_users = []
        for user, checkbox in self.similar_user_checkboxes.items():
            if checkbox.isChecked():
                self.selected_users.append(user)
        
        # 그룹 정보 업데이트
        if self.selected_users:
            user_list = ", ".join(self.selected_users)
            self.group_info_label.setText(f"선택된 그룹: {user_list}")
            self.analyze_button.setEnabled(len(self.selected_users) >= 1)
        else:
            self.group_info_label.setText("선택된 그룹: 없음")
            self.analyze_button.setEnabled(False)
    
    def analyze_user_group(self):
        """사용자 그룹 분석 실행"""
        if not self.selected_users:
            QMessageBox.warning(self, "경고", "분석할 사용자를 선택해주세요.")
            return
            
        try:
            # 그룹 분석 실행
            result = self.compare_user_group_fallback(self.selected_users)
            self.comparison_result = result
            
            if result and 'results' in result:
                self.display_results(result)
                if hasattr(self, 'execute_button'):
                    self.execute_button.setEnabled(True)
            else:
                QMessageBox.information(self, "정보", "선택된 그룹에 대한 중복 파일이 없습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"그룹 분석 중 오류 발생: {str(e)}")
    
    def compare_user_group_fallback(self, user_group):
        """사용자 그룹 비교 (폴백 메서드)"""
        all_results = []
        
        # 각 사용자별로 개별 비교 수행
        for user in user_group:
            try:
                user_result = self.capacity_finder.compare_user_sites(user)
                if user_result and 'results' in user_result:
                    # 각 결과에 사용자 정보 추가
                    for result in user_result['results']:
                        result['source_user'] = user
                    all_results.extend(user_result['results'])
            except Exception as e:
                print(f"사용자 {user} 비교 중 오류: {e}")
                continue
        
        # 파일명과 크기로 그룹화하여 중복 찾기
        file_groups = {}
        for result in all_results:
            key = (result['filename'], result['size'])
            if key not in file_groups:
                file_groups[key] = []
            file_groups[key].append(result)
        
        # 중복 파일만 필터링
        duplicate_results = []
        for key, group in file_groups.items():
            if len(group) > 1:
                # 가장 오래된 파일을 보존, 나머지는 삭제 대상
                sorted_group = sorted(group, key=lambda x: x['date'])
                
                for i, result in enumerate(sorted_group):
                    for site_info in result['sites']:
                        site_info['deletable'] = (i > 0)  # 첫 번째(가장 오래된) 것만 보존
                
                duplicate_results.extend(sorted_group)
        
        return {'results': duplicate_results} if duplicate_results else None
    
    def display_results(self, result):
        """그룹 결과 표시"""
        self.result_tree.clear()
        
        if not result or 'results' not in result:
            return
            
        total_deletable_size = 0
        total_deletable_count = 0
        user_stats = {}
        
        # 사용자별로 그룹화
        user_groups = {}
        for file_data in result['results']:
            user = file_data.get('source_user', 'Unknown')
            if user not in user_groups:
                user_groups[user] = []
            user_groups[user].append(file_data)
        
        # 사용자별로 트리 구성
        for user in sorted(user_groups.keys()):
            user_item = QTreeWidgetItem(self.result_tree)
            user_item.setText(0, f"👤 {user}")
            user_item.setExpanded(True)
            
            if user not in user_stats:
                user_stats[user] = {'total': 0, 'deletable': 0, 'size': 0}
            
            # 날짜별로 그룹화
            date_groups = {}
            for file_data in user_groups[user]:
                date = file_data['date']
                if date not in date_groups:
                    date_groups[date] = []
                date_groups[date].append(file_data)
            
            # 날짜별로 표시
            for date in sorted(date_groups.keys(), reverse=True):
                date_item = QTreeWidgetItem(user_item)
                date_item.setText(0, f"📅 {date}")
                date_item.setExpanded(True)
                
                # 사이트별로 그룹화
                site_groups = {}
                for file_data in date_groups[date]:
                    for site_info in file_data['sites']:
                        site = site_info['site']
                        if site not in site_groups:
                            site_groups[site] = []
                        site_groups[site].append({
                            'filename': file_data['filename'],
                            'size': file_data['size'],
                            'path': site_info['path'],
                            'deletable': site_info.get('deletable', False)
                        })
                
                # 사이트별로 표시
                for site in sorted(site_groups.keys()):
                    site_item = QTreeWidgetItem(date_item)
                    site_count = len(site_groups[site])
                    site_item.setText(0, f"🌐 {site} ({site_count}개 파일)")
                    site_item.setExpanded(True)
                    
                    # 파일별로 표시
                    for file_info in site_groups[site]:
                        file_item = QTreeWidgetItem(site_item)
                        file_item.setText(0, f"📄 {file_info['filename']}")
                        file_item.setText(1, self.format_file_size(file_info['size']))
                        
                        user_stats[user]['total'] += 1
                        
                        if file_info['deletable']:
                            file_item.setText(2, "삭제 대상")
                            file_item.setBackground(2, QColor(255, 200, 200))
                            total_deletable_count += 1
                            total_deletable_size += file_info['size']
                            user_stats[user]['deletable'] += 1
                            user_stats[user]['size'] += file_info['size']
                        else:
                            file_item.setText(2, "보존")
                            file_item.setBackground(2, QColor(200, 255, 200))
        
        # 요약 정보 표시
        summary_lines = []
        summary_lines.append("=== 📊 그룹 비교 결과 요약 ===\n")
        summary_lines.append(f"👥 분석 그룹: {', '.join(self.selected_users)}")
        summary_lines.append(f"📁 삭제 가능한 파일: {total_deletable_count}개")
        summary_lines.append(f"💾 절약 가능한 용량: {self.format_file_size(total_deletable_size)}\n")
        
        if user_stats:
            summary_lines.append("📈 사용자별 통계:")
            for user, stats in user_stats.items():
                if stats['deletable'] > 0:
                    summary_lines.append(f"  👤 {user}: {stats['deletable']}/{stats['total']}개 삭제 예정 ({self.format_file_size(stats['size'])})")
        
        self.summary_text.setPlainText('\n'.join(summary_lines))
    
    def format_file_size(self, size_mb):
        """파일 크기 포맷팅"""
        if size_mb < 1:
            return f"{size_mb * 1024:.1f} KB"
        elif size_mb < 1024:
            return f"{size_mb:.1f} MB"
        else:
            return f"{size_mb / 1024:.1f} GB"
    
    def get_result(self):
        """비교 결과 반환"""
        return self.comparison_result 