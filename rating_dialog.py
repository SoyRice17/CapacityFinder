from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QMessageBox, QFrame,
                             QButtonGroup, QRadioButton)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
import json
import os

class RatingDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username
        self.current_rating = 0
        self.current_comment = ""
        self.rating_file = "user_ratings.json"
        self.rating_history = []
        
        self.setWindowTitle(f"🌟 {username} 사용자 레이팅")
        self.setModal(True)
        self.setFixedSize(600, 550)  # 세로 크기 늘림
        
        # 기존 레이팅 로드
        self.load_existing_rating()
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목 라벨
        title_label = QLabel(f"📊 {self.username} 사용자 평가")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                padding: 10px;
                background-color: #ecf0f1;
                border-radius: 8px;
                border: 2px solid #bdc3c7;
            }
        """)
        layout.addWidget(title_label)
        
        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 이전 평가 기록 섹션
        if self.current_rating > 0 or self.rating_history:
            history_frame = QFrame()
            history_frame.setFrameStyle(QFrame.Box)
            history_frame.setStyleSheet("QFrame { border: 2px solid #3498db; border-radius: 8px; padding: 10px; background-color: #ebf3fd; }")
            history_layout = QVBoxLayout(history_frame)
            
            history_label = QLabel("📜 이전 평가 기록")
            history_label.setFont(QFont("", 12, QFont.Bold))
            history_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
            history_layout.addWidget(history_label)
            
            # 현재 평가 표시
            if self.current_rating > 0:
                current_stars = "⭐" * self.current_rating
                current_text = f"현재: {current_stars} ({self.current_rating}/5)"
                if self.current_comment:
                    current_text += f" - \"{self.current_comment}\""
                
                current_label = QLabel(current_text)
                current_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 5px;")
                current_label.setWordWrap(True)
                history_layout.addWidget(current_label)
            
            # 히스토리 표시
            if self.rating_history:
                for i, record in enumerate(self.rating_history[-3:]):  # 최근 3개만 표시
                    stars = "⭐" * record.get('rating', 0)
                    history_text = f"• {record.get('date', '')} - {stars} ({record.get('rating', 0)}/5)"
                    if record.get('comment'):
                        history_text += f" - \"{record.get('comment')}\""
                    
                    history_item = QLabel(history_text)
                    history_item.setStyleSheet("color: #7f8c8d; font-size: 11px; padding: 2px;")
                    history_item.setWordWrap(True)
                    history_layout.addWidget(history_item)
                    
                if len(self.rating_history) > 3:
                    more_label = QLabel(f"... 외 {len(self.rating_history) - 3}개 더")
                    more_label.setStyleSheet("color: #95a5a6; font-size: 10px; font-style: italic; padding: 2px;")
                    history_layout.addWidget(more_label)
            
            layout.addWidget(history_frame)
        
        # 레이팅 섹션
        rating_layout = QVBoxLayout()
        
        # 레이팅 라벨
        rating_label = QLabel("⭐ 평점 (1-5점):")
        rating_label.setFont(QFont("", 12, QFont.Bold))
        rating_layout.addWidget(rating_label)
        
        # 별점 버튼 레이아웃
        stars_layout = QHBoxLayout()
        
        self.rating_buttons = QButtonGroup()
        self.rating_buttons.setExclusive(True)
        
        for i in range(1, 6):
            star_button = QRadioButton(f"{i}⭐")
            star_button.setStyleSheet("""
                QRadioButton {
                    font-size: 16px;
                    font-weight: bold;
                    padding: 8px;
                    margin: 5px;
                }
                QRadioButton:checked {
                    color: #f39c12;
                }
            """)
            self.rating_buttons.addButton(star_button, i)
            stars_layout.addWidget(star_button)
            
            # 기존 평가가 있으면 선택
            if self.current_rating == i:
                star_button.setChecked(True)
        
        stars_layout.addStretch()
        rating_layout.addLayout(stars_layout)
        
        # 선택된 레이팅 표시
        self.rating_display = QLabel()
        self.rating_display.setAlignment(Qt.AlignCenter)
        self.rating_display.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #e74c3c;
                padding: 10px;
                background-color: #fdf2e9;
                border: 2px solid #f39c12;
                border-radius: 8px;
            }
        """)
        self.update_rating_display()
        self.rating_buttons.buttonClicked.connect(self.update_rating_display)
        rating_layout.addWidget(self.rating_display)
        
        layout.addLayout(rating_layout)
        
        # 코멘트 섹션
        comment_layout = QVBoxLayout()
        
        comment_label = QLabel("💬 코멘트:")
        comment_label.setFont(QFont("", 12, QFont.Bold))
        comment_layout.addWidget(comment_label)
        
        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText("이 사용자에 대한 평가나 메모를 작성해주세요...")
        self.comment_edit.setMinimumHeight(100)
        self.comment_edit.setMaximumHeight(150)
        self.comment_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 8px;
                background-color: #ffffff;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        if self.current_comment:
            self.comment_edit.setPlainText(self.current_comment)
        
        comment_layout.addWidget(self.comment_edit)
        layout.addLayout(comment_layout)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 저장 버튼
        save_button = QPushButton("💾 저장")
        save_button.clicked.connect(self.save_rating)
        save_button.setMinimumHeight(40)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        
        # 삭제 버튼 (기존 레이팅이 있을 때만)
        self.delete_button = QPushButton("🗑️ 삭제")
        self.delete_button.clicked.connect(self.delete_rating)
        self.delete_button.setMinimumHeight(40)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        
        # 취소 버튼
        cancel_button = QPushButton("❌ 취소")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setMinimumHeight(40)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #6c7b7d;
            }
        """)
        
        button_layout.addWidget(save_button)
        if self.current_rating > 0:  # 기존 레이팅이 있을 때만 삭제 버튼 표시
            button_layout.addWidget(self.delete_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def load_existing_rating(self):
        """기존 레이팅 로드"""
        if os.path.exists(self.rating_file):
            try:
                with open(self.rating_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    ratings = data.get('ratings', {})
                    if self.username in ratings:
                        user_rating = ratings[self.username]
                        self.current_rating = user_rating.get('rating', 0)
                        self.current_comment = user_rating.get('comment', '')
                        self.rating_history = user_rating.get('history', [])
            except Exception as e:
                print(f"레이팅 로드 오류: {e}")
                
    def update_rating_display(self):
        """레이팅 표시 업데이트"""
        selected_id = self.rating_buttons.checkedId()
        if selected_id > 0:
            stars = "⭐" * selected_id
            self.rating_display.setText(f"{stars} ({selected_id}/5)")
        else:
            self.rating_display.setText("평점을 선택해주세요")
        
    def save_rating(self):
        """레이팅 저장"""
        selected_rating = self.rating_buttons.checkedId()
        if selected_rating <= 0:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("평점 선택 필요")
            msg.setText("평점을 선택해주세요!")
            msg.exec_()
            return
            
        comment = self.comment_edit.toPlainText().strip()
        
        # 레이팅 데이터 로드
        data = {'ratings': {}}
        if os.path.exists(self.rating_file):
            try:
                with open(self.rating_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'ratings' not in data:
                        data['ratings'] = {}
            except Exception as e:
                print(f"레이팅 파일 로드 오류: {e}")
                data = {'ratings': {}}
        
        # 기존 데이터가 있으면 히스토리에 추가
        current_date = self.get_current_timestamp()
        if self.username in data['ratings'] and self.current_rating > 0:
            existing_data = data['ratings'][self.username]
            if 'history' not in existing_data:
                existing_data['history'] = []
            
            # 기존 평가를 히스토리에 추가
            history_entry = {
                'date': existing_data.get('last_rating', ''),
                'rating': existing_data.get('rating', 0),
                'comment': existing_data.get('comment', '')
            }
            existing_data['history'].append(history_entry)
        
        # 새 레이팅 저장
        data['ratings'][self.username] = {
            'rating': selected_rating,
            'comment': comment,
            'last_rating': current_date,
            'rating_count': data['ratings'].get(self.username, {}).get('rating_count', 0) + 1,
            'history': data['ratings'].get(self.username, {}).get('history', [])
        }
        
        data['last_updated'] = current_date
        data['version'] = '1.0'
        
        try:
            with open(self.rating_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # 성공 메시지
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("저장 완료")
            msg.setText(f"'{self.username}' 사용자의 레이팅이 저장되었습니다!\n평점: {selected_rating}/5")
            msg.exec_()
            
            self.accept()
            
        except Exception as e:
            # 오류 메시지
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("저장 오류")
            msg.setText(f"레이팅 저장 중 오류가 발생했습니다:\n{str(e)}")
            msg.exec_()
            
    def delete_rating(self):
        """레이팅 삭제"""
        # 확인 다이얼로그
        reply = QMessageBox.question(self, "레이팅 삭제", 
                                   f"'{self.username}' 사용자의 레이팅을 삭제하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            data = {'ratings': {}}
            if os.path.exists(self.rating_file):
                try:
                    with open(self.rating_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'ratings' not in data:
                            data['ratings'] = {}
                except Exception as e:
                    print(f"레이팅 파일 로드 오류: {e}")
                    data = {'ratings': {}}
                    
            # 해당 사용자 레이팅 삭제
            if self.username in data['ratings']:
                del data['ratings'][self.username]
                data['last_updated'] = self.get_current_timestamp()
                
                try:
                    with open(self.rating_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                        
                    # 성공 메시지
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Information)
                    msg.setWindowTitle("삭제 완료")
                    msg.setText(f"'{self.username}' 사용자의 레이팅이 삭제되었습니다.")
                    msg.exec_()
                    
                    self.accept()
                    
                except Exception as e:
                    # 오류 메시지
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)
                    msg.setWindowTitle("삭제 오류")
                    msg.setText(f"레이팅 삭제 중 오류가 발생했습니다:\n{str(e)}")
                    msg.exec_()
                    
    def get_current_timestamp(self):
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d") 