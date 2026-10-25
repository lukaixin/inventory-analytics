from dataclasses import dataclass
from .config import ALLOWED_LEGACY_SCOPES, ALLOWED_PDT_SCOPES, ALLOWED_MANAGEMENT_BUSINESS_LINES
@dataclass(frozen=True)
class ActorContext:
    actor_id:str="local-development"
    legacy_scopes:frozenset[str]=frozenset(ALLOWED_LEGACY_SCOPES)
    pdt_scopes:frozenset[str]=frozenset(ALLOWED_PDT_SCOPES)
    management_business_lines:frozenset[str]=frozenset(ALLOWED_MANAGEMENT_BUSINESS_LINES)
class AccessPolicy:
    def __init__(self,actor=ActorContext()): self.actor=actor
    def legacy(self,x): return not self.actor.legacy_scopes or x in self.actor.legacy_scopes
    def pdt(self,x): return not self.actor.pdt_scopes or x in self.actor.pdt_scopes
    def management(self,x): return not self.actor.management_business_lines or x in self.actor.management_business_lines
    def management_group(self): return not self.actor.management_business_lines
    def import_allowed(self): return not self.actor.legacy_scopes and not self.actor.pdt_scopes
    def global_evidence(self): return not self.actor.legacy_scopes
POLICY=AccessPolicy()
