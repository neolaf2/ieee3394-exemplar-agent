"""
Test Skill Loader

Tests automatic skill discovery and loading from .claude/skills/
"""

import asyncio
from pathlib import Path
from src.ieee3394_agent.core.skill_loader import SkillLoader


async def test_skill_loader():
    """Test skill loader"""
    print("\n" + "="*60)
    print("Testing Skill Loader")
    print("="*60)

    skills_dir = Path(".claude/skills")

    print(f"\n1. Initializing skill loader...")
    print(f"   Skills directory: {skills_dir}")

    if not skills_dir.exists():
        print(f"   ✗ Skills directory does not exist")
        print(f"   Create it with: mkdir -p {skills_dir}")
        return

    loader = SkillLoader(skills_dir)
    print(f"   ✓ Skill loader initialized")

    print(f"\n2. Loading all skills...")
    try:
        skills = await loader.load_all_skills()

        print(f"   ✓ Loaded {len(skills)} skills:")
        for name, skill in skills.items():
            print(f"\n   Skill: {name}")
            print(f"   - Description: {skill['description']}")
            print(f"   - Triggers: {skill.get('triggers', [])}")
            print(f"   - Instructions length: {len(skill['instructions'])} chars")

            # Show first 100 chars of instructions
            preview = skill['instructions'][:100].replace('\n', ' ')
            if len(skill['instructions']) > 100:
                preview += "..."
            print(f"   - Preview: {preview}")

    except Exception as e:
        print(f"   ✗ Error loading skills: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\n3. Getting skill triggers...")
    try:
        triggers = loader.get_skill_triggers()

        print(f"   ✓ Found {len(triggers)} trigger patterns:")
        for pattern, skill_name in triggers.items():
            print(f"   - '{pattern}' → {skill_name}")

    except Exception as e:
        print(f"   ✗ Error getting triggers: {e}")
        return

    print(f"\n4. Testing individual skill loading...")
    if skills:
        # Get first skill
        skill_name = list(skills.keys())[0]
        skill_dir = skills_dir / skill_name
        skill_file = skill_dir / "SKILL.md"

        print(f"   Loading: {skill_file}")

        try:
            skill = await loader.load_skill(skill_file)

            print(f"   ✓ Loaded skill:")
            print(f"   - Name: {skill['name']}")
            print(f"   - Description: {skill['description']}")
            print(f"   - Has instructions: {bool(skill['instructions'])}")
            print(f"   - Has triggers: {bool(skill.get('triggers'))}")

        except Exception as e:
            print(f"   ✗ Error: {e}")
            return

    print(f"\n5. Testing skill validation...")
    try:
        # All loaded skills should be valid
        for name, skill in skills.items():
            assert 'name' in skill, f"Skill {name} missing 'name' field"
            assert 'description' in skill, f"Skill {name} missing 'description' field"
            assert 'instructions' in skill, f"Skill {name} missing 'instructions' field"
            assert skill['instructions'], f"Skill {name} has empty instructions"

        print(f"   ✓ All skills validated")

    except AssertionError as e:
        print(f"   ✗ Validation error: {e}")
        return

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_skill_loader())
