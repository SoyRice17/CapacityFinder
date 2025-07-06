#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import platform
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
                             QPushButton, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QSplitter, QGroupBox, QProgressBar,
                             QCheckBox, QComboBox, QTabWidget, QWidget, QTableWidget,
                             QTableWidgetItem, QLineEdit, QDoubleSpinBox, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
import logging
from rating_dialog import RatingDialog

logger = logging.getLogger(__name__)

class IntelligentCleanupDialog(QDialog):
    """지능형 정리 다이얼로그 - AI 기반 자동 삭제 추천"""
    
    def __init__(self, capacity_finder, parent=None):
        super().__init__(parent)
        self.capacity_finder = capacity_finder
        self.analysis_result = None
        self.setup_ui()
        
        logger.info("🧠 지능형 정리 다이얼로그 초기화")
    
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("🧠 지능형 정리 시스템")
        self.setModal(True)
        self.resize(1200, 800)
        
        layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 탭 1: 자동 삭제 추천
        self.create_auto_cleanup_tab()
        
        # 탭 2: 사용자별 분석
        self.create_user_analysis_tab()
        
        # 탭 3: 우선순위 리스트
        self.create_priority_list_tab()
        
        # 탭 4: 키워드 관리
        self.create_keyword_management_tab()
        
        # 하단 버튼
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("🔄 새로고침")
        self.refresh_button.clicked.connect(self.refresh_analysis)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("닫기")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def create_auto_cleanup_tab(self):
        """자동 삭제 추천 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 설정 섹션
        settings_group = QGroupBox("🎯 자동 정리 설정")
        settings_layout = QHBoxLayout(settings_group)
        
        settings_layout.addWidget(QLabel("목표 절약 용량:"))
        
        self.target_savings_spin = QSpinBox()
        self.target_savings_spin.setRange(1, 2000)  # 2테라까지 확장
        self.target_savings_spin.setValue(10)
        self.target_savings_spin.setSuffix(" GB")
        settings_layout.addWidget(self.target_savings_spin)
        
        self.analyze_button = QPushButton("🧠 지능형 분석 시작")
        self.analyze_button.clicked.connect(self.run_intelligent_analysis)
        settings_layout.addWidget(self.analyze_button)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 분할기
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 왼쪽: 분석 결과
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("📊 분석 결과"))
        self.analysis_text = QTextEdit()
        self.analysis_text.setMaximumHeight(200)
        self.analysis_text.setReadOnly(True)
        left_layout.addWidget(self.analysis_text)
        
        # 삭제 추천 파일 리스트
        left_layout.addWidget(QLabel("🗑️ 삭제 추천 파일 (더블클릭: 영상 재생)"))
        self.suggested_files_tree = QTreeWidget()
        self.suggested_files_tree.setHeaderLabels(["사용자", "파일명", "크기", "복합점수", "레이팅점수", "파일점수"])
        self.suggested_files_tree.itemDoubleClicked.connect(self.play_video_from_suggested_files)
        left_layout.addWidget(self.suggested_files_tree)
        
        splitter.addWidget(left_widget)
        
        # 오른쪽: 사용자별 전략
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("👥 사용자별 정리 전략 (더블클릭: 레이팅 수정)"))
        self.strategy_tree = QTreeWidget()
        self.strategy_tree.setHeaderLabels(["사용자", "평점", "전략", "유지비율", "코멘트"])
        self.strategy_tree.itemDoubleClicked.connect(self.edit_user_rating)
        right_layout.addWidget(self.strategy_tree)
        
        splitter.addWidget(right_widget)
        
        # 실행 버튼
        execute_layout = QHBoxLayout()
        
        self.execute_button = QPushButton("⚡ 자동 정리 실행")
        self.execute_button.clicked.connect(self.execute_intelligent_cleanup)
        self.execute_button.setEnabled(False)
        self.execute_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        execute_layout.addWidget(self.execute_button)
        
        layout.addLayout(execute_layout)
        
        self.tab_widget.addTab(tab, "🤖 자동 삭제 추천")
    
    def create_user_analysis_tab(self):
        """사용자별 분석 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 사용자 선택
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("분석할 사용자:"))
        
        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(200)
        user_layout.addWidget(self.user_combo)
        
        self.analyze_user_button = QPushButton("👤 사용자 분석")
        self.analyze_user_button.clicked.connect(self.analyze_selected_user)
        user_layout.addWidget(self.analyze_user_button)
        
        user_layout.addStretch()
        layout.addLayout(user_layout)
        
        # 분석 결과 표시
        self.user_analysis_text = QTextEdit()
        self.user_analysis_text.setMaximumHeight(150)
        self.user_analysis_text.setReadOnly(True)
        layout.addWidget(self.user_analysis_text)
        
        # 파일 리스트 (점수별)
        layout.addWidget(QLabel("📁 파일 리스트 (더블클릭: 영상 재생)"))
        self.user_files_tree = QTreeWidget()
        self.user_files_tree.setHeaderLabels(["순위", "파일명", "크기", "복합점수", "파일점수", "레이팅점수", "품질"])
        self.user_files_tree.itemDoubleClicked.connect(self.play_video_from_user_files)
        layout.addWidget(self.user_files_tree)
        
        self.tab_widget.addTab(tab, "👤 사용자별 분석")
    
    def create_priority_list_tab(self):
        """우선순위 리스트 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 상단 설명
        info_label = QLabel("📋 전체 파일 우선순위 리스트 - AI 판단 기준의 투명성 확보 및 수동 선별 가이드")
        info_label.setFont(QFont("Arial", 10))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #2c3e50; margin: 5px;")
        layout.addWidget(info_label)
        
        # 설정
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(QLabel("표시할 파일 수:"))
        
        self.priority_count_spin = QSpinBox()
        self.priority_count_spin.setRange(10, 10000)  # 10000개까지 확장
        self.priority_count_spin.setValue(200)  # 기본값 증가
        self.priority_count_spin.setSuffix("개")
        priority_layout.addWidget(self.priority_count_spin)
        
        # 균등 분배 모드 체크박스
        self.balanced_mode_checkbox = QCheckBox("🔄 균등 분배 모드")
        self.balanced_mode_checkbox.setToolTip("각 사용자별로 골고루 파일을 선택합니다.\n한 사용자가 독점하는 것을 방지합니다.")
        self.balanced_mode_checkbox.setChecked(True)  # 기본적으로 활성화
        priority_layout.addWidget(self.balanced_mode_checkbox)
        
        self.generate_priority_button = QPushButton("📋 우선순위 생성")
        self.generate_priority_button.clicked.connect(self.generate_priority_list)
        priority_layout.addWidget(self.generate_priority_button)
        
        priority_layout.addStretch()
        layout.addLayout(priority_layout)
        
        # 우선순위 리스트
        layout.addWidget(QLabel("📋 우선순위 리스트 (더블클릭: 영상 재생)"))
        self.priority_tree = QTreeWidget()
        self.priority_tree.setHeaderLabels(["순위", "사용자", "파일명", "크기", "복합점수", "삭제우선도"])
        self.priority_tree.itemDoubleClicked.connect(self.play_video_from_priority_list)
        layout.addWidget(self.priority_tree)
        
        # 통계 표시
        self.priority_stats_text = QTextEdit()
        self.priority_stats_text.setMaximumHeight(100)
        self.priority_stats_text.setReadOnly(True)
        layout.addWidget(self.priority_stats_text)
        
        self.tab_widget.addTab(tab, "📋 우선순위 리스트")
        
        # 사용자 목록 초기화
        self.update_user_combo()
    
    def update_user_combo(self):
        """사용자 콤보박스 업데이트"""
        self.user_combo.clear()
        if self.capacity_finder.dic_files:
            users = sorted(self.capacity_finder.dic_files.keys())
            self.user_combo.addItems(users)
    
    def run_intelligent_analysis(self):
        """지능형 분석 실행"""
        target_gb = self.target_savings_spin.value()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 무한 진행바
        self.analyze_button.setEnabled(False)
        
        try:
            logger.info(f"🧠 지능형 분석 시작: 목표 {target_gb}GB")
            
            # 분석 실행
            self.analysis_result = self.capacity_finder.get_intelligent_deletion_analysis(target_gb)
            
            # 결과 표시
            self.display_analysis_result()
            self.execute_button.setEnabled(True)
            
            logger.info("✅ 지능형 분석 완료")
            
        except Exception as e:
            logger.error(f"분석 오류: {e}")
            QMessageBox.critical(self, "분석 오류", f"분석 중 오류가 발생했습니다:\n{e}")
        
        finally:
            self.progress_bar.setVisible(False)
            self.analyze_button.setEnabled(True)
    
    def display_analysis_result(self):
        """분석 결과 표시"""
        if not self.analysis_result:
            return
        
        stats = self.analysis_result['statistics']
        suggestions = self.analysis_result['suggestions']
        
        # 분석 텍스트 업데이트
        analysis_text = f"""🧠 지능형 분석 결과

