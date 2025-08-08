"""
ヘルスチェックエンドポイントのテスト
"""
import pytest
from src.web.app import ApplicationFactory

@pytest.fixture
def app():
    """テスト用Flaskアプリケーション"""
    app = ApplicationFactory.create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture 
def client(app):
    """テスト用クライアント"""
    return app.test_client()

def test_health_endpoint(client):
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'database' in data

def test_healthz_endpoint(client):
    """ヘルスチェックエンドポイント (/healthz) のテスト"""
    response = client.get('/healthz')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data

def test_ping_endpoint(client):
    """pingエンドポイントのテスト"""
    response = client.get('/ping')
    assert response.status_code == 200
    assert response.data == b'pong'

def test_home_page(client):
    """トップページのテスト"""
    response = client.get('/')
    assert response.status_code == 200