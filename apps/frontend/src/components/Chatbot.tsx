'use client'

import { useState, useEffect, useRef } from 'react'
import { sendChatQuestion } from '../api/chatApi'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
}

interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}

interface FilterInfo {
  summary: string
  details: {
    location?: string
    facilities?: string[]
    deal_type?: string
    building_type?: string
    max_deposit?: string
    max_rent?: string
    style?: string[]
  }
  search_strategy?: string
}

interface ChatbotRecommendData {
  landIds: number[]
  filterInfo: FilterInfo | null
  properties: any[]  // graph_results from backend
}

interface ChatbotProps {
  onRecommendLands?: (landIds: number[]) => void
  onChatbotRecommend?: (data: ChatbotRecommendData) => void
}

// 순위별 색상 정의
const rankColors: Record<number, { bg: string; border: string; badge: string }> = {
  1: { bg: 'bg-amber-50', border: 'border-l-4 border-amber-400', badge: 'bg-amber-400 text-white' },
  2: { bg: 'bg-slate-100', border: 'border-l-4 border-slate-400', badge: 'bg-slate-400 text-white' },
  3: { bg: 'bg-orange-50', border: 'border-l-4 border-orange-400', badge: 'bg-orange-400 text-white' },
};

const defaultRankColor = { bg: 'bg-gray-50', border: 'border-l-4 border-gray-300', badge: 'bg-gray-400 text-white' };

// AI 응답에서 추가질문 섹션을 분리하는 함수
const extractSuggestedQuestions = (content: string): { mainContent: string; questions: string[] } => {
  // 추가질문 패턴: 다양한 형식 지원 (이모지 유무, 띄어쓰기 다양)
  const suggestionPattern = /(?:👍|✨|💡)?\s*추가\s*질문[^\n]*(?:제안)?[^\n]*/i;
  const match = content.match(suggestionPattern);

  console.log('=== extractSuggestedQuestions 디버깅 ===');
  console.log('원본 내용 마지막 200자:', content.substring(content.length - 200));
  console.log('패턴 매치 결과:', match);

  if (!match) {
    return { mainContent: content, questions: [] };
  }

  const splitIndex = content.indexOf(match[0]);
  const mainContent = content.substring(0, splitIndex).trim();
  const questionSection = content.substring(splitIndex + match[0].length).trim();

  console.log('질문 섹션:', questionSection);

  // 줄바꿈으로 질문들 분리, 순번 제거
  const questions = questionSection
    .split(/\n/)
    .map(q => q.trim().replace(/^\d+\.\s*/, '')) // 앞의 "1.", "2." 등 순번 제거
    .filter(q => q.length > 0 && !q.match(/^👍/));

  console.log('추출된 질문들:', questions);

  return { mainContent, questions };
};

