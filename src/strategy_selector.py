"""
전략 선택 인터페이스
키보드 입력을 통한 인터랙티브 전략 선택
"""

import os
import sys
from typing import Optional, Dict, List
from dataclasses import dataclass

# keyboard 모듈 제거 - 표준 input() 사용
KEYBOARD_AVAILABLE = False
    
from loguru import logger

from .config import Config
from .prompt_manager import PromptManager


@dataclass
class StrategyChoice:
    """전략 선택 결과"""
    strategy_name: str
    strategy_description: str
    template_content: str
    user_confirmed: bool


class StrategySelector:
    """전략 선택 인터페이스 클래스"""
    
    def __init__(self, config: Config, prompt_manager: PromptManager):
        """
        전략 선택기 초기화
        
        Args:
            config: 설정 객체
            prompt_manager: 프롬프트 관리자
        """
        self.config = config
        self.prompt_manager = prompt_manager
        self.available_strategies = prompt_manager.get_available_strategies()
        
        # 키보드 단축키 매핑
        self.strategy_keys = {
            '1': 'magic_split_optimization',
            '2': 'short_term_discovery', 
            '3': 'buy_timing_diagnosis',
            '4': 'hold_or_cut_decision',
            '5': 'valuation_analysis'
        }
        
        # 전략별 색상 코드 (터미널 출력용)
        self.colors = {
            'magic_split_optimization': '\033[94m',  # 파란색
            'short_term_discovery': '\033[92m',      # 초록색
            'buy_timing_diagnosis': '\033[93m',      # 노란색
            'hold_or_cut_decision': '\033[91m',      # 빨간색
            'valuation_analysis': '\033[95m',        # 자주색
            'reset': '\033[0m'                       # 색상 리셋
        }
    
    def _clear_screen(self) -> None:
        """화면 클리어"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_header(self) -> None:
        """헤더 출력"""
        print("=" * 80)
        print("🚀 MagicSplitGPT - 주식 분석 전략 선택")
        print("=" * 80)
        print()
    
    def _print_strategy_menu(self) -> None:
        """전략 메뉴 출력"""
        print("📋 사용 가능한 분석 전략:")
        print()
        
        for key, strategy_name in self.strategy_keys.items():
            color = self.colors.get(strategy_name, '')
            reset = self.colors['reset']
            description = self.prompt_manager.get_strategy_description(strategy_name)
            
            print(f"{color}[{key}] {description}{reset}")
        
        print()
        print("🎯 단축키:")
        print("• Enter: 기본 전략 (매직스플릿 최적화)")
        print("• q: 프로그램 종료")
        print("• r: 화면 새로고침")
        print("• h: 도움말 보기")
        print()
    
    def _print_strategy_details(self, strategy_name: str) -> None:
        """선택한 전략의 상세 정보 출력"""
        color = self.colors.get(strategy_name, '')
        reset = self.colors['reset']
        description = self.prompt_manager.get_strategy_description(strategy_name)
        
        print(f"\n{color}📊 선택된 전략: {description}{reset}")
        
        # 템플릿 미리보기
        template_content = self.prompt_manager.load_template(strategy_name)
        if template_content:
            preview = template_content[:200] + "..." if len(template_content) > 200 else template_content
            print(f"\n📝 프롬프트 미리보기:")
            print("-" * 60)
            print(preview)
            print("-" * 60)
        else:
            print(f"\n❌ 템플릿을 로드할 수 없습니다: {strategy_name}")
    
    def _print_help(self) -> None:
        """도움말 출력"""
        print("\n" + "="*60)
        print("📖 MagicSplitGPT 사용 가이드")
        print("="*60)
        
        print("\n🎯 전략별 특징:")
        for key, strategy_name in self.strategy_keys.items():
            description = self.prompt_manager.get_strategy_description(strategy_name)
            print(f"  [{key}] {description}")
        
        print("\n💡 사용 방법:")
        print("1. 숫자 키 (1-5)로 원하는 전략 선택")
        print("2. 주식 코드 입력 (예: 005930, 000660)")
        print("3. 데이터 수집 및 AI 서비스 업로드 자동 진행")
        print("4. 각 AI 서비스에서 분석 결과 확인")
        
        print("\n⚙️ 매직스플릿 시스템 특징:")
        print("• 1차 매수 후 설정 비율 상승시 익절")
        print("• 15% 하락시마다 자동 추가매수")
        print("• 15% 상승시마다 단계적 익절")
        print("• 변동성이 큰 종목에서 높은 수익률")
        
        print("\nPress any key to continue...")
        input()
    
    def _validate_strategy_selection(self, user_input: str) -> Optional[str]:
        """
        사용자 입력 유효성 검사
        
        Args:
            user_input: 사용자 입력
            
        Returns:
            유효한 전략명 또는 None
        """
        user_input = user_input.strip().lower()
        
        # 숫자 키 매핑 확인
        if user_input in self.strategy_keys:
            return self.strategy_keys[user_input]
        
        # 전략명 직접 입력 확인
        if user_input in self.available_strategies:
            return user_input
        
        # 기본 전략 (Enter)
        if user_input == '':
            return 'magic_split_optimization'
        
        return None
    
    def select_strategy_interactive(self) -> Optional[StrategyChoice]:
        """
        인터랙티브 전략 선택
        
        Returns:
            선택된 전략 정보 또는 None (종료)
        """
        while True:
            self._clear_screen()
            self._print_header()
            self._print_strategy_menu()
            
            try:
                user_input = input("전략을 선택하세요: ").strip()
                
                # 특수 명령어 처리
                if user_input.lower() == 'q':
                    print("\n👋 프로그램을 종료합니다.")
                    return None
                    
                elif user_input.lower() == 'r':
                    continue  # 화면 새로고침
                
                elif user_input.lower() == 'h':
                    self._print_help()
                    continue
                
                # 전략 선택 유효성 검사
                strategy_name = self._validate_strategy_selection(user_input)
                
                if strategy_name is None:
                    print(f"\n❌ 잘못된 선택입니다: {user_input}")
                    print("올바른 번호(1-5) 또는 전략명을 입력해주세요.")
                    input("\nPress Enter to continue...")
                    continue
                
                # 선택한 전략 상세 정보 표시
                self._print_strategy_details(strategy_name)
                
                # 사용자 확인
                try:
                    confirm = input(f"\n이 전략을 사용하시겠습니까? (Y/n): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n\n👋 프로그램을 종료합니다.")
                    return None
                
                if confirm in ['', 'y', 'yes']:
                    # 템플릿 로드
                    template_content = self.prompt_manager.load_template(strategy_name)
                    
                    if template_content is None:
                        print(f"\n❌ 템플릿 로드 실패: {strategy_name}")
                        input("Press Enter to continue...")
                        continue
                    
                    # 전략 선택 결과 반환
                    choice = StrategyChoice(
                        strategy_name=strategy_name,
                        strategy_description=self.prompt_manager.get_strategy_description(strategy_name),
                        template_content=template_content,
                        user_confirmed=True
                    )
                    
                    logger.info(f"전략 선택 완료: {strategy_name}")
                    return choice
                
                else:
                    print("\n🔄 전략 선택을 다시 진행합니다.")
                    continue
                    
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋 프로그램을 종료합니다.")
                return None
                
            except Exception as e:
                logger.error(f"전략 선택 중 오류: {e}")
                print(f"\n❌ 오류가 발생했습니다: {e}")
                input("Press Enter to continue...")
                continue
    
    def select_strategy_quick(self, strategy_key: str) -> Optional[StrategyChoice]:
        """
        빠른 전략 선택 (키 입력 없이)
        
        Args:
            strategy_key: 전략 키 또는 전략명
            
        Returns:
            선택된 전략 정보 또는 None
        """
        strategy_name = self._validate_strategy_selection(strategy_key)
        
        if strategy_name is None:
            logger.error(f"잘못된 전략 키: {strategy_key}")
            return None
        
        # 템플릿 로드
        template_content = self.prompt_manager.load_template(strategy_name)
        
        if template_content is None:
            logger.error(f"템플릿 로드 실패: {strategy_name}")
            return None
        
        choice = StrategyChoice(
            strategy_name=strategy_name,
            strategy_description=self.prompt_manager.get_strategy_description(strategy_name),
            template_content=template_content,
            user_confirmed=True
        )
        
        logger.info(f"빠른 전략 선택 완료: {strategy_name}")
        return choice
    
    def get_stock_code_input(self) -> Optional[str]:
        """
        주식 코드 입력 받기
        
        Returns:
            입력된 주식 코드 또는 None (취소)
        """
        print("\n" + "="*50)
        print("📈 주식 코드 입력")
        print("="*50)
        
        print("\n💡 입력 예시:")
        print("• 삼성전자: 005930")
        print("• SK하이닉스: 000660") 
        print("• NAVER: 035420")
        print("• 카카오: 035720")
        
        print("\n🎯 단축키:")
        print("• q: 전략 선택으로 돌아가기")
        print("• exit: 프로그램 종료")
        
        while True:
            try:
                stock_code = input("\n주식 코드를 입력하세요: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋 프로그램을 종료합니다.")
                return None
                
            try:
                
                # 종료 명령어 처리
                if stock_code.lower() == 'q':
                    return None
                    
                if stock_code.lower() == 'exit':
                    sys.exit(0)
                
                # 주식 코드 유효성 검사
                if not stock_code:
                    print("❌ 주식 코드를 입력해주세요.")
                    continue
                
                # 숫자만 있고 6자리인지 확인
                if not stock_code.isdigit() or len(stock_code) != 6:
                    print("❌ 주식 코드는 6자리 숫자여야 합니다. (예: 005930)")
                    continue
                
                # 확인
                try:
                    confirm = input(f"\n주식 코드 '{stock_code}'가 맞습니까? (Y/n): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n\n👋 프로그램을 종료합니다.")
                    return None
                
                if confirm in ['', 'y', 'yes']:
                    logger.info(f"주식 코드 입력 완료: {stock_code}")
                    return stock_code
                else:
                    print("🔄 주식 코드를 다시 입력해주세요.")
                    continue
                    
            except KeyboardInterrupt:
                print("\n\n👋 주식 코드 입력이 취소되었습니다.")
                return None
                
            except Exception as e:
                logger.error(f"주식 코드 입력 중 오류: {e}")
                print(f"❌ 오류가 발생했습니다: {e}")
                continue
    
    def get_strategy_statistics(self) -> Dict[str, any]:
        """
        전략 통계 정보 반환
        
        Returns:
            전략 통계 딕셔너리
        """
        stats = {
            "total_strategies": len(self.available_strategies),
            "strategy_details": {}
        }
        
        for strategy in self.available_strategies:
            template_info = self.prompt_manager.get_template_info(strategy)
            stats["strategy_details"][strategy] = {
                "description": self.prompt_manager.get_strategy_description(strategy),
                "template_exists": template_info["exists"],
                "template_valid": template_info["valid"],
                "template_size": template_info["size"]
            }
        
        return stats
    
    def print_strategy_summary(self) -> None:
        """전략 요약 정보 출력"""
        print("\n" + "="*70)
        print("📊 MagicSplitGPT 전략 요약")
        print("="*70)
        
        stats = self.get_strategy_statistics()
        
        print(f"\n📈 총 {stats['total_strategies']}개의 전략이 준비되어 있습니다.\n")
        
        for strategy, details in stats["strategy_details"].items():
            color = self.colors.get(strategy, '')
            reset = self.colors['reset']
            status = "✅" if details["template_valid"] else "❌"
            
            print(f"{color}{status} {details['description']}{reset}")
            print(f"   파일 크기: {details['template_size']} bytes")
            print()
        
        print("="*70)