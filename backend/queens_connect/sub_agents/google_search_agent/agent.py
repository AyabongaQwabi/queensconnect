"""
google_search_tool: real-time web search (SerpAPI). ADK function tools return dict.
vertex_ai_search_tool: semantic/local search via orchestratorCall searchEverything.
"""
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types

try:
    from ...config import get_sub_agent_model
except ImportError:
    from config import get_sub_agent_model

APP_NAME="queens_connect"
USER_ID="abqwabi@gmail.com"
SESSION_ID="1234"


google_search_agent = LlmAgent(
    name="basic_search_agent",
    model=get_sub_agent_model(),
    description="Agent to answer questions using Google Search.",
    instruction="Answer the following question based on your knowledge of Komani/Queenstown, Eastern Cape, South Africa. Reply in Markdown (use **bold** for emphasis, lists where helpful).",
    # google_search is a pre-built tool which allows the agent to perform Google searches.
    tools=[google_search]
)

# 