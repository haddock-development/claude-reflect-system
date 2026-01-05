# Installation Guide - Claude Reflect System

This guide explains how to install and configure the Reflect system from scratch.

---

## 📋 Prerequisites

Before installing, ensure you have:

- ✅ **Claude Code CLI** installed and working
- ✅ **Python 3.8+** (check: `python3 --version`)
- ✅ **Git** (check: `git --version`)
- ✅ **PyYAML** package (will be installed automatically)

### System Requirements

- **OS**: macOS or Linux (Windows untested)
- **Shell**: bash or zsh
- **Permissions**: Write access to `~/.claude/skills/`

---

## 🚀 Quick Installation

### Option 1: Clone into Skills Directory

```bash
# Clone the repository
cd ~/.claude/skills
git clone https://github.com/haddock-development/claude-reflect-system.git temp-reflect

# Copy only the skills (not the .git directory)
cp -r temp-reflect/reflect .
cp -r temp-reflect/python-project-creator .

# Clean up
rm -rf temp-reflect
```

### Option 2: Manual Download

1. Download from GitHub: https://github.com/haddock-development/claude-reflect-system
2. Extract the archive
3. Copy `reflect/` and `python-project-creator/` to `~/.claude/skills/`

---

## ⚙️ Configuration

### Step 1: Install Python Dependencies

```bash
# The reflect system needs PyYAML
pip3 install pyyaml

# Or use uv (faster)
uv pip install pyyaml
```

### Step 2: Make Scripts Executable

```bash
cd ~/.claude/skills/reflect/scripts
chmod +x *.py *.sh
```

### Step 3: Configure Stop Hook

The Stop hook enables auto-reflection. Add to `~/.claude/settings.local.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/YOUR_USERNAME/.claude/skills/reflect/scripts/hook-stop.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

**IMPORTANT**: Replace `/Users/YOUR_USERNAME/` with your actual home directory path!

**Quick command to add (macOS/Linux):**

```bash
# Get your home directory
echo $HOME

# Edit settings manually or use this helper:
cat >> ~/.claude/settings.local.json << EOF
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.claude/skills/reflect/scripts/hook-stop.sh",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
EOF
```

**If settings.local.json already exists**, manually merge the `hooks` section!

### Step 4: Initialize Git (Optional but Recommended)

For tracking skill evolution:

```bash
cd ~/.claude/skills
git init
git config user.email "you@example.com"
git config user.name "Your Name"
git add reflect/ python-project-creator/
git commit -m "Initial: Add reflect system"
```

### Step 5: Verify Installation

```bash
# Check if reflect is recognized
/reflect-status
```

**Expected output:**

```
═══════════════════════════════════════════════════════════
                    REFLECTION STATUS
═══════════════════════════════════════════════════════════

Status:        ⊘ Deaktiviert
Mode:          Nur manuell
...
```

If you see this, ✅ **installation successful**!

---

## 🧪 Test the System

### Test 1: Manual Reflection

```bash
# In a Claude Code session, create a Python project
# (This will trigger python-project-creator skill)

# Claude will use pip (as initially documented)
# Correct it:
"No, use uv instead of pip!"

# Run reflection:
/reflect

# Follow the review prompts
# Approve with 'A'

# Check if skill was updated:
head -25 ~/.claude/skills/python-project-creator/SKILL.md
# Should now show "Critical Corrections" section!
```

### Test 2: Auto-Reflection

```bash
# Enable auto-reflection
/reflect-on

# Work with Claude, make a correction
# End the session (Ctrl+D or /exit)

# Check logs:
tail ~/.claude/reflect-hook.log

# Next session: Check if changes were applied
head -30 ~/.claude/skills/python-project-creator/SKILL.md
```

---

## 🛠️ Troubleshooting

### Problem: "/reflect-status" not recognized

**Cause**: Skill not loaded or path wrong

**Fix**:
```bash
# Verify skill location
ls -la ~/.claude/skills/reflect/SKILL.md

