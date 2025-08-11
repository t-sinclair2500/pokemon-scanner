"""Regular expressions for Pokemon card text extraction."""

import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class CardPattern:
    """Represents a card information pattern."""
    name: str
    pattern: re.Pattern
    description: str


class PokemonCardRegexes:
    """Collection of regex patterns for Pokemon card text extraction."""
    
    def __init__(self):
        # Collector number pattern: matches formats like "4/102", "25/25", "123/165"
        self.collector_number = re.compile(r'\b(\d{1,3})\s*/\s*(\d{1,3})\b')
        
        # Set code pattern: matches 3-4 letter codes like "base", "BS", "NEO1"
        self.set_code = re.compile(r'\b([A-Z]{2,4}\d?)\b')
        
        # Pokemon name pattern: starts with capital letter, may include special chars
        self.pokemon_name = re.compile(r'^([A-Z][a-zA-Z\s\-\'\.&]{2,20})')
        
        # HP pattern: matches "HP 120", "120 HP", etc.
        self.hp = re.compile(r'(?:HP\s*)?(\d{1,3})(?:\s*HP)?')
        
        # Card type patterns
        self.basic_pokemon = re.compile(r'\bBasic\b', re.IGNORECASE)
        self.evolution_stage = re.compile(r'\b(Stage\s*[12]|Basic|Baby)\b', re.IGNORECASE)
        self.trainer_card = re.compile(r'\b(Trainer|Supporter|Stadium|Item)\b', re.IGNORECASE)
        self.energy_card = re.compile(r'\b(Basic\s*Energy|Special\s*Energy|Energy)\b', re.IGNORECASE)
        
        # Rarity symbols (often appear as special characters)
        self.rarity = re.compile(r'[◊●★♦♠♣♥]|(?:Common|Uncommon|Rare|Ultra\s*Rare|Secret\s*Rare)')
        
        # Copyright and year
        self.copyright = re.compile(r'©\s*(\d{4})')
        self.year = re.compile(r'\b(19|20)\d{2}\b')
        
        # Card text cleaning patterns
        self.noise_chars = re.compile(r'[^\w\s\-\/\.\,\(\)\:]')
        self.multiple_spaces = re.compile(r'\s+')
        
        # Promo and special patterns
        self.promo = re.compile(r'\b(PROMO|Promo)\b')
        self.holographic = re.compile(r'\b(Holo|Holographic|Holofoil)\b', re.IGNORECASE)
        
    def extract_collector_number(self, text: str) -> Optional[Dict[str, int]]:
        """Extract collector number from text."""
        match = self.collector_number.search(text)
        if match:
            return {
                'number': int(match.group(1)),
                'total': int(match.group(2))
            }
        return None
    
    def extract_pokemon_name(self, text: str) -> Optional[str]:
        """Extract Pokemon name from text."""
        # Clean the text first
        cleaned = self.clean_text(text)
        lines = cleaned.split('\n')
        
        for line in lines[:3]:  # Check first few lines
            line = line.strip()
            if len(line) > 2:
                match = self.pokemon_name.match(line)
                if match:
                    name = match.group(1).strip()
                    # Filter out common OCR errors
                    if self._is_valid_pokemon_name(name):
                        return name
        return None
    
    def extract_hp(self, text: str) -> Optional[int]:
        """Extract HP value from text."""
        matches = self.hp.findall(text)
        for match in matches:
            hp = int(match)
            if 10 <= hp <= 350:  # Reasonable HP range
                return hp
        return None
    
    def extract_set_info(self, text: str) -> Dict[str, Any]:
        """Extract set-related information."""
        info = {}
        
        # Collector number
        collector = self.extract_collector_number(text)
        if collector:
            info['collector_number'] = collector
        
        # Set code
        set_match = self.set_code.search(text)
        if set_match:
            info['set_code'] = set_match.group(1)
        
        # Copyright year
        year_match = self.copyright.search(text)
        if year_match:
            info['year'] = int(year_match.group(1))
        else:
            year_match = self.year.search(text)
            if year_match:
                info['year'] = int(year_match.group(0))
        
        # Promo
        if self.promo.search(text):
            info['is_promo'] = True
        
        return info
    
    def identify_card_type(self, text: str) -> str:
        """Identify the type of card."""
        text_lower = text.lower()
        
        if self.trainer_card.search(text):
            return 'trainer'
        elif self.energy_card.search(text):
            return 'energy'
        elif self.evolution_stage.search(text):
            return 'pokemon'
        else:
            # Default to pokemon if we find HP or typical pokemon patterns
            if self.hp.search(text) or any(word in text_lower for word in ['attack', 'weakness', 'resistance']):
                return 'pokemon'
            return 'unknown'
    
    def clean_text(self, text: str) -> str:
        """Clean OCR text for better processing."""
        # Remove noise characters but keep useful punctuation
        cleaned = self.noise_chars.sub(' ', text)
        # Normalize whitespace
        cleaned = self.multiple_spaces.sub(' ', cleaned)
        # Strip and return
        return cleaned.strip()
    
    def _is_valid_pokemon_name(self, name: str) -> bool:
        """Check if extracted name looks like a valid Pokemon name."""
        # Filter out common OCR errors and non-names
        invalid_patterns = [
            r'^\d+$',  # Just numbers
            r'^[A-Z]{1}$',  # Single letter
            r'HP',  # HP text
            r'Stage',  # Stage text
            r'Basic',  # Basic text
            r'Trainer',  # Trainer text
            r'Energy',  # Energy text
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return False
        
        # Must be reasonable length
        return 3 <= len(name) <= 25
    
    def extract_all_patterns(self, text: str) -> Dict[str, Any]:
        """Extract all recognizable patterns from text."""
        result = {
            'raw_text': text,
            'cleaned_text': self.clean_text(text),
            'card_type': self.identify_card_type(text),
        }
        
        # Extract specific fields
        name = self.extract_pokemon_name(text)
        if name:
            result['name'] = name
        
        hp = self.extract_hp(text)
        if hp:
            result['hp'] = hp
        
        # Merge set info
        result.update(self.extract_set_info(text))
        
        return result


# Global instance
pokemon_regexes = PokemonCardRegexes()
