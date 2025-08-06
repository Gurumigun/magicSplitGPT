"""
프롬프트 관리 시스템
"""

import os
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger

from .config import Config


class PromptManager:
    """프롬프트 템플릿 관리 클래스"""
    
    def __init__(self, config: Config):
        """
        프롬프트 매니저 초기화
        
        Args:
            config: 설정 객체
        """
        self.config = config
        self.templates_path = Path(config.prompts.templates_path)
        self.available_strategies = config.prompts.strategies
        self._templates_cache: Dict[str, str] = {}
        
        # 템플릿 디렉토리 존재 확인
        if not self.templates_path.exists():
            logger.error(f"프롬프트 템플릿 디렉토리를 찾을 수 없습니다: {self.templates_path}")
            raise FileNotFoundError(f"템플릿 디렉토리 없음: {self.templates_path}")
    
    def load_template(self, strategy_name: str) -> Optional[str]:
        """
        프롬프트 템플릿 로드
        
        Args:
            strategy_name: 전략 이름 (magic_split_optimization, short_term_discovery 등)
            
        Returns:
            프롬프트 템플릿 내용 또는 None
        """
        if strategy_name not in self.available_strategies:
            logger.warning(f"사용할 수 없는 전략입니다: {strategy_name}")
            return None
        
        # 캐시에서 확인
        if strategy_name in self._templates_cache:
            logger.debug(f"캐시에서 템플릿 로드: {strategy_name}")
            return self._templates_cache[strategy_name]
        
        # 파일에서 로드
        template_file = self.templates_path / f"{strategy_name}.txt"
        
        try:
            with open(template_file, 'r', encoding='utf-8') as file:
                template_content = file.read()
                
            # 캐시에 저장
            self._templates_cache[strategy_name] = template_content
            logger.info(f"프롬프트 템플릿 로드 완료: {strategy_name}")
            
            return template_content
            
        except FileNotFoundError:
            logger.error(f"프롬프트 템플릿 파일을 찾을 수 없습니다: {template_file}")
            return None
        except Exception as e:
            logger.error(f"프롬프트 템플릿 로드 실패: {e}")
            return None
    
    def get_available_strategies(self) -> List[str]:
        """
        사용 가능한 전략 목록 반환
        
        Returns:
            전략 이름 리스트
        """
        return self.available_strategies.copy()
    
    def get_strategy_description(self, strategy_name: str) -> str:
        """
        전략에 대한 설명 반환
        
        Args:
            strategy_name: 전략 이름
            
        Returns:
            전략 설명
        """
        descriptions = {
            "magic_split_optimization": "매직스플릿 최적화 전략 - 종합적인 투자 분석 및 전략 수립",
            "short_term_discovery": "단기 유망 종목 발굴 - 단기간 고수익 가능 종목 선별",
            "buy_timing_diagnosis": "매수 타이밍 진단 - 현재 시점의 매수 적정성 판단",
            "hold_or_cut_decision": "손절/보유 판단 - 보유 종목의 매도/보유 결정 지원",
            "valuation_analysis": "밸류에이션 분석 - 기업 가치 평가 및 적정주가 산출"
        }
        
        return descriptions.get(strategy_name, "설명 없음")
    
    def reload_template(self, strategy_name: str) -> Optional[str]:
        """
        템플릿 파일을 다시 로드 (캐시 무시)
        
        Args:
            strategy_name: 전략 이름
            
        Returns:
            프롬프트 템플릿 내용 또는 None
        """
        # 캐시에서 제거
        if strategy_name in self._templates_cache:
            del self._templates_cache[strategy_name]
        
        logger.info(f"템플릿 다시 로드: {strategy_name}")
        return self.load_template(strategy_name)
    
    def validate_template(self, strategy_name: str) -> bool:
        """
        템플릿 파일의 유효성 검사
        
        Args:
            strategy_name: 전략 이름
            
        Returns:
            유효성 검사 결과
        """
        template_file = self.templates_path / f"{strategy_name}.txt"
        
        if not template_file.exists():
            logger.error(f"템플릿 파일이 존재하지 않습니다: {template_file}")
            return False
        
        try:
            with open(template_file, 'r', encoding='utf-8') as file:
                content = file.read()
            
            if not content.strip():
                logger.error(f"템플릿 파일이 비어있습니다: {template_file}")
                return False
            
            # 기본적인 내용 검증 (매직스플릿 관련 키워드 포함 여부)
            required_keywords = ["매직스플릿", "주식", "분석"]
            if not any(keyword in content for keyword in required_keywords):
                logger.warning(f"템플릿에 필수 키워드가 없습니다: {template_file}")
                return False
            
            logger.info(f"템플릿 유효성 검사 통과: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"템플릿 유효성 검사 실패: {e}")
            return False
    
    def validate_all_templates(self) -> Dict[str, bool]:
        """
        모든 템플릿의 유효성 검사
        
        Returns:
            각 템플릿의 유효성 검사 결과
        """
        validation_results = {}
        
        for strategy in self.available_strategies:
            validation_results[strategy] = self.validate_template(strategy)
        
        valid_count = sum(validation_results.values())
        total_count = len(validation_results)
        
        logger.info(f"템플릿 유효성 검사 완료: {valid_count}/{total_count} 통과")
        
        return validation_results
    
    def get_template_info(self, strategy_name: str) -> Dict[str, any]:
        """
        템플릿 정보 반환
        
        Args:
            strategy_name: 전략 이름
            
        Returns:
            템플릿 정보 딕셔너리
        """
        template_file = self.templates_path / f"{strategy_name}.txt"
        
        info = {
            "name": strategy_name,
            "description": self.get_strategy_description(strategy_name),
            "file_path": str(template_file),
            "exists": template_file.exists(),
            "valid": False,
            "size": 0,
            "content_preview": ""
        }
        
        if template_file.exists():
            try:
                stat = template_file.stat()
                info["size"] = stat.st_size
                info["modified_time"] = stat.st_mtime
                
                with open(template_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    info["content_preview"] = content[:200] + "..." if len(content) > 200 else content
                
                info["valid"] = self.validate_template(strategy_name)
                
            except Exception as e:
                logger.error(f"템플릿 정보 수집 실패: {e}")
        
        return info
    
    def list_template_files(self) -> List[Dict[str, any]]:
        """
        모든 템플릿 파일 정보 리스트 반환
        
        Returns:
            템플릿 파일 정보 리스트
        """
        template_files = []
        
        for strategy in self.available_strategies:
            template_info = self.get_template_info(strategy)
            template_files.append(template_info)
        
        return template_files
    
    def clear_cache(self) -> None:
        """템플릿 캐시 초기화"""
        self._templates_cache.clear()
        logger.info("프롬프트 템플릿 캐시가 초기화되었습니다")
    
    def get_cache_status(self) -> Dict[str, any]:
        """
        캐시 상태 정보 반환
        
        Returns:
            캐시 상태 정보
        """
        return {
            "cached_templates": list(self._templates_cache.keys()),
            "cache_size": len(self._templates_cache),
            "total_templates": len(self.available_strategies)
        }