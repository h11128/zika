"""
Code version management for cache keys and logging.
Generates deterministic, environment-specific version strings.
"""

import os
import subprocess
import logging
from datetime import datetime
from typing import Optional
from functools import lru_cache


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_code_version() -> str:
    """
    Get code version based on environment with fallback strategy.
    
    Returns:
        Environment-specific version string:
        - Development: dev-{short_sha}-{YYYYMMDDHHMMSS}[-dirty]
        - CI: ci-{BUILD_NUMBER}-{short_sha} (fallback to {short_sha})
        - Production: v{semver} or v{semver}+build.{build_number}
    """
    # Check for explicit version override (useful for testing)
    override_version = os.environ.get('ZIKA_CODE_VERSION')
    if override_version:
        logger.debug(f"Using override code version: {override_version}")
        return override_version
    
    # Detect environment
    environment = _detect_environment()
    
    if environment == 'production':
        return _get_production_version()
    elif environment == 'ci':
        return _get_ci_version()
    else:  # development
        return _get_development_version()


def _detect_environment() -> str:
    """Detect current environment based on environment variables."""
    # Check for explicit production indicators first (highest priority)
    if os.environ.get('ENVIRONMENT') == 'production' or os.environ.get('NODE_ENV') == 'production':
        return 'production'

    # Check for CI environment indicators
    ci_indicators = [
        'CI', 'CONTINUOUS_INTEGRATION',
        'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL'
    ]

    # BUILD_NUMBER alone doesn't indicate CI if we're explicitly in production
    if any(os.environ.get(indicator) for indicator in ci_indicators):
        return 'ci'

    # BUILD_NUMBER without explicit production indicator suggests CI
    if os.environ.get('BUILD_NUMBER') and not os.environ.get('ENVIRONMENT'):
        return 'ci'

    # Default to development
    return 'development'


def _get_production_version() -> str:
    """Get production version from semantic version or build metadata."""
    # Try semantic version from environment
    semver = os.environ.get('RELEASE_VERSION') or os.environ.get('VERSION')
    if semver:
        # Clean up version string (remove 'v' prefix if present)
        if semver.startswith('v'):
            semver = semver[1:]
        
        # Add build number if available
        build_number = os.environ.get('BUILD_NUMBER')
        if build_number:
            return f"v{semver}+build.{build_number}"
        else:
            return f"v{semver}"
    
    # Fallback to git tag or SHA
    git_version = _get_git_version()
    if git_version:
        return f"v{git_version}"
    
    # Ultimate fallback
    return "v1.0.0-unknown"


def _get_ci_version() -> str:
    """Get CI version with build number and git SHA."""
    build_number = os.environ.get('BUILD_NUMBER') or os.environ.get('GITHUB_RUN_NUMBER')
    git_sha = _get_git_sha()
    
    if build_number and git_sha:
        return f"ci-{build_number}-{git_sha}"
    elif git_sha:
        return git_sha
    else:
        # Fallback with timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"ci-unknown-{timestamp}"


def _get_development_version() -> str:
    """Get development version with git SHA and timestamp."""
    git_sha = _get_git_sha()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    
    if git_sha:
        # Check if working tree is dirty
        is_dirty = _is_git_dirty()
        dirty_suffix = '-dirty' if is_dirty else ''
        return f"dev-{git_sha}-{timestamp}{dirty_suffix}"
    else:
        # No git available, use timestamp only
        return f"dev-nogit-{timestamp}"


def _get_git_sha(short: bool = True) -> Optional[str]:
    """Get current git SHA."""
    try:
        cmd = ['git', 'rev-parse', '--short' if short else '', 'HEAD']
        cmd = [arg for arg in cmd if arg]  # Remove empty strings
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.dirname(__file__))  # Project root
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.debug(f"Git command failed: {result.stderr}")
            return None
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug(f"Failed to get git SHA: {e}")
        return None


def _get_git_version() -> Optional[str]:
    """Get git version from tags."""
    try:
        # Try to get the latest tag
        result = subprocess.run(
            ['git', 'describe', '--tags', '--exact-match', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        if result.returncode == 0:
            tag = result.stdout.strip()
            # Remove 'v' prefix if present
            if tag.startswith('v'):
                tag = tag[1:]
            return tag
        else:
            return None
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug(f"Failed to get git version: {e}")
        return None


def _is_git_dirty() -> bool:
    """Check if git working tree has uncommitted changes."""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
        
        if result.returncode == 0:
            # If output is not empty, working tree is dirty
            return bool(result.stdout.strip())
        else:
            return False
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug(f"Failed to check git status: {e}")
        return False


def get_version_info() -> dict:
    """
    Get detailed version information for debugging.
    
    Returns:
        Dictionary with version details
    """
    return {
        'code_version': get_code_version(),
        'environment': _detect_environment(),
        'git_sha': _get_git_sha(short=False),
        'git_sha_short': _get_git_sha(short=True),
        'git_dirty': _is_git_dirty(),
        'git_version': _get_git_version(),
        'build_number': os.environ.get('BUILD_NUMBER'),
        'timestamp': datetime.now().isoformat(),
    }


def clear_version_cache():
    """Clear the cached version (useful for testing)."""
    get_code_version.cache_clear()
