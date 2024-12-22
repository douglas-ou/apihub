from openai import OpenAI
import json
import os


class QWENAIInfo:
    api_key = os.getenv('QWEN_API_KEY')
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    default_model = "qwen-plus"


info = QWENAIInfo()

client = OpenAI(
    api_key=info.api_key,
    # http_client=httpx.Client(
    #     proxies={"http://": env.OPENAI_PROXY, "https://": env.OPENAI_PROXY} if env.OPENAI_PROXY else None
    # ),
    base_url=info.base_url,
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_openapi_json",
            "description": "Parse the input document text and files and generate the OpenAPI document",
            "parameters": {
                "type": "object",
                "properties": {
                    "openapi": {
                        "type": "string",
                        "description": "The generated OpenAPI document in json string",
                    },
                },
                "required": ["openapi"],
                "additionalProperties": False,
            },
        }
    }
]

SYSTEM_MESSAGE = "You are a helpful API document assistant. Use the supplied tools to assist the user."
USER_HINT = "Generate OpenAPI spec API document json based on the following document:"


def get_context_messages(content: str):
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": F"{USER_HINT}\n{content}"}
    ]


async def async_handle_openapi_response(content):
    # import asyncio
    # await asyncio.sleep(3)
    # print('return')
    # return
    request_params = dict(
        model=info.default_model,
        messages=get_context_messages(content),
        tools=tools,
        tool_choice={
            "type": "function",
            "function": {
                "name": "get_openapi_json",
            }
        },
    )
    response = await client.chat.completions.create(**request_params)
    arguments: dict = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    openapi = arguments["openapi"]
    if not isinstance(openapi, dict):
        openapi = json.loads(str(openapi))
    if not isinstance(openapi, dict) or not openapi.get('openapi'):
        raise ValueError(f'Invalid openapi: {openapi}')
    return openapi
