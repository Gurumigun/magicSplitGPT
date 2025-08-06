"""
MagicSplitGPT 메인 실행 프로그램
"""

import sys
import time
from pathlib import Path
from typing import Optional
from datetime import datetime

from loguru import logger

from .config import Config
from .prompt_manager import PromptManager
from .stock_data_collector import StockDataCollector, StockData
from .ai_service_automator import AIServiceAutomator
from .strategy_selector import StrategySelector, StrategyChoice


class MagicSplitGPT:
    """MagicSplitGPT 메인 클래스"""
    
    def __init__(self):
        """메인 클래스 초기화"""
        self.config: Optional[Config] = None
        self.prompt_manager: Optional[PromptManager] = None
        self.stock_collector: Optional[StockDataCollector] = None
        self.ai_automator: Optional[AIServiceAutomator] = None
        self.strategy_selector: Optional[StrategySelector] = None
        
        self._setup_logging()
        self._initialize_components()
    
    def _setup_logging(self) -> None:
        """로깅 시스템 설정"""
        try:
            # 기본 로그 설정
            logger.remove()  # 기본 핸들러 제거
            
            # 콘솔 출력 설정
            logger.add(
                sys.stdout,
                level="INFO",
                format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
                colorize=True
            )
            
            # 설정이 로드되면 파일 로깅도 설정
            logger.info("로깅 시스템 초기화 완료")
            
        except Exception as e:
            print(f"로깅 설정 실패: {e}")
            sys.exit(1)
    
    def _initialize_components(self) -> None:
        """컴포넌트 초기화"""
        try:
            logger.info("MagicSplitGPT 컴포넌트 초기화 시작")
            
            # 설정 로드
            self.config = Config()
            logger.info("설정 로드 완료")
            
            # 파일 로깅 설정 (설정 로드 후)
            log_file = Path(self.config.logging.file_path)
            log_file.parent.mkdir(exist_ok=True)
            
            logger.add(
                str(log_file),
                level=self.config.logging.level,
                format=self.config.logging.format,
                rotation=self.config.logging.rotation,
                retention=self.config.logging.retention,
                encoding="utf-8"
            )
            logger.info(f"파일 로깅 설정 완료: {log_file}")
            
            # 프롬프트 관리자 초기화
            self.prompt_manager = PromptManager(self.config)
            logger.info("프롬프트 관리자 초기화 완료")
            
            # 템플릿 유효성 검사
            validation_results = self.prompt_manager.validate_all_templates()
            valid_count = sum(validation_results.values())
            total_count = len(validation_results)
            
            if valid_count != total_count:
                logger.warning(f"일부 템플릿 유효성 검사 실패: {valid_count}/{total_count}")
                for template, valid in validation_results.items():
                    if not valid:
                        logger.error(f"유효하지 않은 템플릿: {template}")
            else:
                logger.info("모든 프롬프트 템플릿 유효성 검사 통과")
            
            # 주식 데이터 수집기 초기화
            self.stock_collector = StockDataCollector(self.config)
            logger.info("주식 데이터 수집기 초기화 완료")
            
            # AI 서비스 자동화 초기화
            self.ai_automator = AIServiceAutomator(self.config)
            logger.info("AI 서비스 자동화 초기화 완료")
            
            # 전략 선택기 초기화
            self.strategy_selector = StrategySelector(self.config, self.prompt_manager)
            logger.info("전략 선택기 초기화 완료")
            
            logger.info("모든 컴포넌트 초기화 완료")
            
        except Exception as e:
            logger.error(f"컴포넌트 초기화 실패: {e}")
            sys.exit(1)
    
    def _print_welcome_message(self) -> None:
        """시작 메시지 출력"""
        print("=" * 80)
        print("🚀 MagicSplitGPT - 주식 분석 자동화 프로그램")
        print("📊 박성현 작가의 매직스플릿 전략 기반 AI 분석 시스템")
        print("=" * 80)
        print()
        print("💡 주요 기능:")
        print("• 네이버 증권에서 종목 데이터 자동 수집")
        print("• 5가지 전문 분석 전략 제공")
        print("• ChatGPT, Claude, Gemini 자동 업로드")
        print("• 차트 이미지와 함께 종합 분석")
        print()
        print("🎯 매직스플릿 시스템:")
        print("• 변동성 기반 자동 매매 시스템")
        print("• 15% 하락시 추가매수, 15% 상승시 익절")
        print("• 급등락 종목에서 최고 수익률 실현")
        print()
        
        # 컴포넌트 상태 확인
        enabled_services = [
            service for service, config in {
                "ChatGPT": self.config.ai_services.chatgpt["enabled"],
                "Claude": self.config.ai_services.claude["enabled"], 
                "Gemini": self.config.ai_services.gemini["enabled"]
            }.items() if config
        ]
        
        print(f"🤖 활성화된 AI 서비스: {', '.join(enabled_services)}")
        print(f"📋 사용 가능한 전략: {len(self.strategy_selector.available_strategies)}개")
        print()
    
    def _process_stock_analysis(
        self, 
        stock_code: str, 
        strategy_choice: StrategyChoice
    ) -> bool:
        """
        주식 분석 프로세스 실행
        
        Args:
            stock_code: 주식 코드
            strategy_choice: 선택된 전략
            
        Returns:
            처리 성공 여부
        """
        try:
            logger.info(f"주식 분석 프로세스 시작: {stock_code}, 전략: {strategy_choice.strategy_name}")
            
            # 1단계: 주식 데이터 수집
            print(f"\n🔍 1단계: {stock_code} 데이터 수집 중...")
            print("• 네이버 증권 접속")
            print("• 기본 정보, 뉴스, 토론실, 차트 수집")
            print("• 예상 소요시간: 2-3분")
            
            stock_data = self.stock_collector.collect_stock_data(stock_code)
            
            if stock_data is None:
                print("❌ 주식 데이터 수집 실패")
                logger.error(f"주식 데이터 수집 실패: {stock_code}")
                return False
            
            print(f"✅ 데이터 수집 완료: {stock_data.stock_name}")
            print(f"   현재가: {stock_data.current_price} ({stock_data.change_rate})")
            print(f"   수집된 뉴스: {len(stock_data.news_data)}개")
            print(f"   차트 이미지: {len(stock_data.chart_screenshots)}개")
            
            # 수집된 데이터 JSON 저장
            try:
                json_path = self.stock_collector.save_data_to_json(stock_data)
                print(f"   데이터 저장: {json_path}")
            except Exception as e:
                logger.warning(f"JSON 저장 실패: {e}")
            
            # 2단계: AI 서비스 업로드 준비
            print(f"\n🤖 2단계: AI 분석 준비 중...")
            print(f"• 선택된 전략: {strategy_choice.strategy_description}")
            print("• 프롬프트와 이미지 준비")
            
            final_prompt, image_paths = self.ai_automator.prepare_stock_data_for_upload(
                stock_data, 
                strategy_choice.template_content
            )
            
            print(f"   프롬프트 길이: {len(final_prompt)} 문자")
            print(f"   첨부 이미지: {len(image_paths)}개")
            
            # 3단계: AI 서비스 업로드
            print(f"\n🚀 3단계: AI 서비스 업로드 중...")
            print("• ChatGPT, Claude, Gemini 순차 업로드")
            print("• 예상 소요시간: 1-2분")
            print("\n⚠️  주의: 각 AI 서비스에 로그인이 되어있는지 확인하세요!")
            
            # 사용자 확인
            try:
                proceed = input("\n업로드를 진행하시겠습니까? (Y/n): ").strip().lower()
                if proceed not in ['', 'y', 'yes']:
                    print("업로드가 취소되었습니다.")
                    return False
            except (EOFError, KeyboardInterrupt):
                print("\n\n👋 프로그램을 종료합니다.")
                return False
            
            # AI 서비스 업로드 실행
            upload_results = self.ai_automator.upload_to_ai_services(
                prompt=final_prompt,
                image_paths=image_paths
            )
            
            # 4단계: 결과 요약
            print(f"\n📊 4단계: 업로드 결과")
            summary = self.ai_automator.get_upload_summary(upload_results)
            print(summary)
            
            # 성공한 서비스가 있는지 확인
            successful_uploads = [r for r in upload_results if r.success]
            
            # AI 업로드 완료 후 드라이버 종료
            try:
                self.stock_collector.close_driver_if_needed()
                logger.info("브라우저 드라이버 정상 종료")
            except Exception as e:
                logger.warning(f"드라이버 종료 중 오류: {e}")
            
            if successful_uploads:
                print("\n🎉 분석 완료! 각 AI 서비스에서 결과를 확인하세요.")
                
                # 성공한 서비스별 URL 정보
                for result in successful_uploads:
                    if result.response_url:
                        print(f"• {result.service_name}: {result.response_url}")
                
                logger.info(f"주식 분석 완료: {stock_code} - {len(successful_uploads)}개 서비스 성공")
                return True
            else:
                print("\n❌ 모든 AI 서비스 업로드 실패")
                print("네트워크 연결이나 로그인 상태를 확인해주세요.")
                logger.error(f"모든 AI 서비스 업로드 실패: {stock_code}")
                return False
                
        except Exception as e:
            logger.error(f"주식 분석 프로세스 오류: {e}")
            print(f"\n❌ 분석 중 오류 발생: {e}")
            
            # 오류 발생 시에도 드라이버 종료
            try:
                self.stock_collector.close_driver_if_needed()
                logger.info("오류 상황에서 브라우저 드라이버 정상 종료")
            except Exception as driver_error:
                logger.warning(f"오류 상황에서 드라이버 종료 중 오류: {driver_error}")
            
            return False
    
    def run(self) -> None:
        """메인 실행 함수"""
        try:
            # 시작 메시지
            self._print_welcome_message()
            
            # 전략 요약 표시
            self.strategy_selector.print_strategy_summary()
            
            logger.info("MagicSplitGPT 프로그램 시작")
            
            # 메인 루프
            while True:
                try:
                    # 전략 선택
                    print("\n" + "="*50)
                    strategy_choice = self.strategy_selector.select_strategy_interactive()
                    
                    if strategy_choice is None:
                        print("\n👋 프로그램을 종료합니다.")
                        break
                    
                    # 주식 코드 입력
                    stock_code = self.strategy_selector.get_stock_code_input()
                    
                    if stock_code is None:
                        print("🔄 전략 선택으로 돌아갑니다.")
                        continue
                    
                    # 주식 분석 실행
                    success = self._process_stock_analysis(stock_code, strategy_choice)
                    
                    if success:
                        # 사용자 다음 행동 선택
                        user_action = self.ai_automator.wait_for_user_action()
                        
                        if user_action == 'exit':
                            print("\n👋 프로그램을 종료합니다.")
                            break
                        else:
                            print("\n🔄 새로운 분석을 시작합니다.")
                            time.sleep(2)
                            continue
                    else:
                        # 실패시 재시도 옵션
                        retry = input("\n다시 시도하시겠습니까? (Y/n): ").strip().lower()
                        if retry not in ['', 'y', 'yes']:
                            break
                        
                except KeyboardInterrupt:
                    print("\n\n👋 사용자가 프로그램을 중단했습니다.")
                    break
                    
                except Exception as e:
                    logger.error(f"메인 루프 오류: {e}")
                    print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
                    
                    # 오류 발생시 계속 여부 확인
                    try:
                        continue_program = input("계속 진행하시겠습니까? (Y/n): ").strip().lower()
                        if continue_program not in ['', 'y', 'yes']:
                            break
                    except (EOFError, KeyboardInterrupt):
                        print("\n\n👋 프로그램을 종료합니다.")
                        break
        
        except Exception as e:
            logger.critical(f"치명적 오류: {e}")
            print(f"\n💥 치명적 오류가 발생했습니다: {e}")
            sys.exit(1)
        
        finally:
            logger.info("MagicSplitGPT 프로그램 종료")
            print("\n감사합니다! MagicSplitGPT를 사용해주셔서 감사합니다. 📊💰")


def main():
    """메인 엔트리 포인트"""
    try:
        app = MagicSplitGPT()
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 프로그램 시작 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()