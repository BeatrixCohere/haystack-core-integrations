# SPDX-FileCopyrightText: 2023-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0
import os

import pytest
from cohere import COHERE_API_URL
from haystack.components.generators.utils import print_streaming_chunk
from haystack_integrations.components.generators.cohere import CohereGenerator

pytestmark = pytest.mark.generators


class TestCohereGenerator:
    def test_init_default(self):
        component = CohereGenerator(api_key="test-api-key")
        assert component.api_key == "test-api-key"
        assert component.model == "command"
        assert component.streaming_callback is None
        assert component.api_base_url == COHERE_API_URL
        assert component.model_parameters == {}

    def test_init_with_parameters(self):
        callback = lambda x: x  # noqa: E731
        component = CohereGenerator(
            api_key="test-api-key",
            model="command-light",
            max_tokens=10,
            some_test_param="test-params",
            streaming_callback=callback,
            api_base_url="test-base-url",
        )
        assert component.api_key == "test-api-key"
        assert component.model == "command-light"
        assert component.streaming_callback == callback
        assert component.api_base_url == "test-base-url"
        assert component.model_parameters == {"max_tokens": 10, "some_test_param": "test-params"}

    def test_to_dict_default(self):
        component = CohereGenerator(api_key="test-api-key")
        data = component.to_dict()
        assert data == {
            "type": "haystack_integrations.components.generators.cohere.generator.CohereGenerator",
            "init_parameters": {
                "model": "command",
                "streaming_callback": None,
                "api_base_url": COHERE_API_URL,
            },
        }

    def test_to_dict_with_parameters(self):
        component = CohereGenerator(
            api_key="test-api-key",
            model="command-light",
            max_tokens=10,
            some_test_param="test-params",
            streaming_callback=print_streaming_chunk,
            api_base_url="test-base-url",
        )
        data = component.to_dict()
        assert data == {
            "type": "haystack_integrations.components.generators.cohere.generator.CohereGenerator",
            "init_parameters": {
                "model": "command-light",
                "max_tokens": 10,
                "some_test_param": "test-params",
                "api_base_url": "test-base-url",
                "streaming_callback": "haystack.components.generators.utils.print_streaming_chunk",
            },
        }

    def test_to_dict_with_lambda_streaming_callback(self):
        component = CohereGenerator(
            api_key="test-api-key",
            model="command",
            max_tokens=10,
            some_test_param="test-params",
            streaming_callback=lambda x: x,
            api_base_url="test-base-url",
        )
        data = component.to_dict()
        assert data == {
            "type": "haystack_integrations.components.generators.cohere.generator.CohereGenerator",
            "init_parameters": {
                "model": "command",
                "streaming_callback": "tests.test_cohere_generators.<lambda>",
                "api_base_url": "test-base-url",
                "max_tokens": 10,
                "some_test_param": "test-params",
            },
        }

    def test_from_dict(self, monkeypatch):
        monkeypatch.setenv("COHERE_API_KEY", "test-key")
        data = {
            "type": "haystack_integrations.components.generators.cohere.generator.CohereGenerator",
            "init_parameters": {
                "model": "command",
                "max_tokens": 10,
                "some_test_param": "test-params",
                "api_base_url": "test-base-url",
                "streaming_callback": "haystack.components.generators.utils.print_streaming_chunk",
            },
        }
        component: CohereGenerator = CohereGenerator.from_dict(data)
        assert component.api_key == "test-key"
        assert component.model == "command"
        assert component.streaming_callback == print_streaming_chunk
        assert component.api_base_url == "test-base-url"
        assert component.model_parameters == {"max_tokens": 10, "some_test_param": "test-params"}

    def test_check_truncated_answers(self, caplog):
        component = CohereGenerator(api_key="test-api-key")
        meta = [{"finish_reason": "MAX_TOKENS"}]
        component._check_truncated_answers(meta)
        assert caplog.records[0].message == (
            "Responses have been truncated before reaching a natural stopping point. "
            "Increase the max_tokens parameter to allow for longer completions."
        )

    @pytest.mark.skipif(
        not os.environ.get("COHERE_API_KEY", None),
        reason="Export an env var called CO_API_KEY containing the Cohere API key to run this test.",
    )
    @pytest.mark.integration
    def test_cohere_generator_run(self):
        component = CohereGenerator()
        results = component.run(prompt="What's the capital of France?")
        assert len(results["replies"]) == 1
        assert "Paris" in results["replies"][0]
        assert len(results["meta"]) == 1
        assert results["meta"][0]["finish_reason"] == "COMPLETE"

    @pytest.mark.skipif(
        not os.environ.get("COHERE_API_KEY", None),
        reason="Export an env var called COHERE_API_KEY containing the Cohere API key to run this test.",
    )
    @pytest.mark.integration
    def test_cohere_generator_run_wrong_model(self):
        import cohere

        component = CohereGenerator(model="something-obviously-wrong")
        with pytest.raises(
            cohere.CohereAPIError,
            match="model not found, make sure the correct model ID was used and that you have access to the model.",
        ):
            component.run(prompt="What's the capital of France?")

    @pytest.mark.skipif(
        not os.environ.get("COHERE_API_KEY", None),
        reason="Export an env var called COHERE_API_KEY containing the Cohere API key to run this test.",
    )
    @pytest.mark.integration
    def test_cohere_generator_run_streaming(self):
        class Callback:
            def __init__(self):
                self.responses = ""

            def __call__(self, chunk):
                self.responses += chunk.content
                return chunk

        callback = Callback()
        component = CohereGenerator(streaming_callback=callback)
        results = component.run(prompt="What's the capital of France?")

        assert len(results["replies"]) == 1
        assert "Paris" in results["replies"][0]
        assert len(results["meta"]) == 1
        assert results["meta"][0]["finish_reason"] == "COMPLETE"
        assert callback.responses == results["replies"][0]
