"""
Unit tests for API endpoints.

Tests all /api/* routes with mocked GitHub API calls.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from github import GithubException

# Import app for testing
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app


@pytest.fixture
def client():
    """Flask test client."""
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


class TestGetPods:
    """Tests for GET /api/pods"""

    @patch('app.list_all_pods')
    def test_get_pods_success(self, mock_list_pods, client):
        """Should return list of pods from list_all_pods()"""
        mock_list_pods.return_value = [
            {'customer': 'acme', 'env': 'dev'},
            {'customer': 'acme', 'env': 'prod'},
        ]

        response = client.get('/api/pods')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        assert data[0]['customer'] == 'acme'
        assert data[0]['env'] == 'dev'

    @patch('app.list_all_pods')
    def test_get_pods_github_error(self, mock_list_pods, client):
        """Should return 500 on GitHub API error"""
        mock_list_pods.side_effect = GithubException(500, 'API error', None)

        response = client.get('/api/pods')

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'GitHub' in data['error']


class TestGetPod:
    """Tests for GET /api/pod/<customer>/<env>"""

    @patch('app.fetch_spec')
    def test_get_pod_success(self, mock_fetch, client):
        """Should return parsed spec for valid pod"""
        mock_fetch.return_value = {
            'metadata': {'customer': 'acme', 'environment': 'dev'},
            'spec': {'compute': {'instance_name': 'acme-dev-web'}}
        }

        response = client.get('/api/pod/acme/dev')

        assert response.status_code == 200
        data = response.get_json()
        assert data['metadata']['customer'] == 'acme'
        assert 'spec' in data

    @patch('app.fetch_spec')
    def test_get_pod_not_found(self, mock_fetch, client):
        """Should return 404 for non-existent pod"""
        mock_fetch.return_value = None

        response = client.get('/api/pod/nonexistent/dev')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    def test_get_pod_invalid_customer(self, client):
        """Should return 400 for invalid customer name"""
        response = client.get('/api/pod/INVALID!/dev')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    @patch('app.fetch_spec')
    def test_get_pod_github_404(self, mock_fetch, client):
        """Should return 404 when GitHub returns 404"""
        mock_fetch.side_effect = GithubException(404, 'Not found', None)

        response = client.get('/api/pod/acme/dev')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data


class TestCreatePod:
    """Tests for POST /api/pod"""

    @patch('api.helpers.create_pod_deployment')
    @patch('app.generate_spec_yaml')
    def test_create_pod_success(self, mock_generate, mock_deploy, client):
        """Should create branch and PR for valid pod"""
        mock_generate.return_value = 'metadata:\n  customer: acme\n'
        mock_deploy.return_value = {
            'branch': 'deploy-acme-dev-123456',
            'pr_url': 'https://github.com/test/repo/pull/1',
            'pr_number': 1
        }

        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev',
            'spec': {
                'instance_name': 'acme-dev-web',
                'waf_enabled': True
            }
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'branch' in data
        assert 'pr_url' in data
        assert data['pr_number'] == 1

    def test_create_pod_missing_customer(self, client):
        """Should return 400 if customer missing"""
        response = client.post('/api/pod', json={
            'env': 'dev',
            'spec': {'instance_name': 'test'}
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'customer' in data['error'].lower()

    def test_create_pod_missing_env(self, client):
        """Should return 400 if env missing"""
        response = client.post('/api/pod', json={
            'customer': 'acme',
            'spec': {'instance_name': 'test'}
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'env' in data['error'].lower()

    def test_create_pod_missing_spec(self, client):
        """Should return 400 if spec missing"""
        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'spec' in data['error'].lower()

    def test_create_pod_missing_instance_name(self, client):
        """Should return 400 if instance_name missing from spec"""
        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev',
            'spec': {'waf_enabled': True}
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'instance_name' in data['error'].lower()

    def test_create_pod_invalid_json(self, client):
        """Should return 400 for invalid JSON"""
        response = client.post(
            '/api/pod',
            data='not json',
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_pod_invalid_customer_format(self, client):
        """Should return 400 for invalid customer format"""
        response = client.post('/api/pod', json={
            'customer': 'invalid!@#',
            'env': 'dev',
            'spec': {'instance_name': 'test-web'}
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_create_pod_invalid_instance_name(self, client):
        """Should return 400 for invalid instance_name format"""
        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev',
            'spec': {'instance_name': 'INVALID_NAME'}  # Uppercase not allowed
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    @patch('api.helpers.create_pod_deployment')
    @patch('app.generate_spec_yaml')
    def test_create_pod_github_error(self, mock_generate, mock_deploy, client):
        """Should return 500 on GitHub API error"""
        mock_generate.return_value = 'metadata:\n  customer: acme\n'
        mock_deploy.side_effect = GithubException(500, 'API error', None)

        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev',
            'spec': {'instance_name': 'acme-dev-web'}
        })

        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data

    @patch('api.helpers.create_pod_deployment')
    @patch('app.generate_spec_yaml')
    def test_create_pod_with_commit_message(self, mock_generate, mock_deploy, client):
        """Should pass custom commit message to deployment"""
        mock_generate.return_value = 'metadata:\n  customer: acme\n'
        mock_deploy.return_value = {
            'branch': 'deploy-acme-dev-123456',
            'pr_url': 'https://github.com/test/repo/pull/1',
            'pr_number': 1
        }

        response = client.post('/api/pod', json={
            'customer': 'acme',
            'env': 'dev',
            'spec': {'instance_name': 'acme-dev-web'},
            'commit_message': 'Custom deployment message'
        })

        assert response.status_code == 200
        # Verify commit_message was passed to create_pod_deployment
        mock_deploy.assert_called_once()
        call_args = mock_deploy.call_args
        assert call_args[0][4] == 'Custom deployment message'  # 5th positional arg


class TestHealthEndpoint:
    """Tests for GET /health (existing endpoint, verify JSON format)"""

    @patch('app.repo')
    @patch('app.github')
    def test_health_success(self, mock_github, mock_repo, client):
        """Should return healthy status with GitHub info"""
        # Mock GitHub connectivity check
        mock_repo.get_contents.return_value = Mock()

        # Mock rate limit
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 5000
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890
        mock_github.get_rate_limit.return_value = mock_rate_limit

        # Mock workflows
        mock_workflows = Mock()
        mock_workflows.totalCount = 1
        mock_repo.get_workflows.return_value = mock_workflows

        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert 'github' in data

    @patch('app.repo')
    @patch('app.github')
    def test_health_github_error(self, mock_github, mock_repo, client):
        """Should return unhealthy status on GitHub error"""
        # Mock GitHub connectivity failure
        mock_repo.get_contents.side_effect = Exception('Connection failed')

        response = client.get('/health')

        assert response.status_code == 503
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'unhealthy'
        assert 'error' in data
