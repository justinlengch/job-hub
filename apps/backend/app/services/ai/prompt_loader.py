from pathlib import Path
from functools import lru_cache
from typing import Optional, Tuple
from string import Template

@lru_cache(maxsize=None)
def load_prompt(prompt_name: str) -> str:
    prompts_dir = Path(__file__).parent / "prompts"
    prompt_file = prompts_dir / f"{prompt_name}.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text(encoding="utf-8").strip()

def format_email_analysis_prompt(
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Format email analysis prompt into separate system and user prompts.
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    template_str = load_prompt("email_analysis")
    
    # Split the template at the EMAIL section
    if "===== EMAIL =====" in template_str:
        system_part, email_part = template_str.split("===== EMAIL =====", 1)
        system_prompt = system_part.strip()
        
        # Format the user prompt with actual email content
        template = Template(email_part)
        html_section = ""
        if body_html:
            html_section = f"\nHTML:\n{body_html}"
        
        user_prompt = template.substitute(
            subject=subject,
            body_text=body_text,
            html_section=html_section,
        ).strip()
        
        return system_prompt, user_prompt
    else:
        # Fallback to original behavior if template doesn't have the split
        template = Template(template_str)
        html_section = ""
        if body_html:
            html_section = f"\nHTML:\n{body_html}"
        
        full_prompt = template.substitute(
            subject=subject,
            body_text=body_text,
            html_section=html_section,
        )
        
        return "", full_prompt
