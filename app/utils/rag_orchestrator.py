import logging
from typing import List, Dict, Optional, Tuple, Literal

from deprecated import deprecated
from openai import AzureOpenAI, OpenAIError, OpenAI

# Assuming the refactored retriever is in the same directory or installable
from .azure_ai_search_retriever import AzureAISearchRetriever

# Setup basic logging if not configured elsewhere
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@deprecated
class RAGOrchestrator:
    """
    Orchestrates the Retrieval-Augmented Generation (RAG) process using
    an AzureAISearchRetriever instance for retrieval and an Azure OpenAI client
    for generation. Accepts configuration and clients via its constructor.
    Allows customization of system prompt and context formatting.
    """

    DEFAULT_SYSTEM_PROMPT = """You are an AI assistant helping answer questions based on provided documents.
Answer the user's query using *only* the information found in the documents below.
If the documents don't contain the answer, state that clearly.
Cite the source document (e.g., Source: filename.pdf) when possible after the information you use.
Do not make up information."""

    DEFAULT_CONTEXT_TEMPLATE = """--- Document {doc_num} (Source: {source}) ---
{content}"""

    def __init__(self,
                 retriever: AzureAISearchRetriever,
                 chat_client: AzureOpenAI | OpenAI,
                 chat_deployment: str,
                 system_prompt: Optional[str] = None,
                 context_template: Optional[str] = None):
        """
        Initializes the RAG Orchestrator.

        Args:
            retriever: An initialized instance of AzureAISearchRetriever.
            chat_client: An initialized AzureOpenAI client instance for chat completions.
            chat_deployment: The name of the chat model deployment in Azure OpenAI.
            system_prompt: An optional custom system prompt for the LLM.
                           If None, uses DEFAULT_SYSTEM_PROMPT.
            context_template: An optional f-string template for formatting each retrieved document
                              in the context sent to the LLM. Must use placeholders:
                              '{doc_num}', '{source}', '{content}'.
                              If None, uses DEFAULT_CONTEXT_TEMPLATE.
        """
        logger.info("Initializing RAGOrchestrator...")

        if not isinstance(retriever, AzureAISearchRetriever):
            raise TypeError("retriever must be an instance of AzureAISearchRetriever")
        if not isinstance(chat_client, AzureOpenAI) and not isinstance(chat_client, OpenAI):
             raise TypeError("chat_client must be an instance of AzureOpenAI or OpenAI")
        if not chat_deployment:
            raise ValueError("chat_deployment cannot be empty.")

        self.retriever = retriever
        self.chat_client = chat_client
        self.chat_deployment = chat_deployment
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.context_template = context_template or self.DEFAULT_CONTEXT_TEMPLATE

        # Validate placeholders in custom context template
        if context_template:
            try:
                context_template.format(doc_num=1, source="test.txt", content="test")
            except KeyError as e:
                raise ValueError(f"Custom context_template is missing required placeholder: {e}") from e

        logger.info(f"Using System Prompt starting with: \"{self.system_prompt[:100]}...\"")
        logger.info(
            f"Using Context Template: \"{self.context_template.replace('{', '{{').replace('}', '}}')[:100]}...\"") # Log template snippet safely
        logger.info(f"Using Chat Deployment: {self.chat_deployment}")
        logger.info("RAGOrchestrator initialized successfully.")


    def _format_context(self, documents: List[Dict]) -> Tuple[str, List[str]]:
        """Formats retrieved documents into a context string and extracts sources."""
        context_parts = []
        sources = set() # Use a set to store unique sources
        for i, doc in enumerate(documents):
            # Prioritize filepath, then title, then url, then generate an ID
            source_identifier = doc['metadata'].get('filepath') or \
                                doc['metadata'].get('title') or \
                                doc['metadata'].get('url') or \
                                doc['metadata'].get('id') or \
                                f"Document {doc.get('rank', i + 1)}" # Fallback

            sources.add(source_identifier)
            try:
                # Use the instance's context_template
                formatted_doc = self.context_template.format(
                    doc_num=i + 1,
                    source=source_identifier,
                    content=doc.get('content', '')
                )
                context_parts.append(formatted_doc)
            except KeyError as e:
                # This check should ideally be caught in __init__, but log as warning if it slips through
                logger.warning(
                    f"Context_template seems to be missing a required placeholder: {e}. Using default formatting for doc {i + 1}.",
                    exc_info=True)
                # Fallback to default formatting for this document if custom template fails
                context_parts.append(self.DEFAULT_CONTEXT_TEMPLATE.format(
                    doc_num=i + 1,
                    source=source_identifier,
                    content=doc.get('content', '')
                ))
            except Exception as e:
                logger.error(f"Error formatting document {i + 1} using context_template: {e}. Skipping document.",
                             exc_info=True)

        # Join the formatted parts with double newlines for separation
        context_str = "\n\n".join(context_parts)
        return context_str, sorted(list(sources))

    def _build_prompt_messages(self, user_query: str, context: str) -> List[Dict]:
        """Builds the list of messages for the OpenAI Chat API."""
        # Construct the user message including the context
        user_prompt = f"""Based *only* on the following documents, please answer the query.

Query: {user_query}

Documents:
{context}

Answer:
"""
        # Return the structured messages list
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def answer_query(self,
                     user_query: str,
                     top_k_retrieval: int = 3,
                     search_type: Literal["hybrid", "vector", "text"] = "hybrid",
                     use_semantic_ranking: bool = False,
                     temperature: float = 0.7,
                     max_tokens: int = 1000
                     ) -> Tuple[Optional[str], List[str]]:
        """
        Executes the full RAG pipeline: Retrieve, Format Context, Generate Answer.

        Args:
            user_query: The question asked by the user.
            top_k_retrieval: The number of documents to retrieve from the search index.
            search_type: The type of search to perform ('hybrid', 'vector', 'text').
            use_semantic_ranking: Whether to use semantic ranking in the retrieval step.
            temperature: The temperature setting for the chat completion generation.
            max_tokens: The maximum number of tokens for the generated answer.

        Returns:
            A tuple containing:
            - The generated answer string (Optional[str]), or None if generation failed.
            - A list of source identifiers (List[str]) used in the context.
        """
        logger.info(f"Processing query: '{user_query}' using '{search_type}' search (k={top_k_retrieval}, semantic={use_semantic_ranking})")

        # 1. Retrieve Documents
        # Pass semantic ranking flag to retriever's search method
        retrieved_docs = self.retriever.search(
            query_text=user_query,
            top_k=top_k_retrieval,
            search_type=search_type,
            use_semantic_ranking=use_semantic_ranking
            # vector_query=None # Allow retriever to generate if needed
        )

        if not retrieved_docs:
            logger.warning("Retrieval step returned no documents.")
            return "I couldn't find any relevant documents to answer your question.", [] # Provide a user-friendly response

        # 2. Format Context
        context_str, sources = self._format_context(retrieved_docs)
        logger.info(f"Formatted context using {len(sources)} unique sources.")
        logger.debug(f"Context String Snippet:\n{context_str[:500]}...") # Log only a snippet

        # 3. Build Prompt
        messages = self._build_prompt_messages(user_query, context_str)

        # 4. Generate Answer
        try:
            logger.info(f"Sending request to chat deployment '{self.chat_deployment}'...")
            response = self.chat_client.chat.completions.create(
                model=self.chat_deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            answer = response.choices[0].message.content
            logger.info("Received chat completion response.")
            return answer.strip(), sources

        except OpenAIError as e:
            logger.error(f"Azure OpenAI API error during chat completion: {e.code} - {e.message}", exc_info=True)
            # Provide a user-friendly error message, but still return sources
            return f"There was an error generating the answer: {e.message}", sources
        except Exception as e:
            logger.error(f"Unexpected error during chat completion: {e}", exc_info=True)
            return "An unexpected error occurred while generating the answer.", sources