// AI 응답을 순위별로 파싱하는 함수
const parseRankedContent = (content: string): { rank: number | null; content: string }[] => {
  // 순위 패턴: 1순위, 2순위, **1순위**, 1위, **1위** 등
  const rankPattern = /(?:#{1,3}\s*)?(?:\*\*)?(?:🥇|🥈|🥉)?(\d+)(?:순위|위)(?:\*\*)?[:\s]*/g;

  const parts: { rank: number | null; content: string }[] = [];
  const matches: { index: number; rank: number; fullMatch: string }[] = [];

  let match;
  while ((match = rankPattern.exec(content)) !== null) {
    matches.push({
      index: match.index,
      rank: parseInt(match[1]),
      fullMatch: match[0]
    });
  }

  if (matches.length === 0) {
    return [{ rank: null, content }];
  }

  // 첫 번째 순위 전의 텍스트 (인트로)
  if (matches[0].index > 0) {
    const introContent = content.substring(0, matches[0].index).trim();
    if (introContent) {
      parts.push({ rank: null, content: introContent });
    }
  }

  // 각 순위별 콘텐츠 분리
  for (let i = 0; i < matches.length; i++) {
    const currentMatch = matches[i];
    const nextMatch = matches[i + 1];
    const startIndex = currentMatch.index + currentMatch.fullMatch.length;
    const endIndex = nextMatch ? nextMatch.index : content.length;
    const rankContent = content.substring(startIndex, endIndex).trim();
    if (rankContent) {
      parts.push({ rank: currentMatch.rank, content: rankContent });
    }
  }

  return parts;
};

export default function Chatbot({ onRecommendLands, onChatbotRecommend }: ChatbotProps = {}) {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [latestFilterInfo, setLatestFilterInfo] = useState<FilterInfo | null>(null)
  const [latestProperties, setLatestProperties] = useState<any[]>([])
  // const messagesEndRef = useRef<HTMLDivElement>(null) // 자동 스크롤 제거됨
  // 초기 마운트 시 저장된 세션 복원
  useEffect(() => {
    const savedSessions = localStorage.getItem('chatSessions')
    const savedCurrentId = localStorage.getItem('currentSessionId')

    if (!savedSessions) return

    const parsed: ChatSession[] = JSON.parse(savedSessions).map((session: any) => ({
      ...session,
      createdAt: new Date(session.createdAt),
      updatedAt: new Date(session.updatedAt),
      messages: session.messages.map((msg: any) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      })),
    }))

    setSessions(parsed)

    if (savedCurrentId) {
      setCurrentSessionId(savedCurrentId)
      const current = parsed.find(s => s.id === savedCurrentId)
      if (current) {
        setMessages(current.messages)
      }
    }
  }, [])

  // 세션 변경 시 LocalStorage 반영
  useEffect(() => {
    if (sessions.length === 0) {
      localStorage.removeItem('chatSessions')
      return
    }
    localStorage.setItem('chatSessions', JSON.stringify(sessions))
  }, [sessions])

  // 현재 세션 ID 변경 시 LocalStorage 반영
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem('currentSessionId', currentSessionId)
    }
  }, [currentSessionId])

  const formatTime = (date: Date) => {
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  }

  const formatDate = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return '오늘'
    if (diffDays === 1) return '어제'
    if (diffDays < 7) return `${diffDays}일 전`

    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
  }

  // 새 채팅 세션 생성 (+ 버튼)
  const startNewChat = () => {
    const newId = Date.now().toString()

    const newSession: ChatSession = {
      id: newId,
      title: '새 대화',
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    }

    setSessions(prev => [newSession, ...prev])
    setCurrentSessionId(newId)
    setMessages([])
  }

  // 메시지 전송
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    let sessionId = currentSessionId

    // 세션이 없으면 자동으로 새 세션 생성
    if (!sessionId) {
      sessionId = Date.now().toString()
      const newSession: ChatSession = {
        id: sessionId,
        title: '새 대화',
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      }
      setSessions(prev => [newSession, ...prev])
      setCurrentSessionId(sessionId)
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      // 직접 fetch로 filter_info와 graph_results 받아오기
      const response = await fetch('http://localhost:8001/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: userMessage.content,
          session_id: sessionId
        }),
      });
      const data = await response.json();
      const answer = data.answer || '응답을 받을 수 없습니다.';

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: answer,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, aiMessage])

      // 필터 정보와 매물 데이터 저장
      if (data.filter_info) {
        setLatestFilterInfo(data.filter_info);
      }

      // AI 응답에서 /landDetail/{id} 형태의 링크를 찾아 매물 ID 추출
      const landIds = [...answer.matchAll(/\/landDetail\/(\d+)/g)]
        .map(match => Number(match[1]))
        .filter(Boolean);

      // 새로운 콜백으로 전달 (우선)
      if (onChatbotRecommend && (landIds.length > 0 || data.filter_info)) {
        onChatbotRecommend({
          landIds,
          filterInfo: data.filter_info || null,
          properties: data.graph_results || []  // 백엔드의 graph_results 전달
        });
        setLatestProperties(data.graph_results || []);
      }
      // 기존 콜백 호환성 유지
      else if (onRecommendLands && landIds.length > 0) {
        onRecommendLands(landIds);
      }
    } catch (error) {
      setMessages(prev => [
        ...prev,
        {
          id: (Date.now() + 2).toString(),
          type: 'ai',
          content: '응답 중 오류가 발생했습니다. 다시 시도해주세요.',
          timestamp: new Date(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  // 메시지 변경 시 세션 내용/제목 업데이트
  useEffect(() => {
    if (!currentSessionId || messages.length === 0) return

    setSessions(prev =>
      prev.map(session =>
        session.id === currentSessionId
          ? {
            ...session,
            messages,
            updatedAt: new Date(),
            title:
              session.title === '새 대화'
                ? messages[0].content.slice(0, 30) +
                (messages[0].content.length > 30 ? '...' : '')
                : session.title,
          }
          : session,
      ),
    )
  }, [messages, currentSessionId])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // 과거 세션 선택
  const handleSelectSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId)
    if (!session) return
    setCurrentSessionId(sessionId)
    setMessages(session.messages)
    setShowHistoryModal(false)
  }

  // 과거 세션 삭제
  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm('이 대화를 삭제하시겠습니까?')) return

    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== sessionId)

      if (currentSessionId === sessionId) {
        setCurrentSessionId(null)
        setMessages([])
      }

      return filtered
    })
  }

  return (
    <>
      <div className="flex flex-col h-full bg-white rounded-xl border"
        style={{ height: 'calc(100vh - 120px)' }}
      >

        {/* 헤더 */}
        <div className="flex justify-between p-4 border-b">
          <h2 className="text-lg font-bold text-black">매물 추천 챗봇</h2>

          <div className="flex items-center gap-2">
            {/* 새 채팅(+ 버튼) */}
            <button
              onClick={startNewChat}
              className="w-9 h-9 flex items-center justify-center rounded-full border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] transition-colors"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 5v14M5 12h14" strokeLinecap="round" />
              </svg>
            </button>

            {/* 과거 대화보기 버튼 */}
            <button
              onClick={() => setShowHistoryModal(true)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[var(--color-text-secondary)] border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 20 20"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M10 18C14.4183 18 18 14.4183 18 10C18 5.58172 14.4183 2 10 2C5.58172 2 2 5.58172 2 10C2 14.4183 5.58172 18 10 18Z"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M10 6V10L13 13"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              채팅 내역
            </button>
          </div>
        </div>

        {/* 메시지 영역 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && !isLoading ? (
            /* 초기 화면 - 환영 메시지 및 추천 질문 */
            <div className="flex flex-col items-center justify-center h-full space-y-6">
              {/* 환영 메시지 */}
              <div className="text-center">
                <h3 className="text-2xl font-bold text-[var(--color-primary)] mb-2">안녕하세요!</h3>
                <p className="text-sm text-[var(--color-text-secondary)]">AI 매물 상담사가 도와드릴게요</p>
              </div>

              {/* 추천 질문 버튼 */}
              <div className="flex flex-wrap gap-3 justify-center max-w-md">
                <button
                  onClick={async () => {
                    const question = '강남 원룸 추천해줘';

                    let sessionId = currentSessionId;
                    if (!sessionId) {
                      sessionId = Date.now().toString();
                      const newSession: ChatSession = {
                        id: sessionId,
                        title: '새 대화',
                        messages: [],
                        createdAt: new Date(),
                        updatedAt: new Date(),
                      };
                      setSessions(prev => [newSession, ...prev]);
                      setCurrentSessionId(sessionId);
                    }

                    const userMessage: Message = {
                      id: Date.now().toString(),
                      type: 'user',
                      content: question,
                      timestamp: new Date(),
                    };

                    setMessages(prev => [...prev, userMessage]);
                    setIsLoading(true);

                    try {
                      const answer = await sendChatQuestion(question, sessionId);
                      const aiMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        type: 'ai',
                        content: answer,
                        timestamp: new Date(),
                      };
                      setMessages(prev => [...prev, aiMessage]);

                      if (onRecommendLands) {
                        const landIds = [...answer.matchAll(/\/landDetail\/(\d+)/g)]
                          .map(match => Number(match[1]))
                          .filter(Boolean);
                        if (landIds.length > 0) {
                          onRecommendLands(landIds);
                        }
                      }
                    } catch (error) {
                      setMessages(prev => [
                        ...prev,
                        {
                          id: (Date.now() + 2).toString(),
                          type: 'ai',
                          content: '응답 중 오류가 발생했습니다. 다시 시도해주세요.',
                          timestamp: new Date(),
                        },
                      ]);
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                  className="px-4 py-2 bg-white border-2 border-purple-200 text-purple-600 rounded-full text-sm font-medium hover:bg-purple-50 hover:border-purple-300 transition-all shadow-sm"
                >
                  강남 원룸 추천해줘
                </button>
                <button
                  onClick={async () => {
                    const question = '전세 매물 알려줘';

                    let sessionId = currentSessionId;
                    if (!sessionId) {
                      sessionId = Date.now().toString();
                      const newSession: ChatSession = {
                        id: sessionId,
                        title: '새 대화',
                        messages: [],
                        createdAt: new Date(),
                        updatedAt: new Date(),
                      };
                      setSessions(prev => [newSession, ...prev]);
                      setCurrentSessionId(sessionId);
                    }

                    const userMessage: Message = {
                      id: Date.now().toString(),
                      type: 'user',
                      content: question,
                      timestamp: new Date(),
                    };

                    setMessages(prev => [...prev, userMessage]);
                    setIsLoading(true);

                    try {
                      const answer = await sendChatQuestion(question, sessionId);
                      const aiMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        type: 'ai',
                        content: answer,
                        timestamp: new Date(),
                      };
                      setMessages(prev => [...prev, aiMessage]);

                      if (onRecommendLands) {
                        const landIds = [...answer.matchAll(/\/landDetail\/(\d+)/g)]
                          .map(match => Number(match[1]))
                          .filter(Boolean);
                        if (landIds.length > 0) {
                          onRecommendLands(landIds);
                        }
                      }
                    } catch (error) {
                      setMessages(prev => [
                        ...prev,
                        {
                          id: (Date.now() + 2).toString(),
                          type: 'ai',
                          content: '응답 중 오류가 발생했습니다. 다시 시도해주세요.',
                          timestamp: new Date(),
                        },
                      ]);
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                  className="px-4 py-2 bg-white border-2 border-purple-200 text-purple-600 rounded-full text-sm font-medium hover:bg-purple-50 hover:border-purple-300 transition-all shadow-sm"
                >
                  전세 매물 알려줘
                </button>
                <button
                  onClick={async () => {
                    const question = '교통 좋은 곳 어디야?';

                    let sessionId = currentSessionId;
                    if (!sessionId) {
                      sessionId = Date.now().toString();
                      const newSession: ChatSession = {
                        id: sessionId,
                        title: '새 대화',
                        messages: [],
                        createdAt: new Date(),
                        updatedAt: new Date(),
                      };
                      setSessions(prev => [newSession, ...prev]);
                      setCurrentSessionId(sessionId);
                    }

                    const userMessage: Message = {
                      id: Date.now().toString(),
                      type: 'user',
                      content: question,
                      timestamp: new Date(),
                    };

                    setMessages(prev => [...prev, userMessage]);
                    setIsLoading(true);

                    try {
                      const answer = await sendChatQuestion(question, sessionId);
                      const aiMessage: Message = {
                        id: (Date.now() + 1).toString(),
                        type: 'ai',
                        content: answer,
                        timestamp: new Date(),
                      };
                      setMessages(prev => [...prev, aiMessage]);

                      if (onRecommendLands) {
                        const landIds = [...answer.matchAll(/\/landDetail\/(\d+)/g)]
                          .map(match => Number(match[1]))
                          .filter(Boolean);
                        if (landIds.length > 0) {
                          onRecommendLands(landIds);
                        }
                      }
                    } catch (error) {
                      setMessages(prev => [
                        ...prev,
                        {
                          id: (Date.now() + 2).toString(),
                          type: 'ai',
                          content: '응답 중 오류가 발생했습니다. 다시 시도해주세요.',
                          timestamp: new Date(),
                        },
                      ]);
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                  className="px-4 py-2 bg-white border-2 border-purple-200 text-purple-600 rounded-full text-sm font-medium hover:bg-purple-50 hover:border-purple-300 transition-all shadow-sm"
                >
                  교통 좋은 곳 어디야?
                </button>
              </div>
            </div>
          ) : (
            /* 기존 메시지 표시 */
            <>
              {messages.map(message => (
                <div key={message.id}>
                  {message.type === 'user' ? (
                    /* 사용자 메시지 */
                    <div className="flex justify-end">
                      <div className="max-w-[75%] p-4 rounded-lg bg-sky-100 text-gray-900">
                        <p className="text-sm whitespace-pre-wrap break-words">
                          {message.content}
                        </p>
                        <p className="text-xs mt-2 text-gray-500">
                          {formatTime(message.timestamp)}
                        </p>
                      </div>
                    </div>
                  ) : (
                    /* AI 메시지 - 순위별 개별 말풍선 */
                    (() => {
                      const { mainContent, questions } = extractSuggestedQuestions(message.content);
                      return (
                        <div className="space-y-3">
                          {parseRankedContent(mainContent).map((part, partIndex, arr) => {
                            const colors = part.rank
                              ? (rankColors[part.rank] || defaultRankColor)
                              : { bg: 'bg-gray-100', border: '', badge: '' };

                            return (
                              <div key={`${message.id}-${partIndex}`} className="flex justify-start">
                                <div className={`w-[85%] p-4 rounded-lg ${colors.bg} ${colors.border}`}>
                                  {part.rank && (
                                    <div className="flex items-center gap-2 mb-2">
                                      <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${colors.badge}`} style={{ color: '#ffffff' }}>
                                        {part.rank === 1 && '🥇 '}
                                        {part.rank === 2 && '🥈 '}
                                        {part.rank === 3 && '🥉 '}
                                        {part.rank}위
                                      </span>
                                    </div>
                                  )}
                                  <div className="prose prose-sm max-w-none text-gray-900">
                                    <ReactMarkdown
                                      components={{
                                        a: ({ href, children }) => {
                                          const text = String(children);
                                          if (text.includes('상세보기')) {
                                            return (
                                              <div className="flex justify-end mt-3 not-prose">
                                                <a
                                                  href={href}
                                                  className="font-bold text-black-600 hover:text-black-800 hover:underline"
                                                >
                                                  {children}
                                                </a>
                                              </div>
                                            );
                                          }
                                          return (
                                            <a href={href} className="text-black-600 hover:underline">
                                              {children}
                                            </a>
                                          );
                                        },
                                      }}
                                    >
                                      {part.content}
                                    </ReactMarkdown>
                                  </div>
                                  {partIndex === arr.length - 1 && questions.length === 0 && (
                                    <p className="text-xs mt-2 text-gray-500">
                                      {formatTime(message.timestamp)}
                                    </p>
                                  )}
                                </div>
                              </div>
                            );
                          })}

                          {/* 추가질문 섹션 - 별도 말풍선, 2열 그리드 */}
                          {questions.length > 0 && (
                            <div className="flex justify-start">
                              <div className="w-[85%] p-4 rounded-lg bg-purple-50 border-l-4 border-purple-400">
                                <div className="flex items-center gap-2 mb-3">
                                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-purple-400 text-white" style={{ color: '#ffffff' }}>
                                    💡 추가질문
                                  </span>
                                </div>
                                <div className="grid grid-cols-2 gap-2">
                                  {questions.map((question, qIndex) => (
                                    <button
                                      key={qIndex}
                                      onClick={async () => {
                                        // 바로 질문 전송
                                        const sessionId = currentSessionId || Date.now().toString();
                                        if (!currentSessionId) {
                                          const newSession: ChatSession = {
                                            id: sessionId,
                                            title: '새 대화',
                                            messages: [],
                                            createdAt: new Date(),
                                            updatedAt: new Date(),
                                          };
                                          setSessions(prev => [newSession, ...prev]);
                                          setCurrentSessionId(sessionId);
                                        }

                                        const userMessage: Message = {
                                          id: Date.now().toString(),
                                          type: 'user',
                                          content: question,
                                          timestamp: new Date(),
                                        };

                                        setMessages(prev => [...prev, userMessage]);
                                        setIsLoading(true);

                                        try {
                                          const answer = await sendChatQuestion(question, sessionId);
                                          const aiMessage: Message = {
                                            id: (Date.now() + 1).toString(),
                                            type: 'ai',
                                            content: answer,
                                            timestamp: new Date(),
                                          };
                                          setMessages(prev => [...prev, aiMessage]);

                                          if (onRecommendLands) {
                                            const landIds = [...answer.matchAll(/\/landDetail\/(\d+)/g)]
                                              .map(match => Number(match[1]))
                                              .filter(Boolean);
                                            if (landIds.length > 0) {
                                              onRecommendLands(landIds);
                                            }
                                          }
                                        } catch (error) {
                                          setMessages(prev => [
                                            ...prev,
                                            {
                                              id: (Date.now() + 2).toString(),
                                              type: 'ai',
                                              content: '응답 중 오류가 발생했습니다. 다시 시도해주세요.',
                                              timestamp: new Date(),
                                            },
                                          ]);
                                        } finally {
                                          setIsLoading(false);
                                        }
                                      }}
                                      className="text-left px-3 py-2 bg-white border border-purple-200 rounded-lg text-sm text-purple-700 hover:bg-purple-100 hover:border-purple-300 transition-colors"
                                    >
                                      {question}
                                    </button>
                                  ))}
                                </div>
                                <p className="text-xs mt-3 text-gray-500">
                                  {formatTime(message.timestamp)}
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })()
                  )}
                </div>
              ))}


              {isLoading && (
                <p className="text-sm text-gray-400">AI가 답변을 생성 중입니다...</p>
              )}
            </>
          )}
        </div>

        {/* 입력 영역 */}
        <div className="p-4 border-t flex gap-2">
          <input
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 border rounded px-3 py-2 text-sm"
            placeholder="궁금한 매물 정보를 물어보세요"
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50 text-sm"
          >
            전송
          </button>
        </div>
      </div>

      {/* 과거 대화 모달 */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-md"
            onClick={() => setShowHistoryModal(false)}
          />
          <div className="relative bg-white rounded-xl shadow-[var(--shadow-xl)] w-full max-w-2xl max-h-[80vh] flex flex-col z-[10000]">
            <div className="flex items-center justify-between p-6 border-b">
              <h3 className="text-xl font-semibold text-[var(--color-primary)]">
                과거 대화 내역
              </h3>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="p-2 hover:bg-[var(--color-bg-hover)] rounded-lg transition-colors"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M18 6L6 18M6 6L18 18"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>
            <div className="p-6 overflow-y-auto">
              {sessions.length === 0 ? (
                <p className="text-sm text-[var(--color-text-tertiary)] text-center py-8">
                  저장된 대화가 없습니다
                </p>
              ) : (
                <div className="space-y-3">
                  {sessions.map(session => (
                    <div
                      key={session.id}
                      onClick={() => handleSelectSession(session.id)}
                      className={`p-4 rounded-lg cursor-pointer transition-colors border ${currentSessionId === session.id
                        ? 'bg-blue-50 border-[var(--color-primary)]'
                        : 'bg-white hover:bg-[var(--color-bg-hover)] border-[var(--color-border-light)]'
                        }`}
                    >
                      <div className="flex justify-between items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                            {session.title}
                          </p>
                          <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                            {formatDate(session.updatedAt)}
                          </p>
                        </div>
                        <button
                          onClick={e => handleDeleteSession(session.id, e)}
                          className="flex-shrink-0 text-[var(--color-text-tertiary)] hover:text-red-600 transition-colors p-1"
                        >
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )
      }
    </>
  )
}
