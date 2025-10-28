"""Service for parsing JSON from LLM responses."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class JSONResponseParser:
    """
    Service for parsing JSON content from LLM responses.

    Handles extraction of JSON from markdown code blocks and other formats.
    """

    JSON_CODE_BLOCK_START = "```json"
    JSON_CODE_BLOCK_END = "```"
    JSON_MARKDOWN_DELIMITER_LEN = 7  # Length of "```json"

    def parse_json_response(self, response: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response.

        Handles multiple formats:
        - Plain JSON
        - JSON wrapped in markdown (```json ... ```)
        - JSON wrapped in generic code block (``` ... ```)

        Args:
            response: LLM response string

        Returns:
            Parsed JSON as dictionary

        Raises:
            RuntimeError: If JSON parsing fails
        """
        try:
            # Try to extract JSON if wrapped in markdown
            if self.JSON_CODE_BLOCK_START in response:
                json_start = response.find(self.JSON_CODE_BLOCK_START) + self.JSON_MARKDOWN_DELIMITER_LEN
                json_end = response.find(self.JSON_CODE_BLOCK_END, json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()

            parsed = json.loads(response)
            logger.debug("Successfully parsed JSON response")
            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            logger.debug(f"Response was: {response}")
            raise RuntimeError(f"Failed to parse JSON response: {e}") from e