📁 전체 파일: {stats['total_files']:,}개
🗑️ 삭제 추천: {stats['suggested_files']:,}개
💾 절약 예상: {stats['suggested_savings_gb']:.2f} GB
📈 효율성: {stats['efficiency_ratio']*100:.1f}%

삭제 기준: {suggestions['criteria']}
"""
        self.analysis_text.setText(analysis_text)
        
        # 추천 파일 리스트 표시
        self.suggested_files_tree.clear()
        for file_data in suggestions['suggested_files']:
            item = QTreeWidgetItem(self.suggested_files_tree)
            item.setText(0, file_data['username'])
            item.setText(1, file_data['name'])
            item.setText(2, self.format_file_size(file_data['size']))
            item.setText(3, f"{file_data['composite_score']:.3f}")
            item.setText(4, f"{file_data['rating_score']:.3f}")
            item.setText(5, f"{file_data['file_score']:.3f}")
            
            # 점수에 따른 색상 (극단적 기준)
            if file_data['composite_score'] <= 0.2:
                item.setBackground(0, QColor(255, 150, 150))  # 진한 빨간색 (삭제 강력 추천)
            elif file_data['composite_score'] <= 0.3:
                item.setBackground(0, QColor(255, 200, 200))  # 빨간색 (삭제 추천)
            elif file_data['composite_score'] <= 0.5:
                item.setBackground(0, QColor(255, 230, 200))  # 주황색 (삭제 고려)
        
        # 사용자별 전략 표시
        self.strategy_tree.clear()
        for username, strategy in self.analysis_result['user_strategies'].items():
            item = QTreeWidgetItem(self.strategy_tree)
            item.setText(0, username)
            item.setText(1, f"{strategy['rating']}/5")
            item.setText(2, strategy['strategy'])
            item.setText(3, f"{strategy['keep_ratio']*100:.0f}%")
            item.setText(4, strategy['comment'][:50] + "..." if len(strategy['comment']) > 50 else strategy['comment'])
            
            # 전략에 따른 색상
            if strategy['rating'] <= 2:
                item.setBackground(1, QColor(255, 200, 200))  # 낮은 평점
            elif strategy['rating'] >= 4:
                item.setBackground(1, QColor(200, 255, 200))  # 높은 평점
    
    def analyze_selected_user(self):
        """선택된 사용자 분석"""
        username = self.user_combo.currentText()
        if not username:
            return
        
        try:
            report = self.capacity_finder.get_user_intelligence_report(username)
            if not report:
                QMessageBox.warning(self, "분석 실패", f"사용자 '{username}'을 분석할 수 없습니다.")
                return
            
            # 분석 결과 텍스트
            breakdown = report['quality_breakdown']
            strategy = report['cleanup_strategy']
            
            analysis_text = f"""👤 사용자: {username}

