"""
Property-based tests for video format validation

Feature: collision-detection-web, Property 10: Video Format Validation
Validates: Requirements 8.1
"""
import os
import tempfile
from hypothesis import given, strategies as st
import pytest

from collision_server.utils import allowed_file, validate_video_format, get_supported_formats


class TestVideoFormatValidation:
    """Property-based tests for video format validation"""
    
    def test_supported_formats_list(self):
        """Test that supported formats list is consistent"""
        formats = get_supported_formats()
        expected_formats = {'.mp4', '.avi', '.mov', '.webm'}
        assert set(formats) == expected_formats
    
    @given(st.text(min_size=1, max_size=50).filter(lambda x: not x.endswith('.') and not x.startswith('.') and '/' not in x and '\\' not in x))
    def test_property_10_video_format_validation_valid_extensions(self, base_name):
        """
        Property 10: Video Format Validation
        For any filename with a supported extension, allowed_file should return True
        **Validates: Requirements 8.1**
        """
        # Test with each supported format
        supported_formats = ['.mp4', '.avi', '.mov', '.webm']
        
        for ext in supported_formats:
            # Create filename with supported extension
            filename = f"{base_name}{ext}"
            
            # Should be allowed
            assert allowed_file(filename) == True, f"File with extension {ext} should be allowed"
            
            # Test case insensitive
            filename_upper = f"{base_name}{ext.upper()}"
            assert allowed_file(filename_upper) == True, f"File with uppercase extension {ext.upper()} should be allowed"
    
    @given(st.text(min_size=1, max_size=50).filter(lambda x: not x.endswith('.') and not x.startswith('.') and '/' not in x and '\\' not in x))
    def test_property_10_video_format_validation_invalid_extensions(self, base_name):
        """
        Property 10: Video Format Validation
        For any filename with an unsupported extension, allowed_file should return False
        **Validates: Requirements 8.1**
        """
        # Test with unsupported formats
        unsupported_formats = ['.txt', '.jpg', '.png', '.pdf', '.doc', '.zip', '.exe', '.mkv', '.flv']
        
        for ext in unsupported_formats:
            filename = f"{base_name}{ext}"
            
            # Should not be allowed
            assert allowed_file(filename) == False, f"File with extension {ext} should not be allowed"
    
    @given(st.text(min_size=0, max_size=50))
    def test_property_10_video_format_validation_no_extension(self, filename):
        """
        Property 10: Video Format Validation
        For any filename without an extension, allowed_file should return False
        **Validates: Requirements 8.1**
        """
        # Ensure filename has no extension
        if '.' in filename:
            filename = filename.replace('.', '_')
        
        # Should not be allowed
        assert allowed_file(filename) == False, f"File without extension should not be allowed: {filename}"
    
    def test_property_10_video_format_validation_empty_filename(self):
        """
        Property 10: Video Format Validation
        For empty or None filename, allowed_file should return False
        **Validates: Requirements 8.1**
        """
        assert allowed_file("") == False, "Empty filename should not be allowed"
        assert allowed_file(None) == False, "None filename should not be allowed"
    
    @given(st.text(min_size=1, max_size=50).filter(lambda x: not x.endswith('.') and not x.startswith('.') and '/' not in x and '\\' not in x))
    def test_property_10_video_format_validation_multiple_extensions(self, base_name):
        """
        Property 10: Video Format Validation
        For filenames with multiple extensions, only the last extension should matter
        **Validates: Requirements 8.1**
        """
        # Test with valid extension at the end
        filename_valid = f"{base_name}.txt.mp4"
        assert allowed_file(filename_valid) == True, "File ending with valid extension should be allowed"
        
        # Test with invalid extension at the end
        filename_invalid = f"{base_name}.mp4.txt"
        assert allowed_file(filename_invalid) == False, "File ending with invalid extension should not be allowed"
    
    def test_property_10_video_format_validation_file_existence(self):
        """
        Property 10: Video Format Validation
        validate_video_format should return False for non-existent files regardless of extension
        **Validates: Requirements 8.1**
        """
        # Test with supported extensions but non-existent files
        supported_formats = ['.mp4', '.avi', '.mov', '.webm']
        
        for ext in supported_formats:
            non_existent_file = f"/non/existent/path/test{ext}"
            assert validate_video_format(non_existent_file) == False, f"Non-existent file should not validate: {non_existent_file}"
    
    def test_property_10_video_format_validation_consistency(self):
        """
        Property 10: Video Format Validation
        allowed_file and validate_video_format should be consistent for file extension checking
        **Validates: Requirements 8.1**
        """
        test_cases = [
            ("test.mp4", True),
            ("test.avi", True),
            ("test.mov", True),
            ("test.webm", True),
            ("test.txt", False),
            ("test.jpg", False),
            ("test", False),
            ("", False)
        ]
        
        for filename, expected in test_cases:
            allowed_result = allowed_file(filename)
            assert allowed_result == expected, f"allowed_file({filename}) should return {expected}, got {allowed_result}"
            
            # For non-existent files, validate_video_format should return False regardless
            # This tests the file existence check part of validation
            if filename:  # Skip empty filename for file path test
                validate_result = validate_video_format(filename)
                assert validate_result == False, f"validate_video_format should return False for non-existent file: {filename}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])