"""
ChatGPT OAuth API 변환기 (순수 함수)

Chat Completions API <-> ChatGPT Responses API 간의
요청/응답 변환을 담당합니다.

이 모듈은 네트워크 I/O 없이 데이터 구조만 변환하므로
테스트와 이식이 용이합니다.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .constants import MODEL_MAPPING, DEFAULT_MODEL

logger = logging.getLogger(__name__)


# =============================================================================
# 업스트림 미지원 파라미터
# =============================================================================

#: ChatGPT account + codex backend 가 거부하는 Chat Completions 파라미터.
#: 전송하지 않는 것이 맞지만, provider 설정의 해당
#: 값이 무효라는 사실이 침묵으로 넘어가면 안 된다(OA-1). 특히 `temperature`
#: 는 생성 편차를 좌우하므로, 설정값이 적용되는 줄 알고 튜닝하면
#: 원인을 잘못 짚게 된다. OpenRouter 경로는 정상 적용되므로 공급자를 바꾸면
#: 생성 특성이 달라진다는 점도 함께 알려야 한다.
UNSUPPORTED_UPSTREAM_PARAMETERS: tuple[str, ...] = ("temperature", "max_tokens")

_dropped_parameter_notice_emitted = False


def dropped_parameter_names(
    chat_completions_body: Dict[str, Any],
) -> tuple[str, ...]:
    """요청에 실려 왔지만 업스트림 미지원으로 폐기될 파라미터 이름을 반환한다."""
    return tuple(
        name
        for name in UNSUPPORTED_UPSTREAM_PARAMETERS
        if chat_completions_body.get(name) is not None
    )


def reset_dropped_parameter_notice_for_test() -> None:
    """테스트 전용 — 1회성 경고 플래그를 초기화한다."""
    global _dropped_parameter_notice_emitted
    _dropped_parameter_notice_emitted = False


def _warn_dropped_parameters_once(dropped: tuple[str, ...]) -> None:
    global _dropped_parameter_notice_emitted
    if not dropped or _dropped_parameter_notice_emitted:
        return
    _dropped_parameter_notice_emitted = True
    logger.warning(
        "ChatGPT OAuth(codex) 업스트림이 %s 를 거부하므로 전송하지 않습니다. "
        "이 값은 chatgpt_oauth 경로에서 무효이며, "
        "OpenRouter 등 다른 공급자에서는 정상 적용됩니다.",
        ", ".join(dropped),
    )


# =============================================================================
# 요청 변환: Chat Completions -> Responses
# =============================================================================


def translate_request(chat_completions_body: Dict[str, Any]) -> Dict[str, Any]:
    """Chat Completions API 요청을 ChatGPT Responses API 형식으로 변환"""
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

    # 2026-03-28 실측 기준 ChatGPT account + codex backend 는 `max_output_tokens`
    # 와 `temperature` 를 모두 거부하므로 전달하지 않는다. v0.62.3 부터는 폐기
    # 사실을 1회 경고로 노출한다(OA-1) — 설정이 적용되는 줄 알고 튜닝하는 것을
    # 막기 위함이다.
    _warn_dropped_parameters_once(dropped_parameter_names(chat_completions_body))

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
    """Chat Completions messages를 Responses API input 항목으로 변환"""
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
    """모델명을 Codex 호환 모델로 매핑"""
    mapped = MODEL_MAPPING.get(model_name)
    if mapped:
        return mapped

    # 알려지지 않은 모델은 그대로 전달 (업스트림에서 거부하면 기본값 사용)
    logger.debug("모델 매핑 없음, 원본 사용: %s", model_name)
    return model_name


def _translate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chat Completions tools를 Responses API 형식으로 변환

    Chat Completions: tools[].function.{name, description, parameters}
    Responses: tools[].{type, name, description, parameters}
    """
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
    """response_format을 Responses API text.format으로 변환"""
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
    requested_model: str | None = None,
) -> Dict[str, Any]:
    """ChatGPT Responses API 응답을 Chat Completions API 형식으로 변환"""
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


def _map_finish_reason(status: str) -> str:
    """Responses API status를 Chat Completions finish_reason으로 매핑"""
    mapping = {
        "completed": "stop",
        "incomplete": "length",
        "failed": "stop",
        "cancelled": "stop",
    }
    return mapping.get(status, "stop")


# =============================================================================
# SSE 스트림 파싱
# =============================================================================


def collect_sse_response(sse_text: str) -> Dict[str, Any]:
    """SSE 스트림 텍스트를 파싱하여 최종 Responses API 응답으로 조합

    ChatGPT Responses API는 SSE 형태로 응답을 반환합니다.
    이 함수는 스트림 전체를 받아서 최종 응답 하나로 재구성합니다.

    Args:
        sse_text: SSE 이벤트 스트림 텍스트

    Returns:
        완전한 Responses API 응답
    """
    final_response: Optional[Dict[str, Any]] = None
    accumulated_text = []
    accumulated_tool_calls = []
    usage_data = {}

    for line in sse_text.split("\n"):
        line = line.strip()

        if not line or line.startswith(":"):
            continue

        if line.startswith("data: "):
            data_str = line[6:]  # "data: " 이후

            if data_str == "[DONE]":
                break

            try:
                event_data = json.loads(data_str)
            except json.JSONDecodeError:
                logger.debug("SSE JSON 파싱 실패: %s", data_str[:100])
                continue

            event_type = event_data.get("type", "")

            # response.completed 이벤트: 내부 response 필드를 벗겨냄
            if event_type == "response.completed":
                inner = event_data.get("response", event_data)
                if accumulated_text and not inner.get("output") and not inner.get("output_text"):
                    inner = dict(inner)
                    inner["output_text"] = "".join(accumulated_text)
                final_response = inner
                continue

            # response.done (대체 형식)
            if event_type == "response.done":
                inner = event_data.get("response", event_data)
                if accumulated_text and not inner.get("output") and not inner.get("output_text"):
                    inner = dict(inner)
                    inner["output_text"] = "".join(accumulated_text)
                final_response = inner
                continue

            # 텍스트 델타 수집
            if event_type in (
                "response.output_text.delta",
                "content_block.delta",
            ):
                delta_text = event_data.get("delta", "")
                if isinstance(delta_text, str):
                    accumulated_text.append(delta_text)

            # function_call 수집
            if event_type == "response.function_call_arguments.done":
                accumulated_tool_calls.append({
                    "type": "function_call",
                    "call_id": event_data.get("call_id", ""),
                    "name": event_data.get("name", ""),
                    "arguments": event_data.get("arguments", ""),
                })

            # usage 정보
            if "usage" in event_data:
                usage_data.update(event_data["usage"])

    # 최종 응답 구성
    if final_response:
        return final_response

    # final_response 이벤트가 없었다면 축적된 데이터로 구성
    output = []
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


def parse_sse_to_chat_completions(sse_text: str) -> Dict[str, Any]:
    """SSE 텍스트를 파싱하여 Chat Completions 응답으로 직접 변환

    collect_sse_response + translate_response를 한 번에 수행합니다.

    Args:
        sse_text: SSE 이벤트 스트림 텍스트

    Returns:
        Chat Completions API 형식의 응답
    """
    responses_body = collect_sse_response(sse_text)
    return translate_response(responses_body)
