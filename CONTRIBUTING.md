# Contributing to Pharma Agent

Welcome to the **Pharma Agent** repository! We deeply appreciate your contributions to help improve this open-source project.

---

## 🛠️ Ways to Contribute

There are several ways you can contribute to the development and accuracy of the Pharma Agent:

- **Fixing Typos or Formatting**: Simple grammar, spelling, or documentation enhancements.
- **Updating Dependencies**: Keeping versions of Python libraries, Node packages, or Docker files up-to-date.
- **Bug Fixes**: Resolving issues with backend endpoints, frontend Phaser UI, or the ingestion pipeline.
- **Improving Knowledge Accuracy**: Suggestions or edits to the J&J content corpus in `jnj_content.txt`.
- **Operating System Support**: Adding guides or fixes for running on different operating systems (Windows/macOS/Linux).

---

## 🐛 Reporting Issues

If you find a bug, have a question, or would like to request a new feature:
1. Search the existing issues to see if it has already been reported.
2. Open a new issue with a clear description, reproduction steps, and screenshots if applicable.

---

## 📬 Submitting Changes

1. **Fork the Repository**: Create a fork of the codebase under your own GitHub account.
2. **Create a Branch**: Create a descriptive branch name from `main` (e.g., `feature/improve-rag-retrieval` or `bugfix/fix-websocket-cors`).
3. **Make and Test Your Changes**: Run local verification tests to ensure nothing is broken.
4. **Follow Formatting Rules**: Run formatter/linter commands to ensure clean code standards:
   - For Backend: `make format-fix` and `make lint-fix`
5. **Commit & Push**: Write clear and descriptive commit messages, push your branch to your fork.
6. **Open a Pull Request**: Submit a Pull Request to the main branch of `apra05/Pharma_agent`. Provide a detailed summary of what was changed and why.

---

## 📐 Code Quality Guidelines

To maintain code readability and reliability:
- Keep code clean, modular, and well-documented.
- Write docstrings and comments for complex logic.
- Ensure that modifications to agent behavior do not disrupt the core J&J corporate identity guidelines defined in `philosopher_factory.py`.
