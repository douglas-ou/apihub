import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawler import APICrawler

class TestTaobaoAPICrawler(unittest.TestCase):
    """Test cases for Taobao API documentation crawling."""
    
    def setUp(self):
        """Set up test environment."""
        self.crawler = APICrawler()
        self.taobao_url = "https://open.taobao.com/api.htm?docId=46&docType=2"
        
    @patch('aiohttp.ClientSession.get')
    async def test_chinese_doc_detection(self, mock_get):
        """Test detection of Chinese API documentation."""
        mock_response = MagicMock()
        mock_response.text.return_value = """
        <html>
            <body>
                <h1>淘宝开放平台API文档</h1>
                <div>接口文档说明</div>
            </body>
        </html>
        """
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.crawler.is_api_doc_page(self.taobao_url)
        self.assertTrue(result, "Should detect Chinese API documentation")
        
    @patch('aiohttp.ClientSession.get')
    async def test_function_tools_parsing(self, mock_get):
        """Test function tools parsing with Tongyi Qianwen."""
        mock_response = MagicMock()
        mock_response.text.return_value = """
        <div class="api-content">
            <h2>taobao.item.get 获取单个商品详细信息</h2>
            <div class="params">
                <h3>请求参数</h3>
                <table>
                    <tr><td>num_iid</td><td>Number</td><td>必选</td></tr>
                    <tr><td>fields</td><td>String</td><td>可选</td></tr>
                </table>
            </div>
        </div>
        """
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Mock Tongyi Qianwen response
        mock_ai_response = {
            "tool_calls": [{
                "function": {
                    "name": "extract_api_info",
                    "arguments": {
                        "path": "/item/get",
                        "method": "GET",
                        "description": "获取单个商品详细信息",
                        "parameters": [
                            {"name": "num_iid", "type": "number", "required": True},
                            {"name": "fields", "type": "string", "required": False}
                        ]
                    }
                }
            }]
        }
        
        with patch('crawler.APICrawler.parse_with_ai') as mock_parse:
            mock_parse.return_value = mock_ai_response
            result = await self.crawler.parse_api_page(self.taobao_url)
            
            self.assertIn("paths", result)
            self.assertIn("/item/get", result["paths"])
            self.assertEqual(
                result["paths"]["/item/get"]["get"]["description"],
                "获取单个商品详细信息"
            )
            
    @patch('aiohttp.ClientSession.get')
    async def test_openapi_spec_generation(self, mock_get):
        """Test OpenAPI specification generation for Taobao API."""
        mock_response = MagicMock()
        mock_response.text.return_value = """
        <div class="api-list">
            <div class="api-item">
                <h2>taobao.item.get</h2>
                <p>获取单个商品详细信息</p>
            </div>
        </div>
        """
        mock_get.return_value.__aenter__.return_value = mock_response
        
        spec = await self.crawler.generate_openapi_spec(self.taobao_url)
        
        self.assertEqual(spec["openapi"], "3.0.0")
        self.assertIn("paths", spec)
        self.assertIn("info", spec)
        self.assertEqual(spec["info"]["title"], "Taobao Open API")
        
    @patch('aiohttp.ClientSession.get')
    async def test_error_handling(self, mock_get):
        """Test error handling during API crawling."""
        mock_get.side_effect = Exception("Connection error")
        
        with self.assertLogs(level='ERROR') as log:
            await self.crawler.crawl(self.taobao_url)
            self.assertIn("Error crawling", log.output[0])

if __name__ == '__main__':
    unittest.main()
