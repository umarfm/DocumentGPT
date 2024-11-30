import os
from typing import List, Dict
import hashlib
from datetime import datetime
import json
from pathlib import Path
from collections import Counter
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

class DocumentService:
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self.index_path = Path(storage_dir) / "document_index.json"
        self.document_index = self._load_index()
        
        # Initialize NLTK components
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
        
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
    
    def _preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for better matching."""
        # Convert to lowercase and tokenize
        tokens = word_tokenize(text.lower())
        
        # Remove stopwords and lemmatize
        tokens = [
            self.lemmatizer.lemmatize(token)
            for token in tokens
            if token not in self.stop_words and token.isalnum()
        ]
        
        return tokens
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract potential key phrases from text."""
        # Simple regex for identifying potential key phrases
        phrase_pattern = r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)|(?:[A-Z]{2,}(?:\s+[A-Z]{2,})*)'
        key_phrases = re.findall(phrase_pattern, text)
        return [phrase.lower() for phrase in key_phrases]
    
    def process_document(self, filepath: str) -> Dict:
        """Process and index a document with improved text analysis."""
        filename = os.path.basename(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
        except UnicodeDecodeError:
            # Try different encodings if UTF-8 fails
            encodings = ['latin-1', 'iso-8859-1', 'cp1252']
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as file:
                        content = file.read()
                    break
                except UnicodeDecodeError:
                    continue
        
        # Split into paragraphs and process each
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        paragraph_data = []
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # Create unique ID for paragraph
                para_hash = hashlib.md5(paragraph.encode()).hexdigest()[:8]
                para_id = f"{filename}-p{i}-{para_hash}"
                
                # Process paragraph text
                tokens = self._preprocess_text(paragraph)
                key_phrases = self._extract_key_phrases(paragraph)
                
                paragraph_data.append({
                    'id': para_id,
                    'content': paragraph,
                    'position': i,
                    'char_start': content.find(paragraph),
                    'char_end': content.find(paragraph) + len(paragraph),
                    'tokens': tokens,
                    'key_phrases': key_phrases
                })
        
        # Store document metadata
        doc_metadata = {
            'filepath': filepath,
            'filename': filename,
            'paragraphs': paragraph_data,
            'last_updated': datetime.now().isoformat(),
            'total_paragraphs': len(paragraph_data)
        }
        
        self.document_index[filename] = doc_metadata
        self._save_index()
        
        return doc_metadata
    
    def find_relevant_sections(self, question: str) -> List[Dict]:
        """Find relevant sections with improved matching algorithm."""
        # Preprocess question
        question_tokens = self._preprocess_text(question)
        question_phrases = self._extract_key_phrases(question)
        
        relevant_sections = []
        
        for doc_name, doc_data in self.document_index.items():
            for para in doc_data['paragraphs']:
                # Calculate relevance score
                token_match_score = len(
                    set(question_tokens) & set(para['tokens'])
                ) / max(len(question_tokens), 1)
                
                phrase_match_score = len(
                    set(question_phrases) & set(para['key_phrases'])
                ) / max(len(question_phrases), 1) if question_phrases else 0
                
                # Weight exact phrase matches more heavily
                for phrase in question_phrases:
                    if phrase in para['content'].lower():
                        phrase_match_score += 0.5
                
                # Combined score with weights
                relevance_score = (token_match_score * 0.6) + (phrase_match_score * 0.4)
                
                # Include context from surrounding paragraphs if highly relevant
                if relevance_score > 0.2:
                    relevant_sections.append({
                        'content': para['content'],
                        'source': {
                            'document': doc_name,
                            'paragraph_id': para['id'],
                            'position': para['position'],
                            'char_start': para['char_start'],
                            'char_end': para['char_end']
                        },
                        'relevance_score': relevance_score
                    })
                    
                    # Add surrounding paragraphs for context if available
                    if relevance_score > 0.4:
                        for offset in [-1, 1]:
                            pos = para['position'] + offset
                            if 0 <= pos < len(doc_data['paragraphs']):
                                context_para = doc_data['paragraphs'][pos]
                                relevant_sections.append({
                                    'content': context_para['content'],
                                    'source': {
                                        'document': doc_name,
                                        'paragraph_id': context_para['id'],
                                        'position': context_para['position'],
                                        'char_start': context_para['char_start'],
                                        'char_end': context_para['char_end']
                                    },
                                    'relevance_score': relevance_score * 0.5  # Lower score for context
                                })
        
        # Sort by relevance and remove duplicates
        relevant_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
        seen_paragraphs = set()
        unique_sections = []
        
        for section in relevant_sections:
            para_id = section['source']['paragraph_id']
            if para_id not in seen_paragraphs:
                unique_sections.append(section)
                seen_paragraphs.add(para_id)
        
        return unique_sections[:5]  # Return top 5 most relevant sections

    def _load_index(self) -> dict:
        """Load existing document index or create new one."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index(self) -> None:
        """Save current index to disk."""
        with open(self.index_path, 'w') as f:
            json.dump(self.document_index, f)