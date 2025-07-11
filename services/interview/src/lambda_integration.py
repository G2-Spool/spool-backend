import os
import json
import asyncio
import boto3
from botocore.exceptions import BotoCore3Error, ClientError
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LambdaIntegration:
    """Integration class for invoking spool-create-thread Lambda function"""
    
    def __init__(self):
        self.lambda_client = boto3.client(
            'lambda',
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        self.function_name = 'spool-create-thread'
    
    async def create_thread_from_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a learning thread by invoking the CreateThread Lambda
        
        Args:
            interview_data: Interview session data containing:
                - session_id: Session identifier
                - student_id: User/student ID
                - messages: List of conversation messages
                - extracted_interests: List of extracted interests
                - mode: Interview mode
                - purpose: Interview purpose
                - auth_token: Optional JWT token
        
        Returns:
            Created thread data from Lambda response
        """
        try:
            logger.info(f"[Lambda Integration] Creating thread from interview session: {interview_data.get('session_id')}")
            
            # Transform interview data to thread format
            thread_payload = self.transform_interview_to_thread(interview_data)
            
            # Prepare Lambda invocation payload
            lambda_payload = {
                'httpMethod': 'POST',
                'path': '/create',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': interview_data.get('auth_token', '')
                },
                'body': json.dumps(thread_payload)
            }
            
            # Invoke Lambda function asynchronously
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.lambda_client.invoke(
                    FunctionName=self.function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(lambda_payload)
                )
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read().decode('utf-8'))
            
            if response['StatusCode'] != 200:
                error_msg = response_payload.get('errorMessage', 'Unknown error')
                raise Exception(f"Lambda invocation failed: {error_msg}")
            
            # Parse the Lambda response body
            if isinstance(response_payload, str):
                response_payload = json.loads(response_payload)
            
            result = json.loads(response_payload.get('body', '{}'))
            logger.info(f"[Lambda Integration] Thread created successfully: {result.get('threadId')}")
            
            return result
            
        except ClientError as e:
            logger.error(f"[Lambda Integration] AWS Client error: {e}")
            raise
        except Exception as e:
            logger.error(f"[Lambda Integration] Failed to create thread: {e}")
            raise
    
    def transform_interview_to_thread(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms interview data into thread format for Lambda
        
        Args:
            interview_data: Interview session data
            
        Returns:
            Thread data formatted for Lambda function
        """
        student_id = interview_data.get('student_id')
        messages = interview_data.get('messages', [])
        extracted_interests = interview_data.get('extracted_interests', [])
        mode = interview_data.get('mode')
        purpose = interview_data.get('purpose')
        
        # Extract the main question/topic from the conversation
        user_messages = [m for m in messages if m.get('role') == 'user']
        primary_question = user_messages[0].get('content', 'Learning exploration') if user_messages else 'Learning exploration'
        
        # Generate a title from the conversation
        title = self.generate_thread_title(messages)
        
        # Extract concepts and subjects from the conversation
        analysis = self.analyze_conversation(messages)
        
        return {
            'userId': student_id,
            'title': title,
            'description': primary_question,
            'interests': extracted_interests or [],
            'concepts': analysis.get('concepts', []),
            'subjects': analysis.get('subjects', []),
            'topics': analysis.get('topics', []),
            'status': 'active',
            'metadata': {
                'source': 'interview',
                'sessionId': interview_data.get('session_id'),
                'mode': mode,
                'purpose': purpose
            }
        }
    
    def generate_thread_title(self, messages: List[Dict[str, Any]]) -> str:
        """
        Generates a thread title from conversation messages
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Generated thread title
        """
        user_messages = [m for m in messages if m.get('role') == 'user']
        if not user_messages:
            return 'New Learning Thread'
        
        # Use first user message, truncated to reasonable length
        first_message = user_messages[0].get('content', '')
        if len(first_message) > 100:
            title = first_message[:97] + '...'
        else:
            title = first_message
        
        return title
    
    def analyze_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Analyzes conversation to extract academic concepts
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Dictionary with subjects, topics, and concepts
        """
        analysis = {
            'subjects': [],
            'topics': [],
            'concepts': []
        }
        
        # Combine all message content for analysis
        conversation_text = ' '.join([
            m.get('content', '') for m in messages
        ]).lower()
        
        # Subject detection with keywords
        subject_keywords = {
            'Mathematics': ['math', 'calculus', 'algebra', 'geometry', 'statistics', 'equation', 'theorem'],
            'Physics': ['physics', 'force', 'energy', 'motion', 'quantum', 'gravity', 'momentum'],
            'Chemistry': ['chemistry', 'chemical', 'molecule', 'reaction', 'element', 'compound', 'atom'],
            'Biology': ['biology', 'cell', 'dna', 'evolution', 'organism', 'ecology', 'genetics'],
            'Computer Science': ['programming', 'algorithm', 'code', 'software', 'computer', 'data structure'],
            'History': ['history', 'historical', 'civilization', 'war', 'revolution', 'ancient', 'modern'],
            'Literature': ['literature', 'novel', 'poetry', 'writing', 'author', 'story', 'narrative'],
            'Psychology': ['psychology', 'behavior', 'mind', 'cognitive', 'emotion', 'personality'],
            'Economics': ['economics', 'economy', 'market', 'finance', 'trade', 'supply', 'demand'],
            'Art': ['art', 'painting', 'sculpture', 'drawing', 'artistic', 'gallery', 'museum']
        }
        
        # Check for subject keywords
        for subject, keywords in subject_keywords.items():
            if any(keyword in conversation_text for keyword in keywords):
                analysis['subjects'].append(subject)
        
        # Extract specific concepts based on detected subjects
        concept_mapping = {
            'calculus': ['Derivatives', 'Integrals', 'Limits'],
            'algebra': ['Equations', 'Variables', 'Functions'],
            'physics': ['Motion', 'Forces', 'Energy'],
            'chemistry': ['Reactions', 'Bonds', 'Elements'],
            'programming': ['Algorithms', 'Data Structures', 'Design Patterns'],
            'economics': ['Supply and Demand', 'Market Theory', 'Economic Models']
        }
        
        # Topic extraction
        topic_keywords = {
            'Calculus': ['calculus', 'derivative', 'integral'],
            'Mechanics': ['physics', 'motion', 'force'],
            'Organic Chemistry': ['organic', 'carbon', 'compound'],
            'Genetics': ['gene', 'dna', 'heredity'],
            'Algorithms': ['algorithm', 'sorting', 'searching'],
            'World History': ['history', 'civilization', 'culture'],
            'Literary Analysis': ['literature', 'theme', 'character']
        }
        
        # Check for topics
        for topic, keywords in topic_keywords.items():
            if any(keyword in conversation_text for keyword in keywords):
                analysis['topics'].append(topic)
        
        # Check for concepts
        for keyword, concepts in concept_mapping.items():
            if keyword in conversation_text:
                analysis['concepts'].extend(concepts)
        
        # Remove duplicates
        analysis['subjects'] = list(set(analysis['subjects']))
        analysis['topics'] = list(set(analysis['topics']))
        analysis['concepts'] = list(set(analysis['concepts']))
        
        # Default if nothing detected
        if not analysis['subjects']:
            analysis['subjects'].append('General Learning')
        
        return analysis