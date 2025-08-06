"""
설정 관리 모듈
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class WebDriverConfig:
    """웹드라이버 설정"""
    headless: bool = False
    window_size: str = "1920,1080"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    wait_timeout: int = 10
    implicit_wait: int = 3


@dataclass
class NaverFinanceConfig:
    """네이버 증권 설정"""
    base_url: str = "https://finance.naver.com"
    stock_url: str = "https://finance.naver.com/item/main.naver"
    delay_between_requests: int = 2


@dataclass
class ScreenshotConfig:
    """스크린샷 설정"""
    save_path: str = "screenshots"
    format: str = "png"
    quality: int = 95


@dataclass
class AIServiceConfig:
    """AI 서비스 설정"""
    chatgpt: Dict[str, Any] = None
    claude: Dict[str, Any] = None
    gemini: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.chatgpt is None:
            self.chatgpt = {"url": "https://chat.openai.com", "enabled": True}
        if self.claude is None:
            self.claude = {"url": "https://claude.ai", "enabled": True}
        if self.gemini is None:
            self.gemini = {"url": "https://gemini.google.com", "enabled": True}


@dataclass
class MagicSplitConfig:
    """매직스플릿 전략 설정"""
    first_buy_profit: int = 10
    additional_buy_drop: int = 15
    additional_buy_profit: int = 15
    max_buy_count: int = 20


@dataclass
class PromptsConfig:
    """프롬프트 설정"""
    templates_path: str = "prompts/templates"
    strategies: list = None
    
    def __post_init__(self):
        if self.strategies is None:
            self.strategies = [
                "magic_split_optimization",
                "short_term_discovery",
                "buy_timing_diagnosis", 
                "hold_or_cut_decision",
                "valuation_analysis"
            ]


@dataclass
class LoggingConfig:
    """로깅 설정"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    file_path: str = "logs/magicsplit.log"
    rotation: str = "1 day"
    retention: str = "7 days"


class Config:
    """통합 설정 관리 클래스"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config_data = self._load_config()
        
        # 설정 객체들 초기화
        self.webdriver = self._create_webdriver_config()
        self.naver_finance = self._create_naver_finance_config()
        self.screenshot = self._create_screenshot_config()
        self.ai_services = self._create_ai_services_config()
        self.magic_split = self._create_magic_split_config()
        self.prompts = self._create_prompts_config()
        self.logging = self._create_logging_config()
        
        # 필요한 디렉토리 생성
        self._create_directories()
    
    def _get_default_config_path(self) -> str:
        """기본 설정 파일 경로 반환"""
        return os.path.join(
            Path(__file__).parent.parent,
            "config", 
            "config.yaml"
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                logger.info(f"설정 파일 로드 완료: {self.config_path}")
                return config_data
        except FileNotFoundError:
            logger.warning(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
            return {}
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            return {}
    
    def _create_webdriver_config(self) -> WebDriverConfig:
        """웹드라이버 설정 생성"""
        config = self._config_data.get("webdriver", {})
        chrome_config = config.get("chrome", {})
        
        return WebDriverConfig(
            headless=chrome_config.get("headless", False),
            window_size=chrome_config.get("window_size", "1920,1080"),
            user_agent=chrome_config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
            wait_timeout=config.get("wait_timeout", 10),
            implicit_wait=config.get("implicit_wait", 3)
        )
    
    def _create_naver_finance_config(self) -> NaverFinanceConfig:
        """네이버 증권 설정 생성"""
        config = self._config_data.get("naver_finance", {})
        
        return NaverFinanceConfig(
            base_url=config.get("base_url", "https://finance.naver.com"),
            stock_url=config.get("stock_url", "https://finance.naver.com/item/main.naver"),
            delay_between_requests=config.get("delay_between_requests", 2)
        )
    
    def _create_screenshot_config(self) -> ScreenshotConfig:
        """스크린샷 설정 생성"""
        config = self._config_data.get("screenshot", {})
        
        return ScreenshotConfig(
            save_path=config.get("save_path", "screenshots"),
            format=config.get("format", "png"),
            quality=config.get("quality", 95)
        )
    
    def _create_ai_services_config(self) -> AIServiceConfig:
        """AI 서비스 설정 생성"""
        config = self._config_data.get("ai_services", {})
        
        return AIServiceConfig(
            chatgpt=config.get("chatgpt", {"url": "https://chat.openai.com", "enabled": True}),
            claude=config.get("claude", {"url": "https://claude.ai", "enabled": True}),
            gemini=config.get("gemini", {"url": "https://gemini.google.com", "enabled": True})
        )
    
    def _create_magic_split_config(self) -> MagicSplitConfig:
        """매직스플릿 설정 생성"""
        config = self._config_data.get("magic_split", {}).get("default_strategy", {})
        
        return MagicSplitConfig(
            first_buy_profit=config.get("first_buy_profit", 10),
            additional_buy_drop=config.get("additional_buy_drop", 15),
            additional_buy_profit=config.get("additional_buy_profit", 15),
            max_buy_count=config.get("max_buy_count", 20)
        )
    
    def _create_prompts_config(self) -> PromptsConfig:
        """프롬프트 설정 생성"""
        config = self._config_data.get("prompts", {})
        
        return PromptsConfig(
            templates_path=config.get("templates_path", "prompts/templates"),
            strategies=config.get("strategies", [
                "magic_split_optimization",
                "short_term_discovery",
                "buy_timing_diagnosis",
                "hold_or_cut_decision", 
                "valuation_analysis"
            ])
        )
    
    def _create_logging_config(self) -> LoggingConfig:
        """로깅 설정 생성"""
        config = self._config_data.get("logging", {})
        
        return LoggingConfig(
            level=config.get("level", "INFO"),
            format=config.get("format", "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"),
            file_path=config.get("file_path", "logs/magicsplit.log"),
            rotation=config.get("rotation", "1 day"),
            retention=config.get("retention", "7 days")
        )
    
    def _create_directories(self) -> None:
        """필요한 디렉토리들 생성"""
        directories = [
            self.screenshot.save_path,
            os.path.dirname(self.logging.file_path),
            self.prompts.templates_path
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"디렉토리 생성/확인: {directory}")
    
    def get_stock_url(self, stock_code: str) -> str:
        """주식 코드로 URL 생성"""
        return f"{self.naver_finance.stock_url}?code={stock_code}"
    
    def reload_config(self) -> None:
        """설정 파일 다시 로드"""
        self._config_data = self._load_config()
        logger.info("설정이 다시 로드되었습니다")


# 전역 설정 인스턴스
config = Config()