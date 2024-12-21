#!/usr/bin/env python3
"""
API Documentation Crawler

This script crawls API documentation sites to find or generate OpenAPI specifications.
It either finds an existing openapi.json file or crawls the documentation pages
to build an OpenAPI specification from the content.
"""

import asyncio
import json
import sys
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup
import requests


class APICrawler:
    def __init__(self, base_url: str):
        """Initialize the crawler with a base URL to crawl."""
        self.base_url = base_url
        self.visited_urls: Set[str] = set()
        self.api_docs: Dict[str, dict] = {}
        
    async def find_openapi_json(self) -> Optional[dict]:
        """
        Check if openapi.json exists at common locations.
        Returns the OpenAPI spec if found, None otherwise.
        """
        common_paths = [
            'openapi.json',
            'swagger.json',
            'api/openapi.json',
            'api/swagger.json',
            'docs/openapi.json',
            'docs/swagger.json',
            '.well-known/openapi.json',
            'api-docs/openapi.json',
            'api-docs/swagger.json'
        ]
        
        async with aiohttp.ClientSession() as session:
            for path in common_paths:
                try:
                    url = urljoin(self.base_url, path)
                    async with session.get(url) as response:
                        if response.status == 200:
                            try:
                                spec = await response.json()
                                # Basic validation that it's an OpenAPI spec
                                if isinstance(spec, dict) and (
                                    'openapi' in spec or 'swagger' in spec
                                ):
                                    return spec
                            except json.JSONDecodeError:
                                continue
                except aiohttp.ClientError:
                    continue
                    
            return None
        
    async def crawl_subpages(self) -> List[str]:
        """
        Crawl subpages of the documentation site to find API documentation pages.
        Returns a list of URLs that appear to be API documentation.
        """
        api_doc_urls = []
        to_visit = {self.base_url}
        base_domain = urlparse(self.base_url).netloc
        
        async with aiohttp.ClientSession() as session:
            while to_visit:
                current_urls = to_visit.copy()
                to_visit.clear()
                
                # Process URLs in parallel
                tasks = []
                for url in current_urls:
                    if url not in self.visited_urls:
                        self.visited_urls.add(url)
                        tasks.append(self.process_page(session, url, to_visit, base_domain))
                
                # Wait for all tasks to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Filter out exceptions and add API doc URLs
                for result in results:
                    if isinstance(result, str) and result:
                        api_doc_urls.append(result)
        
        return api_doc_urls
        
    async def process_page(
        self, 
        session: aiohttp.ClientSession, 
        url: str, 
        to_visit: Set[str], 
        base_domain: str
    ) -> Optional[str]:
        """Process a single page: extract links and determine if it's an API doc."""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                    
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type.lower():
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract all links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    
                    # Only follow links on the same domain
                    if (
                        urlparse(absolute_url).netloc == base_domain
                        and absolute_url not in self.visited_urls
                    ):
                        to_visit.add(absolute_url)
                
                # Check if this page is an API documentation
                if self.is_api_doc_page(soup):
                    return url
                    
                return None
                    
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
            
    def is_api_doc_page(self, soup: BeautifulSoup) -> bool:
        """
        Determine if a page is likely an API documentation page.
        """
        # Look for common API documentation indicators
        api_indicators = {
            'endpoint', 'api reference', 'api documentation', 'rest api',
            'http request', 'http response', 'parameters', 'response body',
            'request body', 'authentication', 'authorization'
        }
        
        # Check page title
        title = soup.find('title')
        if title and any(indicator in title.text.lower() for indicator in api_indicators):
            return True
            
        # Check headings
        headings = soup.find_all(['h1', 'h2', 'h3'])
        for heading in headings:
            if any(indicator in heading.text.lower() for indicator in api_indicators):
                return True
                
        # Check for common API documentation elements
        if soup.find_all(['code', 'pre']):
            text_content = soup.get_text().lower()
            if any(indicator in text_content for indicator in api_indicators):
                return True
                
        return False
        
    async def parse_api_page(self, url: str) -> Optional[dict]:
        """
        Parse a single API documentation page to extract endpoint information.
        Returns a partial OpenAPI spec for the endpoints found on the page.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract endpoints from the page
                    endpoints = []
                    
                    # Look for common API endpoint patterns in code blocks
                    for code_block in soup.find_all(['code', 'pre']):
                        text = code_block.get_text()
                        # Look for HTTP method + path patterns
                        if any(method in text.upper() for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']):
                            endpoint = self.extract_endpoint_info(code_block)
                            if endpoint:
                                endpoints.append(endpoint)
                    
                    if not endpoints:
                        return None
                        
                    # Convert to OpenAPI format
                    paths = {}
                    for endpoint in endpoints:
                        method = endpoint['method'].lower()
                        path = endpoint['path']
                        
                        if path not in paths:
                            paths[path] = {}
                            
                        paths[path][method] = {
                            'summary': endpoint.get('summary', ''),
                            'description': endpoint.get('description', ''),
                            'parameters': endpoint.get('parameters', []),
                            'responses': {
                                '200': {
                                    'description': 'Successful response',
                                    'content': endpoint.get('response', {})
                                }
                            }
                        }
                    
                    return {
                        'paths': paths
                    }
                    
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
            
    def extract_endpoint_info(self, code_block: BeautifulSoup) -> Optional[dict]:
        """
        Extract endpoint information from a code block.
        Returns a dictionary with method, path, and other endpoint details.
        """
        text = code_block.get_text()
        
        # Try to find HTTP method and path
        for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            if method in text.upper():
                # Look for path pattern after HTTP method
                lines = text.split('\n')
                for line in lines:
                    if method in line.upper():
                        # Extract path - look for pattern like "GET /api/v1/users"
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            path_part = parts[1]
                            # Clean up path - remove query parameters
                            path = path_part.split('?')[0]
                            
                            # Look for description in surrounding text
                            parent = code_block.parent
                            description = ''
                            if parent:
                                # Look for nearby paragraph or heading
                                prev_elem = parent.find_previous(['p', 'h1', 'h2', 'h3', 'h4'])
                                if prev_elem:
                                    description = prev_elem.get_text().strip()
                            
                            # Extract parameters from path
                            parameters = []
                            path_params = [p for p in path.split('/') if '{' in p and '}' in p]
                            for param in path_params:
                                param_name = param.strip('{}')
                                parameters.append({
                                    'name': param_name,
                                    'in': 'path',
                                    'required': True,
                                    'schema': {'type': 'string'}
                                })
                            
                            return {
                                'method': method,
                                'path': path,
                                'summary': description[:50] + '...' if len(description) > 50 else description,
                                'description': description,
                                'parameters': parameters,
                                'response': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object'
                                        }
                                    }
                                }
                            }
                            
        return None
        
    def combine_specs(self) -> dict:
        """
        Combine all the partial OpenAPI specs into a single complete specification.
        """
        combined_paths = {}
        
        # Merge all paths from individual specs
        for spec in self.api_docs.values():
            if not spec or 'paths' not in spec:
                continue
                
            for path, methods in spec['paths'].items():
                if path not in combined_paths:
                    combined_paths[path] = {}
                    
                # Merge methods for this path
                for method, operation in methods.items():
                    if method in combined_paths[path]:
                        # If method already exists, merge the operations
                        existing_op = combined_paths[path][method]
                        # Merge parameters
                        existing_params = {
                            (p.get('name', ''), p.get('in', ''))
                            for p in existing_op.get('parameters', [])
                        }
                        for param in operation.get('parameters', []):
                            param_key = (param.get('name', ''), param.get('in', ''))
                            if param_key not in existing_params:
                                existing_op.setdefault('parameters', []).append(param)
                    else:
                        # New method for this path
                        combined_paths[path][method] = operation
        
        # Create the final OpenAPI spec
        return {
            'openapi': '3.0.0',
            'info': {
                'title': 'API Documentation',
                'version': '1.0.0',
                'description': f'API documentation crawled from {self.base_url}'
            },
            'paths': combined_paths
        }
        
    async def crawl(self) -> dict:
        """
        Main crawling method that orchestrates the entire process.
        Returns the final OpenAPI specification.
        """
        # Try to find existing openapi.json first
        if spec := await self.find_openapi_json():
            return spec
            
        # If no openapi.json found, crawl and parse the documentation
        doc_urls = await self.crawl_subpages()
        for url in doc_urls:
            if spec := await self.parse_api_page(url):
                self.api_docs[url] = spec
                
        return self.combine_specs()


async def main(url: str) -> dict:
    """
    Main entry point for the crawler.
    
    Args:
        url: The URL of the API documentation site to crawl
        
    Returns:
        dict: The OpenAPI specification, either found or generated
    """
    crawler = APICrawler(url)
    return await crawler.crawl()


def save_to_provider_library(url: str, openapi_spec: dict, library_path: str = "api_provider_library") -> None:
    """
    Save the OpenAPI specification to the API provider library.
    Creates a structured storage with metadata for quick indexing.
    
    Args:
        url: The documentation site URL
        openapi_spec: The OpenAPI specification dictionary
        library_path: Directory to store the API provider library
    """
    import os
    from datetime import datetime
    
    # Create library directory if it doesn't exist
    os.makedirs(library_path, exist_ok=True)
    
    # Generate a URL-based filename
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{domain}_{timestamp}"
    
    # Save the OpenAPI spec
    spec_path = os.path.join(library_path, f"{filename}_openapi.json")
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
    
    # Create metadata for quick indexing
    metadata = {
        "name": openapi_spec.get("info", {}).get("title", "API Documentation"),
        "description": openapi_spec.get("info", {}).get("description", ""),
        "doc_url": url,
        "version": openapi_spec.get("info", {}).get("version", "1.0.0"),
        "timestamp": timestamp,
        "endpoints_count": sum(
            len(methods) for methods in openapi_spec.get("paths", {}).values()
        ),
        "spec_file": f"{filename}_openapi.json"
    }
    
    # Save metadata
    index_path = os.path.join(library_path, "index.json")
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        index = {"apis": []}
    
    index["apis"].append(metadata)
    
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"API documentation saved to {spec_path}")
    print(f"API metadata indexed in {index_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python crawler.py <documentation_site_url>")
        sys.exit(1)
        
    input_url = sys.argv[1]
    
    # Run the crawler
    openapi_spec = asyncio.run(main(input_url))
    
    # Save to provider library
    save_to_provider_library(input_url, openapi_spec)
    
    # Also output to stdout for debugging
    print("\nGenerated OpenAPI Specification:")
    print(json.dumps(openapi_spec, indent=2, ensure_ascii=False))
