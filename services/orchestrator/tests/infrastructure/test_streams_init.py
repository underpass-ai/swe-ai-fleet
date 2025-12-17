import pytest

from services.orchestrator.infrastructure.streams_init import ensure_streams


class TestStreamsInit:
    @pytest.mark.asyncio
    async def test_ensure_streams_creates_missing_streams(self, mocker) -> None:
        mock_js = mocker.AsyncMock()
        mock_js.stream_info.side_effect = Exception("Stream not found")
        mock_js.add_stream = mocker.AsyncMock()

        await ensure_streams(mock_js)

        assert mock_js.add_stream.call_count == 4
        stream_names = [call[1]["name"] for call in mock_js.add_stream.call_args_list]
        assert "PLANNING_EVENTS" in stream_names
        assert "ORCHESTRATOR_EVENTS" in stream_names
        assert "AGENT_COMMANDS" in stream_names
        assert "AGENT_RESPONSES" in stream_names

    @pytest.mark.asyncio
    async def test_ensure_streams_skips_existing_streams(self, mocker) -> None:
        mock_js = mocker.AsyncMock()
        mock_stream_info = mocker.MagicMock()
        mock_stream_info.config.storage = "FILE"
        mock_js.stream_info.return_value = mock_stream_info
        mock_js.add_stream = mocker.AsyncMock()

        await ensure_streams(mock_js)

        mock_js.add_stream.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_streams_handles_add_stream_errors(self, mocker) -> None:
        mock_js = mocker.AsyncMock()
        mock_js.stream_info.side_effect = Exception("Stream not found")
        mock_js.add_stream.side_effect = Exception("Stream already exists")

        # Should not raise, just log warning
        await ensure_streams(mock_js)

        assert mock_js.add_stream.call_count == 4
