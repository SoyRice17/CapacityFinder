import os
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QComboBox, QListWidget, 
                             QListWidgetItem, QMessageBox, QFileDialog,
                             QGroupBox, QSplitter, QTextEdit, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from datetime import datetime

class PathSelectionDialog(QDialog):
    """경로 선택을 위한 전용 팝업 다이얼로그"""
    
    # 시그널 정의 - 경로가 선택되었을 때 emit
    path_selected = pyqtSignal(str)
    
    def __init__(self, path_history=None, parent=None):
        super().__init__(parent)
        self.path_history = path_history
        self.selected_path = None
        
        self.setWindowTitle("경로 선택 및 관리")
        self.setFixedSize(700, 500)
        self.setModal(True)  # 모달 다이얼로그로 설정
        
        self.init_ui()
        self.load_history_data()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 제목 라벨
        title_label = QLabel("📁 경로 선택 및 관리")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { padding: 10px; background-color: #3498db; color: white; border-radius: 5px; }")
        layout.addWidget(title_label)
        
        # 메인 스플리터 (이전 경로 | 새 경로 입력)
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # === 왼쪽: 이전 경로 그룹 ===
        history_group = QGroupBox("📋 이전 사용 경로")
        history_layout = QVBoxLayout(history_group)
        
        # 정렬 옵션
        sort_layout = QHBoxLayout()
        self.sort_usage_check = QCheckBox("사용빈도순")
        self.sort_usage_check.setChecked(True)
        self.sort_usage_check.stateChanged.connect(self.refresh_history_list)
        self.sort_recent_check = QCheckBox("최근순")
        self.sort_recent_check.stateChanged.connect(self.on_sort_changed)
        
        sort_layout.addWidget(self.sort_usage_check)
        sort_layout.addWidget(self.sort_recent_check)
        sort_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 새로고침")
        refresh_btn.clicked.connect(self.refresh_history_list)
        refresh_btn.setMaximumWidth(100)
        sort_layout.addWidget(refresh_btn)
        
        history_layout.addLayout(sort_layout)
        
        # 이전 경로 리스트
        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(250)
        self.history_list.itemDoubleClicked.connect(self.on_history_double_clicked)
        self.history_list.itemClicked.connect(self.on_history_clicked)
        history_layout.addWidget(self.history_list)
        
        # 선택된 경로 정보 표시
        self.selected_info_label = QLabel("선택된 경로: 없음")
        self.selected_info_label.setStyleSheet("QLabel { padding: 5px; background-color: #ecf0f1; border-radius: 3px; }")
        history_layout.addWidget(self.selected_info_label)
        
        # 삭제 버튼
        delete_btn = QPushButton("🗑️ 선택된 경로 삭제")
        delete_btn.clicked.connect(self.delete_selected_history)
        delete_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; }")
        history_layout.addWidget(delete_btn)
        
        main_splitter.addWidget(history_group)
        
        # === 오른쪽: 새 경로 입력 그룹 ===
        new_path_group = QGroupBox("📂 새 경로 입력")
        new_path_layout = QVBoxLayout(new_path_group)
        
        # 경로 입력
        input_label = QLabel("경로 입력:")
        new_path_layout.addWidget(input_label)
        
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("경로를 입력하거나 아래 버튼으로 폴더를 선택하세요...")
        self.path_input.textChanged.connect(self.on_path_input_changed)
        self.path_input.returnPressed.connect(self.validate_and_accept)
        path_input_layout.addWidget(self.path_input)
        
        browse_btn = QPushButton("📁 찾아보기")
        browse_btn.clicked.connect(self.browse_folder)
        browse_btn.setMaximumWidth(100)
        path_input_layout.addWidget(browse_btn)
        
        new_path_layout.addLayout(path_input_layout)
        
        # 경로 유효성 표시
        self.validity_label = QLabel("경로를 입력해주세요")
        self.validity_label.setStyleSheet("QLabel { padding: 5px; background-color: #f39c12; color: white; border-radius: 3px; }")
        new_path_layout.addWidget(self.validity_label)
        
        # 경로 정보 표시 (파일 개수 등)
        self.path_info_text = QTextEdit()
        self.path_info_text.setMaximumHeight(150)
        self.path_info_text.setPlaceholderText("유효한 경로를 입력하면 폴더 정보가 표시됩니다...")
        self.path_info_text.setReadOnly(True)
        new_path_layout.addWidget(self.path_info_text)
        
        new_path_layout.addStretch()
        
        main_splitter.addWidget(new_path_group)
        
        # 스플리터 비율 설정 (이전 경로 : 새 경로 = 1:1)
        main_splitter.setSizes([350, 350])
        
        # === 하단 버튼 ===
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("✅ 확인")
        self.ok_button.clicked.connect(self.validate_and_accept)
        self.ok_button.setEnabled(False)
        self.ok_button.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 8px; }")
        
        cancel_button = QPushButton("❌ 취소")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("QPushButton { background-color: #95a5a6; color: white; padding: 8px; }")
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_history_data(self):
        """이전 경로 데이터 로드"""
        self.refresh_history_list()
    
    def refresh_history_list(self):
        """이전 경로 리스트 새로고침"""
        self.history_list.clear()
        
        if not self.path_history:
            item = QListWidgetItem("이전 경로 기록이 없습니다")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.history_list.addItem(item)
            return
        
        paths = self.path_history.get_paths()
        if not paths:
            item = QListWidgetItem("이전 경로 기록이 없습니다")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.history_list.addItem(item)
            return
        
        # 정렬 방식에 따라 정렬
        if self.sort_usage_check.isChecked():
            paths.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
        elif self.sort_recent_check.isChecked():
            paths.sort(key=lambda x: x.get("last_used", ""), reverse=True)
        
        for path_info in paths:
            display_name = path_info.get('display_name', '')
            usage_count = path_info.get('usage_count', 0)
            last_used = path_info.get('last_used', '')
            
            # 날짜 포맷팅
            try:
                if last_used:
                    last_used_dt = datetime.fromisoformat(last_used)
                    formatted_date = last_used_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    formatted_date = "알 수 없음"
            except:
                formatted_date = "알 수 없음"
            
            item_text = f"📁 {display_name}\n   💼 사용: {usage_count}회 | 🕒 최근: {formatted_date}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, path_info['path'])
            
            # 사용 빈도에 따른 색상 구분
            if usage_count >= 5:
                item.setBackground(Qt.green)
            elif usage_count >= 3:
                item.setBackground(Qt.yellow)
                
            self.history_list.addItem(item)
    
    def on_sort_changed(self):
        """정렬 방식 변경 처리"""
        if self.sender() == self.sort_recent_check and self.sort_recent_check.isChecked():
            self.sort_usage_check.setChecked(False)
        elif self.sender() == self.sort_usage_check and self.sort_usage_check.isChecked():
            self.sort_recent_check.setChecked(False)
        
        self.refresh_history_list()
    
    def on_history_clicked(self, item):
        """이전 경로 클릭 처리"""
        if item.flags() & Qt.ItemIsEnabled:
            path = item.data(Qt.UserRole)
            if path:
                self.path_input.setText(path)
                self.selected_info_label.setText(f"선택된 경로: {path}")
    
    def on_history_double_clicked(self, item):
        """이전 경로 더블클릭으로 즉시 선택"""
        if item.flags() & Qt.ItemIsEnabled:
            path = item.data(Qt.UserRole)
            if path and os.path.exists(path):
                self.selected_path = path
                self.accept()
    
    def delete_selected_history(self):
        """선택된 이전 경로 삭제"""
        current_item = self.history_list.currentItem()
        if not current_item or not (current_item.flags() & Qt.ItemIsEnabled):
            QMessageBox.warning(self, "경고", "삭제할 경로를 선택해주세요.")
            return
        
        path = current_item.data(Qt.UserRole)
        if not path:
            return
        
        # 확인 다이얼로그
        reply = QMessageBox.question(self, "경로 삭제 확인", 
                                   f"다음 경로를 기록에서 삭제하시겠습니까?\n\n{path}",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.path_history.remove_path(path)
            self.refresh_history_list()
            self.selected_info_label.setText("선택된 경로: 없음")
            QMessageBox.information(self, "완료", "경로가 삭제되었습니다.")
    
    def browse_folder(self):
        """폴더 브라우저 열기"""
        folder_path = QFileDialog.getExistingDirectory(self, "폴더 선택", 
                                                     self.path_input.text() or os.getcwd())
        if folder_path:
            self.path_input.setText(folder_path)
    
    def on_path_input_changed(self, text):
        """경로 입력 변경 처리"""
        self.validate_path(text)
    
    def validate_path(self, path):
        """경로 유효성 검사 및 정보 표시"""
        if not path.strip():
            self.validity_label.setText("경로를 입력해주세요")
            self.validity_label.setStyleSheet("QLabel { padding: 5px; background-color: #f39c12; color: white; border-radius: 3px; }")
            self.path_info_text.clear()
            self.ok_button.setEnabled(False)
            return False
        
        if not os.path.exists(path):
            self.validity_label.setText("❌ 존재하지 않는 경로입니다")
            self.validity_label.setStyleSheet("QLabel { padding: 5px; background-color: #e74c3c; color: white; border-radius: 3px; }")
            self.path_info_text.clear()
            self.ok_button.setEnabled(False)
            return False
        
        if not os.path.isdir(path):
            self.validity_label.setText("❌ 폴더가 아닙니다")
            self.validity_label.setStyleSheet("QLabel { padding: 5px; background-color: #e74c3c; color: white; border-radius: 3px; }")
            self.path_info_text.clear()
            self.ok_button.setEnabled(False)
            return False
        
        # 유효한 경로인 경우
        self.validity_label.setText("✅ 유효한 경로입니다")
        self.validity_label.setStyleSheet("QLabel { padding: 5px; background-color: #27ae60; color: white; border-radius: 3px; }")
        self.ok_button.setEnabled(True)
        
        # 폴더 정보 표시
        try:
            files = os.listdir(path)
            file_count = len([f for f in files if os.path.isfile(os.path.join(path, f))])
            dir_count = len([f for f in files if os.path.isdir(os.path.join(path, f))])
            
            info_text = f"📊 폴더 정보:\n"
            info_text += f"📁 경로: {path}\n"
            info_text += f"📄 파일 수: {file_count}개\n"
            info_text += f"📂 하위 폴더 수: {dir_count}개\n\n"
            
            if file_count > 0:
                info_text += "📋 최근 파일 (최대 5개):\n"
                recent_files = sorted([f for f in files if os.path.isfile(os.path.join(path, f))])[:5]
                for i, filename in enumerate(recent_files, 1):
                    info_text += f"  {i}. {filename}\n"
            
            self.path_info_text.setText(info_text)
            
        except Exception as e:
            self.path_info_text.setText(f"폴더 정보를 가져올 수 없습니다: {str(e)}")
        
        return True
    
    def validate_and_accept(self):
        """경로 검증 후 다이얼로그 종료"""
        path = self.path_input.text().strip()
        if self.validate_path(path):
            self.selected_path = path
            self.accept()
        else:
            QMessageBox.warning(self, "경고", "유효한 경로를 입력해주세요.")
    
    def get_selected_path(self):
        """선택된 경로 반환"""
        return self.selected_path 