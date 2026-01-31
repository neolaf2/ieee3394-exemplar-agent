"""
Skill Loader for Claude Code Skills

Automatically discovers and loads skills from .claude/skills/ directory.
Compatible with Claude Code skill format.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List
import re

logger = logging.getLogger(__name__)


class SkillLoader:
    """
    Loads skills from .claude/skills/ directory.

    Supports Claude Code skill format:
    - SKILL.md with YAML frontmatter
    - Trigger patterns for skill activation
    - Skill instructions for Claude
    """

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Dict[str, Any]] = {}

    async def load_all_skills(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all skills from the skills directory.

        Returns:
            Dictionary of skill_name -> skill_definition
        """
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self.skills_dir}")
            return {}

        loaded_count = 0

        # Scan for skill directories
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                logger.debug(f"Skipping {skill_dir.name} - no SKILL.md found")
                continue

            try:
                skill = await self.load_skill(skill_file)
                if skill:
                    skill_name = skill.get('name', skill_dir.name)
                    self.skills[skill_name] = skill
                    loaded_count += 1
                    logger.info(f"Loaded skill: {skill_name}")

            except Exception as e:
                logger.error(f"Error loading skill from {skill_file}: {e}")

        logger.info(f"Loaded {loaded_count} skills from {self.skills_dir}")
        return self.skills

    async def load_skill(self, skill_file: Path) -> Dict[str, Any]:
        """
        Load a single skill from a SKILL.md file.

        Format:
        ```markdown
        ---
        name: skill-name
        description: Skill description
        triggers:
          - "trigger phrase 1"
          - "trigger phrase 2"
        ---

        # Skill Instructions

        Instructions for Claude when this skill is invoked...
        ```

        Returns:
            Dictionary with skill metadata and instructions
        """
        content = skill_file.read_text()

        # Extract YAML frontmatter
        frontmatter, instructions = self._parse_frontmatter(content)

        if not frontmatter:
            logger.warning(f"No frontmatter found in {skill_file}")
            return {}

        # Build skill definition
        skill = {
            'name': frontmatter.get('name', skill_file.parent.name),
            'description': frontmatter.get('description', ''),
            'triggers': frontmatter.get('triggers', []),
            'instructions': instructions,
            'file': str(skill_file)
        }

        return skill

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter from markdown file.

        Args:
            content: File content

        Returns:
            (frontmatter_dict, remaining_content)
        """
        # Match frontmatter between --- markers
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}, content

        frontmatter_text = match.group(1)
        instructions = match.group(2).strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_text)
            return frontmatter, instructions
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML frontmatter: {e}")
            return {}, instructions

    def get_skill_triggers(self) -> Dict[str, str]:
        """
        Get mapping of trigger patterns to skill names.

        Returns:
            Dictionary of {trigger_pattern: skill_name}
        """
        triggers = {}

        for skill_name, skill in self.skills.items():
            for trigger in skill.get('triggers', []):
                triggers[trigger.lower()] = skill_name

        return triggers

    def get_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        Get a specific skill by name.

        Args:
            skill_name: Name of the skill

        Returns:
            Skill definition dictionary, or empty dict if not found
        """
        return self.skills.get(skill_name, {})

    async def reload_skill(self, skill_name: str) -> bool:
        """
        Reload a specific skill from disk.

        Args:
            skill_name: Name of skill to reload

        Returns:
            True if successfully reloaded, False otherwise
        """
        skill = self.skills.get(skill_name)
        if not skill:
            logger.warning(f"Skill not found: {skill_name}")
            return False

        skill_file = Path(skill['file'])
        if not skill_file.exists():
            logger.warning(f"Skill file not found: {skill_file}")
            return False

        try:
            reloaded_skill = await self.load_skill(skill_file)
            if reloaded_skill:
                self.skills[skill_name] = reloaded_skill
                logger.info(f"Reloaded skill: {skill_name}")
                return True

        except Exception as e:
            logger.error(f"Error reloading skill {skill_name}: {e}")

        return False
