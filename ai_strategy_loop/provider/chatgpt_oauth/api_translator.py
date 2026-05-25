"""ChatGPT OAuth API 변환기 (순수 함수, Newsletter_AI 이식).

Chat Completions API <-> ChatGPT Responses API 간의 요청/응답 변환을 담당한다.
네트워크 I/O 없이 데이터 구조만 변환하므로 테스트와 이식이 용이하다.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_MODEL, MODEL_MAPPING

logger = logging.getLogger(__name__)


# =============================================================================
# 요청 변환: Chat Completions -> Responses
# =============================================================================


def translate_request(chat_completions_body: Dict[str, Any]) -> Dict[str, Any]:
    """Chat Completions API 요청을 ChatGPT Responses API 형식으로 변환."""
    messages = chat_completions_body.get("messages", [])

    instructions_parts = [
        msg.get("content") or ""
        for msg in messages
        if msg.get("role") == "system"
    ]
    input_messages = _translate_messages_to_input(
        [msg for msg in messages if msg.get("role") != "system"]
    )

    original_model = chat_completions_body.get("model", DEFAULT_MODEL)
    mapped_model = _map_model(original_model)

    result: Dict[str, Any] = {
        "model": mapped_model,
        "input": input_messages,
        "store": False,
        "stream": True,
    }

    if instructions_parts:
        result["instructions"] = "\n\n".join(instructions_parts)

    # ChatGPT account + codex backend는 max_output_tokens / temperature를
    # 거부하므로 upstream 호환성을 위해 전달하지 않는다.
    _ = chat_completions_body.get("max_tokens")
    _ = chat_completions_body.get("temperature")

    tools = chat_completions_body.get("tools")
    if tools:
        result["tools"] = _translate_tools(tools)

    response_format = chat_completions_body.get("response_format")
    if response_format:
        text_format = _translate_response_format(response_format)
        if text_format:
            result["text"] = {"format": text_format}

    return result


def _translate_messages_to_input(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chat Completions messages를 Responses API input 항목으로 변환."""
    translated: List[Dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content")

        if role == "tool":
            translated.append({
                "type": "function_call_output",
                "call_id": msg.get("tool_call_id", ""),
                "output": content if isinstance(content, str) else json.dumps(content),
            })
            continue

        tool_calls = msg.get("tool_calls") or []
        if role == "assistant" and tool_calls:
            if content:
                translated.append({"role": "assistant", "content": content})
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                translated.append({
                    "type": "function_call",
                    "name": func.get("name", ""),
                    "call_id": tool_call.get("id", ""),
                    "arguments": func.get("arguments", "{}"),
                })
            continue

        translated_msg: Dict[str, Any] = {"role": role}
        if content is not None:
            translated_msg["content"] = content
        translated.append(translated_msg)

    return translated


def _map_model(model_name: str) -> str:
    """모델명을 Codex 호환 모델로 매핑."""
    mapped = MODEL_MAPPING.get(model_name)
    if mapped:
        return mapped
    logger.debug("모델 매핑 없음, 원본 사용: %s", model_name)
    return model_name


def _translate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chat Completions tools를 Responses API 형식으로 변환."""
    translated = []
    for tool in tools:
        if tool.get("type") == "function":
            func = tool.get("function", {})
            translated.append({
                "type": "function",
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })
        else:
            translated.append(tool)
    return translated


def _translate_response_format(
    response_format: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """response_format을 Responses API text.format으로 변환."""
    fmt_type = response_format.get("type", "")

    if fmt_type == "json_object":
        return {"type": "json_object"}

    if fmt_type == "json_schema":
        json_schema = response_format.get("json_schema", {})
        return {
            "type": "json_schema",
            "name": json_schema.get("name", "response"),
            "schema": json_schema.get("schema", {}),
            "strict": json_schema.get("strict", True),
        }

    return None


# =============================================================================
# 응답 변환: Responses -> Chat Completions
# =============================================================================


def translate_response(
    responses_body: Dict[str, Any],
    requested_model: Optional[str] = None,
) -> Dict[str, Any]:
    """ChatGPT Responses API 응답을 Chat Completions API 형식으로 변환."""
    outputs = responses_body.get("output", [])
    content_parts = []
    tool_calls = []
    finish_reason = "stop"

    for item in outputs:
        item_type = item.get("type", "")

        if item_type == "message":
            for part in item.get("content", []):
                if part.get("type") in {"output_text", "text"}:
                    content_parts.append(part.get("text", ""))

        elif item_type == "function_call":
            tool_calls.append({
                "id": item.get("call_id", item.get("id", "")),
                "type": "function",
                "function": {
                    "name": item.get("name", ""),
                    "arguments": item.get("arguments", "{}"),
                },
            })
            finish_reason = "tool_calls"

    if not content_parts:
        top_level_text = responses_body.get("output_text")
        if isinstance(top_level_text, str) and top_level_text:
            content_parts.append(top_level_text)

    message: Dict[str, Any] = {
        "role": "assistant",
        "content": "\n".join(content_parts) if content_parts else None,
    }
    if tool_calls:
        message["tool_calls"] = tool_calls

    raw_usage = responses_body.get("usage", {})
    usage = {
        "prompt_tokens": raw_usage.get("input_tokens", 0),
        "completion_tokens": raw_usage.get("output_tokens", 0),
        "total_tokens": raw_usage.get(
            "total_tokens",
            raw_usage.get("input_tokens", 0) + raw_usage.get("output_tokens", 0),
        ),
    }

    return {
        "id": responses_body.get("id", ""),
        "object": "chat.completion",
        "created": 0,
        "model": requested_model or responses_body.get("model", ""),
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage,
    }


# =============================================================================
# SSE 스트림 파싱
# =============================================================================


def collect_sse_response(sse_text: str) -> Dict[str, Any]:
    """SSE 스트림 텍스트를 파싱하여 최종 Responses API 응답으로 조합.

    ChatGPT Responses API는 SSE 형태로 응답을 반환한다. 이 함수는 스트림
    전체를 받아 최종 응답 하나로 재구성한다.
    """
    final_response: Optional[Dict[str, Any]] = None
    accumulated_text: List[str] = []
    accumulated_tool_calls: List[Dict[str, Any]] = []
    usage_data: Dict[str, Any] = {}

    for line in sse_text.split("\n"):
        line = line.strip()

        if not line or line.startswith(":"):
            continue

        if line.startswith("data: "):
            data_str = line[6:]

            if data_str == "[DONE]":
                break

            try:
                event_data = json.loads(data_str)
            except json.JSONDecodeError:
                logger.debug("SSE JSON 파싱 실패: %s", data_str[:100])
                continue

            event_type = event_data.get("type", "")

            if event_type in ("response.completed", "response.done"):
                inner = event_data.get("response", event_data)
                if accumulated_text and not inner.get("output") and not inner.get(
                    "output_text"
                ):
                    inner = dict(inner)
                    inner["output_text"] = "".join(accumulated_text)
                final_response = inner
                continue

            if event_type in (
                "response.output_text.delta",
                "content_block.delta",
            ):
                delta_text = event_data.get("delta", "")
                if isinstance(delta_text, str):
                    accumulated_text.append(delta_text)

            if event_type == "response.function_call_arguments.done":
                accumulated_tool_calls.append({
                    "type": "function_call",
                    "call_id": event_data.get("call_id", ""),
                    "name": event_data.get("name", ""),
                    "arguments": event_data.get("arguments", ""),
                })

            if "usage" in event_data:
                usage_data.update(event_data["usage"])

    if final_response:
        return final_response

    output: List[Dict[str, Any]] = []
    if accumulated_text:
        output.append({
            "type": "message",
            "content": [{"type": "output_text", "text": "".join(accumulated_text)}],
        })
    output.extend(accumulated_tool_calls)

    return {
        "output": output,
        "usage": usage_data,
        "status": "completed",
    }
