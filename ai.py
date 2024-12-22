import httpx
from openai import OpenAI
import json

client = OpenAI(
    api_key=api_key,
    http_client=httpx.Client(
        proxies={"http://": env.OPENAI_PROXY, "https://": env.OPENAI_PROXY} if env.OPENAI_PROXY else None
    ),
    base_url=base_url
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


async def async_handle_openapi_response(task):
    # import asyncio
    # await asyncio.sleep(3)
    # print('return')
    # return
    response = await client.chat.completions.create(**task.request_params)
    arguments: dict = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
    openapi = arguments["openapi"]
    if not isinstance(openapi, dict):
        openapi = json.loads(str(openapi))
    if not isinstance(openapi, dict) or not openapi.get('openapi'):
        raise ValueError(f'Invalid openapi: {openapi}')
    return openapi
