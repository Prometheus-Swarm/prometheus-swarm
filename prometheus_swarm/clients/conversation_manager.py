"""Database storage manager for LLM conversations."""

import uuid
import json
from typing import Dict, Optional, List, Any
from prometheus_swarm.database import (
    get_session,
    Conversation,
    Message,
    initialize_database,
)
from prometheus_swarm.database.models import SummarizedMessage
from datetime import datetime

from prometheus_swarm.utils.logging import log_key_value


class ConversationManager:
    """Handles conversation and message storage."""

    def __init__(self):
        """Initialize the conversation manager and database."""
        initialize_database()

    def create_conversation(
        self,
        model: str,
        system_prompt: Optional[str] = None,
        available_tools: Optional[List[str]] = None,
    ) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        with get_session() as session:
            conversation = Conversation(
                id=conversation_id,
                model=model,
                system_prompt=system_prompt,
                available_tools=(
                    json.dumps(available_tools) if available_tools else None
                ),
            )
            session.add(conversation)
            session.commit()
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation details."""
        with get_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            return {
                "model": conversation.model,
                "system_prompt": conversation.system_prompt,
                "available_tools": (
                    json.loads(conversation.available_tools)
                    if conversation.available_tools
                    else None
                ),
            }

    def _should_summarize(self, messages: List[Dict[str, Any]], threshold: int = 5) -> bool:
        """Determine if messages should be summarized based on count.
        
        Args:
            messages: List of messages to check
            threshold: Number of messages that triggers summarization
            
        Returns:
            bool: True if messages should be summarized
        """
        log_key_value("SHOULD SUMMARIZE", len(messages))
        return len(messages) >= threshold

    def get_messages(self, conversation_id: str, client: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Get all messages for a conversation in chronological order.
        
        Args:
            conversation_id: The ID of the conversation
            client: Optional LLM client to use for summarization
            
        Returns:
            List of messages, potentially with summarized messages if summarization was triggered
        """
        with get_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            messages = [
                {"role": msg.role, "content": json.loads(msg.content)}
                for msg in conversation.messages
            ]

            MESSAGE_THRESHOLD = 10
            log_key_value("MESSAGES", messages)
            # Check if we should summarize

            log_key_value("CLIENT", client)
            log_key_value("SHOULD SUMMARIZE", self._should_summarize(messages, MESSAGE_THRESHOLD))
            if client and self._should_summarize(messages, MESSAGE_THRESHOLD):
                # Get the last threshold messages
                log_key_value("SUMMARIZING", messages)
                last_messages = messages[-MESSAGE_THRESHOLD:]
                    # Create new summarized message
                self.save_summarized_messages(
                    conversation_id=conversation_id,
                    messages=last_messages,
                    client=client
                )
            
            return messages
        
    def get_summarized_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation in chronological order."""
        with get_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            return conversation.summarized_messages
        
    def save_summarized_messages(self, conversation_id: str, messages: List[Dict[str, Any]], client: Optional[Any] = None):
        """Save summarized messages with optional AI summarization.
        
        Args:
            conversation_id: The ID of the conversation
            messages: List of messages to consolidate
            client: Optional LLM client to use for summarization
        """
        log_key_value("SUMMARIZATION STARTS", messages)
        with get_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Filter out tool messages
            non_tool_messages = [msg for msg in messages if msg["role"] != "tool"]
            
            # If client is provided, use it to summarize the messages
            if client:
                # Create a summary prompt
                summary_prompt = "Please summarize the following conversation in a concise way, highlighting the key points and decisions made:\n\n"
                for msg in non_tool_messages:
                    role = msg["role"]
                    content = msg["content"]
                    if isinstance(content, list):
                        # Handle structured content
                        text_blocks = [block["text"] for block in content if block["type"] == "text"]
                        content = " ".join(text_blocks)
                    summary_prompt += f"{role}: {content}\n"
                
                # Get summary from the LLM
                response = client.send_message(prompt=summary_prompt)
                if isinstance(response["content"], list):
                    # Extract text from structured response
                    summary = " ".join(block["text"] for block in response["content"] if block["type"] == "text")
                else:
                    summary = response["content"]
                print(f"Summary[SUMMARIZATION STARTS]: {summary}")
                # Store both original messages and summary
                summarized_message = SummarizedMessage(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role="system",
                    content=json.dumps({
                        "original_messages": messages,  # Keep all messages in original_messages
                        "summary": summary
                    }),
                )
                

            else:
                # Store just the original messages without summarization
                summarized_message = SummarizedMessage(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role="system",
                    content=json.dumps(messages),
                )
            
            # Check if we need to remove old summarized messages
            existing_messages = session.query(SummarizedMessage).filter(
                SummarizedMessage.conversation_id == conversation_id
            ).order_by(SummarizedMessage.created_at.desc()).all()
            
            SUMMARIZED_MESSAGE_THRESHOLD = 4
            if len(existing_messages) >= SUMMARIZED_MESSAGE_THRESHOLD:
                # Only delete the oldest message (last in the list since we ordered by desc)
                oldest_message = existing_messages[-1]
                session.delete(oldest_message)

            log_key_value("SUMMARIZED MESSAGE", summarized_message)
            session.add(summarized_message)
            session.commit()

            # Delete the original messages that were summarized
            for msg in messages:
                session.query(Message).filter(
                    Message.conversation_id == conversation_id,
                    Message.role == msg["role"],
                    Message.content == json.dumps(msg["content"])
                ).delete()
            session.commit()
    
    def save_message(self, conversation_id: str, role: str, content: Any):
        """Save a message."""
        with get_session() as session:
            # First verify conversation exists
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")

            # Create and save message
            message = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role=role,
                content=json.dumps(content),
            )
            session.add(message)
            session.commit()

    def update_tools(
        self, conversation_id: str, available_tools: Optional[List[str]] = None
    ):
        """Update available tools for an existing conversation."""
        with get_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            conversation.available_tools = (
                json.dumps(available_tools) if available_tools else None
            )
            session.commit()
