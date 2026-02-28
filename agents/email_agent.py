"""
Email Generation Agent
Generates structured administrative emails (attestation, réclamation, stage, etc.)
using Gemini LLM based on user-provided fields.
"""
import json
import re
from typing import Dict, Any, Optional
from core.llm import get_llm_client


# Supported email types with required/optional fields
EMAIL_TYPES = {
    "attestation": {
        "label": "Attestation de scolarité",
        "required": ["nom_complet", "filiere", "annee", "matricule"],
        "optional": ["motif"],
        "description": "Demande d'attestation de scolarité"
    },
    "reclamation": {
        "label": "Réclamation",
        "required": ["nom_complet", "filiere", "annee", "matricule", "sujet_reclamation"],
        "optional": ["details"],
        "description": "Réclamation administrative ou académique"
    },
    "stage": {
        "label": "Demande de stage",
        "required": ["nom_complet", "filiere", "annee", "matricule", "entreprise", "periode_stage"],
        "optional": ["sujet_stage"],
        "description": "Demande de convention ou attestation de stage"
    },
    "conge": {
        "label": "Demande de congé / absence",
        "required": ["nom_complet", "filiere", "annee", "matricule", "date_debut", "date_fin", "motif"],
        "optional": [],
        "description": "Demande d'autorisation d'absence"
    },
    "releve_notes": {
        "label": "Demande de relevé de notes",
        "required": ["nom_complet", "filiere", "annee", "matricule"],
        "optional": ["semestre", "motif"],
        "description": "Demande de relevé de notes officiel"
    },
    "lettre_recommandation": {
        "label": "Demande de lettre de recommandation",
        "required": ["nom_complet", "filiere", "annee", "matricule", "destinataire"],
        "optional": ["objectif"],
        "description": "Demande de lettre de recommandation"
    },
    "personnalise": {
        "label": "Email personnalisé",
        "required": ["nom_complet", "sujet", "contenu"],
        "optional": ["filiere", "annee", "matricule"],
        "description": "Rédiger un email administratif personnalisé"
    }
}

# Field labels for the UI
FIELD_LABELS = {
    "nom_complet": "Nom complet",
    "filiere": "Filière",
    "annee": "Année d'étude",
    "matricule": "Matricule",
    "motif": "Motif",
    "sujet_reclamation": "Sujet de la réclamation",
    "details": "Détails supplémentaires",
    "entreprise": "Entreprise / Organisme",
    "periode_stage": "Période de stage",
    "sujet_stage": "Sujet du stage",
    "date_debut": "Date de début",
    "date_fin": "Date de fin",
    "semestre": "Semestre",
    "destinataire": "Destinataire",
    "objectif": "Objectif (master, emploi, etc.)",
    "sujet": "Sujet de l'email",
    "contenu": "Description du contenu souhaité"
}


class EmailAgent:
    """
    Agent for generating structured administrative emails.
    """

    def __init__(self):
        self.llm = get_llm_client()

    def get_email_types(self) -> Dict[str, Dict]:
        """Return available email types and their field definitions."""
        return EMAIL_TYPES

    def get_field_labels(self) -> Dict[str, str]:
        """Return human-readable labels for fields."""
        return FIELD_LABELS

    def validate_fields(self, email_type: str, fields: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate that all required fields are provided.

        Returns:
            {"valid": True} or {"valid": False, "missing": [...]}
        """
        if email_type not in EMAIL_TYPES:
            return {"valid": False, "missing": [], "error": f"Type d'email inconnu: {email_type}"}

        template = EMAIL_TYPES[email_type]
        missing = [f for f in template["required"] if not fields.get(f, "").strip()]

        if missing:
            labels = [FIELD_LABELS.get(f, f) for f in missing]
            return {"valid": False, "missing": labels}

        return {"valid": True}

    def generate_email(self, email_type: str, fields: Dict[str, str]) -> Dict[str, str]:
        """
        Generate an administrative email.

        Args:
            email_type: Type of email (attestation, reclamation, stage, etc.)
            fields: User-provided field values

        Returns:
            {"email_subject": "...", "email_body": "..."}
        """
        # Validate
        validation = self.validate_fields(email_type, fields)
        if not validation.get("valid"):
            missing = validation.get("missing", [])
            return {
                "email_subject": "",
                "email_body": f"Champs manquants: {', '.join(missing)}"
            }

        # Sanitize inputs
        sanitized = {k: self._sanitize(v) for k, v in fields.items() if v}

        template_info = EMAIL_TYPES[email_type]

        # Build prompt
        fields_text = "\n".join([
            f"- {FIELD_LABELS.get(k, k)}: {v}"
            for k, v in sanitized.items()
        ])

        prompt = f"""Tu es un assistant administratif universitaire expert en rédaction d'emails formels en français.

TYPE D'EMAIL: {template_info['label']} — {template_info['description']}

INFORMATIONS FOURNIES:
{fields_text}

INSTRUCTIONS:
1. Rédige un email administratif formel et professionnel en français
2. L'email doit commencer par "Madame, Monsieur," 
3. Utilise un ton respectueux et formel
4. Inclus toutes les informations fournies de manière naturelle
5. Termine par une formule de politesse et la signature avec le nom de l'étudiant
6. Ne mentionne PAS que tu es une IA

RÉPONDS UNIQUEMENT au format JSON suivant (sans markdown, sans ```):
{{"email_subject": "...", "email_body": "..."}}
"""

        try:
            response = self.llm.generate(prompt, temperature=0.3)
            return self._parse_response(response, sanitized)
        except Exception as e:
            print(f"[Email Agent Error] {e}")
            return {
                "email_subject": "",
                "email_body": f"Erreur lors de la génération: {str(e)}"
            }

    def _parse_response(self, response: str, fields: Dict[str, str]) -> Dict[str, str]:
        """Parse the LLM JSON response, with fallback."""
        try:
            # Try to extract JSON from the response
            # Remove markdown code blocks if present
            cleaned = response.strip()
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()

            result = json.loads(cleaned)

            if "email_subject" in result and "email_body" in result:
                return {
                    "email_subject": result["email_subject"],
                    "email_body": result["email_body"]
                }
        except (json.JSONDecodeError, KeyError):
            pass

        # Fallback: use the raw response as body
        nom = fields.get("nom_complet", "")
        return {
            "email_subject": f"Demande administrative — {nom}",
            "email_body": response.strip()
        }

    def _sanitize(self, value: str) -> str:
        """Sanitize user input to prevent prompt injection."""
        if not value:
            return ""
        # Remove potential prompt injection patterns
        sanitized = value.strip()
        # Limit length
        sanitized = sanitized[:500]
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', sanitized)
        return sanitized


# Singleton
_email_agent = None

def get_email_agent() -> EmailAgent:
    """Get or create EmailAgent singleton."""
    global _email_agent
    if _email_agent is None:
        _email_agent = EmailAgent()
    return _email_agent
