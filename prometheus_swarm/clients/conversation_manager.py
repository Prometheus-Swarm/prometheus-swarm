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

from prometheus_swarm.utils.logging import log_key_value, log_section, log_error
from prometheus_swarm.utils.logging import record_conversation


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

            MESSAGE_THRESHOLD = 500
            log_key_value("Current Messages Number", len(messages))
            
            # Check if we should summarize
            if client and self._should_summarize(messages, MESSAGE_THRESHOLD):
                # Get the last threshold messages
                log_key_value("Should Summarize", True)
                last_messages = messages[-MESSAGE_THRESHOLD:]
                # Create new summarized message and wait for it to complete
                try:
                    self.save_summarized_messages(
                        conversation_id=conversation_id,
                        messages=last_messages,
                        client=client
                    )
                    # After summarization, get the updated messages
                    messages = [
                        {"role": msg.role, "content": json.loads(msg.content)}
                        for msg in conversation.messages
                    ]
                except Exception as e:
                    log_error(e, "Error during summarization")
            
            return messages
        
    def get_summarized_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation in chronological order."""
        with get_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Convert to dict format while still in session
            return [
                {
                    "role": msg.role,
                    "content": msg.content if isinstance(msg.content, str) else json.loads(msg.content)
                }
                for msg in conversation.summarized_messages
            ]
        
    def save_summarized_messages(self, conversation_id: str, messages: List[Dict[str, Any]], client: Optional[Any] = None):
        """Save summarized messages with optional AI summarization.
        
        Args:
            conversation_id: The ID of the conversation
            messages: List of messages to consolidate
            client: Optional LLM client to use for summarization
        """
        log_section("Summarizing", conversation_id, "messages", len(messages), "client", bool(client))
        
        with get_session() as session:
            conversation = session.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Find the last tool message and response
            last_tool_idx = -1
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "tool":
                    last_tool_idx = i
                    break
            
            # Split messages into those to summarize and those to keep
            # Always skip the last 2 messages
            messages_to_summarize = messages[:-2] if len(messages) > 2 else []
            log_key_value("Messages to Summarize", len(messages_to_summarize))
            
            # If client is provided, use it to summarize the messages
            if client:
                # Create a summary prompt
                summary_prompt = "Please summarize the following conversation in a concise way, highlighting the key points and decisions made: Please format your response as a JSON object with the following fields: 'summary', 'key_points', and 'decisions'. If none, please reply N/A. \n\n "
                for msg in messages_to_summarize:
                    role = msg["role"]
                    content = msg["content"]
                    if isinstance(content, list):
                        # Handle structured content
                        text_blocks = [block["text"] for block in content if block["type"] == "text"]
                        content = " ".join(text_blocks)
                    summary_prompt += f"{role}: {content}\n"
                
                log_key_value("Summary Prompt", summary_prompt)
                
                # Get summary from the LLM
                response = client.send_message(prompt=summary_prompt)
                if isinstance(response["content"], list):
                    # Extract text from structured response
                    summary = " ".join(block["text"] for block in response["content"] if block["type"] == "text")
                else:
                    summary = response["content"]
                
                log_key_value("Generated Summary", summary)
                
                # Store both original messages and summary
                summarized_message = SummarizedMessage(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role="user",
                    content=json.dumps(summary),  # Store only the summary
                )
            else:
                # Store just the original messages without summarization
                log_key_value("No Client", "Storing messages without summarization")
                summarized_message = SummarizedMessage(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    role="user",
                    content=json.dumps(messages_to_summarize),
                )
            
            # Check if we need to remove old summarized messages
            existing_messages = session.query(SummarizedMessage).filter(
                SummarizedMessage.conversation_id == conversation_id
            ).order_by(SummarizedMessage.created_at.desc()).all()
            
            SUMMARIZED_MESSAGE_THRESHOLD = 4
            if len(existing_messages) >= SUMMARIZED_MESSAGE_THRESHOLD:
                # Only delete the oldest message (last in the list since we ordered by desc)
                oldest_message = existing_messages[-1]
                log_key_value("Removing Old Summary", f"ID: {oldest_message.id}")
                session.delete(oldest_message)

            log_key_value("New Summary ID", summarized_message.id)
            log_key_value("New Summary Content", json.loads(summarized_message.content))
            
            session.add(summarized_message)
            session.commit()

            # Delete the original messages that were summarized
            deleted_count = 0
            # Skip the last 2 messages when deleting
            messages_to_delete = messages_to_summarize[:-2] if len(messages_to_summarize) > 2 else []
            for msg in messages_to_delete:
                result = session.query(Message).filter(
                    Message.conversation_id == conversation_id,
                    Message.role == msg["role"],
                    Message.content == json.dumps(msg["content"])
                ).delete()
                deleted_count += result
            log_key_value("Deleted Original Messages", deleted_count)
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

            # Record via hook if configured
            record_conversation(conversation_id, role, content, conversation.model)

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
