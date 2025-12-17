"""Unit tests for validators module."""
import pytest
from werkzeug.datastructures import FileStorage
from io import BytesIO
from validators import (
    ValidationError,
    validate_file_upload,
    validate_template_data,
    validate_student_info,
    validate_answers,
    validate_google_sheets_url,
    sanitize_filename,
    validate_api_key,
    validate_pagination,
)


class TestFileUpload:
    """Tests for file upload validation."""
    
    def test_valid_pdf_upload(self):
        """Test valid PDF file upload."""
        file = FileStorage(
            stream=BytesIO(b"fake pdf content"),
            filename="test.pdf",
            content_type="application/pdf"
        )
        # Should not raise
        validate_file_upload(file, {'pdf', 'png'})
    
    def test_empty_filename(self):
        """Test empty filename raises error."""
        file = FileStorage(stream=BytesIO(b"content"), filename="")
        with pytest.raises(ValidationError, match="Файл не выбран"):
            validate_file_upload(file, {'pdf'})
    
    def test_invalid_extension(self):
        """Test invalid file extension raises error."""
        file = FileStorage(
            stream=BytesIO(b"content"),
            filename="test.exe"
        )
        with pytest.raises(ValidationError, match="Неподдерживаемый формат"):
            validate_file_upload(file, {'pdf', 'png'})
    
    def test_file_too_large(self):
        """Test file size limit."""
        large_content = b"x" * (17 * 1024 * 1024)  # 17MB
        file = FileStorage(
            stream=BytesIO(large_content),
            filename="large.pdf"
        )
        with pytest.raises(ValidationError, match="слишком большой"):
            validate_file_upload(file, {'pdf'}, max_size_mb=16)


class TestTemplateValidation:
    """Tests for template data validation."""
    
    def test_valid_template(self):
        """Test valid template data."""
        data = {
            "name": "Test Template",
            "fields": [
                {
                    "id": "field1",
                    "variants": ["answer1", "answer2"]
                }
            ]
        }
        # Should not raise
        validate_template_data(data)
    
    def test_missing_name(self):
        """Test missing name field."""
        data = {"fields": []}
        with pytest.raises(ValidationError, match="Отсутствует обязательное поле: name"):
            validate_template_data(data)
    
    def test_empty_name(self):
        """Test empty name."""
        data = {"name": "  ", "fields": []}
        with pytest.raises(ValidationError, match="не может быть пустым"):
            validate_template_data(data)
    
    def test_no_fields(self):
        """Test template with no fields."""
        data = {"name": "Test", "fields": []}
        with pytest.raises(ValidationError, match="хотя бы одно поле"):
            validate_template_data(data)
    
    def test_too_many_fields(self):
        """Test template with too many fields."""
        data = {
            "name": "Test",
            "fields": [{"id": f"f{i}", "variants": ["a"]} for i in range(101)]
        }
        with pytest.raises(ValidationError, match="Слишком много полей"):
            validate_template_data(data)


class TestStudentInfo:
    """Tests for student information validation."""
    
    def test_valid_student_info(self):
        """Test valid student info."""
        data = {"name": "Иванов Иван", "class": "10А"}
        # Should not raise
        validate_student_info(data)
    
    def test_missing_name(self):
        """Test missing name."""
        data = {"class": "10А"}
        with pytest.raises(ValidationError, match="Не указано: name"):
            validate_student_info(data)
    
    def test_short_name(self):
        """Test too short name."""
        data = {"name": "А", "class": "10А"}
        with pytest.raises(ValidationError, match="слишком короткое"):
            validate_student_info(data)
    
    def test_invalid_characters_in_name(self):
        """Test invalid characters in name."""
        data = {"name": "Test123", "class": "10А"}
        with pytest.raises(ValidationError, match="недопустимые символы"):
            validate_student_info(data)


class TestAnswersValidation:
    """Tests for answers validation."""
    
    def test_valid_answers(self):
        """Test valid answers."""
        answers = {"field1": "answer1", "field2": "answer2"}
        # Should not raise
        validate_answers(answers)
    
    def test_answers_not_dict(self):
        """Test non-dict answers."""
        with pytest.raises(ValidationError, match="должны быть словарём"):
            validate_answers(["answer1", "answer2"])
    
    def test_answer_too_long(self):
        """Test answer exceeding max length."""
        answers = {"field1": "x" * 501}
        with pytest.raises(ValidationError, match="слишком длинный"):
            validate_answers(answers, max_answer_length=500)


class TestGoogleSheetsUrl:
    """Tests for Google Sheets URL validation."""
    
    def test_valid_url(self):
        """Test valid Google Sheets URL."""
        url = "https://docs.google.com/spreadsheets/d/abc123/edit"
        # Should not raise
        validate_google_sheets_url(url)
    
    def test_empty_url(self):
        """Test empty URL (should be allowed)."""
        # Should not raise
        validate_google_sheets_url("")
    
    def test_invalid_url(self):
        """Test invalid URL."""
        url = "https://example.com/spreadsheet"
        with pytest.raises(ValidationError, match="Некорректная ссылка"):
            validate_google_sheets_url(url)


class TestSanitizeFilename:
    """Tests for filename sanitization."""
    
    def test_basic_sanitization(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("test file.pdf")
        assert result == "test file.pdf"
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention."""
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
    
    def test_dangerous_characters_removed(self):
        """Test dangerous characters are removed."""
        result = sanitize_filename("test<>:|?.pdf")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result


class TestApiKeyValidation:
    """Tests for API key validation."""
    
    def test_valid_gemini_key(self):
        """Test valid Gemini API key."""
        key = "AIzaSyB3b0OZunDascOfvHDLqJydDfN56ml1SnY"
        # Should not raise
        validate_api_key(key, "gemini")
    
    def test_placeholder_key(self):
        """Test placeholder key raises error."""
        with pytest.raises(ValidationError, match="не настроен"):
            validate_api_key("YOUR_API_KEY_HERE", "gemini")
    
    def test_short_key(self):
        """Test too short key."""
        with pytest.raises(ValidationError, match="слишком короткий"):
            validate_api_key("short", "gemini")
    
    def test_invalid_gemini_format(self):
        """Test invalid Gemini key format."""
        with pytest.raises(ValidationError, match="Некорректный формат"):
            validate_api_key("invalid_key_format_but_long_enough", "gemini")


class TestPagination:
    """Tests for pagination validation."""
    
    def test_valid_pagination(self):
        """Test valid pagination parameters."""
        page, per_page = validate_pagination(1, 20)
        assert page == 1
        assert per_page == 20
    
    def test_invalid_page_number(self):
        """Test invalid page number."""
        with pytest.raises(ValidationError, match="должен быть >= 1"):
            validate_pagination(0, 20)
    
    def test_too_many_per_page(self):
        """Test too many items per page."""
        with pytest.raises(ValidationError, match="Максимум"):
            validate_pagination(1, 200, max_per_page=100)
