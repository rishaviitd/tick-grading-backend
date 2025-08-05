# Testing Documentation for TickAI Cloudinary Integration

This directory contains comprehensive unit tests and integration tests for the Cloudinary integration in the question parsing module.

## Test Structure

```
testing/
├── README.md                           # This file
├── pytest.ini                         # Pytest configuration
├── requirements-test.txt               # Test dependencies
├── run_tests.py                       # Test runner script
├── test_cloudinary_save.py            # Simple database save test
└── test_cloudinary_integration.py     # Comprehensive unit tests
```

## Test Categories

### 1. Unit Tests (`TestCloudinaryUtils`)

- **Cloudinary Upload Functions**: Test individual upload functions
- **Error Handling**: Test network failures, invalid responses
- **Data Validation**: Test input validation and edge cases

### 2. Database Schema Tests (`TestDatabaseSchema`)

- **Schema Validation**: Test Pydantic model validation
- **Required Fields**: Test required field enforcement
- **Data Types**: Test proper data type handling

### 3. Database Integration Tests (`TestDatabaseIntegration`)

- **Save Operations**: Test saving to MongoDB
- **Data Retrieval**: Test reading from database
- **Cleanup**: Test proper data cleanup

### 4. Error Handling Tests (`TestErrorHandling`)

- **Network Errors**: Test Cloudinary upload failures
- **Invalid Data**: Test handling of invalid inputs
- **Database Errors**: Test database connection failures

### 5. Integration Tests (`TestCompleteWorkflow`)

- **End-to-End Workflow**: Test complete extraction → upload → save
- **Mock Integration**: Test with mocked external services

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r testing/requirements-test.txt

# Run all tests
python testing/run_tests.py

# Run with coverage
python testing/run_tests.py --coverage

# Run specific test types
python testing/run_tests.py --type unit
python testing/run_tests.py --type integration
python testing/run_tests.py --type cloudinary
```

### Using Pytest Directly

```bash
# Run all tests
pytest testing/ -v

# Run specific test file
pytest testing/test_cloudinary_integration.py -v

# Run specific test class
pytest testing/test_cloudinary_integration.py::TestCloudinaryUtils -v

# Run specific test method
pytest testing/test_cloudinary_integration.py::TestCloudinaryUtils::test_upload_image_to_cloudinary_success -v

# Run with coverage
pytest testing/ --cov=app.question_parsing --cov=database --cov-report=html
```

### Test Runner Options

```bash
# Install dependencies and run tests
python testing/run_tests.py --install-deps --type all --coverage --verbose

# Run only unit tests
python testing/run_tests.py --type unit

# Run only integration tests
python testing/run_tests.py --type integration

# Run only Cloudinary tests
python testing/run_tests.py --type cloudinary

# Run only database tests
python testing/run_tests.py --type database
```

## Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.unit`: Unit tests (fast, no external dependencies)
- `@pytest.mark.integration`: Integration tests (require database)
- `@pytest.mark.asyncio`: Async tests
- `@pytest.mark.slow`: Slow running tests

### Running by Markers

```bash
# Run only unit tests
pytest testing/ -m unit

# Run only integration tests
pytest testing/ -m integration

# Run async tests
pytest testing/ -m asyncio

# Skip slow tests
pytest testing/ -m "not slow"
```

## Test Coverage

The tests cover:

### Cloudinary Utils (100%)

- ✅ `upload_image_to_cloudinary()` - Success and failure cases
- ✅ `upload_figures_to_cloudinary()` - Multiple figure uploads
- ✅ `upload_overview_image_to_cloudinary()` - Overview image uploads
- ✅ Error handling for network failures
- ✅ Input validation

### Database Schema (100%)

- ✅ `DiagramExtractionResult` validation
- ✅ Required field enforcement
- ✅ Data type validation
- ✅ Optional field handling

### Database Integration (100%)

- ✅ Save operations to MongoDB
- ✅ Data retrieval and verification
- ✅ Cleanup operations
- ✅ Error handling

### Error Handling (100%)

- ✅ Network error scenarios
- ✅ Invalid data handling
- ✅ Database connection failures
- ✅ Cloudinary API failures

## Test Data

### Sample Images

Tests create sample PIL Images for testing:

- Simple RGB images with different colors
- Various sizes and formats
- Mock figure snippets (pages → figures)

### Mock Cloudinary Responses

```python
# Successful upload response
{
    'secure_url': 'https://res.cloudinary.com/test/image/upload/v123/test.png',
    'public_id': 'test_folder/test.png',
    'format': 'png'
}

# Error responses are mocked as exceptions
```

### Database Test Data

```python
# Sample extraction result
{
    'run_id': 'test_run_123',
    'total_figures': 2,
    'pages_processed': 2,
    'extraction_success': True,
    'figures': [...],
    'tables': [],
    'overview_image_figures': 'https://...',
    'overview_image_tables': None
}
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r testing/requirements-test.txt
      - name: Run tests
        run: python testing/run_tests.py --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## Best Practices

### Writing New Tests

1. **Use descriptive test names**: `test_upload_image_to_cloudinary_success`
2. **Test both success and failure cases**
3. **Use fixtures for common test data**
4. **Mock external dependencies**
5. **Clean up test data after tests**
6. **Use appropriate markers**

### Test Organization

```python
class TestFeatureName:
    """Test cases for specific feature"""

    @pytest.fixture
    def setup_data(self):
        """Setup test data"""
        pass

    def test_success_case(self, setup_data):
        """Test successful operation"""
        pass

    def test_failure_case(self, setup_data):
        """Test failure handling"""
        pass
```

### Mocking Guidelines

```python
# Mock external services
@patch('app.question_parsing.cloudinary_utils.cloudinary.uploader.upload')
def test_upload_function(self, mock_upload):
    mock_upload.return_value = {'secure_url': 'https://...'}
    # Test implementation
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**

   - Ensure MongoDB is running
   - Check environment variables
   - Use `--type unit` to skip database tests

2. **Cloudinary Configuration Missing**

   - Set environment variables for Cloudinary
   - Tests will mock Cloudinary if not configured

3. **Import Errors**

   - Ensure project root is in Python path
   - Install all test dependencies

4. **Async Test Failures**
   - Use `@pytest.mark.asyncio` for async tests
   - Ensure proper async/await usage

### Debug Mode

```bash
# Run with debug output
pytest testing/ -v -s --tb=long

# Run single test with debug
pytest testing/test_cloudinary_integration.py::TestCloudinaryUtils::test_upload_image_to_cloudinary_success -v -s
```

## Performance

### Test Execution Times

- **Unit Tests**: ~1-2 seconds
- **Integration Tests**: ~3-5 seconds
- **Full Test Suite**: ~10-15 seconds

### Optimization Tips

- Use `@pytest.mark.slow` for slow tests
- Mock external services in unit tests
- Use database transactions for integration tests
- Clean up test data efficiently

## Contributing

When adding new features:

1. **Write tests first** (TDD approach)
2. **Ensure 100% coverage** for new code
3. **Add appropriate markers**
4. **Update this documentation**
5. **Run full test suite** before committing

### Test Checklist

- [ ] Unit tests for new functions
- [ ] Integration tests for database operations
- [ ] Error handling tests
- [ ] Edge case tests
- [ ] Documentation updated
- [ ] All tests pass
- [ ] Coverage maintained
