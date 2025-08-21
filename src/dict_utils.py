"""
Dictionary utilities for Chinese-English translation lookup.
"""

import json
import re
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class ChineseDict:
    """Chinese-English dictionary with multiple data sources."""
    
    def __init__(self):
        self.mini_dict: Dict[str, List[str]] = {}
        self.cedict_data: Dict[str, List[str]] = {}
        self.loaded_sources = []
    
    def load_mini_dict(self, path: str) -> bool:
        """
        Load the mini dictionary JSON file.
        
        Args:
            path: Path to mini_cedict.json
            
        Returns:
            True if loaded successfully
        """
        try:
            if not os.path.exists(path):
                print(f"Warning: Mini dictionary not found at {path}")
                return False
                
            with open(path, 'r', encoding='utf-8') as f:
                self.mini_dict = json.load(f)
            
            self.loaded_sources.append(f"Mini dict: {len(self.mini_dict)} entries")
            return True
            
        except Exception as e:
            print(f"Error loading mini dictionary: {e}")
            return False
    
    def load_cedict_file(self, path: str) -> bool:
        """
        Load full CEDICT file (cedict_ts.u8 format).
        
        Args:
            path: Path to cedict_ts.u8 file
            
        Returns:
            True if loaded successfully
        """
        try:
            if not os.path.exists(path):
                print(f"Warning: CEDICT file not found at {path}")
                return False
            
            self.cedict_data = {}
            entry_count = 0
            
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse CEDICT format: Traditional Simplified [pinyin] /definition1/definition2/
                    match = re.match(r'^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/$', line)
                    if match:
                        traditional, simplified, pinyin, definitions = match.groups()
                        
                        # Split definitions by '/'
                        def_list = [d.strip() for d in definitions.split('/') if d.strip()]
                        
                        # Store both traditional and simplified forms
                        for hanzi in [traditional, simplified]:
                            if hanzi not in self.cedict_data:
                                self.cedict_data[hanzi] = def_list
                            else:
                                # Merge definitions, avoiding duplicates
                                existing = set(self.cedict_data[hanzi])
                                for def_item in def_list:
                                    if def_item not in existing:
                                        self.cedict_data[hanzi].append(def_item)
                        
                        entry_count += 1
            
            self.loaded_sources.append(f"CEDICT: {entry_count} entries, {len(self.cedict_data)} unique hanzi")
            return True
            
        except Exception as e:
            print(f"Error loading CEDICT file: {e}")
            return False
    
    def lookup_translation(self, word: str, max_definitions: int = 3) -> Optional[str]:
        """
        Look up English translation for a Chinese word.
        
        Args:
            word: Chinese word to translate
            max_definitions: Maximum number of definitions to return
            
        Returns:
            English translation or None if not found
        """
        if not word or not word.strip():
            return None
        
        word = word.strip()
        
        # First try mini dictionary (higher quality, curated)
        if word in self.mini_dict:
            definitions = self.mini_dict[word][:max_definitions]
            return "; ".join(definitions)
        
        # Then try CEDICT
        if word in self.cedict_data:
            definitions = self.cedict_data[word][:max_definitions]
            # Clean up CEDICT definitions (remove technical markers)
            cleaned_defs = []
            for def_item in definitions:
                # Remove classifiers and technical markers
                cleaned = re.sub(r'\(.*?\)', '', def_item)  # Remove parentheses
                cleaned = re.sub(r'\[.*?\]', '', cleaned)   # Remove brackets
                cleaned = cleaned.strip()
                if cleaned and cleaned not in cleaned_defs:
                    cleaned_defs.append(cleaned)
            
            if cleaned_defs:
                return "; ".join(cleaned_defs[:max_definitions])
        
        # Try character-by-character lookup for multi-character words
        if len(word) > 1:
            char_translations = []
            for char in word:
                char_trans = self.lookup_translation(char, max_definitions=1)
                if char_trans:
                    char_translations.append(char_trans)
            
            if char_translations:
                return " + ".join(char_translations)
        
        return None

    def get_all_translations(self, word: str, max_definitions: int = 3) -> Dict[str, Optional[str]]:
        """
        Get translations from all available dictionary sources.

        Args:
            word: Chinese word to translate
            max_definitions: Maximum number of definitions per source

        Returns:
            Dictionary mapping source names to their translations
        """
        if not word or not word.strip():
            return {}

        word = word.strip()
        translations = {}

        # Mini Dictionary
        if word in self.mini_dict:
            definitions = self.mini_dict[word][:max_definitions]
            translations['mini'] = "; ".join(definitions)

        # CEDICT with cleaning
        if word in self.cedict_data:
            definitions = self.cedict_data[word][:max_definitions]
            cleaned_defs = []

            def is_english_only(text):
                """Check if text contains only English characters, punctuation, and spaces."""
                allowed_pattern = r'^[a-zA-Z0-9\s\.,;:\-\'\"!?()]+$'
                return bool(re.match(allowed_pattern, text))

            for def_item in definitions:
                # Split by semicolon to handle individual definitions
                parts = [part.strip() for part in def_item.split(';')]

                for part in parts:
                    if not part:
                        continue

                    # Remove brackets and parentheses content first
                    cleaned = re.sub(r'\([^)]*\)', '', part)
                    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
                    cleaned = cleaned.strip()

                    # Skip if contains non-English characters
                    if not is_english_only(cleaned):
                        continue

                    # Skip technical markers and low-value definitions
                    if any(marker in cleaned.lower() for marker in [
                        'used in', 'abbr for', 'abbr.', 'cl:', 'surname',
                        'see also', 'variant of', '...'
                    ]):
                        continue

                    # Keep meaningful English definitions
                    if len(cleaned) > 2 and cleaned not in cleaned_defs:
                        cleaned_defs.append(cleaned)

            if cleaned_defs:
                translations['cedict'] = "; ".join(cleaned_defs[:max_definitions])

        # Custom dictionaries (if any)
        if hasattr(self, 'custom_dicts'):
            for dict_name, dict_data in self.custom_dicts.items():
                if word in dict_data:
                    definitions = dict_data[word][:max_definitions]
                    translations[dict_name] = "; ".join(definitions)

        return translations

    def lookup_translation_mixed(self, word: str, max_definitions: int = 3) -> Optional[str]:
        """
        Look up English translation using mixed strategy (combine all available dictionary sources).

        Args:
            word: Chinese word to translate
            max_definitions: Maximum number of definitions to return per source

        Returns:
            English translation combining all sources or None if not found
        """
        if not word or not word.strip():
            return None

        word = word.strip()

        # Get translations from all available sources
        all_translations = self.get_all_translations(word, max_definitions)

        # Extract translation strings in priority order (mini first, then others)
        translation_values = []

        # Add mini dictionary first (highest priority)
        if 'mini' in all_translations:
            translation_values.append(all_translations['mini'])

        # Add CEDICT
        if 'cedict' in all_translations:
            translation_values.append(all_translations['cedict'])

        # Add any custom dictionaries
        for source_name, translation in all_translations.items():
            if source_name not in ['mini', 'cedict']:
                translation_values.append(translation)

        # Use shared translation combining logic for multiple sources
        from services.translation import combine_translations_smart
        result = combine_translations_smart(*translation_values)

        # If we got a result from dictionaries, return it
        if result:
            return result

        # Fallback to character-by-character lookup
        if len(word) > 1:
            char_translations = []
            for char in word:
                char_trans = self.lookup_translation(char, max_definitions=1)
                if char_trans:
                    char_translations.append(char_trans)

            if char_translations:
                return " + ".join(char_translations)

        return None

    def add_custom_dictionary(self, name: str, data: Dict[str, List[str]]) -> bool:
        """
        Add a custom dictionary source.

        Args:
            name: Name of the dictionary source
            data: Dictionary mapping Chinese words to lists of English definitions

        Returns:
            True if added successfully
        """
        if not hasattr(self, 'custom_dicts'):
            self.custom_dicts = {}

        self.custom_dicts[name] = data
        self.loaded_sources.append(f"Custom dict '{name}': {len(data)} entries")
        return True

    def get_word_info(self, word: str) -> Dict[str, any]:
        """
        Get comprehensive information about a word.
        
        Args:
            word: Chinese word to analyze
            
        Returns:
            Dictionary with word information
        """
        info = {
            'word': word,
            'translation': None,
            'source': None,
            'alternatives': [],
            'character_count': len(word),
            'found': False
        }
        
        # Check mini dictionary first
        if word in self.mini_dict:
            info['translation'] = "; ".join(self.mini_dict[word][:3])
            info['source'] = 'mini_dict'
            info['alternatives'] = self.mini_dict[word][3:] if len(self.mini_dict[word]) > 3 else []
            info['found'] = True
        
        # Check CEDICT
        elif word in self.cedict_data:
            definitions = self.cedict_data[word][:3]
            cleaned_defs = []
            for def_item in definitions:
                cleaned = re.sub(r'\(.*?\)|\[.*?\]', '', def_item).strip()
                if cleaned:
                    cleaned_defs.append(cleaned)
            
            if cleaned_defs:
                info['translation'] = "; ".join(cleaned_defs)
                info['source'] = 'cedict'
                info['alternatives'] = self.cedict_data[word][3:] if len(self.cedict_data[word]) > 3 else []
                info['found'] = True
        
        # Character-by-character fallback
        if not info['found'] and len(word) > 1:
            char_info = []
            for char in word:
                char_trans = self.lookup_translation(char, max_definitions=1)
                if char_trans:
                    char_info.append(f"{char}({char_trans})")
            
            if char_info:
                info['translation'] = " + ".join(char_info)
                info['source'] = 'character_breakdown'
                info['found'] = True
        
        return info
    
    def get_statistics(self) -> Dict[str, any]:
        """Get dictionary statistics."""
        return {
            'mini_dict_entries': len(self.mini_dict),
            'cedict_entries': len(self.cedict_data),
            'total_entries': len(self.mini_dict) + len(self.cedict_data),
            'loaded_sources': self.loaded_sources
        }


