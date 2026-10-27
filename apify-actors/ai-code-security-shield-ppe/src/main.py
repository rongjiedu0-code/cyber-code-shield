from .common.runtime import execute, entrypoint
from .shield_engine import collect, collect_fallback, settings


async def run_actor(actor):
    """Default code is analyzed now using AST + regex; it is not a canned finding."""
    return await execute(actor, settings, collect, 'security-audit-file', 'ai-code-security-shield-ppe', collect_fallback)


def main():
    entrypoint(run_actor)
