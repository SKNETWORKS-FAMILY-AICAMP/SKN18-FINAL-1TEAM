#!/usr/bin/env python
"""
AWS environment PostgreSQL and Elasticsearch connection test
"""
import os
import sys
import psycopg2
import urllib.request
from dotenv import load_dotenv

load_dotenv()

def test_postgresql():
    """PostgreSQL connection test"""
    print("\n" + "=" * 70)
    print(" " * 20 + "PostgreSQL Connection Test")
    print("=" * 70)
    
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {dbname}")
    print(f"User: {user}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        table_count = cursor.fetchone()[0]
        
        print(f"\nPostgreSQL Connection SUCCESS!")
        print(f"Version: {version[:50]}...")
        print(f"Table count: {table_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\nPostgreSQL Connection FAILED: {e}")
        return False


def test_elasticsearch():
    """Elasticsearch connection test"""
    print("\n" + "=" * 70)
    print(" " * 20 + "Elasticsearch Connection Test")
    print("=" * 70)
    
    host = os.getenv("ES_HOST", os.getenv("ELASTICSEARCH_HOST"))
    port = os.getenv("ES_PORT", os.getenv("ELASTICSEARCH_PORT", "9200"))
    
    url = f"http://{host}:{port}"
    print(f"URL: {url}")
    
    try:
        health_url = f"{url}/_cluster/health"
        req = urllib.request.urlopen(health_url, timeout=10)
        
        if req.status == 200:
            import json
            health_data = json.loads(req.read().decode())
            
            print(f"\nElasticsearch Connection SUCCESS!")
            print(f"Cluster name: {health_data.get('cluster_name')}")
            print(f"Status: {health_data.get('status')}")
            print(f"Node count: {health_data.get('number_of_nodes')}")
            
            indices_url = f"{url}/_cat/indices?format=json"
            indices_req = urllib.request.urlopen(indices_url, timeout=10)
            indices_data = json.loads(indices_req.read().decode())
            
            print(f"Index count: {len(indices_data)}")
            if indices_data:
                print("Indices:")
                for idx in indices_data[:5]:
                    print(f"  - {idx.get('index')} (docs: {idx.get('docs.count')})")
            
            return True
        else:
            print(f"\nElasticsearch Connection FAILED: HTTP {req.status}")
            return False
            
    except Exception as e:
        print(f"\nElasticsearch Connection FAILED: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print(" " * 15 + "AWS Database Connection Test")
    print("=" * 70)
    
    results = {
        "PostgreSQL": test_postgresql(),
        "Elasticsearch": test_elasticsearch()
    }
    
    print("\n" + "=" * 70)
    print(" " * 20 + "Test Results Summary")
    print("=" * 70)
    
    for db, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{db}: {status}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\nAll database connections successful!")
        sys.exit(0)
    else:
        print("\nSome database connections failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