📊 품질 분석 (극단적 기준):
• 고품질 (0.8+): {breakdown['high_quality']}개
• 중품질 (0.2-0.8): {breakdown['medium_quality']}개  
• 저품질 (0.2-): {breakdown['low_quality']}개

💾 총 용량: {self.format_file_size(report['total_size'])}
📁 파일 수: {report['file_count']}개

🎯 정리 전략: {strategy['strategy'] if strategy else '없음'}
📈 유지 비율: {(strategy['keep_ratio']*100 if strategy else 0):.0f}%
"""
            self.user_analysis_text.setText(analysis_text)
            
            # 파일 리스트 표시
            self.user_files_tree.clear()
            for i, file_data in enumerate(report['files']):
                item = QTreeWidgetItem(self.user_files_tree)
                item.setText(0, str(i + 1))
                item.setText(1, file_data['name'])
                item.setText(2, self.format_file_size(file_data['size']))
                item.setText(3, f"{file_data['composite_score']:.3f}")
                item.setText(4, f"{file_data['file_score']:.3f}")
                item.setText(5, f"{file_data['rating_score']:.3f}")
                
                # 품질 라벨 (극단적 기준)
                if file_data['composite_score'] >= 0.8:
                    quality = "고품질"
                    item.setBackground(6, QColor(200, 255, 200))
                elif file_data['composite_score'] >= 0.2:
                    quality = "중품질"
                    item.setBackground(6, QColor(255, 255, 200))
                else:
                    quality = "저품질"
                    item.setBackground(6, QColor(255, 150, 150))
                
                item.setText(6, quality)
            
        except Exception as e:
            logger.error(f"사용자 분석 오류: {e}")
            QMessageBox.critical(self, "분석 오류", f"사용자 분석 중 오류가 발생했습니다:\n{e}")
    
    def generate_priority_list(self):
        """우선순위 리스트 생성"""
        count = self.priority_count_spin.value()
        balanced_mode = self.balanced_mode_checkbox.isChecked()
        
        try:
            priority_result = self.capacity_finder.get_priority_deletion_list(count, balanced_mode)
            
            # 우선순위 리스트 표시
            self.priority_tree.clear()
            for i, file_data in enumerate(priority_result['priority_files']):
                item = QTreeWidgetItem(self.priority_tree)
                item.setText(0, str(i + 1))
                item.setText(1, file_data['username'])
                item.setText(2, file_data['name'])
                item.setText(3, self.format_file_size(file_data['size']))
                item.setText(4, f"{file_data['composite_score']:.3f}")
                
                # 삭제 우선도 계산 (극단적 기준)
                if file_data['composite_score'] <= 0.1:
                    priority = "최고"
                    item.setBackground(5, QColor(255, 100, 100))
                elif file_data['composite_score'] <= 0.2:
                    priority = "매우 높음"
                    item.setBackground(5, QColor(255, 150, 150))
                elif file_data['composite_score'] <= 0.3:
                    priority = "높음"
                    item.setBackground(5, QColor(255, 200, 200))
                elif file_data['composite_score'] <= 0.5:
                    priority = "보통"
                    item.setBackground(5, QColor(255, 255, 200))
                elif file_data['composite_score'] <= 0.7:
                    priority = "낮음"
                    item.setBackground(5, QColor(200, 255, 200))
                else:
                    priority = "매우 낮음"
                    item.setBackground(5, QColor(150, 255, 150))
                
                item.setText(5, priority)
            
            # 통계 표시
            mode_text = "🔄 균등 분배" if priority_result.get('balanced_mode', False) else "📊 점수 순위"
            
            stats_text = f"""📋 우선순위 삭제 리스트 ({mode_text})

