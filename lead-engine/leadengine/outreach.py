"""Drafting the first touch.

This is the one place an LLM genuinely earns its keep in this pipeline.
Finding the records is a data problem; scoring them is arithmetic. Writing
two hundred letters that each sound like a person wrote them, in a
situation where a tone-deaf sentence costs you the listing and possibly a
complaint, is what Claude is actually good at.

Everything generated here is a DRAFT for you to read before it is sent.
The system prompt below is a hard constraint, not a suggestion: no
pressure tactics, no claims about the estate, no pretending to know the
family. If the API is unavailable the module falls back to a plain
template so the pipeline still runs end to end offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

MODEL = os.environ.get("LEADENGINE_MODEL", "claude-opus-5")

# Hard rules for every draft. Written as constraints rather than style
# notes because the failure mode here is not a bad sentence, it is a
# letter that makes a grieving family feel hunted.
SYSTEM_PROMPT = """\
You write first-contact letters for a licensed real estate agent who works \
with families handling property after a death or a divorce.

These are people in the worst month of their year. Your job is to write \
something a decent neighbor would write - brief, plain, and easy to ignore \
without feeling pursued.

Hard rules:
- Never say "I'm sorry for your loss" and then pivot to business in the same
  breath. If you acknowledge the circumstance, do it once, plainly, and let
  it stand on its own.
- Never claim to know the family, the deceased, the property's condition, or
  what anyone intends to do with it.
- Never state or imply urgency, scarcity, or a deadline. No "before the
  market shifts", no "I have a buyer" unless the agent supplied one as fact.
- Never mention the court filing, the case number, or how you found them.
  They know their business is public record; saying so reads as surveillance.
- Never give legal or tax advice, and never speculate about probate timelines.
- Do not ask for a meeting in a first letter. Offer information and a way to
  reach you if they want it.
- Include a plain opt-out line.
- Use only facts supplied in the lead data and agent profile. Invent nothing.
  If a fact is missing, write around it - never guess at a name or address.

Style: short paragraphs, no more than 200 words, no exclamation marks, no \
marketing adjectives, no bulleted sales pitch. Sign with the agent's name, \
license number, and brokerage.

