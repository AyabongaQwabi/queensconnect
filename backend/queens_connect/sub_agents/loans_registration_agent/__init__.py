"""Loans registration agent (DEPRECATED). KYC via Didit.me, create lender/borrower profile.

Unified onboarding now handles the loans branch in onboarding_agent. When a user needs
to join the loans programme, loans_agent sets resumeFor and transfers to onboarding_agent.
This module is kept for reference only; it is not used as a sub-agent anymore.
"""

from .agent import loans_registration_agent
