from crawler import main, save_to_provider_library
import asyncio
import json


def crawler_test(input_url):
    # Run the crawler
    openapi_spec = asyncio.run(main(input_url, max_urls=2))

    # Save to provider library
    save_to_provider_library(input_url, openapi_spec)

    # Also output to stdout for debugging
    print("\nGenerated OpenAPI Specification:")
    print(json.dumps(openapi_spec, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    # crawler_test('https://open.taobao.com/api.htm?docId=46&docType=2')
    # crawler_test('https://coinmarketcap.com/api/documentation/v1/')
    crawler_test('https://www.xfyun.cn/doc/asr/voicedictation/API.html')
    # crawler_test('https://vatlayer.com/documentation')
