import time
import sys
import os
from neo4j import GraphDatabase
import psycopg2


class DatabaseHealthCheck:
    """데이터베이스 연결 검증 및 헬스체크 유틸리티"""
    
    @staticmethod
    def wait_for_neo4j(uri, user, password, max_retries=10, base_delay=2):
        """
        Neo4j 연결을 지수 백오프로 재시도
        
        Args:
            uri: Neo4j 연결 URI
            user: Neo4j 사용자명
            password: Neo4j 비밀번호
            max_retries: 최대 재시도 횟수
            base_delay: 기본 대기 시간 (초)
        
        Returns:
            bool: 연결 성공 시 True, 실패 시 프로그램 종료
        """
        print(f"Neo4j 연결 확인 중: {uri}")
        
        for attempt in range(max_retries):
            try:
                # 연결 타임아웃 30초로 증가
                driver = GraphDatabase.driver(
                    uri, 
                    auth=(user, password),
                    connection_timeout=30,  # 30초 타임아웃
                    max_connection_lifetime=3600
                )
                driver.verify_connectivity()
                driver.close()
                print(f"✓ Neo4j 연결 성공: {uri}")
                return True
            except Exception as e:
                # 최대 30초까지만 대기
                delay = min(base_delay * (2 ** attempt), 30)
                print(f"Neo4j 연결 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"  {delay}초 후 재시도...")
                    time.sleep(delay)
        
        print(f"\n✗ Neo4j 연결 실패: 최대 재시도 횟수 초과")
        print(f"  연결 URL 확인: {uri}")
        print(f"  자격 증명 확인: 사용자={user}")
        print(f"  Neo4j 컨테이너가 실행 중인지 확인하세요: docker-compose ps")
        sys.exit(1)
    
    @staticmethod
    def wait_for_postgres(host, port, dbname, user, password, max_retries=10, base_delay=2):
        """
        PostgreSQL 연결을 지수 백오프로 재시도
        
        Args:
            host: PostgreSQL 호스트
            port: PostgreSQL 포트
            dbname: 데이터베이스 이름
            user: PostgreSQL 사용자명
            password: PostgreSQL 비밀번호
            max_retries: 최대 재시도 횟수
            base_delay: 기본 대기 시간 (초)
        
        Returns:
            bool: 연결 성공 시 True, 실패 시 프로그램 종료
        """
        print(f"PostgreSQL 연결 확인 중: {host}:{port}/{dbname}")
        
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(
                    dbname=dbname,
                    user=user,
                    password=password,
                    host=host,
                    port=port
                )
                conn.close()
                print(f"✓ PostgreSQL 연결 성공: {host}:{port}/{dbname}")
                return True
            except Exception as e:
                # 최대 30초까지만 대기
                delay = min(base_delay * (2 ** attempt), 30)
                print(f"PostgreSQL 연결 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"  {delay}초 후 재시도...")
                    time.sleep(delay)
        
        print(f"\n✗ PostgreSQL 연결 실패: 최대 재시도 횟수 초과")
        print(f"  연결 정보 확인: {host}:{port}")
        print(f"  데이터베이스: {dbname}")
        print(f"  사용자: {user}")
        print(f"  PostgreSQL 컨테이너가 실행 중인지 확인하세요: docker-compose ps")
        sys.exit(1)
    
    @staticmethod
    def wait_for_elasticsearch(host, port=9200, max_retries=10, base_delay=2):
        """
        Elasticsearch 연결을 지수 백오프로 재시도
        
        Args:
            host: Elasticsearch 호스트
            port: Elasticsearch 포트
            max_retries: 최대 재시도 횟수
            base_delay: 기본 대기 시간 (초)
        
        Returns:
            bool: 연결 성공 시 True, 실패 시 프로그램 종료
        """
        import urllib.request
        import urllib.error
        
        url = f"http://{host}:{port}/_cluster/health"
        print(f"Elasticsearch 연결 확인 중: {host}:{port}")
        
        for attempt in range(max_retries):
            try:
                req = urllib.request.urlopen(url, timeout=10)
                if req.status == 200:
                    print(f"✓ Elasticsearch 연결 성공: {host}:{port}")
                    return True
            except (urllib.error.URLError, Exception) as e:
                # 최대 30초까지만 대기
                delay = min(base_delay * (2 ** attempt), 30)
                print(f"Elasticsearch 연결 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"  {delay}초 후 재시도...")
                    time.sleep(delay)
        
        print(f"\n✗ Elasticsearch 연결 실패: 최대 재시도 횟수 초과")
        print(f"  연결 정보 확인: {host}:{port}")
        print(f"  Elasticsearch 컨테이너가 실행 중인지 확인하세요: docker-compose ps")
        raise ConnectionError(f"Elasticsearch 연결 실패: {host}:{port}")