def create_default_dict(data_dir: str = "data") -> ChineseDict:
    """
    Create a dictionary instance with default data sources.
    
    Args:
        data_dir: Directory containing dictionary files
        
    Returns:
        Configured ChineseDict instance
    """
    dict_instance = ChineseDict()
    
    # Load mini dictionary
    mini_path = os.path.join(data_dir, "mini_cedict.json")
    dict_instance.load_mini_dict(mini_path)
    
    # Try to load full CEDICT if available
    cedict_path = os.path.join(data_dir, "cedict_ts.txt")
    if os.path.exists(cedict_path):
        dict_instance.load_cedict_file(cedict_path)
    else:
        # Fallback to compressed version
        cedict_gz_path = os.path.join(data_dir, "cedict_ts.u8")
        if os.path.exists(cedict_gz_path):
            dict_instance.load_cedict_file(cedict_gz_path)
    
    return dict_instance


if __name__ == "__main__":
    # Test the dictionary
    print("Testing dictionary functionality...")
    
    # Create dictionary instance
    dict_obj = create_default_dict("../data")
    
    # Test words
    test_words = ["爱", "家", "朋友", "水", "火", "山", "不存在的词"]
    
    print("\nDictionary statistics:")
    stats = dict_obj.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nTranslation tests:")
    for word in test_words:
        translation = dict_obj.lookup_translation(word)
        info = dict_obj.get_word_info(word)
        
        print(f"{word}: {translation}")
        if info['source']:
            print(f"  Source: {info['source']}")
        if info['alternatives']:
            print(f"  Alternatives: {info['alternatives']}")
        print()
