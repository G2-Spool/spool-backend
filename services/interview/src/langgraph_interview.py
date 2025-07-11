"""LangGraph-based interview orchestration module."""

import asyncio
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
import re
import logging

logger = logging.getLogger(__name__)


class InterviewState(TypedDict):
    """State for the interview graph"""
    messages: List[BaseMessage]
    interests: List[Dict[str, Any]]
    current_topic: Optional[str]
    follow_up_count: int
    interview_stage: str  # "greeting", "exploration", "deep_dive", "wrap_up"
    user_info: Dict[str, Any]
    extracted_concepts: List[str]
    should_create_thread: bool
    mode: Optional[str]


class InterviewGraph:
    """LangGraph-based interview orchestration"""
    
    def __init__(self, llm_model: Optional[ChatOpenAI] = None):
        self.llm = llm_model or ChatOpenAI(
            model="gpt-4.1-nano-2025-04-14",
            temperature=0.7
        )
        self.graph = self._build_graph()
        self.system_prompt = SystemMessage(content="""You are a friendly interview assistant helping to learn about a student's interests and hobbies.
Your goal is to have a natural conversation and discover:
1. What interests and hobbies they have
2. What they enjoy most about each interest
3. How these interests might relate to their learning goals

Be conversational, ask follow-up questions, and show genuine interest in their responses.
When you identify a clear interest or hobby, mark it with [INTEREST: name] in your response.
Keep responses concise and natural for voice conversation.

Interview stages:
- greeting: Welcome the student and ask about their interests
- exploration: Explore different interests they mention
- deep_dive: Go deeper into 1-2 main interests
- wrap_up: Summarize what you've learned and thank them""")
        
    def _build_graph(self) -> StateGraph:
        """Build the interview state graph"""
        graph = StateGraph(InterviewState)
        
        # Add nodes
        graph.add_node("analyze_input", self.analyze_input)
        graph.add_node("generate_response", self.generate_response)
        graph.add_node("extract_interests", self.extract_interests)
        graph.add_node("determine_next_stage", self.determine_next_stage)
        graph.add_node("prepare_thread_data", self.prepare_thread_data)
        
        # Add edges
        graph.add_edge("analyze_input", "extract_interests")
        graph.add_edge("extract_interests", "determine_next_stage")
        graph.add_edge("determine_next_stage", "generate_response")
        
        # Conditional edges
        graph.add_conditional_edges(
            "generate_response",
            self._should_continue,
            {
                "continue": "analyze_input",
                "prepare_thread": "prepare_thread_data",
                "end": END
            }
        )
        
        graph.add_edge("prepare_thread_data", END)
        
        # Set entry point
        graph.set_entry_point("analyze_input")
        
        return graph.compile()
    
    async def analyze_input(self, state: InterviewState) -> InterviewState:
        """Analyze the latest user input"""
        if not state["messages"]:
            # First message - initialize
            state["messages"] = [self.system_prompt]
            state["interview_stage"] = "greeting"
            return state
        
        # Get the latest user message
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            # Analyze sentiment and engagement
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", "Analyze the user's message for sentiment, engagement level, and key topics mentioned."),
                ("human", "{message}")
            ])
            
            analysis = await self.llm.ainvoke(
                analysis_prompt.format_messages(message=last_message.content)
            )
            
            # Store analysis in user_info
            state["user_info"]["last_analysis"] = analysis.content
        
        return state
    
    async def extract_interests(self, state: InterviewState) -> InterviewState:
        """Extract interests from the conversation"""
        # Look for interests in the last AI message if any
        if len(state["messages"]) > 1:
            for msg in reversed(state["messages"]):
                if isinstance(msg, AIMessage):
                    interests = self._extract_interest_tags(msg.content)
                    for interest in interests:
                        if not any(i["name"] == interest for i in state["interests"]):
                            state["interests"].append({
                                "name": interest,
                                "detected_at": datetime.utcnow().isoformat(),
                                "context": msg.content[:200]
                            })
                    break
        
        # Also extract concepts from user messages
        if len(state["messages"]) > 2:
            last_user_msg = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    last_user_msg = msg
                    break
            
            if last_user_msg:
                concepts = await self._extract_concepts(last_user_msg.content)
                state["extracted_concepts"].extend(concepts)
        
        return state
    
    async def determine_next_stage(self, state: InterviewState) -> InterviewState:
        """Determine what stage of the interview we should be in"""
        message_count = len([m for m in state["messages"] if isinstance(m, (HumanMessage, AIMessage))])
        interests_count = len(state["interests"])
        
        current_stage = state["interview_stage"]
        
        # Stage progression logic
        if current_stage == "greeting" and message_count > 2:
            state["interview_stage"] = "exploration"
        elif current_stage == "exploration" and interests_count >= 2 and message_count > 6:
            state["interview_stage"] = "deep_dive"
        elif current_stage == "deep_dive" and message_count > 12:
            state["interview_stage"] = "wrap_up"
        
        # Check if we should create a thread
        if state.get("mode") == "thread" and interests_count >= 1:
            state["should_create_thread"] = True
        
        return state
    
    async def generate_response(self, state: InterviewState) -> InterviewState:
        """Generate the next response based on the current state"""
        stage = state["interview_stage"]
        interests = state["interests"]
        
        # Build context-aware prompt
        stage_prompts = {
            "greeting": "Start by warmly greeting the student and asking about their interests or hobbies.",
            "exploration": f"Explore the student's interests. They've mentioned: {[i['name'] for i in interests]}. Ask about other interests or get more details.",
            "deep_dive": f"Go deeper into their main interests: {[i['name'] for i in interests[:2]]}. Ask specific questions about what they enjoy most.",
            "wrap_up": f"Summarize what you've learned about their interests: {[i['name'] for i in interests]}. Thank them for sharing."
        }
        
        response_prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt.content + f"\n\nCurrent stage: {stage}\n{stage_prompts.get(stage, '')}"),
            MessagesPlaceholder("messages"),
            ("human", "Generate your next response. Remember to mark any new interests with [INTEREST: name].")
        ])
        
        # Generate response
        response = await self.llm.ainvoke(
            response_prompt.format_messages(messages=state["messages"][1:])  # Skip system message
        )
        
        # Add the response to messages
        state["messages"].append(AIMessage(content=response.content))
        
        return state
    
    async def prepare_thread_data(self, state: InterviewState) -> InterviewState:
        """Prepare data for thread creation if needed"""
        if state["should_create_thread"]:
            # Summarize the conversation for thread creation
            summary_prompt = ChatPromptTemplate.from_messages([
                ("system", "Summarize this interview conversation into a concise learning thread title and description."),
                MessagesPlaceholder("messages"),
                ("human", "Create a title (max 100 chars) and description (max 500 chars) for a learning thread based on this conversation.")
            ])
            
            summary = await self.llm.ainvoke(
                summary_prompt.format_messages(messages=state["messages"][1:])
            )
            
            state["user_info"]["thread_summary"] = summary.content
        
        return state
    
    def _extract_interest_tags(self, text: str) -> List[str]:
        """Extract interests marked with [INTEREST: name] from text"""
        pattern = r'\[INTEREST:\s*([^\]]+)\]'
        matches = re.findall(pattern, text)
        return [match.strip() for match in matches if match.strip()]
    
    async def _extract_concepts(self, text: str) -> List[str]:
        """Extract academic concepts from text using LLM"""
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract academic subjects, topics, and concepts from the user's message. Return a comma-separated list."),
            ("human", "{text}")
        ])
        
        result = await self.llm.ainvoke(
            extraction_prompt.format_messages(text=text)
        )
        
        concepts = [c.strip() for c in result.content.split(",") if c.strip()]
        return concepts
    
    def _should_continue(self, state: InterviewState) -> str:
        """Determine if the interview should continue"""
        if state["interview_stage"] == "wrap_up" and len(state["messages"]) > 15:
            if state["should_create_thread"]:
                return "prepare_thread"
            return "end"
        return "continue"
    
    async def process_message(
        self, 
        user_message: str, 
        conversation_history: List[BaseMessage],
        mode: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a user message through the interview graph"""
        # Initialize state
        initial_state: InterviewState = {
            "messages": conversation_history + [HumanMessage(content=user_message)],
            "interests": [],
            "current_topic": None,
            "follow_up_count": 0,
            "interview_stage": "greeting",
            "user_info": user_info or {},
            "extracted_concepts": [],
            "should_create_thread": False,
            "mode": mode
        }
        
        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        # Extract the response
        ai_response = None
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage):
                ai_response = msg.content
                break
        
        return {
            "response": ai_response,
            "interests": final_state["interests"],
            "stage": final_state["interview_stage"],
            "should_create_thread": final_state["should_create_thread"],
            "thread_summary": final_state["user_info"].get("thread_summary"),
            "concepts": final_state["extracted_concepts"]
        }