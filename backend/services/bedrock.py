"""
Bedrock service for Claude chat completions (Lab 2)
Provides Claude Sonnet 3.7 chat capabilities via Bedrock
"""
import logging
import json
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for Claude chat completions via Bedrock"""
    
    def __init__(self):
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.aws_region
        )
        self.model_id = settings.bedrock_chat_model
        logger.info(f"Initialized Bedrock chat service with model: {self.model_id}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Generate a chat completion using Claude
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Generated response text
        """
        try:
            # Prepare request body for Claude
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            
            if system:
                body["system"] = system
            
            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            
            # Extract text from content blocks
            if "content" in response_body:
                content_blocks = response_body["content"]
                text_content = []
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_content.append(block.get("text", ""))
                return "\n".join(text_content)
            
            logger.error("No content in Claude response")
            return None
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            return None
    
    async def generate_product_description(
        self,
        product_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate an enhanced product description using Claude
        
        Args:
            product_data: Dictionary containing product information
        
        Returns:
            Enhanced description
        """
        system_prompt = (
            "You are a helpful e-commerce assistant. Generate concise, "
            "engaging product descriptions based on product data."
        )
        
        user_message = (
            f"Generate a brief, engaging description for this product:\n"
            f"Name: {product_data.get('product_description', 'N/A')}\n"
            f"Category: {product_data.get('category_name', 'N/A')}\n"
            f"Price: ${product_data.get('price', 0)}\n"
            f"Rating: {product_data.get('stars', 0)} stars\n"
            f"Keep it under 100 words."
        )
        
        messages = [{"role": "user", "content": user_message}]
        
        return await self.chat_completion(
            messages=messages,
            system=system_prompt,
            max_tokens=500,
            temperature=0.7
        )
    
    def health_check(self) -> bool:
        """Check if Bedrock chat service is accessible"""
        try:
            # Try a minimal chat completion
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response["body"].read())
            return "content" in response_body
            
        except Exception as e:
            logger.error(f"Bedrock chat health check failed: {e}")
            return False