🗑️ 표시된 파일: {priority_result['file_count']}개
💾 절약 가능: {priority_result['total_savings_gb']:.2f} GB

👥 사용자별 분포:
"""
            for username, stats in priority_result['user_breakdown'].items():
                stats_text += f"• {username}: {stats['count']}개 ({self.format_file_size(stats['size'])})\n"
            
            self.priority_stats_text.setText(stats_text)
            
        except Exception as e:
            logger.error(f"우선순위 생성 오류: {e}")
            QMessageBox.critical(self, "생성 오류", f"우선순위 리스트 생성 중 오류가 발생했습니다:\n{e}")
    
    def execute_intelligent_cleanup(self):
        """지능형 정리 실행"""
        if not self.analysis_result:
            QMessageBox.warning(self, "분석 필요", "먼저 지능형 분석을 실행해주세요.")
            return
        
        suggested_files = self.analysis_result['suggestions']['suggested_files']
        if not suggested_files:
            QMessageBox.information(self, "정리 불필요", "삭제할 파일이 없습니다.")
            return
        
        # 확인 다이얼로그
        savings_gb = self.analysis_result['suggestions']['total_savings_gb']
        file_count = len(suggested_files)
        
        reply = QMessageBox.question(
            self, "지능형 정리 확인",
            f"🧠 지능형 분석 결과를 바탕으로 {file_count}개 파일을 삭제하시겠습니까?\n"
            f"💾 절약 예상 용량: {savings_gb:.2f} GB\n\n"
            f"⚠️ 이 작업은 되돌릴 수 없습니다!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 정리 실행
                result = self.capacity_finder.execute_intelligent_cleanup(
                    self.analysis_result,
                    confirm_callback=None  # 이미 확인했음
                )
                
                if result and result['success']:
                    QMessageBox.information(
                        self, "정리 완료",
                        f"✅ 지능형 정리가 완료되었습니다!\n\n"
                        f"🗑️ 삭제된 파일: {result['deleted_count']}개\n"
                        f"💾 절약된 용량: {result['deleted_size_gb']:.2f} GB"
                    )
                    
                    # 분석 결과 초기화
                    self.analysis_result = None
                    self.execute_button.setEnabled(False)
                    self.analysis_text.clear()
                    self.suggested_files_tree.clear()
                    self.strategy_tree.clear()
                else:
                    QMessageBox.warning(self, "정리 실패", "정리 중 오류가 발생했습니다.")
                    
            except Exception as e:
                logger.error(f"정리 실행 오류: {e}")
                QMessageBox.critical(self, "실행 오류", f"정리 실행 중 오류가 발생했습니다:\n{e}")
    
    def refresh_analysis(self):
        """분석 새로고침"""
        self.update_user_combo()
        self.analysis_result = None
        self.execute_button.setEnabled(False)
        
        # 모든 표시 초기화
        self.analysis_text.clear()
        self.suggested_files_tree.clear()
        self.strategy_tree.clear()
        self.user_analysis_text.clear()
        self.user_files_tree.clear()
        self.priority_tree.clear()
        self.priority_stats_text.clear()
        
        logger.info("🔄 지능형 정리 다이얼로그 새로고침")
    
    def format_file_size(self, size_mb):
        """파일 사이즈 포맷팅"""
        if size_mb >= 1024:
            return f"{size_mb/1024:.2f} GB"
        else:
            return f"{size_mb:.2f} MB" 
    
    def create_keyword_management_tab(self):
        """키워드 관리 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 상단 설명
        info_label = QLabel("🔧 키워드 가중치 시스템 관리")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(info_label)
        
        # 분할기
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 왼쪽: 키워드 목록
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("📊 현재 키워드 목록"))
        
        # 키워드 테이블
        self.keyword_table = QTableWidget()
        self.keyword_table.setColumnCount(3)
        self.keyword_table.setHorizontalHeaderLabels(["키워드", "가중치", "카테고리"])
        
        # 테이블 열 너비 설정
        header = self.keyword_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        # 테이블 스타일 설정
        self.keyword_table.setAlternatingRowColors(True)
        self.keyword_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.keyword_table.setSelectionMode(QTableWidget.SingleSelection)
        
        left_layout.addWidget(self.keyword_table)
        
        # 키워드 테이블 버튼
        table_button_layout = QHBoxLayout()
        
        self.load_keywords_button = QPushButton("🔄 키워드 로드")
        self.load_keywords_button.clicked.connect(self.load_keywords)
        table_button_layout.addWidget(self.load_keywords_button)
        
        self.delete_keyword_button = QPushButton("🗑️ 선택 삭제")
        self.delete_keyword_button.clicked.connect(self.delete_selected_keyword)
        table_button_layout.addWidget(self.delete_keyword_button)
        
        self.reset_keywords_button = QPushButton("🔄 기본값 복원")
        self.reset_keywords_button.clicked.connect(self.reset_keywords)
        table_button_layout.addWidget(self.reset_keywords_button)
        
        table_button_layout.addStretch()
        left_layout.addLayout(table_button_layout)
        
        splitter.addWidget(left_widget)
        
        # 오른쪽: 키워드 추가/수정
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("➕ 키워드 추가/수정"))
        
        # 키워드 입력 그룹
        input_group = QGroupBox("키워드 정보")
        input_layout = QVBoxLayout(input_group)
        
        # 키워드 입력
        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(QLabel("키워드:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("키워드 입력 (예: ㅅㅌㅊ)")
        keyword_layout.addWidget(self.keyword_input)
        input_layout.addLayout(keyword_layout)
        
        # 가중치 입력
        weight_layout = QHBoxLayout()
        weight_layout.addWidget(QLabel("가중치:"))
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(-1.0, 1.0)
        self.weight_input.setSingleStep(0.1)
        self.weight_input.setDecimals(2)
        self.weight_input.setValue(0.0)
        weight_layout.addWidget(self.weight_input)
        input_layout.addLayout(weight_layout)
        
        # 카테고리 선택
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("카테고리:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["긍정적 (유지선호)", "부정적 (삭제선호)", "중립"])
        category_layout.addWidget(self.category_combo)
        input_layout.addLayout(category_layout)
        
        right_layout.addWidget(input_group)
        
        # 추가/수정 버튼
        add_button_layout = QHBoxLayout()
        
        self.add_keyword_button = QPushButton("➕ 키워드 추가")
        self.add_keyword_button.clicked.connect(self.add_keyword)
        add_button_layout.addWidget(self.add_keyword_button)
        
        self.update_keyword_button = QPushButton("✏️ 키워드 수정")
        self.update_keyword_button.clicked.connect(self.update_keyword)
        add_button_layout.addWidget(self.update_keyword_button)
        
        right_layout.addLayout(add_button_layout)
        
        # 가중치 가이드
        guide_group = QGroupBox("📋 가중치 가이드")
        guide_layout = QVBoxLayout(guide_group)
        
        guide_text = """
• 긍정적 키워드: 0.1 ~ 1.0 (높을수록 보존 우선)
  - 최고품질: 0.9 ~ 1.0 (ㅆㅅㅌㅊ, GOAT)
  - 고품질: 0.7 ~ 0.9 (ㅅㅌㅊ, 신)
  - 중품질: 0.5 ~ 0.7 (ㅈㅅㅌㅊ, 귀여움)
  - 저품질: 0.1 ~ 0.5 (자위, 육덕)

• 부정적 키워드: -1.0 ~ -0.1 (낮을수록 삭제 우선)
  - 강력삭제: -0.7 ~ -1.0 (가지치기필요, 추적중지)
  - 일반삭제: -0.3 ~ -0.7 (녹화중지, 계륵)
  - 약한삭제: -0.1 ~ -0.3 (현재, 애매함)

• 중립 키워드: -0.1 ~ 0.1 (거의 영향 없음)
        """
        
        guide_label = QLabel(guide_text)
        guide_label.setFont(QFont("Consolas", 9))
        guide_label.setWordWrap(True)
        guide_layout.addWidget(guide_label)
        
        right_layout.addWidget(guide_group)
        
        right_layout.addStretch()
        
        # 저장 버튼
        save_layout = QHBoxLayout()
        
        self.save_keywords_button = QPushButton("💾 변경사항 저장")
        self.save_keywords_button.clicked.connect(self.save_keywords)
        self.save_keywords_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_layout.addWidget(self.save_keywords_button)
        
        right_layout.addLayout(save_layout)
        
        splitter.addWidget(right_widget)
        
        # 키워드 테이블 선택 이벤트
        self.keyword_table.itemSelectionChanged.connect(self.on_keyword_selected)
        
        # 탭 추가
        self.tab_widget.addTab(tab, "🔧 키워드 관리")
        
        # 초기 키워드 로드
        self.load_keywords()
    
    def load_keywords(self):
        """현재 키워드 목록을 테이블에 로드"""
        try:
            # 지능형 시스템에서 키워드 가져오기
            keyword_weights = self.capacity_finder.intelligent_system.keyword_weights
            
            # 테이블 행 수 설정
            self.keyword_table.setRowCount(len(keyword_weights))
            
            # 키워드를 카테고리별로 정렬
            sorted_keywords = sorted(keyword_weights.items(), key=lambda x: (-x[1], x[0]))
            
            for row, (keyword, weight) in enumerate(sorted_keywords):
                # 키워드
                keyword_item = QTableWidgetItem(keyword)
                keyword_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.keyword_table.setItem(row, 0, keyword_item)
                
                # 가중치
                weight_item = QTableWidgetItem(f"{weight:.2f}")
                weight_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.keyword_table.setItem(row, 1, weight_item)
                
                # 카테고리 결정
                if weight > 0.1:
                    category = "긍정적 (유지선호)"
                    color = QColor(46, 204, 113)  # 녹색
                elif weight < -0.1:
                    category = "부정적 (삭제선호)"
                    color = QColor(231, 76, 60)   # 빨간색
                else:
                    category = "중립"
                    color = QColor(149, 165, 166)  # 회색
                
                category_item = QTableWidgetItem(category)
                category_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                category_item.setBackground(color.lighter(180))
                self.keyword_table.setItem(row, 2, category_item)
            
            logger.info(f"키워드 로드 완료: {len(keyword_weights)}개")
            
        except Exception as e:
            logger.error(f"키워드 로드 오류: {e}")
            QMessageBox.warning(self, "오류", f"키워드를 로드할 수 없습니다: {e}")
    
    def add_keyword(self):
        """새 키워드 추가"""
        keyword = self.keyword_input.text().strip()
        weight = self.weight_input.value()
        
        if not keyword:
            QMessageBox.warning(self, "입력 오류", "키워드를 입력해주세요.")
            return
        
        try:
            # 지능형 시스템에 키워드 추가
            self.capacity_finder.intelligent_system.keyword_weights[keyword] = weight
            
            # 테이블 새로고침
            self.load_keywords()
            
            # 입력 필드 초기화
            self.keyword_input.clear()
            self.weight_input.setValue(0.0)
            self.category_combo.setCurrentIndex(0)
            
            logger.info(f"키워드 추가: {keyword} = {weight}")
            QMessageBox.information(self, "성공", f"키워드 '{keyword}'이 추가되었습니다.")
            
        except Exception as e:
            logger.error(f"키워드 추가 오류: {e}")
            QMessageBox.warning(self, "오류", f"키워드를 추가할 수 없습니다: {e}")
    
    def update_keyword(self):
        """선택된 키워드 수정"""
        selected_row = self.keyword_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "선택 오류", "수정할 키워드를 선택해주세요.")
            return
        
        # 선택된 키워드 가져오기
        old_keyword = self.keyword_table.item(selected_row, 0).text()
        new_keyword = self.keyword_input.text().strip()
        new_weight = self.weight_input.value()
        
        if not new_keyword:
            QMessageBox.warning(self, "입력 오류", "키워드를 입력해주세요.")
            return
        
        try:
            # 기존 키워드 삭제 (키워드명이 변경된 경우)
            if old_keyword != new_keyword:
                del self.capacity_finder.intelligent_system.keyword_weights[old_keyword]
            
            # 새 키워드 추가/수정
            self.capacity_finder.intelligent_system.keyword_weights[new_keyword] = new_weight
            
            # 테이블 새로고침
            self.load_keywords()
            
            # 입력 필드 초기화
            self.keyword_input.clear()
            self.weight_input.setValue(0.0)
            self.category_combo.setCurrentIndex(0)
            
            logger.info(f"키워드 수정: {old_keyword} -> {new_keyword} = {new_weight}")
            QMessageBox.information(self, "성공", f"키워드가 수정되었습니다.")
            
        except Exception as e:
            logger.error(f"키워드 수정 오류: {e}")
            QMessageBox.warning(self, "오류", f"키워드를 수정할 수 없습니다: {e}")
    
    def delete_selected_keyword(self):
        """선택된 키워드 삭제"""
        selected_row = self.keyword_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "선택 오류", "삭제할 키워드를 선택해주세요.")
            return
        
        keyword = self.keyword_table.item(selected_row, 0).text()
        
        # 확인 대화상자
        reply = QMessageBox.question(self, "삭제 확인", 
                                   f"키워드 '{keyword}'을 삭제하시겠습니까?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # 키워드 삭제
                del self.capacity_finder.intelligent_system.keyword_weights[keyword]
                
                # 테이블 새로고침
                self.load_keywords()
                
                logger.info(f"키워드 삭제: {keyword}")
                QMessageBox.information(self, "성공", f"키워드 '{keyword}'이 삭제되었습니다.")
                
            except Exception as e:
                logger.error(f"키워드 삭제 오류: {e}")
                QMessageBox.warning(self, "오류", f"키워드를 삭제할 수 없습니다: {e}")
    
    def reset_keywords(self):
        """키워드를 기본값으로 복원"""
        reply = QMessageBox.question(self, "복원 확인",
                                   "모든 키워드를 기본값으로 복원하시겠습니까?\n현재 설정이 모두 삭제됩니다.",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # 기본 키워드 가중치 복원 (극단적 버전)
                default_weights = {
                    # 긍정적 키워드 (유지 선호) - 더 극단적으로
                    'ㅅㅌㅊ': 1.2,        # 0.9 → 1.2
                    'ㅆㅅㅌㅊ': 1.5,       # 0.95 → 1.5
                    'ㅈㅅㅌㅊ': 1.0,       # 0.8 → 1.0
                    'ㅍㅅㅌㅊ': 0.8,       # 0.7 → 0.8
                    'GOAT': 1.5,         # 0.95 → 1.5
                    '신': 1.3,           # 0.9 → 1.3
                    '귀여움': 1.0,        # 0.8 → 1.0
                    '올노': 0.9,         # 0.7 → 0.9
                    '자위': 0.7,         # 0.6 → 0.7
                    
                    # 부정적 키워드 (삭제 선호) - 더 극단적으로
                    '가지치기필요': -1.5,   # -0.8 → -1.5
                    '녹화중지': -1.0,      # -0.5 → -1.0
                    '녹화중단': -1.0,      # -0.5 → -1.0
                    '추적중지': -1.2,      # -0.6 → -1.2
                    '현재': -0.6,         # -0.3 → -0.6
                    '애매함': -0.8,        # -0.4 → -0.8
                    '계륵': -1.3,         # -0.6 → -1.3
                    '정으로보는느낌': -1.0,  # -0.5 → -1.0
                    'ㅍㅌㅊ': -0.5,        # -0.2 → -0.5
                    
                    # 중립 키워드 (그대로 유지)
                    '얼굴': 0.1,
                    '육덕': 0.2,
                    '코스': 0.1,
                    '2인': 0.1,
                    '3인': 0.1,
                }
                
                # 기본값으로 설정
                self.capacity_finder.intelligent_system.keyword_weights = default_weights
                
                # 테이블 새로고침
                self.load_keywords()
                
                logger.info("키워드 기본값 복원 완료")
                QMessageBox.information(self, "성공", "키워드가 기본값으로 복원되었습니다.")
                
            except Exception as e:
                logger.error(f"키워드 복원 오류: {e}")
                QMessageBox.warning(self, "오류", f"키워드를 복원할 수 없습니다: {e}")
    
    def save_keywords(self):
        """키워드 변경사항을 영구 저장"""
        try:
            # 키워드 가중치를 파일로 저장
            import json
            
            keyword_data = {
                'keywords': self.capacity_finder.intelligent_system.keyword_weights,
                'last_updated': __import__('datetime').datetime.now().isoformat()
            }
            
            with open('keyword_weights.json', 'w', encoding='utf-8') as f:
                json.dump(keyword_data, f, ensure_ascii=False, indent=2)
            
            logger.info("키워드 변경사항 저장 완료")
            QMessageBox.information(self, "성공", "키워드 변경사항이 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"키워드 저장 오류: {e}")
            QMessageBox.warning(self, "오류", f"키워드를 저장할 수 없습니다: {e}")
    
    def on_keyword_selected(self):
        """키워드 테이블에서 선택된 항목 처리"""
        selected_row = self.keyword_table.currentRow()
        if selected_row >= 0:
            keyword = self.keyword_table.item(selected_row, 0).text()
            weight = float(self.keyword_table.item(selected_row, 1).text())
            
            # 입력 필드에 선택된 값 설정
            self.keyword_input.setText(keyword)
            self.weight_input.setValue(weight)
            
            # 카테고리 자동 설정
            if weight > 0.1:
                self.category_combo.setCurrentIndex(0)  # 긍정적
            elif weight < -0.1:
                self.category_combo.setCurrentIndex(1)  # 부정적
            else:
                self.category_combo.setCurrentIndex(2)  # 중립
    
    # === 🎬 영상 재생 기능 ===
    
    def play_video_from_suggested_files(self, item):
        """추천 파일 리스트에서 영상 재생"""
        # 어느 컬럼을 클릭해도 작동하도록 파일명을 가져옴
        row = item.parent().indexOfChild(item) if item.parent() else self.suggested_files_tree.indexOfTopLevelItem(item)
        filename = self.suggested_files_tree.topLevelItem(row).text(1)  # 파일명은 1번 컬럼
        self.play_video(filename)
    
    def play_video_from_user_files(self, item):
        """사용자 파일 리스트에서 영상 재생"""
        # 어느 컬럼을 클릭해도 작동하도록 파일명을 가져옴
        row = item.parent().indexOfChild(item) if item.parent() else self.user_files_tree.indexOfTopLevelItem(item)
        filename = self.user_files_tree.topLevelItem(row).text(1)  # 파일명은 1번 컬럼
        self.play_video(filename)
    
    def play_video_from_priority_list(self, item):
        """우선순위 리스트에서 영상 재생"""
        # 어느 컬럼을 클릭해도 작동하도록 파일명을 가져옴
        row = item.parent().indexOfChild(item) if item.parent() else self.priority_tree.indexOfTopLevelItem(item)
        filename = self.priority_tree.topLevelItem(row).text(2)  # 파일명은 2번 컬럼
        self.play_video(filename)
    
    def play_video(self, filename):
        """영상 파일 재생"""
        try:
            # 전체 파일 경로 생성
            file_path = os.path.join(self.capacity_finder.current_path, filename)
            
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "파일 없음", f"파일을 찾을 수 없습니다:\n{file_path}")
                return
            
            # 운영체제별 기본 플레이어로 실행
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
            
            logger.info(f"🎬 영상 재생 요청: {filename}")
            
        except Exception as e:
            logger.error(f"영상 재생 오류: {e}")
            QMessageBox.critical(self, "재생 오류", f"영상 재생 중 오류가 발생했습니다:\n{e}")
    
    # === 💫 레이팅 수정 기능 ===
    
    def edit_user_rating(self, item):
        """사용자 레이팅 수정"""
        # 어느 컬럼을 클릭해도 작동하도록 사용자명을 가져옴
        row = item.parent().indexOfChild(item) if item.parent() else self.strategy_tree.indexOfTopLevelItem(item)
        username = self.strategy_tree.topLevelItem(row).text(0)  # 사용자명은 0번 컬럼
        self.open_rating_dialog(username)
    
    def open_rating_dialog(self, username):
        """레이팅 다이얼로그 열기"""
        try:
            dialog = RatingDialog(username, self)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                # 레이팅이 수정되었으므로 지능형 시스템 데이터 다시 로드
                self.capacity_finder.intelligent_system.keyword_weights = self.capacity_finder.intelligent_system.load_keyword_weights()
                self.capacity_finder.intelligent_system.ratings_data = self.capacity_finder.intelligent_system.load_ratings()
                
                logger.info(f"💫 레이팅 수정 완료: {username}")
                
                # 현재 활성 탭에 따라 즉시 반영
                current_tab = self.tab_widget.currentIndex()
                
                if current_tab == 0:  # 자동 삭제 추천 탭
                    if self.analysis_result:
                        # 기존 분석 결과가 있으면 자동으로 재분석
                        target_gb = self.target_savings_spin.value()
                        self.analysis_result = self.capacity_finder.get_intelligent_deletion_analysis(target_gb)
                        self.display_analysis_result()
                        self.execute_button.setEnabled(True)
                        logger.info("🔄 자동 삭제 추천 탭 분석 결과 업데이트됨")
                        
                elif current_tab == 1:  # 사용자별 분석 탭
                    if self.user_combo.currentText() == username:
                        # 현재 선택된 사용자가 수정된 사용자면 즉시 업데이트
                        self.analyze_selected_user()
                        logger.info(f"🔄 사용자 분석 탭 '{username}' 업데이트됨")
                        
                elif current_tab == 2:  # 우선순위 리스트 탭
                    if self.priority_tree.topLevelItemCount() > 0:
                        # 우선순위 리스트가 있으면 재생성
                        self.generate_priority_list()
                        logger.info("🔄 우선순위 리스트 탭 업데이트됨")
                
                # 성공 메시지
                QMessageBox.information(self, "레이팅 수정", f"'{username}' 사용자의 레이팅이 수정되었습니다.\n✨ 분석 결과가 자동으로 업데이트되었습니다!")
                
        except Exception as e:
            logger.error(f"레이팅 수정 오류: {e}")
            QMessageBox.critical(self, "수정 오류", f"레이팅 수정 중 오류가 발생했습니다:\n{e}")