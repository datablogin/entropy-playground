# Contributing to Entropy-Playground

Thank you for your interest in contributing to Entropy-Playground! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct (to be added).

## How to Contribute

### Reporting Issues

- Check if the issue already exists in the [issue tracker](https://github.com/datablogin/entropy-playground/issues)
- Use the appropriate issue template
- Provide clear description and steps to reproduce
- Include relevant logs and error messages

### Suggesting Features

- Open a discussion in [GitHub Discussions](https://github.com/datablogin/entropy-playground/discussions)
- Describe the use case and benefits
- Consider implementation complexity

### Contributing Code

1. **Fork the Repository**
   ```bash
   gh repo fork datablogin/entropy-playground
   ```

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/entropy-playground.git
   cd entropy-playground
   ```

3. **Set Up Development Environment**
   ```bash
   # Create virtual environment
   uv venv --python 3.11
   source .venv/bin/activate
   
   # Install development dependencies
   uv pip install -e ".[dev]"
   
   # Install pre-commit hooks
   pre-commit install
   ```

4. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

5. **Make Your Changes**
   - Write clean, readable code
   - Add tests for new functionality
   - Update documentation as needed
   - Follow the project's coding standards

6. **Run Tests and Linting**
   ```bash
   # Run tests
   pytest
   
   # Run linting
   ruff check .
   black --check .
   mypy .
   ```

7. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add amazing new feature"
   ```

   Follow conventional commit format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `test:` for tests
   - `refactor:` for refactoring
   - `chore:` for maintenance

8. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   gh pr create
   ```

## Development Guidelines

### Code Style

- Python code follows [PEP 8](https://pep8.org/)
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Testing

- Write unit tests for new functionality
- Maintain or improve code coverage
- Use pytest fixtures for test setup
- Mock external dependencies

### Documentation

- Update docstrings for new functions/classes
- Update relevant documentation in `/docs`
- Include examples in docstrings
- Keep README.md up to date

### Git Workflow

- Keep commits atomic and focused
- Write clear commit messages
- Rebase on main before creating PR
- Squash commits if requested

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add entry to CHANGELOG (if exists)
4. Request review from maintainers
5. Address review feedback
6. Maintainer will merge when approved

## Getting Help

- Join discussions in [GitHub Discussions](https://github.com/datablogin/entropy-playground/discussions)
- Ask questions in issues with `question` label
- Reach out to maintainers

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- Annual contributor reports

Thank you for contributing to Entropy-Playground!