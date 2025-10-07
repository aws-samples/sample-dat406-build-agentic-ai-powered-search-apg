"""
Embeddings service for DAT406 Workshop

Generates vector embeddings using Amazon Titan Text Embeddings v2 via Bedrock.
Provides async embedding generation for search queries and documents.
"""

import logging
from typing import List

import boto3
import json
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using Amazon Titan v2.
    
    Titan Text Embeddings v2 generates 1024-dimensional vectors optimized
    for semantic search and retrieval tasks.
    """
    
    def __init__(self):
        """Initialize embeddings service with Bedrock client."""
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION
        )
        self.model_id = settings.BEDROCK_EMBEDDING_MODEL
        self.embedding_dimension = 1024
        
        logger.info(f"Initialized embeddings service: {self.model_id}")
    
    def generate_embedding(
        self,
        text: str,
        normalize: bool = True,
    ) -> List[float]:
        """
        Generate embedding vector for a single text string.
        
        Args:
            text: Input text to embed
            normalize: Whether to normalize the embedding vector
            
        Returns:
            List of floats representing the embedding vector (1024 dimensions)
            
        Raises:
            ValueError: If text is empty or invalid
            ClientError: If Bedrock API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Truncate if too long (Titan v2 has input limits)
        max_length = 8192  # characters
        text = text[:max_length].strip()
        
        try:
            # Prepare request body for Titan
            request_body = {
                "inputText": text
            }
            
            # Call Bedrock API
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract embedding vector (Titan format)
            embedding = response_body.get('embedding', [])
            
            if not embedding or len(embedding) != self.embedding_dimension:
                raise ValueError(
                    f"Invalid embedding dimension: expected {self.embedding_dimension}, "
                    f"got {len(embedding)}"
                )
            
            return embedding
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Bedrock API error ({error_code}): {error_message}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        normalize: bool = True,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Note: Titan v2 doesn't support native batch processing, so this
        method calls the API sequentially. For production, consider
        implementing async batch processing with rate limiting.
        
        Args:
            texts: List of input texts
            normalize: Whether to normalize embedding vectors
            
        Returns:
            List of embedding vectors, one per input text
        """
        if not texts:
            return []
        
        embeddings = []
        errors = []
        
        for i, text in enumerate(texts):
            try:
                embedding = self.generate_embedding(text, normalize=normalize)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Error embedding text {i}: {e}")
                errors.append((i, str(e)))
                # Append zero vector as placeholder
                embeddings.append([0.0] * self.embedding_dimension)
        
        if errors:
            logger.warning(
                f"Failed to generate {len(errors)} embeddings out of {len(texts)}"
            )
        
        return embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Convenience method that applies query-specific preprocessing.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector for the query
        """
        # Clean and preprocess query
        query = query.strip()
        
        if not query:
            raise ValueError("Query cannot be empty")
        
        # Generate embedding
        return self.generate_embedding(query, normalize=True)
    
    def embed_document(self, document: str) -> List[float]:
        """
        Generate embedding for a document.
        
        Convenience method that applies document-specific preprocessing.
        
        Args:
            document: Document text to embed
            
        Returns:
            Embedding vector for the document
        """
        # Clean and preprocess document
        document = document.strip()
        
        if not document:
            raise ValueError("Document cannot be empty")
        
        # Generate embedding
        return self.generate_embedding(document, normalize=True)
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embedding vectors.
        
        Returns:
            int: Embedding dimension (1024 for Titan v2)
        """
        return self.embedding_dimension
    
    def get_model_id(self) -> str:
        """
        Get the Bedrock model ID being used.
        
        Returns:
            str: Model ID
        """
        return self.model_id
    
    def health_check(self) -> dict:
        """
        Check if embeddings service is healthy.
        
        Performs a test embedding generation to verify Bedrock connectivity.
        
        Returns:
            dict: Health check results
        """
        try:
            # Generate test embedding
            test_text = "test"
            embedding = self.generate_embedding(test_text)
            
            return {
                "status": "healthy",
                "model_id": self.model_id,
                "embedding_dimension": len(embedding),
                "region": settings.AWS_REGION
            }
            
        except Exception as e:
            logger.error(f"Embeddings health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "model_id": self.model_id
            }