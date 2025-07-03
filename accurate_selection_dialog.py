import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QTextEdit, QSplitter, QSpinBox, 
                             QCheckBox, QProgressBar, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

class AccurateSelectionDialog(QDialog):
    def __init__(self, capacity_finder, current_path, parent=None):
        super().__init__(parent)
        self.capacity_finder = capacity_finder
        self.current_path = current_path
        self.selection_result = None
        self.candidates_data = None
        
        self.setWindowTitle("정확한 선별도우미")
        self.setGeometry(150, 150, 1000, 700)
        self.setModal(True)
        
        self.init_ui()
        self.load_users()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        
        # 상단 설정 섹션
        settings_group = QGroupBox("선별 설정")
        settings_layout = QHBoxLayout(settings_group)
        
        # 사용자 선택
        settings_layout.addWidget(QLabel("사용자:"))
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(150)
        self.user_combo.currentTextChanged.connect(self.on_user_changed)
        settings_layout.addWidget(self.user_combo)
        
        # 후보 파일 수 설정
        settings_layout.addWidget(QLabel("후보 파일 수:"))
        self.candidate_count_spin = QSpinBox()
        self.candidate_count_spin.setRange(10, 200)
        self.candidate_count_spin.setValue(50)
        self.candidate_count_spin.setSuffix("개")
        settings_layout.addWidget(self.candidate_count_spin)
        
        # 분석 버튼
        self.analyze_button = QPushButton("분석 시작")
        self.analyze_button.clicked.connect(self.analyze_files)
        self.analyze_button.setEnabled(False)
        settings_layout.addWidget(self.analyze_button)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # 진행 상황 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 메인 컨텐츠 분할기
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # 파일 리스트 트리
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["순위", "파일명", "크기", "점수", "선택"])
        self.file_tree.setColumnWidth(0, 60)
        self.file_tree.setColumnWidth(1, 400)
        self.file_tree.setColumnWidth(2, 100)
        self.file_tree.setColumnWidth(3, 80)
        self.file_tree.setColumnWidth(4, 60)
        self.file_tree.itemChanged.connect(self.on_item_changed)
        # 더블클릭 이벤트 연결 - 영상 재생 기능
        self.file_tree.itemDoubleClicked.connect(self.on_video_double_clicked)
        splitter.addWidget(self.file_tree)
        
        # 하단 정보 패널
        info_panel = QSplitter(Qt.Horizontal)
        
        # 선별 통계
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setReadOnly(True)
        info_panel.addWidget(self.stats_text)
        
        # 제어 버튼들
        button_group = QGroupBox("빠른 선택")
        button_layout = QVBoxLayout(button_group)
        
        # 상위 N개 선택 - 사용자 입력
        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.addWidget(QLabel("상위"))
        
        self.top_n_spinbox = QSpinBox()
        self.top_n_spinbox.setRange(1, 200)
        self.top_n_spinbox.setValue(10)
        self.top_n_spinbox.setSuffix("개")
        self.top_n_spinbox.setMaximumWidth(80)
        top_buttons_layout.addWidget(self.top_n_spinbox)
        
        self.select_top_button = QPushButton("선택")
        self.select_top_button.clicked.connect(self.select_custom_top_n)
        top_buttons_layout.addWidget(self.select_top_button)
        
        top_buttons_layout.addStretch()
        button_layout.addLayout(top_buttons_layout)
        
        # 전체 선택/해제 버튼들
        control_buttons_layout = QHBoxLayout()
        self.select_all_button = QPushButton("모두 선택")
        self.select_all_button.clicked.connect(self.select_all)
        self.clear_all_button = QPushButton("모두 해제")
        self.clear_all_button.clicked.connect(self.clear_all)
        
        control_buttons_layout.addWidget(self.select_all_button)
        control_buttons_layout.addWidget(self.clear_all_button)
        button_layout.addLayout(control_buttons_layout)
        
        info_panel.addWidget(button_group)
        splitter.addWidget(info_panel)
        
        # 최종 실행 버튼들
        final_button_layout = QHBoxLayout()
        
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
        
        final_button_layout.addStretch()
        final_button_layout.addWidget(self.execute_button)
        final_button_layout.addWidget(cancel_button)
        
        layout.addLayout(final_button_layout)
        
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
        self.file_tree.clear()
        self.stats_text.clear()
        self.execute_button.setEnabled(False)
        self.candidates_data = None
    
    def analyze_files(self):
        """파일 분석 및 후보 생성"""
        username = self.user_combo.currentText()
        if not username or username == "사용 가능한 사용자 없음":
            return
        
        candidate_count = self.candidate_count_spin.value()
        
        # 진행 상황 표시
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 무한 진행바
        
        try:
            # 후보 데이터 생성
            self.candidates_data = self.capacity_finder.get_selection_candidates(username, candidate_count)
            
            if not self.candidates_data:
                QMessageBox.warning(self, "분석 실패", f"사용자 '{username}'의 데이터를 분석할 수 없습니다.")
                return
            
            self.display_candidates()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"분석 중 오류가 발생했습니다: {e}")
        finally:
            self.progress_bar.setVisible(False)
    
    def display_candidates(self):
        """후보 파일들 표시"""
        if not self.candidates_data:
            return
        
        self.file_tree.clear()
        candidates = self.candidates_data['candidates']
        
        for file_info in candidates:
            item = QTreeWidgetItem(self.file_tree)
            item.setText(0, str(file_info['rank']))
            item.setText(1, file_info['name'])
            item.setText(2, self.format_file_size(file_info['size']))
            item.setText(3, f"{file_info['score']:.3f}")
            
            # 체크박스 추가
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            self.file_tree.setItemWidget(item, 4, checkbox)
            
            # 점수에 따른 색상 구분
            if file_info['score'] >= 0.8:
                item.setBackground(0, QColor(200, 255, 200))  # 연한 초록
            elif file_info['score'] >= 0.6:
                item.setBackground(0, QColor(255, 255, 200))  # 연한 노랑
            elif file_info['score'] >= 0.4:
                item.setBackground(0, QColor(255, 230, 200))  # 연한 주황
            else:
                item.setBackground(0, QColor(255, 200, 200))  # 연한 빨강
        
        self.update_stats()
        self.execute_button.setEnabled(True)
    
    def on_item_changed(self, item, column):
        """아이템 변경시 통계 업데이트"""
        self.update_stats()
    
    def update_stats(self):
        """선별 통계 업데이트"""
        if not self.candidates_data:
            return
        
        total_files = self.candidates_data['total_files']
        candidate_count = len(self.candidates_data['candidates'])
        excluded_count = len(self.candidates_data['excluded'])
        
        # 선택된 파일 카운트
        selected_count = 0
        selected_size = 0.0
        unselected_size = 0.0
        
        root = self.file_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            checkbox = self.file_tree.itemWidget(item, 4)
            
            file_info = self.candidates_data['candidates'][i]
            if checkbox and checkbox.isChecked():
                selected_count += 1
                selected_size += file_info['size']
            else:
                unselected_size += file_info['size']
        
        # 자동 제외된 파일들의 크기
        excluded_size = sum(f['size'] for f in self.candidates_data['excluded'])
        total_delete_size = unselected_size + excluded_size
        
        # 통계 텍스트 생성
        stats = f"📊 선별 통계 - 사용자: {self.candidates_data['username']}\n\n"
        stats += f"📁 전체 파일: {total_files}개\n"
        stats += f"🎯 후보 파일: {candidate_count}개\n"
        stats += f"❌ 자동 제외: {excluded_count}개\n\n"
        
        stats += f"✅ 선택된 파일: {selected_count}개\n"
        stats += f"💾 유지할 용량: {self.format_file_size(selected_size)}\n\n"
        
        stats += f"🗑️ 삭제 예정: {total_files - selected_count}개\n"
        stats += f"💽 절약될 용량: {self.format_file_size(total_delete_size)}\n\n"
        
        if selected_count > 0:
            efficiency = (total_delete_size / (selected_size + total_delete_size)) * 100
            stats += f"📈 공간 효율성: {efficiency:.1f}% 절약"
        
        self.stats_text.setPlainText(stats)
    
    def select_top_n(self, n):
        """상위 N개 파일 선택"""
        root = self.file_tree.invisibleRootItem()
        count = min(n, root.childCount())
        
        for i in range(root.childCount()):
            item = root.child(i)
            checkbox = self.file_tree.itemWidget(item, 4)
            if checkbox:
                checkbox.setChecked(i < count)
        
        self.update_stats()
    
    def select_custom_top_n(self):
        """사용자가 입력한 수만큼 상위 파일 선택"""
        n = self.top_n_spinbox.value()
        self.select_top_n(n)
    
    def select_all(self):
        """모든 후보 파일 선택"""
        root = self.file_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            checkbox = self.file_tree.itemWidget(item, 4)
            if checkbox:
                checkbox.setChecked(True)
        
        self.update_stats()
    
    def clear_all(self):
        """모든 선택 해제"""
        root = self.file_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            checkbox = self.file_tree.itemWidget(item, 4)
            if checkbox:
                checkbox.setChecked(False)
        
        self.update_stats()
    
    def format_file_size(self, size_mb):
        """파일 사이즈 포맷팅"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
    
    def get_result(self):
        """선별 결과 반환"""
        if not self.candidates_data:
            return None
        
        # 선택된 파일과 삭제할 파일 구분
        files_to_keep = []
        files_to_delete = []
        
        # 후보 중에서 선택된 것들
        root = self.file_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            checkbox = self.file_tree.itemWidget(item, 4)
            file_info = self.candidates_data['candidates'][i]
            
            if checkbox and checkbox.isChecked():
                files_to_keep.append(file_info)
            else:
                files_to_delete.append(file_info)
        
        # 자동 제외된 파일들은 모두 삭제 대상
        files_to_delete.extend(self.candidates_data['excluded'])
        
        total_savings = sum(f['size'] for f in files_to_delete)
        
        self.selection_result = {
            'files_to_keep': files_to_keep,
            'files_to_delete': files_to_delete,
            'total_savings': total_savings,
            'username': self.candidates_data['username']
        }
        
        return self.selection_result 

    def on_video_double_clicked(self, item, column):
        """영상 리스트에서 더블클릭시 해당 영상을 재생하는 함수"""
        if not item:
            return
        
        # 파일명 얻기 (두 번째 컬럼에 저장됨)
        file_name = item.text(1)
        if not file_name:
            QMessageBox.warning(self, "오류", "파일명을 가져올 수 없습니다.")
            return
        
        # 전체 파일 경로 조합
        file_path = os.path.join(self.current_path, file_name)
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "파일 없음", f"해당 영상 파일이 존재하지 않습니다:\n{file_path}")
            return
        
        try:
            # 윈도우 기본 플레이어로 영상 재생
            os.startfile(file_path)
        except Exception as e:
            QMessageBox.warning(self, "재생 오류", f"영상을 재생할 수 없습니다:\n{str(e)}") 