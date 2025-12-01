"""Service initialization utilities."""

import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from dotenv import load_dotenv
from pydantic import HttpUrl
from openai import AzureOpenAI

from app.services.rubric_refinement_service import RubricRefinementService
from app.utils.env_var_util import get_str_var
from app.utils.llm_service import LLMService

logger = logging.getLogger(__name__)


def _extract_deployment_from_url(url_str: str) -> Optional[str]:
    """Extract deployment name from URL path."""
    parsed = urlparse(url_str)
    path_parts = [p for p in parsed.path.split('/') if p]
    if 'deployments' in path_parts:
        idx = path_parts.index('deployments')
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1]
    return None


def _build_llm_service_url(base_url: str, deployment_name: str, api_version: str) -> str:
    """Build URL format required by LLMService: base/openai/deployments/{name}?api-version=..."""
    parsed = urlparse(base_url.rstrip('/'))
    path = f'/openai/deployments/{deployment_name}'
    query_params = parse_qs(parsed.query)
    query_params['api-version'] = [api_version]
    return urlunparse((
        parsed.scheme, parsed.netloc, path,
        '', urlencode(query_params, doseq=True), ''
    ))


def _patch_llm_service_init():
    """Patch LLMService.__init__ to use base URL for AzureOpenAI client."""
    original_init = LLMService.__init__
    
    def patched_init(self, endpoint_url: HttpUrl, api_key: str):
        # Extract api-version from URL
        api_version = next(
            (param[1] for param in endpoint_url.query_params() if param[0] == "api-version"),
            None
        )
        if not api_version:
            raise ValueError("api-version is required in the endpoint URL")
        
        # Extract base URL (scheme + netloc only)
        parsed = urlparse(str(endpoint_url))
        base_url = urlunparse((parsed.scheme, parsed.netloc, '', '', '', '')).rstrip('/') + '/'
        
        # Extract deployment name from path
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) >= 3 and path_parts[0] == 'openai' and path_parts[1] == 'deployments':
            deployment_name = path_parts[2].split('?')[0]
        else:
            raise ValueError(f"Cannot extract deployment name from URL: {endpoint_url}")
        
        # Initialize with base URL only
        self.client = AzureOpenAI(api_version=api_version, azure_endpoint=base_url, api_key=api_key)
        self.deployment_name = deployment_name
    
    LLMService.__init__ = patched_init


def initialize_llm_service() -> bool:
    """Initialize the LLM service from environment variables."""
    try:
        load_dotenv()
        
        endpoint_url_str = get_str_var("AZURE_LLM_DEPLOYMENT_URL", allow_none=True)
        api_key = get_str_var("AZURE_LLM_DEPLOYMENT_KEY", allow_none=True)
        api_version = get_str_var("AZURE_OPENAI_API_VERSION", allow_none=True)
        deployment_name = get_str_var("AZURE_OPENAI_DEPLOYMENT_NAME", allow_none=True)
        
        if not endpoint_url_str or not api_key:
            missing = [k for k, v in [
                ("AZURE_LLM_DEPLOYMENT_URL", endpoint_url_str),
                ("AZURE_LLM_DEPLOYMENT_KEY", api_key)
            ] if not v]
            logger.error(f"Missing required environment variables: {', '.join(missing)}")
            return False
        
        # Extract or use deployment name
        final_deployment_name = deployment_name or _extract_deployment_from_url(endpoint_url_str)
        if not final_deployment_name:
            logger.error("Deployment name not found in URL or environment variables")
            return False
        
        if not api_version:
            logger.error("AZURE_OPENAI_API_VERSION is required")
            return False
        
        # Build URL for LLMService
        endpoint_url = HttpUrl(_build_llm_service_url(endpoint_url_str, final_deployment_name, api_version))
        
        # Patch LLMService to use base URL correctly
        _patch_llm_service_init()
        
        LLMService.init_singleton(endpoint_url, api_key)
        logger.info("LLMService initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize LLMService: {e}", exc_info=True)
        return False


def create_rubric_refinement_service() -> Optional[RubricRefinementService]:
    """Create and return a RubricRefinementService instance."""
    if LLMService.get_instance() is None:
        logger.error("LLMService must be initialized before creating RubricRefinementService")
        return None
    return RubricRefinementService()

