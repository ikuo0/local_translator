import json
from unittest.mock import patch

from impl_translator.src.libs.translation_formatter import OllamaClient, translate_batch


def test_retains_layout_without_sending_markers():
    batch = {"lines": [
        {"id": "1234", "text": "hoge [[KEEP_6]] piyo"},
        {"id": "1235", "text": "Title . . . . .   385"},
        {"id": "1236", "text": "First\nSecond"},
    ]}

    with patch.object(OllamaClient, "generate", return_value=json.dumps({
        "1236-2": "後",
        "1235-1": "見出し",
        "1234-2": "ピヨ",
        "1234-1": "ホゲ",
        "1236-1": "先",
    })) as generate:
        result = translate_batch(batch)

    assert json.loads(generate.call_args.kwargs["prompt"]) == {
        "1234-1": "hoge", "1234-2": "piyo", "1235-1": "Title",
        "1236-1": "First", "1236-2": "Second",
    }
    schema = generate.call_args.kwargs["output_schema"]
    assert set(schema["required"]) == set(json.loads(generate.call_args.kwargs["prompt"]))
    assert schema["additionalProperties"] is False
    assert result == {
        "1234": "ホゲ [[KEEP_6]] ピヨ",
        "1235": "見出し . . . . .   385",
        "1236": "先<br>後",
    }


def test_repairs_json_and_retries_only_ambiguous_or_truncated_fragments():
    batch = {"lines": [
        {"id": "1", "text": "First"},
        {"id": "2", "text": "Second"},
        {"id": "3", "text": "Third"},
    ]}
    damaged = '{"1":"一","2":"重複","2":"二","3":"途'

    with patch.object(OllamaClient, "generate", side_effect=[damaged, "二", "三"]) as generate:
        assert translate_batch(batch) == {"1": "一", "2": "二", "3": "三"}

    retries = generate.call_args_list[1:]
    assert [call.kwargs["prompt"] for call in retries] == ["Second", "Third"]
    assert all("output_schema" not in call.kwargs for call in retries)


def test_reuses_all_values_when_only_closing_brace_is_missing():
    batch = {"lines": [{"id": "1", "text": "First"}]}

    with patch.object(OllamaClient, "generate", return_value='{"1":"一"') as generate:
        assert translate_batch(batch) == {"1": "一"}

    generate.assert_called_once()
