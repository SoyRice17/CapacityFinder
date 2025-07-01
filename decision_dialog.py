#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import json
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QProgressBar, QFrame, QScrollArea,
                             QWidget, QMessageBox, QComboBox, QGroupBox, QRadioButton,
                             QButtonGroup, QLineEdit, QSplitter, QDialogButtonBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class ModelDecisionDialog(QDialog):
    """모델별 결정을 위한 팝업 다이얼로그"""
    
    def __init__(self, decision_data, current_path, sort_method="size", parent=None):
        super().__init__(parent)
        self.decision_data = decision_data  # 결정할 모델 리스트
        self.current_path = current_path    # 파일 경로
        self.current_index = 0
        self.decisions = {}  # {username: 'keep'/'delete'/'skip'}
        self.total_savings = 0
        self.user_ratings = {}  # 평가 데이터
        self.ratings_file = "user_ratings.json"
        self.sort_method = sort_method
        
        self.load_user_ratings()
        self.sort_decision_data()  # 정렬 적용
        self.setup_ui()
        self.show_current_model()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("📋 모델 정리 도우미")
        self.setGeometry(200, 200, 1200, 850)  # 높이 더 확장
        self.setModal(True)
        
        # 메인 수평 분할기
        main_layout = QHBoxLayout(self)
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # 왼쪽 메인 컨텐츠 영역
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
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
        
        # 평가 섹션 (대표 파일들 위로 이동)
        rating_group = self.create_rating_section()
        layout.addWidget(rating_group)
        
        # 샘플 파일 영역 (스크롤 가능)
        sample_header = QLabel("📁 대표 파일들 (더블클릭하면 파일이 열립니다):")
        sample_header.setStyleSheet("font-weight: bold; color: #34495e; font-size: 13px;")
        layout.addWidget(sample_header)
        
        self.sample_area = QScrollArea()
        self.sample_widget = QWidget()
        self.sample_layout = QVBoxLayout(self.sample_widget)
        self.sample_area.setWidget(self.sample_widget)
        self.sample_area.setWidgetResizable(True)
        self.sample_area.setMaximumHeight(250)  # 높이 증가
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
        
        # 왼쪽 위젯을 스플리터에 추가
        main_splitter.addWidget(left_widget)
        
        # 오른쪽 통계 패널 생성
        stats_panel = self.create_stats_panel()
        main_splitter.addWidget(stats_panel)
        
        # 스플리터 비율 설정 (왼쪽:오른쪽 = 8:4)
        main_splitter.setSizes([800, 400])
    
    def create_rating_section(self):
        """평가 섹션 생성"""
        rating_group = QGroupBox("⭐ 사용자 평가")
        rating_group.setMinimumHeight(120)  # 최소 높이 보장
        rating_layout = QVBoxLayout(rating_group)
        rating_layout.setContentsMargins(10, 15, 10, 10)  # 상단 여백 늘림
        
        # 이전 평가 기록 표시
        self.rating_history_label = QLabel("새로운 사용자입니다")
        self.rating_history_label.setStyleSheet("""
            font-size: 11px; 
            color: #7f8c8d; 
            padding: 8px; 
            background-color: #f8f9fa; 
            border-radius: 3px;
        """)
        self.rating_history_label.setWordWrap(True)  # 텍스트 줄바꿈 허용
        rating_layout.addWidget(self.rating_history_label)
        
        # 평가 입력 영역
        rating_input_layout = QVBoxLayout()  # 세로 배치로 변경해서 공간 확보
        rating_input_layout.setSpacing(8)
        
        # 별점 선택 행
        stars_layout = QHBoxLayout()
        stars_layout.addWidget(QLabel("별점:"))
        self.rating_buttons = QButtonGroup()
        
        for i in range(1, 6):
            btn = QRadioButton(f"{i}⭐")
            btn.setStyleSheet("font-size: 12px; padding: 4px;")
            self.rating_buttons.addButton(btn, i)
            stars_layout.addWidget(btn)
            
        stars_layout.addStretch()
        rating_input_layout.addLayout(stars_layout)
        
        # 코멘트 입력 행
        comment_layout = QHBoxLayout()
        comment_layout.addWidget(QLabel("코멘트:"))
        self.rating_comment = QLineEdit()
        self.rating_comment.setPlaceholderText("간단한 평가를 남겨주세요")
        self.rating_comment.setMaxLength(50)
        self.rating_comment.setMinimumHeight(25)  # 높이 보장
        comment_layout.addWidget(self.rating_comment)
        rating_input_layout.addLayout(comment_layout)
        
        rating_layout.addLayout(rating_input_layout)
        
        return rating_group
    
    def create_stats_panel(self):
        """오른쪽 통계 패널 생성"""
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        
        # 패널 제목
        stats_title = QLabel("📊 정리 통계")
        stats_title.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #2c3e50; 
            padding: 10px; 
            background-color: #ecf0f1; 
            border-radius: 5px;
            text-align: center;
        """)
        stats_layout.addWidget(stats_title)
        
        # 현재 절약 용량 표시
        self.savings_label = QLabel("💾 현재까지 절약 예상\n0 MB")
        self.savings_label.setStyleSheet("""
            font-weight: bold; 
            color: white; 
            font-size: 14px; 
            padding: 15px; 
            background-color: #27ae60; 
            border-radius: 8px;
            text-align: center;
        """)
        self.savings_label.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.savings_label)
        
        # 진행 상황 요약
        self.progress_summary = QLabel("진행 상황\n0 / 0 완료")
        self.progress_summary.setStyleSheet("""
            font-size: 12px; 
            color: #7f8c8d; 
            padding: 10px; 
            background-color: #f8f9fa; 
            border-radius: 5px;
            text-align: center;
        """)
        self.progress_summary.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.progress_summary)
        
        # 결정 통계
        self.decision_stats = QTextEdit()
        self.decision_stats.setReadOnly(True)
        self.decision_stats.setMaximumHeight(150)
        self.decision_stats.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-size: 11px;
            }
        """)
        self.decision_stats.setPlainText("📋 결정 현황\n\n아직 결정이 없습니다.")
        stats_layout.addWidget(self.decision_stats)
        
        # 평가 통계
        self.rating_stats = QTextEdit()
        self.rating_stats.setReadOnly(True)
        self.rating_stats.setMaximumHeight(120)
        self.rating_stats.setStyleSheet("""
            QTextEdit {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 5px;
                padding: 10px;
                font-size: 11px;
            }
        """)
        self.rating_stats.setPlainText("⭐ 평가 현황\n\n아직 평가가 없습니다.")
        stats_layout.addWidget(self.rating_stats)
        
        stats_layout.addStretch()
        
        return stats_widget
    
    def update_stats_panel(self):
        """통계 패널 업데이트"""
        # 진행 상황 업데이트
        total_models = len(self.decision_data)
        decided_models = len(self.decisions)
        self.progress_summary.setText(f"진행 상황\n{decided_models} / {total_models} 완료")
        
        # 결정 통계 업데이트
        delete_count = len([d for d in self.decisions.values() if d == 'delete'])
        keep_count = len([d for d in self.decisions.values() if d == 'keep'])
        skip_count = len([d for d in self.decisions.values() if d == 'skip'])
        
        decision_text = "📋 결정 현황\n\n"
        decision_text += f"🗑️ 삭제: {delete_count}개\n"
        decision_text += f"✅ 유지: {keep_count}개\n"
        decision_text += f"⏭️ 나중에: {skip_count}개\n"
        if decided_models > 0:
            decision_text += f"\n📈 진행률: {(decided_models/total_models)*100:.1f}%"
        
        self.decision_stats.setPlainText(decision_text)
        
        # 평가 통계 업데이트
        rated_users = []
        for username in [d['username'] for d in self.decision_data[:self.current_index+1]]:
            if username in self.user_ratings:
                rating = self.user_ratings[username].get('rating', 0)
                rated_users.append(rating)
        
        if rated_users:
            avg_rating = sum(rated_users) / len(rated_users)
            rating_text = "⭐ 평가 현황\n\n"
            rating_text += f"📊 평가된 유저: {len(rated_users)}명\n"
            rating_text += f"⭐ 평균 별점: {avg_rating:.1f}⭐\n"
            
            rating_counts = {i: rated_users.count(i) for i in range(1, 6)}
            for stars, count in rating_counts.items():
                if count > 0:
                    rating_text += f"{stars}⭐: {count}명\n"
        else:
            rating_text = "⭐ 평가 현황\n\n아직 평가가 없습니다."
        
        self.rating_stats.setPlainText(rating_text)
    
    def load_user_ratings(self):
        """사용자 평가 데이터 로드"""
        try:
            if os.path.exists(self.ratings_file):
                with open(self.ratings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_ratings = data.get('ratings', {})
            else:
                self.user_ratings = {}
        except Exception as e:
            print(f"평가 데이터 로드 실패: {e}")
            self.user_ratings = {}
    
    def save_user_ratings(self):
        """사용자 평가 데이터 저장"""
        try:
            data = {
                'ratings': self.user_ratings,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': '1.0'
            }
            with open(self.ratings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"평가 데이터 저장 실패: {e}")
    
    def get_user_rating_info(self, username):
        """특정 사용자의 평가 정보 가져오기"""
        if username not in self.user_ratings:
            return {
                'is_new': True,
                'message': "🆕 이번에 새로 만난 사용자입니다",
                'last_rating': None,
                'rating_count': 0
            }
        
        user_data = self.user_ratings[username]
        rating_count = user_data.get('rating_count', 0)
        last_rating = user_data.get('rating', 0)
        last_comment = user_data.get('comment', '')
        last_date = user_data.get('last_rating', '')
        
        # 메시지 생성
        if last_rating >= 4:
            message = f"😊 지난번에 좋은 평가를 남겼습니다 ({last_rating}⭐)"
        elif last_rating >= 3:
            message = f"😐 지난번에 보통 평가를 남겼습니다 ({last_rating}⭐)"
        else:
            message = f"😞 지난번에 낮은 평가를 남겼습니다 ({last_rating}⭐)"
        
        if last_comment:
            message += f' - "{last_comment}"'
        
        if last_date:
            message += f"\n📅 마지막 평가: {last_date}"
        
        if rating_count > 1:
            message += f" (총 {rating_count}번 평가)"
        
        return {
            'is_new': False,
            'message': message,
            'last_rating': last_rating,
            'rating_count': rating_count
        }
    
    def save_user_rating(self, username, rating, comment):
        """사용자 평가 저장"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if username not in self.user_ratings:
            self.user_ratings[username] = {
                'rating': rating,
                'comment': comment,
                'last_rating': current_date,
                'rating_count': 1,
                'history': []
            }
        else:
            # 기존 평가를 히스토리에 추가
            user_data = self.user_ratings[username]
            if 'rating' in user_data:
                history_entry = {
                    'date': user_data.get('last_rating', ''),
                    'rating': user_data.get('rating', 0),
                    'comment': user_data.get('comment', '')
                }
                if 'history' not in user_data:
                    user_data['history'] = []
                user_data['history'].append(history_entry)
            
            # 새로운 평가 저장
            user_data['rating'] = rating
            user_data['comment'] = comment
            user_data['last_rating'] = current_date
            user_data['rating_count'] = user_data.get('rating_count', 0) + 1
        
        self.save_user_ratings()
    
    def sort_decision_data(self):
        """결정 데이터 정렬"""
        if self.sort_method == "size":
            # 기본 크기순 정렬 (이미 정렬되어 있지만 명시적으로)
            self.decision_data.sort(key=lambda x: x['total_size'], reverse=True)
        
        elif self.sort_method == "rating":
            # 평가순 정렬: 평가 안됨 → 낮은 평가 → 높은 평가
            def get_sort_key(model):
                username = model['username']
                
                if username not in self.user_ratings:
                    # 평가 안된 모델: 가장 우선 (0), 크기 큰 순
                    return (0, -model['total_size'])
                
                # 평가된 모델: 평가 점수 순, 같은 평가 내에서는 크기 큰 순
                rating = self.user_ratings[username].get('rating', 0)
                return (rating, -model['total_size'])
            
            self.decision_data.sort(key=get_sort_key)
            
            # 정렬 결과 로그 출력
            print(f"\n📊 평가순 정렬 결과:")
            for i, model in enumerate(self.decision_data):
                username = model['username']
                if username in self.user_ratings:
                    rating = self.user_ratings[username].get('rating', 0)
                    print(f"{i+1}. {username} - {rating}⭐ ({model['total_size']:.0f}MB)")
                else:
                    print(f"{i+1}. {username} - 미평가 ({model['total_size']:.0f}MB)")
    
    def show_current_model(self):
        """현재 모델 정보 표시"""
        if self.current_index >= len(self.decision_data):
            self.finish_decisions()
            return
        
        current = self.decision_data[self.current_index]
        username = current['username']
        
        # 진행률 업데이트
        progress = (self.current_index + 1) / len(self.decision_data) * 100
        self.progress_bar.setValue(int(progress))
        self.progress_label.setText(f"진행: {self.current_index + 1}/{len(self.decision_data)} 모델")
        
        # 모델 정보
        self.model_name_label.setText(f"📊 {username}")
        stats_text = (f"📁 {current['file_count']}개 파일 | "
                     f"💾 {self.format_file_size(current['total_size'])} | "
                     f"💰 삭제시 절약: {self.format_file_size(current['potential_savings'])}")
        self.model_stats_label.setText(stats_text)
        
        # 평가 정보 업데이트
        rating_info = self.get_user_rating_info(username)
        self.rating_history_label.setText(rating_info['message'])
        
        # 평가 입력 초기화
        self.rating_buttons.setExclusive(False)
        for button in self.rating_buttons.buttons():
            button.setChecked(False)
        self.rating_buttons.setExclusive(True)
        self.rating_comment.clear()
        
        # 기존 평가가 있으면 기본값으로 설정
        if not rating_info['is_new'] and rating_info['last_rating']:
            for button in self.rating_buttons.buttons():
                if self.rating_buttons.id(button) == rating_info['last_rating']:
                    button.setChecked(True)
                    break
        
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
        
        # 통계 패널 업데이트
        self.update_stats_panel()
    
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
        username = current['username']
        
        # 평가 저장 (별점이 선택되었을 때만)
        selected_rating = self.rating_buttons.checkedId()
        comment = self.rating_comment.text().strip()
        
        if selected_rating != -1:  # 별점이 선택됨
            self.save_user_rating(username, selected_rating, comment)
            print(f"평가 저장: {username} - {selected_rating}⭐ '{comment}'")
        
        # 이전 결정이 있었다면 절약 용량에서 제거
        if username in self.decisions:
            if self.decisions[username] == 'delete':
                self.total_savings -= current['potential_savings']
        
        # 새로운 결정 저장
        self.decisions[username] = decision
        
        # 절약 용량 계산
        if decision == 'delete':
            self.total_savings += current['potential_savings']
        
        self.savings_label.setText(f"💾 현재까지 절약 예상\n{self.format_file_size(self.total_savings)}")
        
        # 통계 패널 업데이트
        self.update_stats_panel()
        
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


class SortSelectionDialog(QDialog):
    """정렬 방식 선택 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_sort_method = "size"  # 기본값: 크기순
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("정렬 방식 선택")
        self.setFixedSize(600, 400)  # 크기 더 확장
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # 제목
        title_label = QLabel("🔀 모델 정렬 방식을 선택해주세요")
        title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #2c3e50; 
            padding: 15px; 
            text-align: center;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 정렬 방식 선택
        sort_group = QGroupBox("정렬 방식")
        sort_layout = QVBoxLayout(sort_group)
        sort_layout.setContentsMargins(15, 20, 15, 15)  # 여백 늘림
        sort_layout.setSpacing(8)  # 요소간 간격
        
        self.sort_buttons = QButtonGroup()
        
        # 크기순 옵션
        size_button = QRadioButton("📊 크기순 (기본)")
        size_button.setChecked(True)
        size_button.setStyleSheet("font-size: 14px; padding: 10px;")  # 폰트 크기 늘림
        self.sort_buttons.addButton(size_button, 0)
        sort_layout.addWidget(size_button)
        
        size_desc = QLabel("용량이 큰 모델부터 검토합니다.")
        size_desc.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-left: 20px; padding: 5px;")
        sort_layout.addWidget(size_desc)
        
        sort_layout.addSpacing(15)  # 간격 늘림
        
        # 평가순 옵션
        rating_button = QRadioButton("⭐ 평가순 (스마트)")
        rating_button.setStyleSheet("font-size: 14px; padding: 10px;")  # 폰트 크기 늘림
        self.sort_buttons.addButton(rating_button, 1)
        sort_layout.addWidget(rating_button)
        
        rating_desc = QLabel("평가 안된 모델 → 낮은 평가 → 높은 평가 순으로 검토합니다.\n(평가가 좋은 모델일수록 나중에 검토)\n\n• 미평가: 최우선 검토\n• 1⭐~2⭐: 삭제 검토 우선\n• 3⭐~5⭐: 유지 검토 우선")
        rating_desc.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-left: 20px; line-height: 1.5; padding: 8px;")
        rating_desc.setWordWrap(True)
        rating_desc.setMinimumHeight(100)  # 최소 높이 보장
        sort_layout.addWidget(rating_desc)
        
        layout.addWidget(sort_group)
        
        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        layout.addWidget(button_box)
    
    def get_sort_method(self):
        """선택된 정렬 방식 반환"""
        selected_id = self.sort_buttons.checkedId()
        return "rating" if selected_id == 1 else "size"


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