Output only the letter or script text. No preamble, no commentary.\
"""


@dataclass
class AgentProfile:
    """The licensee sending the outreach. All of this appears in the draft."""

    name: str
    brokerage: str
    license_number: str
    phone: str
    email: str = ""
    market_area: str = ""
    # Something specific and true - "I've handled 14 estate sales in this
    # county" beats any adjective a model can produce.
    credential_note: str = ""
    mailing_address: str = ""  # required on email under CAN-SPAM

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentProfile":
        known = {f for f in cls.__annotations__}
        return cls(**{k: v for k, v in data.items() if k in known})


def _lead_brief(lead) -> str:
    """The facts handed to the model. Deliberately narrow.

    Case numbers, filing dates, and scores are withheld on purpose - the
    model has no legitimate use for them and they leak into drafts.
    """
    lines = [
        f"Situation: {lead.lead_type}",
        f"Recipient name: {lead.contact_name or 'unknown'}",
        f"Recipient's role: {lead.contact_role}",
    ]
    if lead.property_address:
        city = lead.property_city or lead.county
        lines.append(f"Property: {lead.property_address}, {city} {lead.property_state}")
    if lead.is_absentee:
        lines.append(
            f"Recipient lives in {lead.mailing_state}, property is in "
            f"{lead.property_state} (they may be managing this from a distance)"
        )
    if lead.property_vacant:
        lines.append("The property is reported vacant.")
    return "\n".join(lines)


def _agent_brief(profile: AgentProfile) -> str:
    lines = [
        f"Agent: {profile.name}",
        f"Brokerage: {profile.brokerage}",
        f"License number: {profile.license_number}",
        f"Phone: {profile.phone}",
    ]
    if profile.email:
        lines.append(f"Email: {profile.email}")
    if profile.mailing_address:
        lines.append(f"Business mailing address: {profile.mailing_address}")
    if profile.market_area:
        lines.append(f"Works in: {profile.market_area}")
    if profile.credential_note:
        lines.append(f"True background detail to use: {profile.credential_note}")
    return "\n".join(lines)


_CHANNEL_INSTRUCTIONS = {
    "mail": "Write a physical letter. Open with a date line and their name.",
    "email": (
        "Write an email. Give a subject line on the first line as "
        "'Subject: ...', then the body. Include the agent's physical mailing "
        "address and an unsubscribe line, as CAN-SPAM requires."
    ),
    "phone": (
        "Write a CALL SCRIPT, not a letter. Open by naming yourself and your "
        "brokerage and asking whether this is a good moment. Include a natural "
        "exit if they say no, and a line honoring a do-not-call request on the "
        "spot. Keep it under 45 seconds spoken."
    ),
}


def draft_outreach(
    lead,
    profile: AgentProfile,
    channel: str = "mail",
    *,
    client: Optional[Any] = None,
    extra_context: str = "",
) -> tuple[str, str]:
    """Draft one piece of outreach.

    Returns (text, generator) where generator is "claude" or "template",
    so you can tell at a glance which drafts got the model and which fell
    back. Never raises on an API problem - it degrades to the template.
    """
    if channel not in _CHANNEL_INSTRUCTIONS:
        raise ValueError(
            f"unsupported channel {channel!r}; expected one of "
            f"{sorted(_CHANNEL_INSTRUCTIONS)}"
        )

    prompt = (
        f"{_CHANNEL_INSTRUCTIONS[channel]}\n\n"
        f"--- Lead ---\n{_lead_brief(lead)}\n\n"
        f"--- Agent ---\n{_agent_brief(profile)}\n"
    )
    if extra_context:
        prompt += f"\n--- Additional instructions from the agent ---\n{extra_context}\n"

    text = _call_claude(prompt, client=client)
    if text:
        return text, "claude"
    return _template(lead, profile, channel), "template"


def _call_claude(prompt: str, client: Optional[Any] = None) -> Optional[str]:
    """Return Claude's draft, or None if the API is unavailable or declines."""
    try:
        import anthropic
    except ImportError:
        return None

    if client is None:
        if not (os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            return None
        client = anthropic.Anthropic()

    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            # Sensitive subject matter sits close to a policy boundary; if the
            # primary model declines, let the API rescue the call in-flight
            # rather than dropping the draft on the floor.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as exc:
        print(f"  ! Claude API error {exc.status_code}: falling back to template")
        return None
    except anthropic.APIConnectionError:
        print("  ! could not reach the Claude API: falling back to template")
        return None

    if response.stop_reason == "refusal":
        return None

    parts = [b.text for b in response.content if b.type == "text"]
    return "\n".join(parts).strip() or None


def _template(lead, profile: AgentProfile, channel: str) -> str:
    """Deterministic fallback so the pipeline runs without an API key.

    Intentionally plain. It is meant to be edited, not sent as-is.
    """
    name = lead.contact_name or "Neighbor"
    where = lead.property_address or profile.market_area or "your area"
    contact = f"{profile.name}, {profile.brokerage} - {profile.phone}"
    license_line = f"License #{profile.license_number}"

    if channel == "phone":
        return (
            f"[CALL SCRIPT - DRAFT, review before dialing]\n\n"
            f"Hi, is this {name}? My name is {profile.name}, I'm a real estate "
            f"agent with {profile.brokerage}. Do you have a minute, or is this a "
            f"bad time?\n\n"
            f"[If bad time] No problem at all - I'll leave you alone. Would you "
            f"rather I sent something in the mail?\n\n"
            f"[If yes] I work with families who end up responsible for a property "
            f"they weren't planning on. I'm not calling to ask you to list "
            f"anything. If it would help to know what the property at {where} is "
            f"worth as-is, I can put that together at no cost and no obligation.\n\n"
            f"[If they decline] Understood - I'll take you off my list and you "
            f"won't hear from me again.\n\n"
            f"{contact} | {license_line}"
        )

    subject = "" if channel == "mail" else "Subject: A no-obligation offer of help\n\n"
    opt_out = (
        "If you'd rather not hear from me again, just let me know and I'll "
        "remove your name."
    )
    if channel == "email" and profile.mailing_address:
        opt_out += f"\n\n{profile.brokerage}, {profile.mailing_address}"

    return (
        f"{subject}Dear {name},\n\n"
        f"My name is {profile.name} and I'm a real estate agent with "
        f"{profile.brokerage} here in {profile.market_area or lead.county}.\n\n"
        f"I work with families who find themselves responsible for a property "
        f"they hadn't planned on. Sometimes that means selling, and often it "
        f"doesn't. Either way, people usually want to know what they're dealing "
        f"with before deciding anything.\n\n"
        f"If it would be useful, I'm glad to put together what {where} is worth "
        f"in its current condition - no cost, and no obligation to do anything "
        f"with it. If the timing is wrong, please ignore this letter entirely.\n\n"
        f"{opt_out}\n\n"
        f"Sincerely,\n{profile.name}\n{profile.brokerage}\n{license_line}\n"
        f"{profile.phone}"
        + (f"\n{profile.email}" if profile.email else "")
        + "\n\n[DRAFT - review before sending]"
    )
