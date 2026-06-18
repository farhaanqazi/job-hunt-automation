"""CV-driven candidate profile builder.

A *contract-based* extractor: the LLM only fills a fixed schema, never writes prose,
and every extracted skill/title/location is verified to appear verbatim in the CV or
the user's answers (see :mod:`jobhunt.profile.grounding`). Ungrounded items are dropped.
"""