# Restart Claude Code session
```

### Problem: "Permission denied" when running scripts

**Cause**: Scripts not executable

**Fix**:
```bash
chmod +x ~/.claude/skills/reflect/scripts/*.py
chmod +x ~/.claude/skills/reflect/scripts/*.sh
```

### Problem: Hook doesn't trigger

**Cause**: Hook path incorrect in settings.local.json

**Fix**:
```bash
# Check your actual path
echo "$HOME/.claude/skills/reflect/scripts/hook-stop.sh"

# Verify file exists
ls -la $HOME/.claude/skills/reflect/scripts/hook-stop.sh

# Update settings.local.json with correct path
```

### Problem: "No module named 'yaml'"

**Cause**: PyYAML not installed

**Fix**:
```bash
pip3 install pyyaml
# or
uv pip install pyyaml
```

### Problem: Hook times out

**Cause**: Transcript too large or processing slow

**Fix**: Hook spawns background process, should complete eventually. Check log:
```bash
tail -f ~/.claude/reflect-hook.log
```

---

## 📂 Directory Structure After Installation

```
~/.claude/
├── skills/
│   ├── reflect/                    # Self-learning system
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── USER_GUIDE.md
│   │   ├── scripts/
│   │   │   ├── reflect.py
│   │   │   ├── extract_signals.py
│   │   │   ├── update_skill.py
│   │   │   ├── present_review.py
│   │   │   ├── hook-stop.sh
│   │   │   ├── toggle-on.sh
│   │   │   ├── toggle-off.sh
│   │   │   └── toggle-status.sh
│   │   ├── .state/
│   │   │   ├── auto-reflection.json
│   │   │   └── last-reflection.timestamp
│   │   └── references/
│   │       └── signal-patterns.md
│   └── python-project-creator/     # Demo skill
│       ├── SKILL.md
│       ├── scripts/
│       ├── references/
│       └── assets/
└── settings.local.json              # With hooks configured
```

---

## 🔧 Advanced Configuration

### Custom Pattern Detection

Edit `~/.claude/skills/reflect/scripts/extract_signals.py`:

```python
# Add your own patterns
CORRECTION_PATTERNS = [
    r"(?i)no,?\s+don't\s+(?:do|use)\s+(.+?)[,.]?\s+(?:do|use)\s+(.+)",
    r"(?i)YOUR_CUSTOM_PATTERN",  # ← Add here
]
```

### Backup Retention

Default: 30 days. To change:

Edit `~/.claude/skills/reflect/scripts/update_skill.py`:

```python
def cleanup_old_backups(backup_dir, days=30):  # ← Change days here
```

### Hook Timeout

Default: 5 seconds. To change in `~/.claude/settings.local.json`:

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "timeout": 10000  // ← Change to 10 seconds
      }]
    }]
  }
}
```

---

## 📚 Next Steps

After successful installation:

1. **Read the User Guide**: `~/.claude/skills/reflect/USER_GUIDE.md`
2. **Test manually first**: Use `/reflect` a few times
3. **Enable auto-mode**: Run `/reflect-on` when ready
4. **Check Git history**: `cd ~/.claude/skills && git log`

---

## 🔄 Updating

To get the latest version:

```bash
cd /tmp
git clone https://github.com/haddock-development/claude-reflect-system.git
cd claude-reflect-system

# Backup your current version
cp -r ~/.claude/skills/reflect ~/.claude/skills/reflect.backup

# Copy new version
cp -r reflect ~/.claude/skills/

# Check what changed
diff -r ~/.claude/skills/reflect.backup ~/.claude/skills/reflect
```

---

## 🗑️ Uninstallation

To remove the system:

```bash
# Remove skills
rm -rf ~/.claude/skills/reflect
rm -rf ~/.claude/skills/python-project-creator

# Remove hooks from settings.local.json (manual edit)
# Remove git history (optional)
cd ~/.claude/skills
rm -rf .git
```

---

## ✅ Installation Checklist

- [ ] Python 3.8+ installed
- [ ] Claude Code working
- [ ] Git installed
- [ ] PyYAML installed (`pip3 install pyyaml`)
- [ ] `reflect/` copied to `~/.claude/skills/`
- [ ] `python-project-creator/` copied to `~/.claude/skills/`
- [ ] Scripts made executable (`chmod +x`)
- [ ] Hook configured in `settings.local.json`
- [ ] Git initialized (optional)
- [ ] `/reflect-status` works
- [ ] Tested with `/reflect`

---

## 🆘 Need Help?

- **Documentation**: Read `reflect/USER_GUIDE.md`
- **Issues**: https://github.com/haddock-development/claude-reflect-system/issues
- **Logs**: Check `~/.claude/reflect-hook.log`

---

**Installation complete!** 🎉

Start using: `/reflect-status` → Work with Claude → `/reflect`
