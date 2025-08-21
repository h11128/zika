import pytest
from src.dict_utils import ChineseDict


class TestMultiDictionary:
    
    def test_add_custom_dictionary(self):
        """Test adding custom dictionaries."""
        dict_obj = ChineseDict()
        
        custom_dict = {
            '测试': ['test', 'examination'],
            '爱': ['love', 'affection']
        }
        
        result = dict_obj.add_custom_dictionary('technical', custom_dict)
        assert result is True
        assert hasattr(dict_obj, 'custom_dicts')
        assert 'technical' in dict_obj.custom_dicts
        assert dict_obj.custom_dicts['technical'] == custom_dict
        assert "Custom dict 'technical': 2 entries" in dict_obj.loaded_sources
    
    def test_get_all_translations_mini_only(self):
        """Test get_all_translations with only mini dictionary."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'爱': ['love', 'to love']}
        
        result = dict_obj.get_all_translations('爱')
        expected = {'mini': 'love; to love'}
        assert result == expected
    
    def test_get_all_translations_multiple_sources(self):
        """Test get_all_translations with multiple sources."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'爱': ['love', 'to love']}
        dict_obj.cedict_data = {'爱': ['to love', 'to be fond of', 'to like']}
        
        # Add custom dictionary
        dict_obj.add_custom_dictionary('emotional', {'爱': ['affection', 'romance']})
        
        result = dict_obj.get_all_translations('爱')
        
        assert 'mini' in result
        assert 'cedict' in result
        assert 'emotional' in result
        assert result['mini'] == 'love; to love'
        assert result['emotional'] == 'affection; romance'
    
    def test_get_all_translations_empty_word(self):
        """Test get_all_translations with empty word."""
        dict_obj = ChineseDict()
        
        result = dict_obj.get_all_translations('')
        assert result == {}
        
        result = dict_obj.get_all_translations(None)
        assert result == {}
    
    def test_lookup_translation_mixed_single_source(self):
        """Test mixed lookup with single source."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'爱': ['love', 'to love']}
        
        result = dict_obj.lookup_translation_mixed('爱')
        assert result == 'love; to love'
    
    def test_lookup_translation_mixed_multiple_sources(self):
        """Test mixed lookup with multiple sources."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'爱': ['love']}
        dict_obj.cedict_data = {'爱': ['to be fond of', 'to like']}
        
        result = dict_obj.lookup_translation_mixed('爱')
        assert result == 'love | to be fond of; to like'
    
    def test_lookup_translation_mixed_with_custom_dict(self):
        """Test mixed lookup including custom dictionaries."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'书': ['book']}

        # Add custom dictionary with non-overlapping terms
        dict_obj.add_custom_dictionary('academic', {'书': ['tome', 'manuscript']})

        result = dict_obj.lookup_translation_mixed('书')
        assert result == 'book | tome; manuscript'
    
    def test_lookup_translation_mixed_deduplication(self):
        """Test that mixed lookup removes duplicates."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'测试': ['test']}
        dict_obj.cedict_data = {'测试': ['test', 'examination']}
        
        result = dict_obj.lookup_translation_mixed('测试')
        assert result == 'test | examination'  # 'test' should not be duplicated
    
    def test_lookup_translation_mixed_fallback_to_chars(self):
        """Test mixed lookup falls back to character breakdown."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'爱': ['love'], '情': ['emotion']}  # Both characters available

        result = dict_obj.lookup_translation_mixed('爱情')  # Multi-character word not in dict
        # Should fall back to character-by-character
        assert result == 'love + emotion'
    
    def test_lookup_translation_mixed_no_results(self):
        """Test mixed lookup with no results."""
        dict_obj = ChineseDict()
        
        result = dict_obj.lookup_translation_mixed('不存在')
        assert result is None
    
    def test_multiple_custom_dictionaries(self):
        """Test adding multiple custom dictionaries."""
        dict_obj = ChineseDict()
        
        tech_dict = {'算法': ['algorithm'], '数据': ['information']}
        business_dict = {'管理': ['management'], '数据': ['metrics']}

        dict_obj.add_custom_dictionary('tech', tech_dict)
        dict_obj.add_custom_dictionary('business', business_dict)

        # Test that both dictionaries are available
        result = dict_obj.get_all_translations('数据')
        assert 'tech' in result
        assert 'business' in result
        assert result['tech'] == 'information'
        assert result['business'] == 'metrics'

        # Test mixed lookup combines both
        mixed_result = dict_obj.lookup_translation_mixed('数据')
        assert 'information' in mixed_result
        assert 'metrics' in mixed_result
    
    def test_custom_dict_priority_order(self):
        """Test that custom dictionaries maintain proper priority order."""
        dict_obj = ChineseDict()
        dict_obj.mini_dict = {'爱': ['love']}
        
        dict_obj.add_custom_dictionary('first', {'爱': ['affection']})
        dict_obj.add_custom_dictionary('second', {'爱': ['romance']})
        
        result = dict_obj.lookup_translation_mixed('爱')
        # Should be: mini | first_custom | second_custom
        assert result == 'love | affection | romance'
