"""
📧 Email Generator Page
Generates structured administrative emails for university students.
"""
import streamlit as st
import json

st.set_page_config(
    page_title="Générateur d'Emails",
    page_icon="📧",
    layout="centered"
)

# Auth guard
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("Veuillez vous connecter d'abord.")
    st.page_link("app.py", label="🔑 Se connecter", icon="🏠")
    st.stop()

from agents.email_agent import get_email_agent, EMAIL_TYPES, FIELD_LABELS

email_agent = get_email_agent()

# ========== HEADER ==========
st.title("📧 Générateur d'Emails Administratifs")
st.markdown("Générez des emails formels pour vos demandes universitaires en quelques clics.")

st.divider()

# ========== EMAIL TYPE SELECTION ==========
type_options = {k: v["label"] for k, v in EMAIL_TYPES.items()}
selected_type = st.selectbox(
    "📋 Type d'email",
    options=list(type_options.keys()),
    format_func=lambda x: type_options[x],
    help="Choisissez le type de demande administrative"
)

template = EMAIL_TYPES[selected_type]
st.caption(f"ℹ️ {template['description']}")

st.divider()

# ========== DYNAMIC FORM ==========
st.markdown("### 📝 Informations requises")

fields = {}

# Pre-fill with user info if available
default_name = st.session_state.user.get("username", "") if st.session_state.user else ""

# Required fields
required_fields = template["required"]
optional_fields = template["optional"]

col1, col2 = st.columns(2)

for i, field in enumerate(required_fields):
    label = FIELD_LABELS.get(field, field)
    target_col = col1 if i % 2 == 0 else col2

    with target_col:
        if field == "contenu" or field == "details":
            fields[field] = st.text_area(
                f"{label} *",
                key=f"field_{field}",
                height=120
            )
        elif field == "annee":
            fields[field] = st.selectbox(
                f"{label} *",
                options=["1ère année", "2ème année", "3ème année", "4ème année", "5ème année"],
                key=f"field_{field}"
            )
        else:
            default = default_name if field == "nom_complet" else ""
            fields[field] = st.text_input(
                f"{label} *",
                value=default,
                key=f"field_{field}"
            )

# Optional fields
if optional_fields:
    st.markdown("### 📎 Informations optionnelles")
    col3, col4 = st.columns(2)

    for i, field in enumerate(optional_fields):
        label = FIELD_LABELS.get(field, field)
        target_col = col3 if i % 2 == 0 else col4

        with target_col:
            if field in ("details", "contenu", "motif"):
                fields[field] = st.text_area(
                    label,
                    key=f"field_{field}",
                    height=100
                )
            else:
                fields[field] = st.text_input(
                    label,
                    key=f"field_{field}"
                )

st.divider()

# ========== GENERATE BUTTON ==========
if st.button("✉️ Générer l'email", type="primary", use_container_width=True):
    # Validate
    validation = email_agent.validate_fields(selected_type, fields)

    if not validation.get("valid"):
        missing = validation.get("missing", [])
        st.error(f"⚠️ Champs manquants: {', '.join(missing)}")
    else:
        with st.spinner("✍️ Rédaction de l'email en cours..."):
            result = email_agent.generate_email(selected_type, fields)

        if result["email_subject"] and result["email_body"]:
            st.success("✅ Email généré avec succès!")

            # Store in session for display
            st.session_state["generated_email"] = result

            # Display subject
            st.markdown("### 📨 Objet")
            st.info(result["email_subject"])

            # Display body
            st.markdown("### 📄 Corps de l'email")
            st.text_area(
                "Contenu de l'email (modifiable)",
                value=result["email_body"],
                height=350,
                key="email_body_output"
            )

            # Action buttons
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                # Copy as JSON
                json_output = json.dumps(result, ensure_ascii=False, indent=2)
                st.download_button(
                    "📋 Télécharger JSON",
                    data=json_output,
                    file_name="email_generated.json",
                    mime="application/json",
                    use_container_width=True
                )

            with col_b:
                # Copy as text
                text_output = f"Objet: {result['email_subject']}\n\n{result['email_body']}"
                st.download_button(
                    "📄 Télécharger TXT",
                    data=text_output,
                    file_name="email_generated.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            with col_c:
                if st.button("🔄 Régénérer", use_container_width=True):
                    st.rerun()
        else:
            st.error(f"❌ {result['email_body']}")

# ========== PREVIOUSLY GENERATED ==========
if "generated_email" in st.session_state and not st.session_state.get("_just_generated"):
    prev = st.session_state["generated_email"]
    with st.expander("📬 Dernier email généré"):
        st.markdown(f"**Objet:** {prev['email_subject']}")
        st.text(prev["email_body"])

# Footer
st.markdown("---")
st.caption("📧 Générateur d'Emails | Université AI Assistant")
