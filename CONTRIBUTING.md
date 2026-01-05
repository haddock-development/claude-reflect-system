# Contributing to Claude Reflect System

First off, thank you for considering contributing to the Claude Reflect System! 🎉

## 🌟 How Can I Contribute?

### 1. Report Bugs

Found a bug? Help us fix it!

**Before submitting:**
- Check existing [issues](https://github.com/haddock-development/claude-reflect-system/issues)
- Ensure you're using the latest version

**Include in your report:**
- Claude Code version
- Python version (`python3 --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### 2. Suggest Features

Have an idea? We'd love to hear it!

**Good feature requests include:**
- Clear description of the problem it solves
- Examples of how it would work
- Why it's useful to others (not just you)

### 3. Improve Documentation

Documentation improvements are always welcome:
- Fix typos
- Clarify confusing sections
- Add examples
- Translate to other languages

### 4. Add Pattern Detection

Enhance the learning system with new patterns:

```python
# In reflect/scripts/extract_signals.py

# Add new correction pattern
CORRECTION_PATTERNS = [
    r"(?i)your_new_pattern_here",  # Your pattern
]
```

**Include:**
- Pattern regex
- Example sentences that match
- Test cases

### 5. Create Skills

Share your learned skills:
- Create useful skills
- Let them learn from corrections
- Share the results!

### 6. Code Contributions

**Setup Development Environment:**

```bash
# Clone
git clone https://github.com/haddock-development/claude-reflect-system.git
cd claude-reflect-system

# Install dependencies
pip3 install -r requirements.txt

# Install dev dependencies
pip3 install pytest black flake8 mypy

# Run tests (when available)
pytest tests/
```

**Coding Standards:**
- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests
- Keep it simple

**Before Submitting:**
- Run `black .` to format code
- Run `flake8 .` to check style
- Run `mypy .` to check types
- Test manually with Claude Code

## 📋 Pull Request Process

1. **Fork** the repository
2. **Create** a branch: `git checkout -b feature/amazing-feature`
3. **Make** your changes
4. **Test** thoroughly
5. **Commit**: `git commit -m "feat: add amazing feature"`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open** a Pull Request

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new pattern detection for German corrections
fix: resolve YAML parsing error in update_skill.py
docs: improve installation instructions
refactor: simplify signal extraction logic
test: add tests for pattern matching
```

### Pull Request Template

```markdown
## Description
What does this PR do?

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (describe)

## Testing
How did you test this?

## Checklist
- [ ] Code follows project style
- [ ] Self-reviewed the code
- [ ] Commented complex parts
- [ ] Updated documentation
- [ ] No new warnings
- [ ] Added tests (if applicable)
```

## 🎯 Development Guidelines

### Pattern Detection

When adding new patterns:
- Be specific (avoid false positives)
- Include examples
- Document in `signal-patterns.md`
- Consider edge cases

### Skill Updates

When modifying `update_skill.py`:
- Preserve YAML structure
- Always create backups
- Validate before writing
- Handle errors gracefully

### Documentation

- Keep README.md updated
- Update USER_GUIDE.md for new features
- Add examples
- Use clear language

## 🧪 Testing

Currently manual testing with Claude Code:
```bash
# Test pattern detection
python3 reflect/scripts/extract_signals.py test_transcript.jsonl

# Test skill update (use test skill)
python3 reflect/scripts/update_skill.py test-skill

# Test reflection flow
/reflect
```

**Future:** Automated test suite planned

## 🏗️ Project Structure

```
claude-reflect-system/
├── reflect/              # Core reflection system
│   ├── scripts/          # Main logic (Python/Shell)
│   ├── references/       # Documentation
│   └── .state/           # Runtime state
├── python-project-creator/  # Demo skill
├── docs/                 # Additional documentation (planned)
└── tests/                # Test suite (planned)
```

## 📜 Code of Conduct

### Our Standards

✅ **Positive Environment:**
- Be respectful and inclusive
- Accept constructive criticism
- Focus on what's best for the community

❌ **Unacceptable Behavior:**
- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Unprofessional conduct

### Enforcement

Violations will be reviewed and may result in:
1. Warning
2. Temporary ban
3. Permanent ban

Report issues to: haddock.development@gmail.com

## 💡 Ideas for Contributions

Not sure where to start? Try these:

### Beginner Friendly
- Fix typos in documentation
- Add more pattern examples
- Improve error messages
- Add comments to code

### Intermediate
- Add new correction patterns
- Improve backup system
- Enhance Git integration
- Add tests

### Advanced
- ML-based pattern detection
- Cross-skill learning
- Analytics dashboard
- VS Code extension

## 🎓 Learning Resources

New to the codebase? Start here:

1. **Read the docs:**
   - `README.md` - Overview
   - `USER_GUIDE.md` - Complete guide
   - `INSTALLATION.md` - Setup instructions

2. **Explore the code:**
   - `reflect/scripts/extract_signals.py` - Pattern detection
   - `reflect/scripts/update_skill.py` - Skill updates
   - `reflect/scripts/reflect.py` - Main orchestration

3. **Try it yourself:**
   - Install the system
   - Create corrections
   - Run `/reflect`
   - See how it works!

## 📬 Questions?

- **GitHub Discussions**: Ask questions
- **GitHub Issues**: Report bugs
- **HuggingFace**: [@mindchain](https://huggingface.co/mindchain)
- **Email**: haddock.development@gmail.com

## 🙏 Thank You!

Every contribution matters:
- Code contributions
- Bug reports
- Documentation improvements
- Feature suggestions
- Spreading the word

**Together we make AI that actually learns!** 🚀

---

*Happy Contributing!*
*The Claude Reflect Team*
