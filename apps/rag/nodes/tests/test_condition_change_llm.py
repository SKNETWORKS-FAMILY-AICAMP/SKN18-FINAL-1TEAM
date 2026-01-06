"""
LLM 기반 조건 변경 의도 감지 테스트

이 스크립트는 OpenAI API를 mock하여 condition_change_intent 기능을 테스트합니다.
"""
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from apps.rag.nodes.query_analyzer_node import analyze_query
from apps.rag.common.state import RAGState


def test_llm_condition_change_detection():
    """LLM이 조건 변경 의도를 감지하는지 테스트"""
    
    # Mock OpenAI response
    mock_response = {
        "hard_filters": {
            "location": "홍대",
            "deal_type": "전세",
            "building_type": "",
            "max_deposit": None,
            "min_deposit": None,
            "max_rent": None,
            "max_size": None,
            "max_distance": None,
            "facilities": []
        },
        "soft_filters": [],
        "search_strategy": "neo4j_keyword",
        "use_cached_context": False,
        "cached_context_reason": "새로운 조건",
        "condition_change_intent": "deal_type"  # 거래유형 변경 감지
    }
    
    # Mock OpenAI client
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = f"""```json
{str(mock_response).replace("'", '"').replace("None", "null").replace("False", "false")}
```"""
    mock_client.chat.completions.create.return_value = mock_completion
    
    # 초기 상태: 사용자가 이미 월세로 조건을 설정함
    state = RAGState(
        question="아니 월세 말고 전세로 바꿔줘",
        session_id="test_session",
        collected_conditions={
            "location": "홍대",
            "deal_type": "월세"  # 기존에 월세로 설정되어 있음
        }
    )
    
    # OpenAI 클라이언트를 mock으로 패치
    with patch('apps.rag.nodes.query_analyzer_node.OpenAI', return_value=mock_client):
        result = analyze_query(state)
    
    # 검증: LLM이 조건 변경 의도를 감지했는지
    print("\n" + "="*60)
    print("테스트 결과")
    print("="*60)
    print(f"입력 질문: {state['question']}")
    print(f"기존 조건: {{'location': '홍대', 'deal_type': '월세'}}")
    print(f"\nLLM 감지 결과:")
    print(f"  - 조건 변경 의도: {mock_response['condition_change_intent']}")
    print(f"\n기대 동작: deal_type이 collected_conditions에서 제거되어야 함")
    print(f"실제 collected_conditions: {result.get('collected_conditions', {})}")
    
    # collected_conditions에서 deal_type이 제거되었는지 확인
    assert 'deal_type' not in result.get('collected_conditions', {}), \
        "deal_type이 collected_conditions에서 제거되지 않았습니다!"
    
    print("\n✅ 테스트 통과: LLM이 조건 변경 의도를 정확히 감지하고 처리했습니다!")
    print("="*60 + "\n")


def test_no_condition_change():
    """조건 변경 의도가 없을 때 정상 동작하는지 테스트"""
    
    mock_response = {
        "hard_filters": {
            "location": "강남",
            "deal_type": "월세",
            "building_type": "원룸",
            "max_deposit": 5000,
            "min_deposit": None,
            "max_rent": 50,
            "max_size": None,
            "max_distance": None,
            "facilities": []
        },
        "soft_filters": ["깔끔한"],
        "search_strategy": "neo4j_keyword",
        "use_cached_context": False,
        "cached_context_reason": "새로운 검색",
        "condition_change_intent": None  # 변경 의도 없음
    }
    
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = f"""```json
{str(mock_response).replace("'", '"').replace("None", "null").replace("False", "false")}
```"""
    mock_client.chat.completions.create.return_value = mock_completion
    
    state = RAGState(
        question="강남 월세 원룸 보증금 5000 이하 월세 50 이하 깔끔한 곳",
        session_id="test_session2",
        collected_conditions={}
    )
    
    with patch('apps.rag.nodes.query_analyzer_node.OpenAI', return_value=mock_client):
        result = analyze_query(state)
    
    print("\n" + "="*60)
    print("테스트 결과 (조건 변경 없음)")
    print("="*60)
    print(f"입력 질문: {state['question']}")
    print(f"조건 변경 의도: {mock_response['condition_change_intent']}")
    print(f"hard_filters: {result.get('hard_filters', {})}")
    print(f"soft_filters: {result.get('soft_filters', [])}")
    
    assert result.get('hard_filters', {}).get('location') == "강남"
    assert result.get('hard_filters', {}).get('deal_type') == "월세"
    
    print("\n✅ 테스트 통과: 조건 변경 의도가 없을 때도 정상 동작합니다!")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n🧪 LLM 기반 조건 변경 의도 감지 테스트 시작\n")
    
    try:
        test_llm_condition_change_detection()
        test_no_condition_change()
        print("\n🎉 모든 테스트 통과!\n")
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
