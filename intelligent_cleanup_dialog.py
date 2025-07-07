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
        
        # 탭 5: 보호 목록 관리
        self.create_protected_files_tab()
        
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
        left_layout.addWidget(QLabel("🗑️ 삭제 추천 파일 (더블클릭: 영상 재생, 우클릭: 보호 추가)"))
        self.suggested_files_tree = QTreeWidget()
        self.suggested_files_tree.setHeaderLabels(["사용자", "파일명", "크기", "복합점수", "레이팅점수", "파일점수"])
        self.suggested_files_tree.itemDoubleClicked.connect(self.play_video_from_suggested_files)
        
        # 우클릭 메뉴 설정
        self.suggested_files_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.suggested_files_tree.customContextMenuRequested.connect(self.show_suggested_files_context_menu)
        
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
        user_files_layout = QVBoxLayout()
        
        # 리스트 제목과 선택 버튼들
        user_files_header_layout = QHBoxLayout()
        user_files_header_layout.addWidget(QLabel("📁 파일 리스트 (더블클릭: 영상 재생)"))
        user_files_header_layout.addStretch()
        
        # 선택 관련 버튼들
        self.select_all_user_files_button = QPushButton("☑️ 전체 선택")
        self.select_all_user_files_button.clicked.connect(self.select_all_user_files)
        user_files_header_layout.addWidget(self.select_all_user_files_button)
        
        self.deselect_all_user_files_button = QPushButton("☐ 전체 해제")
        self.deselect_all_user_files_button.clicked.connect(self.deselect_all_user_files)
        user_files_header_layout.addWidget(self.deselect_all_user_files_button)
        
        self.delete_selected_user_files_button = QPushButton("🗑️ 선택 삭제")
        self.delete_selected_user_files_button.clicked.connect(self.delete_selected_user_files)
        self.delete_selected_user_files_button.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        self.delete_selected_user_files_button.setEnabled(False)
        user_files_header_layout.addWidget(self.delete_selected_user_files_button)
        
        user_files_layout.addLayout(user_files_header_layout)
        
        # 트리 위젯
        self.user_files_tree = QTreeWidget()
        self.user_files_tree.setHeaderLabels(["선택", "순위", "파일명", "크기", "복합점수", "파일점수", "레이팅점수", "품질"])
        self.user_files_tree.itemDoubleClicked.connect(self.play_video_from_user_files)
        self.user_files_tree.itemChanged.connect(self.on_user_file_selection_changed)
        user_files_layout.addWidget(self.user_files_tree)
        
        layout.addLayout(user_files_layout)
        
        # 선택된 파일 통계
        self.selected_user_files_stats_text = QTextEdit()
        self.selected_user_files_stats_text.setMaximumHeight(80)
        self.selected_user_files_stats_text.setReadOnly(True)
        self.selected_user_files_stats_text.setStyleSheet("background-color: #f0f8ff; border: 1px solid #87ceeb;")
        layout.addWidget(self.selected_user_files_stats_text)
        
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
        priority_list_layout = QVBoxLayout()
        
        # 리스트 제목과 선택 버튼들
        list_header_layout = QHBoxLayout()
        list_header_layout.addWidget(QLabel("📋 우선순위 리스트 (더블클릭: 영상 재생)"))
        list_header_layout.addStretch()
        
        # 선택 관련 버튼들
        self.select_all_priority_button = QPushButton("☑️ 전체 선택")
        self.select_all_priority_button.clicked.connect(self.select_all_priority_files)
        list_header_layout.addWidget(self.select_all_priority_button)
        
        self.deselect_all_priority_button = QPushButton("☐ 전체 해제")
        self.deselect_all_priority_button.clicked.connect(self.deselect_all_priority_files)
        list_header_layout.addWidget(self.deselect_all_priority_button)
        
        self.delete_selected_priority_button = QPushButton("🗑️ 선택 삭제")
        self.delete_selected_priority_button.clicked.connect(self.delete_selected_priority_files)
        self.delete_selected_priority_button.setStyleSheet("background-color: #ff6b6b; color: white; font-weight: bold;")
        self.delete_selected_priority_button.setEnabled(False)
        list_header_layout.addWidget(self.delete_selected_priority_button)
        
        priority_list_layout.addLayout(list_header_layout)
        
        # 트리 위젯
        self.priority_tree = QTreeWidget()
        self.priority_tree.setHeaderLabels(["선택", "순위", "사용자", "파일명", "크기", "복합점수", "삭제우선도"])
        self.priority_tree.itemDoubleClicked.connect(self.play_video_from_priority_list)
        self.priority_tree.itemChanged.connect(self.on_priority_item_selection_changed)
        priority_list_layout.addWidget(self.priority_tree)
        
        layout.addLayout(priority_list_layout)
        
        # 선택된 파일 통계
        self.selected_priority_stats_text = QTextEdit()
        self.selected_priority_stats_text.setMaximumHeight(80)
        self.selected_priority_stats_text.setReadOnly(True)
        self.selected_priority_stats_text.setStyleSheet("background-color: #e8f4fd; border: 1px solid #3498db;")
        layout.addWidget(self.selected_priority_stats_text)
        
        # 전체 통계 표시
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
        target_gb = suggestions.get('target_gb', 0)
        achievement_rate = suggestions.get('achievement_rate', 0)
        
        # 목표 달성률에 따른 상태 아이콘
        if achievement_rate >= 95:
            status_icon = "✅"
            status_text = "목표 달성!"
        elif achievement_rate >= 80:
            status_icon = "🟢"
            status_text = "목표 근접"
        elif achievement_rate >= 50:
            status_icon = "🟡"
            status_text = "부분 달성"
        else:
            status_icon = "🔴"
            status_text = "목표 부족"
        
        analysis_text = f"""🧠 지능형 분석 결과

📁 전체 파일: {stats['total_files']:,}개
🗑️ 삭제 추천: {stats['suggested_files']:,}개
💾 절약 예상: {stats['suggested_savings_gb']:.2f} GB

🎯 목표 용량: {target_gb:.1f} GB
{status_icon} 달성률: {achievement_rate:.1f}% ({status_text})

📋 삭제 기준: {suggestions['criteria']}
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
                
                # 체크박스 컬럼 (0번)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setText(0, "")
                
                # 기존 컬럼들 (1번부터)
                item.setText(1, str(i + 1))
                item.setText(2, file_data['name'])
                item.setText(3, self.format_file_size(file_data['size']))
                item.setText(4, f"{file_data['composite_score']:.3f}")
                item.setText(5, f"{file_data['file_score']:.3f}")
                item.setText(6, f"{file_data['rating_score']:.3f}")
                
                # 품질 라벨 (극단적 기준)
                if file_data['composite_score'] >= 0.8:
                    quality = "고품질"
                    item.setBackground(7, QColor(200, 255, 200))
                elif file_data['composite_score'] >= 0.2:
                    quality = "중품질"
                    item.setBackground(7, QColor(255, 255, 200))
                else:
                    quality = "저품질"
                    item.setBackground(7, QColor(255, 150, 150))
                
                item.setText(7, quality)
                
                # 파일 데이터를 아이템에 저장 (삭제시 사용)
                file_data_with_user = {
                    'name': file_data['name'],
                    'size': file_data['size'],
                    'composite_score': file_data['composite_score'],
                    'username': username
                }
                item.setData(0, Qt.UserRole, file_data_with_user)
            
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
                
                # 체크박스 컬럼 (0번)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Unchecked)
                item.setText(0, "")
                
                # 기존 컬럼들 (1번부터)
                item.setText(1, str(i + 1))
                item.setText(2, file_data['username'])
                item.setText(3, file_data['name'])
                item.setText(4, self.format_file_size(file_data['size']))
                item.setText(5, f"{file_data['composite_score']:.3f}")
                
                # 삭제 우선도 계산 (극단적 기준)
                if file_data['composite_score'] <= 0.1:
                    priority = "최고"
                    item.setBackground(6, QColor(255, 100, 100))
                elif file_data['composite_score'] <= 0.2:
                    priority = "매우 높음"
                    item.setBackground(6, QColor(255, 150, 150))
                elif file_data['composite_score'] <= 0.3:
                    priority = "높음"
                    item.setBackground(6, QColor(255, 200, 200))
                elif file_data['composite_score'] <= 0.5:
                    priority = "보통"
                    item.setBackground(6, QColor(255, 255, 200))
                elif file_data['composite_score'] <= 0.7:
                    priority = "낮음"
                    item.setBackground(6, QColor(200, 255, 200))
                else:
                    priority = "매우 낮음"
                    item.setBackground(6, QColor(150, 255, 150))
                
                item.setText(6, priority)
                
                # 파일 데이터를 아이템에 저장 (삭제시 사용)
                item.setData(0, Qt.UserRole, file_data)
            
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
        target_gb = self.analysis_result['suggestions'].get('target_gb', 0)
        achievement_rate = self.analysis_result['suggestions'].get('achievement_rate', 0)
        
        # 목표 달성률 표시
        if achievement_rate >= 95:
            achievement_text = f"✅ 목표 달성률: {achievement_rate:.1f}% (완벽!)"
        elif achievement_rate >= 80:
            achievement_text = f"🟢 목표 달성률: {achievement_rate:.1f}% (양호)"
        elif achievement_rate >= 50:
            achievement_text = f"🟡 목표 달성률: {achievement_rate:.1f}% (부분적)"
        else:
            achievement_text = f"🔴 목표 달성률: {achievement_rate:.1f}% (부족)"
        
        reply = QMessageBox.question(
            self, "지능형 정리 확인",
            f"🧠 지능형 분석 결과를 바탕으로 {file_count}개 파일을 삭제하시겠습니까?\n\n"
            f"🎯 목표 용량: {target_gb:.1f} GB\n"
            f"💾 절약 예상: {savings_gb:.2f} GB\n"
            f"{achievement_text}\n\n"
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
                        f"💾 절약된 용량: {result['deleted_size_gb']:.2f} GB\n\n"
                        f"🔄 화면이 자동으로 새로고침됩니다."
                    )
                    
                    # 🔥 중요: 메인 GUI도 자동 새로고침
                    self._refresh_main_gui_after_cleanup()
                    
                    # 분석 결과 초기화
                    self.analysis_result = None
                    self.execute_button.setEnabled(False)
                    self.analysis_text.clear()
                    self.suggested_files_tree.clear()
                    self.strategy_tree.clear()
                    
                    # 지능형 다이얼로그 전체 새로고침
                    self.refresh_analysis()
                else:
                    QMessageBox.warning(self, "정리 실패", "정리 중 오류가 발생했습니다.")
                    
            except Exception as e:
                logger.error(f"정리 실행 오류: {e}")
                QMessageBox.critical(self, "실행 오류", f"정리 실행 중 오류가 발생했습니다:\n{e}")
    
    def _refresh_main_gui_after_cleanup(self):
        """정리 완료 후 메인 GUI 새로고침"""
        try:
            # 메인 창의 파일 목록 새로고침
            if self.parent() and hasattr(self.parent(), 'refresh_file_list'):
                self.parent().refresh_file_list()
                logger.info("🖥️ 메인 GUI 파일 목록 새로고침 완료")
            elif self.parent() and hasattr(self.parent(), 'update_tree_display'):
                # MainWindow의 트리 디스플레이 업데이트
                self.parent().update_tree_display()
                logger.info("🖥️ 메인 GUI 트리 디스플레이 업데이트 완료")
            else:
                logger.warning("⚠️ 메인 GUI 새로고침 메서드를 찾을 수 없음")
        except Exception as e:
            logger.error(f"메인 GUI 새로고침 오류: {e}")
    
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
        
        # 선택 통계 텍스트들도 초기화
        self.selected_priority_stats_text.clear()
        self.selected_user_files_stats_text.clear()
        
        # 선택 삭제 버튼들 비활성화
        self.delete_selected_priority_button.setEnabled(False)
        self.delete_selected_user_files_button.setEnabled(False)
        
        # 보호 목록 관련도 새로고침
        try:
            self.load_protected_files_display()
            self.update_protect_user_combo()
        except AttributeError:
            # 보호 목록 탭이 아직 생성되지 않은 경우
            pass
        
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
    
    def create_protected_files_tab(self):
        """보호 목록 관리 탭"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 상단 설명
        info_label = QLabel("🛡️ 보호된 파일 관리 - 자동삭제에서 제외된 파일들")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(info_label)
        
        # 분할기
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 왼쪽: 보호된 파일 목록
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 통계 정보
        self.protected_stats_label = QLabel("📊 보호된 파일: 0개")
        self.protected_stats_label.setFont(QFont("Arial", 10, QFont.Bold))
        left_layout.addWidget(self.protected_stats_label)
        
        # 보호된 파일 테이블
        self.protected_files_table = QTableWidget()
        self.protected_files_table.setColumnCount(4)
        self.protected_files_table.setHorizontalHeaderLabels(["사용자", "파일명", "크기", "보호 일시"])
        
        # 테이블 열 너비 설정
        header = self.protected_files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # 테이블 스타일 설정
        self.protected_files_table.setAlternatingRowColors(True)
        self.protected_files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.protected_files_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # 더블클릭으로 영상 재생
        self.protected_files_table.itemDoubleClicked.connect(self.play_video_from_protected_table)
        
        left_layout.addWidget(self.protected_files_table)
        
        # 보호 목록 관리 버튼
        protected_button_layout = QHBoxLayout()
        
        self.load_protected_button = QPushButton("🔄 목록 새로고침")
        self.load_protected_button.clicked.connect(self.load_protected_files_display)
        protected_button_layout.addWidget(self.load_protected_button)
        
        self.unprotect_button = QPushButton("🗑️ 보호 해제")
        self.unprotect_button.clicked.connect(self.unprotect_selected_file)
        protected_button_layout.addWidget(self.unprotect_button)
        
        self.clear_all_protected_button = QPushButton("🧹 전체 보호 해제")
        self.clear_all_protected_button.clicked.connect(self.clear_all_protected_files)
        self.clear_all_protected_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        protected_button_layout.addWidget(self.clear_all_protected_button)
        
        protected_button_layout.addStretch()
        left_layout.addLayout(protected_button_layout)
        
        splitter.addWidget(left_widget)
        
        # 오른쪽: 수동 보호 추가
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("➕ 수동 보호 추가"))
        
        # 파일 검색 섹션
        search_group = QGroupBox("🔍 파일 검색")
        search_layout = QVBoxLayout(search_group)
        
        # 사용자 선택
        user_search_layout = QHBoxLayout()
        user_search_layout.addWidget(QLabel("사용자:"))
        self.protect_user_combo = QComboBox()
        self.protect_user_combo.setMinimumWidth(150)
        self.protect_user_combo.currentTextChanged.connect(self.update_user_files_for_protection)
        user_search_layout.addWidget(self.protect_user_combo)
        user_search_layout.addStretch()
        search_layout.addLayout(user_search_layout)
        
        # 파일 검색
        file_search_layout = QHBoxLayout()
        file_search_layout.addWidget(QLabel("파일명:"))
        self.file_search_input = QLineEdit()
        self.file_search_input.setPlaceholderText("파일명 검색...")
        self.file_search_input.textChanged.connect(self.filter_files_for_protection)
        file_search_layout.addWidget(self.file_search_input)
        search_layout.addLayout(file_search_layout)
        
        right_layout.addWidget(search_group)
        
        # 파일 목록 (보호 추가용)
        right_layout.addWidget(QLabel("📁 파일 목록 (더블클릭: 보호 추가)"))
        self.files_for_protection_table = QTableWidget()
        self.files_for_protection_table.setColumnCount(3)
        self.files_for_protection_table.setHorizontalHeaderLabels(["파일명", "크기", "복합점수"])
        
        # 테이블 열 너비 설정
        header2 = self.files_for_protection_table.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.Stretch)
        header2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # 더블클릭으로 보호 추가
        self.files_for_protection_table.itemDoubleClicked.connect(self.add_file_to_protection)
        
        right_layout.addWidget(self.files_for_protection_table)
        
        # 보호 추가 버튼
        add_protect_layout = QHBoxLayout()
        
        self.add_protect_button = QPushButton("🛡️ 선택 파일 보호 추가")
        self.add_protect_button.clicked.connect(self.add_file_to_protection)
        add_protect_layout.addWidget(self.add_protect_button)
        
        right_layout.addLayout(add_protect_layout)
        
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        
        # 탭 추가
        self.tab_widget.addTab(tab, "🛡️ 보호 목록")
        
        # 초기 데이터 로드
        self.load_protected_files_display()
        self.update_protect_user_combo()
    
    def load_protected_files_display(self):
        """보호된 파일 목록을 테이블에 표시"""
        try:
            protected_data = self.capacity_finder.intelligent_system.get_protected_files_list()
            protected_files = protected_data['protected_files']
            
            # 통계 업데이트
            self.protected_stats_label.setText(f"📊 보호된 파일: {len(protected_files)}개")
            
            # 테이블 설정
            self.protected_files_table.setRowCount(len(protected_files))
            
            # 현재 분석된 파일 데이터에서 추가 정보 가져오기
            for row, filename in enumerate(protected_files):
                # 파일명으로 사용자와 크기 찾기
                username, file_size = self.find_file_info(filename)
                
                # 파일명
                filename_item = QTableWidgetItem(filename)
                filename_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.protected_files_table.setItem(row, 1, filename_item)
                
                # 사용자명
                user_item = QTableWidgetItem(username or "알 수 없음")
                user_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.protected_files_table.setItem(row, 0, user_item)
                
                # 크기
                size_text = self.format_file_size(file_size) if file_size else "알 수 없음"
                size_item = QTableWidgetItem(size_text)
                size_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.protected_files_table.setItem(row, 2, size_item)
                
                # 보호 일시 (현재는 고정값, 나중에 개선 가능)
                protect_date = "수동 보호"
                date_item = QTableWidgetItem(protect_date)
                date_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.protected_files_table.setItem(row, 3, date_item)
                
                # 보호된 파일 색상 표시
                for col in range(4):
                    if self.protected_files_table.item(row, col):
                        self.protected_files_table.item(row, col).setBackground(QColor(200, 255, 200))
            
            logger.info(f"🛡️ 보호된 파일 목록 표시 완료: {len(protected_files)}개")
            
        except Exception as e:
            logger.error(f"보호된 파일 목록 표시 오류: {e}")
    
    def find_file_info(self, filename):
        """파일명으로 사용자와 크기 정보 찾기"""
        try:
            for username, user_data in self.capacity_finder.dic_files.items():
                for file_info in user_data['files']:
                    if file_info['name'] == filename:
                        return username, file_info['size']
            return None, None
        except Exception as e:
            logger.error(f"파일 정보 찾기 오류: {e}")
            return None, None
    
    def update_protect_user_combo(self):
        """보호 추가용 사용자 콤보박스 업데이트"""
        self.protect_user_combo.clear()
        if self.capacity_finder.dic_files:
            users = sorted(self.capacity_finder.dic_files.keys())
            self.protect_user_combo.addItems(users)
    
    def update_user_files_for_protection(self):
        """선택된 사용자의 파일 목록 업데이트"""
        username = self.protect_user_combo.currentText()
        if not username or username not in self.capacity_finder.dic_files:
            self.files_for_protection_table.setRowCount(0)
            return
        
        try:
            user_data = self.capacity_finder.dic_files[username]
            files = user_data['files']
            
            # 보호되지 않은 파일만 표시
            unprotected_files = [f for f in files if not self.capacity_finder.intelligent_system.is_file_protected(f['name'])]
            
            self.files_for_protection_table.setRowCount(len(unprotected_files))
            
            for row, file_info in enumerate(unprotected_files):
                # 파일명
                filename_item = QTableWidgetItem(file_info['name'])
                filename_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.files_for_protection_table.setItem(row, 0, filename_item)
                
                # 크기
                size_item = QTableWidgetItem(self.format_file_size(file_info['size']))
                size_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.files_for_protection_table.setItem(row, 1, size_item)
                
                # 복합점수
                score_data = self.capacity_finder.intelligent_system.calculate_composite_score(username, file_info, files)
                score_item = QTableWidgetItem(f"{score_data['composite_score']:.3f}")
                score_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.files_for_protection_table.setItem(row, 2, score_item)
                
                # 점수에 따른 색상
                if score_data['composite_score'] <= 0.25:
                    score_item.setBackground(QColor(255, 200, 200))  # 삭제 위험
                elif score_data['composite_score'] >= 0.7:
                    score_item.setBackground(QColor(200, 255, 200))  # 안전
            
        except Exception as e:
            logger.error(f"사용자 파일 목록 업데이트 오류: {e}")
    
    def filter_files_for_protection(self):
        """파일명 필터링"""
        search_text = self.file_search_input.text().lower()
        
        for row in range(self.files_for_protection_table.rowCount()):
            item = self.files_for_protection_table.item(row, 0)  # 파일명
            if item:
                filename = item.text().lower()
                should_show = search_text in filename
                self.files_for_protection_table.setRowHidden(row, not should_show)
    
    def add_file_to_protection(self):
        """선택된 파일을 보호 목록에 추가"""
        current_row = self.files_for_protection_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "선택 오류", "보호할 파일을 선택해주세요.")
            return
        
        filename_item = self.files_for_protection_table.item(current_row, 0)
        if not filename_item:
            return
        
        filename = filename_item.text()
        
        # 확인 대화상자
        reply = QMessageBox.question(
            self, "보호 추가 확인",
            f"'{filename}'을 보호 목록에 추가하시겠습니까?\n\n"
            "보호된 파일은 자동삭제 추천에서 제외됩니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.capacity_finder.intelligent_system.add_to_protected_files(filename):
                    QMessageBox.information(self, "보호 추가 완료", f"'{filename}'이 보호 목록에 추가되었습니다.")
                    
                    # 화면 새로고침
                    self.load_protected_files_display()
                    self.update_user_files_for_protection()
                    
                    # 다른 탭의 분석 결과도 새로고침
                    self.refresh_analysis_after_protection_change()
                else:
                    QMessageBox.information(self, "이미 보호됨", "이미 보호된 파일입니다.")
                    
            except Exception as e:
                logger.error(f"보호 추가 오류: {e}")
                QMessageBox.critical(self, "오류", f"보호 추가 중 오류가 발생했습니다:\n{e}")
    
    def unprotect_selected_file(self):
        """선택된 파일의 보호 해제"""
        current_row = self.protected_files_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "선택 오류", "보호 해제할 파일을 선택해주세요.")
            return
        
        filename_item = self.protected_files_table.item(current_row, 1)  # 파일명은 1번 컬럼
        if not filename_item:
            return
        
        filename = filename_item.text()
        
        # 확인 대화상자
        reply = QMessageBox.question(
            self, "보호 해제 확인",
            f"'{filename}'의 보호를 해제하시겠습니까?\n\n"
            "보호 해제된 파일은 다시 자동삭제 추천에 포함될 수 있습니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.capacity_finder.intelligent_system.remove_from_protected_files(filename):
                    QMessageBox.information(self, "보호 해제 완료", f"'{filename}'의 보호가 해제되었습니다.")
                    
                    # 화면 새로고침
                    self.load_protected_files_display()
                    self.update_user_files_for_protection()
                    
                    # 다른 탭의 분석 결과도 새로고침
                    self.refresh_analysis_after_protection_change()
                else:
                    QMessageBox.information(self, "보호되지 않음", "보호되지 않은 파일입니다.")
                    
            except Exception as e:
                logger.error(f"보호 해제 오류: {e}")
                QMessageBox.critical(self, "오류", f"보호 해제 중 오류가 발생했습니다:\n{e}")
    
    def clear_all_protected_files(self):
        """모든 보호된 파일 해제"""
        if not self.capacity_finder.intelligent_system.protected_files:
            QMessageBox.information(self, "보호 목록 없음", "보호된 파일이 없습니다.")
            return
        
        protected_count = len(self.capacity_finder.intelligent_system.protected_files)
        
        reply = QMessageBox.question(
            self, "전체 보호 해제 확인",
            f"모든 보호된 파일({protected_count}개)의 보호를 해제하시겠습니까?\n\n"
            "⚠️ 이 작업은 되돌릴 수 없습니다!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.capacity_finder.intelligent_system.protected_files.clear()
                self.capacity_finder.intelligent_system.save_protected_files()
                
                QMessageBox.information(self, "전체 보호 해제 완료", f"{protected_count}개 파일의 보호가 해제되었습니다.")
                
                # 화면 새로고침
                self.load_protected_files_display()
                self.update_user_files_for_protection()
                
                # 다른 탭의 분석 결과도 새로고침
                self.refresh_analysis_after_protection_change()
                
            except Exception as e:
                logger.error(f"전체 보호 해제 오류: {e}")
                QMessageBox.critical(self, "오류", f"전체 보호 해제 중 오류가 발생했습니다:\n{e}")
    
    def play_video_from_protected_table(self, item):
        """보호된 파일 테이블에서 영상 재생"""
        row = item.row()
        filename_item = self.protected_files_table.item(row, 1)  # 파일명은 1번 컬럼
        if filename_item:
            filename = filename_item.text()
            self.play_video(filename)
    
    def refresh_analysis_after_protection_change(self):
        """보호 목록 변경 후 분석 결과 새로고침"""
        try:
            # 현재 활성 탭 확인
            current_tab = self.tab_widget.currentIndex()
            
            if current_tab == 0:  # 자동 삭제 추천 탭
                if self.analysis_result:
                    # 자동으로 재분석
                    target_gb = self.target_savings_spin.value()
                    self.analysis_result = self.capacity_finder.get_intelligent_deletion_analysis(target_gb)
                    self.display_analysis_result()
                    self.execute_button.setEnabled(True)
                    logger.info("🔄 자동 삭제 추천 탭 보호 변경 후 업데이트됨")
                    
            elif current_tab == 2:  # 우선순위 리스트 탭
                if self.priority_tree.topLevelItemCount() > 0:
                    # 우선순위 리스트가 있으면 재생성
                    self.generate_priority_list()
                    logger.info("🔄 우선순위 리스트 탭 보호 변경 후 업데이트됨")
                    
        except Exception as e:
            logger.error(f"보호 변경 후 새로고침 오류: {e}")
    
    # === 🎬 영상 재생 기능 ===
    
    def show_suggested_files_context_menu(self, position):
        """추천 파일 리스트 우클릭 메뉴 표시"""
        item = self.suggested_files_tree.itemAt(position)
        if not item:
            return
        
        # 메뉴 생성
        from PyQt5.QtWidgets import QMenu, QAction
        context_menu = QMenu(self)
        
        # 보호 추가 액션
        protect_action = QAction("🛡️ 보호 목록에 추가", self)
        protect_action.triggered.connect(lambda: self.add_suggested_file_to_protection(item))
        context_menu.addAction(protect_action)
        
        # 구분선
        context_menu.addSeparator()
        
        # 영상 재생 액션
        play_action = QAction("🎬 영상 재생", self)
        play_action.triggered.connect(lambda: self.play_video_from_suggested_files(item))
        context_menu.addAction(play_action)
        
        # 메뉴 표시
        context_menu.exec_(self.suggested_files_tree.mapToGlobal(position))
    
    def add_suggested_file_to_protection(self, item):
        """추천 파일을 보호 목록에 추가"""
        if not item:
            return
        
        # 파일명 가져오기 (1번 컬럼)
        filename = item.text(1)
        username = item.text(0)
        
        if not filename:
            return
        
        # 확인 대화상자
        reply = QMessageBox.question(
            self, "보호 추가 확인",
            f"사용자 '{username}'의 파일\n'{filename}'을\n보호 목록에 추가하시겠습니까?\n\n"
            "🛡️ 보호된 파일은 자동삭제 추천에서 제외되며,\n"
            "🔄 다음 분석부터 추천 리스트에 나타나지 않습니다.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.capacity_finder.intelligent_system.add_to_protected_files(filename):
                    QMessageBox.information(
                        self, "보호 추가 완료", 
                        f"'{filename}'이 보호 목록에 추가되었습니다.\n\n"
                        "✨ 즉시 분석 결과가 업데이트됩니다."
                    )
                    
                    # 즉시 분석 결과 새로고침
                    target_gb = self.target_savings_spin.value()
                    self.analysis_result = self.capacity_finder.get_intelligent_deletion_analysis(target_gb)
                    self.display_analysis_result()
                    self.execute_button.setEnabled(True)
                    
                    # 5번째 탭의 보호 목록도 새로고침
                    self.load_protected_files_display()
                    
                    logger.info(f"🛡️ 추천 파일에서 보호 추가: {filename}")
                else:
                    QMessageBox.information(self, "이미 보호됨", "이미 보호된 파일입니다.")
                    
            except Exception as e:
                logger.error(f"추천 파일 보호 추가 오류: {e}")
                QMessageBox.critical(self, "오류", f"보호 추가 중 오류가 발생했습니다:\n{e}")
    
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
        filename = self.user_files_tree.topLevelItem(row).text(2)  # 파일명은 2번 컬럼 (체크박스 추가로 인해 변경)
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
    
    # === 우선순위 리스트 선택 관련 메서드들 ===
    
    def select_all_priority_files(self):
        """우선순위 리스트 전체 선택"""
        for i in range(self.priority_tree.topLevelItemCount()):
            item = self.priority_tree.topLevelItem(i)
            item.setCheckState(0, Qt.Checked)
        self.update_selected_priority_stats()
        logger.info("📋 우선순위 리스트 전체 선택")
    
    def deselect_all_priority_files(self):
        """우선순위 리스트 전체 해제"""
        for i in range(self.priority_tree.topLevelItemCount()):
            item = self.priority_tree.topLevelItem(i)
            item.setCheckState(0, Qt.Unchecked)
        self.update_selected_priority_stats()
        logger.info("📋 우선순위 리스트 전체 해제")
    
    def on_priority_item_selection_changed(self, item, column):
        """우선순위 아이템 선택 상태 변경시"""
        if column == 0:  # 체크박스 컬럼
            self.update_selected_priority_stats()
    
    def update_selected_priority_stats(self):
        """선택된 우선순위 파일 통계 업데이트"""
        selected_files = []
        total_size = 0
        user_stats = {}
        
        for i in range(self.priority_tree.topLevelItemCount()):
            item = self.priority_tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                file_data = item.data(0, Qt.UserRole)
                if file_data:
                    selected_files.append(file_data)
                    total_size += file_data['size']
                    
                    username = file_data['username']
                    if username not in user_stats:
                        user_stats[username] = {'count': 0, 'size': 0}
                    user_stats[username]['count'] += 1
                    user_stats[username]['size'] += file_data['size']
        
        # 선택 삭제 버튼 활성화/비활성화
        self.delete_selected_priority_button.setEnabled(len(selected_files) > 0)
        
        # 통계 텍스트 업데이트
        if selected_files:
            stats_text = f"""✅ 선택된 파일 통계

🗑️ 선택된 파일: {len(selected_files)}개
💾 절약 예상: {self.format_file_size(total_size)}

👥 사용자별 선택:
"""
            for username, stats in user_stats.items():
                stats_text += f"• {username}: {stats['count']}개 ({self.format_file_size(stats['size'])})\n"
        else:
            stats_text = "📝 파일을 선택하면 통계가 여기에 표시됩니다."
        
        self.selected_priority_stats_text.setText(stats_text)
    
    def delete_selected_priority_files(self):
        """선택된 우선순위 파일들 삭제"""
        selected_files = []
        
        for i in range(self.priority_tree.topLevelItemCount()):
            item = self.priority_tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                file_data = item.data(0, Qt.UserRole)
                if file_data:
                    selected_files.append(file_data)
        
        if not selected_files:
            QMessageBox.warning(self, "선택 없음", "삭제할 파일을 선택해주세요.")
            return
        
        # 확인 다이얼로그
        total_size = sum(f['size'] for f in selected_files)
        user_stats = {}
        for file_data in selected_files:
            username = file_data['username']
            if username not in user_stats:
                user_stats[username] = {'count': 0, 'size': 0}
            user_stats[username]['count'] += 1
            user_stats[username]['size'] += file_data['size']
        
        user_summary = "\n".join([f"• {username}: {stats['count']}개 ({self.format_file_size(stats['size'])})" 
                                 for username, stats in user_stats.items()])
        
        reply = QMessageBox.question(
            self, "선택 파일 삭제 확인",
            f"📋 선택된 {len(selected_files)}개 파일을 삭제하시겠습니까?\n\n"
            f"💾 절약 예상: {self.format_file_size(total_size)}\n\n"
            f"👥 사용자별 삭제:\n{user_summary}\n\n"
            f"⚠️ 이 작업은 되돌릴 수 없습니다!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 삭제 실행
                deleted_files = []
                deleted_size = 0
                
                for file_data in selected_files:
                    file_path = os.path.join(self.capacity_finder.current_path, file_data['name'])
                    
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            deleted_files.append(file_data)
                            deleted_size += file_data['size']
                            logger.debug(f"선택 삭제 완료: {file_data['name']}")
                        else:
                            logger.warning(f"파일을 찾을 수 없음: {file_path}")
                    except Exception as e:
                        logger.error(f"파일 삭제 오류: {file_path}, 에러: {e}")
                
                # 🔥 중요: 삭제된 파일들을 메모리에서도 제거
                self.capacity_finder._remove_deleted_files_from_memory(deleted_files)
                
                # 결과 메시지
                deleted_size_gb = deleted_size / 1024
                QMessageBox.information(
                    self, "선택 삭제 완료",
                    f"✅ 선택된 파일 삭제가 완료되었습니다!\n\n"
                    f"🗑️ 삭제된 파일: {len(deleted_files)}개\n"
                    f"💾 절약된 용량: {deleted_size_gb:.2f} GB\n\n"
                    f"🔄 화면이 자동으로 새로고침됩니다."
                )
                
                # 메인 GUI 새로고침
                self._refresh_main_gui_after_cleanup()
                
                # 우선순위 리스트 새로고침
                self.generate_priority_list()
                
                logger.info(f"🎯 선택 삭제 완료: {len(deleted_files)}개 파일, {deleted_size_gb:.2f}GB 절약")
                
            except Exception as e:
                logger.error(f"선택 삭제 실행 오류: {e}")
                QMessageBox.critical(self, "삭제 오류", f"선택 파일 삭제 중 오류가 발생했습니다:\n{e}")
    
    # === 사용자별 분석 탭 선택 관련 메서드들 ===
    
    def select_all_user_files(self):
        """사용자 파일 리스트 전체 선택"""
        for i in range(self.user_files_tree.topLevelItemCount()):
            item = self.user_files_tree.topLevelItem(i)
            item.setCheckState(0, Qt.Checked)
        self.update_selected_user_files_stats()
        logger.info("👤 사용자 파일 리스트 전체 선택")
    
    def deselect_all_user_files(self):
        """사용자 파일 리스트 전체 해제"""
        for i in range(self.user_files_tree.topLevelItemCount()):
            item = self.user_files_tree.topLevelItem(i)
            item.setCheckState(0, Qt.Unchecked)
        self.update_selected_user_files_stats()
        logger.info("👤 사용자 파일 리스트 전체 해제")
    
    def on_user_file_selection_changed(self, item, column):
        """사용자 파일 아이템 선택 상태 변경시"""
        if column == 0:  # 체크박스 컬럼
            self.update_selected_user_files_stats()
    
    def update_selected_user_files_stats(self):
        """선택된 사용자 파일 통계 업데이트"""
        selected_files = []
        total_size = 0
        
        for i in range(self.user_files_tree.topLevelItemCount()):
            item = self.user_files_tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                file_data = item.data(0, Qt.UserRole)
                if file_data:
                    selected_files.append(file_data)
                    total_size += file_data['size']
        
        # 선택 삭제 버튼 활성화/비활성화
        self.delete_selected_user_files_button.setEnabled(len(selected_files) > 0)
        
        # 통계 텍스트 업데이트
        if selected_files:
            username = selected_files[0]['username'] if selected_files else "알 수 없음"
            stats_text = f"""✅ 선택된 파일 통계 ({username})

🗑️ 선택된 파일: {len(selected_files)}개
💾 절약 예상: {self.format_file_size(total_size)}

📊 점수 분포:
"""
            # 점수별 분포 계산
            high_quality = len([f for f in selected_files if f['composite_score'] >= 0.7])
            medium_quality = len([f for f in selected_files if 0.3 <= f['composite_score'] < 0.7])
            low_quality = len([f for f in selected_files if f['composite_score'] < 0.3])
            
            stats_text += f"• 고품질 (0.7+): {high_quality}개\n"
            stats_text += f"• 중품질 (0.3-0.7): {medium_quality}개\n"
            stats_text += f"• 저품질 (0.3-): {low_quality}개"
        else:
            stats_text = "📝 파일을 선택하면 통계가 여기에 표시됩니다."
        
        self.selected_user_files_stats_text.setText(stats_text)
    
    def delete_selected_user_files(self):
        """선택된 사용자 파일들 삭제"""
        selected_files = []
        
        for i in range(self.user_files_tree.topLevelItemCount()):
            item = self.user_files_tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                file_data = item.data(0, Qt.UserRole)
                if file_data:
                    selected_files.append(file_data)
        
        if not selected_files:
            QMessageBox.warning(self, "선택 없음", "삭제할 파일을 선택해주세요.")
            return
        
        # 확인 다이얼로그
        total_size = sum(f['size'] for f in selected_files)
        username = selected_files[0]['username'] if selected_files else "알 수 없음"
        
        # 점수별 분포
        high_quality = len([f for f in selected_files if f['composite_score'] >= 0.7])
        medium_quality = len([f for f in selected_files if 0.3 <= f['composite_score'] < 0.7])
        low_quality = len([f for f in selected_files if f['composite_score'] < 0.3])
        
        reply = QMessageBox.question(
            self, "선택 파일 삭제 확인",
            f"👤 사용자 '{username}'의 선택된 {len(selected_files)}개 파일을 삭제하시겠습니까?\n\n"
            f"💾 절약 예상: {self.format_file_size(total_size)}\n\n"
            f"📊 점수별 분포:\n"
            f"• 고품질 (0.7+): {high_quality}개\n"
            f"• 중품질 (0.3-0.7): {medium_quality}개\n"
            f"• 저품질 (0.3-): {low_quality}개\n\n"
            f"⚠️ 이 작업은 되돌릴 수 없습니다!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 삭제 실행
                deleted_files = []
                deleted_size = 0
                
                for file_data in selected_files:
                    file_path = os.path.join(self.capacity_finder.current_path, file_data['name'])
                    
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            deleted_files.append(file_data)
                            deleted_size += file_data['size']
                            logger.debug(f"선택 삭제 완료: {file_data['name']}")
                        else:
                            logger.warning(f"파일을 찾을 수 없음: {file_path}")
                    except Exception as e:
                        logger.error(f"파일 삭제 오류: {file_path}, 에러: {e}")
                
                # 🔥 중요: 삭제된 파일들을 메모리에서도 제거
                self.capacity_finder._remove_deleted_files_from_memory(deleted_files)
                
                # 결과 메시지
                deleted_size_gb = deleted_size / 1024
                QMessageBox.information(
                    self, "선택 삭제 완료",
                    f"✅ 선택된 파일 삭제가 완료되었습니다!\n\n"
                    f"🗑️ 삭제된 파일: {len(deleted_files)}개\n"
                    f"💾 절약된 용량: {deleted_size_gb:.2f} GB\n\n"
                    f"🔄 화면이 자동으로 새로고침됩니다."
                )
                
                # 메인 GUI 새로고침
                self._refresh_main_gui_after_cleanup()
                
                # 사용자별 분석 새로고침 (같은 사용자 재분석)
                if self.user_combo.currentText():
                    self.analyze_selected_user()
                
                logger.info(f"🎯 사용자별 선택 삭제 완료: {len(deleted_files)}개 파일, {deleted_size_gb:.2f}GB 절약")
                
            except Exception as e:
                logger.error(f"사용자별 선택 삭제 실행 오류: {e}")
                QMessageBox.critical(self, "삭제 오류", f"선택 파일 삭제 중 오류가 발생했습니다:\n{e}")