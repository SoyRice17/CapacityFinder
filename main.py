#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gui import MainWindow
import sys
import os
import re
import json
from datetime import datetime
from enum import Enum
from PyQt5.QtWidgets import QApplication

class SiteType(Enum):
    """지원하는 성인 플랫폼 목록"""
    CHATURBATE = "chaturbate"
    STRIPCHAT = "stripchat"
    CAMSODA = "camsoda"
    MYFREECAMS = "myfreecams"
    CAM4 = "cam4"
    BONGACAMS = "bongacams"
    LIVEJASMIN = "livejasmin"
    FLIRT4FREE = "flirt4free"
    XHAMSTERLIVE = "xhamsterlive"
    STREAMATE = "streamate"
    CAMGIRLS = "camgirls"
    IMLIVE = "imlive"
    CAMS = "cams"
    JERKMATE = "jerkmate"
    AMATEUR = "amateur"
    
    @classmethod
    def get_all_sites(cls):
        """모든 사이트명을 리스트로 반환"""
        return [site.value for site in cls]
    
    @classmethod
    def is_valid_site(cls, site_name):
        """주어진 문자열이 유효한 사이트명인지 확인"""
        return site_name.lower() in cls.get_all_sites()

class PathHistory:
    """경로 기록을 관리하는 클래스"""
    def __init__(self, config_file="path_history.json"):
        self.config_file = config_file
        self.history = self.load_history()
    
    def load_history(self):
        """JSON 파일에서 경로 기록을 로드"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"경로 기록 로드됨: {len(data.get('paths', []))}개 경로")
                    return data
            else:
                print("경로 기록 파일이 없음, 새로 생성")
                return {"paths": [], "last_updated": None}
        except Exception as e:
            print(f"경로 기록 로드 오류: {e}")
            return {"paths": [], "last_updated": None}
    
    def save_history(self):
        """현재 경로 기록을 JSON 파일에 저장"""
        try:
            self.history["last_updated"] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            print(f"경로 기록 저장됨: {self.config_file}")
        except Exception as e:
            print(f"경로 기록 저장 오류: {e}")
    
    def add_path(self, path):
        """새로운 경로를 기록에 추가"""
        if not path or not os.path.exists(path):
            return False
        
        # 절대 경로로 변환
        abs_path = os.path.abspath(path)
        
        # 기존 경로 찾기
        existing_path = None
        for item in self.history["paths"]:
            if item["path"] == abs_path:
                existing_path = item
                break
        
        if existing_path:
            # 기존 경로 업데이트 (마지막 사용 시간, 사용 횟수 증가)
            existing_path["last_used"] = datetime.now().isoformat()
            existing_path["usage_count"] = existing_path.get("usage_count", 0) + 1
            print(f"기존 경로 업데이트: {abs_path} (사용 횟수: {existing_path['usage_count']})")
        else:
            # 새 경로 추가
            new_path_info = {
                "path": abs_path,
                "display_name": os.path.basename(abs_path) or abs_path,
                "first_used": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "usage_count": 1
            }
            self.history["paths"].append(new_path_info)
            print(f"새 경로 추가: {abs_path}")
        
        # 사용 횟수와 최근 사용 시간 기준으로 정렬
        self.history["paths"].sort(key=lambda x: (x.get("usage_count", 0), x.get("last_used", "")), reverse=True)
        
        # 최대 20개까지만 보관
        if len(self.history["paths"]) > 20:
            self.history["paths"] = self.history["paths"][:20]
        
        self.save_history()
        return True
    
    def get_paths(self):
        """저장된 경로 목록 반환"""
        return self.history.get("paths", [])
    
    def remove_path(self, path):
        """경로를 기록에서 제거"""
        abs_path = os.path.abspath(path)
        self.history["paths"] = [item for item in self.history["paths"] if item["path"] != abs_path]
        self.save_history()
        print(f"경로 제거됨: {abs_path}")

class CapacityFinder:
    def __init__(self):
        self.current_path = None
        self.dic_files = {}  # {username: {'total_size': float, 'files': [{'name': str, 'size': float}]}}
        self.window = None  # GUI 윈도우 참조를 위해 추가
        self.path_history = PathHistory()  # 경로 기록 관리자 추가
        # 날짜 패턴 정의 (2025-06-26T15_09_46+09_00 형식)
        self.date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}[+-]\d{2}_\d{2}')
        
        # === 도구 간 간단한 네비게이션 컨텍스트 ===
        self.navigation_context = {
            'selected_user': None,        # 현재 선택된 사용자
            'source_tool': None,          # 출발점 도구
            'return_callback': None,      # 돌아갈 때 호출할 콜백
        }
        
    def format_file_size(self, size_mb):
        """파일 사이즈를 적절한 단위(MB/GB)로 포맷팅하는 함수"""
        if size_mb >= 1024:  # 1GB 이상
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"
        
    def handle_path_confirmation(self, path):
        """GUI에서 경로가 확인되었을 때 호출되는 함수"""
        print(f"메인에서 받은 경로: {path}")
        self.current_path = path
        
        # 경로를 기록에 추가 (JSON에 자동 저장)
        if self.path_history.add_path(path):
            print(f"경로가 기록에 저장됨: {path}")
        
        # 기존 데이터 초기화
        self.dic_files = {}
        
        # 파일 용량 계산
        result_dict = self.listing_files()
        
        if result_dict:
            # GUI 리스트 초기화
            self.window.clear_results()
            
            # 용량 기준으로 내림차순 정렬 (큰 것부터)
            sorted_users = sorted(result_dict.items(), key=lambda x: x[1]['total_size'], reverse=True)
            
            # 전체 파일 통계 계산
            total_files_size = sum(user_data['total_size'] for _, user_data in sorted_users)
            total_files_count = sum(len(user_data['files']) for _, user_data in sorted_users)
            formatted_total_size = self.format_file_size(total_files_size)
            
            # 결과를 GUI에 표시 (헤더를 각 열에 맞춰 표시)
            self.window.add_header_with_totals("사용자별 파일 용량 (용량 큰 순)", formatted_total_size, total_files_count)
            for username, user_data in sorted_users:
                total_size = user_data['total_size']
                file_count = len(user_data['files'])
                formatted_size = self.format_file_size(total_size)
                
                # 새로운 트리 구조로 사용자 데이터 추가
                self.window.add_user_data(username, user_data, formatted_size)
                
                print(f"사용자: {username}, 총 용량: {formatted_size}, 파일 수: {file_count}")
            
            # CapacityFinder 인스턴스를 GUI에 설정하고 모델 정리 버튼 활성화
            self.window.set_capacity_finder(self)
            self.window.update_cleanup_button_state()
        else:
            self.window.add_result_to_list("처리할 파일이 없습니다.")
            self.window.update_cleanup_button_state()
        
    def listing_files_capacity(self) -> list:
        """파일 용량을 계산하는 함수"""
        list_files = []
        if self.current_path:
            try:
                for file in os.listdir(self.current_path):
                    file_path = os.path.join(self.current_path, file)
                    # 파일인지 확인 (디렉토리 제외)
                    if os.path.isfile(file_path):
                        # 리스트에 파일명, 파일크기 저장 MB 단위
                        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        list_files.append([file, file_size_mb])
                return list_files
            except Exception as e:
                print(f"파일 목록 읽기 오류: {e}")
                return []
        else:
            print("경로가 설정되지 않았습니다.")
            return []
    
    def listing_files(self):
        """파일 목록을 가져와서 사용자별로 용량을 계산하는 함수"""
        file_list = self.listing_files_capacity()
        
        if not file_list:
            return {}
            
        for file_info in file_list:
            file_name = file_info[0]
            file_size = file_info[1]
            
            username = self.file_name_handle(file_name)
            if username:
                # 사용자별 용량 누적
                if username not in self.dic_files:
                    self.dic_files[username] = {'total_size': 0.0, 'files': []}
                self.dic_files[username]['total_size'] += file_size
                self.dic_files[username]['files'].append({'name': file_name, 'size': file_size})
            else:
                print(f"파일명 처리 불가: {file_name}")
        
        return self.dic_files

    def file_name_handle(self, file_name):
        """파일 이름을 처리해서 채널명만 반환하는 함수
        다양한 파일명 구조 지원:
        - 사이트-채널-날짜
        - 채널-사이트-날짜
        - 기타 조합
        예: instagram-john_doe-2025-06-26T15_09_46+09_00.txt -> john_doe 반환
        """
        if not file_name:
            return None
            
        try:
            # 확장자 제거
            name_without_ext = file_name.split('.')[0] if '.' in file_name else file_name
            
            # 날짜 패턴 찾기
            date_match = self.date_pattern.search(name_without_ext)
            if not date_match:
                print(f"날짜 패턴을 찾을 수 없음: {file_name}")
                return None
            
            date_part = date_match.group()
            date_start = date_match.start()
            
            # 날짜 이전 부분 추출
            before_date = name_without_ext[:date_start].rstrip('-')
            
            # '-'로 분리
            parts = before_date.split('-')
            
            if len(parts) < 2:
                print(f"파일명 구조가 올바르지 않음: {file_name}")
                return None
            
            # 사이트 찾기
            site_part = None
            channel_parts = []
            
            for i, part in enumerate(parts):
                if SiteType.is_valid_site(part):
                    site_part = part
                    # 사이트가 아닌 나머지 부분들을 채널명으로 결합
                    channel_parts = parts[:i] + parts[i+1:]
                    break
            
            if not site_part:
                print(f"알려진 사이트를 찾을 수 없음: {file_name}")
                return None
            
            if not channel_parts:
                print(f"채널명을 찾을 수 없음: {file_name}")
                return None
            
            # 채널명 결합 (여러 부분이 있을 경우 '-'로 다시 결합)
            channel_name = '-'.join(channel_parts)
            
            print(f"파일명: {file_name} -> 사이트: {site_part}, 채널: {channel_name}, 날짜: {date_part}")
            return channel_name
                    
        except Exception as e:
            print(f"파일명 처리 중 오류: {file_name}, 에러: {e}")
            return None

    def extract_date_from_filename(self, file_name):
        """파일명에서 날짜 추출"""
        try:
            date_match = self.date_pattern.search(file_name)
            if date_match:
                date_str = date_match.group()
                # 2025-06-26T15_09_46+09_00 -> datetime 변환
                file_date = datetime.fromisoformat(date_str.replace('_', ':'))
                return file_date
        except Exception as e:
            print(f"날짜 추출 오류: {file_name}, 에러: {e}")
        return None

    def select_representative_samples(self, files):
        """더 대표성 있는 샘플 선택"""
        if len(files) <= 5:
            return files  # 파일 적으면 다 보여주기
        
        samples = []
        
        # 파일들을 날짜순으로 정렬
        files_with_dates = []
        for file_info in files:
            file_date = self.extract_date_from_filename(file_info['name'])
            if file_date:
                files_with_dates.append({'file': file_info, 'date': file_date})
        
        if not files_with_dates:
            return files[:5]  # 날짜 추출 실패시 첫 5개
        
        files_with_dates.sort(key=lambda x: x['date'])
        sorted_files = [item['file'] for item in files_with_dates]
        
        # 1. 가장 최근 파일
        samples.append(sorted_files[-1])
        
        # 2. 가장 큰 파일  
        largest_file = max(files, key=lambda x: x['size'])
        if largest_file not in samples:
            samples.append(largest_file)
        
        # 3. 시간대별 분산 샘플 (처음/중간)
        if len(sorted_files) > 2:
            # 첫 기록
            if sorted_files[0] not in samples:
                samples.append(sorted_files[0])
            # 중간
            middle_file = sorted_files[len(sorted_files)//2]
            if middle_file not in samples:
                samples.append(middle_file)
        
        # 4. 남은 자리에 다른 파일들
        for file_info in files:
            if file_info not in samples and len(samples) < 5:
                samples.append(file_info)
        
        return samples[:5]  # 최대 5개

    def create_decision_list(self):
        """결정하기 쉬운 형태로 정리"""
        if not self.dic_files:
            print("분석할 데이터가 없습니다.")
            return []
        
        # 용량 큰 순으로 정렬
        sorted_models = sorted(
            self.dic_files.items(), 
            key=lambda x: x[1]['total_size'], 
            reverse=True
        )
        
        decision_list = []
        for username, data in sorted_models:
            # 대표 파일들 선택
            sample_files = self.select_representative_samples(data['files'])
            
            decision_list.append({
                'username': username,
                'total_size': data['total_size'],
                'file_count': len(data['files']),
                'sample_files': sample_files,
                'potential_savings': data['total_size']  # 삭제시 절약 용량
            })
        
        return decision_list

    def compare_user_sites(self, username):
        """특정 사용자의 사이트별 파일 비교 및 중복 제거 추천
        
        Args:
            username: 비교할 사용자명
            
        Returns:
            dict: {
                'files_to_delete': [{'name': str, 'size': float, 'site': str, 'date': str}],
                'total_savings': float,
                'username': str,
                'comparison_results': [dict]  # 비교 결과 상세
            }
        """
        if username not in self.dic_files:
            return None
        
        user_files = self.dic_files[username]['files']
        
        # 파일들을 사이트별, 날짜별로 그룹화
        date_site_groups = {}  # {date: {site: [files]}}
        
        for file_info in user_files:
            file_name = file_info['name']
            file_size = file_info['size']
            
            # 파일명에서 사이트와 날짜 추출
            site, date_str = self.extract_site_and_date(file_name)
            if not site or not date_str:
                continue
            
            if date_str not in date_site_groups:
                date_site_groups[date_str] = {}
            
            if site not in date_site_groups[date_str]:
                date_site_groups[date_str][site] = []
            
            date_site_groups[date_str][site].append({
                'name': file_name,
                'size': file_size,
                'site': site,
                'date': date_str
            })
        
        # 같은 날짜에 여러 사이트가 있는 경우 용량 비교
        files_to_delete = []
        comparison_results = []
        total_savings = 0
        
        for date_str, sites in date_site_groups.items():
            if len(sites) <= 1:
                continue  # 사이트가 하나뿐이면 비교할 필요 없음
            
            # 사이트별 총 용량 계산
            site_totals = {}
            for site, files in sites.items():
                site_totals[site] = sum(f['size'] for f in files)
            
            # 가장 큰 용량의 사이트 찾기
            max_site = max(site_totals.items(), key=lambda x: x[1])
            max_site_name = max_site[0]
            max_size = max_site[1]
            
            # 다른 사이트들의 파일을 삭제 대상으로 추가
            comparison_result = {
                'date': date_str,
                'sites': {},
                'keep_site': max_site_name,
                'delete_sites': []
            }
            
            for site, files in sites.items():
                site_total = site_totals[site]
                comparison_result['sites'][site] = {
                    'files': files,
                    'total_size': site_total,
                    'file_count': len(files)
                }
                
                if site != max_site_name:
                    # 작은 용량의 사이트 파일들을 삭제 대상에 추가
                    for file_info in files:
                        files_to_delete.append(file_info)
                        total_savings += file_info['size']
                    comparison_result['delete_sites'].append(site)
            
            comparison_results.append(comparison_result)
        
        return {
            'files_to_delete': files_to_delete,
            'total_savings': total_savings,
            'username': username,
            'comparison_results': comparison_results
        }
    
    def extract_site_and_date(self, file_name):
        """파일명에서 사이트와 날짜를 추출
        
        Args:
            file_name: 파일명
            
        Returns:
            tuple: (site, date_str) 또는 (None, None)
        """
        if not file_name:
            return None, None
            
        try:
            # 확장자 제거
            name_without_ext = file_name.split('.')[0] if '.' in file_name else file_name
            
            # 날짜 패턴 찾기
            date_match = self.date_pattern.search(name_without_ext)
            if not date_match:
                return None, None
            
            date_part = date_match.group()
            date_start = date_match.start()
            
            # 날짜 이전 부분 추출
            before_date = name_without_ext[:date_start].rstrip('-')
            
            # '-'로 분리
            parts = before_date.split('-')
            
            if len(parts) < 2:
                return None, None
            
            # 사이트 찾기
            for part in parts:
                if SiteType.is_valid_site(part):
                    # 날짜에서 시간 부분만 추출해서 날짜로 변환 (2025-06-26 형식)
                    date_only = date_part.split('T')[0] if 'T' in date_part else date_part
                    return part, date_only
            
            return None, None
                    
        except Exception as e:
            print(f"사이트/날짜 추출 중 오류: {file_name}, 에러: {e}")
            return None, None

    def get_available_users(self):
        """분석된 사용자 목록 반환"""
        if not self.dic_files:
            return []
        return list(self.dic_files.keys())

    def calculate_file_score(self, file_info, user_files):
        """파일의 메타데이터 기반 점수 계산
        
        Args:
            file_info: 개별 파일 정보
            user_files: 해당 사용자의 전체 파일 목록
            
        Returns:
            float: 0.0 ~ 1.0 사이의 점수
        """
        file_name = file_info['name']
        file_size = file_info['size']
        
        # 기본 점수 구성 요소들
        size_score = 0.0
        rarity_score = 0.0
        date_score = 0.0
        
        try:
            # 1. 파일 크기 점수 (60% 가중치) - 증가
            all_sizes = [f['size'] for f in user_files]
            if all_sizes:
                max_size = max(all_sizes)
                min_size = min(all_sizes)
                if max_size > min_size:
                    # 크기 점수를 더 관대하게 계산 (상위 30% 이상이면 0.8+ 점수)
                    normalized_score = (file_size - min_size) / (max_size - min_size)
                    # 제곱근 적용해서 중간값들도 더 높은 점수 받도록
                    size_score = min(normalized_score ** 0.5, 1.0)
                else:
                    size_score = 1.0
            
            # 2. 희귀성 점수 (25% 가중치) - 증가
            file_date = self.extract_date_from_filename(file_name)
            if file_date:
                # 같은 날짜의 파일 수가 적을수록 희귀함
                same_date_count = 0
                for f in user_files:
                    f_date = self.extract_date_from_filename(f['name'])
                    if f_date and f_date.date() == file_date.date():
                        same_date_count += 1
                
                if same_date_count <= 1:
                    rarity_score = 1.0
                elif same_date_count <= 2:
                    rarity_score = 0.9
                elif same_date_count <= 3:
                    rarity_score = 0.8
                elif same_date_count <= 5:
                    rarity_score = 0.7
                else:
                    rarity_score = 0.5
            else:
                # 날짜를 추출할 수 없는 파일은 중간 점수
                rarity_score = 0.6
            
            # 3. 날짜 점수 (15% 가중치) - 증가, 최근일수록 높은 점수
            if file_date:
                all_dates = []
                for f in user_files:
                    f_date = self.extract_date_from_filename(f['name'])
                    if f_date:
                        all_dates.append(f_date)
                
                if all_dates:
                    all_dates.sort()
                    oldest = all_dates[0]
                    newest = all_dates[-1]
                    
                    if newest > oldest:
                        total_days = (newest - oldest).days
                        file_days = (file_date - oldest).days
                        date_score = file_days / total_days if total_days > 0 else 1.0
                    else:
                        date_score = 1.0
                else:
                    date_score = 0.8
            else:
                # 날짜를 추출할 수 없는 파일은 중간 점수
                date_score = 0.5
        
        except Exception as e:
            print(f"점수 계산 오류: {file_name}, 에러: {e}")
            return 0.6  # 기본값을 0.6으로 상향
        
        # 가중 평균 계산 (시간 점수 제거, 다른 요소들 가중치 증가)
        final_score = (size_score * 0.6 + rarity_score * 0.25 + date_score * 0.15)
        
        # 추가 보너스: 매우 큰 파일에게 보너스 점수
        if all_sizes:
            size_percentile = (file_size - min(all_sizes)) / (max(all_sizes) - min(all_sizes)) if max(all_sizes) > min(all_sizes) else 1.0
            if size_percentile >= 0.9:  # 상위 10% 크기
                final_score = min(final_score + 0.1, 1.0)
            elif size_percentile >= 0.8:  # 상위 20% 크기
                final_score = min(final_score + 0.05, 1.0)
        
        return min(max(final_score, 0.0), 1.0)  # 0.0 ~ 1.0 사이로 클램핑

    def get_user_files_with_scores(self, username):
        """특정 사용자의 파일들을 점수와 함께 반환
        
        Args:
            username: 사용자명
            
        Returns:
            list: [{'name': str, 'size': float, 'score': float, 'rank': int}, ...]
        """
        if username not in self.dic_files:
            return []
        
        user_files = self.dic_files[username]['files']
        
        # 각 파일에 점수 추가
        files_with_scores = []
        for file_info in user_files:
            score = self.calculate_file_score(file_info, user_files)
            files_with_scores.append({
                'name': file_info['name'],
                'size': file_info['size'],
                'score': score,
                'rank': 0  # 나중에 설정
            })
        
        # 점수 기준으로 정렬 (높은 점수부터)
        files_with_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 순위 설정
        for i, file_info in enumerate(files_with_scores):
            file_info['rank'] = i + 1
        
        return files_with_scores

    def get_selection_candidates(self, username, top_n=50):
        """선별 후보 파일들 반환 (상위 N개)
        
        Args:
            username: 사용자명
            top_n: 후보로 선택할 파일 수
            
        Returns:
            dict: {
                'candidates': list,  # 선별 후보 파일들
                'excluded': list,    # 자동 제외된 파일들
                'total_files': int,  # 전체 파일 수
                'username': str
            }
        """
        if username not in self.dic_files:
            return None
        
        all_files = self.get_user_files_with_scores(username)
        total_files = len(all_files)
        
        # 상위 N개를 후보로 선택
        top_n = min(top_n, total_files)
        candidates = all_files[:top_n]
        excluded = all_files[top_n:]
        
        return {
            'candidates': candidates,
            'excluded': excluded,
            'total_files': total_files,
            'username': username
        }

def main():
    """메인 함수에서 GUI 애플리케이션을 실행합니다."""
    app = QApplication(sys.argv)
    
    # CapacityFinder 인스턴스 생성
    finder = CapacityFinder()
    
    # GUI 생성 시 콜백 함수와 경로 기록 전달
    finder.window = MainWindow(
        on_path_confirmed=finder.handle_path_confirmation,
        path_history=finder.path_history
    )
    finder.window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
